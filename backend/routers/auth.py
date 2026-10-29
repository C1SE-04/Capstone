import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.security import OAuth2PasswordRequestForm

import models, schemas, auth, dependencies
from database import get_db

router = APIRouter(tags=["Auth"])

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    """
    Đăng ký tài khoản mới bằng Email/Password đồng bộ với luồng Onboarding:
    - Tạo tài khoản ban đầu với role='PENDING' (chưa chọn vai trò và khối lớp).
    - Sau khi đăng ký xong, Frontend sẽ đưa người dùng sang /onboarding để chọn vai trò
      giống hệt luồng Google Login, đảm bảo giao diện đồng bộ 100%.
    """
    normalized_email = user_data.email.lower().strip()
    existing_user = db.query(models.User).filter(func.lower(models.User.email) == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    new_user = models.User(
        email=normalized_email,
        hashed_password=auth.hash_password(user_data.password),
        role="PENDING",
        grade=None,
        session_version=1,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/register/student", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    normalized_email = user_data.email.lower()
    existing_user = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

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
    normalized_email = user_data.email.lower()
    existing_user = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Chuẩn hóa email về chữ thường trước khi tra cứu DB — cho phép đăng nhập với mọi kiểu viết hoa
    normalized_username = form_data.username.lower()
    user = (
        db.query(models.User).filter(
            func.lower(models.User.email) == normalized_username
        ).first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng"
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
            "role": user.role,
            "grade_level": user.grade,
            "session_version": user_version,
        }
    )
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer",
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

        user = models.User(
            id=uuid.uuid4().hex,
            email=normalized_email,
            google_id=resolved_google_id,
            oauth_provider="google",
            hashed_password=None,
            role=initial_role,
            grade=initial_grade,
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


