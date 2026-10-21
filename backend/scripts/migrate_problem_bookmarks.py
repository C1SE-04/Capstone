# US 7.2 - Task T7.7: Migration — Tạo bảng problem_bookmarks (Sổ Tay Bài Toán Yêu Thích)
# Chạy script này MỘT LẦN để tạo bảng mới trên database Neon đang production.
#
# Cách chạy:
#   cd backend
#   python scripts/migrate_problem_bookmarks.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine


def run_migration():
    with engine.connect() as conn:
        # Kiểm tra bảng đã tồn tại chưa (tránh lỗi khi chạy lại)
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'problem_bookmarks';
        """))
        existing = result.fetchone()

        if existing:
            print("[SKIP] Table 'problem_bookmarks' already exists. Skipping migration.")
            return

        print("[MIGRATE] Creating table 'problem_bookmarks'...")
        conn.execute(text("""
            CREATE TABLE problem_bookmarks (
                id                VARCHAR PRIMARY KEY,
                student_id        VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_id        VARCHAR NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                problem_snapshot  TEXT,
                attachment_url    VARCHAR,
                chat_summary      TEXT,
                independence_score INTEGER,
                note              TEXT,
                created_at        TIMESTAMPTZ DEFAULT NOW()
            );
        """))

        # Index: mỗi học sinh chỉ bookmark 1 lần / session (UNIQUE)
        conn.execute(text("""
            CREATE UNIQUE INDEX ix_bookmarks_student_session
            ON problem_bookmarks (student_id, session_id);
        """))

        # Index: lấy bookmarks của 1 học sinh sort theo ngày mới nhất
        conn.execute(text("""
            CREATE INDEX ix_bookmarks_student_created
            ON problem_bookmarks (student_id, created_at);
        """))

        conn.commit()
        print("[OK] Table 'problem_bookmarks' created successfully!")
        print("[INFO] Columns: id, student_id, session_id, problem_snapshot,")
        print("       attachment_url, chat_summary, independence_score, note, created_at")
        print("[INFO] Indexes: UNIQUE(student_id, session_id), (student_id, created_at)")


if __name__ == "__main__":
    run_migration()
