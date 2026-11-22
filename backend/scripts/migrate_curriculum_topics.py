"""
US 8.4 - Task T8.23:
Migration script cho bang curriculum_topics (Chuong Trinh Hoc Linh Dong) tren Neon DB.
- Tao bang curriculum_topics (idempotent, IF NOT EXISTS).
- Tao cac chi muc toi uu hoa (Unique Index, Grade-Active Index, Chapter-Order Index).
- Tu dong nap du lieu mau khoi dau tu grade_curriculum.json (an toan voi ON CONFLICT DO NOTHING).

Cach chay:
    cd backend
    $env:PYTHONIOENCODING="utf-8"; python scripts/migrate_curriculum_topics.py
"""

import sys
import os
import json
import uuid

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
    print("[START] Migration: US 8.4 - Curriculum Topics Table (Neon DB)")
    print("=" * 60)

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Tao bang curriculum_topics
            print("\n[1/3] Kiem tra / tao bang 'curriculum_topics'...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS curriculum_topics (
                    id            VARCHAR PRIMARY KEY,
                    grade         INTEGER NOT NULL,
                    book_series   VARCHAR NOT NULL DEFAULT 'Kết nối tri thức',
                    semester      INTEGER,
                    chapter_name  VARCHAR NOT NULL,
                    topic_name    VARCHAR NOT NULL,
                    order_index   INTEGER NOT NULL DEFAULT 0,
                    school_year   VARCHAR DEFAULT '2024-2025',
                    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
                    source_url    VARCHAR,
                    description   TEXT,
                    created_at    TIMESTAMPTZ DEFAULT NOW(),
                    updated_at    TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            print("  [OK] Bang 'curriculum_topics' san sang.")

            # 2. Tao cac chi muc (Indexes)
            print("\n[2/3] Tao cac indexes toi uu hoa...")
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_curriculum_unique_topic
                ON curriculum_topics (grade, book_series, chapter_name, topic_name);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_curriculum_grade_active
                ON curriculum_topics (grade, is_active);
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_curriculum_grade_chapter_order
                ON curriculum_topics (grade, chapter_name, order_index);
            """))
            print("  [OK] Cac indexes san sang.")

            # 3. Seed du lieu khoi tao tu grade_curriculum.json (neu co)
            print("\n[3/3] Nap du lieu chuan khoi tao tu grade_curriculum.json...")
            json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents", "grade_curriculum.json")
            seed_count = 0

            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    curriculum_data = json.load(f)

                insert_stmt = text("""
                    INSERT INTO curriculum_topics (
                        id, grade, book_series, semester, chapter_name, topic_name, order_index, school_year, is_active
                    ) VALUES (
                        :id, :grade, :book_series, :semester, :chapter_name, :topic_name, :order_index, :school_year, :is_active
                    )
                    ON CONFLICT (grade, book_series, chapter_name, topic_name) DO NOTHING;
                """)

                for grade_str, topics in curriculum_data.items():
                    try:
                        g_int = int(grade_str)
                    except ValueError:
                        continue

                    for idx, topic in enumerate(topics):
                        # Bóc tách tên chương hoặc phân loại cơ bản
                        ch_name = "Chương trình trọng tâm"
                        if ":" in topic:
                            parts = topic.split(":", 1)
                            ch_name = parts[0].strip()

                        sem = 1 if idx < (len(topics) // 2) else 2

                        res = conn.execute(insert_stmt, {
                            "id": uuid.uuid4().hex,
                            "grade": g_int,
                            "book_series": "Kết nối tri thức",
                            "semester": sem,
                            "chapter_name": ch_name,
                            "topic_name": topic.strip(),
                            "order_index": idx + 1,
                            "school_year": "2024-2025",
                            "is_active": True,
                        })
                        if res.rowcount > 0:
                            seed_count += 1

                print(f"  [OK] Da nap {seed_count} chuyen de moi vao co so du lieu.")
            else:
                print("  [SKIP] Khong tim thay file grade_curriculum.json de seed.")

            trans.commit()
            print("\n" + "=" * 60)
            print("[SUCCESS] Migration curriculum_topics hoan tat thanh cong 100%!")
            print("=" * 60)
        except Exception as e:
            trans.rollback()
            print(f"\n[ERROR] Migration that bai: {e}")
            raise


if __name__ == "__main__":
    run_migration()
