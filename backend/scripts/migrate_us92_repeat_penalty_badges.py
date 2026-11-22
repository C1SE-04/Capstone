"""
US 9.2 - Script Migration an toàn (T9.6 & T9.7)
==============================================
Thực hiện:
  1. Thêm cột `repeat_count`   (INTEGER, default 1, not null) vào bảng independence_scores.
  2. Thêm cột `max_score`      (INTEGER, default 100, not null) vào bảng independence_scores.
  3. Thêm cột `repeat_warning` (TEXT, nullable) vào bảng independence_scores.
  4. Tạo bảng `user_unlocked_badges` (id, user_id, badge_id, unlocked_at) cùng các index.

Script này IDEMPOTENT — có thể chạy lại nhiều lần mà không gây lỗi.

Chạy:
    cd backend
    python scripts/migrate_us92_repeat_penalty_badges.py
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

BADGES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS user_unlocked_badges (
    id          VARCHAR     PRIMARY KEY,
    user_id     VARCHAR     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id    VARCHAR     NOT NULL,
    unlocked_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_user_unlocked_badges_user_badge
    ON user_unlocked_badges (user_id, badge_id);

CREATE INDEX IF NOT EXISTS ix_user_unlocked_badges_user
    ON user_unlocked_badges (user_id);

CREATE INDEX IF NOT EXISTS ix_user_unlocked_badges_badge
    ON user_unlocked_badges (badge_id);
"""


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :tbl AND column_name = :col"
        ),
        {"tbl": table, "col": column},
    )
    return result.fetchone() is not None


def run_migration():
    print("=" * 60)
    print("  US 9.2 Migration: Anti-Spam Repeat Penalty & User Badges")
    print("=" * 60)

    with engine.begin() as conn:
        # 1. Thêm repeat_count vào independence_scores
        if not _column_exists(conn, "independence_scores", "repeat_count"):
            print("[1/4] Thêm cột independence_scores.repeat_count ...")
            conn.execute(
                text("ALTER TABLE independence_scores ADD COLUMN repeat_count INTEGER DEFAULT 1 NOT NULL;")
            )
            print("      ✓ Đã thêm cột repeat_count.")
        else:
            print("[1/4] Cột repeat_count đã tồn tại — bỏ qua.")

        # 2. Thêm max_score vào independence_scores
        if not _column_exists(conn, "independence_scores", "max_score"):
            print("[2/4] Thêm cột independence_scores.max_score ...")
            conn.execute(
                text("ALTER TABLE independence_scores ADD COLUMN max_score INTEGER DEFAULT 100 NOT NULL;")
            )
            print("      ✓ Đã thêm cột max_score.")
        else:
            print("[2/4] Cột max_score đã tồn tại — bỏ qua.")

        # 3. Thêm repeat_warning vào independence_scores
        if not _column_exists(conn, "independence_scores", "repeat_warning"):
            print("[3/4] Thêm cột independence_scores.repeat_warning ...")
            conn.execute(
                text("ALTER TABLE independence_scores ADD COLUMN repeat_warning TEXT;")
            )
            print("      ✓ Đã thêm cột repeat_warning.")
        else:
            print("[3/4] Cột repeat_warning đã tồn tại — bỏ qua.")

        # 4. Tạo bảng user_unlocked_badges
        print("[4/4] Tạo bảng user_unlocked_badges & indexes ...")
        conn.execute(text(BADGES_TABLE_DDL))
        print("      ✓ Bảng user_unlocked_badges và indexes đã sẵn sàng.")

    # Kiểm tra cấu trúc sau migration
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("independence_scores")]
    assert "repeat_count" in cols, "Lỗi: Không tìm thấy cột repeat_count!"
    assert "max_score" in cols, "Lỗi: Không tìm thấy cột max_score!"
    assert "repeat_warning" in cols, "Lỗi: Không tìm thấy cột repeat_warning!"

    tables = inspector.get_table_names()
    assert "user_unlocked_badges" in tables, "Lỗi: Không tìm thấy bảng user_unlocked_badges!"

    print()
    print("✅ Migration US 9.2 hoàn tất thành công 100%!")


if __name__ == "__main__":
    run_migration()

