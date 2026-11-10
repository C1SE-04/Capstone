"""
US 10.4 - Script Migration: Bảng Audit Feedback Logs (T10.4.0)
===================================================================
Tạo bảng audit_feedback_logs phục vụ Hệ Thống Tự Học & Tiến Hóa Mô Hình
(Self-Reflective Feedback Loop & Active Learning Pipeline with Human-in-the-Loop).

Bảng lưu trữ các câu hỏi của học sinh bị phân luồng sai kèm nhãn đề xuất từ Gemini
thông qua Giao thức Thẻ ẩn (Hidden Tag Protocol: <!-- AUDIT_AGENT: <AGENT> -->).

Các cột chính:
  - id              : SERIAL PRIMARY KEY
  - user_query      : TEXT (câu hỏi thực tế của học sinh)
  - predicted_agent : VARCHAR(64) (nhãn Orchestrator đoán sai ban đầu)
  - suggested_agent : VARCHAR(64) (nhãn Gemini đề xuất đúng)
  - status          : VARCHAR(20) (PENDING | APPROVED | REJECTED)
  - created_at      : TIMESTAMPTZ (thời điểm ghi nhận)

Chạy migration:
    python backend/scripts/migrate_audit_feedback_logs.py
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Thêm thư mục backend vào sys.path để import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database import engine


# ==============================================================================
# DDL: Bảng audit_feedback_logs
# Thiết kế chuẩn Idempotent: chạy nhiều lần không gây lỗi duplicate hay mất dữ liệu.
# ==============================================================================
_DDL_AUDIT_FEEDBACK_LOGS = """
CREATE TABLE IF NOT EXISTS audit_feedback_logs (
    id                  SERIAL          PRIMARY KEY,
    user_query          TEXT            NOT NULL,
    predicted_agent     VARCHAR(64)     NOT NULL,
    suggested_agent     VARCHAR(64)     NOT NULL,
    status              VARCHAR(20)     NOT NULL DEFAULT 'PENDING',
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT now(),

    -- Ràng buộc chỉ chấp nhận 3 trạng thái hợp lệ
    CONSTRAINT chk_audit_feedback_status 
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))
);

-- Bảo đảm schema evolution an toàn nếu bảng đã tồn tại từ trước
ALTER TABLE audit_feedback_logs ADD COLUMN IF NOT EXISTS user_query TEXT NOT NULL DEFAULT '';
ALTER TABLE audit_feedback_logs ADD COLUMN IF NOT EXISTS predicted_agent VARCHAR(64) NOT NULL DEFAULT '';
ALTER TABLE audit_feedback_logs ADD COLUMN IF NOT EXISTS suggested_agent VARCHAR(64) NOT NULL DEFAULT '';
ALTER TABLE audit_feedback_logs ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'PENDING';
ALTER TABLE audit_feedback_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();

-- 1. Composite Index phục vụ màn hình Tab 2 trang Giám Sát Agent (/admin/safety):
-- Lọc nhanh các bản ghi trạng thái PENDING sắp xếp giảm dần theo thời gian tạo
CREATE INDEX IF NOT EXISTS ix_audit_feedback_logs_status_created
    ON audit_feedback_logs (status, created_at DESC);

-- 2. Index phục vụ truy vấn phân tích lịch sử theo mốc thời gian
CREATE INDEX IF NOT EXISTS ix_audit_feedback_logs_created_at
    ON audit_feedback_logs (created_at DESC);
"""


def run_migration():
    print("=" * 70)
    print("  US 10.4 Migration: Bảng audit_feedback_logs (Active Learning Hub)")
    print("=" * 70)

    with engine.begin() as conn:
        print("\n[1/2] Thực thi DDL tạo bảng audit_feedback_logs & thiết lập Indexes ...")
        conn.execute(text(_DDL_AUDIT_FEEDBACK_LOGS))
        print("      ✓ Hoàn tất tạo bảng, ràng buộc CHECK và Composite Indexes.")

    # Kiểm tra xác thực cấu trúc sau khi migration
    print("\n[2/2] Xác thực cấu trúc bảng trên cơ sở dữ liệu ...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "audit_feedback_logs" in tables, "❌ Lỗi: Bảng 'audit_feedback_logs' không tồn tại sau migration!"
    
    columns = {c["name"]: c for c in inspector.get_columns("audit_feedback_logs")}
    required_cols = ["id", "user_query", "predicted_agent", "suggested_agent", "status", "created_at"]
    
    for col in required_cols:
        assert col in columns, f"❌ Lỗi: Thiếu cột bắt buộc '{col}' trong bảng audit_feedback_logs!"
        print(f"      • Cột '{col}': kiểu {columns[col]['type']}, nullable={columns[col]['nullable']}")

    # Kiểm tra danh sách Index
    indexes = [idx["name"] for idx in inspector.get_indexes("audit_feedback_logs")]
    print(f"\n      Danh sách Index hiện diện: {indexes}")
    assert "ix_audit_feedback_logs_status_created" in indexes, "❌ Lỗi: Thiếu index ix_audit_feedback_logs_status_created!"

    print("\n✅ Migration US 10.4 (Task T10.4.0) hoàn tất thành công 100%!")


if __name__ == "__main__":
    run_migration()

