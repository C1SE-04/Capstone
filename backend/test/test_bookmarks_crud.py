"""
Test suite cho US 7.2 - CRUD API /bookmarks (Sổ Tay Bài Toán).
Test logic trực tiếp (không cần server đang chạy).
Chạy: python test/test_bookmarks_crud.py
"""
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
import schemas
from database import SessionLocal


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

def make_id() -> str:
    return uuid.uuid4().hex


def get_db():
    return SessionLocal()


def _cleanup(db, student_id: str):
    db.query(models.ProblemBookmark).filter(models.ProblemBookmark.student_id == student_id).delete()
    db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == student_id).delete()
    db.query(models.SessionActiveInterval).filter(models.SessionActiveInterval.user_id == student_id).delete()
    db.query(models.Message).filter(
        models.Message.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id == student_id)
        )
    ).delete(synchronize_session=False)
    db.query(models.Session).filter(models.Session.user_id == student_id).delete()
    db.query(models.User).filter(models.User.id == student_id).delete()
    db.commit()


def _create_test_student(db) -> models.User:
    user = models.User(
        id=make_id(),
        email=f"{make_id()[:8]}@test.com",
        hashed_password="x",
        role="STUDENT",
        grade=5,
    )
    db.add(user)
    db.commit()
    return user


def _create_test_session(db, user_id: str, title: str = "Bài toán tổng hợp") -> models.Session:
    session = models.Session(id=make_id(), user_id=user_id, title=title)
    db.add(session)
    db.commit()
    return session


def _add_messages(db, session_id: str, texts: list[str]) -> list[models.Message]:
    msgs = []
    for text in texts:
        msg = models.Message(
            id=make_id(),
            session_id=session_id,
            sender_type="USER",
            content=text,
        )
        db.add(msg)
        msgs.append(msg)
    db.commit()
    return msgs


# ──────────────────────────────────────────────────────────
# TEST 1: _build_bookmark_snapshot điền đúng snapshot
# ──────────────────────────────────────────────────────────
def test_build_bookmark_snapshot():
    from routers.bookmarks import _build_bookmark_snapshot

    db = get_db()
    student = _create_test_student(db)

    try:
        session = _create_test_session(db, student.id)
        _add_messages(db, session.id, ["Đề bài số 1", "Gợi ý thêm", "Câu hỏi phụ"])

        snap = _build_bookmark_snapshot(session.id, db)
        assert snap["problem_snapshot"] == "Đề bài số 1", f"Snapshot sai: {snap['problem_snapshot']}"
        assert snap["chat_summary"] == "Đề bài số 1 | Gợi ý thêm | Câu hỏi phụ"
        assert snap["attachment_url"] is None
        print("[PASS] Test 1: _build_bookmark_snapshot OK")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 2: _build_bookmark_snapshot lấy đúng attachment_url
# ──────────────────────────────────────────────────────────
def test_build_snapshot_with_attachment():
    from routers.bookmarks import _build_bookmark_snapshot

    db = get_db()
    student = _create_test_student(db)

    try:
        session = _create_test_session(db, student.id)
        msg_with_img = models.Message(
            id=make_id(), session_id=session.id, sender_type="USER",
            content="Xem ảnh đề bài", attachment_url="https://cloudinary.com/img.jpg",
        )
        db.add(msg_with_img)
        db.commit()

        snap = _build_bookmark_snapshot(session.id, db)
        assert snap["attachment_url"] == "https://cloudinary.com/img.jpg"
        print("[PASS] Test 2: attachment_url được lấy đúng từ snapshot")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 3: Ghi bookmark vào DB và đọc lại
# ──────────────────────────────────────────────────────────
def test_create_bookmark_db():
    db = get_db()
    student = _create_test_student(db)

    try:
        session = _create_test_session(db, student.id)
        _add_messages(db, session.id, ["Tìm hai số khi biết tổng và hiệu"])

        bookmark = models.ProblemBookmark(
            id=make_id(),
            student_id=student.id,
            session_id=session.id,
            problem_snapshot="Tìm hai số khi biết tổng và hiệu",
            chat_summary="Tìm hai số khi biết tổng và hiệu",
            attachment_url=None,
            independence_score=75,
            note="Cần ôn lại phần lời giải",
        )
        db.add(bookmark)
        db.commit()

        fetched = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.student_id == student.id
        ).first()
        assert fetched is not None
        assert fetched.independence_score == 75
        assert fetched.note == "Cần ôn lại phần lời giải"
        print("[PASS] Test 3: Ghi và đọc bookmark OK")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 4: Unique constraint mỗi student chỉ lưu 1 lần/session
# ──────────────────────────────────────────────────────────
def test_bookmark_unique_constraint():
    from sqlalchemy.exc import IntegrityError

    db = get_db()
    student = _create_test_student(db)

    try:
        session = _create_test_session(db, student.id)

        b1 = models.ProblemBookmark(
            id=make_id(), student_id=student.id, session_id=session.id,
            problem_snapshot="Đề bài", chat_summary="Đề bài",
        )
        db.add(b1)
        db.commit()

        b2 = models.ProblemBookmark(
            id=make_id(), student_id=student.id, session_id=session.id,
            problem_snapshot="Đề bài lần 2",
        )
        db.add(b2)
        try:
            db.commit()
            db.rollback()
            assert False, "Phải raise IntegrityError khi lưu trùng session"
        except IntegrityError:
            db.rollback()
            print("[PASS] Test 4: Unique constraint student+session hoạt động đúng")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 5: Lọc bookmark theo score_filter
