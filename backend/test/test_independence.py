import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import uuid
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
import dependencies
import models
from database import SessionLocal
from routers.independence import calculate_independence_score, save_independence_score

client = TestClient(app)

TEST_STUDENT_ID = "test-student-independence"


def mock_get_current_user():
    return {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}


app.dependency_overrides[dependencies.get_current_user] = mock_get_current_user


def setup_test_data(db):
    db.query(models.IndependenceScore).filter(
        models.IndependenceScore.student_id == TEST_STUDENT_ID
    ).delete()
    db.query(models.SessionStats).filter(
        models.SessionStats.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id == TEST_STUDENT_ID)
        )
    ).delete()
    db.query(models.Session).filter(models.Session.user_id == TEST_STUDENT_ID).delete()
    db.query(models.User).filter(models.User.id == TEST_STUDENT_ID).delete()
    db.commit()

    user = models.User(
        id=TEST_STUDENT_ID,
        email="test_independence@socratickid.local",
        hashed_password="hash",
        role="STUDENT",
        grade=5,
    )
    db.add(user)
    db.commit()


def test_independence_scoring_algorithm():
    print("\n--- TEST 1: Thuật toán tính điểm Independence (Barem nội bộ) ---")
    # 0 gợi ý: 100đ
    res0 = calculate_independence_score(hints_used=0, not_understood_count=0)
    assert res0["score"] == 100
    assert "Tự lập xuất sắc" in res0["level"]
    print(f"[OK] 0 gợi ý: {res0['score']}đ ({res0['level']})")

    # 1 gợi ý: 90đ
    res1 = calculate_independence_score(hints_used=1, not_understood_count=0)
    assert res1["score"] == 90
    print(f"[OK] 1 gợi ý: {res1['score']}đ")

    # 2 gợi ý: 80đ
    res2 = calculate_independence_score(hints_used=2, not_understood_count=0)
    assert res2["score"] == 80
    assert "Tự lập tốt" in res2["level"]
    print(f"[OK] 2 gợi ý: {res2['score']}đ ({res2['level']})")

    # AC2: Bấm 'Chưa hiểu' 3 lần, dùng 2 hints: 100 - (2*10) - (3*15) = 35đ
    res_ac2 = calculate_independence_score(hints_used=2, not_understood_count=3)
    assert res_ac2["score"] == 35
    assert "Cần thêm hỗ trợ" in res_ac2["level"]
    print(f"[OK] AC2: 2 hints + 3 lần Chưa hiểu = {res_ac2['score']}đ ({res_ac2['level']})")


def test_post_independence_api():
    print("\n--- TEST 2: Task #159 - POST /independence API ---")
    db = SessionLocal()
    try:
        setup_test_data(db)

        # Tạo session test
        session_id = uuid.uuid4().hex
        sess = models.Session(id=session_id, user_id=TEST_STUDENT_ID, title="Bài toán phân số")
        db.add(sess)
        db.commit()

        # Tạo stats giả lập: 1 hint, 0 chưa hiểu
        stats = models.SessionStats(
            session_id=session_id,
            consecutive_wrong_count=1,
            hint_count=1,
            not_understood_count=0,
        )
        db.add(stats)
        db.commit()

        # Gọi POST /independence
        res = client.post(
            "/independence",
            json={
                "session_id": session_id,
            },
        )
        assert res.status_code == 201, f"Status code: {res.status_code}, {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["data"]["score"] == 90
        assert data["data"]["student_id"] == TEST_STUDENT_ID
        assert data["data"]["hints_used"] == 1

        # Kiểm tra bản ghi trong DB
        db_record = (
            db.query(models.IndependenceScore)
            .filter(models.IndependenceScore.id == data["data"]["id"])
            .first()
        )
        assert db_record is not None
        assert db_record.score == 90
        print(f"[OK] POST /independence thành công, bản ghi đã lưu vào DB với điểm = {db_record.score}")

        # Kiểm tra stats đã được reset hint_count
        db.refresh(stats)
        assert stats.hint_count == 0
        assert stats.consecutive_wrong_count == 0
        print("[OK] SessionStats hint_count & consecutive_wrong_count đã được reset sau khi lưu điểm")
    finally:
        db.close()


def test_chat_comprehension_understood_flow():
    print("\n--- TEST 3: Task #160 - Sửa luồng 'Đã hiểu' trong API /chat/comprehension ---")
    db = SessionLocal()
    try:
        setup_test_data(db)

        session_id = uuid.uuid4().hex
        sess = models.Session(id=session_id, user_id=TEST_STUDENT_ID, title="Hình học không gian")
        db.add(sess)
        db.commit()

        # Giả lập học sinh giải bài với 2 gợi ý, 1 lần bấm chưa hiểu
        stats = models.SessionStats(
            session_id=session_id,
            consecutive_wrong_count=0,
            hint_count=2,
            not_understood_count=1,
        )
        db.add(stats)
        db.commit()

        # Học sinh bấm "Đã hiểu" -> POST /chat/comprehension với understood=True
        res = client.post(
            "/chat/comprehension",
            json={
                "session_id": session_id,
                "understood": True,
            },
        )
        assert res.status_code == 200, f"Status: {res.status_code}, {res.text}"
        res_data = res.json()
        assert res_data["status"] == "success"
        assert "independence" in res_data
        assert res_data["independence"] is not None

        # 100 - (2*10) - (1*15) = 65đ
        expected_score = 65
        assert res_data["independence"]["score"] == expected_score
        assert res_data["independence"]["hints_used"] == 2
        assert res_data["independence"]["not_understood_count"] == 1
        print(f"[OK] Luồng 'Đã hiểu' kích hoạt tính điểm: {res_data['independence']['score']}đ ({res_data['independence']['evaluation']})")

        # Kiểm tra bản ghi đã tồn tại trong DB
        db_score = (
            db.query(models.IndependenceScore)
            .filter(models.IndependenceScore.session_id == session_id)
            .first()
        )
        assert db_score is not None
        assert db_score.score == expected_score
        print(f"[OK] Bản ghi điểm Tự Lực đã được lưu vào DB (ID: {db_score.id})")

        # 4. Kiểm tra API GET /independence/summary
        summary_res = client.get(f"/independence/summary?student_id={TEST_STUDENT_ID}")
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["total_completed"] == 1
        assert summary_data["latest_score"] == expected_score
        assert summary_data["average_score"] == float(expected_score)
        print(f"[OK] GET /independence/summary: total={summary_data['total_completed']}, avg={summary_data['average_score']}")
    finally:
        # Dọn dẹp
        db.query(models.IndependenceScore).filter(
            models.IndependenceScore.student_id == TEST_STUDENT_ID
        ).delete()
        db.query(models.SessionStats).filter(
            models.SessionStats.session_id.in_(
                db.query(models.Session.id).filter(models.Session.user_id == TEST_STUDENT_ID)
            )
        ).delete()
        db.query(models.Session).filter(models.Session.user_id == TEST_STUDENT_ID).delete()
        db.query(models.User).filter(models.User.id == TEST_STUDENT_ID).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_independence_scoring_algorithm()
    test_post_independence_api()
    test_chat_comprehension_understood_flow()
    print("\nALL INDEPENDENCE TESTS (TASK #159 & #160) PASSED!")
