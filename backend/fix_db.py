from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE session_stats ADD COLUMN hint_count INTEGER NOT NULL DEFAULT 0;"))
    conn.commit()
    print("Column added successfully!")
