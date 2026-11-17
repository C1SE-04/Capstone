"""
US 11.3 - Script Migration: Mở rộng bảng system_errors (Task T374)
===================================================================
Bổ sung 2 cột và index phục vụ tính năng Trợ Lý AI Chẩn Đoán Lỗi (RCA Cache):
  1. ai_diagnosis (JSONB / JSON): Lưu trữ kết quả phân tích có cấu trúc của Gemini AI.
  2. ai_diagnosed_at (TIMESTAMPTZ): Mốc thời gian AI hoàn tất chẩn đoán (UTC).
  3. ix_system_errors_ai_diagnosed_at: B-Tree Index tối ưu hóa truy vấn lọc/sắp xếp lỗi đã chẩn đoán.

Cách chạy:
    cd backend
    python scripts/migrate_system_errors_ai_diagnosis.py
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo import được module từ thư mục backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text, inspect
from database import engine

MIGRATION_DDL = """
DO $$
BEGIN
    -- 1. Thêm cột ai_diagnosis nếu chưa tồn tại
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'system_errors' AND column_name = 'ai_diagnosis'
    ) THEN
        ALTER TABLE system_errors ADD COLUMN ai_diagnosis JSONB DEFAULT NULL;
        RAISE NOTICE 'Đã thêm cột ai_diagnosis vào bảng system_errors.';
    ELSE
        RAISE NOTICE 'Cột ai_diagnosis đã tồn tại, bỏ qua.';
    END IF;

    -- 2. Thêm cột ai_diagnosed_at nếu chưa tồn tại
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'system_errors' AND column_name = 'ai_diagnosed_at'
    ) THEN
        ALTER TABLE system_errors ADD COLUMN ai_diagnosed_at TIMESTAMPTZ DEFAULT NULL;
        RAISE NOTICE 'Đã thêm cột ai_diagnosed_at vào bảng system_errors.';
    ELSE
        RAISE NOTICE 'Cột ai_diagnosed_at đã tồn tại, bỏ qua.';
    END IF;
END $$;

-- 3. Tạo Index cho cột ai_diagnosed_at để tối ưu hóa truy vấn lọc/sắp xếp sự cố
CREATE INDEX IF NOT EXISTS ix_system_errors_ai_diagnosed_at ON system_errors (ai_diagnosed_at DESC);
"""


def run_migration():
    print("=" * 65)
    print("  US 11.3 Migration: Mở rộng bảng system_errors (Task T374)")
    print("=" * 65)

    with engine.begin() as conn:
        print("[1/2] Đang thực thi DDL kiểm tra và bổ sung cột mới & Index...")
        conn.execute(text(MIGRATION_DDL))
        print("      ✓ Thực thi DDL thành công!")

    # Bước kiểm tra xác thực sau migration
    print("[2/2] Xác thực cấu trúc bảng system_errors sau migration...")
    inspector = inspect(engine)
    columns = {c["name"]: c for c in inspector.get_columns("system_errors")}

    assert "ai_diagnosis" in columns, "LỖI: Không tìm thấy cột 'ai_diagnosis' sau migration!"
    assert "ai_diagnosed_at" in columns, "LỖI: Không tìm thấy cột 'ai_diagnosed_at' sau migration!"

    diag_type = str(columns["ai_diagnosis"]["type"]).upper()
    time_type = str(columns["ai_diagnosed_at"]["type"]).upper()

    print(f"      ✓ Cột 'ai_diagnosis'    : Type = {diag_type}, Nullable = {columns['ai_diagnosis']['nullable']}")
    print(f"      ✓ Cột 'ai_diagnosed_at' : Type = {time_type}, Nullable = {columns['ai_diagnosed_at']['nullable']}")

    # Kiểm tra Index
    indexes = [idx["name"] for idx in inspector.get_indexes("system_errors")]
    has_index = "ix_system_errors_ai_diagnosed_at" in indexes
    print(f"      ✓ Index 'ix_system_errors_ai_diagnosed_at': {'TỒN TẠI' if has_index else 'CHƯA TỒN TẠI (hoặc tên tự động)'}")

    print()
    print("✅ MIGRATION HOÀN TẤT THÀNH CÔNG 100%! Bảng system_errors đã sẵn sàng cho US 11.3.")


if __name__ == "__main__":
    run_migration()
