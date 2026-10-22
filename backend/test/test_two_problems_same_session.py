import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup utf-8 encoding for stdout on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(".env")

from database import get_db
import models
import schemas
from routers.bookmarks import create_bookmark, list_bookmarks, get_bookmark

def run_test():
    db = next(get_db())
    student_id = f"test_student_{uuid.uuid4().hex[:8]}"
    session_id = f"test_sess_{uuid.uuid4().hex[:8]}"
    
    current_user = {
        "id": student_id,
        "role": "STUDENT",
        "email": "test@socratic.edu.vn",
    }
    
    try:
        # 1. Tao student user
        user = models.User(
            id=student_id,
            email=f"{student_id}@socratic.edu.vn",
            hashed_password="fakehashpassword123",
            role="STUDENT",
            grade=5,
        )
        db.add(user)
        db.commit()
        
        # 2. Tao session
        sess = models.Session(
            id=session_id,
            user_id=student_id,
            title="Luyen tap Hinh hoc va Dai so",
        )
        db.add(sess)
        db.commit()
        
        base_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        # --- BÀI TOÁN 1 ---
        t1_start = base_time + timedelta(minutes=1)
        m1 = models.Message(
            id=uuid.uuid4().hex,
            session_id=session_id,
            sender_type="USER",
            content="Bài 1: Tính diện tích hình tròn có bán kính r = 3",
            created_at=t1_start,
        )
        m2 = models.Message(
            id=uuid.uuid4().hex,
            session_id=session_id,
            sender_type="AGENT_TUTOR",
            content="Chào em, công thức diện tích hình tròn là S = pi * r^2. Em thay r = 3 vào nhé!",
            created_at=t1_start + timedelta(seconds=20),
        )
        m3 = models.Message(
            id=uuid.uuid4().hex,
            session_id=session_id,
            sender_type="USER",
            content="Dạ em tính ra S = 3.14 * 9 = 28.26 ạ",
            created_at=t1_start + timedelta(seconds=40),
        )
        t1_score = t1_start + timedelta(minutes=1)
        score1 = models.IndependenceScore(
            id=uuid.uuid4().hex,
            session_id=session_id,
            student_id=student_id,
            score=95,
            hints_used=0,
            not_understood_count=0,
            evaluation="XUAT_SAC",
            created_at=t1_score,
        )
        db.add_all([m1, m2, m3, score1])
        db.commit()
        
        # --- BÀI TOÁN 2 ---
        t2_start = t1_score + timedelta(minutes=2)
        m4 = models.Message(
            id=uuid.uuid4().hex,
            session_id=session_id,
            sender_type="USER",
            content="Bài 2: Giải phương trình 2x + 4 = 10",
            created_at=t2_start,
        )
        m5 = models.Message(
            id=uuid.uuid4().hex,
            session_id=session_id,
            sender_type="AGENT_TUTOR",
            content="Em thử chuyển số 4 sang vế bên phải đổi dấu thành gì nào?",
            created_at=t2_start + timedelta(seconds=15),
        )
        m6 = models.Message(
            id=uuid.uuid4().hex,
            session_id=session_id,
            sender_type="USER",
            content="Dạ 2x = 10 - 4 = 6 nên x = 3 ạ",
            created_at=t2_start + timedelta(seconds=30),
        )
        t2_score = t2_start + timedelta(minutes=1)
        score2 = models.IndependenceScore(
            id=uuid.uuid4().hex,
            session_id=session_id,
            student_id=student_id,
            score=80,
            hints_used=1,
            not_understood_count=0,
            evaluation="TOT",
            created_at=t2_score,
        )
        db.add_all([m4, m5, m6, score2])
        db.commit()
        
        print("[SETUP OK] Đã tạo session với 2 bài toán độc lập.")
        
        # --- TEST BƯỚC 1: Lưu Bài 1 vào Sổ tay ---
        req1 = schemas.BookmarkCreate(
            session_id=session_id,
            message_created_at=t1_score,
            note="Bài hình tròn rất dễ nhớ",
        )
        bm1 = create_bookmark(body=req1, current_user=current_user, db=db)
        print(f"[TEST 1 PASS] Lưu Bài 1 thành công: id={bm1.id}")
        assert bm1.problem_snapshot == "Bài 1: Tính diện tích hình tròn có bán kính r = 3", f"Snapshot sai: {bm1.problem_snapshot}"
        assert bm1.independence_score == 95, f"Score sai: {bm1.independence_score}"
        # Kiểm tra đối thoại của Bài 1: chỉ chứa các tin nhắn của Bài 1
        d1_contents = [d.content for d in bm1.dialogue_messages]
        assert "Bài 1: Tính diện tích hình tròn có bán kính r = 3" in d1_contents
        assert "Dạ em tính ra S = 3.14 * 9 = 28.26 ạ" in d1_contents
        assert "Bài 2: Giải phương trình 2x + 4 = 10" not in d1_contents, "Lỗi ranh giới: Bài 1 chứa tin nhắn của Bài 2!"
        print("[TEST 1 PASS] Ranh giới đối thoại Bài 1 hoàn toàn chuẩn xác!")
        
        # --- TEST BƯỚC 2: Lưu Bài 2 vào Sổ tay ---
        req2 = schemas.BookmarkCreate(
            session_id=session_id,
            message_created_at=t2_score,
            note="Bài đại số phương trình bậc nhất",
        )
        bm2 = create_bookmark(body=req2, current_user=current_user, db=db)
        print(f"[TEST 2 PASS] Lưu Bài 2 thành công: id={bm2.id}")
        assert bm2.id != bm1.id, "Lỗi: Không tạo được bookmark riêng cho bài 2!"
        assert bm2.problem_snapshot == "Bài 2: Giải phương trình 2x + 4 = 10", f"Snapshot sai: {bm2.problem_snapshot}"
        assert bm2.independence_score == 80, f"Score sai: {bm2.independence_score}"
        # Kiểm tra đối thoại của Bài 2: chỉ chứa các tin nhắn của Bài 2
        d2_contents = [d.content for d in bm2.dialogue_messages]
        assert "Bài 2: Giải phương trình 2x + 4 = 10" in d2_contents
        assert "Dạ 2x = 10 - 4 = 6 nên x = 3 ạ" in d2_contents
        assert "Bài 1: Tính diện tích hình tròn có bán kính r = 3" not in d2_contents, "Lỗi ranh giới: Bài 2 chứa tin nhắn của Bài 1!"
        print("[TEST 2 PASS] Ranh giới đối thoại Bài 2 hoàn toàn chuẩn xác!")
        
        # --- TEST BƯỚC 3: Lưu lại Bài 1 (Kiểm tra tính Idempotent) ---
        bm1_again = create_bookmark(body=req1, current_user=current_user, db=db)
        assert bm1_again.id == bm1.id, "Lỗi: Lưu lại Bài 1 không trả về đúng bookmark cũ!"
        print("[TEST 3 PASS] Tính Idempotent hoạt động hoàn hảo khi nhấn lưu lại cùng bài toán!")
        
        # --- TEST BƯỚC 4: Kiểm tra danh sách Sổ tay (GET /bookmarks) ---
        all_bookmarks = list_bookmarks(current_user=current_user, db=db)
        assert len(all_bookmarks) == 2, f"Kỳ vọng 2 bài trong Sổ tay, thực tế: {len(all_bookmarks)}"
        bm_titles = [b.problem_snapshot for b in all_bookmarks]
        assert "Bài 1: Tính diện tích hình tròn có bán kính r = 3" in bm_titles
        assert "Bài 2: Giải phương trình 2x + 4 = 10" in bm_titles
        print("[TEST 4 PASS] Sổ tay hiển thị đầy đủ cả 2 bài toán độc lập từ cùng 1 phiên chat!")
        
        print("\n========================================================")
        print("TẤT CẢ CÁC BÀI TEST ĐÃ VƯỢT QUA XUẤT SẮC 100%!")
        print("========================================================")
        
    finally:
        # Cleanup test data
        try:
            db.rollback()
            db.query(models.ProblemBookmark).filter(models.ProblemBookmark.student_id == student_id).delete()
            db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == student_id).delete()
            db.query(models.Message).filter(models.Message.session_id == session_id).delete()
            db.query(models.Session).filter(models.Session.id == session_id).delete()
            db.query(models.User).filter(models.User.id == student_id).delete()
            db.commit()
        except Exception:
            pass
        finally:
            db.close()

if __name__ == "__main__":
    run_test()
