"""
Migration Script: Drop notification_email column from users table
==================================================================
Nghiệp vụ:
1. Gộp toàn bộ dữ liệu từ notification_email sang email (nếu email NULL và notification_email NOT NULL).
2. Xóa cột notification_email khỏi bảng users.
3. Xác minh cột notification_email đã được xóa thành công.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database import engine

def migrate():
    print("=== BẮT ĐẦU MIGRATION: XÓA CỘT notification_email KHỎI BẢNG users ===")
    
    with engine.begin() as conn:
        insp = inspect(conn)
        columns = [c["name"] for c in insp.get_columns("users")]
        
        if "notification_email" not in columns:
            print("[INFO] Cột notification_email không tồn tại hoặc đã được xóa trước đó. Bỏ qua.")
            return

        print("[1/2] Đồng bộ dữ liệu sang cột email nếu email đang NULL...")
        conn.execute(text("""
            UPDATE users 
            SET email = notification_email 
            WHERE email IS NULL AND notification_email IS NOT NULL;
        """))
        
        print("[2/2] Xóa cột notification_email...")
        conn.execute(text("""
            ALTER TABLE users DROP COLUMN IF EXISTS notification_email;
        """))
        print("[SUCCESS] Đã thực hiện DROP COLUMN notification_email.")

    # Xác minh lại
    with engine.connect() as conn:
        insp = inspect(conn)
        columns = [c["name"] for c in insp.get_columns("users")]
        assert "notification_email" not in columns, "Lỗi: Cột notification_email vẫn còn trong bảng users!"
        print("[VERIFIED] Xác nhận thành công: Cột notification_email đã hoàn toàn bị xóa khỏi bảng users.")

if __name__ == "__main__":
    migrate()

