# routers/bookmarks.py
# US 7.2 (Task T7.13): CRUD API /bookmarks — Sổ Tay Bài Toán Yêu Thích
#
# Danh sách endpoint:
#   POST   /bookmarks                  — Học sinh lưu 1 bookmark từ session
#   GET    /bookmarks                  — Lấy danh sách bookmark (hỗ trợ lọc + tìm kiếm)
#   GET    /bookmarks/{bookmark_id}    — Xem chi tiết 1 bookmark
#   PATCH  /bookmarks/{bookmark_id}    — Cập nhật ghi chú (note)
#   DELETE /bookmarks/{bookmark_id}    — Xóa bookmark

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
import dependencies
from database import get_db

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


# ==============================================================================
# HELPER: Tự động điền snapshot/summary khi tạo bookmark
# ==============================================================================

def _build_bookmark_snapshot(session_id: str, db: Session) -> dict:
    """
    Đọc các tin nhắn của session để tạo snapshot đề bài và tóm tắt chat.
    - problem_snapshot: nội dung tin nhắn USER đầu tiên có text (đề bài)
    - attachment_url: ảnh Cloudinary từ tin nhắn USER đầu tiên có ảnh
    - chat_summary: 3 tin nhắn USER đầu tiên nối bằng " | "
    """
    user_messages = (
        db.query(models.Message)
        .filter(
            models.Message.session_id == session_id,
            models.Message.sender_type == "USER",
        )
        .order_by(models.Message.created_at.asc())
        .limit(5)
        .all()
    )

    # Lấy ảnh đề bài từ tin nhắn USER đầu tiên có attachment
    attachment_url: Optional[str] = None
    for msg in user_messages:
        if msg.attachment_url:
            attachment_url = msg.attachment_url
            break

    # Snapshot = nội dung tin nhắn USER đầu tiên
    problem_snapshot: Optional[str] = user_messages[0].content if user_messages else None

    # Chat summary = 3 tin nhắn USER đầu nối " | "
    summary_parts = [m.content for m in user_messages[:3] if m.content]
    chat_summary: Optional[str] = " | ".join(summary_parts) if summary_parts else None

    return {
        "problem_snapshot": problem_snapshot,
        "attachment_url": attachment_url,
        "chat_summary": chat_summary,
    }


def _get_latest_score(session_id: str, student_id: str, db: Session) -> Optional[int]:
    """Lấy điểm tự lực mới nhất của học sinh trong session."""
    score_record = (
        db.query(models.IndependenceScore)
        .filter(
            models.IndependenceScore.session_id == session_id,
            models.IndependenceScore.student_id == student_id,
        )
        .order_by(models.IndependenceScore.created_at.desc())
        .first()
    )
    return score_record.score if score_record else None


# ==============================================================================
# POST /bookmarks — Tạo bookmark mới
# ==============================================================================

