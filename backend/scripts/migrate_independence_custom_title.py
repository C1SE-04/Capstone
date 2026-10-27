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
    US 8.1 - Task T8.4:
    Thêm các cột lưu tên bài toán vào bảng independence_scores:
    - custom_title: Tên bài toán do học sinh tự đặt khi lưu vào Sổ tay.
    - friendly_parent_title: Tên chuẩn sư phạm do AI sinh ra ([Lớp X] [Chủ đề] – [Dạng toán]).
    """
    print("=== BẮT ĐẦU MIGRATION: THÊM CỘT custom_title & friendly_parent_title VÀO BẢNG independence_scores ===")
    with engine.connect() as conn:
        # 1. Thêm các cột an toàn bằng ADD COLUMN IF NOT EXISTS
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS custom_title VARCHAR;"))
        conn.execute(text("ALTER TABLE independence_scores ADD COLUMN IF NOT EXISTS friendly_parent_title VARCHAR;"))
        conn.commit()
        print("[OK] Đã thực thi các lệnh ALTER TABLE thành công.")

    # 2. Kiểm tra lại cấu trúc bảng
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("independence_scores")]
    print(f"[VERIFY] Các cột hiện tại trong bảng independence_scores: {columns}")
    assert "custom_title" in columns, "Lỗi: Không tìm thấy cột custom_title sau migration!"
    assert "friendly_parent_title" in columns, "Lỗi: Không tìm thấy cột friendly_parent_title sau migration!"
    print("[SUCCESS] Migration T8.4 hoàn tất thành công 100%!")

if __name__ == "__main__":
    run_migration()
