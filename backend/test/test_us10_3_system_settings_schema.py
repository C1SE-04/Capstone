"""
Unit Tests for US 10.3 (Task T10.3.0)
Admin Settings Hub: Database Schema & ORM Models
=================================================
Test suite covers:
  - T10.3.0: SystemSettings & SystemSettingAudit ORM models in backend/models.py
  - T10.3.0: 6 model columns corresponding to 6 subsystems with exact defaults
  - T10.3.0: Security constraint verification (NO api_key_override or multi_key_pool in DB)
  - T10.3.0: In-memory SQLite table creation, singleton row insertion, JSON audit serialization
  - T10.3.0: DDL script string verification in backend/scripts/migrate_system_settings.py
"""

import sys
import os
import unittest
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
from models import SystemSettings, SystemSettingAudit, Base
import scripts.migrate_system_settings as migration_module


class TestUS10_3_SystemSettingsSchema(unittest.TestCase):
    """Kiểm tra cấu trúc ORM models và kịch bản Migration của US 10.3 (T10.3.0)."""

    def setUp(self):
        # Tạo in-memory SQLite database phục vụ kiểm thử cô lập nhanh, không cần mạng
        self.engine = create_engine("sqlite:///:memory:")
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(
            bind=self.engine,
            tables=[SystemSettings.__table__, SystemSettingAudit.__table__]
        )
        self.session = self.Session()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(
            bind=self.engine,
            tables=[SystemSettings.__table__, SystemSettingAudit.__table__]
        )

    def test_system_settings_attributes_and_defaults(self):
        """Kiểm tra đầy đủ các thuộc tính và giá trị mặc định của SystemSettings."""
        setting = SystemSettings()
        self.session.add(setting)
        self.session.commit()

        # Singleton ID
        self.assertEqual(setting.id, "current")

        # 6 Model AI phân hệ
        self.assertEqual(setting.primary_model, "gemini-3.8-flash")
        self.assertEqual(setting.parent_insight_model, "gemini-3.5-flash")
        self.assertEqual(setting.classifier_model, "gemini-3.1-flash-lite")
        self.assertEqual(setting.email_model, "gemini-3.1-flash-lite")
        self.assertEqual(setting.flashcard_model, "gemini-3.5-flash-lite")
        self.assertEqual(setting.backup_model, "gemini-3.5-flash-lite")

        # Generation config
        self.assertEqual(float(setting.temperature), 0.35)
        self.assertEqual(float(setting.top_p), 0.90)
        self.assertEqual(setting.max_output_tokens, 512)

        # Pedagogical & Safety
        self.assertEqual(setting.socratic_strictness, "BALANCED")
        self.assertTrue(setting.enable_math_reviewer)
        self.assertTrue(setting.enable_vision_support)
        self.assertEqual(setting.safety_threshold, "BLOCK_MEDIUM_AND_ABOVE")
        self.assertTrue(setting.enable_parent_alert)

        # Rate Limiting
        self.assertEqual(setting.guest_rate_limit, 10)
        self.assertEqual(setting.student_rate_limit, 30)

        # Mock Curriculum Month
        self.assertIsNone(setting.mock_curriculum_month)

        # Metadata
        self.assertEqual(setting.system_version, "v1.7.0")
        self.assertEqual(setting.environment, "Production (Neon + Vercel)")
        self.assertEqual(setting.last_updated_by, "admin@socratickid.edu.vn")

    def test_security_api_key_not_in_db(self):
        """BẢO MẬT: Đảm bảo api_key_override và multi_key_pool không tồn tại trong model."""
        self.assertFalse(
            hasattr(SystemSettings, "api_key_override"),
            "Lỗi bảo mật: api_key_override không được phép tồn tại trong SystemSettings!"
        )
        self.assertFalse(
            hasattr(SystemSettings, "multi_key_pool"),
            "Lỗi bảo mật: multi_key_pool không được phép tồn tại trong SystemSettings!"
        )

        # Kiểm tra qua inspector của SQLite table
        inspector = inspect(self.engine)
        cols = {c["name"] for c in inspector.get_columns("system_settings")}
        self.assertNotIn("api_key_override", cols)
        self.assertNotIn("multi_key_pool", cols)

    def test_singleton_persistence_and_query(self):
        """Kiểm tra lưu trữ và truy vấn Singleton row trong database."""
        setting = SystemSettings(id="current")
        self.session.add(setting)
        self.session.commit()

        loaded = self.session.query(SystemSettings).filter_by(id="current").first()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.primary_model, "gemini-3.8-flash")
        self.assertEqual(loaded.parent_insight_model, "gemini-3.5-flash")
        self.assertEqual(loaded.classifier_model, "gemini-3.1-flash-lite")
        self.assertEqual(loaded.email_model, "gemini-3.1-flash-lite")
        self.assertEqual(loaded.flashcard_model, "gemini-3.5-flash-lite")
        self.assertEqual(loaded.backup_model, "gemini-3.5-flash-lite")

    def test_audit_log_persistence_with_json(self):
        """Kiểm tra bảng system_setting_audits lưu trữ đúng cấu trúc JSON."""
        audit = SystemSettingAudit(
            id="audit_test_001",
            changed_by="admin@socratickid.edu.vn",
            change_summary="Đổi Chat Socratic sang gemini-3.8-flash, nhiệt độ 0.25",
            previous_config={"primary_model": "gemini-3.5-flash", "temperature": 0.35},
            new_config={"primary_model": "gemini-3.8-flash", "temperature": 0.25},
        )
        self.session.add(audit)
        self.session.commit()

        loaded = self.session.query(SystemSettingAudit).filter_by(id="audit_test_001").first()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.changed_by, "admin@socratickid.edu.vn")
        self.assertEqual(loaded.new_config["primary_model"], "gemini-3.8-flash")
        self.assertEqual(loaded.previous_config["temperature"], 0.35)

    def test_migration_script_ddl_integrity(self):
        """Kiểm tra mã DDL trong file migrate_system_settings.py có đầy đủ các ràng buộc."""
        ddl_settings = migration_module._DDL_SYSTEM_SETTINGS
        ddl_audits = migration_module._DDL_SYSTEM_SETTING_AUDITS

        # Kiểm tra DDL system_settings
        self.assertIn("CREATE TABLE IF NOT EXISTS system_settings", ddl_settings)
        self.assertIn("primary_model", ddl_settings)
        self.assertIn("parent_insight_model", ddl_settings)
        self.assertIn("classifier_model", ddl_settings)
        self.assertIn("email_model", ddl_settings)
        self.assertIn("flashcard_model", ddl_settings)
        self.assertIn("backup_model", ddl_settings)

        # Kiểm tra lệnh DROP bảo mật
        self.assertIn("DROP COLUMN IF EXISTS api_key_override", ddl_settings)
        self.assertIn("DROP COLUMN IF EXISTS multi_key_pool", ddl_settings)

        # Kiểm tra khởi tạo Singleton
        self.assertIn("INSERT INTO system_settings (id) VALUES ('current')", ddl_settings)
        self.assertIn("ON CONFLICT (id) DO NOTHING", ddl_settings)

        # Kiểm tra DDL system_setting_audits
        self.assertIn("CREATE TABLE IF NOT EXISTS system_setting_audits", ddl_audits)
        self.assertIn("previous_config", ddl_audits)
        self.assertIn("new_config", ddl_audits)
        self.assertIn("ix_setting_audits_created_at", ddl_audits)


if __name__ == "__main__":
    unittest.main()
