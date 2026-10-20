# US 7.1 - Task T7.4 & T7.5: Unit & Integration Tests cho API /metrics/heatmap và /metrics/summary
# Kiểm tra:
# 1. GET /metrics/heatmap quét session_active_intervals 16-24 tuần chuẩn format GitHub
# 2. GET /metrics/summary tính toán 100% dữ liệu thật (completed_problems, streak, score, hours)
# 3. Phân quyền truy cập (STUDENT xem chính mình, MONITOR xem con liên kết, chặn xem trái phép)

import sys
import os
import uuid
from datetime import datetime, timedelta, timezone, date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import dependencies
import models
from database import SessionLocal

client = TestClient(app)

TEST_STUDENT_ID = "test-student-us71"
TEST_PARENT_ID = "test-parent-us71"
OTHER_STUDENT_ID = "test-other-student-us71"

current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}


def mock_get_current_user():
    return current_mock_user


app.dependency_overrides[dependencies.get_current_user] = mock_get_current_user


def cleanup_db(db):
    """Xóa dữ liệu test cũ để đảm bảo kết quả kiểm thử độc lập."""
    db.rollback()
    test_ids = [TEST_STUDENT_ID, TEST_PARENT_ID, OTHER_STUDENT_ID]
    db.query(models.SessionActiveInterval).filter(models.SessionActiveInterval.user_id.in_(test_ids)).delete(synchronize_session=False)
    db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id.in_(test_ids)).delete(synchronize_session=False)
    db.query(models.SessionStats).filter(
        models.SessionStats.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id.in_(test_ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.Session).filter(models.Session.user_id.in_(test_ids)).delete(synchronize_session=False)
    db.query(models.ParentStudentLink).filter(
        (models.ParentStudentLink.parent_id == TEST_PARENT_ID) |
        (models.ParentStudentLink.student_id.in_(test_ids))
    ).delete(synchronize_session=False)
    db.query(models.User).filter(models.User.id.in_(test_ids)).delete(synchronize_session=False)
    db.commit()


def setup_users(db):
    cleanup_db(db)
    student = models.User(
        id=TEST_STUDENT_ID,
        email="student_us71@socratickid.local",
        hashed_password="hash",
        role="STUDENT",
        grade=5,
    )
    parent = models.User(
        id=TEST_PARENT_ID,
        email="parent_us71@socratickid.local",
        hashed_password="hash",
        role="MONITOR",
    )
    other = models.User(
        id=OTHER_STUDENT_ID,
        email="other_us71@socratickid.local",
        hashed_password="hash",
        role="STUDENT",
        grade=6,
    )
    db.add_all([student, parent, other])
    db.commit()

    link = models.ParentStudentLink(
        parent_id=TEST_PARENT_ID,
        student_id=TEST_STUDENT_ID,
        student_nickname="Bé Bi",
    )
    db.add(link)
    db.commit()


def test_heatmap_api():
    print("\n--- TEST 1: Task T7.4 - GET /metrics/heatmap (16 - 24 tuần) ---")
    global current_mock_user
    current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}

    db = SessionLocal()
    try:
        setup_users(db)
        today = date.today()

        # Tạo session test
        session_obj = models.Session(
            id="session-us71-heatmap",
            user_id=TEST_STUDENT_ID,
            title="Session Toán Heatmap",
        )
        db.add(session_obj)
        db.commit()

        # Thêm 3 khoảng active intervals:
        # 1. Hôm nay: 35 phút (2100s) -> intensity = 2
        # 2. Hôm qua: 90 phút (5400s) -> intensity = 4
        # 3. 2 ngày trước: 15 phút (900s) -> intensity = 1
        t_today = datetime.now(timezone.utc)
        t_yesterday = t_today - timedelta(days=1)
        t_2days_ago = t_today - timedelta(days=2)

        iv1 = models.SessionActiveInterval(
            session_id=session_obj.id,
            user_id=TEST_STUDENT_ID,
            start_time=t_today,
            end_time=t_today + timedelta(minutes=35),
            active_seconds=2100,
        )
        iv2 = models.SessionActiveInterval(
            session_id=session_obj.id,
            user_id=TEST_STUDENT_ID,
            start_time=t_yesterday,
            end_time=t_yesterday + timedelta(minutes=90),
            active_seconds=5400,
        )
        iv3 = models.SessionActiveInterval(
            session_id=session_obj.id,
            user_id=TEST_STUDENT_ID,
            start_time=t_2days_ago,
            end_time=t_2days_ago + timedelta(minutes=15),
            active_seconds=900,
        )
        db.add_all([iv1, iv2, iv3])
        db.commit()

        # 1. Kiểm tra mặc định 24 tuần (168 ngày)
        res = client.get(f"/metrics/heatmap?student_id={TEST_STUDENT_ID}")
        assert res.status_code == 200, f"Error: {res.text}"
        data = res.json()
        assert data["student_id"] == TEST_STUDENT_ID
        assert data["weeks"] == 24
        assert data["days"] == 168
        assert len(data["data"]) == 168
        assert data["total_active_minutes"] == (35 + 90 + 15)
        assert data["total_study_hours"] == round((35 + 90 + 15) / 60, 1)

        # Kiểm tra chi tiết 3 ngày đã tạo
        day_map = {item["date"]: item for item in data["data"]}
        today_str = str(today)
        yesterday_str = str(today - timedelta(days=1))
        two_days_str = str(today - timedelta(days=2))

        assert day_map[today_str]["minutes"] == 35
        assert day_map[today_str]["intensity_level"] == 2

        assert day_map[yesterday_str]["minutes"] == 90
        assert day_map[yesterday_str]["intensity_level"] == 4

        assert day_map[two_days_str]["minutes"] == 15
        assert day_map[two_days_str]["intensity_level"] == 1

        print(f"[OK] 24 tuần (168 ngày) trả về chuẩn: tổng {data['total_active_minutes']}p ({data['total_study_hours']}h)")

        # 2. Kiểm tra tùy chọn 16 tuần (112 ngày)
        res16 = client.get(f"/metrics/heatmap?student_id={TEST_STUDENT_ID}&weeks=16")
        assert res16.status_code == 200
        data16 = res16.json()
        assert data16["weeks"] == 16
        assert data16["days"] == 112
        assert len(data16["data"]) == 112
        print(f"[OK] 16 tuần (112 ngày) trả về chính xác")

    finally:
        cleanup_db(db)
        db.close()


