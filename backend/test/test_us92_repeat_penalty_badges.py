"""
US 9.2 - Test Suite: Anti-Spam Mastery & User Badges Sync
==========================================================
Kiểm thử nghiệm thu 100% 5 tiêu chí chấp nhận:
  [AC 9.2.1] Phạt điểm trần bài trùng: Lần 1 = 100đ, Lần 2 = 90đ, Lần 3 = 80đ.
  [AC 9.2.2] Bảo toàn điểm sàn 30đ: Không bao giờ giảm xuống dưới 30đ (kể cả giải lại 10 lần hay dùng quá nhiều gợi ý).
  [AC 9.2.3] Vẫn ghi nhận số bài hoàn thành: total_completed trên /independence/summary nhảy +1 đều đặn sau mỗi lần giải lại.
  [AC 9.2.4] Không bắn lại popup cúp/huy hiệu khi đổi máy: POST /api/user/badges/unlock trả về is_first_time=True lần đầu, is_first_time=False các lần sau.
  [AC 9.2.5] Đồng bộ kho huy hiệu & migrate: GET /api/user/badges trả về đầy đủ badge_ids đã lưu trong DB.

Chạy:
    python -m pytest test/test_us92_repeat_penalty_badges.py -v
"""

import sys
import os
import uuid
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import SessionLocal
import models
import dependencies
from routers.independence import calculate_independence_score, save_independence_score
from agents.independence_evaluator import evaluate_independence

client = TestClient(app)

TEST_USER_ID = f"test_user_us92_{uuid.uuid4().hex[:8]}"
TEST_SESSION_PREFIX = f"session_us92_{uuid.uuid4().hex[:6]}"


def mock_current_user():
    return {
        "id": TEST_USER_ID,
        "username": "student_us92",
        "email": f"{TEST_USER_ID}@socratickid.local",
        "role": "STUDENT",
        "grade": 5,
    }


app.dependency_overrides[dependencies.get_current_user] = mock_current_user


@pytest.fixture(autouse=True)
def ensure_auth_override():
    app.dependency_overrides[dependencies.get_current_user] = mock_current_user
    yield
    app.dependency_overrides[dependencies.get_current_user] = mock_current_user


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_user():
    """Tạo user test trước khi chạy và xóa sau khi hoàn tất."""
    db: Session = SessionLocal()
    try:
        user = models.User(
            id=TEST_USER_ID,
            username="student_us92",
            email=f"{TEST_USER_ID}@socratickid.local",
            hashed_password="mocked_password",
            role="STUDENT",
            grade=5,
        )
        db.add(user)
        db.commit()
        yield
    finally:
        # Cleanup
        db.query(models.UserUnlockedBadge).filter(models.UserUnlockedBadge.user_id == TEST_USER_ID).delete()
        db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == TEST_USER_ID).delete()
        db.query(models.SessionStats).filter(
            models.SessionStats.session_id.in_(
                db.query(models.Session.id).filter(models.Session.user_id == TEST_USER_ID)
            )
        ).delete()
        db.query(models.Session).filter(models.Session.user_id == TEST_USER_ID).delete()
        db.query(models.User).filter(models.User.id == TEST_USER_ID).delete()
        db.commit()
        db.close()


# ==============================================================================
# 1. AC 9.2.1: Phạt điểm trần bài trùng (100đ -> 90đ -> 80đ)
# ==============================================================================

