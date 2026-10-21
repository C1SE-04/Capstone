# Lightweight test: kiểm tra trực tiếp schema, model, và bảng DB — không import main.py
# Tránh dependency lên cloudinary/PIL chưa cài

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from database import engine, SessionLocal
import models

passed = 0
failed = 0

def run(name, fn):
    global passed, failed
    try:
        print(f"[RUN] {name}")
        fn()
        print(f"[PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        failed += 1

# ─── Seed data ───────────────────────────────────────────────────────────────
SID  = "test-cp-student-lite"
PID  = "test-cp-parent-lite"
OID  = "test-cp-other-lite"

def cleanup():
    db = SessionLocal()
    try:
        db.rollback()
        ids = [SID, PID, OID]
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
        db.query(models.ProblemBookmark).filter(models.ProblemBookmark.student_id.in_(ids)).delete(synchronize_session=False)
        db.query(models.User).filter(models.User.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

def seed():
    db = SessionLocal()
    try:
        student = models.User(id=SID, email="s_lite@test.com", hashed_password="x", role="STUDENT", grade=5)
        parent  = models.User(id=PID, email="p_lite@test.com", hashed_password="x", role="MONITOR")
        other   = models.User(id=OID, email="o_lite@test.com", hashed_password="x", role="MONITOR")
        db.add_all([student, parent, other])
        db.flush()

        link = models.ParentStudentLink(parent_id=PID, student_id=SID)
        db.add(link)
        db.flush()

        sess = models.Session(id=uuid.uuid4().hex, user_id=SID, title="Bài tập giải")
        db.add(sess)
        db.flush()

        m1 = models.Message(id=uuid.uuid4().hex, session_id=sess.id, sender_type="USER",
                            content="Cho em hỏi bài toán", attachment_url=None,
                            created_at=datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc))
        m2 = models.Message(id=uuid.uuid4().hex, session_id=sess.id, sender_type="USER",
                            content="Ảnh đây ạ", attachment_url="https://res.cloudinary.com/test/abc.jpg",
                            created_at=datetime(2026, 10, 1, 8, 2, 0, tzinfo=timezone.utc))
        m3 = models.Message(id=uuid.uuid4().hex, session_id=sess.id, sender_type="USER",
                            content="Em đã hiểu", attachment_url=None,
                            created_at=datetime(2026, 10, 1, 8, 10, 0, tzinfo=timezone.utc))
        db.add_all([m1, m2, m3])

        score = models.IndependenceScore(
            id=uuid.uuid4().hex, session_id=sess.id, student_id=SID,
            score=85, hints_used=0, not_understood_count=0, evaluation="Xuất sắc",
            created_at=datetime(2026, 10, 1, 8, 15, 0, tzinfo=timezone.utc)
        )
        db.add(score)
        db.commit()
        return sess.id
    finally:
        db.close()

# ─── Tests ───────────────────────────────────────────────────────────────────

cleanup()
session_id = seed()

def test_independence_score_linked_to_session():
    """IndependenceScore đã ghi đúng session_id và student_id."""
    db = SessionLocal()
    try:
        s = db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == SID).first()
        assert s is not None, "Không tìm thấy IndependenceScore"
        assert s.score == 85
        assert s.evaluation == "Xuất sắc"
        print(f"  score={s.score}, eval={s.evaluation}")
    finally:
        db.close()

def test_attachment_url_query():
    """Query tìm đúng ảnh đề bài (attachment_url) đầu tiên trong session."""
    db = SessionLocal()
    try:
        msgs = (db.query(models.Message)
                .filter(models.Message.session_id == session_id, models.Message.sender_type == "USER")
                .order_by(models.Message.created_at.asc())
                .limit(5).all())
        url = next((m.attachment_url for m in msgs if m.attachment_url), None)
        assert url == "https://res.cloudinary.com/test/abc.jpg"
        print(f"  attachment_url={url}")
    finally:
        db.close()

