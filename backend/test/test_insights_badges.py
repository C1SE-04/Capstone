"""
Test suite cho US 7.3 (AI Insights background service) và US 7.4 (Badge System).
Chạy: python -m pytest test/test_insights_badges.py -v  (hoặc python test/test_insights_badges.py)
"""
import sys
import os
import json
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
import schemas
from database import SessionLocal

# ──────────────────────────────────────────────────────────
# Helpers / setup
# ──────────────────────────────────────────────────────────

def make_id() -> str:
    return uuid.uuid4().hex


def get_db():
    return SessionLocal()


def _cleanup(db, student_id: str):
    """Xóa dữ liệu test của 1 student."""
    db.query(models.StudentBadge).filter(models.StudentBadge.student_id == student_id).delete()
    db.query(models.ParentAiInsight).filter(models.ParentAiInsight.student_id == student_id).delete()
    db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == student_id).delete()
    db.query(models.SessionActiveInterval).filter(models.SessionActiveInterval.user_id == student_id).delete()
    db.query(models.Session).filter(models.Session.user_id == student_id).delete()
    db.query(models.User).filter(models.User.id == student_id).delete()
    db.commit()


# ──────────────────────────────────────────────────────────
# TEST 1: Model ParentAiInsight tồn tại và có đủ cột
# ──────────────────────────────────────────────────────────
def test_parent_ai_insight_model_columns():
    required_cols = {"id", "student_id", "period_start", "period_end", "report_json",
                     "avg_independence_score", "total_problems", "is_fallback", "created_at"}
    actual_cols = {c.name for c in models.ParentAiInsight.__table__.columns}
    missing = required_cols - actual_cols
    assert not missing, f"Thiếu columns: {missing}"
    print("[PASS] Test 1: ParentAiInsight model columns OK")


# ──────────────────────────────────────────────────────────
# TEST 2: Model StudentBadge tồn tại và có đủ cột
# ──────────────────────────────────────────────────────────
def test_student_badge_model_columns():
    required_cols = {"id", "student_id", "badge_key", "badge_name",
                     "badge_description", "category", "unlocked_at"}
    actual_cols = {c.name for c in models.StudentBadge.__table__.columns}
    missing = required_cols - actual_cols
    assert not missing, f"Thiếu columns: {missing}"
    print("[PASS] Test 2: StudentBadge model columns OK")


# ──────────────────────────────────────────────────────────
# TEST 3: BADGE_CATALOG hợp lệ
# ──────────────────────────────────────────────────────────
def test_badge_catalog_structure():
    catalog = models.BADGE_CATALOG
    assert len(catalog) >= 10, "Phải có ít nhất 10 huy hiệu"
    for key, info in catalog.items():
        assert "name" in info, f"{key}: thiếu 'name'"
        assert "description" in info, f"{key}: thiếu 'description'"
        assert "category" in info, f"{key}: thiếu 'category'"
        assert "threshold" in info, f"{key}: thiếu 'threshold'"
        assert info["category"] in ("streak", "problems", "independence"), \
            f"{key}: category không hợp lệ = {info['category']}"
    print(f"[PASS] Test 3: BADGE_CATALOG hợp lệ ({len(catalog)} huy hiệu)")


