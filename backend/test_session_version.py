"""
Unit Test Suite cho US 6.2 - Tasks T6.10 & T6.11:
- T6.10: Trường session_version (integer) trong bảng User.
- T6.11: Middleware API /chat kiểm tra session_version, trả 401 { error: "SESSION_STALE" } nếu lệch version.
"""
import sys
import os
import uuid
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
import models
import auth
from database import SessionLocal

client = TestClient(app)

TEST_EMAIL = f"test_version_{uuid.uuid4().hex[:8]}@socratickid.local"
TEST_PASSWORD = "Password123@"


def setup_test_user():
    db = SessionLocal()
    try:
        # Xoá user cũ nếu trùng email
        old_user = db.query(models.User).filter(models.User.email == TEST_EMAIL).first()
        if old_user:
            db.query(models.Session).filter(models.Session.user_id == old_user.id).delete()
            db.query(models.RefreshToken).filter(models.RefreshToken.user_id == old_user.id).delete()
            db.delete(old_user)
            db.commit()

        # Tạo user mới với grade=5, session_version=1
        user = models.User(
            email=TEST_EMAIL,
            hashed_password=auth.hash_password(TEST_PASSWORD),
            role="STUDENT",
            grade=5,
            session_version=1
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Tạo sẵn session thực tế cho user để test
        sess = models.Session(
            id="test-session-tab-an-danh",
            user_id=user.id,
            title="Phiên chat kiểm thử"
        )
        db.add(sess)
        db.commit()

        return user.id
    finally:
        db.close()


def cleanup_test_user(user_id):
    db = SessionLocal()
    try:
        db.query(models.IndependenceScore).filter(models.IndependenceScore.session_id == "test-session-tab-an-danh").delete()
        db.query(models.Session).filter(models.Session.id == "test-session-tab-an-danh").delete()
        db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete()
        db.query(models.User).filter(models.User.id == user_id).delete()
        db.commit()
    finally:
        db.close()



def test_session_version_flow():
    print("\n=== BẮT ĐẦU TEST TOÀN DIỆN US 6.2 (TASKS T6.10 & T6.11) ===")
    user_id = setup_test_user()
    try:
        # 1. Đăng nhập để lấy token đầu tiên (session_version = 1)
        login_res = client.post(
            "/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        token_tab_an_danh = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        assert login_data.get("session_version") == 1
        assert login_data.get("grade") == 5

        # Giải mã token để xác nhận payload có session_version = 1
        decoded = auth.jwt.decode(token_tab_an_danh, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert decoded.get("session_version") == 1
        assert decoded.get("grade_level") == 5
        print("[OK] Đăng nhập thành công: Token mang session_version = 1, grade = 5")

        # 2. Tab thường đổi lớp từ 5 sang lớp 6 (gọi PATCH /users/me/grade)
        # Tab thường cũng đăng nhập và có token
        patch_res = client.patch(
            "/users/me/grade",
            json={"grade": 6},
            headers={"Authorization": f"Bearer {token_tab_an_danh}"}
        )
        assert patch_res.status_code == 200
        patch_data = patch_res.json()
        assert patch_data["grade"] == 6
        assert patch_data["session_version"] == 2
        print("[OK] Tab thường đổi lớp sang 6: DB đã tăng session_version lên 2!")

        # Kiểm tra trực tiếp trong DB
        db = SessionLocal()
        user_in_db = db.query(models.User).filter(models.User.id == user_id).first()
        assert user_in_db.grade == 6
        assert user_in_db.session_version == 2
        db.close()
        print("[OK] DB xác nhận: user.grade = 6, user.session_version = 2")

        # 3. Tab ẩn danh (vẫn giữ token cũ với session_version = 1) gửi tin nhắn đến API /chat/orchestrator
        # Kỳ vọng: Middleware chặn lại ngay, trả về 401 với body {"error": "SESSION_STALE"}!
        chat_res = client.post(
            "/chat/orchestrator",
            json={
                "session_id": "test-session-tab-an-danh",
                "prompt": "Em chào thầy",
            },
            headers={"Authorization": f"Bearer {token_tab_an_danh}"}
        )
        assert chat_res.status_code == 401, f"Expected 401 but got {chat_res.status_code}: {chat_res.text}"
        chat_json = chat_res.json()
        assert chat_json == {"error": "SESSION_STALE"}, f"Body expected {{'error': 'SESSION_STALE'}} but got {chat_json}"
        print("[OK] [AC2 PASS] Tab ẩn danh dùng token cũ bị middleware chặn chính xác với mã 401 và body {'error': 'SESSION_STALE'}!")

        # 4. Kiểm tra middleware cũng chặn trên các endpoint chat khác (ví dụ /chat/comprehension)
        comp_res = client.post(
            "/chat/comprehension",
            json={"session_id": "test-session-tab-an-danh", "understood": True},
            headers={"Authorization": f"Bearer {token_tab_an_danh}"}
        )
        assert comp_res.status_code == 401
        assert comp_res.json() == {"error": "SESSION_STALE"}
        print("[OK] /chat/comprehension cũng trả về 401 {'error': 'SESSION_STALE'} khi token lệch session_version!")

        # 5. Frontend tự gọi refresh token (NextAuth update()) để đồng bộ phiên mà không logout
        refresh_res = client.post(
            "/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_res.status_code == 200
        refresh_data = refresh_res.json()
        token_moi = refresh_data["access_token"]
        assert refresh_data["session_version"] == 2
        assert refresh_data["grade"] == 6

        decoded_moi = auth.jwt.decode(token_moi, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert decoded_moi.get("session_version") == 2
        assert decoded_moi.get("grade_level") == 6
        print("[OK] [AC3 PASS] Refresh token thành công: Cấp token mới mang session_version = 2 và grade = 6 (không cần đăng nhập lại)")

        # 6. Tab ẩn danh retry request với token mới (session_version = 2 trùng với DB = 2)
        # Kỳ vọng: Middleware cho qua (không bị lỗi 401 SESSION_STALE)
        # Lưu ý: /chat/comprehension với session hợp lệ
        comp_res_moi = client.post(
            "/chat/comprehension",
            json={"session_id": "test-session-tab-an-danh", "understood": True},
            headers={"Authorization": f"Bearer {token_moi}"}
        )
        assert comp_res_moi.status_code == 200, f"Expected 200 with new token but got {comp_res_moi.status_code}: {comp_res_moi.text}"
        assert comp_res_moi.json().get("status") == "success"
        print("[OK] [AC1 & AC2 PASS] Request với token mới qua middleware thành công, trả về 200 OK!")

        # 7. Kiểm tra Guest request (không có header Authorization) không bị ảnh hưởng
        guest_res = client.post(
            "/chat/orchestrator",
            json={
                "session_id": "guest-test-12345",
                "prompt": "Chào bạn",
            }
        )
        # Guest request qua được middleware (không bị 401 SESSION_STALE)
        assert guest_res.status_code != 401 or guest_res.json() != {"error": "SESSION_STALE"}
        print("[OK] Guest request không bị chặn bởi session_version middleware!")

        print("\n=== TẤT CẢ 7 TEST CASES US 6.2 (T6.10 & T6.11) ĐÃ PASS 100%! ===")

    finally:
        cleanup_test_user(user_id)


if __name__ == "__main__":
    test_session_version_flow()
