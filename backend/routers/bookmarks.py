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
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import schemas
import dependencies
from database import get_db

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


# ==============================================================================
# HELPER: Tự động điền snapshot/summary & trích xuất đối thoại chuẩn từng bài
# ==============================================================================

HIDDEN_PROMPTS = (
    "Hoc sinh chua hieu cach giai thich tren. Hay giai thich lai theo cach khac, don gian va de hieu hon.",
    "Hoc sinh van chua hieu sau nhieu lan giai thich. Hay dua ra dap an chinh xac va giai thich tung buoc that ro rang.",
)

def _to_epoch(dt: datetime) -> float:
    """Helper chuyển datetime sang epoch timestamp để so sánh mốc an toàn cả aware và naive."""
    return dt.timestamp() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).timestamp()


def _extract_bookmark_dialogue(
    session_id: str,
    db: Session,
    bookmark_created_at: Optional[datetime] = None,
    problem_snapshot: Optional[str] = None,
    attachment_url: Optional[str] = None,
) -> list[schemas.ProblemDialogueMessage]:
    """
    Trích xuất toàn bộ chuỗi đối thoại của riêng bài toán được bookmark:
    Từ câu hỏi / đề bài ban đầu của con -> các bước AI gợi mở Socratic -> con suy luận -> đến khi ra đáp án.
    Tái sử dụng cơ chế phân định ranh giới bài toán theo mốc IndependenceScore (tương tự Dashboard Phụ huynh).
    """
    all_scores = (
        db.query(models.IndependenceScore)
        .filter(models.IndependenceScore.session_id == session_id)
        .order_by(models.IndependenceScore.created_at.asc(), models.IndependenceScore.id.asc())
        .all()
    )

    prev_time = None
    end_time = None

    if all_scores:
        matched_score = None
        matched_idx = -1

        # 1. Nếu có problem_snapshot hoặc attachment_url, ưu tiên tìm bài toán có đề bài khớp
        if problem_snapshot or attachment_url:
            for i, score in enumerate(all_scores):
                e_t = score.created_at + timedelta(seconds=5)
                p_t = all_scores[i - 1].created_at if i > 0 else None
                m_q = (
                    db.query(models.Message)
                    .filter(
                        models.Message.session_id == session_id,
                        models.Message.sender_type == "USER",
                        models.Message.created_at <= e_t,
                    )
                )
                if p_t:
                    m_q = m_q.filter(models.Message.created_at > p_t)
                first_user_msg = m_q.order_by(models.Message.created_at.asc()).first()
                if first_user_msg:
                    if problem_snapshot and first_user_msg.content == problem_snapshot:
                        matched_score = score
                        matched_idx = i
                        break
                    if not problem_snapshot and attachment_url and first_user_msg.attachment_url == attachment_url:
                        matched_score = score
                        matched_idx = i
                        break

        # 2. Nếu chưa khớp và có bookmark_created_at, tìm score gần mốc bookmark_created_at nhất
        if not matched_score and bookmark_created_at:
            b_epoch = _to_epoch(bookmark_created_at)
            # Chỉ xét các score tạo ra trước hoặc ngay tại thời điểm lưu bookmark (+15s)
            candidate_scores = [s for s in all_scores if _to_epoch(s.created_at) <= b_epoch + 15]
            if candidate_scores:
                matched_score = max(candidate_scores, key=lambda s: _to_epoch(s.created_at))
                matched_idx = all_scores.index(matched_score)

        # 3. Fallback: lấy score cuối cùng (bài mới nhất)
        if not matched_score:
            matched_score = all_scores[-1]
            matched_idx = len(all_scores) - 1

        end_time = matched_score.created_at + timedelta(seconds=5)
        if matched_idx > 0:
            prev_time = all_scores[matched_idx - 1].created_at
    elif bookmark_created_at:
        end_time = bookmark_created_at + timedelta(seconds=5)

    msg_query = db.query(models.Message).filter(models.Message.session_id == session_id)
    if end_time:
        msg_query = msg_query.filter(models.Message.created_at <= end_time)
    if prev_time:
        msg_query = msg_query.filter(models.Message.created_at > prev_time)

    raw_msgs = msg_query.order_by(models.Message.created_at.asc()).all()

    if not raw_msgs:
        raw_msgs = (
            db.query(models.Message)
            .filter(models.Message.session_id == session_id)
            .order_by(models.Message.created_at.asc())
            .all()
        )

    dialogue: list[schemas.ProblemDialogueMessage] = []
    for m in raw_msgs:
        if m.sender_type not in ("USER", "AGENT_TUTOR"):
            continue
        if not m.content:
            continue
        content_str = m.content.strip()
        if any(hp in content_str for hp in HIDDEN_PROMPTS):
            continue
        if content_str.startswith("[") and content_str.endswith("]") and "Chua hieu" in content_str:
            continue
        dialogue.append(
            schemas.ProblemDialogueMessage(
                sender_type=m.sender_type,
                content=m.content,
                attachment_url=m.attachment_url,
                created_at=m.created_at,
            )
        )

    return dialogue