def test_summary_cards_api():
    print("\n--- TEST 2: Task T7.5 - GET /metrics/summary (Dữ liệu thật cho Summary Cards) ---")
    global current_mock_user
    current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}

    db = SessionLocal()
    try:
        setup_users(db)
        today = date.today()

        session_obj = models.Session(
            id="session-us71-summary",
            user_id=TEST_STUDENT_ID,
            title="Session Toán Summary",
        )
        db.add(session_obj)
        db.commit()

        # 1. Tạo 3 bài toán hoàn thành trong bảng independence_scores
        # Bài 1 (hôm nay): 90đ
        # Bài 2 (hôm qua): 80đ
        # Bài 3 (2 ngày trước): 70đ
        # Trung bình: (90 + 80 + 70)/3 = 80đ -> "Tự lập xuất sắc"
        now_dt = datetime.now(timezone.utc)
        score1 = models.IndependenceScore(
            session_id=session_obj.id,
            student_id=TEST_STUDENT_ID,
            score=90,
            hints_used=1,
            not_understood_count=0,
            evaluation="Tự lập xuất sắc",
            created_at=now_dt,
        )
        score2 = models.IndependenceScore(
            session_id=session_obj.id,
            student_id=TEST_STUDENT_ID,
            score=80,
            hints_used=2,
            not_understood_count=0,
            evaluation="Tự lập xuất sắc",
            created_at=now_dt - timedelta(days=1),
        )
        score3 = models.IndependenceScore(
            session_id=session_obj.id,
            student_id=TEST_STUDENT_ID,
            score=70,
            hints_used=3,
            not_understood_count=0,
            evaluation="Tự lập tốt",
            created_at=now_dt - timedelta(days=2),
        )

        # 2. Tạo khoảng thời gian active intervals cho 3 ngày
        # Hôm nay: 40p (2400s)
        # Hôm qua: 50p (3000s)
        # 2 ngày trước: 30p (1800s)
        # Tổng = 120p = 2.0h. Trung bình 3 ngày = 40p/ngày
        iv1 = models.SessionActiveInterval(
            session_id=session_obj.id,
            user_id=TEST_STUDENT_ID,
            start_time=now_dt,
            end_time=now_dt + timedelta(minutes=40),
            active_seconds=2400,
        )
        iv2 = models.SessionActiveInterval(
            session_id=session_obj.id,
            user_id=TEST_STUDENT_ID,
            start_time=now_dt - timedelta(days=1),
            end_time=now_dt - timedelta(days=1, minutes=-50),
            active_seconds=3000,
        )
        iv3 = models.SessionActiveInterval(
            session_id=session_obj.id,
            user_id=TEST_STUDENT_ID,
            start_time=now_dt - timedelta(days=2),
            end_time=now_dt - timedelta(days=2, minutes=-30),
            active_seconds=1800,
        )

        # Thêm 1 chuỗi ngày học cũ trong quá khứ (4 ngày liên tiếp cách đây 15 ngày) để test max_streak
        old_day = now_dt - timedelta(days=15)
        old_scores = []
        for d in range(4):
            old_scores.append(
                models.IndependenceScore(
                    session_id=session_obj.id,
                    student_id=TEST_STUDENT_ID,
                    score=85,
                    hints_used=1,
                    not_understood_count=0,
                    created_at=old_day - timedelta(days=d),
                )
            )

        db.add_all([score1, score2, score3, iv1, iv2, iv3] + old_scores)
        db.commit()

        # Gọi GET /metrics/summary?time_range=7d
        res = client.get(f"/metrics/summary?student_id={TEST_STUDENT_ID}&time_range=7d")
        assert res.status_code == 200, f"Summary error: {res.text}"
        data = res.json()

        assert data["completed_problems"] == 3
        assert data["completedProblems"] == 3
        assert data["independence_score"] == 80
        assert data["independenceScore"] == 80
        assert "Tự lập xuất sắc" in data["independence_level"]

        # Chuỗi ngày học liên tục:
        # Hôm nay, hôm qua, 2 ngày trước -> current_streak = 3
        # Đợt cũ 4 ngày liên tiếp -> max_streak = 4
        assert data["current_streak"] == 3
        assert data["currentStreak"] == 3
        assert data["max_streak"] == 4
        assert data["maxStreak"] == 4

        # Thời gian học:
        # 40 + 50 + 30 = 120p = 2.0h
        assert data["total_active_minutes"] == 120
        assert data["total_study_hours"] == 2.0
        assert data["totalStudyHours"] == 2.0
        assert data["avg_minutes_per_day"] == 40
        assert data["avgMinutesPerDay"] == 40

        print(f"[OK] Summary 7d: {data['completedProblems']} bài, điểm {data['independenceScore']}, streak {data['currentStreak']}/{data['maxStreak']}, {data['totalStudyHours']}h")

        # Kiểm tra time_range=30d bao gồm cả 4 bài cũ -> 3 + 4 = 7 bài
        res30 = client.get(f"/metrics/summary?student_id={TEST_STUDENT_ID}&time_range=30d")
        assert res30.status_code == 200
        data30 = res30.json()
        assert data30["completedProblems"] == 7
        print(f"[OK] Summary 30d: {data30['completedProblems']} bài hoàn thành")

    finally:
        cleanup_db(db)
        db.close()


