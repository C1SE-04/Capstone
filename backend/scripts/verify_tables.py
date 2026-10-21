import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    r1 = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='parent_ai_insights'")).scalar()
    r2 = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='student_badges'")).scalar()
    print('parent_ai_insights exists:', r1 > 0)
    print('student_badges exists:', r2 > 0)
