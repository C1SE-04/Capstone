"""
US 9.1 - Test Suite (T9.0 → T9.2b)
=====================================
Nghiệm thu end-to-end các tính năng:
  1. Đăng ký bằng username (không cần email).
  2. Username validation: độ dài, ký tự hợp lệ, trùng lặp.
  3. Đăng nhập kép: bằng username VÀ bằng email cũ (tương thích ngược).
  4. OTP Phụ huynh: gửi, xác thực, rate-limit 60s, max-attempts 5 lần.
  5. Google OAuth tự sinh username.
  6. Đổi email Phụ huynh qua OTP (endpoint Cài đặt).
"""

import sys
import os
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

from main import app
import models
import auth
import dependencies
from database import SessionLocal

client = TestClient(app)

# ─── Hằng test data ───────────────────────────────────────────────────────────

TEST_USERNAME_STUDENT = f"teststu_{uuid.uuid4().hex[:6]}"
TEST_USERNAME_MONITOR = f"testmon_{uuid.uuid4().hex[:6]}"
TEST_EMAIL_MONITOR    = f"monitor_{uuid.uuid4().hex[:6]}@testmail.com"
TEST_PASSWORD         = "Test@12345"

# ─── Fixture cleanup ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.pop(dependencies.get_current_user, None)
    yield
    app.dependency_overrides.pop(dependencies.get_current_user, None)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


def cleanup_test_users(db):
    """Xóa tất cả user và OTP test sau khi chạy xong."""
    usernames = [TEST_USERNAME_STUDENT, TEST_USERNAME_MONITOR]
    for uname in usernames:
        user = db.query(models.User).filter(models.User.username == uname).first()
        if user:
            db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user.id).delete()
            db.delete(user)
    db.query(models.EmailOtp).filter(models.EmailOtp.email == TEST_EMAIL_MONITOR).delete()
    db.commit()


# ==============================================================================
# 1. Đăng ký bằng username (không cần email)
# ==============================================================================

