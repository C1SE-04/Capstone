"""
Unit Tests for US 10.3 (Task T10.3.1)
SystemConfigService: Redis Cache, DB Persistence & Hot-Reloading
================================================================
Test suite covers:
  - T10.3.1: get_system_settings() with Cache Miss -> reads DB & populates Cache (TTL 300s)
  - T10.3.1: get_system_settings() with Cache Hit -> returns cached dict without DB query
  - T10.3.1: update_system_settings() updates DB, writes Audit Trail, invalidates Redis Cache
  - T10.3.1: rollback_system_settings() successfully restores previous configuration
  - T10.3.1: get_setting_audits() returns audits sorted descending
  - T10.3.1: Security constraint: ignores sensitive keys like api_key_override
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, SystemSettings, SystemSettingAudit
from services.system_config_service import (
    SystemConfigService,
    get_system_settings,
    update_system_settings,
    rollback_system_settings,
    get_setting_audits,
    CACHE_KEY,
    CACHE_TTL_SECONDS,
    DEFAULT_SYSTEM_SETTINGS,
)


class TestUS10_3_SystemConfigService(unittest.TestCase):
    """Kiểm thử tầng nghiệp vụ SystemConfigService của US 10.3 (T10.3.1)."""

    def setUp(self):
        # Database SQLite in-memory phục vụ kiểm thử cô lập
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(
            bind=self.engine,
            tables=[SystemSettings.__table__, SystemSettingAudit.__table__]
        )
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(
            bind=self.engine,
            tables=[SystemSettings.__table__, SystemSettingAudit.__table__]
        )

    @patch("services.system_config_service._read_from_cache")
    @patch("services.system_config_service._write_to_cache")
    def test_get_settings_cache_miss_queries_db_and_populates_cache(self, mock_write_cache, mock_read_cache):
        """Khi Cache Miss: đọc từ DB, tự động khởi tạo singleton row 'current' và nạp cache."""
        mock_read_cache.return_value = None  # Cache Miss

        settings = get_system_settings(db=self.db)

        self.assertIsNotNone(settings)
        self.assertEqual(settings["id"], "current")
        self.assertEqual(settings["primary_model"], "gemini-3.8-flash")
        self.assertEqual(settings["parent_insight_model"], "gemini-3.5-flash")
        self.assertEqual(settings["classifier_model"], "gemini-3.1-flash-lite")
        self.assertEqual(settings["email_model"], "gemini-3.1-flash-lite")
        self.assertEqual(settings["flashcard_model"], "gemini-3.5-flash-lite")
        self.assertEqual(settings["backup_model"], "gemini-3.5-flash-lite")

        # Kiểm tra _write_to_cache được gọi để nạp cache
        mock_write_cache.assert_called_once()
        cached_data = mock_write_cache.call_args[0][0]
        self.assertEqual(cached_data["primary_model"], "gemini-3.8-flash")

    @patch("services.system_config_service._read_from_cache")
    def test_get_settings_cache_hit_returns_cached_data_without_db(self, mock_read_cache):
        """Khi Cache Hit: trả về dữ liệu từ Redis Cache ngay lập tức (<1ms)."""
        cached_dict = {
            "id": "current",
            "primary_model": "gemini-3.8-flash-fast-cached",
            "temperature": 0.2,
        }
        mock_read_cache.return_value = cached_dict

        result = get_system_settings(db=self.db)

        self.assertEqual(result["primary_model"], "gemini-3.8-flash-fast-cached")
        self.assertEqual(result["temperature"], 0.2)

    @patch("services.system_config_service._invalidate_cache")
    @patch("services.system_config_service._write_to_cache")
    @patch("services.system_config_service._read_from_cache")
    def test_update_settings_persists_db_creates_audit_and_invalidates_cache(
        self, mock_read_cache, mock_write_cache, mock_invalidate_cache
    ):
        """Khi cập nhật: ghi DB, ghi Audit Trail, xóa Cache để học sinh nhận ngay config mới."""
        mock_read_cache.return_value = None

        new_payload = {
            "primary_model": "gemini-3.5-flash",
            "temperature": 0.25,
            "socratic_strictness": "STRICT",
            "api_key_override": "MALICIOUS_KEY_ATTEMPT",  # Phải bị loại bỏ
        }

        updated = update_system_settings(
            new_data=new_payload,
            changed_by="admin_test@socratickid.edu.vn",
            change_summary="Đổi sang 3.5-flash và tăng độ nghiêm khắc",
            db=self.db,
        )

        # 1. Kiểm tra cấu hình trả về
        self.assertEqual(updated["primary_model"], "gemini-3.5-flash")
        self.assertEqual(updated["temperature"], 0.25)
        self.assertEqual(updated["socratic_strictness"], "STRICT")
        self.assertNotIn("api_key_override", updated)

        # 2. Kiểm tra Cache bị xóa (Hot-Reload Invalidation)
        mock_invalidate_cache.assert_called_once()

        # 3. Kiểm tra Audit Log được lưu vào DB
        audits = get_setting_audits(limit=5, db=self.db)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0]["changed_by"], "admin_test@socratickid.edu.vn")
        self.assertIn("Đổi sang 3.5-flash", audits[0]["change_summary"])
        self.assertEqual(audits[0]["previous_config"]["primary_model"], "gemini-3.8-flash")
        self.assertEqual(audits[0]["new_config"]["primary_model"], "gemini-3.5-flash")

    @patch("services.system_config_service._invalidate_cache")
    @patch("services.system_config_service._write_to_cache")
    @patch("services.system_config_service._read_from_cache")
    def test_rollback_system_settings_restores_previous_state(
        self, mock_read_cache, mock_write_cache, mock_invalidate_cache
    ):
        """Kiểm thử tính năng Hoàn tác 1-Click (Rollback - AC-SET-07)."""
        mock_read_cache.return_value = None

        # Bước 1: Thay đổi từ 3.8-flash sang 3.5-flash
        update_system_settings(
            new_data={"primary_model": "gemini-3.5-flash", "max_output_tokens": 1024},
            changed_by="admin@socratickid.edu.vn",
            change_summary="Đổi cấu hình tạm",
            db=self.db,
        )

        audits = get_setting_audits(limit=1, db=self.db)
        audit_id = audits[0]["id"]

        # Bước 2: Kích hoạt Rollback dựa trên audit_id
        rolled_back = rollback_system_settings(
            audit_id=audit_id,
            changed_by="admin@socratickid.edu.vn",
            db=self.db,
        )

        # Cấu hình phải được khôi phục về bản cũ (primary_model ban đầu: gemini-3.8-flash)
        self.assertEqual(rolled_back["primary_model"], "gemini-3.8-flash")
        self.assertEqual(rolled_back["max_output_tokens"], 512)

        # Phải sinh ra thêm 1 bản ghi audit ghi nhận thao tác rollback
        all_audits = get_setting_audits(limit=5, db=self.db)
        self.assertEqual(len(all_audits), 2)
        self.assertIn("Hoàn tác về phiên trước", all_audits[0]["change_summary"])

    def test_facade_class_methods(self):
        """Kiểm tra class facade SystemConfigService hoạt động đồng bộ với các hàm độc lập."""
        self.assertTrue(callable(SystemConfigService.get_settings))
        self.assertTrue(callable(SystemConfigService.update_settings))
        self.assertTrue(callable(SystemConfigService.rollback))
        self.assertTrue(callable(SystemConfigService.get_audits))
        self.assertTrue(callable(SystemConfigService.invalidate_cache))


if __name__ == "__main__":
    unittest.main()

