"""
US 10.3 - Script Migration: Hệ Thống Cài Đặt Admin Hub (T10.3.0)
===================================================================
Tạo 2 bảng phục vụ Admin Settings Hub:
  1. system_settings        – Lưu cấu hình hệ thống duy nhất (Singleton Row: id = 'current')
                             Bao gồm 6 cột model AI cho 6 phân hệ, tham số sư phạm, rate limit, mock month.
                             BẢO MẬT: XÓA hoàn toàn api_key_override & multi_key_pool khỏi DDL.
  2. system_setting_audits  – Nhật ký lịch sử thay đổi cấu hình (Audit Trail & Rollback 1-Click)

Chạy:
    python backend/scripts/migrate_system_settings.py
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database import engine


# ==============================================================================
# Bảng 1: system_settings
# Singleton Row (id = 'current') lưu trữ toàn bộ cấu hình hoạt động của SocraticKid.
#
# 6 Dropdown Model tương ứng 6 phân hệ:
#   - primary_model        : Chat Socratic (GEMINI_CHAT_MODEL) -> gemini-3.8-flash
#   - parent_insight_model : Báo Cáo Phụ Huynh (GEMINI_INSIGHT_MODEL) -> gemini-3.5-flash
#   - classifier_model     : Phân Loại SGK (GEMINI_CLASSIFIER_MODEL) -> gemini-3.1-flash-lite
#   - email_model          : Email Cảnh Báo (GEMINI_EMAIL_MODEL) -> gemini-3.1-flash-lite
#   - flashcard_model      : Flashcard & Bookmark (GEMINI_FLASHCARD_MODEL) -> gemini-3.5-flash-lite
#   - backup_model         : Dự Phòng Failover (GEMINI_BACKUP_MODEL) -> gemini-3.5-flash-lite
#
# BẢO MẬT: TUYỆT ĐỐI KHÔNG lưu API Key vào DB. api_key_override và multi_key_pool
# đã bị loại bỏ hoàn toàn khỏi schema.
# ==============================================================================
_DDL_SYSTEM_SETTINGS = """
CREATE TABLE IF NOT EXISTS system_settings (
    id                      VARCHAR(32)     PRIMARY KEY DEFAULT 'current',

    -- 6 Cột Model AI cho 6 phân hệ (US 10.3)
    primary_model           VARCHAR(64)     NOT NULL DEFAULT 'gemini-3.8-flash',
    parent_insight_model    VARCHAR(64)     NOT NULL DEFAULT 'gemini-3.5-flash',
    classifier_model        VARCHAR(64)     NOT NULL DEFAULT 'gemini-3.1-flash-lite',
    email_model             VARCHAR(64)     NOT NULL DEFAULT 'gemini-3.1-flash-lite',
    flashcard_model         VARCHAR(64)     NOT NULL DEFAULT 'gemini-3.5-flash-lite',
    backup_model            VARCHAR(64)     NOT NULL DEFAULT 'gemini-3.5-flash-lite',

    -- Tham số Sinh văn bản (Generation Config)
    temperature             NUMERIC(3, 2)   NOT NULL DEFAULT 0.35,
    top_p                   NUMERIC(3, 2)   NOT NULL DEFAULT 0.90,
    max_output_tokens       INTEGER         NOT NULL DEFAULT 512,

    -- Tham số Sư phạm & An toàn (Pedagogical & Safety)
    socratic_strictness     VARCHAR(20)     NOT NULL DEFAULT 'BALANCED',
    enable_math_reviewer    BOOLEAN         NOT NULL DEFAULT TRUE,
    enable_vision_support   BOOLEAN         NOT NULL DEFAULT TRUE,
    safety_threshold        VARCHAR(32)     NOT NULL DEFAULT 'BLOCK_MEDIUM_AND_ABOVE',
    enable_parent_alert     BOOLEAN         NOT NULL DEFAULT TRUE,

    -- Giới hạn Tần suất (Rate Limiting - tin / 5 phút)
    guest_rate_limit        INTEGER         NOT NULL DEFAULT 10,
    student_rate_limit      INTEGER         NOT NULL DEFAULT 30,

    -- Giả lập Thời gian Nghiệm thu (US 9.3 Mock Curriculum Month: NULL = giờ thực, 1-12 = mock tháng)
    mock_curriculum_month   INTEGER,

    -- Thông tin quản trị & Môi trường
    system_version          VARCHAR(32)     NOT NULL DEFAULT 'v1.7.0',
    environment             VARCHAR(32)     NOT NULL DEFAULT 'Production (Neon + Vercel)',
    last_updated_at         TIMESTAMPTZ     NOT NULL DEFAULT now(),
    last_updated_by         VARCHAR(255)    NOT NULL DEFAULT 'admin@socratickid.edu.vn'
);