def test_ac_921_algorithm_repeat_penalty():
    """Kiểm tra thuật toán calculate_independence_score áp dụng trần điểm chính xác."""
    # Lần 1: Bài mới -> tối đa 100đ, không có cảnh báo
    r1 = calculate_independence_score(hints_used=0, not_understood_count=0, repeat_count=1)
    assert r1["score"] == 100
    assert r1["max_score"] == 100
    assert r1["repeat_count"] == 1
    assert r1["is_repeat"] is False
    assert r1["repeat_warning"] is None

    # Lần 2: Giải lại lần 1 (0 hints) -> trần tối đa 90đ, có cảnh báo
    r2 = calculate_independence_score(hints_used=0, not_understood_count=0, repeat_count=2)
    assert r2["score"] == 90
    assert r2["max_score"] == 90
    assert r2["repeat_count"] == 2
    assert r2["is_repeat"] is True
    assert "90đ" in r2["repeat_warning"]

    # Lần 3: Giải lại lần 2 (0 hints) -> trần tối đa 80đ
    r3 = calculate_independence_score(hints_used=0, not_understood_count=0, repeat_count=3)
    assert r3["score"] == 80
    assert r3["max_score"] == 80
    assert r3["repeat_count"] == 3
    assert r3["is_repeat"] is True
    assert "80đ" in r3["repeat_warning"]


def test_ac_921_save_independence_score_reduces_ceiling():
    """
    [AC 9.2.1] Giải đi giải lại cùng 1 bài toán qua save_independence_score:
    Lần 1 = 100đ, Lần 2 = 90đ, Lần 3 = 80đ.
    """
    db: Session = SessionLocal()
    problem_text = "Tìm x biết 2x + 10 = 20"
    try:
        # Lần 1: Giải bài lần đầu
        s1 = models.Session(id=f"{TEST_SESSION_PREFIX}_1", user_id=TEST_USER_ID, title="Lần 1")
        db.add(s1)
        db.commit()

        rec1 = save_independence_score(
            db=db,
            session_id=s1.id,
            student_id=TEST_USER_ID,
            custom_hints=0,
            custom_not_understood=0,
            problem_text_input=problem_text,
        )
        assert rec1.score == 100
        assert rec1.max_score == 100
        assert rec1.repeat_count == 1
        assert rec1.is_duplicate is False
        assert rec1.repeat_warning is None

        # Lần 2: Giải lại bài cũ lần 1
        s2 = models.Session(id=f"{TEST_SESSION_PREFIX}_2", user_id=TEST_USER_ID, title="Lần 2")
        db.add(s2)
        db.commit()

        rec2 = save_independence_score(
            db=db,
            session_id=s2.id,
            student_id=TEST_USER_ID,
            custom_hints=0,
            custom_not_understood=0,
            problem_text_input=problem_text,
        )
        assert rec2.score == 90, f"Lần 2 phải đạt tối đa 90đ, thực tế: {rec2.score}"
        assert rec2.max_score == 90
        assert rec2.repeat_count == 2
        assert rec2.is_duplicate is True
        assert "90đ" in rec2.repeat_warning

        # Lần 3: Giải lại bài cũ lần 2
        s3 = models.Session(id=f"{TEST_SESSION_PREFIX}_3", user_id=TEST_USER_ID, title="Lần 3")
        db.add(s3)
        db.commit()

        rec3 = save_independence_score(
            db=db,
            session_id=s3.id,
            student_id=TEST_USER_ID,
            custom_hints=0,
            custom_not_understood=0,
            problem_text_input=problem_text,
        )
        assert rec3.score == 80, f"Lần 3 phải đạt tối đa 80đ, thực tế: {rec3.score}"
        assert rec3.max_score == 80
        assert rec3.repeat_count == 3
        assert rec3.is_duplicate is True
        assert "80đ" in rec3.repeat_warning
    finally:
        db.close()


# ==============================================================================
# 2. AC 9.2.2: Bảo toàn điểm sàn 30đ
# ==============================================================================

