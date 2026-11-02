"""
US 9.1 - Script Migration an toàn (T9.0)
==========================================
Thực hiện:
  1. Thêm cột `username`       (VARCHAR, UNIQUE, nullable) vào bảng users.
  2. Thêm cột `email_verified` (BOOLEAN, default=false)   vào bảng users.
  3. Chuyển cột `email`        từ NOT NULL → NULL          trên bảng users.
  4. Sinh username duy nhất cho tất cả user cũ (chưa có username).
  5. Tạo bảng `email_otps` nếu chưa tồn tại.

Script này IDEMPOTENT — chạy lại nhiều lần không gây lỗi, mỗi bước
kiểm tra xem đã tồn tại chưa trước khi thực hiện.

Chạy:
    cd backend
    python scripts/migrate_us91_username_otp.py
"""

import sys
import os
import re

# Đảm bảo import được từ thư mục backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from sqlalchemy import text, inspect as sa_inspect
from database import engine

# ─── Hằng số ──────────────────────────────────────────────────────────────────

OTP_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS email_otps (
    id           VARCHAR      PRIMARY KEY,
    email        VARCHAR      NOT NULL,
    otp_code     VARCHAR(6)   NOT NULL,
    purpose      VARCHAR      NOT NULL DEFAULT 'PARENT_REGISTER',
    attempts     INTEGER      NOT NULL DEFAULT 0,
    expires_at   TIMESTAMPTZ  NOT NULL,
    is_used      BOOLEAN      NOT NULL DEFAULT false,
    last_sent_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_email_otps_email_purpose
    ON email_otps (email, purpose) WHERE is_used = false;
CREATE INDEX IF NOT EXISTS ix_email_otps_email
    ON email_otps (email);
"""


def _column_exists(conn, table: str, column: str) -> bool:
    """Kiểm tra cột đã tồn tại trong bảng chưa."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :tbl AND column_name = :col"
    ), {"tbl": table, "col": column})
    return result.fetchone() is not None


def _make_unique_username(base: str, existing: set) -> str:
    """
    Sinh username duy nhất từ base string (prefix email trước dấu @).
    Nếu trùng, thêm hậu tố số nguyên tăng dần: _2, _3, ...
    """
    # Chuẩn hóa: chỉ giữ chữ, số, dấu gạch dưới; tối đa 20 ký tự
    clean = re.sub(r"[^a-z0-9_]", "_", base.lower())[:20]
    if not clean or clean.startswith("_"):
        clean = "user" + clean

    candidate = clean
    suffix = 2
    while candidate in existing:
        suffix_str = f"_{suffix}"
        candidate = clean[:20 - len(suffix_str)] + suffix_str
        suffix += 1

    return candidate


def run_migration():
    print("=" * 60)
    print("  US 9.1 Migration: username + email_verified + email_otps")
    print("=" * 60)

    with engine.begin() as conn:

        # ── Bước 1: Thêm cột username ────────────────────────────────────────
        if not _column_exists(conn, "users", "username"):
            print("[1/5] Thêm cột users.username ...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN username VARCHAR"
            ))
            print("      ✓ Đã thêm cột username (nullable, chưa có unique constraint).")
        else:
            print("[1/5] Cột users.username đã tồn tại — bỏ qua.")

        # ── Bước 2: Thêm cột email_verified ──────────────────────────────────
        if not _column_exists(conn, "users", "email_verified"):
            print("[2/5] Thêm cột users.email_verified ...")
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false"
            ))
            print("      ✓ Đã thêm cột email_verified.")
        else:
            print("[2/5] Cột users.email_verified đã tồn tại — bỏ qua.")

        # ── Bước 3: Chuyển email từ NOT NULL → NULL ───────────────────────────
        print("[3/5] Chuyển users.email về nullable ...")
        conn.execute(text(
            "ALTER TABLE users ALTER COLUMN email DROP NOT NULL"
        ))
        print("      ✓ email hiện tại là nullable.")

        # ── Bước 4: Sinh username cho user cũ ────────────────────────────────
        print("[4/5] Sinh username cho các user cũ chưa có username ...")

        # Lấy tất cả username hiện có (để chống trùng)
        rows_existing = conn.execute(text(
            "SELECT username FROM users WHERE username IS NOT NULL"
        )).fetchall()
        existing_usernames: set = {r[0] for r in rows_existing}

        # Lấy các user chưa có username
        rows_no_username = conn.execute(text(
            "SELECT id, email, username FROM users WHERE username IS NULL"
        )).fetchall()

        updated = 0
        for row in rows_no_username:
            user_id, email, _ = row
            if email:
                base = email.split("@")[0]
            else:
                # Không có email (user bị import lạ) → dùng prefix id
                base = f"user_{user_id[:6]}"

            new_username = _make_unique_username(base, existing_usernames)
            existing_usernames.add(new_username)

            conn.execute(text(
                "UPDATE users SET username = :uname WHERE id = :uid"
            ), {"uname": new_username, "uid": user_id})
            updated += 1

        print(f"      ✓ Đã sinh username cho {updated} user cũ.")

        # Thêm UNIQUE constraint trên username sau khi đã điền đầy đủ
        # Kiểm tra index đã tồn tại chưa
        idx_exists = conn.execute(text(
            "SELECT 1 FROM pg_indexes WHERE tablename='users' AND indexname='ix_users_username'"
        )).fetchone()
        if not idx_exists:
            conn.execute(text(
                "CREATE UNIQUE INDEX ix_users_username ON users (username) WHERE username IS NOT NULL"
            ))
            print("      ✓ Đã thêm UNIQUE index trên users.username.")
        else:
            print("      ✓ UNIQUE index ix_users_username đã tồn tại — bỏ qua.")

        # ── Bước 5: Tạo bảng email_otps ──────────────────────────────────────
        print("[5/5] Tạo bảng email_otps ...")
        conn.execute(text(OTP_TABLE_DDL))
        print("      ✓ Bảng email_otps và các index đã sẵn sàng.")

    print()
    print("✅ Migration US 9.1 hoàn thành thành công!")
    print("   Tiếp theo: chạy pytest test/test_us91_username_otp.py để nghiệm thu.")


if __name__ == "__main__":
    run_migration()