@router.post("", response_model=schemas.BookmarkResponse, status_code=201)
def create_bookmark(
    body: schemas.BookmarkCreate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Học sinh lưu một session vào Sổ Tay Bài Toán.

    - Tự động lấy snapshot đề bài (tin nhắn USER đầu) và ảnh Cloudinary từ session.
    - Tự động điền điểm tự lực từ bảng independence_scores.
    - Mỗi học sinh chỉ lưu một bookmark cho mỗi session (unique constraint).
    """
    if current_user.get("role") not in ("STUDENT", "MONITOR"):
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể lưu vào Sổ Tay.")

    student_id = current_user["id"]

    # Kiểm tra session tồn tại và thuộc về học sinh
    session = db.query(models.Session).filter(models.Session.id == body.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session không tồn tại.")
    if session.user_id != student_id:
        raise HTTPException(status_code=403, detail="Session này không thuộc về bạn.")

    # Kiểm tra đã lưu chưa
    existing = (
        db.query(models.ProblemBookmark)
        .filter(
            models.ProblemBookmark.student_id == student_id,
            models.ProblemBookmark.session_id == body.session_id,
        )
        .first()
    )
    if existing:
        # Trả về bookmark đã có (idempotent, không lỗi)
        return schemas.BookmarkResponse(
            id=existing.id,
            student_id=existing.student_id,
            session_id=existing.session_id,
            session_title=session.title,
            problem_snapshot=existing.problem_snapshot,
            attachment_url=existing.attachment_url,
            chat_summary=existing.chat_summary,
            independence_score=existing.independence_score,
            note=existing.note,
            created_at=existing.created_at,
        )

    # Tự động điền snapshot + score
    snapshot = _build_bookmark_snapshot(body.session_id, db)
    independence_score = _get_latest_score(body.session_id, student_id, db)

    bookmark = models.ProblemBookmark(
        id=uuid.uuid4().hex,
        student_id=student_id,
        session_id=body.session_id,
        problem_snapshot=snapshot["problem_snapshot"],
        attachment_url=snapshot["attachment_url"],
        chat_summary=snapshot["chat_summary"],
        independence_score=independence_score,
        note=body.note,
    )
    db.add(bookmark)
    try:
        db.commit()
        db.refresh(bookmark)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bài toán này đã có trong Sổ Tay của bạn.")

    return schemas.BookmarkResponse(
        id=bookmark.id,
        student_id=bookmark.student_id,
        session_id=bookmark.session_id,
        session_title=session.title,
        problem_snapshot=bookmark.problem_snapshot,
        attachment_url=bookmark.attachment_url,
        chat_summary=bookmark.chat_summary,
        independence_score=bookmark.independence_score,
        note=bookmark.note,
        created_at=bookmark.created_at,
    )


# ==============================================================================
# GET /bookmarks — Danh sách bookmark (hỗ trợ lọc)
# ==============================================================================

@router.get("", response_model=list[schemas.BookmarkResponse])
def list_bookmarks(
    search: Optional[str] = Query(None, description="Tìm kiếm theo từ khóa trong snapshot / chat_summary"),
    score_filter: Optional[str] = Query(
        "all",
        description="Lọc theo điểm: 'all' | 'perfect' (>= 80) | 'passed' (>= 60)",
    ),
    has_attachment: Optional[bool] = Query(None, description="Chỉ lấy bookmark có ảnh đề bài"),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(20, ge=1, le=100, description="Số bookmark mỗi trang"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Học sinh xem danh sách Sổ Tay của mình.
    Hỗ trợ:
    - Tìm kiếm full-text trong problem_snapshot và chat_summary
    - Lọc theo mức điểm tự lực (all / perfect / passed)
    - Lọc chỉ hiện bookmark có ảnh đề bài
    - Phân trang
    """
    student_id = current_user["id"]

    query = (
        db.query(models.ProblemBookmark)
        .filter(models.ProblemBookmark.student_id == student_id)
    )

    # Lọc tìm kiếm từ khóa
    if search and search.strip():
        keyword = f"%{search.strip()}%"
        query = query.filter(
            (models.ProblemBookmark.problem_snapshot.ilike(keyword))
            | (models.ProblemBookmark.chat_summary.ilike(keyword))
            | (models.ProblemBookmark.note.ilike(keyword))
        )

    # Lọc theo điểm tự lực
    if score_filter == "perfect":
        query = query.filter(models.ProblemBookmark.independence_score >= 80)
    elif score_filter == "passed":
        query = query.filter(models.ProblemBookmark.independence_score >= 60)

    # Lọc có ảnh đính kèm
    if has_attachment is True:
        query = query.filter(models.ProblemBookmark.attachment_url.isnot(None))

    # Sắp xếp mới nhất lên đầu + phân trang
    offset = (page - 1) * page_size
    bookmarks = (
        query.order_by(models.ProblemBookmark.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # Lấy session title cho từng bookmark
    session_ids = [b.session_id for b in bookmarks]
    sessions = {
        s.id: s for s in db.query(models.Session).filter(models.Session.id.in_(session_ids)).all()
    }

    result = []
    for bm in bookmarks:
        session = sessions.get(bm.session_id)
        result.append(
            schemas.BookmarkResponse(
                id=bm.id,
                student_id=bm.student_id,
                session_id=bm.session_id,
                session_title=session.title if session else None,
                problem_snapshot=bm.problem_snapshot,
                attachment_url=bm.attachment_url,
                chat_summary=bm.chat_summary,
                independence_score=bm.independence_score,
                note=bm.note,
                created_at=bm.created_at,
            )
        )
    return result


# ==============================================================================
# GET /bookmarks/{bookmark_id} — Chi tiết 1 bookmark
# ==============================================================================

@router.get("/{bookmark_id}", response_model=schemas.BookmarkResponse)
def get_bookmark(
    bookmark_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết 1 bookmark theo ID."""
    student_id = current_user["id"]

    bm = db.query(models.ProblemBookmark).filter(models.ProblemBookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark không tồn tại.")
    if bm.student_id != student_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem bookmark này.")

    session = db.query(models.Session).filter(models.Session.id == bm.session_id).first()

    return schemas.BookmarkResponse(
        id=bm.id,
        student_id=bm.student_id,
        session_id=bm.session_id,
        session_title=session.title if session else None,
        problem_snapshot=bm.problem_snapshot,
        attachment_url=bm.attachment_url,
        chat_summary=bm.chat_summary,
        independence_score=bm.independence_score,
        note=bm.note,
        created_at=bm.created_at,
    )


# ==============================================================================
# PATCH /bookmarks/{bookmark_id} — Cập nhật ghi chú
# ==============================================================================

class BookmarkNoteUpdate(schemas.BaseModel if hasattr(schemas, "BaseModel") else object):
    note: Optional[str] = None


# Dùng pydantic trực tiếp
from pydantic import BaseModel

class BookmarkNoteUpdate(BaseModel):
    note: Optional[str] = None


@router.patch("/{bookmark_id}", response_model=schemas.BookmarkResponse)
def update_bookmark_note(
    bookmark_id: str,
    body: BookmarkNoteUpdate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật ghi chú (note) của một bookmark."""
    student_id = current_user["id"]

    bm = db.query(models.ProblemBookmark).filter(models.ProblemBookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark không tồn tại.")
    if bm.student_id != student_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa bookmark này.")

    bm.note = body.note
    db.commit()
    db.refresh(bm)

    session = db.query(models.Session).filter(models.Session.id == bm.session_id).first()

    return schemas.BookmarkResponse(
        id=bm.id,
        student_id=bm.student_id,
        session_id=bm.session_id,
        session_title=session.title if session else None,
        problem_snapshot=bm.problem_snapshot,
        attachment_url=bm.attachment_url,
        chat_summary=bm.chat_summary,
        independence_score=bm.independence_score,
        note=bm.note,
        created_at=bm.created_at,
    )


# ==============================================================================
# DELETE /bookmarks/{bookmark_id} — Xóa bookmark
# ==============================================================================

@router.delete("/{bookmark_id}", status_code=204)
def delete_bookmark(
    bookmark_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Học sinh xóa một bookmark khỏi Sổ Tay.
    Trả về HTTP 204 No Content khi thành công.
    """
    student_id = current_user["id"]

    bm = db.query(models.ProblemBookmark).filter(models.ProblemBookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark không tồn tại.")
    if bm.student_id != student_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bookmark này.")

    db.delete(bm)
    db.commit()
    # 204 No Content — không trả body