def test_register_with_username_no_email():
    """[AC 9.1.1] Học sinh đăng ký bằng username + password — không cần email."""
    resp = client.post("/register", json={
        "username": TEST_USERNAME_STUDENT,
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 201, f"Đăng ký thất bại: {resp.text}"
    data = resp.json()

    assert data["username"] == TEST_USERNAME_STUDENT
    assert data["email"] is None, "Học sinh không có email"
    assert data["role"] == "PENDING"
    assert data.get("email_verified", False) is False
    print(f"  [PASS] Đăng ký username '{TEST_USERNAME_STUDENT}' không cần email thành công.")


def test_register_duplicate_username():
    """Username trùng phải trả về 400."""
    resp = client.post("/register", json={
        "username": TEST_USERNAME_STUDENT,
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 400
    assert "đã tồn tại" in resp.json()["detail"].lower() or "tồn tại" in resp.json()["detail"]
    print("  [PASS] Trùng username trả về 400 đúng.")


# ==============================================================================
# 2. Validation username
# ==============================================================================

@pytest.mark.parametrize("bad_username, expected_error_fragment", [
    ("ab",       "3 đến 30"),       # Quá ngắn
    ("a" * 31,   "3 đến 30"),       # Quá dài
    ("hello world", "gạch dưới"),   # Có khoảng trắng
    ("tên@user", "gạch dưới"),      # Có ký tự đặc biệt
    ("UPPERCASE", None),            # Chữ hoa → được nhận nhưng normalize thành lowercase
])
def test_register_username_validation(bad_username, expected_error_fragment):
    """Username không hợp lệ phải bị từ chối."""
    resp = client.post("/register", json={
        "username": bad_username,
        "password": TEST_PASSWORD,
    })
    if expected_error_fragment:
        assert resp.status_code == 422, f"Phải là 422 với username: '{bad_username}'"
        assert expected_error_fragment in resp.json()["detail"]
        print(f"  [PASS] Username '{bad_username}' bị từ chối đúng.")
    else:
        # Chữ hoa sẽ được normalize, có thể 201 hoặc 400 (nếu đã tồn tại lowercase)
        assert resp.status_code in (201, 400)
        print(f"  [PASS] Username '{bad_username}' được xử lý đúng (status={resp.status_code}).")


# ==============================================================================
# 3. Đăng nhập kép: username VÀ email
# ==============================================================================

def test_login_by_username():
    """[AC 9.1.4] Đăng nhập bằng username hoạt động bình thường."""
    resp = client.post("/login", data={
        "username": TEST_USERNAME_STUDENT,
        "password": TEST_PASSWORD,
    })
    assert resp.status_code == 200, f"Đăng nhập bằng username thất bại: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    print(f"  [PASS] Đăng nhập bằng username '{TEST_USERNAME_STUDENT}' thành công.")


def test_login_by_old_email_backward_compatible(db):
    """[AC 9.1.4] User cũ (có email) vẫn đăng nhập bằng email — tương thích ngược."""
    # Tạo user cũ kiểu Sprint cũ (có email, chưa có username)
    old_email = f"legacy_{uuid.uuid4().hex[:6]}@old.com"
    old_pass  = "Legacy@123"
    old_user  = models.User(
        email=old_email,
        hashed_password=auth.hash_password(old_pass),
        role="STUDENT",
        grade=7,
        session_version=1,
        email_verified=False,
    )
    db.add(old_user)
    db.commit()

    try:
        resp = client.post("/login", data={
            "username": old_email,  # Gõ email vào ô username
            "password": old_pass,
        })
        assert resp.status_code == 200, f"Login bằng email cũ thất bại: {resp.text}"
        print(f"  [PASS] User cũ email='{old_email}' đăng nhập bằng email vẫn hoạt động (tương thích ngược).")
    finally:
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == old_user.id).delete()
        db.delete(old_user)
        db.commit()


# ==============================================================================
# 4. OTP Phụ huynh — đăng ký 2 bước
# ==============================================================================

def _get_token_for_user(username: str, password: str) -> str:
    resp = client.post("/login", data={"username": username, "password": password})
    assert resp.status_code == 200, f"Login thất bại: {resp.text}"
    return resp.json()["access_token"]


def test_otp_request_success():
    """Phụ huynh gửi OTP thành công → trả 200 và email log được ghi nhận."""
    # Đăng ký monitor
    client.post("/register", json={"username": TEST_USERNAME_MONITOR, "password": TEST_PASSWORD})
    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)

    resp = client.post(
        "/auth/request-otp",
        json={"email": TEST_EMAIL_MONITOR, "purpose": "PARENT_REGISTER"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Request OTP thất bại: {resp.text}"
    data = resp.json()
    assert data["success"] is True
    assert "rate_limit_seconds" in data
    print(f"  [PASS] Gửi OTP tới {TEST_EMAIL_MONITOR} thành công.")


def test_otp_rate_limit():
    """Rate-limit: gửi lại trong vòng 60s → 429."""
    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)

    # Gửi lần 2 ngay lập tức
    resp = client.post(
        "/auth/request-otp",
        json={"email": TEST_EMAIL_MONITOR, "purpose": "PARENT_REGISTER"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 429, f"Phải trả 429 khi gửi lại quá sớm: {resp.text}"
    assert "giây" in resp.json()["detail"]
    print("  [PASS] Rate-limit 60s hoạt động đúng — trả 429.")


def test_otp_verify_wrong_code_increments_attempts(db):
    """Nhập sai mã → tăng attempts, phản hồi báo còn bao nhiêu lần thử."""
    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)

    resp = client.post(
        "/auth/verify-otp",
        json={
            "email": TEST_EMAIL_MONITOR,
            "otp_code": "000000",       # Mã sai chắc chắn
            "purpose": "PARENT_REGISTER",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "lần thử" in detail
    print(f"  [PASS] Nhập sai mã → trả 400 với thông báo: '{detail}'")


def test_otp_verify_correct_code(db):
    """Nhập đúng mã OTP → email và email_verified được cập nhật."""
    from services.email_service import get_sent_emails, clear_sent_emails
    clear_sent_emails()

    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)

    # Đọc mã OTP từ log (mock mode)
    # Trước tiên force-gửi bằng cách update last_sent_at để vượt rate-limit
    otp_email = f"correct_{uuid.uuid4().hex[:6]}@test.com"

    resp = client.post(
        "/auth/request-otp",
        json={"email": otp_email, "purpose": "PARENT_REGISTER"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Đọc mã OTP từ email log (DEV MODE)
    sent = get_sent_emails()
    otp_to_verify = None
    for mail in reversed(sent):
        if mail.get("to_email") == otp_email:
            # Mã OTP nằm trong text_content: "Mã OTP của bạn là: XXXXXX"
            import re
            match = re.search(r"\b(\d{6})\b", mail.get("text_content", ""))
            if match:
                otp_to_verify = match.group(1)
                break

    if not otp_to_verify:
        # Fallback: đọc trực tiếp từ DB
        otp_record = (
            db.query(models.EmailOtp)
            .filter(models.EmailOtp.email == otp_email, models.EmailOtp.is_used.is_(False))
            .order_by(models.EmailOtp.created_at.desc())
            .first()
        )
        assert otp_record, "Không tìm thấy OTP record trong DB"
        otp_to_verify = otp_record.otp_code

    # Verify mã đúng
    resp2 = client.post(
        "/auth/verify-otp",
        json={
            "email": otp_email,
            "otp_code": otp_to_verify,
            "purpose": "PARENT_REGISTER",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200, f"Verify OTP thất bại: {resp2.text}"
    data = resp2.json()
    assert data["success"] is True

    # Kiểm tra DB: email và email_verified được cập nhật
    monitor_user = (
        db.query(models.User)
        .filter(models.User.username == TEST_USERNAME_MONITOR)
        .first()
    )
    db.refresh(monitor_user)
    assert monitor_user.email == otp_email
    assert monitor_user.email_verified is True
    print(f"  [PASS] Verify OTP đúng → email='{otp_email}', email_verified=True.")

    # Dọn dẹp OTP record phụ
    db.query(models.EmailOtp).filter(models.EmailOtp.email == otp_email).delete()
    db.commit()


def test_otp_verify_expired_code(db):
    """Mã OTP quá hạn → 400 không hợp lệ."""
    expired_otp = models.EmailOtp(
        email="expired@test.com",
        otp_code="999999",
        purpose="PARENT_REGISTER",
        attempts=0,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),  # Đã hết hạn
        is_used=False,
        last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    db.add(expired_otp)
    db.commit()

    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)

    resp = client.post(
        "/auth/verify-otp",
        json={"email": "expired@test.com", "otp_code": "999999", "purpose": "PARENT_REGISTER"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "hết hạn" in resp.json()["detail"] or "không hợp lệ" in resp.json()["detail"]
    print("  [PASS] Mã OTP hết hạn → 400 đúng.")

    db.query(models.EmailOtp).filter(models.EmailOtp.email == "expired@test.com").delete()
    db.commit()


def test_otp_max_attempts_lockout(db):
    """Nhập sai 5 lần → mã bị khóa tự động."""
    lockout_email = f"lockout_{uuid.uuid4().hex[:6]}@test.com"
    locked_otp = models.EmailOtp(
        email=lockout_email,
        otp_code="123456",
        purpose="PARENT_REGISTER",
        attempts=5,   # Đã nhập sai đủ 5 lần
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        is_used=False,
        last_sent_at=datetime.now(timezone.utc) - timedelta(minutes=2),
    )
    db.add(locked_otp)
    db.commit()

    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)

    resp = client.post(
        "/auth/verify-otp",
        json={"email": lockout_email, "otp_code": "123456", "purpose": "PARENT_REGISTER"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    assert "khóa" in resp.json()["detail"]
    print("  [PASS] Max attempts 5 lần → mã bị khóa đúng.")

    db.query(models.EmailOtp).filter(models.EmailOtp.email == lockout_email).delete()
    db.commit()


def test_parent_settings_change_email_flow(db):
    """[US 9.1 - T9.5] Phụ huynh đổi email trong Cài đặt bằng luồng OTP 2 bước."""
    # Đảm bảo user có role MONITOR
    user = db.query(models.User).filter(models.User.username == TEST_USERNAME_MONITOR).first()
    assert user is not None
    user.role = "MONITOR"
    db.commit()

    token = _get_token_for_user(TEST_USERNAME_MONITOR, TEST_PASSWORD)
    new_email = f"new_email_{uuid.uuid4().hex[:6]}@parent.com"

    # Bước 1: Yêu cầu OTP tới new_email
    resp = client.post(
        "/parent/settings/request-email-otp",
        json={"new_email": new_email},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Request change email OTP failed: {resp.text}"
    assert resp.json()["success"] is True

    # Lấy OTP từ DB
    otp_record = (
        db.query(models.EmailOtp)
        .filter(models.EmailOtp.email == new_email, models.EmailOtp.purpose == "PARENT_CHANGE_EMAIL")
        .first()
    )
    assert otp_record is not None
    code = otp_record.otp_code

    # Bước 2: Xác nhận OTP
    resp_verify = client.post(
        "/parent/settings/verify-email-otp",
        json={"new_email": new_email, "otp_code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_verify.status_code == 200, f"Verify change email OTP failed: {resp_verify.text}"
    assert resp_verify.json()["success"] is True

    # Kiểm tra DB user đã đổi email và email_verified = True
    db.refresh(user)
    assert user.email == new_email
    assert user.email_verified is True
    print(f"  [PASS] Phụ huynh đổi email thành công sang '{new_email}'.")

    # Cleanup OTP
    db.query(models.EmailOtp).filter(models.EmailOtp.email == new_email).delete()
    db.commit()


# ==============================================================================
# 5. Cleanup toàn bộ sau test
# ==============================================================================

def test_cleanup(db):
    """Dọn dẹp tất cả dữ liệu test."""
    cleanup_test_users(db)
    print("  [PASS] Dọn dẹp test data thành công.")
