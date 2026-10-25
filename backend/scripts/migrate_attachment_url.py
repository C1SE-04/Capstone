# US 6.4 - Task #173: Migration — thêm cột attachment_url vào bảng messages
# Chạy script này MỘT LẦN để cập nhật schema database Neon đang production.
# 
# Cách chạy:
#   cd backend
#   python scripts/migrate_attachment_url.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine

def run_migration():
    with engine.connect() as conn:
        # Kiem tra xem cot da ton tai chua (tranh loi khi chay lai)
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'messages'
              AND column_name = 'attachment_url';
        """))
        existing = result.fetchone()

        if existing:
            print("[SKIP] Column 'attachment_url' already exists in 'messages'. Skipping migration.")
            return

        print("[MIGRATE] Adding column 'attachment_url' to table 'messages'...")
        conn.execute(text("""
            ALTER TABLE messages
            ADD COLUMN attachment_url VARCHAR;
        """))
        conn.commit()
        print("[OK] Column 'attachment_url' added to table 'messages' successfully!")
        print("[INFO] This column stores the Cloudinary HTTPS URL for image attachments (nullable).")


if __name__ == "__main__":
    run_migration()
