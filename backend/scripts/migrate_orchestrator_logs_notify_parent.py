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
    US 8.1 - Task T8.7:
    Cập nhật bảng orchestrator_logs thêm trường notify_parent, parent_notified_at, user_id, session_id
    và tạo bảng parent_alert_logs để lưu lịch sử cảnh báo email cho phụ huynh.
    """
    print("=== BẮT ĐẦU MIGRATION: CẬP NHẬT orchestrator_logs VÀ TẠO parent_alert_logs ===")
    with engine.connect() as conn:
        # 1. Thêm các cột vào orchestrator_logs an toàn bằng ADD COLUMN IF NOT EXISTS
        conn.execute(text("ALTER TABLE orchestrator_logs ADD COLUMN IF NOT EXISTS notify_parent BOOLEAN NOT NULL DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE orchestrator_logs ADD COLUMN IF NOT EXISTS parent_notified_at TIMESTAMP WITH TIME ZONE;"))
        conn.execute(text("ALTER TABLE orchestrator_logs ADD COLUMN IF NOT EXISTS user_id VARCHAR;"))
        conn.execute(text("ALTER TABLE orchestrator_logs ADD COLUMN IF NOT EXISTS session_id VARCHAR;"))
        
        # 2. Tạo index tối ưu truy vấn worker quét log cần gửi trong 5 phút
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orchestrator_logs_notify_parent ON orchestrator_logs (notify_parent, created_at);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orchestrator_logs_user_id ON orchestrator_logs (user_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_orchestrator_logs_session_id ON orchestrator_logs (session_id);"))

        # 3. Tạo bảng parent_alert_logs để ghi vết lịch sử email cảnh báo học tập & ngôn từ
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS parent_alert_logs (
                id VARCHAR PRIMARY KEY,
                student_id VARCHAR NOT NULL,
                parent_id VARCHAR,
                alert_type VARCHAR NOT NULL,
                recipient_email VARCHAR NOT NULL,
                subject VARCHAR NOT NULL,
                email_body TEXT,
                trigger_reason VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_parent_alert_logs_student_created ON parent_alert_logs (student_id, created_at);"))
        conn.commit()
        print("[OK] Đã thực thi các lệnh ALTER TABLE và CREATE TABLE thành công.")

    # 4. Kiểm tra lại cấu trúc bảng orchestrator_logs
    inspector = inspect(engine)
    orch_cols = [col["name"] for col in inspector.get_columns("orchestrator_logs")]
    print(f"[VERIFY] Các cột hiện tại trong bảng orchestrator_logs: {orch_cols}")
    assert "notify_parent" in orch_cols, "Lỗi: Không tìm thấy cột notify_parent sau migration!"
    assert "parent_notified_at" in orch_cols, "Lỗi: Không tìm thấy cột parent_notified_at sau migration!"
    assert "user_id" in orch_cols, "Lỗi: Không tìm thấy cột user_id sau migration!"
    assert "session_id" in orch_cols, "Lỗi: Không tìm thấy cột session_id sau migration!"

    # 5. Kiểm tra bảng parent_alert_logs
    tables = inspector.get_table_names()
    assert "parent_alert_logs" in tables, "Lỗi: Không tìm thấy bảng parent_alert_logs sau migration!"
    print("[SUCCESS] Migration T8.7 hoàn tất thành công 100%!")

if __name__ == "__main__":
    run_migration()