def _build_bookmark_snapshot(
    session_id: str,
    db: Session,
    target_time: Optional[datetime] = None,
) -> dict:
    """
    Đọc các tin nhắn của session để tạo snapshot đề bài và tóm tắt chat.
    Tự động phân định ranh giới nếu trong session có nhiều bài toán đã giải (tương tự get_child_problems).
    - problem_snapshot: nội dung tin nhắn USER đầu tiên của bài toán này
    - attachment_url: ảnh Cloudinary từ tin nhắn USER đầu tiên có ảnh của bài này
    - chat_summary: các tin nhắn USER của bài toán này nối bằng " | "
    - independence_score: điểm tự lực của bài toán này
    """
    all_scores = (
        db.query(models.IndependenceScore)
        .filter(models.IndependenceScore.session_id == session_id)
        .order_by(models.IndependenceScore.created_at.asc(), models.IndependenceScore.id.asc())
        .all()
    )

    target_score = None
    target_idx = -1
    prev_time = None
    end_time = None

    if all_scores:
        if target_time:
            t_epoch = _to_epoch(target_time)
            # Tìm score gần với target_time nhất
            target_score = min(all_scores, key=lambda s: abs(_to_epoch(s.created_at) - t_epoch))
            target_idx = all_scores.index(target_score)
        else:
            target_score = all_scores[-1]
            target_idx = len(all_scores) - 1

        end_time = target_score.created_at + timedelta(seconds=5)
        if target_idx > 0:
            prev_time = all_scores[target_idx - 1].created_at

    msg_query = (
        db.query(models.Message)
        .filter(
            models.Message.session_id == session_id,
            models.Message.sender_type == "USER",
        )
    )
    if end_time:
        msg_query = msg_query.filter(models.Message.created_at <= end_time)
    if prev_time:
        msg_query = msg_query.filter(models.Message.created_at > prev_time)

    user_messages = msg_query.order_by(models.Message.created_at.asc()).all()

    if not user_messages:
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

    # Snapshot = nội dung tin nhắn USER đầu tiên của bài này
    problem_snapshot: Optional[str] = user_messages[0].content if user_messages else None

    # Chat summary = các tin nhắn USER đầu nối " | "
    summary_parts = [m.content for m in user_messages[:3] if m.content]
    chat_summary: Optional[str] = " | ".join(summary_parts) if summary_parts else None

    score_val = target_score.score if target_score else None

    return {
        "problem_snapshot": problem_snapshot,
        "attachment_url": attachment_url,
        "chat_summary": chat_summary,
        "independence_score": score_val,
        "target_score": target_score,
    }


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
    Học sinh lưu một bài toán từ session vào Sổ Tay.
    - Hỗ trợ lưu nhiều bài toán độc lập trong cùng 1 session (chia ranh giới theo IndependenceScore như bên phụ huynh).
    - Tự động lấy snapshot đề bài (tin nhắn USER đầu) và ảnh Cloudinary của bài toán đó.
    - Tự động điền điểm tự lực từ bài toán tương ứng.
    - Idempotent: Nếu đã lưu bài toán này rồi, trả về bookmark đã có thay vì báo lỗi.
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

    # Tự động điền snapshot + score của bài toán theo mốc message_created_at
    snapshot = _build_bookmark_snapshot(body.session_id, db, target_time=body.message_created_at)
    p_snap = snapshot["problem_snapshot"]
    att_url = snapshot["attachment_url"]
    score_val = snapshot["independence_score"]

    # Kiểm tra xem bài toán này đã được lưu trong session chưa (so khớp đề bài / ảnh)
    existing_bookmarks = (
        db.query(models.ProblemBookmark)
        .filter(
            models.ProblemBookmark.student_id == student_id,
            models.ProblemBookmark.session_id == body.session_id,
        )
        .all()
    )
    existing = None
    for bm in existing_bookmarks:
        if p_snap and bm.problem_snapshot == p_snap:
            existing = bm
            break
        if not p_snap and att_url and bm.attachment_url == att_url:
            existing = bm
            break

    if existing:
        # Trả về bookmark đã có (idempotent, không lỗi)
        dialogue_messages = _extract_bookmark_dialogue(
            existing.session_id,
            db,
            bookmark_created_at=existing.created_at,
            problem_snapshot=existing.problem_snapshot,
            attachment_url=existing.attachment_url,
        )
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
            dialogue_messages=dialogue_messages,
        )

    bookmark = models.ProblemBookmark(
        id=uuid.uuid4().hex,
        student_id=student_id,
        session_id=body.session_id,
        problem_snapshot=p_snap,
        attachment_url=att_url,
        chat_summary=snapshot["chat_summary"],
        independence_score=score_val,
        note=body.note,
    )
    db.add(bookmark)
    try:
        db.commit()
        db.refresh(bookmark)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bài toán này đã có trong Sổ Tay của bạn.")

    dialogue_messages = _extract_bookmark_dialogue(
        bookmark.session_id,
        db,
        bookmark_created_at=bookmark.created_at,
        problem_snapshot=bookmark.problem_snapshot,
        attachment_url=bookmark.attachment_url,
    )
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
        dialogue_messages=dialogue_messages,
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

    search_str = search if isinstance(search, str) else None
    score_filter_str = score_filter if isinstance(score_filter, str) else "all"
    has_att = has_attachment if isinstance(has_attachment, bool) else None
    p_num = page if isinstance(page, int) else 1
    p_size = page_size if isinstance(page_size, int) else 20

    query = (
        db.query(models.ProblemBookmark)
        .filter(models.ProblemBookmark.student_id == student_id)
    )

    # Lọc tìm kiếm từ khóa
    if search_str and search_str.strip():
        keyword = f"%{search_str.strip()}%"
        query = query.filter(
            (models.ProblemBookmark.problem_snapshot.ilike(keyword))
            | (models.ProblemBookmark.chat_summary.ilike(keyword))
            | (models.ProblemBookmark.note.ilike(keyword))
        )

    # Lọc theo điểm tự lực
    if score_filter_str == "perfect":
        query = query.filter(models.ProblemBookmark.independence_score >= 80)
    elif score_filter_str == "passed":
        query = query.filter(models.ProblemBookmark.independence_score >= 60)

    # Lọc có ảnh đính kèm
    if has_att is True:
        query = query.filter(models.ProblemBookmark.attachment_url.isnot(None))

    # Sắp xếp mới nhất lên đầu + phân trang
    offset = (p_num - 1) * p_size
    bookmarks = (
        query.order_by(models.ProblemBookmark.created_at.desc())
        .offset(offset)
        .limit(p_size)
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
        dialogue_messages = _extract_bookmark_dialogue(
            bm.session_id,
            db,
            bookmark_created_at=bm.created_at,
            problem_snapshot=bm.problem_snapshot,
            attachment_url=bm.attachment_url,
        )
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
                dialogue_messages=dialogue_messages,
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
    dialogue_messages = _extract_bookmark_dialogue(
        bm.session_id,
        db,
        bookmark_created_at=bm.created_at,
        problem_snapshot=bm.problem_snapshot,
        attachment_url=bm.attachment_url,
    )

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
        dialogue_messages=dialogue_messages,
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
    dialogue_messages = _extract_bookmark_dialogue(bm.session_id, bm.created_at, db)

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
        dialogue_messages=dialogue_messages,
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
