import uuid
import random
import string
from datetime import datetime, timedelta, timezone
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from fastapi.security import OAuth2PasswordRequestForm
import redis.asyncio as aioredis
from redis_client import get_redis
from services.rate_limiter_service import RateLimiterService, _fallback_memory_limiter

import models, schemas, auth, dependencies
from database import get_db
from services.email_service import send_email

router = APIRouter(tags=["Auth"])

# ─── Hàm tiện ích nội bộ ────────────────────────────────────────────────────

# Cấu hình giới hạn OTP
OTP_EXPIRE_MINUTES = 5         # Mã OTP hết hạn sau 5 phút
OTP_RATE_LIMIT_SECONDS = 60    # Không gửi lại trong vòng 60 giây
OTP_MAX_ATTEMPTS = 5           # Tối đa 5 lần nhập sai
VALID_OTP_PURPOSES = {"PARENT_REGISTER", "PARENT_CHANGE_EMAIL", "PARENT_RESET_PASSWORD"}


def _generate_otp_code() -> str:
    """Sinh mã OTP 6 chữ số ngẫu nhiên."""
    return "".join(random.choices(string.digits, k=6))


def _validate_username(username: str) -> str:
    """
    Chuẩn hóa và kiểm tra username hợp lệ.
    Trả về username đã chuẩn hóa hoặc ném HTTPException nếu không hợp lệ.
    """
    import re
    username = username.strip().lower()
    if len(username) < 3 or len(username) > 30:
        raise HTTPException(
            status_code=422,
            detail="Tên tài khoản phải từ 3 đến 30 ký tự."
        )
    if not re.match(r"^[a-z0-9_]+$", username):
        raise HTTPException(
            status_code=422,
            detail="Tên tài khoản chỉ được chứa chữ cái (a-z), số (0-9) và dấu gạch dưới (_)."
        )
    return username


def _auto_gen_username_from_email(email: str, db: Session) -> str:
    """
    Tự động sinh username duy nhất từ email (dùng cho Google OAuth user mới).
    Công thức: prefix_email + số ngẫu nhiên 4 chữ số, thử lại nếu trùng.
    """
    import re
    base = re.sub(r"[^a-z0-9_]", "_", email.split("@")[0].lower())[:16]
    if not base:
        base = "user"
    for _ in range(20):  # thử tối đa 20 lần
        suffix = "".join(random.choices(string.digits, k=4))
        candidate = f"{base}_{suffix}"
        if not db.query(models.User).filter(models.User.username == candidate).first():
            return candidate
    # Fallback an toàn: dùng uuid
    return f"user_{uuid.uuid4().hex[:8]}"


def _request_otp_internal(
    email: str,
    purpose: str,
    db: Session,
) -> models.EmailOtp:
    """
    Logic lõi gửi OTP — dùng chung cho cả endpoint đăng ký lẫn cài đặt.
    Áp dụng:
      - Rate-limit 60s: Trả 429 nếu gửi lại quá sớm.
      - Hủy mã cũ cùng email+purpose trước khi tạo mã mới.
    """
    now = datetime.now(timezone.utc)

    # Kiểm tra rate-limit: tìm mã OTP gần nhất còn hiệu lực của email+purpose
    recent_otp = (
        db.query(models.EmailOtp)
        .filter(
            models.EmailOtp.email == email,
            models.EmailOtp.purpose == purpose,
            models.EmailOtp.is_used.is_(False),
        )
        .order_by(models.EmailOtp.created_at.desc())
        .first()
    )

    if recent_otp and recent_otp.last_sent_at:
        elapsed = (now - recent_otp.last_sent_at).total_seconds()
        if elapsed < OTP_RATE_LIMIT_SECONDS:
            wait = int(OTP_RATE_LIMIT_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Vui lòng chờ thêm {wait} giây trước khi gửi lại mã."
            )

    # Hủy (invalidate) tất cả mã OTP cũ còn hiệu lực của email+purpose này
    db.query(models.EmailOtp).filter(
        models.EmailOtp.email == email,
        models.EmailOtp.purpose == purpose,
        models.EmailOtp.is_used.is_(False),
    ).update({"is_used": True})

    # Tạo mã OTP mới
    new_otp = models.EmailOtp(
        email=email,
        otp_code=_generate_otp_code(),
        purpose=purpose,
        attempts=0,
        expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
        is_used=False,
        last_sent_at=now,
    )
    db.add(new_otp)
    db.commit()
    db.refresh(new_otp)
    return new_otp


