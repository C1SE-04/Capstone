# test/test_streak_leaderboard_search_and_auth_sync.py
"""
Kiểm thử US 9.4: Tìm kiếm Bảng Xếp Hạng Chuỗi Ngày Học & Đồng Bộ Tên Người Dùng
=============================================================================
1. Leaderboard Search & Rank Preservation:
   - GET /metrics/streak-leaderboard?search=...
   - Tìm kiếm không phân biệt hoa thường theo display_name và username
   - Bảo toàn thứ hạng gốc (rank) không bị đánh số lại từ 1
   - Bảo toàn total_participants của toàn bộ người tham gia
   - Trả về rỗng khi tìm từ khóa không khớp
2. Auth Username & Name Consistency:
   - POST /login: trả về username và encode username vào access_token
   - POST /auth/google-callback: trả về username và encode username vào access_token
   - POST /auth/verify-otp: đồng bộ notification_email = email khi xác thực OTP
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from jose import jwt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import auth
import models
from database import SessionLocal

client = TestClient(app)

TEST_STUDENT_ID = f"std_test_{uuid.uuid4().hex[:6]}"
TEST_STUDENT_USER = f"linh_dan_{uuid.uuid4().hex[:4]}"
TEST_STUDENT_TOKEN = auth.create_access_token({
    "sub": TEST_STUDENT_ID,
    "username": TEST_STUDENT_USER,
    "role": "STUDENT",
    "grade_level": 5,
    "session_version": 1,
})
STUDENT_HEADERS = {"Authorization": f"Bearer {TEST_STUDENT_TOKEN}"}


@pytest.fixture(scope="module", autouse=True)
def setup_test_students():
    """Tạo học sinh mẫu có username đặc biệt để kiểm thử tìm kiếm thứ hạng."""
    db = SessionLocal()
    try:
        # Tạo học sinh đặc biệt có tên chứa 'Linh'
        student_linh = models.User(
            id=TEST_STUDENT_ID,
            username=TEST_STUDENT_USER,
            email=f"{TEST_STUDENT_USER}@test.edu.vn",
            hashed_password=auth.hash_password("Password123!"),
            role="STUDENT",
            grade=5,
            email_verified=True,
            session_version=1,
        )
        db.add(student_linh)
        db.commit()
    finally:
        db.close()


class TestStreakLeaderboardSearch:
    """Kiểm thử API GET /metrics/streak-leaderboard?search=..."""

    def test_01_search_preserves_original_rank(self):
        """
        Gõ tên bạn vào ô tìm kiếm -> Bảng lọc học sinh theo từ khóa,
        nhưng BẢO TOÀN thứ hạng gốc (rank) trên bảng tổng sắp.
        """
        # 1. Lấy toàn bộ bảng xếp hạng trước
        all_res = client.get("/metrics/streak-leaderboard?grade=5", headers=STUDENT_HEADERS)
        assert all_res.status_code == 200
        all_data = all_res.json()
        assert "leaderboard" in all_data
        total_p = all_data["total_participants"]
        assert total_p >= 1

        # Tìm thứ hạng gốc của học sinh test trong bảng toàn bộ
        original_rank = None
        for it in all_data["leaderboard"]:
            if it["student_id"] == TEST_STUDENT_ID:
                original_rank = it["rank"]
                break

        # 2. Tìm kiếm với từ khóa 'linh' (không phân biệt hoa thường)
        search_res = client.get(f"/metrics/streak-leaderboard?grade=5&search=Linh", headers=STUDENT_HEADERS)
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert "leaderboard" in search_data
        assert search_data["total_participants"] == total_p  # Bảo toàn tổng số người tham gia

        # Kết quả lọc phải chứa học sinh test
        matching_items = [it for it in search_data["leaderboard"] if it["student_id"] == TEST_STUDENT_ID]
        assert len(matching_items) == 1
        found_item = matching_items[0]

        # Kiểm tra thứ hạng được bảo toàn, không bị đánh số lại từ 1
        if original_rank is not None:
            assert found_item["rank"] == original_rank

        # Kiểm tra display_name hoặc username chứa 'linh'
        assert "linh" in found_item["display_name"].lower() or "linh" in (found_item.get("username") or "").lower()

    def test_02_search_nonexistent_returns_empty(self):
        """Gõ một từ khóa không tồn tại -> Trả về danh sách rỗng (FE hiển thị Không tìm thấy)."""
        res = client.get("/metrics/streak-leaderboard?search=NONEXISTENT_XYZ_9999", headers=STUDENT_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["leaderboard"] == []
        assert data["total_participants"] >= 1  # Vẫn giữ tổng số học sinh thực tế

    def test_03_empty_search_restores_default_list(self):
        """Xóa trắng ô tìm kiếm (search="") -> Tự động khôi phục danh sách đầy đủ ban đầu."""
        res_empty = client.get("/metrics/streak-leaderboard?search=", headers=STUDENT_HEADERS)
        assert res_empty.status_code == 200
        res_no_param = client.get("/metrics/streak-leaderboard", headers=STUDENT_HEADERS)
        assert res_no_param.status_code == 200

        assert len(res_empty.json()["leaderboard"]) == len(res_no_param.json()["leaderboard"])


class TestAuthUsernameAndSync:
    """Kiểm thử tính đồng nhất username và notification_email giữa các phương thức đăng nhập."""

    def test_01_login_returns_username_and_jwt_payload(self):
        """POST /login trả về username và encode username vào access_token."""
        res = client.post(
            "/login",
            data={
                "username": TEST_STUDENT_USER,
                "password": "Password123!",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert "username" in data
        assert data["username"] == TEST_STUDENT_USER

        # Giải mã access_token kiểm tra payload
        token = data["access_token"]
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload.get("username") == TEST_STUDENT_USER
        assert payload.get("sub") == TEST_STUDENT_ID

    def test_02_google_callback_returns_consistent_username(self):
        """POST /auth/google-callback trả về đúng username từ DB và encode vào token."""
        # Gọi google-callback với email của học sinh đã có sẵn username trong DB
        res = client.post(
            "/auth/google-callback",
            json={
                "email": f"{TEST_STUDENT_USER}@test.edu.vn",
                "google_id": f"gid_{uuid.uuid4().hex[:8]}",
                "name": "Google Display Name Khac",
            },
        )
        assert res.status_code == 200
        data = res.json()
        # username trả về từ DB phải là TEST_STUDENT_USER
        assert data["username"] == TEST_STUDENT_USER
        assert data["user_id"] == TEST_STUDENT_ID

        # Token chứa username đúng từ DB
        payload = jwt.decode(data["access_token"], auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert payload.get("username") == TEST_STUDENT_USER

    def test_03_verify_otp_syncs_notification_email(self):
        """POST /auth/verify-otp cập nhật đồng thời cả email và notification_email."""
        db = SessionLocal()
        parent_id = f"parent_test_{uuid.uuid4().hex[:6]}"
        parent_user = f"parent_{uuid.uuid4().hex[:4]}"
        target_email = f"parent_{uuid.uuid4().hex[:6]}@gmail.com"

        try:
            parent = models.User(
                id=parent_id,
                username=parent_user,
                email=None,
                notification_email=None,
                hashed_password=auth.hash_password("Password123!"),
                role="MONITOR",
                email_verified=False,
            )
            db.add(parent)

            # Tạo mã OTP hợp lệ
            otp = models.EmailOtp(
                id=uuid.uuid4().hex,
                email=target_email,
                otp_code="654321",
                purpose="PARENT_REGISTER",
                attempts=0,
                expires_at=datetime.now(timezone.utc).replace(year=2030),
                is_used=False,
            )
            db.add(otp)
            db.commit()

            parent_token = auth.create_access_token({"sub": parent_id, "role": "MONITOR", "username": parent_user})
            res = client.post(
                "/auth/verify-otp",
                headers={"Authorization": f"Bearer {parent_token}"},
                json={
                    "email": target_email,
                    "otp_code": "654321",
                    "purpose": "PARENT_REGISTER",
                },
            )
            assert res.status_code == 200

            # Kiểm tra trong DB: CẢ 2 cột email và notification_email đều được lưu
            db.refresh(parent)
            assert parent.email == target_email
            assert parent.notification_email == target_email
            assert parent.email_verified is True
        finally:
            db.close()
