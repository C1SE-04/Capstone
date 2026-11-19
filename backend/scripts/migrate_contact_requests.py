"""
========================================================================================
File: backend/scripts/migrate_contact_requests.py
Sprint 11 - US 11.5: Feedback & Contact Hub
========================================================================================
Migration script tạo bảng 'contact_requests' trên PostgreSQL (NeonDB) và SQLite:
  - id: VARCHAR(64) PRIMARY KEY
  - full_name: VARCHAR(255) NOT NULL
  - email: VARCHAR(255) NOT NULL
  - role: VARCHAR(50) NOT NULL DEFAULT 'GUEST'
  - topic: VARCHAR(50) NOT NULL DEFAULT 'FEEDBACK'
  - content: TEXT NOT NULL
  - attachment_urls: JSON DEFAULT '[]'
  - recaptcha_score: NUMERIC(3, 2)
  - status: VARCHAR(50) NOT NULL DEFAULT 'PENDING'
  - created_at: TIMESTAMP WITH TIME ZONE DEFAULT NOW()

Cách chạy:
  python backend/scripts/migrate_contact_requests.py
========================================================================================
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import inspect, text
from database import engine, Base
import models


def migrate():
    print("=" * 80)
    print("▶ BẮT ĐẦU MIGRATION: TẠO BẢNG contact_requests (US 11.5 Contact Hub)")
    print("=" * 80)

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "contact_requests" in existing_tables:
        print("[INFO] Bảng 'contact_requests' đã tồn tại trong cơ sở dữ liệu.")
        columns = [col["name"] for col in inspector.get_columns("contact_requests")]
        print(f"[INFO] Các cột hiện có: {columns}")
    else:
        print("[INFO] Đang tạo mới bảng 'contact_requests'...")
        models.ContactRequest.__table__.create(bind=engine, checkfirst=True)
        print("[SUCCESS] Đã tạo bảng 'contact_requests' thành công!")

    # Kiểm tra lại sau khi tạo
    inspector_after = inspect(engine)
    columns_after = [col["name"] for col in inspector_after.get_columns("contact_requests")]
    print(f"[OK] Cấu trúc bảng 'contact_requests' hoàn chỉnh: {columns_after}")
    print("=" * 80)
    print("✔ MIGRATION HOÀN TẤT THÀNH CÔNG!")
    print("=" * 80)


if __name__ == "__main__":
    migrate()

