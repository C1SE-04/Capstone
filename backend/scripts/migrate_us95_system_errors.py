"""
US 9.5 - Script Migration: Bảng system_errors (T9.16)
=====================================================
Tạo bảng system_errors và các index phục vụ:
  - Tra cứu sự cố hệ thống (CRASH_500, AI_TIMEOUT, SMTP_ERROR)
  - Tiếp nhận phản ánh lỗi học sinh (USER_REPORT)
  - Bộ lọc tìm kiếm nhanh theo user_id, user_email, error_type, severity, status

Chạy:
    python backend/scripts/migrate_us95_system_errors.py
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

SYSTEM_ERRORS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS system_errors (
    id              VARCHAR      PRIMARY KEY,
    error_code      VARCHAR(64)  NOT NULL,
    error_type      VARCHAR(32)  NOT NULL,
    severity        VARCHAR(16)  NOT NULL,
    message         TEXT         NOT NULL,
    stack_trace     TEXT,
    endpoint        VARCHAR(255),
    request_payload TEXT,
    user_id         VARCHAR      REFERENCES users(id) ON DELETE SET NULL,
    user_email      VARCHAR(255),
    status          VARCHAR(16)  NOT NULL DEFAULT 'OPEN',
    resolved_at     TIMESTAMPTZ,
    resolved_by     VARCHAR      REFERENCES users(id) ON DELETE SET NULL,
    resolved_note   TEXT,
    created_at      TIMESTAMPTZ  DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_system_errors_error_code ON system_errors (error_code);
CREATE INDEX IF NOT EXISTS ix_system_errors_error_type ON system_errors (error_type);
CREATE INDEX IF NOT EXISTS ix_system_errors_severity ON system_errors (severity);
CREATE INDEX IF NOT EXISTS ix_system_errors_status ON system_errors (status);
CREATE INDEX IF NOT EXISTS ix_system_errors_user_id ON system_errors (user_id);
CREATE INDEX IF NOT EXISTS ix_system_errors_user_email ON system_errors (user_email);
CREATE INDEX IF NOT EXISTS ix_system_errors_created_at ON system_errors (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_system_errors_status_created ON system_errors (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_system_errors_type_created ON system_errors (error_type, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_system_errors_severity_created ON system_errors (severity, created_at DESC);
"""


def run_migration():
    print("=" * 60)
    print("  US 9.5 Migration: Bảng system_errors (System Error & Incident Hub)")
    print("=" * 60)

    with engine.begin() as conn:
        print("[1/2] Tạo bảng system_errors và các index...")
        conn.execute(text(SYSTEM_ERRORS_TABLE_DDL))
        print("      ✓ Đã thực thi DDL thành công.")

    # Kiểm tra cấu trúc sau migration
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "system_errors" in tables, "Lỗi: Không tìm thấy bảng system_errors sau migration!"

    cols = [c["name"] for c in inspector.get_columns("system_errors")]
    print(f"[2/2] Kiểm tra các cột trong bảng system_errors: {cols}")
    assert "error_code" in cols
    assert "error_type" in cols
    assert "severity" in cols
    assert "stack_trace" in cols
    assert "status" in cols

    print()
    print("✅ Migration US 9.5 hoàn tất thành công 100%!")


if __name__ == "__main__":
    run_migration()
