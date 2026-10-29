# US 8.3 - Task T8.18 & T8.19: Tests cho tính năng Google OAuth Login
# Nghiệp vụ:
# 1. T8.18: Bảng users hỗ trợ google_id, oauth_provider và hashed_password nullable.
# 2. T8.19: POST /auth/google-callback tạo mới hoặc tìm user, cấp JWT chuẩn, trả về is_new_user.
# 3. JWT cấp từ Google Login gọi được các API của hệ thống không bị 401.
# 4. Onboarding: Chuyển đổi trạng thái is_new_user sau khi chọn vai trò / khối lớp.

import sys
import os
import uuid
import pytest
from datetime import datetime, timezone
from jose import jwt

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import auth
import models
import dependencies
from database import SessionLocal, engine
from sqlalchemy import text

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.pop(dependencies.get_current_user, None)
    yield
    app.dependency_overrides.pop(dependencies.get_current_user, None)

TEST_NEW_GOOGLE_EMAIL = "google_newbie_us83@gmail.com"
TEST_NEW_GOOGLE_ID    = "gid_sub_99887766"

TEST_EXISTING_GOOGLE_EMAIL = "google_existing_us83@gmail.com"
TEST_EXISTING_GOOGLE_ID    = "gid_sub_11223344"

TEST_LINK_EMAIL = "link_acc_us83@gmail.com"
TEST_LINK_GID   = "gid_sub_55667788"


def cleanup_db(db):
    db.rollback()
    emails = [TEST_NEW_GOOGLE_EMAIL, TEST_EXISTING_GOOGLE_EMAIL, TEST_LINK_EMAIL]
    user_ids = [
        row[0] for row in db.query(models.User.id).filter(models.User.email.in_(emails)).all()
    ]
    if user_ids:
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(models.User).filter(models.User.id.in_(user_ids)).delete(synchronize_session=False)
        db.commit()