def _send_otp_email(to_email: str, otp_code: str, purpose: str):
    """Gửi email OTP với template HTML căn bản."""
    if purpose == "PARENT_CHANGE_EMAIL":
        subject = "[SocraticKid] Xác nhận đổi email nhận thông báo"
        instruction = "xác nhận đổi địa chỉ email nhận thông báo"
    elif purpose == "PARENT_RESET_PASSWORD":
        subject = "[SocraticKid] Mã OTP khôi phục mật khẩu Phụ huynh"
        instruction = "đặt lại mật khẩu cho tài khoản Phụ huynh"
    else:
        subject = "[SocraticKid] Mã xác nhận tài khoản Phụ huynh"
        instruction = "hoàn tất kích hoạt tài khoản Phụ huynh"

    text_content = (
        f"Mã OTP của bạn là: {otp_code}\n"
        f"Mã có hiệu lực trong {OTP_EXPIRE_MINUTES} phút. Không chia sẻ mã này với ai."
    )
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
        <div style="background-color: #8C4905; padding: 16px; border-radius: 8px; text-align: center;">
            <h2 style="color: #fff; margin: 0;">SocraticKid – Xác Thực Tài Khoản</h2>
        </div>
        <div style="padding: 24px 0;">
            <p>Chào bạn,</p>
            <p>Bạn vừa yêu cầu mã OTP để <strong>{instruction}</strong>.</p>
            <div style="text-align: center; margin: 24px 0;">
                <span style="font-size: 36px; font-weight: bold; letter-spacing: 10px;
                             color: #8C4905; background: #FDF5EC; padding: 12px 24px;
                             border-radius: 8px; border: 2px dashed #C1762A;">
                    {otp_code}
                </span>
            </div>
            <p style="color: #888; font-size: 13px;">
                Mã có hiệu lực trong <strong>{OTP_EXPIRE_MINUTES} phút</strong>.
                Không chia sẻ mã này với ai.
            </p>
        </div>
        <div style="text-align: center; font-size: 12px; color: #bbb; border-top: 1px solid #eee; padding-top: 12px;">
            Hệ thống Trợ lý SocraticKid – Dạy bằng phương pháp gợi mở tư duy.
        </div>
    </body>
    </html>
    """
    send_email(
        to_email=to_email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        category="OTP",
    )

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.RegisterInput, db: Session = Depends(get_db)):
    """
    US 9.1 - T9.1:
    Đăng ký tài khoản mới bằng username + mật khẩu (đồng bộ luồng Onboarding):
    - Không yêu cầu email — giảm rào cản cho học sinh nhỏ tuổi.
    - Tạo tài khoản với role='PENDING'.
    - Frontend chuyển hướng sang /onboarding: chọn vai trò và khối lớp (học sinh)
      hoặc nhập email + OTP (phụ huynh).
    """
    username = _validate_username(user_data.username)

    # Kiểm tra username chưa được dùng
    existing = db.query(models.User).filter(
        func.lower(models.User.username) == username
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tên tài khoản đã tồn tại, vui lòng chọn tên khác.")

    new_user = models.User(
        username=username,
        email=None,            # Học sinh không cần email
        hashed_password=auth.hash_password(user_data.password),
        role="PENDING",
        grade=None,
        email_verified=False,
        session_version=1,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/register/student", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    normalized_email = user_data.email.lower().strip()
    existing_user = db.query(models.User).filter(func.lower(models.User.email) == normalized_email).first()
    if existing_user:
        if existing_user.oauth_provider == "google" or existing_user.google_id:
            raise HTTPException(
                status_code=400,
                detail="Email này đã được đăng nhập bằng tài khoản Google. Vui lòng sử dụng email khác hoặc đăng nhập bằng Google."
            )
        raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống. Vui lòng chọn email khác.")

    # Validate grade bắt buộc và hợp lệ cho STUDENT
    if user_data.grade is None or user_data.grade not in range(4, 10):
        raise HTTPException(status_code=422, detail="Lớp học phải là số từ 4 đến 9")

    new_user = models.User(
        email=normalized_email,
        hashed_password=auth.hash_password(user_data.password),
        role="STUDENT",
        grade=user_data.grade
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/register/monitor", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_monitor(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    normalized_email = user_data.email.lower().strip()
    existing_user = db.query(models.User).filter(func.lower(models.User.email) == normalized_email).first()
    if existing_user:
        if existing_user.oauth_provider == "google" or existing_user.google_id:
            raise HTTPException(
                status_code=400,
                detail="Email này đã được đăng nhập bằng tài khoản Google. Vui lòng sử dụng email khác hoặc đăng nhập bằng Google."
            )
        raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống. Vui lòng chọn email khác.")

    new_user = models.User(
        email=normalized_email,
        hashed_password=auth.hash_password(user_data.password),
        role="MONITOR"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

from sqlalchemy import func

@router.post("/login", response_model=schemas.TokenResponse)
@router.post("/auth/login", response_model=schemas.TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    US 9.1 (T9.1): Đăng nhập bằng username HOẶC email (tương thích ngược với user cũ).
    US 11.1 - Task #360: Phòng thủ Brute-force 3 lớp:
    - Lớp 1: Khóa 15 phút theo cặp (Username + Client IP) nếu sai 5 lần liên tiếp.
    - Lớp 2: Khóa 30 phút theo IP nếu quét sai trên 20 tài khoản khác nhau.
    - Lớp 3: Theo dõi Username đa IP, áp dụng progressive delay nếu nghi ngờ xoay proxy.
    """
    normalized = form_data.username.lower().strip()
    client_ip = RateLimiterService.extract_client_ip(request)

    # 1. KIỂM TRA TẠM KHÓA TRƯỚC (Bảo vệ CPU băm bcrypt)
    is_locked, lock_info = await RateLimiterService.check_login_lockout(
        redis_client=redis,
        username=normalized,
        client_ip=client_ip
    )
    if is_locked and lock_info:
        raise RateLimiterService.create_429_exception(
            reason=lock_info["reason"],
            message=lock_info["message"],
            limit=RateLimiterService.MAX_LOGIN_ATTEMPTS,
            remaining=0,
            retry_after=lock_info["retry_after"],
            reset_at=lock_info["reset_at"],
        )

    # 2. Trước tiên dò query cả username lẫn email cùng lúc (OR)
    user = (
        db.query(models.User)
        .filter(
            or_(
                func.lower(models.User.username) == normalized,
                func.lower(models.User.email) == normalized,
            )
        )
        .first()
    )

    is_valid_user = (
        user is not None
        and bool(user.hashed_password)
        and auth.verify_password(form_data.password, user.hashed_password)
    )

    if not is_valid_user:
        # Ghi nhận lần nhập sai mật khẩu (Task #360)
        failure_info = await RateLimiterService.record_login_failure(
            redis_client=redis,
            username=normalized,
            client_ip=client_ip
        )

        # Lớp 3: Nếu phát hiện dấu hiệu brute-force từ nhiều IP lạ, áp dụng delay lũy tiến
        if failure_info.get("progressive_delay"):
            await asyncio.sleep(2.0)

        if failure_info.get("is_locked"):
            raise RateLimiterService.create_429_exception(
                reason=failure_info["reason"],
                message=failure_info["message"],
                limit=RateLimiterService.MAX_LOGIN_ATTEMPTS,
                remaining=0,
                retry_after=failure_info["retry_after"],
                reset_at=failure_info["reset_at"],
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_credentials",
                "message": failure_info["message"],
                "remaining_attempts": failure_info["remaining_attempts"],
            }
        )

    # 3. ĐĂNG NHẬP THÀNH CÔNG: Xóa lịch sử thử sai của cặp (Username + IP)
    actual_username = user.username.lower() if user.username else normalized
    await RateLimiterService.clear_login_failures(
        redis_client=redis,
        username=actual_username,
        client_ip=client_ip
    )
    if actual_username != normalized:
        await RateLimiterService.clear_login_failures(
            redis_client=redis,
            username=normalized,
            client_ip=client_ip
        )

    raw_refresh_token = auth.create_refresh_token()
    refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(raw_refresh_token),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
        ),
        revoked=False
    )
    db.add(refresh_token_db)
    db.commit()
    
    user_version = getattr(user, "session_version", 1) or 1
    access_token = auth.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "grade_level": user.grade,
            "session_version": user_version,
        }
    )
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer",
        "username": user.username,
        "grade": user.grade,  # Task #132: trả về FE để hiển thị và lưu local
        "session_version": user_version,  # US 6.2: phiên bản session của user
    }


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_access_token(
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db)
):
    token_hash = auth.hash_refresh_token(data.refresh_token)

    stored_token = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash)
        .first()
    )

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ"
        )

    if stored_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã bị thu hồi"
        )

    now = datetime.now(timezone.utc)

    if stored_token.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã hết hạn"
        )

    user = (
        db.query(models.User)
        .filter(models.User.id == stored_token.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User không tồn tại"
        )

    # Token cũ không được sử dụng lại
    stored_token.revoked = True

    new_refresh_token = auth.create_refresh_token()

    new_refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(new_refresh_token),
        expires_at=(
            now + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
        )
    )

    db.add(new_refresh_token_db)

    # Tạo access token mới
    user_version = getattr(user, "session_version", 1) or 1
    new_access_token = auth.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "grade_level": user.grade,  # Task #132: cấp lại grade khi refresh token
            "session_version": user_version,  # US 6.2: cấp lại session_version mới nhất từ DB
        }
    )

    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "username": user.username,
        "grade": user.grade,  # Task #132: trả về grade mới nhất
        "session_version": user_version,  # US 6.2: trả về session_version mới nhất
    }


