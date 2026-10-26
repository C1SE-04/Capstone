import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm thư mục backend vào python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text, inspect

def run_migration():
    print("=== BẮT ĐẦU MIGRATION: THÊM CỘT DEDUPLICATION VÀO BẢNG independence_scores ===")
    with engine.connect() as conn:
        # 1. Thêm các cột
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS problem_text TEXT;"))
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS problem_hash VARCHAR(64);"))
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS category VARCHAR(32) DEFAULT 'NEW_TOPIC';"))
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS is_duplicate BOOLEAN DEFAULT FALSE NOT NULL;"))
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS gentle_reminder TEXT;"))
        
        # 2. Tạo index cho problem_hash để tăng tốc truy vấn deduplication
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_independence_student_hash ON independence_scores (student_id, problem_hash);"
        ))
        
        conn.commit()
        print("[OK] Đã thực thi các lệnh ALTER TABLE và CREATE INDEX thành công.")

    # 3. Kiểm tra lại cấu trúc bảng
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("independence_scores")]
    print(f"[VERIFY] Các cột hiện tại trong bảng independence_scores: {columns}")
    assert "problem_hash" in columns, "Lỗi: Không tìm thấy cột problem_hash sau migration!"
    assert "is_duplicate" in columns, "Lỗi: Không tìm thấy cột is_duplicate sau migration!"
    print("[SUCCESS] Migration T8.2 hoàn tất thành công 100%!")

if __name__ == "__main__":
    run_migration()