"""
Test Suite: Merge Notification Email & Google Email Uniqueness Checks
======================================================================
Kiểm thử nghiệm thu theo quyết định hệ thống:
1. Xóa cột notification_email ở bảng users (chỉ dùng cột email duy nhất).
2. Email thông báo và email Google gộp chung vô cột email.
3. Nếu email đã được đăng nhập bằng tài khoản Google:
   - Không cho phép đăng ký / liên kết bằng tên đăng nhập & mật khẩu (qua Onboarding OTP hoặc register).
   - Không cho phép đổi email thông báo bên trong trang cài đặt thành email đã đăng nhập Google.
4. Bản thân tài khoản Google không được đổi email trong trang cài đặt.
5. Cho phép đổi sang email mới hợp lệ (chưa ai dùng).
"""

import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from main import app
from database import SessionLocal, engine
import models
import auth

client = TestClient(app)

GOOGLE_USER_ID = f"google_user_{uuid.uuid4().hex[:8]}"
GOOGLE_EMAIL = f"google_vip_{uuid.uuid4().hex[:6]}@gmail.com"
GOOGLE_SUB = f"gid_{uuid.uuid4().hex[:10]}"

NORMAL_USER_ID = f"normal_user_{uuid.uuid4().hex[:8]}"
NORMAL_USERNAME = f"normal_parent_{uuid.uuid4().hex[:6]}"
NORMAL_EMAIL = f"normal_parent_{uuid.uuid4().hex[:6]}@gmail.com"


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    db: Session = SessionLocal()
    try:
        # 1. Tạo một tài khoản Phụ huynh đăng nhập bằng Google OAuth
        google_user = models.User(
            id=GOOGLE_USER_ID,
            username=f"google_{uuid.uuid4().hex[:6]}",
            email=GOOGLE_EMAIL,
            google_id=GOOGLE_SUB,
            oauth_provider="google",
            hashed_password=None,
            role="MONITOR",
            email_verified=True,
        )

        # 2. Tạo một tài khoản Phụ huynh đăng nhập bằng Mật khẩu thông thường
        normal_user = models.User(
            id=NORMAL_USER_ID,
            username=NORMAL_USERNAME,
            email=NORMAL_EMAIL,
            google_id=None,
            oauth_provider=None,
            hashed_password=auth.hash_password("Password123!"),
            role="MONITOR",
            email_verified=True,
        )

        db.add_all([google_user, normal_user])
        db.commit()

        yield
    finally:
        db.query(models.EmailOtp).filter(models.EmailOtp.email.in_([GOOGLE_EMAIL, NORMAL_EMAIL])).delete()
        db.query(models.User).filter(models.User.id.in_([GOOGLE_USER_ID, NORMAL_USER_ID])).delete()
        db.commit()
        db.close()


def test_01_notification_email_column_does_not_exist():
    """1. Xác minh cột notification_email đã bị xóa hoàn toàn khỏi bảng users và model models.User."""
    # Kiểm tra model SQLAlchemy
    assert not hasattr(models.User, "notification_email"), "models.User không được chứa thuộc tính notification_email"

    # Kiểm tra bảng trong DB
    with engine.connect() as conn:
        insp = inspect(conn)
        columns = [c["name"] for c in insp.get_columns("users")]
        assert "notification_email" not in columns, "Bảng users trong DB không được có cột notification_email"


def test_02_get_user_profile_returns_merged_email():
    """2. GET /users/me trả về email và notification_email trỏ về cùng giá trị email duy nhất."""
    token = auth.create_access_token({"sub": GOOGLE_USER_ID, "role": "MONITOR"})
    res = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == GOOGLE_EMAIL
    assert data["notification_email"] == GOOGLE_EMAIL


def test_03_cannot_request_otp_using_existing_google_email():
    """
    3. Đăng ký tài khoản mới bằng mật khẩu, khi Onboarding nhập email đã có tài khoản Google:
    POST /auth/request-otp PHẢI bị từ chối 400.
    """
    # Giả lập user mới đang ở trạng thái PENDING
    pending_id = f"pending_user_{uuid.uuid4().hex[:6]}"
    pending_token = auth.create_access_token({"sub": pending_id, "role": "PENDING"})

    res = client.post(
        "/auth/request-otp",
        headers={"Authorization": f"Bearer {pending_token}"},
        json={
            "email": GOOGLE_EMAIL,
            "purpose": "PARENT_REGISTER",
        },
    )
    assert res.status_code == 400
    data = res.json()
    assert "tài khoản Google" in data["detail"] or "đã tồn tại" in data["detail"]


