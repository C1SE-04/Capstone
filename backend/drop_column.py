import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL found.")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS pairing_code;"))
        conn.commit()
        print("Dropped column pairing_code from users table.")
    except Exception as e:
        print(f"Error dropping column: {e}")