# ==============================================================================
# US 8.3 (Task T8.19): Google OAuth Callback & Onboarding
# ==============================================================================

@router.post("/auth/google-callback", response_model=schemas.GoogleAuthResponse)
@router.post("/google-callback", response_model=schemas.GoogleAuthResponse, include_in_schema=False)
def google_callback(
    payload: schemas.GoogleCallbackRequest,
    db: Session = Depends(get_db),
):
    """
    US 8.3 - Task T8.19:
    Tiếp nhận thông tin hồ sơ Google từ NextAuth sau khi người dùng xác thực Google thành công.
    - Kiểm tra email trong DB:
      + Nếu chưa có: Tạo mới user (oauth_provider='google', hashed_password=None, role='STUDENT', grade=None).
        Đặt is_new_user = True (để FE điều hướng sang /onboarding).
      + Nếu đã có: Liên kết google_id nếu chưa có.
        Nếu user đã có khối lớp hoặc vai trò MONITOR -> is_new_user = False (vào thẳng Dashboard).
        Nếu user là STUDENT nhưng chưa có khối lớp -> is_new_user = True (yêu cầu onboarding).
    - Cấp JWT access_token và refresh_token hợp lệ của backend để gọi các API /chat, /bookmarks,...
    """
    normalized_email = payload.email.lower().strip()
    resolved_google_id = (payload.google_id or payload.sub or "").strip() or None

    # 1. Tra cứu user qua google_id trước
    user = None
    if resolved_google_id:
        user = db.query(models.User).filter(models.User.google_id == resolved_google_id).first()

    # 2. Nếu chưa thấy qua google_id, tra cứu theo email chuẩn hóa
    if not user:
        user = db.query(models.User).filter(func.lower(models.User.email) == normalized_email).first()

    is_new = False

    if not user:
        # User hoàn toàn mới -> Tạo mới bản ghi user trong DB với role='PENDING' (chưa chọn vai trò)
        is_new = True
        initial_role = payload.role if (payload.role in ("STUDENT", "MONITOR")) else "PENDING"
        initial_grade = payload.grade if (payload.grade and payload.grade in range(4, 10)) else None

        # US 9.1: Tự động sinh username từ email Google
        auto_username = _auto_gen_username_from_email(normalized_email, db)

        user = models.User(
            id=uuid.uuid4().hex,
            email=normalized_email,
            username=auto_username,
            google_id=resolved_google_id,
            oauth_provider="google",
            hashed_password=None,
            role=initial_role,
            grade=initial_grade,
            email_verified=True,  # Google đã xác thực email -> đánh dấu luôn
            session_version=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # User đã tồn tại -> Liên kết google_id / oauth_provider nếu chưa có
        need_commit = False
        if resolved_google_id and not user.google_id:
            user.google_id = resolved_google_id
            need_commit = True
        if not user.oauth_provider:
            user.oauth_provider = "google"
            need_commit = True
        if payload.grade and not user.grade and payload.grade in range(4, 10):
            user.grade = payload.grade
            need_commit = True
        if need_commit:
            db.commit()
            db.refresh(user)

        # Xác định user có cần Onboarding không:
        # Nếu role là PENDING hoặc là STUDENT nhưng chưa chọn lớp -> is_new = True
        if user.role == "PENDING" or (user.role == "STUDENT" and user.grade is None):
            is_new = True
        else:
            is_new = False

    # 3. Tạo Refresh Token lưu vào DB
    raw_refresh_token = auth.create_refresh_token()
    refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(refresh_token_db)
    db.commit()

    # 4. Sinh JWT Access Token chuẩn của Backend
    user_version = getattr(user, "session_version", 1) or 1
    access_token = auth.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "grade_level": user.grade,
            "session_version": user_version,
        }
    )

    return schemas.GoogleAuthResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        is_new_user=is_new,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        grade=user.grade,
        session_version=user_version,
    )


@router.post("/auth/onboarding", response_model=schemas.GoogleAuthResponse)
def complete_onboarding(
    payload: schemas.OnboardingRequest,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 8.3 - Task T8.21:
    Endpoint hoàn tất Onboarding:
    - Nhận role ("STUDENT" hoặc "MONITOR") và grade (4-9 nếu STUDENT).
    - Cập nhật thông tin user và cấp JWT mới nhất.
    """
    target_role = payload.role.upper().strip()
    if target_role not in ("STUDENT", "MONITOR"):
        raise HTTPException(status_code=400, detail="Vai trò phải là STUDENT hoặc MONITOR.")

    grade_val = None
    if target_role == "STUDENT":
        if payload.grade is None or payload.grade not in range(4, 10):
            raise HTTPException(status_code=422, detail="Học sinh phải chọn khối lớp từ 4 đến 9.")
        grade_val = payload.grade

    user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")

    user.role = target_role
    user.grade = grade_val
    user.session_version = (user.session_version or 1) + 1
    db.commit()
    db.refresh(user)

    # Cấp access token mới đã có role và grade_level
    new_access_token = auth.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "grade_level": user.grade,
            "session_version": user.session_version,
        }
    )

    # Sinh Refresh Token mới
    raw_refresh_token = auth.create_refresh_token()
    refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(raw_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(refresh_token_db)
    db.commit()

    return schemas.GoogleAuthResponse(
        access_token=new_access_token,
        refresh_token=raw_refresh_token,
        token_type="bearer",
        is_new_user=False,
        user_id=str(user.id),
        username=user.username,
        email=user.email,
        role=user.role,
        grade=user.grade,
        session_version=user.session_version,
    )


@router.post("/auth/cancel-onboarding")
@router.post("/cancel-onboarding", include_in_schema=False)
def cancel_onboarding(
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Hủy tiến trình Onboarding:
    - Nếu user mới đang ở trạng thái 'PENDING' (chưa chọn vai trò), xóa bản ghi khỏi DB để không lưu tài khoản rác.
    - Xóa các RefreshToken liên quan của user.
    """
    user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if user and user.role == "PENDING":
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user.id).delete()
        db.delete(user)
        db.commit()
        return {"success": True, "message": "Đã hủy phiên onboarding và dọn dẹp tài khoản tạm trong cơ sở dữ liệu."}
    return {"success": True, "message": "Tài khoản đã hoàn tất vai trò, không cần dọn dẹp."}


