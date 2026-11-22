"""
US 8.4 - Test suite cho bang curriculum_topics tren Neon DB (Task T8.23).
Kiem tra:
1. Bang curriculum_topics ton tai va co du lieu khoi tao cho cac khoi lop 4 - 9.
2. Schema Pydantic hop le (CurriculumTopicResponse, CurriculumTopicCreate, CurriculumTopicToggle).
3. Tinh nang Toggle Bật / Tắt (is_active) phuc vu giam tai theo chuong trinh.
4. Rang buoc Unique Composite Index chong trung lap chuyen de khi cào nhieu lan.
5. Truy van toi uu theo (grade, is_active).

Chay:
    $env:PYTHONIOENCODING="utf-8"; python test/test_curriculum_topics.py
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import models
import schemas
from database import SessionLocal
from sqlalchemy.exc import IntegrityError


def get_db():
    return SessionLocal()


def test_table_exists_and_has_data():
    """TEST 1: Bang curriculum_topics ton tai va co du lieu day du cho cac lop tu 4 den 9."""
    db = get_db()
    try:
        total = db.query(models.CurriculumTopic).count()
        assert total >= 200, f"So luong chuyen de phai >= 200, thuc te co: {total}"

        for g in range(4, 10):
            count_g = db.query(models.CurriculumTopic).filter(models.CurriculumTopic.grade == g).count()
            assert count_g > 0, f"Khong tim thay chuyen de nao cho lop {g}"

        print(f"[PASS] Test 1: Bang curriculum_topics co tong cong {total} chuyen de tu lop 4 den 9.")
    finally:
        db.close()


def test_pydantic_schemas():
    """TEST 2: Pydantic schemas cho CurriculumTopic hoat dong dung."""
    db = get_db()
    try:
        sample = db.query(models.CurriculumTopic).filter(models.CurriculumTopic.grade == 5).first()
        assert sample is not None

        resp = schemas.CurriculumTopicResponse.model_validate(sample)
        assert resp.id == sample.id
        assert resp.grade == 5
        assert resp.is_active is True
        assert resp.topic_name == sample.topic_name
        assert resp.chapter_name == sample.chapter_name

        print("[PASS] Test 2: Pydantic Schema CurriculumTopicResponse hop le 100%.")
    finally:
        db.close()


def test_toggle_is_active():
    """TEST 3: Toggle bat/tat is_active cua chuyen de (AC 8.4.3)."""
    db = get_db()
    test_id = uuid.uuid4().hex
    test_topic = models.CurriculumTopic(
        id=test_id,
        grade=5,
        book_series="Kết nối tri thức",
        chapter_name="Chương kiểm thử toggle",
        topic_name=f"Bài toán toggle {test_id[:6]}",
        order_index=999,
        is_active=True,
    )
    try:
        db.add(test_topic)
        db.commit()

        # Toggle sang False (An)
        test_topic.is_active = False
        db.commit()
        db.refresh(test_topic)
        assert test_topic.is_active is False

        # Toggle lai sang True (Bat)
        test_topic.is_active = True
        db.commit()
        db.refresh(test_topic)
        assert test_topic.is_active is True

        print("[PASS] Test 3: Toggle trang thai is_active thanh cong.")
    finally:
        db.query(models.CurriculumTopic).filter(models.CurriculumTopic.id == test_id).delete()
        db.commit()
        db.close()


def test_unique_constraint_crawler_upsert():
    """TEST 4: Rang buoc Unique Composite Index (grade, book_series, chapter_name, topic_name)."""
    db = get_db()
    uid1 = uuid.uuid4().hex
    uid2 = uuid.uuid4().hex
    topic_name = f"Bài toán trùng lặp {uid1[:6]}"
    t1 = models.CurriculumTopic(
        id=uid1,
        grade=6,
        book_series="Cánh diều",
        chapter_name="Chương Số học",
        topic_name=topic_name,
        order_index=1,
    )
    t2 = models.CurriculumTopic(
        id=uid2,
        grade=6,
        book_series="Cánh diều",
        chapter_name="Chương Số học",
        topic_name=topic_name,
        order_index=2,
    )
    try:
        db.add(t1)
        db.commit()

        # Chen ban ghi t2 giong het cac khoa unique se bi IntegrityError
        db.add(t2)
        try:
            db.commit()
            assert False, "Dang le phai throw IntegrityError do trung lap khoa Unique!"
        except IntegrityError:
            db.rollback()
            print("[PASS] Test 4: Unique Composite Index hoat dong dung, ngan chan trung lap du lieu khi cào nhieu lan.")
    finally:
        db.query(models.CurriculumTopic).filter(models.CurriculumTopic.id == uid1).delete()
        db.commit()
        db.close()


def test_fast_query_for_ai_engine():
    """TEST 5: Truy van nhanh theo (grade, is_active) phuc vu AI engine agent_prompts.py."""
    db = get_db()
    try:
        active_topics_g5 = (
            db.query(models.CurriculumTopic.topic_name)
            .filter(
                models.CurriculumTopic.grade == 5,
                models.CurriculumTopic.is_active == True,
            )
            .order_by(models.CurriculumTopic.order_index.asc())
            .all()
        )
        assert len(active_topics_g5) > 0
        topic_names = [t[0] for t in active_topics_g5]
        assert any("phan so" in name.lower() or "phân số" in name.lower() for name in topic_names)

        print(f"[PASS] Test 5: Truy van danh muc chuyen de cho AI Engine hoan tat ({len(topic_names)} chuyen de lop 5).")
    finally:
        db.close()


def run_all_tests():
    print("=" * 60)
    print("BAT DAU TEST SUITE US 8.4 - BẢNG CURRICULUM_TOPICS")
    print("=" * 60)
    tests = [
        test_table_exists_and_has_data,
        test_pydantic_schemas,
        test_toggle_is_active,
        test_unique_constraint_crawler_upsert,
        test_fast_query_for_ai_engine,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Ket qua: {passed}/{len(tests)} PASSED | {failed} FAILED")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
