from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Thêm cột pairing_code vào bảng users (US 5.2)
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS pairing_code VARCHAR(6) UNIQUE;"))
    conn.commit()
    print("Column pairing_code added successfully to users table!")
