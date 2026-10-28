# test/test_admin_logs_filter.py
# US 8.5 - Task T8.29B: Kiểm thử API Admin Logs lọc theo tài khoản (user_id / email)

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import auth
import models
from database import get_db

client = TestClient(app)

ADMIN_TOKEN = auth.create_access_token({"sub": "admin_test_01", "email": "admin@socratickid.edu.vn", "role": "ADMIN", "session_version": 1})
STUDENT_TOKEN = auth.create_access_token({"sub": "student_test_01", "email": "student@socratickid.edu.vn", "role": "STUDENT", "session_version": 1})

ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}


class TestAdminLogsFilterAPI:
    """Bộ kiểm thử cho API GET /admin/logs?user_id=...&email=..."""

    def test_01_rbac_permission_denied_for_non_admin(self):
        """Học sinh hoặc người dùng không có quyền ADMIN bị chặn 403."""
        res = client.get("/admin/logs", headers=STUDENT_HEADERS)
        assert res.status_code == 403

    def test_02_get_all_logs_default(self):
        """Admin lấy toàn bộ logs khi không truyền query filter."""
        res = client.get("/admin/logs", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1

    def test_03_filter_by_email_found(self):
        """AC 8.5.2: Nhập email vào ô tìm kiếm -> Bảng chỉ hiển thị đúng các sự kiện của tài khoản đó."""
        target_email = "an.dinh@example.com"
        res = client.get(f"/admin/logs?email={target_email}", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert target_email.lower() in (item["student_email"] or "").lower() or target_email.lower() in (item["email"] or "").lower()

    def test_04_filter_by_user_id_found(self):
        """Lọc logs theo user_id tài khoản."""
        target_uid = "std_1009"
        res = client.get(f"/admin/logs?user_id={target_uid}", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["student_id"] == target_uid or item["user_id"] == target_uid

    def test_05_filter_nonexistent_email_returns_empty(self):
        """Tìm email không tồn tại trong hệ thống trả về 0 kết quả."""
        res = client.get("/admin/logs?email=nonexistent_user_99999@test.com", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_06_filter_real_db_orchestrator_log(self):
        """Kiểm tra tra cứu log thật được ghi trong bảng orchestrator_logs (kèm cờ notify_parent)."""
        db: Session = next(get_db())

        unique_id = uuid.uuid4().hex[:8]
        real_email = f"student_real_{unique_id}@test.school.vn"
        real_user = models.User(
            email=real_email,
            role="STUDENT",
            grade=5,
        )
        db.add(real_user)
        db.commit()
        db.refresh(real_user)

        # Tạo log Orchestrator trong DB với notify_parent=True
        test_log = models.OrchestratorLog(
            user_id=real_user.id,
            user_query="Bài này con chửi thề vcl thầy ơi",
            target_agent="SAFETY_AGENT",
            reason="Phát hiện ngôn từ thô tục profanity",
            notify_parent=True,
        )
        db.add(test_log)
        db.commit()

        try:
            # Gọi API GET /admin/logs?email=...
            res = client.get(f"/admin/logs?email={real_email}", headers=ADMIN_HEADERS)
            assert res.status_code == 200
            data = res.json()
            assert data["total"] >= 1
            matched_item = next((it for it in data["items"] if it["id"] == test_log.id), None)
            assert matched_item is not None
            assert matched_item["student_email"] == real_email
            assert matched_item["notify_parent"] is True
            assert matched_item["message_snippet"] == "Bài này con chửi thề vcl thầy ơi"

            # Gọi API GET /admin/logs?user_id=...
            res_uid = client.get(f"/admin/logs?user_id={real_user.id}", headers=ADMIN_HEADERS)
            assert res_uid.status_code == 200
            data_uid = res_uid.json()
            assert any(it["id"] == test_log.id for it in data_uid["items"])
        finally:
            db.delete(test_log)
            db.delete(real_user)
            db.commit()

    def test_07_mock_safety_logs_endpoint_compatible(self):
        """Đảm bảo endpoint /admin/mock/safety/logs cũng nhận user_id / email lọc mượt mà."""
        res = client.get("/admin/mock/safety/logs?email=huy.doan@example.com", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        assert "huy.doan@example.com" in data["items"][0]["student_email"]