# ──────────────────────────────────────────────────────────
def test_filter_by_score():
    db = get_db()
    student = _create_test_student(db)

    try:
        # Tạo 3 sessions với 3 mức điểm khác nhau
        for score, title in [(90, "Bài xuất sắc"), (65, "Bài khá"), (30, "Bài yếu")]:
            s = _create_test_session(db, student.id, title=title)
            bm = models.ProblemBookmark(
                id=make_id(), student_id=student.id, session_id=s.id,
                problem_snapshot=title, independence_score=score,
            )
            db.add(bm)
        db.commit()

        # Lọc perfect (>= 80)
        perfect = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.student_id == student.id,
            models.ProblemBookmark.independence_score >= 80,
        ).all()
        assert len(perfect) == 1 and perfect[0].problem_snapshot == "Bài xuất sắc"

        # Lọc passed (>= 60)
        passed = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.student_id == student.id,
            models.ProblemBookmark.independence_score >= 60,
        ).all()
        assert len(passed) == 2

        # Lấy tất cả
        all_bm = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.student_id == student.id,
        ).all()
        assert len(all_bm) == 3

        print("[PASS] Test 5: Lọc theo score_filter hoạt động đúng")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 6: Tìm kiếm full-text trong problem_snapshot
# ──────────────────────────────────────────────────────────
def test_search_keyword():
    db = get_db()
    student = _create_test_student(db)

    try:
        for text in ["Tìm hai số biết tổng", "Bài toán chu vi", "Phân số thập phân"]:
            s = _create_test_session(db, student.id, title=text)
            bm = models.ProblemBookmark(
                id=make_id(), student_id=student.id, session_id=s.id,
                problem_snapshot=text, independence_score=70,
            )
            db.add(bm)
        db.commit()

        keyword = "%chu vi%"
        results = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.student_id == student.id,
            (models.ProblemBookmark.problem_snapshot.ilike(keyword))
            | (models.ProblemBookmark.chat_summary.ilike(keyword)),
        ).all()
        assert len(results) == 1
        assert "chu vi" in results[0].problem_snapshot

        print("[PASS] Test 6: Tìm kiếm full-text ilike hoạt động đúng")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 7: Xóa bookmark
# ──────────────────────────────────────────────────────────
def test_delete_bookmark():
    db = get_db()
    student = _create_test_student(db)

    try:
        session = _create_test_session(db, student.id)
        bm = models.ProblemBookmark(
            id=make_id(), student_id=student.id, session_id=session.id,
            problem_snapshot="Bài cần xóa",
        )
        db.add(bm)
        db.commit()
        bm_id = bm.id

        # Xóa
        db.delete(bm)
        db.commit()

        # Kiểm tra đã xóa
        result = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.id == bm_id
        ).first()
        assert result is None
        print("[PASS] Test 7: Xóa bookmark hoạt động đúng")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 8: Cập nhật note
# ──────────────────────────────────────────────────────────
def test_update_note():
    db = get_db()
    student = _create_test_student(db)

    try:
        session = _create_test_session(db, student.id)
        bm = models.ProblemBookmark(
            id=make_id(), student_id=student.id, session_id=session.id,
            problem_snapshot="Bài cần ghi chú", note="Ghi chú ban đầu",
        )
        db.add(bm)
        db.commit()

        # Cập nhật note
        bm.note = "Ghi chú đã chỉnh sửa"
        db.commit()
        db.refresh(bm)

        assert bm.note == "Ghi chú đã chỉnh sửa"
        print("[PASS] Test 8: Cập nhật note bookmark OK")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# TEST 9: Schemas BookmarkCreate và BookmarkResponse hợp lệ
# ──────────────────────────────────────────────────────────
def test_schemas():
    body = schemas.BookmarkCreate(session_id="sess123", note="Ghi chú")
    assert body.session_id == "sess123"

    now = datetime.now(timezone.utc)
    resp = schemas.BookmarkResponse(
        id="bm1", student_id="s1", session_id="sess1",
        session_title="Bài toán 1", problem_snapshot="Đề bài",
        independence_score=80, note="Ghi chú", created_at=now,
    )
    assert resp.independence_score == 80
    print("[PASS] Test 9: Schemas BookmarkCreate và BookmarkResponse hợp lệ")


# ──────────────────────────────────────────────────────────
# TEST 10: Lọc has_attachment
# ──────────────────────────────────────────────────────────
def test_filter_has_attachment():
    db = get_db()
    student = _create_test_student(db)

    try:
        s1 = _create_test_session(db, student.id, "Có ảnh")
        s2 = _create_test_session(db, student.id, "Không ảnh")

        db.add(models.ProblemBookmark(
            id=make_id(), student_id=student.id, session_id=s1.id,
            problem_snapshot="Bài có ảnh", attachment_url="https://img.jpg",
        ))
        db.add(models.ProblemBookmark(
            id=make_id(), student_id=student.id, session_id=s2.id,
            problem_snapshot="Bài không ảnh", attachment_url=None,
        ))
        db.commit()

        with_img = db.query(models.ProblemBookmark).filter(
            models.ProblemBookmark.student_id == student.id,
            models.ProblemBookmark.attachment_url.isnot(None),
        ).all()
        assert len(with_img) == 1 and with_img[0].problem_snapshot == "Bài có ảnh"
        print("[PASS] Test 10: Lọc has_attachment hoạt động đúng")
    finally:
        _cleanup(db, student.id)
        db.close()


# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        test_build_bookmark_snapshot,
        test_build_snapshot_with_attachment,
        test_create_bookmark_db,
        test_bookmark_unique_constraint,
        test_filter_by_score,
        test_search_keyword,
        test_delete_bookmark,
        test_update_note,
        test_schemas,
        test_filter_has_attachment,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Ket qua: {passed}/{passed+failed} PASSED | {failed} FAILED")
    print("=" * 50)