def test_ac_922_floor_score_preserved_on_repeated_spam():
    """
    [AC 9.2.2] Học sinh spam giải lại cùng 1 bài 10 lần liên tiếp:
    Điểm nhận được vẫn được giữ ở mức sàn 30đ, không bao giờ trừ về 0 hay điểm âm.
    """
    db: Session = SessionLocal()
    problem_text = "Tính chu vi hình vuông có cạnh bằng 5cm"
    try:
        # Giả lập học sinh giải lại bài lần thứ 10
        for i in range(1, 11):
            sid = f"{TEST_SESSION_PREFIX}_spam_{i}"
            sess = models.Session(id=sid, user_id=TEST_USER_ID, title=f"Spam {i}")
            db.add(sess)
            db.commit()

            rec = save_independence_score(
                db=db,
                session_id=sid,
                student_id=TEST_USER_ID,
                custom_hints=0,
                custom_not_understood=0,
                problem_text_input=problem_text,
            )
            if i >= 8:
                # Từ lần 8 trở đi, max_score đã chạm sàn 30đ: max(30, 100 - (8-1)*10) = 30
                assert rec.max_score == 30
                assert rec.score == 30
                assert rec.score >= 30, "Điểm không bao giờ được nhỏ hơn 30đ"
    finally:
        db.close()


def test_ac_922_evaluator_and_algorithm_sync_floor_30():
    """
    [AC 9.2.2] Đồng bộ barem điểm sàn 30đ giữa independence.py và independence_evaluator.py:
    Kể cả dùng 10 gợi ý + 10 lần chưa hiểu (điểm thô < 0), điểm trả về vẫn là 30đ.
    """
    # 1. Trong independence.py
    r_router = calculate_independence_score(hints_used=10, not_understood_count=10)
    assert r_router["score"] == 30, f"Điểm sàn trong independence.py phải là 30, thực tế: {r_router['score']}"

    # 2. Trong agents/independence_evaluator.py
    r_agent = evaluate_independence(hints_used=10, not_understood_count=10, solving_time_seconds=600)
    assert r_agent.score == 30, f"Điểm sàn trong independence_evaluator.py phải là 30, thực tế: {r_agent.score}"


# ==============================================================================
# 3. AC 9.2.3: Vẫn ghi nhận số bài hoàn thành (+1 đều đặn)
# ==============================================================================

def test_ac_923_total_completed_increments_for_repeated_problems():
    """
    [AC 9.2.3] Con số 'Tổng bài đã giải' trên /independence/summary vẫn nhảy +1 đều đặn
    kể cả bài giải lại lần 2, lần 3, lần 4.
    """
    db: Session = SessionLocal()
    unique_problem = f"Bài toán ôn tập cộng trừ phân số {uuid.uuid4().hex[:6]}"
    try:
        # Lấy số bài hoàn thành ban đầu
        res_before = client.get(f"/independence/summary?student_id={TEST_USER_ID}")
        assert res_before.status_code == 200
        count_before = res_before.json()["total_completed"]

        # Giải bài lần 1
        s1 = models.Session(id=f"{TEST_SESSION_PREFIX}_tc1", user_id=TEST_USER_ID, title="Lần 1")
        db.add(s1)
        db.commit()
        save_independence_score(db=db, session_id=s1.id, student_id=TEST_USER_ID, problem_text_input=unique_problem)

        res1 = client.get(f"/independence/summary?student_id={TEST_USER_ID}")
        assert res1.json()["total_completed"] == count_before + 1

        # Giải lại bài cũ lần 2
        s2 = models.Session(id=f"{TEST_SESSION_PREFIX}_tc2", user_id=TEST_USER_ID, title="Lần 2")
        db.add(s2)
        db.commit()
        save_independence_score(db=db, session_id=s2.id, student_id=TEST_USER_ID, problem_text_input=unique_problem)

        res2 = client.get(f"/independence/summary?student_id={TEST_USER_ID}")
        assert res2.json()["total_completed"] == count_before + 2, "Giải lại lần 2 vẫn phải +1 vào total_completed"

        # Giải lại bài cũ lần 3
        s3 = models.Session(id=f"{TEST_SESSION_PREFIX}_tc3", user_id=TEST_USER_ID, title="Lần 3")
        db.add(s3)
        db.commit()
        save_independence_score(db=db, session_id=s3.id, student_id=TEST_USER_ID, problem_text_input=unique_problem)

        res3 = client.get(f"/independence/summary?student_id={TEST_USER_ID}")
        assert res3.json()["total_completed"] == count_before + 3, "Giải lại lần 3 vẫn phải +1 vào total_completed"
    finally:
        db.close()


