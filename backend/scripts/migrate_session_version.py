"""
Script Migration cho Task T6.10 (US 6.2):
Thêm trường session_version (INTEGER, DEFAULT 1, NOT NULL) vào bảng 'users'.
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm thư mục backend vào python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text, inspect

def run_migration():
    print("=== BẮT ĐẦU MIGRATION: THÊM CỘT session_version VÀO BẢNG users ===")
    with engine.connect() as conn:
        # 1. Thêm cột session_version nếu chưa có
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS session_version INTEGER DEFAULT 1 NOT NULL;"
        ))
        
        # 2. Cập nhật các bản ghi cũ nếu bị NULL (phòng ngừa)
        conn.execute(text(
            "UPDATE users SET session_version = 1 WHERE session_version IS NULL;"
        ))
        
        conn.commit()
        print("[OK] Đã thực thi ALTER TABLE users ADD COLUMN session_version thành công.")

    # 3. Kiểm tra lại cấu trúc bảng
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("users")]
    print(f"[VERIFY] Danh sách các cột hiện tại trong bảng users: {columns}")
    assert "session_version" in columns, "Lỗi: Không tìm thấy cột session_version sau migration!"
    print("[SUCCESS] Migration hoàn tất thành công 100%!")

if __name__ == "__main__":
    run_migration()
