"""
Migration: Tạo bảng parent_ai_insights và student_badges
US 7.3 (Task T7.8) + US 7.4 (Task T7.9)

Chạy 1 lần bằng lệnh:
    python scripts/migrate_ai_insights_badges.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text


def run_migration():
    with engine.connect() as conn:

        # ── Bảng parent_ai_insights ────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS parent_ai_insights (
                id                    VARCHAR PRIMARY KEY,
                student_id            VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                period_start          TIMESTAMPTZ NOT NULL,
                period_end            TIMESTAMPTZ NOT NULL,
                report_json           TEXT NOT NULL,
                avg_independence_score INTEGER,
                total_problems        INTEGER NOT NULL DEFAULT 0,
                is_fallback           BOOLEAN NOT NULL DEFAULT FALSE,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_ai_insights_student_created
                ON parent_ai_insights (student_id, created_at DESC);
        """))

        # ── Bảng student_badges ───────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS student_badges (
                id                  VARCHAR PRIMARY KEY,
                student_id          VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                badge_key           VARCHAR NOT NULL,
                badge_name          VARCHAR NOT NULL,
                badge_description   VARCHAR,
                category            VARCHAR NOT NULL,
                unlocked_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """))

        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_student_badges_unique
                ON student_badges (student_id, badge_key);
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_student_badges_student
                ON student_badges (student_id, unlocked_at DESC);
        """))

        conn.commit()
        print("✅ Migration hoàn thành: bảng parent_ai_insights và student_badges đã được tạo.")


if __name__ == "__main__":
    run_migration()