# ==============================================================================
# US 9.1 (T9.2 & T9.2b): Endpoints OTP xác thực Email Phụ huynh
# ==============================================================================

@router.post("/auth/request-otp", status_code=status.HTTP_200_OK)
def request_otp(
    payload: schemas.OtpRequestInput,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 9.1 - T9.2:
    Gửi mã OTP 6 chữ số qua email cho Phụ huynh xác thực.
    - Bảo vệ rate-limit: chỉ gửi lại sau {OTP_RATE_LIMIT_SECONDS}s.
    - Tự động hủy các mã OTP cũ còn hiệu lực trước khi tạo mã mới.
    """
    if payload.purpose not in VALID_OTP_PURPOSES:
        raise HTTPException(status_code=422, detail="Purpose không hợp lệ.")

    email = payload.email.lower().strip()

    # Kiểm tra email chưa được dùng bởi tài khoản khác (nếu đăng ký mới)
    if payload.purpose == "PARENT_REGISTER":
        conflict = (
            db.query(models.User)
            .filter(
                func.lower(models.User.email) == email,
                models.User.id != current_user["id"],
            )
            .first()
        )
        if conflict:
            if conflict.oauth_provider == "google" or conflict.google_id:
                raise HTTPException(
                    status_code=400,
                    detail="Email này đã được đăng nhập bằng tài khoản Google. Vui lòng sử dụng email khác hoặc đăng nhập bằng Google."
                )
            raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống. Vui lòng chọn email khác.")

    new_otp = _request_otp_internal(email=email, purpose=payload.purpose, db=db)
    _send_otp_email(to_email=email, otp_code=new_otp.otp_code, purpose=payload.purpose)

    return {
        "success": True,
        "message": f"Mã OTP đã được gửi đến {email}. Hiệu lực trong {OTP_EXPIRE_MINUTES} phút.",
        "rate_limit_seconds": OTP_RATE_LIMIT_SECONDS,
    }


# ────────────────────────────────────────────────────────────────────────────
# US 11.2 (Task #41): API Gửi mã OTP khôi phục mật khẩu Phụ huynh
# ────────────────────────────────────────────────────────────────────────────

@router.post("/auth/forgot-password/request-otp", status_code=status.HTTP_200_OK)
@router.post("/forgot-password/request-otp", status_code=status.HTTP_200_OK)
def request_forgot_password_otp(
    payload: schemas.ForgotPasswordOtpRequestInput,
    db: Session = Depends(get_db),
):
    """
    US 11.2 - API gửi mã OTP cho Phụ huynh quên mật khẩu:
    1. Kiểm tra tài khoản trong hệ thống. Nếu không tìm thấy -> 404.
    2. Chặn tài khoản Google (oauth_provider == 'google' hoặc không có hashed_password) -> 400.
    3. Phân tách vai trò: Nếu là tài khoản học sinh (STUDENT) -> 400 hướng dẫn sang luồng phụ huynh cấp mật khẩu.
    4. Áp dụng giới hạn 60s chống spam và sinh mã OTP 6 số ngẫu nhiên qua _request_otp_internal.
    5. Gửi email chứa mã OTP qua Brevo SMTP.
    """
    normalized_email = payload.email.lower().strip()

    # 1. Tra cứu người dùng theo email
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == normalized_email)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email này chưa được đăng ký trong hệ thống."
        )

    # 2. Chặn tài khoản đăng nhập bằng Google (AC3)
    is_google_account = (
        user.oauth_provider == "google"
        or getattr(user, "google_id", None) is not None
        or not user.hashed_password
    )
    if is_google_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản này dùng đăng nhập Google, vui lòng bấm nút 'Đăng nhập bằng Google' ngoài màn hình chính."
        )

    # 3. Phân tách vai trò: Học sinh không đặt lại mật khẩu bằng email
    if user.role == "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản học sinh không đặt lại mật khẩu bằng email. Vui lòng nhờ Phụ huynh cấp lại mật khẩu trong trang Giám sát."
        )

    # 4. Sinh OTP 6 số, áp dụng giới hạn 60s và hủy mã cũ
    new_otp = _request_otp_internal(
        email=normalized_email,
        purpose="PARENT_RESET_PASSWORD",
        db=db,
    )

    # 5. Gửi email OTP qua Brevo SMTP
    _send_otp_email(
        to_email=normalized_email,
        otp_code=new_otp.otp_code,
        purpose="PARENT_RESET_PASSWORD",
    )

    return {
        "success": True,
        "message": f"Mã OTP đã được gửi đến email {normalized_email}. Hiệu lực trong {OTP_EXPIRE_MINUTES} phút.",
        "email": normalized_email,
        "rate_limit_seconds": OTP_RATE_LIMIT_SECONDS,
    }


# ────────────────────────────────────────────────────────────────────────────
# US 11.2: Các hàm tiện ích cho Forgot Password & Mask Email
# ────────────────────────────────────────────────────────────────────────────

OTP_LOCKOUT_SECONDS = 900             # Khóa tạm 15 phút sau 5 lần nhập sai OTP (US 11.2 Note)
STUDENT_NOTIF_COOLDOWN_SECONDS = 60  # Cooldown 60s khi gửi thông báo tới phụ huynh


def mask_email(email: str | None) -> str:
    """
    Che mờ email theo chuẩn US 11.2 (ví dụ: ng***@gmail.com, a***@gmail.com).
    """
    if not email or "@" not in email:
        return email or ""
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 1:
        masked_local = f"{local_part}***"
    elif len(local_part) == 2:
        masked_local = f"{local_part[0]}***"
    else:
        masked_local = f"{local_part[:2]}***"
    return f"{masked_local}@{domain}"


async def _check_otp_lockout(email: str) -> None:
    """Kiểm tra tài khoản có đang bị khóa tạm thời 15 phút do nhập sai OTP 5 lần không."""
    lockout_key = f"auth:otp_lockout:{email}"
    try:
        redis_client = await get_redis()
        if redis_client:
            ttl = await redis_client.ttl(lockout_key)
            if ttl > 0:
                minutes_left = max(1, ttl // 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Tài khoản đang bị tạm khóa xác thực OTP do nhập sai quá 5 lần. Vui lòng thử lại sau {minutes_left} phút."
                )
    except HTTPException:
        raise
    except Exception:
        pass

    ram_ttl = _fallback_memory_limiter.get_lockout(lockout_key)
    if ram_ttl is not None and ram_ttl > 0:
        minutes_left = max(1, ram_ttl // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Tài khoản đang bị tạm khóa xác thực OTP do nhập sai quá 5 lần. Vui lòng thử lại sau {minutes_left} phút."
        )


async def _set_otp_lockout(email: str, duration_seconds: int = OTP_LOCKOUT_SECONDS) -> None:
    """Kích hoạt khóa tạm thời 15 phút khi nhập sai OTP đủ 5 lần."""
    lockout_key = f"auth:otp_lockout:{email}"
    try:
        redis_client = await get_redis()
        if redis_client:
            await redis_client.set(lockout_key, "1", ex=duration_seconds)
    except Exception:
        pass
    _fallback_memory_limiter.set_lockout(lockout_key, duration_seconds)


async def _clear_otp_lockout(email: str) -> None:
    """Xóa khóa tạm thời sau khi đổi mật khẩu thành công."""
    lockout_key = f"auth:otp_lockout:{email}"
    try:
        redis_client = await get_redis()
        if redis_client:
            await redis_client.delete(lockout_key)
    except Exception:
        pass
    _fallback_memory_limiter.clear_key(lockout_key)


# ────────────────────────────────────────────────────────────────────────────
# US 11.2 (Bug #414): API Xác thực OTP ở Bước 2 cho Phụ huynh
# ────────────────────────────────────────────────────────────────────────────

@router.post("/auth/forgot-password/verify-otp", response_model=schemas.ForgotPasswordVerifyOtpResponse)
@router.post("/forgot-password/verify-otp", response_model=schemas.ForgotPasswordVerifyOtpResponse)
async def forgot_password_verify_otp(
    payload: schemas.ForgotPasswordVerifyOtpInput,
    db: Session = Depends(get_db),
):
    """
    US 11.2 - API xác thực mã OTP ở Bước 2 trước khi chuyển sang bước đặt mật khẩu mới:
    1. Kiểm tra khóa chống brute-force (khóa tạm 15 phút sau 5 lần nhập sai).
    2. Tra cứu mã OTP còn hiệu lực cho PARENT_RESET_PASSWORD.
    3. Kiểm tra số lần thử sai (tối đa 5 lần thử; khóa 15 phút nếu >= 5 lần).
    4. Trả về thông báo thành công và số lần thử nếu sai.
    """
    normalized_email = payload.email.lower().strip()
    clean_otp = payload.otp_code.strip()

    if len(clean_otp) != 6 or not clean_otp.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP phải gồm đúng 6 chữ số."
        )

    # 1. Kiểm tra khóa chống brute-force 15 phút
    await _check_otp_lockout(normalized_email)

    # 2. Tìm mã OTP hợp lệ
    now = datetime.now(timezone.utc)
    otp_record = (
        db.query(models.EmailOtp)
        .filter(
            models.EmailOtp.email == normalized_email,
            models.EmailOtp.purpose == "PARENT_RESET_PASSWORD",
            models.EmailOtp.is_used.is_(False),
            models.EmailOtp.expires_at > now,
        )
        .order_by(models.EmailOtp.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu gửi lại mã mới."
        )

    # 3. Kiểm tra số lần nhập sai trên mã OTP này
    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        await _set_otp_lockout(normalized_email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã OTP đã bị khóa do nhập sai quá {OTP_MAX_ATTEMPTS} lần. Tài khoản bị tạm khóa 15 phút."
        )

    # 4. Xác thực mã OTP
    if otp_record.otp_code != clean_otp:
        otp_record.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        if remaining <= 0:
            otp_record.is_used = True
            db.commit()
            await _set_otp_lockout(normalized_email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã OTP đã bị khóa do nhập sai quá {OTP_MAX_ATTEMPTS} lần. Tài khoản bị tạm khóa 15 phút."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã OTP không đúng. Bạn còn {remaining} lần thử."
        )

    return schemas.ForgotPasswordVerifyOtpResponse(
        success=True,
        message="Mã OTP chính xác. Vui lòng thiết lập mật khẩu mới."
    )


# ────────────────────────────────────────────────────────────────────────────
# US 11.2 (Task 1): API Xác thực OTP & Đổi mật khẩu Phụ huynh
# ────────────────────────────────────────────────────────────────────────────

@router.post("/auth/forgot-password/verify-and-reset", response_model=schemas.ForgotPasswordResetResponse)
@router.post("/forgot-password/verify-and-reset", response_model=schemas.ForgotPasswordResetResponse)
async def forgot_password_verify_and_reset(
    payload: schemas.ForgotPasswordVerifyAndResetInput,
    db: Session = Depends(get_db),
):
    """
    US 11.2 - API xác thực OTP & Đổi mật khẩu cho Phụ huynh:
    1. Kiểm tra khóa chống brute-force (khóa tạm 15 phút sau 5 lần nhập sai).
    2. Kiểm tra email và tài khoản phụ huynh trong hệ thống.
    3. Chặn tài khoản Google (hướng dẫn dùng Google Auth).
    4. Kiểm tra OTP: tối đa 5 lần thử; băm bcrypt mật khẩu mới.
    5. Tăng session_version và thu hồi refresh token để đăng xuất các thiết bị cũ (AC4).
    """
    normalized_email = payload.email.lower().strip()

    # 1. Kiểm tra xem tài khoản có đang bị khóa 15 phút không
    await _check_otp_lockout(normalized_email)

    # 2. Tra cứu người dùng
    user = (
        db.query(models.User)
        .filter(func.lower(models.User.email) == normalized_email)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email này chưa được đăng ký trong hệ thống."
        )

    # 3. Chặn tài khoản Google (AC3)
    is_google_account = (
        user.oauth_provider == "google"
        or getattr(user, "google_id", None) is not None
        or not user.hashed_password
    )
    if is_google_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản này dùng đăng nhập Google, vui lòng bấm nút 'Đăng nhập bằng Google' ngoài màn hình chính."
        )

    # 4. Phân tách vai trò
    if user.role == "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản học sinh không đặt lại mật khẩu bằng email. Vui lòng nhờ Phụ huynh cấp lại mật khẩu trong trang Giám sát."
        )

    # 5. Kiểm tra mật khẩu mới
    new_password = payload.new_password.strip() if payload.new_password else ""
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có ít nhất 6 ký tự."
        )

    # 6. Tìm mã OTP hợp lệ
    now = datetime.now(timezone.utc)
    otp_record = (
        db.query(models.EmailOtp)
        .filter(
            models.EmailOtp.email == normalized_email,
            models.EmailOtp.purpose == "PARENT_RESET_PASSWORD",
            models.EmailOtp.is_used.is_(False),
            models.EmailOtp.expires_at > now,
        )
        .order_by(models.EmailOtp.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu gửi lại mã mới."
        )

    # 7. Kiểm tra số lần nhập sai trên mã OTP này
    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        await _set_otp_lockout(normalized_email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã OTP đã bị khóa do nhập sai quá {OTP_MAX_ATTEMPTS} lần. Tài khoản bị tạm khóa 15 phút."
        )

    # 8. Xác thực mã OTP
    if otp_record.otp_code != payload.otp_code.strip():
        otp_record.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        if remaining <= 0:
            otp_record.is_used = True
            db.commit()
            await _set_otp_lockout(normalized_email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã OTP đã bị khóa do nhập sai quá {OTP_MAX_ATTEMPTS} lần. Tài khoản bị tạm khóa 15 phút."
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã OTP không đúng. Bạn còn {remaining} lần thử."
        )

    # 9. Mã đúng: Đánh dấu đã dùng
    otp_record.is_used = True

    # 10. Băm mật khẩu mới bằng bcrypt và cập nhật user
    user.hashed_password = auth.hash_password(new_password)

    # 11. Tăng session_version để tự động đăng xuất các máy cũ (AC4)
    user.session_version = (user.session_version or 1) + 1

    # 12. Thu hồi toàn bộ refresh token cũ của user
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user.id,
        models.RefreshToken.revoked.is_(False)
    ).update({"revoked": True})

    db.commit()

    # 13. Xóa cờ khóa tạm (nếu có)
    await _clear_otp_lockout(normalized_email)

    return schemas.ForgotPasswordResetResponse(
        success=True,
        message="Đổi mật khẩu thành công. Các phiên đăng nhập trên thiết bị cũ đã được đăng xuất. Vui lòng đăng nhập lại bằng mật khẩu mới."
    )


# ────────────────────────────────────────────────────────────────────────────
# US 11.2 (Task 2): API Tra cứu học sinh & Gửi email thông báo cho Phụ huynh
# ────────────────────────────────────────────────────────────────────────────

@router.post("/auth/forgot-password/student-lookup", response_model=schemas.StudentLookupResponse)
@router.post("/forgot-password/student-lookup", response_model=schemas.StudentLookupResponse)
async def student_lookup_forgot_password(
    payload: schemas.StudentLookupInput,
    db: Session = Depends(get_db),
):
    """
    US 11.2 - API tra cứu học sinh & Gửi email thông báo phụ huynh:
    1. Học sinh nhập tên tài khoản -> tra cứu hệ thống.
    2. Tra cứu liên kết bảo trợ gia đình (parent_student_links).
    3. Trả về email phụ huynh che mờ (ví dụ: ng***@gmail.com, a***@gmail.com) theo AC5.
    4. Nếu send_notification=True -> gửi email thông báo nhắc nhở phụ huynh cấp mật khẩu kèm giới hạn 60s.
    """
    clean_username = payload.username.strip()
    if not clean_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập tên tài khoản học sinh."
        )

    # 1. Tra cứu tài khoản học sinh
    student = (
        db.query(models.User)
        .filter(func.lower(models.User.username) == clean_username.lower())
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản học sinh với tên đăng nhập này."
        )

    if student.role != "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên tài khoản này không thuộc về học sinh. Nếu bạn là Phụ huynh, vui lòng chọn tab 'Phụ huynh' để khôi phục mật khẩu bằng email."
        )

    # 2. Tra cứu liên kết bảo trợ gia đình
    link = (
        db.query(models.ParentStudentLink)
        .filter(models.ParentStudentLink.student_id == student.id)
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản học sinh này chưa được liên kết với tài khoản Phụ huynh nào. Bé hãy nhờ Bố/Mẹ vào tài khoản Phụ huynh để kết nối nhé."
        )

    # 3. Tra cứu thông tin phụ huynh bảo trợ
    parent = db.query(models.User).filter(models.User.id == link.parent_id).first()
    if not parent or not parent.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phụ huynh bảo trợ chưa cập nhật địa chỉ email nhận thông báo trong hệ thống."
        )

    masked_parent_email = mask_email(parent.email)

    # 4. Nếu chưa yêu cầu gửi email thông báo -> chỉ trả về thông tin tra cứu
    if not payload.send_notification:
        return schemas.StudentLookupResponse(
            success=True,
            student_username=student.username or clean_username,
            parent_email_masked=masked_parent_email,
            notification_sent=False,
            message="Đã tìm thấy tài khoản học sinh. Bạn có thể bấm 'Gửi thông báo tới Bố/Mẹ' để gửi email nhắc nhở."
        )

    # 5. Nếu yêu cầu gửi email thông báo -> kiểm tra giới hạn 60s chống spam
    cooldown_key = f"notif:student_reset:{student.id}"
    try:
        redis_client = await get_redis()
        if redis_client:
            ttl = await redis_client.ttl(cooldown_key)
            if ttl > 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Thông báo đã được gửi tới Phụ huynh cách đây ít phút. Vui lòng đợi {ttl} giây trước khi gửi lại."
                )
    except HTTPException:
        raise
    except Exception:
        pass

    ram_ttl = _fallback_memory_limiter.get_lockout(cooldown_key)
    if ram_ttl is not None and ram_ttl > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Thông báo đã được gửi tới Phụ huynh cách đây ít phút. Vui lòng đợi {ram_ttl} giây trước khi gửi lại."
        )

    # 6. Gửi email thông báo nhắc nhở phụ huynh qua Brevo SMTP
    subject = f"[SocraticKid] Bé {student.username} cần Bố/Mẹ cấp lại mật khẩu"
    text_content = (
        f"Kính gửi Quý phụ huynh,\n\n"
        f"Bé nhà mình có tài khoản là '{student.username}' vừa gửi yêu cầu hỗ trợ cấp lại mật khẩu đăng nhập trên nền tảng SocraticKid.\n\n"
        f"Để cấp lại mật khẩu cho con, Quý phụ huynh vui lòng thực hiện theo các bước sau:\n"
        f"1. Đăng nhập vào SocraticKid bằng tài khoản Phụ huynh ({parent.email}).\n"
        f"2. Truy cập trang Giám sát con (/dashboard/monitor).\n"
        f"3. Tại thẻ của bé '{student.username}', bấm nút '🔑 Cấp lại mật khẩu' để nhập mật khẩu mới cho con.\n\n"
        f"Sau khi lưu, bé có thể sử dụng mật khẩu mới này để đăng nhập ngay lập tức.\n"
        f"Nếu không phải bé nhà mình yêu cầu, Quý phụ huynh có thể bỏ qua thông báo này.\n\n"
        f"Trân trọng,\nĐội ngũ SocraticKid"
    )
    html_content = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; padding: 24px;">
        <h2 style="color: #2b6cb0; margin-top: 0;">SocraticKid - Nhắc Nhở Cấp Mật Khẩu Cho Con</h2>
        <p>Kính gửi Quý phụ huynh,</p>
        <p>Bé nhà mình với tên tài khoản <strong>{student.username}</strong> vừa gửi yêu cầu hỗ trợ cấp lại mật khẩu đăng nhập trên nền tảng <strong>SocraticKid</strong>.</p>
        <div style="background-color: #f7fafc; border-left: 4px solid #3182ce; padding: 12px 16px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-weight: bold; color: #2d3748;">Hướng dẫn cấp lại mật khẩu cho con:</p>
            <ol style="margin: 8px 0 0 0; padding-left: 20px;">
                <li>Đăng nhập tài khoản Phụ huynh trên SocraticKid.</li>
                <li>Truy cập trang <strong>Giám sát con</strong> (<code>/dashboard/monitor</code>).</li>
                <li>Tại thẻ của bé <strong>{student.username}</strong>, nhấn nút <strong>🔑 Cấp lại mật khẩu</strong>.</li>
                <li>Nhập mật khẩu mới và bấm Lưu để bé đăng nhập ngay lập tức.</li>
            </ol>
        </div>
        <p style="color: #718096; font-size: 13px;">Nếu không phải bé nhà mình yêu cầu, Quý phụ huynh có thể yên tâm bỏ qua email này.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="color: #a0aec0; font-size: 12px; margin: 0;">Email tự động từ hệ thống SocraticKid. Vui lòng không trả lời thư này.</p>
    </div>
    """

    send_email(
        to_email=parent.email,
        subject=subject,
        text_content=text_content,
        html_content=html_content,
        category="PARENT_RESET_NOTIFICATION"
    )

    # 7. Kích hoạt giới hạn cooldown 60s
    try:
        redis_client = await get_redis()
        if redis_client:
            await redis_client.set(cooldown_key, "1", ex=STUDENT_NOTIF_COOLDOWN_SECONDS)
    except Exception:
        pass
    _fallback_memory_limiter.set_lockout(cooldown_key, STUDENT_NOTIF_COOLDOWN_SECONDS)

    return schemas.StudentLookupResponse(
        success=True,
        student_username=student.username or clean_username,
        parent_email_masked=masked_parent_email,
        notification_sent=True,
        message=f"Đã gửi email thông báo nhắc nhở tới Bố/Mẹ ({masked_parent_email}). Bé hãy báo Bố/Mẹ kiểm tra hòm thư nhé!"
    )


# ────────────────────────────────────────────────────────────────────────────
# US 11.2 (Task 3): API Phụ huynh cấp lại mật khẩu cho con
# ────────────────────────────────────────────────────────────────────────────

@router.post("/parent/students/{student_id}/reset-password", response_model=schemas.ParentResetStudentPasswordResponse)
@router.post("/family/students/{student_id}/reset-password", response_model=schemas.ParentResetStudentPasswordResponse)
def parent_reset_student_password(
    student_id: str,
    payload: schemas.ParentResetStudentPasswordInput,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 11.2 - API Phụ huynh cấp lại mật khẩu cho con:
    1. Kiểm tra vai trò phụ huynh (MONITOR/PARENT) hoặc Quản trị viên (ADMIN).
    2. Kiểm tra quyền giám hộ chặt chẽ (AC7): Phụ huynh chỉ được đổi mật khẩu cho đúng con của mình qua parent_student_links.
    3. Cập nhật mật khẩu mới cho học sinh ngay lập tức (AC6).
    4. Tăng session_version và thu hồi refresh token của học sinh để bảo mật.
    """
    user_role = current_user.get("role")
    if user_role not in ["MONITOR", "PARENT", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ phụ huynh mới có quyền cấp lại mật khẩu cho học sinh."
        )

    # Kiểm tra quyền giám hộ chặt chẽ ngăn phụ huynh can thiệp tài khoản con nhà khác (AC7)
    if user_role != "ADMIN":
        link = (
            db.query(models.ParentStudentLink)
            .filter(
                models.ParentStudentLink.parent_id == current_user["id"],
                models.ParentStudentLink.student_id == student_id
            )
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền quản lý hoặc đổi mật khẩu cho học sinh này."
            )

    # Tra cứu học sinh
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tài khoản học sinh."
        )

    if student.role != "STUDENT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản đích không phải là tài khoản học sinh."
        )

    # Kiểm tra mật khẩu mới
    new_password = payload.new_password.strip() if payload.new_password else ""
    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu mới phải có ít nhất 6 ký tự."
        )

    # Cập nhật mật khẩu băm bcrypt
    student.hashed_password = auth.hash_password(new_password)

    # Tăng session_version của học sinh để tự động vô hiệu hóa phiên cũ
    student.session_version = (student.session_version or 1) + 1

    # Thu hồi refresh tokens cũ của học sinh
    db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == student.id,
        models.RefreshToken.revoked.is_(False)
    ).update({"revoked": True})

    db.commit()

    return schemas.ParentResetStudentPasswordResponse(
        success=True,
        message=f"Cấp lại mật khẩu cho học sinh '{student.username or student.id}' thành công. Học sinh có thể dùng mật khẩu mới đăng nhập ngay lập tức.",
        student_id=student.id,
        student_username=student.username,
    )


@router.post("/auth/verify-otp", response_model=schemas.OtpVerifyResponse)
def verify_otp(
    payload: schemas.OtpVerifyInput,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 9.1 - T9.2:
    Xác thực mã OTP người dùng nhập vào.
    - Kiểm tra mã còn hiệu lực và chưa hết hạn.
    - Tăng biến attempts mỗi lần nhập sai; khóa sau {OTP_MAX_ATTEMPTS} lần.
    - Khi xác thực thành công: cập nhật email + email_verified=True cho user.
    """
    if payload.purpose not in VALID_OTP_PURPOSES:
        raise HTTPException(status_code=422, detail="Purpose không hợp lệ.")

    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)

    # Tìm mã OTP hợp lệ (chưa dùng, chưa hết hạn, đúng email+purpose)
    otp_record = (
        db.query(models.EmailOtp)
        .filter(
            models.EmailOtp.email == email,
            models.EmailOtp.purpose == payload.purpose,
            models.EmailOtp.is_used.is_(False),
            models.EmailOtp.expires_at > now,
        )
        .order_by(models.EmailOtp.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu gửi lại mã mới."
        )

    # Kiểm tra số lần nhập sai
    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Mã OTP đã bị khóa do nhập sai quá {OTP_MAX_ATTEMPTS} lần. Vui lòng yêu cầu mã mới."
        )

    # Kiểm tra mã có đúng không
    if otp_record.otp_code != payload.otp_code.strip():
        otp_record.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Mã OTP không đúng. Bạn còn {remaining} lần thử."
        )

    # ✔ Mã đúng: đánh dấu đã dùng và cập nhật email cho user
    otp_record.is_used = True

    user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if user:
        # Kiểm tra conflict email trước khi gán
        conflict = (
            db.query(models.User)
            .filter(
                func.lower(models.User.email) == email,
                models.User.id != user.id,
            )
            .first()
        )
        if conflict:
            if conflict.oauth_provider == "google" or conflict.google_id:
                raise HTTPException(
                    status_code=400,
                    detail="Email này đã được đăng nhập bằng tài khoản Google. Vui lòng sử dụng email khác hoặc đăng nhập bằng Google."
                )
            raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống. Vui lòng chọn email khác.")

        user.email = email
        user.email_verified = True
    db.commit()

    return schemas.OtpVerifyResponse(
        success=True,
        message="Xác thực OTP thành công! Email đã được liên kết vào tài khoản."
    )


