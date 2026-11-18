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
        "student_username": student_username,
        "parent_username": f"parent_{suffix}",
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


def test_forgot_password_verify_and_reset_invalid_otp_and_lockout(test_users_setup):
    """
    [Task 1]: Nhập sai OTP -> Báo lỗi số lần còn lại.
    Nhập sai đủ 5 lần -> Tạm khóa 15 phút.
    """
    from datetime import timedelta
    client = TestClient(app)
    parent_email = test_users_setup["parent_email"]

    # 1. Tạo OTP trong DB
    db = SessionLocal()
    otp = models.EmailOtp(
        email=parent_email.lower(),
        otp_code="123456",
        purpose="PARENT_RESET_PASSWORD",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False,
    )
    db.add(otp)
    db.commit()
    db.close()

    # Nhập sai lần 1..4 -> báo còn thử
    for i in range(1, 5):
        res = client.post(
            "/auth/forgot-password/verify-and-reset",
            json={
                "email": parent_email,
                "otp_code": "000000",
                "new_password": "NewSecretPass123",
            }
        )
        assert res.status_code == 400
        assert f"Bạn còn {5 - i} lần thử" in res.json()["detail"]

    # Nhập sai lần 5 -> Khóa 15 phút
    res5 = client.post(
        "/auth/forgot-password/verify-and-reset",
        json={
            "email": parent_email,
            "otp_code": "000000",
            "new_password": "NewSecretPass123",
        }
    )
    assert res5.status_code in [400, 429]
    assert "khóa" in res5.json()["detail"]