def test_04_cannot_verify_otp_using_existing_google_email():
    """3b. POST /auth/verify-otp PHẢI chặn nếu email đã thuộc tài khoản Google."""
    pending_id = f"pending_user_{uuid.uuid4().hex[:6]}"
    db: Session = SessionLocal()
    try:
        pending_user = models.User(
            id=pending_id,
            username=f"pending_{uuid.uuid4().hex[:4]}",
            email=None,
            hashed_password=auth.hash_password("Password123!"),
            role="PENDING",
            email_verified=False,
        )
        # Giả sử có mã OTP tồn tại cho email Google
        otp = models.EmailOtp(
            id=uuid.uuid4().hex,
            email=GOOGLE_EMAIL,
            otp_code="999888",
            purpose="PARENT_REGISTER",
            attempts=0,
            expires_at=datetime.now(timezone.utc).replace(year=2030),
            is_used=False,
        )
        db.add_all([pending_user, otp])
        db.commit()

        token = auth.create_access_token({"sub": pending_id, "role": "PENDING"})
        res = client.post(
            "/auth/verify-otp",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": GOOGLE_EMAIL,
                "otp_code": "999888",
                "purpose": "PARENT_REGISTER",
            },
        )
        assert res.status_code == 400
        assert "tài khoản Google" in res.json()["detail"] or "đã tồn tại" in res.json()["detail"]
    finally:
        db.query(models.EmailOtp).filter(models.EmailOtp.email == GOOGLE_EMAIL).delete()
        db.query(models.User).filter(models.User.id == pending_id).delete()
        db.commit()
        db.close()


def test_05_cannot_change_notification_email_to_google_email_in_settings():
    """
    4. Phụ huynh thông thường đổi email thông báo trong cài đặt sang email đã đăng nhập Google:
    POST /parent/settings/request-email-otp và PATCH /users/me/notification-email PHẢI bị từ chối 400.
    """
    normal_token = auth.create_access_token({"sub": NORMAL_USER_ID, "role": "MONITOR"})

    # Flow 1: Qua OTP
    res_otp = client.post(
        "/parent/settings/request-email-otp",
        headers={"Authorization": f"Bearer {normal_token}"},
        json={"new_email": GOOGLE_EMAIL},
    )
    assert res_otp.status_code == 400
    assert "tài khoản Google" in res_otp.json()["detail"] or "đã tồn tại" in res_otp.json()["detail"]

    # Flow 2: Qua PATCH /users/me/notification-email
    res_patch = client.patch(
        "/users/me/notification-email",
        headers={"Authorization": f"Bearer {normal_token}"},
        json={"notification_email": GOOGLE_EMAIL},
    )
    assert res_patch.status_code == 400
    assert "tài khoản Google" in res_patch.json()["detail"] or "đã tồn tại" in res_patch.json()["detail"]


def test_06_google_account_itself_cannot_change_email():
    """4b. Bản thân tài khoản Google không được phép thay đổi email trong cài đặt."""
    google_token = auth.create_access_token({"sub": GOOGLE_USER_ID, "role": "MONITOR"})
    fresh_email = f"another_{uuid.uuid4().hex[:6]}@gmail.com"

    res_otp = client.post(
        "/parent/settings/request-email-otp",
        headers={"Authorization": f"Bearer {google_token}"},
        json={"new_email": fresh_email},
    )
    assert res_otp.status_code == 400
    assert "Google" in res_otp.json()["detail"]

    res_patch = client.patch(
        "/users/me/notification-email",
        headers={"Authorization": f"Bearer {google_token}"},
        json={"notification_email": fresh_email},
    )
    assert res_patch.status_code == 400
    assert "Google" in res_patch.json()["detail"]


def test_07_normal_user_can_change_to_unused_email():
    """5. Phụ huynh mật khẩu đổi sang một email mới toanh (chưa ai dùng) thành công và cập nhật vào cột email."""
    normal_token = auth.create_access_token({"sub": NORMAL_USER_ID, "role": "MONITOR"})
    new_free_email = f"free_parent_{uuid.uuid4().hex[:6]}@gmail.com"

    res_patch = client.patch(
        "/users/me/notification-email",
        headers={"Authorization": f"Bearer {normal_token}"},
        json={"notification_email": new_free_email},
    )
    assert res_patch.status_code == 200
    data = res_patch.json()
    assert data["email"] == new_free_email
    assert data["notification_email"] == new_free_email

    # Kiểm tra trong DB
    db: Session = SessionLocal()
    try:
        user_db = db.query(models.User).filter(models.User.id == NORMAL_USER_ID).first()
        assert user_db.email == new_free_email
    finally:
        db.close()


def test_08_student_onboarding_without_email_succeeds_without_500():
    """
    6. Học sinh đăng ký bằng username/password (email=None) hoàn tất Onboarding:
    POST /auth/onboarding với role='STUDENT' và grade=7 PHẢI trả về 200 OK
    (không bị lỗi 500 Internal Server Error do schema GoogleAuthResponse đòi email non-null).
    """
    db: Session = SessionLocal()
    student_id = f"stu_no_email_{uuid.uuid4().hex[:6]}"
    student_username = f"stu_user_{uuid.uuid4().hex[:6]}"

    try:
        user = models.User(
            id=student_id,
            username=student_username,
            email=None,
            hashed_password=auth.hash_password("Password123!"),
            role="PENDING",
            grade=None,
            email_verified=False,
        )
        db.add(user)
        db.commit()

        token = auth.create_access_token({"sub": student_id, "role": "PENDING", "username": student_username})
        res = client.post(
            "/auth/onboarding",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "STUDENT", "grade": 7},
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["email"] is None, "Học sinh không có email, response phải trả về email=None"
        assert data["role"] == "STUDENT"
        assert data["grade"] == 7
    finally:
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == student_id).delete()
        db.query(models.User).filter(models.User.id == student_id).delete()
        db.commit()
        db.close()