-- Bảo đảm schema evolution an toàn (nếu bảng đã tồn tại từ trước)
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS primary_model VARCHAR(64) NOT NULL DEFAULT 'gemini-3.8-flash';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS parent_insight_model VARCHAR(64) NOT NULL DEFAULT 'gemini-3.5-flash';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS classifier_model VARCHAR(64) NOT NULL DEFAULT 'gemini-3.1-flash-lite';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS email_model VARCHAR(64) NOT NULL DEFAULT 'gemini-3.1-flash-lite';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS flashcard_model VARCHAR(64) NOT NULL DEFAULT 'gemini-3.5-flash-lite';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS backup_model VARCHAR(64) NOT NULL DEFAULT 'gemini-3.5-flash-lite';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS temperature NUMERIC(3, 2) NOT NULL DEFAULT 0.35;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS top_p NUMERIC(3, 2) NOT NULL DEFAULT 0.90;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS max_output_tokens INTEGER NOT NULL DEFAULT 512;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS socratic_strictness VARCHAR(20) NOT NULL DEFAULT 'BALANCED';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS enable_math_reviewer BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS enable_vision_support BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS safety_threshold VARCHAR(32) NOT NULL DEFAULT 'BLOCK_MEDIUM_AND_ABOVE';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS enable_parent_alert BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS guest_rate_limit INTEGER NOT NULL DEFAULT 10;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS student_rate_limit INTEGER NOT NULL DEFAULT 30;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS mock_curriculum_month INTEGER;
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS system_version VARCHAR(32) NOT NULL DEFAULT 'v1.7.0';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS environment VARCHAR(32) NOT NULL DEFAULT 'Production (Neon + Vercel)';
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS last_updated_by VARCHAR(255) NOT NULL DEFAULT 'admin@socratickid.edu.vn';

-- TUYỆT ĐỐI KHÔNG lưu API Key vào DB: Loại bỏ hoàn toàn api_key_override & multi_key_pool
ALTER TABLE system_settings DROP COLUMN IF EXISTS api_key_override;
ALTER TABLE system_settings DROP COLUMN IF EXISTS multi_key_pool;

-- Khởi tạo Singleton Row mặc định nếu chưa có
INSERT INTO system_settings (id) VALUES ('current')
ON CONFLICT (id) DO NOTHING;
"""


# ==============================================================================
# Bảng 2: system_setting_audits
# Lưu lịch sử mọi lần thay đổi cấu hình hệ thống (Audit Trail)
# Phục vụ tính năng Rollback 1-Click (AC-SET-07).
# ==============================================================================
_DDL_SYSTEM_SETTING_AUDITS = """
CREATE TABLE IF NOT EXISTS system_setting_audits (
    id                      VARCHAR(64)     PRIMARY KEY,
    changed_by              VARCHAR(255)    NOT NULL,
    change_summary          TEXT            NOT NULL,
    previous_config         JSONB           NOT NULL,
    new_config              JSONB           NOT NULL,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- Index phục vụ truy vấn lịch sử sắp xếp giảm dần theo thời gian
CREATE INDEX IF NOT EXISTS ix_setting_audits_created_at
    ON system_setting_audits (created_at DESC);
"""


def run_migration():
    print("=" * 65)
    print("  US 10.3 Migration: Hệ Thống Cài Đặt Admin Hub (T10.3.0)")
    print("=" * 65)

    with engine.begin() as conn:
        print("\n[1/2] Tạo bảng system_settings & nạp Singleton Row ('current') ...")
        conn.execute(text(_DDL_SYSTEM_SETTINGS))
        print("      ✓ Hoàn tất (6 cột model mới, XÓA api_key_override & multi_key_pool).")

        print("\n[2/2] Tạo bảng system_setting_audits ...")
        conn.execute(text(_DDL_SYSTEM_SETTING_AUDITS))
        print("      ✓ Hoàn tất (Audit Trail & Rollback index).")

    # Kiểm tra xác nhận cấu trúc sau migration
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required_tables = ["system_settings", "system_setting_audits"]
    for table in required_tables:
        assert table in tables, f"Lỗi: Bảng '{table}' không tồn tại sau migration!"
        cols = [c["name"] for c in inspector.get_columns(table)]
        print(f"\n      Cột của {table}: {cols}")

    # Xác nhận các cột bảo mật đã được xóa
    settings_cols = [c["name"] for c in inspector.get_columns("system_settings")]
    assert "api_key_override" not in settings_cols, "Lỗi bảo mật: api_key_override vẫn còn trong system_settings!"
    assert "multi_key_pool" not in settings_cols, "Lỗi bảo mật: multi_key_pool vẫn còn trong system_settings!"

    # Xác nhận 6 cột model hiện diện
    required_models = [
        "primary_model",
        "parent_insight_model",
        "classifier_model",
        "email_model",
        "flashcard_model",
        "backup_model",
    ]
    for m in required_models:
        assert m in settings_cols, f"Lỗi: Thiếu cột model '{m}' trong system_settings!"

    print("\n✅ Migration US 10.3 (T10.3.0) hoàn tất thành công!")


if __name__ == "__main__":
    run_migration()

