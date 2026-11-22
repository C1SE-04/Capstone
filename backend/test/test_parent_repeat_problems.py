"""
Test Suite: Parent View for Repeat Problems (US 9.2 Anti-Spam Mastery)
======================================================================
Kiểm thử nghiệp vụ:
- Phụ huynh xem danh sách bài tập của con (/parent/child-problems):
  Hiển thị đầy đủ cả bài giải lần đầu (100đ) và các bài giải lại (90đ, 80đ) với nhãn EXACT_DUPLICATE (is_duplicate=True).
- Dashboard phụ huynh (/metrics/summary và /independence/summary):
  Ghi nhận tăng đủ số bài hoàn thành (+1 cho mỗi lần giải lại) và cập nhật điểm tự lực chính xác.
"""

import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import SessionLocal
import models
import dependencies
from routers.independence import save_independence_score

client = TestClient(app)

TEST_STUDENT_ID = f"test_stu_rep_{uuid.uuid4().hex[:8]}"
TEST_PARENT_ID = f"test_par_rep_{uuid.uuid4().hex[:8]}"
TEST_STUDENT_USERNAME = f"stu_rep_{uuid.uuid4().hex[:6]}"
TEST_PARENT_USERNAME = f"par_rep_{uuid.uuid4().hex[:6]}"

current_mock_user = {"id": TEST_PARENT_ID, "username": TEST_PARENT_USERNAME, "role": "MONITOR"}


def mock_user():
    return current_mock_user


@pytest.fixture(autouse=True)
def override_user():
    app.dependency_overrides[dependencies.get_current_user] = mock_user
    yield
    app.dependency_overrides[dependencies.get_current_user] = mock_user


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    db: Session = SessionLocal()
    try:
        # Tạo student
        student = models.User(
            id=TEST_STUDENT_ID,
            username=TEST_STUDENT_USERNAME,
            email=f"{TEST_STUDENT_ID}@socratickid.local",
            hashed_password="mocked_password",
            role="STUDENT",
            grade=7,
        )
        # Tạo parent
        parent = models.User(
            id=TEST_PARENT_ID,
            username=TEST_PARENT_USERNAME,
            email=f"{TEST_PARENT_ID}@socratickid.local",
            hashed_password="mocked_password",
            role="MONITOR",
        )
        db.add_all([student, parent])
        db.commit()

        # Tạo liên kết phụ huynh - con
        link = models.ParentStudentLink(
            parent_id=TEST_PARENT_ID,
            student_id=TEST_STUDENT_ID,
        )
        db.add(link)
        db.commit()

        yield
    finally:
        db.query(models.ParentStudentLink).filter(models.ParentStudentLink.student_id == TEST_STUDENT_ID).delete()
        db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == TEST_STUDENT_ID).delete()
        db.query(models.SessionStats).filter(
            models.SessionStats.session_id.in_(
                db.query(models.Session.id).filter(models.Session.user_id == TEST_STUDENT_ID)
            )
        ).delete()
        db.query(models.Session).filter(models.Session.user_id == TEST_STUDENT_ID).delete()
        db.query(models.User).filter(models.User.id.in_([TEST_STUDENT_ID, TEST_PARENT_ID])).delete()
        db.commit()
        db.close()
        app.dependency_overrides.pop(dependencies.get_current_user, None)


def test_parent_views_repeated_problems_in_history():
    """
    [US 9.2]: Phụ huynh truy vấn /parent/child-problems PHẢI nhìn thấy
    cả bài giải lần đầu và các lần giải lại (is_duplicate=True) kèm điểm bị trừ theo barem.
    """
    global current_mock_user
    db: Session = SessionLocal()
    problem_text = "Hình chữ nhật có chiều dài 15m, chiều rộng 10m. Tính chu vi hình chữ nhật đó."

    try:
        # Lần 1: Học sinh giải bài trong session 1 (không gợi ý -> 100đ)
        s1 = models.Session(id=f"sess_{uuid.uuid4().hex[:6]}", user_id=TEST_STUDENT_ID, title="Toán hình lớp 7")
        db.add(s1)
        db.commit()
        rec1 = save_independence_score(
            db=db,
            session_id=s1.id,
            student_id=TEST_STUDENT_ID,
            custom_hints=0,
            custom_not_understood=0,
            problem_text_input=problem_text,
        )
        assert rec1.score == 100
        assert rec1.is_duplicate is False

        # Lần 2: Học sinh giải lại cùng bài trong session 2 (không gợi ý -> phạt trần 90đ)
        s2 = models.Session(id=f"sess_{uuid.uuid4().hex[:6]}", user_id=TEST_STUDENT_ID, title="Toán hình lớp 7 giải lại 1")
        db.add(s2)
        db.commit()
        rec2 = save_independence_score(
            db=db,
            session_id=s2.id,
            student_id=TEST_STUDENT_ID,
            custom_hints=0,
            custom_not_understood=0,
            problem_text_input=problem_text,
        )
        assert rec2.score == 90
        assert rec2.is_duplicate is True
        assert rec2.repeat_count == 2
        assert rec2.max_score == 90

        # Lần 3: Học sinh giải lại cùng bài trong session 3 (không gợi ý -> phạt trần 80đ)
        s3 = models.Session(id=f"sess_{uuid.uuid4().hex[:6]}", user_id=TEST_STUDENT_ID, title="Toán hình lớp 7 giải lại 2")
        db.add(s3)
        db.commit()
        rec3 = save_independence_score(
            db=db,
            session_id=s3.id,
            student_id=TEST_STUDENT_ID,
            custom_hints=0,
            custom_not_understood=0,
            problem_text_input=problem_text,
        )
        assert rec3.score == 80
        assert rec3.is_duplicate is True
        assert rec3.repeat_count == 3
        assert rec3.max_score == 80

        # Phụ huynh truy vấn /parent/child-problems
        current_mock_user = {"id": TEST_PARENT_ID, "username": TEST_PARENT_USERNAME, "role": "MONITOR"}
        resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
        assert resp.status_code == 200
        data = resp.json()

        # PHẢI nhận đủ 3 bài (không bị ẩn các bài giải lại)
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Sắp xếp mới nhất lên đầu: Lần 3 (80đ) -> Lần 2 (90đ) -> Lần 1 (100đ)
        item3 = data["items"][0]
        item2 = data["items"][1]
        item1 = data["items"][2]

        assert item3["score"] == 80
        assert item3["is_duplicate"] is True
        assert item3["repeat_count"] == 3
        assert item3["max_score"] == 80
        assert "Bài giải lại" in (item3["repeat_warning"] or "")

        assert item2["score"] == 90
        assert item2["is_duplicate"] is True
        assert item2["repeat_count"] == 2
        assert item2["max_score"] == 90

        assert item1["score"] == 100
        assert item1["is_duplicate"] is False
        assert item1["repeat_count"] == 1

        # 2. Kiểm tra API /metrics/summary ghi nhận 3 bài hoàn thành
        resp_progress = client.get(f"/metrics/summary?student_id={TEST_STUDENT_ID}&time_range=all")
        assert resp_progress.status_code == 200
        progress_data = resp_progress.json()
        assert progress_data["completed_problems"] == 3

        # 3. Kiểm tra API /independence/summary ghi nhận total_completed = 3 và history có 3 điểm
        resp_summary = client.get(f"/independence/summary?student_id={TEST_STUDENT_ID}")
        assert resp_summary.status_code == 200
        summary_data = resp_summary.json()
        assert summary_data["total_completed"] == 3
        assert summary_data["latest_score"] == 80
        assert len(summary_data["history"]) == 3

    finally:
        db.close()