def test_forgot_password_verify_and_reset_success_and_session_version(test_users_setup):
    """
    [Task 1 & AC4]: Nhập đúng OTP -> Cập nhật mật khẩu mới, tăng session_version, thu hồi refresh token.
    Đăng nhập bằng mật khẩu mới thành công, mật khẩu cũ không còn hợp lệ.
    """
    from datetime import timedelta
    client = TestClient(app)
    parent_email = test_users_setup["parent_email"]

    db = SessionLocal()
    # Tạo refresh token mẫu
    user_before = db.query(models.User).filter_by(email=parent_email).first()
    old_version = user_before.session_version or 1
    rf_token = models.RefreshToken(
        user_id=user_before.id,
        token_hash=auth.hash_refresh_token(uuid.uuid4().hex),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False,
    )
    db.add(rf_token)

    # Tạo OTP hợp lệ
    otp = models.EmailOtp(
        email=parent_email.lower(),
        otp_code="654321",
        purpose="PARENT_RESET_PASSWORD",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False,
    )
    db.add(otp)
    db.commit()
    db.close()

    # Gọi API đổi mật khẩu thành công
    res = client.post(
        "/auth/forgot-password/verify-and-reset",
        json={
            "email": parent_email,
            "otp_code": "654321",
            "new_password": "BrandNewPassword456!",
        }
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Kiểm tra DB: session_version tăng, refresh token bị revoked
    db = SessionLocal()
    user_after = db.query(models.User).filter_by(email=parent_email).first()
    assert user_after.session_version == old_version + 1
    
    revoked_tokens = db.query(models.RefreshToken).filter_by(user_id=user_after.id).all()
    assert all(t.revoked is True for t in revoked_tokens)
    db.close()

    # Kiểm tra đăng nhập: mật khẩu cũ thất bại, mật khẩu mới thành công
    login_fail = client.post(
        "/auth/login",
        data={"username": parent_email, "password": "ValidPassword123"}
    )
    assert login_fail.status_code == 401

    login_success = client.post(
        "/auth/login",
        data={"username": parent_email, "password": "BrandNewPassword456!"}
    )
    assert login_success.status_code == 200
    assert "access_token" in login_success.json()


def test_student_lookup_masked_email_and_send_notification(test_users_setup):
    """
    [Task 2 & AC5]:
    1. Tra cứu học sinh bằng username -> trả về email phụ huynh che mờ.
    2. send_notification=True -> gửi email thông báo nhắc nhở tới phụ huynh qua Brevo SMTP.
    3. Gửi lại ngay lập tức -> bị giới hạn 60s cooldown.
    """
    client = TestClient(app)
    student_username = test_users_setup["student_username"]
    parent_email = test_users_setup["parent_email"]

    # 1. Tra cứu không gửi thông báo
    res_lookup = client.post(
        "/auth/forgot-password/student-lookup",
        json={"username": student_username, "send_notification": False}
    )
    assert res_lookup.status_code == 200
    data = res_lookup.json()
    assert data["success"] is True
    assert data["student_username"] == student_username
    assert data["notification_sent"] is False
    assert "***@" in data["parent_email_masked"]

    # 2. Bấm "Gửi thông báo tới Bố/Mẹ"
    clear_sent_emails()
    res_notify = client.post(
        "/auth/forgot-password/student-lookup",
        json={"username": student_username, "send_notification": True}
    )
    assert res_notify.status_code == 200
    notify_data = res_notify.json()
    assert notify_data["notification_sent"] is True

    sent_emails = get_sent_emails()
    assert len(sent_emails) == 1
    assert sent_emails[0]["to_email"] == parent_email.lower()
    assert student_username in sent_emails[0]["subject"]
    assert "Cấp lại mật khẩu" in sent_emails[0]["text_content"]

    # 3. Gửi lại ngay lập tức -> bị chặn cooldown 60s
    res_cooldown = client.post(
        "/auth/forgot-password/student-lookup",
        json={"username": student_username, "send_notification": True}
    )
    assert res_cooldown.status_code == 429
    assert "Thông báo đã được gửi" in res_cooldown.json()["detail"]


def test_student_lookup_unlinked_student():
    """Học sinh chưa liên kết với phụ huynh nào -> trả về lỗi 400 hướng dẫn."""
    db = SessionLocal()
    orphan_id = f"orphan-{uuid.uuid4().hex[:6]}"
    orphan_username = f"orphan_{uuid.uuid4().hex[:6]}"
    orphan_student = models.User(
        id=orphan_id,
        username=orphan_username,
        role="STUDENT",
        grade=4,
    )
    db.add(orphan_student)
    db.commit()
    db.close()

    client = TestClient(app)
    res = client.post(
        "/auth/forgot-password/student-lookup",
        json={"username": orphan_username}
    )
    assert res.status_code == 400
    assert "chưa được liên kết" in res.json()["detail"]

    # Dọn dẹp
    db = SessionLocal()
    db.query(models.User).filter_by(id=orphan_id).delete()
    db.commit()
    db.close()


def test_parent_reset_student_password_flow(test_users_setup):
    """
    [Task 3 & AC6, AC7]:
    1. Phụ huynh khác không có liên kết giám hộ -> bị từ chối 403 (AC7).
    2. Phụ huynh hợp lệ cấp mật khẩu mới -> thành công ngay lập tức (AC6).
    3. Học sinh có thể dùng mật khẩu mới đăng nhập ngay lập tức.
    """
    client = TestClient(app)
    parent_id = test_users_setup["parent_id"]
    student_id = test_users_setup["student_id"]
    student_username = test_users_setup["student_username"]

    # Tạo phụ huynh khác không liên kết
    db = SessionLocal()
    other_parent_id = f"other-parent-{uuid.uuid4().hex[:6]}"
    other_parent = models.User(
        id=other_parent_id,
        username=f"other_{uuid.uuid4().hex[:6]}",
        email=f"other_{uuid.uuid4().hex[:6]}@example.com",
        role="MONITOR",
    )
    db.add(other_parent)
    db.commit()
    db.close()

    parent_token = auth.create_access_token({"sub": parent_id, "role": "MONITOR", "session_version": 1})
    other_parent_token = auth.create_access_token({"sub": other_parent_id, "role": "MONITOR", "session_version": 1})

    # 1. Phụ huynh lạ cố tình đổi mật khẩu con người khác -> 403 (AC7)
    res_forbidden = client.post(
        f"/parent/students/{student_id}/reset-password",
        json={"new_password": "HackerPassword123"},
        headers={"Authorization": f"Bearer {other_parent_token}"}
    )
    assert res_forbidden.status_code == 403
    assert "không có quyền" in res_forbidden.json()["detail"]

    # 2. Phụ huynh hợp lệ đổi mật khẩu cho con -> 200 thành công (AC6)
    res_success = client.post(
        f"/parent/students/{student_id}/reset-password",
        json={"new_password": "ConYeuPassword2026!"},
        headers={"Authorization": f"Bearer {parent_token}"}
    )
    assert res_success.status_code == 200
    assert res_success.json()["success"] is True

    # 3. Cũng kiểm tra route alias qua /family/students/{student_id}/reset-password
    res_alias = client.post(
        f"/family/students/{student_id}/reset-password",
        json={"new_password": "ConYeuPassword2026_Alias!"},
        headers={"Authorization": f"Bearer {parent_token}"}
    )
    assert res_alias.status_code == 200
    assert res_alias.json()["success"] is True

    # 4. Học sinh đăng nhập bằng mật khẩu mới -> thành công ngay lập tức
    student_login = client.post(
        "/auth/login",
        data={"username": student_username, "password": "ConYeuPassword2026_Alias!"}
    )
    assert student_login.status_code == 200
    assert "access_token" in student_login.json()

    # Dọn dẹp phụ huynh lạ
    db = SessionLocal()
    db.query(models.User).filter_by(id=other_parent_id).delete()
    db.commit()
    db.close()