def test_permission_access():
    print("\n--- TEST 3: Phân quyền truy cập Dashboard Phụ huynh ---")
    global current_mock_user

    db = SessionLocal()
    try:
        setup_users(db)

        # 1. Phụ huynh TEST_PARENT_ID đã liên kết với TEST_STUDENT_ID -> Được phép xem
        current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
        res_parent = client.get(f"/metrics/summary?student_id={TEST_STUDENT_ID}")
        assert res_parent.status_code == 200, f"Parent access failed: {res_parent.text}"
        print("[OK] Phụ huynh đã liên kết xem metrics của con thành công")

        # 2. Phụ huynh xem học sinh KHÁC chưa liên kết -> 403 Forbidden
        res_forbidden = client.get(f"/metrics/summary?student_id={OTHER_STUDENT_ID}")
        assert res_forbidden.status_code == 403
        print("[OK] Phụ huynh xem học sinh lạ bị chặn 403 Forbidden chính xác")

        # 3. Học sinh xem học sinh khác -> 403 Forbidden
        current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}
        res_student_forbidden = client.get(f"/metrics/summary?student_id={OTHER_STUDENT_ID}")
        assert res_student_forbidden.status_code == 403
        print("[OK] Học sinh xem chéo học sinh khác bị chặn 403 Forbidden chính xác")

    finally:
        cleanup_db(db)
        db.close()


if __name__ == "__main__":
    test_heatmap_api()
    test_summary_cards_api()
    test_permission_access()
    print("\n=== TẤT CẢ TEST CASES US 7.1 (T7.4 & T7.5) ĐÃ PASS 100%! ===")