# ==============================================================================
# US 9.1 (T9.5): Endpoints đổi email Phụ huynh ở trang Cài đặt
# ==============================================================================

@router.post("/parent/settings/request-email-otp", status_code=status.HTTP_200_OK)
def parent_request_email_otp(
    payload: schemas.ParentChangeEmailRequest,
    current_user: dict = Depends(dependencies.require_role(["MONITOR"])),
    db: Session = Depends(get_db),
):
    """
    US 9.1 - T9.5:
    Bước 1: Phụ huynh yêu cầu gửi OTP tới email mới muốn đổi.
    - Chỉ MONITOR mới được gọi endpoint này.
    - Tài khoản đăng nhập bằng Google OAuth cố định email, không được đổi.
    - Kiểm tra email mới chưa ai dùng (đặc biệt không được dùng email đã đăng nhập Google).
    - Rate-limit và hủy mã cũ được xử lý tự động.
    """
    # Nếu tài khoản là Google OAuth -> từ chối đổi email
    current_db_user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if current_db_user and (current_db_user.oauth_provider == "google" or current_db_user.google_id):
        raise HTTPException(
            status_code=400,
            detail="Tài khoản Google OAuth không thể thay đổi email thông báo. Email thông báo luôn là email Google của bạn."
        )

    new_email = payload.new_email.lower().strip()

    # Kiểm tra email mới chưa được dùng bởi tài khoản khác (bao gồm cả tài khoản Google)
    conflict = (
        db.query(models.User)
        .filter(
            func.lower(models.User.email) == new_email,
            models.User.id != current_user["id"],
        )
        .first()
    )
    if conflict:
        if conflict.oauth_provider == "google" or conflict.google_id:
            raise HTTPException(
                status_code=400,
                detail="Email này đã được đăng nhập bằng tài khoản Google. Vui lòng sử dụng email khác."
            )
        raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống. Vui lòng chọn email khác.")

    new_otp = _request_otp_internal(email=new_email, purpose="PARENT_CHANGE_EMAIL", db=db)
    _send_otp_email(to_email=new_email, otp_code=new_otp.otp_code, purpose="PARENT_CHANGE_EMAIL")

    return {
        "success": True,
        "message": f"Mã OTP đã được gửi đến {new_email}. Vui lòng kiểm tra hộp thư.",
        "rate_limit_seconds": OTP_RATE_LIMIT_SECONDS,
    }


