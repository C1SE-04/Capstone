# US 7.1 (Task T7.6) & US 7.2 (Task T7.7): Tests cho API /parent/child-problems và schema Bookmark
# Kiểm tra:
# 1. GET /parent/child-problems trả đúng dữ liệu (score, ảnh, chat tóm tắt)
# 2. Phân quyền: MONITOR xem được, STUDENT bị chặn, MONITOR không có link bị chặn
# 3. Phân trang hoạt động đúng
# 4. Bảng problem_bookmarks tồn tại trên DB với đúng cột và index

import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import dependencies
import models
from database import SessionLocal

client = TestClient(app)

TEST_STUDENT_ID = "test-student-child-probs"
TEST_PARENT_ID  = "test-parent-child-probs"
TEST_OTHER_ID   = "test-other-child-probs"

current_mock_user: dict = {"id": TEST_PARENT_ID, "role": "MONITOR"}


def mock_user():
    return current_mock_user


app.dependency_overrides[dependencies.get_current_user] = mock_user

# ─── Helpers ──────────────────────────────────────────────────────────────────

def cleanup_db(db):
    db.rollback()
    ids = [TEST_STUDENT_ID, TEST_PARENT_ID, TEST_OTHER_ID]
    db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.Message).filter(
        models.Message.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id.in_(ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.SessionStats).filter(
        models.SessionStats.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id.in_(ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.Session).filter(models.Session.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.ParentStudentLink).filter(
        (models.ParentStudentLink.parent_id.in_(ids)) |
        (models.ParentStudentLink.student_id.in_(ids))
    ).delete(synchronize_session=False)
    db.query(models.User).filter(models.User.id.in_(ids)).delete(synchronize_session=False)
    db.commit()


def seed_db(db):
    """Tạo dữ liệu test: student, parent, link, session, messages, independence_score."""
    # Users
    student = models.User(id=TEST_STUDENT_ID, email="student_cp@test.com", hashed_password="x", role="STUDENT", grade=5)
    parent  = models.User(id=TEST_PARENT_ID,  email="parent_cp@test.com",  hashed_password="x", role="MONITOR")
    other   = models.User(id=TEST_OTHER_ID,   email="other_cp@test.com",   hashed_password="x", role="MONITOR")
    db.add_all([student, parent, other])
    db.flush()

    # Parent-student link
    link = models.ParentStudentLink(parent_id=TEST_PARENT_ID, student_id=TEST_STUDENT_ID)
    db.add(link)
    db.flush()

    # Session + messages + score
    session = models.Session(id=uuid.uuid4().hex, user_id=TEST_STUDENT_ID, title="Bài tập về nhà")
    db.add(session)
    db.flush()

    # 3 tin nhắn USER (2 không có ảnh, 1 có ảnh)
    m1 = models.Message(id=uuid.uuid4().hex, session_id=session.id, sender_type="USER",
                        content="Cho em hỏi bài toán này", attachment_url=None,
                        created_at=datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc))
    m2 = models.Message(id=uuid.uuid4().hex, session_id=session.id, sender_type="USER",
                        content="Ảnh đây ạ", attachment_url="https://res.cloudinary.com/test/image/upload/abc.jpg",
                        created_at=datetime(2026, 10, 1, 8, 2, 0, tzinfo=timezone.utc))
    m3 = models.Message(id=uuid.uuid4().hex, session_id=session.id, sender_type="USER",
                        content="Em hiểu rồi ạ", attachment_url=None,
                        created_at=datetime(2026, 10, 1, 8, 10, 0, tzinfo=timezone.utc))
    db.add_all([m1, m2, m3])

    score = models.IndependenceScore(
        id=uuid.uuid4().hex, session_id=session.id, student_id=TEST_STUDENT_ID,
        score=80, hints_used=1, not_understood_count=0, evaluation="Xuất sắc",
        created_at=datetime(2026, 10, 1, 8, 15, 0, tzinfo=timezone.utc)
    )
    db.add(score)
    db.commit()
    return session.id


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_child_problems_success():
    """MONITOR xem được danh sách bài toán của con đã liên kết."""
    global current_mock_user
    db = SessionLocal()
    try:
        cleanup_db(db)
        seed_db(db)
    finally:
        db.close()

    current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
    resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["student_id"] == TEST_STUDENT_ID
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["score"] == 80
    assert item["evaluation"] == "Xuất sắc"
    assert item["hints_used"] == 1
    print(f"  [OK] score={item['score']}, evaluation={item['evaluation']}")


def test_child_problems_attachment_url():
    """Ảnh đề bài (attachment_url) được trích đúng từ tin nhắn USER."""
    global current_mock_user
    current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
    resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["attachment_url"] == "https://res.cloudinary.com/test/image/upload/abc.jpg"
    print(f"  [OK] attachment_url={item['attachment_url']}")


def test_child_problems_chat_summary():
    """Chat tóm tắt ghép đúng 3 tin nhắn USER đầu tiên."""
    global current_mock_user
    current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
    resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    summary = item["chat_summary"]
    assert "Cho em hỏi bài toán này" in summary
    assert "Ảnh đây ạ" in summary
    assert "Em hiểu rồi ạ" in summary
    print(f"  [OK] chat_summary='{summary[:60]}...'")


def test_child_problems_pagination():
    """Phân trang hoạt động đúng — page=1, page_size=1 trả 1 bài."""
    global current_mock_user
    current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
    resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}&page=1&page_size=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["items"]) == 1
    print(f"  [OK] page={data['page']}, page_size={data['page_size']}, items={len(data['items'])}")


