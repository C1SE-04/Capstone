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
    """
    US 8.3 - Task T8.18:
    Migration DB:
    1. Thêm cột google_id (VARCHAR, UNIQUE, INDEX).
    2. Thêm cột oauth_provider (VARCHAR) để đánh dấu nguồn xác thực (VD: 'google').
    3. Chuyển cột hashed_password sang NULLABLE (DROP NOT NULL) để hỗ trợ tài khoản đăng nhập OAuth không dùng password.
    """
    print("=== BẮT ĐẦU MIGRATION: GOOGLE OAUTH CHO BẢNG USERS ===")
    with engine.connect() as conn:
        # 1. Chuyển hashed_password thành nullable
        conn.execute(text("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;"))
        print("[OK] Đã cho phép hashed_password NULLABLE.")

        # 2. Thêm google_id
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR;"))
        print("[OK] Đã thêm cột google_id.")

        # 3. Thêm oauth_provider
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR;"))
        print("[OK] Đã thêm cột oauth_provider.")

        # 4. Tạo Unique Index cho google_id để tối ưu tra cứu và chống trùng lặp tài khoản Google
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id);"))
        print("[OK] Đã tạo index ix_users_google_id.")

        conn.commit()

    # 5. Kiểm tra lại cấu trúc bảng users
    inspector = inspect(engine)
    columns = {col["name"]: col for col in inspector.get_columns("users")}
    print(f"[VERIFY] Các cột hiện tại trong bảng users: {list(columns.keys())}")

    assert "google_id" in columns, "Lỗi: Không tìm thấy cột google_id sau migration!"
    assert "oauth_provider" in columns, "Lỗi: Không tìm thấy cột oauth_provider sau migration!"
    assert columns["hashed_password"]["nullable"] is True, "Lỗi: hashed_password vẫn chưa phải là nullable!"

    print("[SUCCESS] Migration T8.18 hoàn tất thành công 100%!")

if __name__ == "__main__":
    run_migration()