def test_t8_18_db_schema_google_columns_and_nullable_password():
    """
    T8.18: Kiểm tra bảng users đã có các cột google_id, oauth_provider
    và hashed_password cho phép NULL.
    """
    from sqlalchemy import inspect
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("users")}

    assert "google_id" in columns, "Thiếu cột google_id trong bảng users"
    assert "oauth_provider" in columns, "Thiếu cột oauth_provider trong bảng users"
    assert columns["hashed_password"]["nullable"] is True, "hashed_password phải là NULLABLE"

    # Kiểm tra lưu user với hashed_password=None thành công
    db = SessionLocal()
    try:
        cleanup_db(db)
        user = models.User(
            id=uuid.uuid4().hex,
            email=TEST_NEW_GOOGLE_EMAIL,
            google_id=TEST_NEW_GOOGLE_ID,
            oauth_provider="google",
            hashed_password=None,
            role="STUDENT",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.hashed_password is None
        assert user.google_id == TEST_NEW_GOOGLE_ID
        assert user.oauth_provider == "google"
        print("  [PASS] T8.18: Bảng users hỗ trợ google_id, oauth_provider và nullable password")
    finally:
        cleanup_db(db)
        db.close()


def test_t8_19_new_google_user_first_login():
    """
    T8.19: Người dùng Google hoàn toàn mới đăng nhập lần đầu:
    - POST /auth/google-callback tạo mới user
    - hashed_password = None, oauth_provider = 'google'
    - Trả về JWT access_token, refresh_token hợp lệ
    - Cờ is_new_user = True (để FE chuyển hướng sang /onboarding)
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        resp = client.post("/auth/google-callback", json={
            "email": TEST_NEW_GOOGLE_EMAIL,
            "google_id": TEST_NEW_GOOGLE_ID,
            "name": "Nguyen Van Google",
        })
        assert resp.status_code == 200, f"Google callback failed: {resp.text}"
        data = resp.json()

        # Kiểm tra token và cờ is_new_user
        assert data["is_new_user"] is True, "User mới phải có is_new_user = True"
        assert data["email"] == TEST_NEW_GOOGLE_EMAIL
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20
        assert len(data["refresh_token"]) > 20

        # Kiểm tra giải mã JWT token
        payload = jwt.decode(data["access_token"], auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload["sub"] == data["user_id"]
        assert payload["email"] == TEST_NEW_GOOGLE_EMAIL
        assert payload["role"] == "PENDING", "Tài khoản mới phải có role=PENDING khi chưa chọn vai trò"

        # Kiểm tra user trong DB
        user_in_db = db.query(models.User).filter(models.User.email == TEST_NEW_GOOGLE_EMAIL).first()
        assert user_in_db is not None
        assert user_in_db.google_id == TEST_NEW_GOOGLE_ID
        assert user_in_db.oauth_provider == "google"
        assert user_in_db.hashed_password is None
        assert user_in_db.role == "PENDING", "Trong DB chưa chọn vai trò thì role phải là PENDING"

        print("  [PASS] T8.19: User Google mới tạo thành công kèm role=PENDING & is_new_user=True")
    finally:
        cleanup_db(db)
        db.close()


def test_cancel_onboarding_purges_pending_user():
    """
    Kiểm tra khi người dùng bấm Hủy / Back ở trang onboarding:
    - POST /auth/cancel-onboarding dọn dẹp sạch sẽ tài khoản PENDING trong Neon DB.
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        # 1. Đăng nhập Google tạo tài khoản PENDING
        login_resp = client.post("/auth/google-callback", json={
            "email": TEST_NEW_GOOGLE_EMAIL,
            "google_id": TEST_NEW_GOOGLE_ID,
        })
        token = login_resp.json()["access_token"]
        assert login_resp.json()["role"] == "PENDING"

        # User tạm đang tồn tại trong DB với role='PENDING'
        user_before = db.query(models.User).filter(models.User.email == TEST_NEW_GOOGLE_EMAIL).first()
        assert user_before is not None
        assert user_before.role == "PENDING"

        # 2. Người dùng hủy onboarding
        cancel_resp = client.post("/auth/cancel-onboarding", headers={"Authorization": f"Bearer {token}"})
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["success"] is True

        # 3. Kiểm tra DB: tài khoản PENDING đã bị xóa hoàn toàn khỏi DB
        user_after = db.query(models.User).filter(models.User.email == TEST_NEW_GOOGLE_EMAIL).first()
        assert user_after is None, "Tài khoản PENDING phải được xóa sạch sau khi hủy onboarding"
        print("  [PASS] cancel_onboarding: Dọn dẹp tài khoản PENDING thành công, không lưu tài khoản rác")
    finally:
        cleanup_db(db)
        db.close()


def test_t8_19_google_jwt_calls_protected_endpoints_no_401():
    """
    [AC 8.3.1]: Click 'Đăng nhập với Google' -> cấp JWT chuẩn,
    gọi các API yêu cầu xác thực không còn lỗi 401.
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        login_resp = client.post("/auth/google-callback", json={
            "email": TEST_NEW_GOOGLE_EMAIL,
            "google_id": TEST_NEW_GOOGLE_ID,
        })
        token = login_resp.json()["access_token"]

        # Gọi API /users/me với token này
        me_resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.status_code == 200, f"Gọi /users/me bị lỗi {me_resp.status_code}: {me_resp.text}"
        user_data = me_resp.json()
        assert user_data["email"] == TEST_NEW_GOOGLE_EMAIL

        # Gọi API /bookmarks với token này
        bm_resp = client.get("/bookmarks", headers={"Authorization": f"Bearer {token}"})
        assert bm_resp.status_code == 200, f"Gọi /bookmarks bị lỗi {bm_resp.status_code}: {bm_resp.text}"

        print("  [PASS] AC 8.3.1: Token JWT từ Google gọi API /users/me và /bookmarks thành công (200 OK, không lỗi 401)")
    finally:
        cleanup_db(db)
        db.close()


def test_t8_19_onboarded_google_user_logs_in_again():
    """
    [AC 8.3.3]: Tài khoản Google đã từng onboarding khi đăng nhập lại:
    - is_new_user = False (FE cho vào thẳng Dashboard)
    - Giữ nguyên user_id và dữ liệu đã có.
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        # Tạo sẵn user đã hoàn thành onboarding (có grade = 5)
        existing_user = models.User(
            id=uuid.uuid4().hex,
            email=TEST_EXISTING_GOOGLE_EMAIL,
            google_id=TEST_EXISTING_GOOGLE_ID,
            oauth_provider="google",
            hashed_password=None,
            role="STUDENT",
            grade=5,
        )
        db.add(existing_user)
        db.commit()

        # Đăng nhập lại qua Google
        resp = client.post("/auth/google-callback", json={
            "email": TEST_EXISTING_GOOGLE_EMAIL,
            "google_id": TEST_EXISTING_GOOGLE_ID,
        })
        assert resp.status_code == 200
        data = resp.json()

        # User cũ đã onboarding -> is_new_user phải là False
        assert data["is_new_user"] is False
        assert data["user_id"] == existing_user.id
        assert data["grade"] == 5
        print("  [PASS] AC 8.3.3: User Google đã onboarding khi đăng nhập lại có is_new_user=False")
    finally:
        cleanup_db(db)
        db.close()


def test_t8_19_existing_password_user_links_google():
    """
    Người dùng trước đó đăng ký qua Email/Password, nay ấn 'Đăng nhập Google':
    - Hệ thống tìm thấy user theo email
    - Tự động liên kết google_id
    - is_new_user = False
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        # Tạo sẵn user có password và grade=6
        old_user = models.User(
            id=uuid.uuid4().hex,
            email=TEST_LINK_EMAIL,
            hashed_password=auth.hash_password("MatKhau123!"),
            role="STUDENT",
            grade=6,
        )
        db.add(old_user)
        db.commit()

        # Đăng nhập Google với cùng email
        resp = client.post("/auth/google-callback", json={
            "email": TEST_LINK_EMAIL,
            "google_id": TEST_LINK_GID,
        })
        assert resp.status_code == 200
        data = resp.json()

        assert data["user_id"] == old_user.id
        assert data["is_new_user"] is False
        assert data["grade"] == 6

        # Kiểm tra DB đã liên kết google_id
        db.refresh(old_user)
        assert old_user.google_id == TEST_LINK_GID
        assert old_user.oauth_provider == "google"
        # Mật khẩu cũ vẫn được giữ nguyên
        assert old_user.hashed_password is not None
        print("  [PASS] T8.19: Liên kết thành công Google ID cho tài khoản Email/Password có sẵn")
    finally:
        cleanup_db(db)
        db.close()


def test_t8_21_complete_onboarding_endpoint():
    """
    T8.21: Luồng Onboarding cho user Google:
    1. User mới đăng nhập -> is_new_user = True
    2. Gọi POST /auth/onboarding chọn vai trò và lớp -> Cập nhật DB và cấp JWT mới
    3. Đăng nhập Google lần sau -> is_new_user = False
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        # 1. Đăng nhập lần đầu
        first_resp = client.post("/auth/google-callback", json={
            "email": TEST_NEW_GOOGLE_EMAIL,
            "google_id": TEST_NEW_GOOGLE_ID,
        })
        first_data = first_resp.json()
        assert first_data["is_new_user"] is True
        token = first_data["access_token"]

        # 2. Hoàn tất Onboarding: Chọn vai trò STUDENT, lớp 5
        onboard_resp = client.post(
            "/auth/onboarding",
            headers={"Authorization": f"Bearer {token}"},
            json={"role": "STUDENT", "grade": 5},
        )
        assert onboard_resp.status_code == 200, f"Onboarding failed: {onboard_resp.text}"
        onboard_data = onboard_resp.json()
        assert onboard_data["is_new_user"] is False
        assert onboard_data["role"] == "STUDENT"
        assert onboard_data["grade"] == 5

        # 3. Lần sau đăng nhập lại
        again_resp = client.post("/auth/google-callback", json={
            "email": TEST_NEW_GOOGLE_EMAIL,
            "google_id": TEST_NEW_GOOGLE_ID,
        })
        again_data = again_resp.json()
        assert again_data["is_new_user"] is False
        assert again_data["grade"] == 5
        print("  [PASS] T8.21: Luồng Onboarding hoàn tất -> Lần đăng nhập sau có is_new_user=False")
    finally:
        cleanup_db(db)
        db.close()


def test_refresh_token_flow_for_google_user():
    """
    Kiểm tra refresh_token được cấp cho Google user hoạt động trơn tru với POST /refresh.
    """
    db = SessionLocal()
    try:
        cleanup_db(db)
        login_resp = client.post("/auth/google-callback", json={
            "email": TEST_NEW_GOOGLE_EMAIL,
            "google_id": TEST_NEW_GOOGLE_ID,
        })
        rf_token = login_resp.json()["refresh_token"]

        # Gọi POST /refresh
        refresh_resp = client.post("/refresh", json={"refresh_token": rf_token})
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        # Access token mới hoạt động tốt
        me_resp = client.get("/users/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
        assert me_resp.status_code == 200
        print("  [PASS] POST /refresh hoạt động trơn tru cho tài khoản Google OAuth")
    finally:
        cleanup_db(db)
        db.close()
