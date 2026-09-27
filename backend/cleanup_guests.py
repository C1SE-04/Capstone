import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def cleanup_old_guest_sessions():
    db: Session = SessionLocal()
    try:
        # Thời điểm 24h trước
        threshold_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        
        # Tìm tất cả các session thuộc về guest-user-id và cũ hơn 24h
        old_guest_sessions = db.query(models.Session).filter(
            models.Session.user_id == "guest-user-id",
            models.Session.created_at < threshold_time
        ).all()

        deleted_count = 0
        for session in old_guest_sessions:
            # Xoá các Message thuộc về Session này trước (nếu DB không cấu hình cascade)
            db.query(models.Message).filter(models.Message.session_id == session.id).delete()
            # Xoá Session
            db.delete(session)
            deleted_count += 1
            
        db.commit()
        print(f"✅ Đã dọn dẹp {deleted_count} phòng chat rác của Guest (cũ hơn 24h).")
    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi dọn dẹp: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("🧹 Đang chạy tiến trình dọn dẹp DB...")
    cleanup_old_guest_sessions()