def test_chat_summary_build():
    """Chat summary ghép đúng 3 tin nhắn USER đầu tiên."""
    db = SessionLocal()
    try:
        msgs = (db.query(models.Message)
                .filter(models.Message.session_id == session_id, models.Message.sender_type == "USER")
                .order_by(models.Message.created_at.asc())
                .limit(5).all())
        parts = [m.content for m in msgs[:3] if m.content]
        summary = " | ".join(parts)
        assert "Cho em hỏi bài toán" in summary
        assert "Ảnh đây ạ" in summary
        assert "Em đã hiểu" in summary
        print(f"  summary='{summary}'")
    finally:
        db.close()

def test_parent_link_exists():
    """ParentStudentLink đúng giữa parent và student."""
    db = SessionLocal()
    try:
        link = db.query(models.ParentStudentLink).filter(
            models.ParentStudentLink.parent_id == PID,
            models.ParentStudentLink.student_id == SID
        ).first()
        assert link is not None
        print(f"  link OK: {PID} -> {SID}")
    finally:
        db.close()

def test_bookmark_model_create():
    """Tạo ProblemBookmark vào DB thành công."""
    db = SessionLocal()
    try:
        bm = models.ProblemBookmark(
            id=uuid.uuid4().hex,
            student_id=SID,
            session_id=session_id,
            problem_snapshot="Cho em hỏi bài toán",
            attachment_url="https://res.cloudinary.com/test/abc.jpg",
            chat_summary="Cho em hỏi bài toán | Ảnh đây ạ | Em đã hiểu",
            independence_score=85,
            note=None
        )
        db.add(bm)
        db.commit()
        fetched = db.query(models.ProblemBookmark).filter(models.ProblemBookmark.student_id == SID).first()
        assert fetched is not None
        assert fetched.independence_score == 85
        assert fetched.attachment_url == "https://res.cloudinary.com/test/abc.jpg"
        print(f"  Bookmark created: id={fetched.id}, score={fetched.independence_score}")
    finally:
        db.close()

def test_bookmark_unique_constraint():
    """Thêm bookmark trùng (student_id + session_id) phải báo lỗi UNIQUE violation."""
    db = SessionLocal()
    try:
        bm2 = models.ProblemBookmark(
            id=uuid.uuid4().hex,
            student_id=SID,
            session_id=session_id,
            problem_snapshot="Duplicate"
        )
        db.add(bm2)
        try:
            db.commit()
            assert False, "Phải raise IntegrityError do UNIQUE constraint"
        except Exception as e:
            db.rollback()
            assert "unique" in str(e).lower() or "duplicate" in str(e).lower(), f"Lỗi không đúng: {e}"
            print(f"  UNIQUE constraint hoạt động đúng: {type(e).__name__}")
    finally:
        db.close()

def test_bookmark_table_columns():
    """Bảng problem_bookmarks có đầy đủ cột theo thiết kế."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'problem_bookmarks' ORDER BY ordinal_position;
        """))
        cols = [r[0] for r in result.fetchall()]
    required = ["id","student_id","session_id","problem_snapshot",
                "attachment_url","chat_summary","independence_score","note","created_at"]
    for c in required:
        assert c in cols, f"Thiếu cột: {c}"
    print(f"  Columns OK: {cols}")

def test_bookmark_unique_index_exists():
    """UNIQUE index ix_bookmarks_student_session tồn tại."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, indexdef FROM pg_indexes
            WHERE tablename='problem_bookmarks' AND indexname='ix_bookmarks_student_session';
        """))
        row = result.fetchone()
    assert row is not None, "UNIQUE index không tồn tại!"
    assert "UNIQUE" in row[1].upper()
    print(f"  UNIQUE index: {row[0]}")

run("IndependenceScore ghi đúng DB", test_independence_score_linked_to_session)
run("Attachment URL query đúng", test_attachment_url_query)
run("Chat summary build đúng", test_chat_summary_build)
run("ParentStudentLink tồn tại", test_parent_link_exists)
run("Tạo ProblemBookmark thành công", test_bookmark_model_create)
run("UNIQUE constraint Bookmark hoạt động", test_bookmark_unique_constraint)
run("Columns problem_bookmarks đủ", test_bookmark_table_columns)
run("UNIQUE index tồn tại", test_bookmark_unique_index_exists)

cleanup()

print(f"\n{'='*50}")
print(f"Results: {passed} PASSED, {failed} FAILED out of {passed+failed} tests")
