"""
US 8.2: Migration script cho bookmark_playlists, bookmark_playlist_items và cot title tren problem_bookmarks.
- Them cot title vao bang problem_bookmarks (neu chua co).
- Tao bang bookmark_playlists.
- Tao bang bookmark_playlist_items.
- Tao indexes ho tro truy van toi uu.

Cach chay:
    cd backend
    python scripts/migrate_bookmark_playlists.py
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
    print("[START] Migration: US 8.2 - Bookmark Playlists & Problem Title")
    print("=" * 60)

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Them cot title vao bang problem_bookmarks
            print("\n[1/4] Kiem tra / them cot 'title' vao 'problem_bookmarks'...")
            conn.execute(text("""
                ALTER TABLE problem_bookmarks
                ADD COLUMN IF NOT EXISTS title VARCHAR;
            """))
            print("  [OK] Cot 'title' tren 'problem_bookmarks' san sang.")

            # 2. Tao bang bookmark_playlists
            print("\n[2/4] Kiem tra / tao bang 'bookmark_playlists'...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bookmark_playlists (
                    id                 VARCHAR PRIMARY KEY,
                    student_id         VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name               VARCHAR NOT NULL,
                    description        TEXT,
                    color              VARCHAR,
                    is_default         BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at         TIMESTAMPTZ DEFAULT NOW(),
                    updated_at         TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            print("  [OK] Bang 'bookmark_playlists' san sang.")

            # 3. Tao bang bookmark_playlist_items
            print("\n[3/4] Kiem tra / tao bang 'bookmark_playlist_items'...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS bookmark_playlist_items (
                    id                 VARCHAR PRIMARY KEY,
                    playlist_id        VARCHAR NOT NULL REFERENCES bookmark_playlists(id) ON DELETE CASCADE,
                    bookmark_id        VARCHAR NOT NULL REFERENCES problem_bookmarks(id) ON DELETE CASCADE,
                    position           INTEGER NOT NULL DEFAULT 0,
                    added_at           TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            print("  [OK] Bang 'bookmark_playlist_items' san sang.")

            # 4. Tao indexes toi uu hoa
            print("\n[4/4] Tao cac indexes toi uu hoa...")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_bookmark_playlists_student_created
                ON bookmark_playlists (student_id, created_at DESC);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_bookmark_playlists_student_name
                ON bookmark_playlists (student_id, name);
            """))
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_playlist_items_unique
                ON bookmark_playlist_items (playlist_id, bookmark_id);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_playlist_items_playlist
                ON bookmark_playlist_items (playlist_id, added_at DESC);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_playlist_items_bookmark
                ON bookmark_playlist_items (bookmark_id);
            """))
            print("  [OK] Cac indexes san sang.")

            trans.commit()
            print("\n" + "=" * 60)
            print("[SUCCESS] Migration hoan tat thanh cong 100%!")
            print("=" * 60)
        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Migration that bai: {e}")
            raise


if __name__ == "__main__":
    run_migration()
