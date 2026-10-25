"""
US 7.2 - Task T7.21 (va T7.12):
Migration & Toi uu hoa Index cho bang problem_bookmarks (So Tay Bai Toan Yeu Thich).
- Tao bang problem_bookmarks an toan (idempotent, IF NOT EXISTS).
- Toi uu hoa Index tra cuu:
    1. ix_bookmarks_student_session: UNIQUE (student_id, session_id) - Chong duplicate bookmark.
    2. ix_bookmarks_student_created: (student_id, created_at DESC) - Toi uu truy van So tay sap xep thoi gian moi nhat.

Cach chay:
    cd backend
    python scripts/migrate_problem_bookmarks.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from database import engine


def run_migration():
    print("=" * 60)
    print("[START] Migration: problem_bookmarks & Toi uu hoa Indexes")
    print("=" * 60)

    with engine.connect() as conn:
        # 1. Tao bang neu chua ton tai
        print("\n[1/3] Kiem tra / tao bang 'problem_bookmarks'...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS problem_bookmarks (
                id                 VARCHAR PRIMARY KEY,
                student_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                session_id         VARCHAR NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                problem_snapshot   TEXT,
                attachment_url     VARCHAR,
                chat_summary       TEXT,
                independence_score INTEGER,
                note               TEXT,
                created_at         TIMESTAMPTZ DEFAULT NOW()
            );
        """))
        print("  [OK] Bang 'problem_bookmarks' san sang.")

        # 2. Tao Unique Index (student_id, session_id)
        print("\n[2/3] Toi uu hoa Unique Index: ix_bookmarks_student_session...")
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_bookmarks_student_session
            ON problem_bookmarks (student_id, session_id);
        """))
        print("  [OK] Index 'ix_bookmarks_student_session' san sang.")

        # 3. Tao / Cap nhat Composite Index (student_id, created_at DESC)
        print("\n[3/3] Toi uu hoa Composite Index: ix_bookmarks_student_created (student_id, created_at DESC)...")
        idx_check = conn.execute(text("""
            SELECT indexdef FROM pg_indexes
            WHERE tablename = 'problem_bookmarks' AND indexname = 'ix_bookmarks_student_created';
        """)).fetchone()

        need_recreate = False
        if idx_check:
            indexdef = idx_check[0]
            if "DESC" not in indexdef.upper():
                print("  [INFO] Phat hien index cu chua co DESC, tien hanh cap nhat...")
                need_recreate = True

        if need_recreate:
            conn.execute(text("DROP INDEX IF EXISTS ix_bookmarks_student_created;"))
            conn.execute(text("""
                CREATE INDEX ix_bookmarks_student_created
                ON problem_bookmarks (student_id, created_at DESC);
            """))
            print("  [OK] Da tai tao 'ix_bookmarks_student_created' voi chieu DESC toi uu.")
        else:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_bookmarks_student_created
                ON problem_bookmarks (student_id, created_at DESC);
            """))
            print("  [OK] Index 'ix_bookmarks_student_created' (student_id, created_at DESC) da san sang.")

        conn.commit()

        # 4. Xac nhan trang thai sau migration
        print("\n" + "=" * 60)
        print("[INFO] XAC NHAN TRANG THAI DATABASE (pg_indexes):")
        print("=" * 60)
        indexes = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'problem_bookmarks'
            ORDER BY indexname;
        """)).fetchall()
        for idx in indexes:
            print(f"  * {idx[0]}: {idx[1]}")

        print("\n[DONE] Migration hoan tat thanh cong 100%!")


if __name__ == "__main__":
    run_migration()
