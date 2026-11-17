"""
File: backend/test/test_us11_2_forgot_password.py
Mô tả: Bộ kiểm thử cho US 11.2 - Khôi phục mật khẩu cho Phụ huynh:
- [DB] Cấu hình bảng dữ liệu & Mã OTP: Bổ sung mục đích "PARENT_RESET_PASSWORD", kiểm tra ràng buộc khóa ngoại users và parent_student_links
- [BE] API gửi mã OTP cho Phụ huynh (POST /auth/forgot-password/request-otp):
  + Kiểm tra tài khoản
  + Chặn tài khoản Google
  + Phân tách vai trò học sinh
  + Sinh OTP 6 số, áp dụng giới hạn 60s chống spam
  + Gửi email qua Brevo SMTP / email_service
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import SessionLocal
import models
import auth
from services.email_service import get_sent_emails, clear_sent_emails


@pytest.fixture(autouse=True)
def clean_email_logs():
    clear_sent_emails()
    yield
    clear_sent_emails()


@pytest.fixture
def test_users_setup():
    """Tạo bộ user kiểm thử: Parent bình thường, Parent Google, Student."""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]

    parent_email = f"parent_{suffix}@example.com"
    google_parent_email = f"google_parent_{suffix}@gmail.com"
    student_email = f"student_{suffix}@example.com"
    student_username = f"student_{suffix}"

    parent_id = f"parent-{suffix}"
    google_parent_id = f"google-parent-{suffix}"
    student_id = f"student-{suffix}"

    # 1. Phụ huynh mật khẩu thường (hợp lệ để reset password)
    parent = models.User(
        id=parent_id,
        email=parent_email,
        username=f"parent_{suffix}",
        hashed_password=auth.hash_password("ValidPassword123"),
        role="MONITOR",
        email_verified=True,
    )

    # 2. Phụ huynh dùng Google OAuth (không có hashed_password)
    google_parent = models.User(
        id=google_parent_id,
        email=google_parent_email,
        username=f"google_parent_{suffix}",
        hashed_password=None,
        oauth_provider="google",
        role="MONITOR",
        email_verified=True,
    )

    # 3. Học sinh
    student = models.User(
        id=student_id,
        email=student_email,
        username=student_username,
        hashed_password=auth.hash_password("StudentPassword123"),
        role="STUDENT",
        grade=5,
    )

    db.add_all([parent, google_parent, student])
    db.commit()

    # 4. Tạo liên kết gia đình giữa parent và student
    link = models.ParentStudentLink(
        parent_id=parent_id,
        student_id=student_id,
        student_nickname="Bé Cưng",
    )
    db.add(link)
    db.commit()
    db.close()

    yield {
        "parent_email": parent_email,
        "google_parent_email": google_parent_email,
        "student_email": student_email,
        "parent_id": parent_id,
        "student_id": student_id,
    }

    # Dọn dẹp
    db = SessionLocal()
    db.query(models.ParentStudentLink).filter(
        models.ParentStudentLink.parent_id == parent_id
    ).delete()
    db.query(models.EmailOtp).filter(
        models.EmailOtp.email.in_([parent_email, google_parent_email, student_email])
    ).delete()
    db.query(models.User).filter(
        models.User.id.in_([parent_id, google_parent_id, student_id])
    ).delete()
    db.commit()
    db.close()


def test_parent_student_link_foreign_key_constraints(test_users_setup):
    """
    [DB Task]: Kiểm tra ràng buộc khóa ngoại giữa users và parent_student_links.
    Khi xóa parent hoặc student, liên kết gia đình phải được xử lý toàn vẹn (CASCADE).
    """
    db = SessionLocal()
    parent_id = test_users_setup["parent_id"]
    student_id = test_users_setup["student_id"]

    # Kiểm tra liên kết đã tồn tại
    link = db.query(models.ParentStudentLink).filter_by(
        parent_id=parent_id, student_id=student_id
    ).first()
    assert link is not None
    assert link.student_nickname == "Bé Cưng"

    # Kiểm tra relationship monitored_students trên User
    parent_user = db.query(models.User).filter_by(id=parent_id).first()
    assert parent_user is not None
    student_ids = [s.id for s in parent_user.monitored_students]
    assert student_id in student_ids
    db.close()


def test_forgot_password_request_otp_non_existent_email():
    """Kiểm tra email chưa đăng ký -> trả về HTTP 404."""
    client = TestClient(app)
    res = client.post(
        "/auth/forgot-password/request-otp",
        json={"email": "non_existent_123456@gmail.com"}
    )
    assert res.status_code == 404
    assert "chưa được đăng ký" in res.json()["detail"]


def test_forgot_password_request_otp_google_account_blocked(test_users_setup):
    """
    [AC3]: Phụ huynh nhập email từng dùng đăng nhập Google ->
    Hệ thống chặn và hướng dẫn bấm nút 'Đăng nhập bằng Google' ngoài màn hình chính.
    """
    client = TestClient(app)
    google_email = test_users_setup["google_parent_email"]

    res = client.post(
        "/auth/forgot-password/request-otp",
        json={"email": google_email}
    )
    assert res.status_code == 400
    assert "dùng đăng nhập Google" in res.json()["detail"]


def test_forgot_password_request_otp_student_account_rejected(test_users_setup):
    """Tài khoản học sinh không đặt lại mật khẩu bằng email -> trả về HTTP 400."""
    client = TestClient(app)
    student_email = test_users_setup["student_email"]

    res = client.post(
        "/auth/forgot-password/request-otp",
        json={"email": student_email}
    )
    assert res.status_code == 400
    assert "học sinh không đặt lại mật khẩu bằng email" in res.json()["detail"]


def test_forgot_password_request_otp_success_and_rate_limit(test_users_setup):
    """
    [BE Task]:
    - Phụ huynh nhập email hợp lệ -> Sinh OTP 6 số, purpose='PARENT_RESET_PASSWORD', gửi email thành công.
    - Gửi lại ngay lập tức (< 60s) -> Bị chặn với HTTP 429 và thông báo chờ.
    """
    client = TestClient(app)
    parent_email = test_users_setup["parent_email"]

    # 1. Yêu cầu mã lần đầu -> Thành công 200
    res1 = client.post(
        "/auth/forgot-password/request-otp",
        json={"email": parent_email}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    assert data1["email"] == parent_email.lower()
    assert data1["rate_limit_seconds"] == 60

    # Kiểm tra bản ghi OTP trong database
    db = SessionLocal()
    otp_record = (
        db.query(models.EmailOtp)
        .filter_by(email=parent_email.lower(), purpose="PARENT_RESET_PASSWORD")
        .order_by(models.EmailOtp.created_at.desc())
        .first()
    )
    assert otp_record is not None
    assert len(otp_record.otp_code) == 6
    assert otp_record.otp_code.isdigit()
    assert otp_record.is_used is False
    db.close()

    # Kiểm tra email đã được gửi qua email_service
    sent_emails = get_sent_emails()
    assert len(sent_emails) == 1
    assert sent_emails[0]["to_email"] == parent_email.lower()
    assert "khôi phục mật khẩu" in sent_emails[0]["subject"]
    assert otp_record.otp_code in sent_emails[0]["text_content"]

    # 2. Yêu cầu gửi lại ngay lập tức -> Vi phạm giới hạn 60s -> HTTP 429
    res2 = client.post(
        "/auth/forgot-password/request-otp",
        json={"email": parent_email}
    )
    assert res2.status_code == 429
    assert "Vui lòng chờ thêm" in res2.json()["detail"]
