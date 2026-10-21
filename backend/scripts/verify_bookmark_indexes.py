import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def check_status():
    with engine.connect() as conn:
        # Check table
        r = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='problem_bookmarks'")).fetchone()
        print("Table problem_bookmarks exists:", r is not None)
        
        # Check columns
        if r:
            cols = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='problem_bookmarks' ORDER BY ordinal_position")).fetchall()
            print("Columns:", [(c[0], c[1]) for c in cols])
        
        # Check indexes
        indexes = conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename='problem_bookmarks'")).fetchall()
        print(f"Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f" - {idx[0]}: {idx[1]}")

        # Recreate index with created_at DESC to test optimization
        print("\n--- RECREATING INDEX WITH DESC ---")
        conn.execute(text("DROP INDEX IF EXISTS ix_bookmarks_student_created;"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bookmarks_student_created ON problem_bookmarks (student_id, created_at DESC);"))
        conn.commit()

        # Check indexes again
        indexes = conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename='problem_bookmarks'")).fetchall()
        print(f"Found {len(indexes)} index(es):")
        for idx in indexes:
            print(f" - {idx[0]}: {idx[1]}")

        # Test EXPLAIN ANALYZE on Sổ tay bookmark query
        print("\n--- EXPLAIN QUERY PLAN (Index Scan) ---")
        conn.execute(text("SET enable_bitmapscan = off;"))
        explain_query = text("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT * FROM problem_bookmarks
            WHERE student_id = 'test_student_id'
            ORDER BY created_at DESC
            LIMIT 10;
        """)
        plan_rows = conn.execute(explain_query).fetchall()
        for p in plan_rows:
            print(p[0])



if __name__ == "__main__":
    check_status()

