"""
Unit & Integration Tests for US 10.3 (Task T10.3.2)
Admin Settings Router: 8 Endpoints CRUD, Healthcheck, Models, Playground & Rollback
===================================================================================
Test suite covers:
  - T10.3.2: Endpoint 1: get_admin_settings() (Readonly masked key, 6 models, DB/Cache persistence)
  - T10.3.2: Endpoint 2: update_admin_settings() (Update settings, audit creation, hot-reloading)
  - T10.3.2: Endpoint 3: list_available_models() (List Google Gemini models with fallback)
  - T10.3.2: Endpoint 4: test_gemini_api_key() (Test Ping without saving key)
  - T10.3.2: Endpoint 5: get_system_health() (Real healthcheck of DB, Redis, Gemini, SMTP)
  - T10.3.2: Endpoint 6: test_prompt_playground() (Socratic prompt execution & token count)
  - T10.3.2: Endpoint 7: get_audit_history() (Audit trail query)
  - T10.3.2: Endpoint 8: rollback_setting_version() (1-Click rollback)
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base
from models import SystemSettings, SystemSettingAudit
import schemas
from routers.admin_settings import (
    get_admin_settings,
    update_admin_settings,
    list_available_models,
    test_gemini_api_key,
    get_system_health,
    test_prompt_playground,
    get_audit_history,
    rollback_setting_version,
)


class TestUS10_3_AdminSettingsRouter(unittest.TestCase):
    """Kiểm thử trực tiếp 8 hàm endpoint của router admin_settings.py."""

    def setUp(self):
        # Database SQLite in-memory cô lập
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(
            bind=self.engine,
            tables=[SystemSettings.__table__, SystemSettingAudit.__table__]
        )
        self.db = self.SessionLocal()

        self.admin_user = {
            "id": "admin_uuid_123",
            "username": "admin_master",
            "role": "ADMIN",
            "email": "admin@socratickid.edu.vn",
        }

        # Mock Redis trên service và router để cô lập test
        self.patcher_redis_srv = patch("services.system_config_service._get_sync_redis")
        self.mock_redis_srv = self.patcher_redis_srv.start()
        mock_r = MagicMock()
        mock_r.ping.return_value = True
        mock_r.get.return_value = None
        self.mock_redis_srv.return_value = mock_r

        self.patcher_cache_read = patch("services.system_config_service._read_from_cache", return_value=None)
        self.patcher_cache_read.start()

        self.patcher_cache_write = patch("services.system_config_service._write_to_cache")
        self.patcher_cache_write.start()

        self.patcher_cache_inv = patch("services.system_config_service._invalidate_cache")
        self.patcher_cache_inv.start()

    def tearDown(self):
        self.db.close()
        self.patcher_redis_srv.stop()
        self.patcher_cache_read.stop()
        self.patcher_cache_write.stop()
        self.patcher_cache_inv.stop()
        Base.metadata.drop_all(
            bind=self.engine,
            tables=[SystemSettings.__table__, SystemSettingAudit.__table__]
        )

    def test_01_get_admin_settings(self):
        """1. GET /admin/settings: Đọc cấu hình đầy đủ và trả về API Key masked."""
        res = get_admin_settings(db=self.db)
        self.assertEqual(res.id, "current")
        self.assertEqual(res.primary_model, "gemini-3.8-flash")
        self.assertEqual(res.parent_insight_model, "gemini-3.5-flash")
        self.assertEqual(res.classifier_model, "gemini-3.1-flash-lite")
        self.assertEqual(res.email_model, "gemini-3.1-flash-lite")
        self.assertEqual(res.flashcard_model, "gemini-3.5-flash-lite")
        self.assertEqual(res.backup_model, "gemini-3.5-flash-lite")
        self.assertIsNotNone(res.api_key_masked)
        self.assertTrue(res.api_key_masked.startswith("••••") or "Chưa cấu hình" in res.api_key_masked)

    def test_02_update_admin_settings(self):
        """2. PUT /admin/settings: Cập nhật cấu hình có ghi DB và Audit Trail."""
        payload = schemas.AdminSystemSettingsUpdate(
            primary_model="gemini-3.5-flash",
            temperature=0.25,
            socratic_strictness="STRICT",
            mock_curriculum_month=10,
        )

        res = update_admin_settings(
            body=payload,
            db=self.db,
            current_user=self.admin_user,
        )

        self.assertEqual(res.primary_model, "gemini-3.5-flash")
        self.assertEqual(res.temperature, 0.25)
        self.assertEqual(res.socratic_strictness, "STRICT")
        self.assertEqual(res.mock_curriculum_month, 10)

        # Kiểm tra audit log đã được tạo trong DB
        audits = get_audit_history(limit=5, db=self.db)
        self.assertEqual(len(audits), 1)
        self.assertIn("Đổi Chat Socratic Model sang gemini-3.5-flash", audits[0].change_summary)

    @patch("google.generativeai.list_models")
    @patch("google.generativeai.configure")
    def test_03_list_available_models(self, mock_configure, mock_list_models):
        """3. GET /admin/settings/models: Lấy danh sách các model khả dụng."""
        mock_model_1 = MagicMock()
        mock_model_1.name = "models/gemini-3.8-flash"
        mock_model_1.display_name = "Gemini 3.8 Flash"
        mock_model_1.description = "Newest Socratic model"
        mock_model_1.supported_generation_methods = ["generateContent"]

        mock_list_models.return_value = [mock_model_1]

        models = list_available_models()
        self.assertIsInstance(models, list)
        self.assertGreaterEqual(len(models), 1)
        names = [m.name for m in models]
        self.assertIn("gemini-3.8-flash", names)

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTest1234567890AbCd"})
    def test_04_test_gemini_api_key(self, mock_configure, mock_model_class):
        """4. POST /admin/settings/test-key: Ping đo latency và trả về key masked."""
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = MagicMock(text="Pong")
        mock_model_class.return_value = mock_instance

        res = test_gemini_api_key()
        self.assertTrue(res.success)
        self.assertGreater(res.latency_ms, 0)
        self.assertEqual(res.key_masked, "••••••••AbCd")

    @patch("socket.create_connection")
    @patch("google.generativeai.get_model")
    @patch("google.generativeai.configure")
    def test_05_get_system_health(self, mock_configure, mock_get_model, mock_socket):
        """5. GET /admin/settings/health: Healthcheck thật 4 dịch vụ."""
        mock_get_model.return_value = MagicMock()
        mock_socket.return_value = MagicMock()

        health = get_system_health(db=self.db)
        self.assertIn(health.overall_status, ["HEALTHY", "DEGRADED"])
        self.assertIn("neon_postgresql", health.services)
        self.assertIn("upstash_redis", health.services)
        self.assertIn("gemini_api", health.services)
        self.assertIn("smtp_email", health.services)
        self.assertEqual(health.services["neon_postgresql"].status, "ONLINE")

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    @patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSyTest1234567890AbCd"})
    def test_06_test_prompt_playground(self, mock_configure, mock_model_class):
        """6. POST /admin/settings/test-playground: Mini Playground thử nghiệm Socratic."""
        mock_response = MagicMock()
        mock_response.text = "Em hãy thử trừ cả hai vế cho 5 xem sao nhé!"
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=20,
            candidates_token_count=15,
        )
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_instance

        req = schemas.AdminPlaygroundRequest(
            prompt="x + 5 = 12",
            model_name="gemini-3.8-flash",
            temperature=0.3,
            socratic_strictness="BALANCED",
        )
        res = test_prompt_playground(body=req, db=self.db)
        self.assertIn("trừ cả hai vế", res.response_text)
        self.assertEqual(res.prompt_tokens, 20)
        self.assertEqual(res.completion_tokens, 15)
        self.assertEqual(res.model_used, "gemini-3.8-flash")

    def test_07_get_audit_history(self):
        """7. GET /admin/settings/audits: Truy vấn danh sách lịch sử thay đổi."""
        # Tạo 1 audit log trước
        update_admin_settings(
            body=schemas.AdminSystemSettingsUpdate(primary_model="gemini-3.5-flash"),
            db=self.db,
            current_user=self.admin_user,
        )

        audits = get_audit_history(limit=5, db=self.db)
        self.assertEqual(len(audits), 1)
        self.assertEqual(audits[0].changed_by, "admin@socratickid.edu.vn")

    def test_08_rollback_setting_version(self):
        """8. POST /admin/settings/rollback/{id}: Hoàn tác cấu hình 1-Click."""
        # Đổi cấu hình
        update_admin_settings(
            body=schemas.AdminSystemSettingsUpdate(primary_model="gemini-3.5-flash"),
            db=self.db,
            current_user=self.admin_user,
        )

        audits = get_audit_history(limit=1, db=self.db)
        audit_id = audits[0].id

        # Rollback
        restored = rollback_setting_version(
            audit_id=audit_id,
            db=self.db,
            current_user=self.admin_user,
        )

        # Cấu hình phải trở về gemini-3.8-flash ban đầu
        self.assertEqual(restored.primary_model, "gemini-3.8-flash")


if __name__ == "__main__":
    unittest.main()