@router.post("/parent/settings/verify-email-otp", response_model=schemas.OtpVerifyResponse)
def parent_verify_email_otp(
    payload: schemas.ParentChangeEmailVerify,
    current_user: dict = Depends(dependencies.require_role(["MONITOR"])),
    db: Session = Depends(get_db),
):
    """
    US 9.1 - T9.5:
    Bước 2: Phụ huynh nhập OTP xác nhận đổi email mới thành công.
    - Chỉ MONITOR mới được gọi endpoint này.
    - Kiểm tra OTP hợp lệ, đúng purpose, chưa hết hạn, chưa vượt max attempts.
    - Khi đúng: cập nhận email mới và email_verified=True.
    """
    new_email = payload.new_email.lower().strip()
    now = datetime.now(timezone.utc)

    user = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")

    if user.oauth_provider == "google" or user.google_id:
        raise HTTPException(
            status_code=400,
            detail="Tài khoản Google OAuth không thể thay đổi email thông báo."
        )

    # Kiểm tra conflict email trước khi đổi
    conflict = (
        db.query(models.User)
        .filter(
            func.lower(models.User.email) == new_email,
            models.User.id != user.id,
        )
        .first()
    )
    if conflict:
        if conflict.oauth_provider == "google" or conflict.google_id:
            raise HTTPException(
                status_code=400,
                detail="Email này đã được đăng nhập bằng tài khoản Google. Vui lòng sử dụng email khác."
            )
        raise HTTPException(status_code=400, detail="Email này đã tồn tại trong hệ thống. Vui lòng chọn email khác.")

    otp_record = (
        db.query(models.EmailOtp)
        .filter(
            models.EmailOtp.email == new_email,
            models.EmailOtp.purpose == "PARENT_CHANGE_EMAIL",
            models.EmailOtp.is_used.is_(False),
            models.EmailOtp.expires_at > now,
        )
        .order_by(models.EmailOtp.created_at.desc())
        .first()
    )

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Mã OTP không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu gửi lại mã mới."
        )

    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Mã OTP đã bị khóa do nhập sai quá {OTP_MAX_ATTEMPTS} lần. Vui lòng yêu cầu mã mới."
        )

    if otp_record.otp_code != payload.otp_code.strip():
        otp_record.attempts += 1
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - otp_record.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Mã OTP không đúng. Bạn còn {remaining} lần thử."
        )

    # ✔ Mã đúng: cập nhật email mới và đánh dấu đã xác thực
    otp_record.is_used = True
    user.email = new_email
    user.email_verified = True
    db.commit()

    return schemas.OtpVerifyResponse(
        success=True,
        message="Cập nhật email mới thành công! Email đã được xác thực."
    )