def test_child_problems_student_forbidden():
    """STUDENT không được gọi API này (403)."""
    global current_mock_user
    current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT"}
    resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    print(f"  [OK] STUDENT bị chặn đúng (403)")


def test_child_problems_no_link_forbidden():
    """MONITOR không có liên kết với học sinh bị chặn (403)."""
    global current_mock_user
    current_mock_user = {"id": TEST_OTHER_ID, "role": "MONITOR"}
    resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    print(f"  [OK] MONITOR không link bị chặn đúng (403)")


def test_bookmark_table_exists():
    """Bảng problem_bookmarks đã được tạo trên DB với đúng cột."""
    from sqlalchemy import text
    from database import engine
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'problem_bookmarks'
            ORDER BY ordinal_position;
        """))
        columns = [row[0] for row in result.fetchall()]
    required = ["id", "student_id", "session_id", "problem_snapshot",
                "attachment_url", "chat_summary", "independence_score", "note", "created_at"]
    for col in required:
        assert col in columns, f"Missing column: {col}"
    print(f"  [OK] Columns: {columns}")


def test_bookmark_unique_index_exists():
    """Index UNIQUE(student_id, session_id) tồn tại trên problem_bookmarks."""
    from sqlalchemy import text
    from database import engine
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'problem_bookmarks'
              AND indexname = 'ix_bookmarks_student_session';
        """))
        row = result.fetchone()
    assert row is not None, "UNIQUE index ix_bookmarks_student_session không tồn tại!"
    assert "UNIQUE" in row[1].upper()
    print(f"  [OK] UNIQUE index: {row[0]}")


def test_bookmark_student_created_index_exists():
    """US 7.2 - Task 7.21: Composite index ix_bookmarks_student_created tồn tại và tối ưu DESC."""
    from sqlalchemy import text
    from database import engine
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'problem_bookmarks'
              AND indexname = 'ix_bookmarks_student_created';
        """))
        row = result.fetchone()
    assert row is not None, "Composite index ix_bookmarks_student_created không tồn tại!"
    indexdef = row[1]
    assert "student_id" in indexdef, "Index thiếu cột student_id"
    assert "created_at" in indexdef, "Index thiếu cột created_at"
    assert "DESC" in indexdef.upper(), "Index chưa được tối ưu với created_at DESC"
    print(f"  [OK] Composite index tối ưu: {row[0]} -> {indexdef}")


def test_bookmark_query_plan_performance():
    """US 7.2 - Task 7.21: Verify query EXPLAIN sử dụng ix_bookmarks_student_created không bị Seq Scan."""
    from sqlalchemy import text
    from database import engine
    with engine.connect() as conn:
        conn.execute(text("SET enable_bitmapscan = off;"))
        conn.execute(text("SET enable_seqscan = off;"))
        result = conn.execute(text("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT * FROM problem_bookmarks
            WHERE student_id = :student_id
            ORDER BY created_at DESC
            LIMIT 10;
        """), {"student_id": TEST_STUDENT_ID})
        plan_lines = [r[0] for r in result.fetchall()]
        plan_text = " ".join(plan_lines)
    assert "ix_bookmarks_student_created" in plan_text, f"Query không sử dụng index ix_bookmarks_student_created: {plan_text}"
    assert "Seq Scan" not in plan_text, f"Query bị rơi vào Seq Scan: {plan_text}"
    print(f"  [OK] EXPLAIN plan tối ưu Index Scan thành công: {plan_lines[0]}")


if __name__ == "__main__":
    tests = [
        test_child_problems_success,
        test_child_problems_attachment_url,
        test_child_problems_chat_summary,
        test_child_problems_pagination,
        test_child_problems_student_forbidden,
        test_child_problems_no_link_forbidden,
        test_bookmark_table_exists,
        test_bookmark_unique_index_exists,
        test_bookmark_student_created_index_exists,
        test_bookmark_query_plan_performance,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            print(f"[RUN] {t.__name__}")
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {passed} PASSED, {failed} FAILED")