# ──────────────────────────────────────────────────────────
# TEST 4: Ghi và đọc ParentAiInsight trên DB thật
# ──────────────────────────────────────────────────────────
def test_save_and_read_ai_insight():
    db = get_db()
    student_id = make_id()

    try:
        # Tạo user test
        user = models.User(id=student_id, email=f"{student_id}@test.com",
                           hashed_password="x", role="STUDENT", grade=5)
        db.add(user)
        db.commit()

        fake_report = {
            "summary": "Em học tốt.",
            "strengths": ["Chăm chỉ"],
            "weak_points": ["Cần cải thiện tốc độ"],
            "recommendations": ["Luyện thêm dạng toán đố"],
            "mastery_assessment": "Tự lập tốt",
            "is_fallback": False,
        }

        now = datetime.now(timezone.utc)
        insight = models.ParentAiInsight(
            id=make_id(),
            student_id=student_id,
            period_start=now - timedelta(days=6),
            period_end=now,
            report_json=json.dumps(fake_report),
            avg_independence_score=72,
            total_problems=5,
            is_fallback=False,
        )
        db.add(insight)
        db.commit()

        # Đọc lại
        fetched = db.query(models.ParentAiInsight).filter(
            models.ParentAiInsight.student_id == student_id
        ).first()
        assert fetched is not None, "Không tìm thấy record vừa lưu"
        assert fetched.avg_independence_score == 72
        assert fetched.total_problems == 5
        assert json.loads(fetched.report_json)["summary"] == "Em học tốt."

        print("[PASS] Test 4: Ghi và đọc ParentAiInsight OK")
    finally:
        _cleanup(db, student_id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 5: Trao huy hiệu streak_3 khi học 3 ngày liên tiếp
# ──────────────────────────────────────────────────────────
def test_badge_unlock_streak():
    from routers.insights import _unlock_badges_for_student
    db = get_db()
    student_id = make_id()

    try:
        user = models.User(id=student_id, email=f"{student_id}@test.com",
                           hashed_password="x", role="STUDENT", grade=5)
        db.add(user)
        db.commit()

        today = datetime.now(timezone.utc).date()

        # Tạo session và interval cho 3 ngày liên tiếp
        for offset in range(3):
            day = today - timedelta(days=offset)
            day_start = datetime(day.year, day.month, day.day, 8, 0, 0, tzinfo=timezone.utc)
            day_end = datetime(day.year, day.month, day.day, 9, 0, 0, tzinfo=timezone.utc)

            session = models.Session(id=make_id(), user_id=student_id, title=f"Ngày {offset}")
            db.add(session)
            db.commit()

            interval = models.SessionActiveInterval(
                id=make_id(), session_id=session.id, user_id=student_id,
                start_time=day_start, end_time=day_end, active_seconds=3600,
            )
            db.add(interval)
        db.commit()

        newly = _unlock_badges_for_student(student_id, db)
        unlocked_keys = {b.badge_key for b in newly}
        assert "streak_3" in unlocked_keys, f"streak_3 chưa được trao. Nhận được: {unlocked_keys}"
        print(f"[PASS] Test 5: Trao huy hiệu streak_3 OK (unlocked: {unlocked_keys})")
    finally:
        _cleanup(db, student_id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 6: Trao huy hiệu problems_5 khi hoàn thành 5 bài
# ──────────────────────────────────────────────────────────
def test_badge_unlock_problems():
    from routers.insights import _unlock_badges_for_student
    db = get_db()
    student_id = make_id()

    try:
        user = models.User(id=student_id, email=f"{student_id}@test.com",
                           hashed_password="x", role="STUDENT", grade=5)
        db.add(user)
        db.commit()

        session = models.Session(id=make_id(), user_id=student_id, title="Test session")
        db.add(session)
        db.commit()

        # Tạo 5 bài hoàn thành
        for _ in range(5):
            score = models.IndependenceScore(
                id=make_id(), session_id=session.id, student_id=student_id,
                score=70, hints_used=1, not_understood_count=0, evaluation="Khá",
            )
            db.add(score)
        db.commit()

        newly = _unlock_badges_for_student(student_id, db)
        unlocked_keys = {b.badge_key for b in newly}
        assert "problems_5" in unlocked_keys, f"problems_5 chưa được trao. Nhận được: {unlocked_keys}"
        print(f"[PASS] Test 6: Trao huy hiệu problems_5 OK (unlocked: {unlocked_keys})")
    finally:
        _cleanup(db, student_id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 7: Không trao badge trùng (idempotent)
# ──────────────────────────────────────────────────────────
def test_badge_idempotent():
    from routers.insights import _unlock_badges_for_student
    db = get_db()
    student_id = make_id()

    try:
        user = models.User(id=student_id, email=f"{student_id}@test.com",
                           hashed_password="x", role="STUDENT", grade=5)
        db.add(user)
        db.commit()

        session = models.Session(id=make_id(), user_id=student_id, title="Test session")
        db.add(session)
        db.commit()

        # 5 bài
        for _ in range(5):
            score = models.IndependenceScore(
                id=make_id(), session_id=session.id, student_id=student_id,
                score=70, hints_used=1, not_understood_count=0,
            )
            db.add(score)
        db.commit()

        # Lần 1
        first_run = _unlock_badges_for_student(student_id, db)
        first_keys = {b.badge_key for b in first_run}

        # Lần 2 – phải không trao thêm gì mới
        second_run = _unlock_badges_for_student(student_id, db)
        assert len(second_run) == 0, f"Lần 2 vẫn trao badge (không idempotent): {[b.badge_key for b in second_run]}"

        print(f"[PASS] Test 7: Badge idempotent OK (lần 1 unlocked: {first_keys}, lần 2: rỗng)")
    finally:
        _cleanup(db, student_id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 8: _get_student_weekly_data trả đúng cấu trúc
# ──────────────────────────────────────────────────────────
def test_get_weekly_data_structure():
    from routers.insights import _get_student_weekly_data
    db = get_db()
    student_id = make_id()

    try:
        user = models.User(id=student_id, email=f"{student_id}@test.com",
                           hashed_password="x", role="STUDENT", grade=5)
        db.add(user)
        db.commit()

        # Không có bài → total_problems = 0
        data = _get_student_weekly_data(student_id, 7, db)
        assert data["total_problems"] == 0
        assert "topic_breakdown" in data
        assert isinstance(data["topic_breakdown"], list)
        print("[PASS] Test 8: _get_student_weekly_data trả đúng cấu trúc khi rỗng")
    finally:
        _cleanup(db, student_id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 9: Schemas WeeklyInsightServiceResult và BadgeCheckResponse hợp lệ
# ──────────────────────────────────────────────────────────
def test_schemas_validation():
    result = schemas.WeeklyInsightServiceResult(
        student_id="abc",
        student_name="Nguyen Van A",
        status="success",
        insight_id="xyz123",
    )
    assert result.status == "success"

    badge_resp = schemas.BadgeResponse(
        id="b1", student_id="abc", badge_key="streak_3",
        badge_name="Ngon Lua Nho", category="streak",
        unlocked_at=datetime.now(timezone.utc),
    )
    check = schemas.BadgeCheckResponse(
        student_id="abc",
        newly_unlocked=[badge_resp],
        all_badges=[badge_resp],
        current_streak=3,
    )
    assert len(check.newly_unlocked) == 1
    print("[PASS] Test 9: Schemas WeeklyInsightServiceResult và BadgeCheckResponse hợp lệ")


# ──────────────────────────────────────────────────────────
# MAIN RUNNER
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        test_parent_ai_insight_model_columns,
        test_student_badge_model_columns,
        test_badge_catalog_structure,
        test_save_and_read_ai_insight,
        test_badge_unlock_streak,
        test_badge_unlock_problems,
        test_badge_idempotent,
        test_get_weekly_data_structure,
        test_schemas_validation,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Ket qua: {passed}/{passed+failed} PASSED | {failed} FAILED")
    print('='*50)
