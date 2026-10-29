# test/test_curriculum_sync_vietjack.py
# US 8.4 - Task T8.25: Kiểm thử API POST /admin/curriculum/sync-vietjack kích hoạt crawler và upsert chuyên đề vào DB.

import os
import sys
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import auth
import models
import schemas
from database import get_db

client = TestClient(app)

ADMIN_TOKEN = auth.create_access_token({"sub": "admin_test_sync", "email": "admin@socratickid.edu.vn", "role": "ADMIN", "session_version": 1})
STUDENT_TOKEN = auth.create_access_token({"sub": "student_test_sync", "email": "student@socratickid.edu.vn", "role": "STUDENT", "session_version": 1})
MONITOR_TOKEN = auth.create_access_token({"sub": "monitor_test_sync", "email": "parent@socratickid.edu.vn", "role": "MONITOR", "session_version": 1})

ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}
MONITOR_HEADERS = {"Authorization": f"Bearer {MONITOR_TOKEN}"}


class TestCurriculumSyncVietjackAPI:
    """Bộ kiểm thử cho API POST /admin/curriculum/sync-vietjack kích hoạt crawler và upsert Neon DB."""

    def test_01_rbac_unauthenticated_and_forbidden(self):
        """
        Kiểm tra bảo mật RBAC:
        1. Người dùng chưa đăng nhập -> 401 Unauthorized.
        2. Học sinh (STUDENT) hoặc Phụ huynh (MONITOR) gọi API -> 403 Forbidden.
        """
        # 1. Không có token
        res_no_auth = client.post("/admin/curriculum/sync-vietjack")
        assert res_no_auth.status_code == 401

        # 2. Học sinh
        res_student = client.post("/admin/curriculum/sync-vietjack", headers=STUDENT_HEADERS)
        assert res_student.status_code == 403

        # 3. Phụ huynh
        res_monitor = client.post("/admin/curriculum/sync-vietjack", headers=MONITOR_HEADERS)
        assert res_monitor.status_code == 403

    def test_02_sync_curriculum_fallback_mode(self):
        """
        Admin gọi POST /admin/curriculum/sync-vietjack với force_fallback=True (Lớp 4, 5).
        Kiểm tra response định dạng chuẩn SyncVietjackResult và dữ liệu lưu thành công vào DB.
        """
        payload = {
            "grades": [4, 5],
            "school_year": "2024-2025",
            "force_fallback": True,
        }
        res = client.post("/admin/curriculum/sync-vietjack", json=payload, headers=ADMIN_HEADERS)
        assert res.status_code == 200

        data = res.json()
        assert data["success"] is True
        assert data["total_synced"] > 0
        assert data["grades"] == [4, 5]
        assert data["current_total_in_db"] >= data["total_synced"]
        assert "Đồng bộ thành công" in data["message"]
        assert data["elapsed_seconds"] >= 0

        # Xác thực Pydantic schema
        result = schemas.SyncVietjackResult.model_validate(data)
        assert result.success is True

    def test_03_idempotency_bulk_upsert(self):
        """
        Đồng bộ lặp lại nhiều lần không sinh ra bản ghi trùng lặp và không lỗi Unique Constraint.
        """
        payload = {
            "grades": [4],
            "school_year": "2024-2025",
            "force_fallback": True,
        }
        # Lần 1
        res1 = client.post("/admin/curriculum/sync-vietjack", json=payload, headers=ADMIN_HEADERS)
        assert res1.status_code == 200
        count1 = res1.json()["total_synced"]

        # Lần 2 (ngay sau đó với cùng payload)
        res2 = client.post("/admin/curriculum/sync-vietjack", json=payload, headers=ADMIN_HEADERS)
        assert res2.status_code == 200
        count2 = res2.json()["total_synced"]

        assert count1 == count2
        assert res2.json()["success"] is True

    def test_04_preserve_is_active_toggle_on_sync(self):
        """
        Kiểm tra tính toàn vẹn trạng thái Bật/Tắt (AC 8.4.3):
        Nếu Admin đã cấu hình ẩn một bài học (is_active = False), khi kích hoạt crawler/sync
        bài học đó vẫn phải giữ nguyên is_active = False, không bị ghi đè thành True.
        """
        db: Session = next(get_db())
        try:
            # Chọn 1 topic lớp 4 để tắt
            topic = db.query(models.CurriculumTopic).filter(
                models.CurriculumTopic.grade == 4,
                models.CurriculumTopic.book_series == "Kết nối tri thức"
            ).first()

            assert topic is not None, "Cần có ít nhất 1 bài học lớp 4 trong DB"
            target_id = topic.id

            # Đổi sang False (Tắt/Ẩn)
            topic.is_active = False
            db.commit()

            # Chạy sync lại cho Lớp 4
            res = client.post(
                "/admin/curriculum/sync-vietjack",
                json={"grades": [4], "force_fallback": True},
                headers=ADMIN_HEADERS,
            )
            assert res.status_code == 200

            # Lấy lại topic từ DB để kiểm tra
            db.expire_all()
            updated_topic = db.query(models.CurriculumTopic).filter(models.CurriculumTopic.id == target_id).first()
            assert updated_topic is not None
            assert updated_topic.is_active is False, "is_active phải được bảo toàn là False khi Admin đã cấu hình giảm tải"

            # Phục hồi lại True
            updated_topic.is_active = True
            db.commit()
        finally:
            db.close()

    def test_05_mock_route_alias(self):
        """
        Kiểm tra endpoint tương đương trên router mock: POST /admin/mock/curriculum/sync-vietjack.
        Đảm bảo cả 2 router /admin và /admin/mock đều hoạt động đồng bộ.
        """
        res = client.post(
            "/admin/mock/curriculum/sync-vietjack",
            json={"grades": [6], "force_fallback": True},
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["grades"] == [6]
        assert data["total_synced"] > 0

    def test_06_live_crawler_or_auto_fallback(self):
        """
        Kiểm tra luồng mặc định (không ép fallback):
        Kích hoạt crawler cho lớp 4. Nếu kết nối VietJack bình thường sẽ cào trực tiếp;
        nếu mạng timeout / lỗi thì tự động fallback an toàn mà không làm sập server.
        """
        res = client.post(
            "/admin/curriculum/sync-vietjack",
            json={"grades": [4]},
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["total_synced"] > 0
        assert data["elapsed_seconds"] >= 0