# ==============================================================================
# 4. AC 9.2.4 & AC 9.2.5: Đồng bộ Huy hiệu qua DB & Không bắn lại popup
# ==============================================================================

def test_ac_924_badge_unlock_first_time_and_prevent_duplicate_popups():
    """
    [AC 9.2.4]
    - Bước 1: Học sinh mở khóa huy hiệu 'independence_100' (Tự Lập Nhí) lần đầu
      -> Trả về is_first_time = True (bung modal).
    - Bước 2: Giả lập đăng nhập ở máy B / ẩn danh, giải bài tiếp đạt 100đ hoặc gọi unlock lại
      -> Trả về is_first_time = False (tuyệt đối KHÔNG bung popup chúc mừng lại).
    """
    badge_id = "independence_100"

    # Bước 1: Lần đầu tiên đạt huy hiệu
    resp1 = client.post("/api/user/badges/unlock", json={"badge_id": badge_id})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["success"] is True
    assert data1["is_first_time"] is True, "Lần đầu tiên mở khóa phải trả về is_first_time = True"
    assert badge_id in data1["newly_unlocked_ids"]
    assert badge_id in data1["unlocked_badge_ids"]

    # Bước 2: Lần 2 (đổi máy / tab ẩn danh gọi lại cùng huy hiệu)
    resp2 = client.post("/api/user/badges/unlock", json={"badge_id": badge_id})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    assert data2["is_first_time"] is False, "Lần 2 gọi lại phải trả về is_first_time = False để chặn popup"
    assert len(data2["newly_unlocked_ids"]) == 0
    assert badge_id in data2["unlocked_badge_ids"]

    # Alias endpoint không có prefix /api cũng hoạt động y hệt
    resp_alias = client.post("/user/badges/unlock", json={"badge_id": badge_id})
    assert resp_alias.status_code == 200
    assert resp_alias.json()["is_first_time"] is False


def test_ac_925_get_badges_and_batch_migration():
    """
    [AC 9.2.5]
    - Migrate danh sách huy hiệu từ localStorage lên DB qua badge_ids.
    - GET /api/user/badges trả về đầy đủ danh sách huy hiệu đã đạt.
    """
    # Migrate đồng thời 2 huy hiệu cũ từ localStorage: "streak_3" và "photo_solver"
    migrate_payload = {"badge_ids": ["streak_3", "photo_solver"]}
    res_migrate = client.post("/api/user/badges/unlock", json=migrate_payload)
    assert res_migrate.status_code == 200
    data_migrate = res_migrate.json()
    assert data_migrate["is_first_time"] is True
    assert "streak_3" in data_migrate["newly_unlocked_ids"]
    assert "photo_solver" in data_migrate["newly_unlocked_ids"]

    # Gọi GET /api/user/badges kiểm tra danh sách huy hiệu
    res_get = client.get("/api/user/badges")
    assert res_get.status_code == 200
    data_get = res_get.json()
    assert data_get["success"] is True
    badge_ids = data_get["badge_ids"]
    assert "independence_100" in badge_ids
    assert "streak_3" in badge_ids
    assert "photo_solver" in badge_ids
    assert len(data_get["badges"]) >= 3

    # Alias /user/badges hoạt động đồng nhất
    res_alias = client.get("/user/badges")
    assert res_alias.status_code == 200
    assert "independence_100" in res_alias.json()["badge_ids"]


def test_ac_924_idempotent_db_records():
    """Đảm bảo trong DB bảng user_unlocked_badges không bao giờ bị duplicate bản ghi."""
    db: Session = SessionLocal()
    try:
        count = (
            db.query(models.UserUnlockedBadge)
            .filter(
                models.UserUnlockedBadge.user_id == TEST_USER_ID,
                models.UserUnlockedBadge.badge_id == "independence_100",
            )
            .count()
        )
        assert count == 1, f"Bản ghi huy hiệu phải duy nhất trong DB, thực tế: {count}"
    finally:
        db.close()

