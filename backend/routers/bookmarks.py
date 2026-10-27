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
import collections
import models
import schemas
import dependencies
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from agents.problem_title_generator import generate_friendly_problem_title


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

    # Nếu bài toán kế thừa attachment_url và đối thoại chưa có tin nhắn nào có ảnh,
    # gán attachment_url cho tin nhắn USER đầu tiên
    if attachment_url and not any(d.attachment_url for d in dialogue):
        for d in dialogue:
            if d.sender_type == "USER":
                d.attachment_url = attachment_url
                break

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

    # Nếu bài toán này không đính kèm ảnh riêng, kế thừa ảnh đã gửi trong cùng session
    if not attachment_url:
        prev_attachment = (
            db.query(models.Message.attachment_url)
            .filter(
                models.Message.session_id == session_id,
                models.Message.created_at <= end_time if end_time else True,
                models.Message.attachment_url.isnot(None),
                models.Message.attachment_url != "",
            )
            .order_by(models.Message.created_at.desc())
            .first()
        )
        if prev_attachment and prev_attachment[0]:
            attachment_url = prev_attachment[0]
        else:
            any_attachment = (
                db.query(models.Message.attachment_url)
                .filter(
                    models.Message.session_id == session_id,
                    models.Message.attachment_url.isnot(None),
                    models.Message.attachment_url != "",
                )
                .order_by(models.Message.created_at.asc())
                .first()
            )
            if any_attachment and any_attachment[0]:
                attachment_url = any_attachment[0]

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


def _to_bookmark_response(
    bm: models.ProblemBookmark,
    db: Session,
    session_title: Optional[str] = None,
    playlist_ids: Optional[list[str]] = None,
) -> schemas.BookmarkResponse:
    """Helper chuyển đổi ProblemBookmark model sang BookmarkResponse thống nhất."""
    if playlist_ids is None:
        playlist_ids = [
            row[0]
            for row in db.query(models.BookmarkPlaylistItem.playlist_id)
            .filter(models.BookmarkPlaylistItem.bookmark_id == bm.id)
            .all()
        ]

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
        session_title=session_title,
        problem_snapshot=bm.problem_snapshot,
        attachment_url=bm.attachment_url,
        chat_summary=bm.chat_summary,
        independence_score=bm.independence_score,
        title=bm.title,
        note=bm.note,
        playlist_ids=playlist_ids,
        created_at=bm.created_at,
        dialogue_messages=dialogue_messages,
    )


# ==============================================================================
# POST /bookmarks — Tạo bookmark mới
# ==============================================================================
@router.post("/suggest-title", response_model=schemas.ProblemTitleResult)
def suggest_problem_title(
    body: schemas.ProblemTitleGenerateRequest,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 8.1 - Task T8.3:
    Gọi Prompt Gemini sinh tên bài toán mặc định (friendly_parent_title) chuẩn sư phạm:
    [Lớp X] [Chủ đề] – [Tên dạng toán]
    Dùng làm placeholder gợi ý khi học sinh bấm 'Lưu vào Sổ tay'.
    """
    problem_text = body.problem_text.strip() if body.problem_text else ""
    grade_val = body.grade or current_user.get("grade") or 5

    # Nếu truyền session_id mà chưa có problem_text, tự động trích xuất từ session
    if not problem_text and body.session_id:
        from deduplication import extract_session_problem_text
        problem_text = extract_session_problem_text(db, body.session_id)

    result = generate_friendly_problem_title(problem_text=problem_text, grade=grade_val)
    return result

@router.post("", response_model=schemas.BookmarkResponse, status_code=201)
def create_bookmark(
    body: schemas.BookmarkCreate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Học sinh lưu một bài toán từ session vào Sổ Tay (US 7.2 & US 8.2).
    - Hỗ trợ lưu nhiều bài toán độc lập trong cùng 1 session.
    - Hỗ trợ tiêu đề bài toán (title) do học sinh tự đặt hoặc AI gợi ý.
    - Hỗ trợ lưu ngay vào các danh sách phát (playlist_ids).
    - Tự động lấy snapshot đề bài và ảnh Cloudinary của bài toán đó.
    - Tự động điền điểm tự lực từ bài toán tương ứng.
    - Idempotent: Nếu đã lưu bài toán này rồi, cập nhật title/playlists và trả về.
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

    title_val = body.title.strip() if body.title and body.title.strip() else None

    # US 8.1 (Task T8.3): Nếu học sinh để trống tiêu đề khi lưu, tự động dùng tên AI chuẩn sư phạm
    if not title_val:
        student_grade = current_user.get("grade") or 5
        auto_title_obj = generate_friendly_problem_title(
            problem_text=p_snap or session.title or "Bài toán",
            grade=student_grade
        )
        title_val = auto_title_obj.friendly_parent_title

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
        # Nếu đã có bài, cập nhật title/note nếu có truyền mới
        if title_val and not existing.title:
            existing.title = title_val
        if body.note and not existing.note:
            existing.note = body.note

        # Thêm bài vào các playlist mới được chọn (nếu có)
        if body.playlist_ids:
            valid_pls = (
                db.query(models.BookmarkPlaylist.id)
                .filter(
                    models.BookmarkPlaylist.id.in_(body.playlist_ids),
                    models.BookmarkPlaylist.student_id == student_id,
                )
                .all()
            )
            valid_pids = {r[0] for r in valid_pls}
            curr_pids = {
                r[0]
                for r in db.query(models.BookmarkPlaylistItem.playlist_id)
                .filter(models.BookmarkPlaylistItem.bookmark_id == existing.id)
                .all()
            }
            for pid in valid_pids - curr_pids:
                db.add(
                    models.BookmarkPlaylistItem(
                        id=uuid.uuid4().hex,
                        playlist_id=pid,
                        bookmark_id=existing.id,
                    )
                )

        db.commit()
        db.refresh(existing)
        return _to_bookmark_response(existing, db, session_title=session.title)

    bookmark = models.ProblemBookmark(
        id=uuid.uuid4().hex,
        student_id=student_id,
        session_id=body.session_id,
        problem_snapshot=p_snap,
        attachment_url=att_url,
        chat_summary=snapshot["chat_summary"],
        independence_score=score_val,
        title=title_val,
        note=body.note,
    )
    db.add(bookmark)
    try:
        db.commit()
        db.refresh(bookmark)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bài toán này đã có trong Sổ Tay của bạn.")

    # Thêm vào các danh sách phát nếu có
    if body.playlist_ids:
        valid_pls = (
            db.query(models.BookmarkPlaylist.id)
            .filter(
                models.BookmarkPlaylist.id.in_(body.playlist_ids),
                models.BookmarkPlaylist.student_id == student_id,
            )
            .all()
        )
        for row in valid_pls:
            pid = row[0]
            db.add(
                models.BookmarkPlaylistItem(
                    id=uuid.uuid4().hex,
                    playlist_id=pid,
                    bookmark_id=bookmark.id,
                )
            )
        db.commit()

    # US 8.1 (T8.4): Đồng bộ custom_title vào bảng independence_scores nếu học sinh tự đặt tên
    if body.title and body.title.strip():
        custom_name = body.title.strip()
        score_q = (
            db.query(models.IndependenceScore)
            .filter(
                models.IndependenceScore.student_id == student_id,
                models.IndependenceScore.session_id == body.session_id,
            )
        )
        if body.message_created_at:
            matched_score = (
                score_q.filter(models.IndependenceScore.created_at >= body.message_created_at - timedelta(seconds=10))
                .order_by(models.IndependenceScore.created_at.asc())
                .first()
            )
        else:
            matched_score = score_q.order_by(models.IndependenceScore.created_at.desc()).first()
        if matched_score:
            matched_score.custom_title = custom_name
            db.commit()

    return _to_bookmark_response(bookmark, db, session_title=session.title)


# ==============================================================================
# GET /bookmarks — Danh sách bookmark (hỗ trợ lọc + playlist)
# ==============================================================================

@router.get("", response_model=list[schemas.BookmarkResponse])
def list_bookmarks(
    playlist_id: Optional[str] = Query(None, description="Lọc theo Playlist ID"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo từ khóa trong tiêu đề / snapshot / chat_summary / note"),
    score_filter: Optional[str] = Query(
        "all",
        description="Lọc theo điểm: 'all' | 'perfect' (>= 80) | 'passed' (>= 60)",
    ),
    has_attachment: Optional[bool] = Query(None, description="Chỉ lấy bookmark có ảnh đề bài"),
    page: int = Query(1, ge=1, description="Trang hiện tại"),
    page_size: int = Query(20, ge=1, le=100, description="Số bookmark mỗi trang (mặc định 20, Sổ tay có thể dùng 10)"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Học sinh xem danh sách Sổ Tay của mình (US 7.2 & US 8.2).
    Hỗ trợ:
    - Lọc theo Playlist ID (dành cho Sidebar danh sách Sổ tay phong cách YouTube)
    - Tìm kiếm full-text trong title, problem_snapshot, chat_summary, note
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

    # Lọc theo Playlist ID nếu có
    if playlist_id:
        pl = (
            db.query(models.BookmarkPlaylist)
            .filter(
                models.BookmarkPlaylist.id == playlist_id,
                models.BookmarkPlaylist.student_id == student_id,
            )
            .first()
        )
        if not pl:
            raise HTTPException(status_code=404, detail="Danh sách phát không tồn tại.")
        query = query.join(
            models.BookmarkPlaylistItem,
            models.BookmarkPlaylistItem.bookmark_id == models.ProblemBookmark.id,
        ).filter(models.BookmarkPlaylistItem.playlist_id == playlist_id)

    # Lọc tìm kiếm từ khóa
    if search_str and search_str.strip():
        keyword = f"%{search_str.strip()}%"
        query = query.filter(
            (models.ProblemBookmark.title.ilike(keyword))
            | (models.ProblemBookmark.problem_snapshot.ilike(keyword))
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

    # Batch query danh sách playlist_ids của tất cả bookmarks để tránh N+1
    bm_ids = [b.id for b in bookmarks]
    bm_to_playlists = collections.defaultdict(list)
    if bm_ids:
        pl_items = (
            db.query(
                models.BookmarkPlaylistItem.bookmark_id,
                models.BookmarkPlaylistItem.playlist_id,
            )
            .filter(models.BookmarkPlaylistItem.bookmark_id.in_(bm_ids))
            .all()
        )
        for b_id, p_id in pl_items:
            bm_to_playlists[b_id].append(p_id)

    result = []
    for bm in bookmarks:
        sess = sessions.get(bm.session_id)
        result.append(
            _to_bookmark_response(
                bm,
                db,
                session_title=sess.title if sess else None,
                playlist_ids=bm_to_playlists.get(bm.id, []),
            )
        )
    return result


# ==============================================================================
# PLAYLISTS API — Danh sách phát Sổ Tay YouTube-Style (US 8.2)
# ==============================================================================

def _ensure_default_playlist(student_id: str, db: Session) -> models.BookmarkPlaylist:
    """Tự động tạo playlist mặc định '⭐ Yêu thích' nếu học sinh chưa có playlist nào."""
    default_pl = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.student_id == student_id,
            models.BookmarkPlaylist.is_default == True,
        )
        .first()
    )
    if not default_pl:
        default_pl = models.BookmarkPlaylist(
            id=uuid.uuid4().hex,
            student_id=student_id,
            name="⭐ Yêu thích",
            description="Danh sách các bài toán yêu thích",
            color="#F59E0B",
            is_default=True,
        )
        db.add(default_pl)
        db.commit()
        db.refresh(default_pl)
    return default_pl


@router.get("/playlists", response_model=list[schemas.PlaylistResponse])
def list_playlists(
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lấy danh sách các Playlist của học sinh kèm số lượng bài toán (item_count).
    Tự động khởi tạo playlist mặc định '⭐ Yêu thích' nếu học sinh chưa có playlist nào.
    """
    if current_user.get("role") not in ("STUDENT", "MONITOR"):
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể quản lý Sổ Tay.")

    student_id = current_user["id"]
    _ensure_default_playlist(student_id, db)

    playlists = (
        db.query(models.BookmarkPlaylist)
        .filter(models.BookmarkPlaylist.student_id == student_id)
        .order_by(models.BookmarkPlaylist.is_default.desc(), models.BookmarkPlaylist.created_at.asc())
        .all()
    )

    pl_ids = [p.id for p in playlists]
    counts_query = (
        db.query(
            models.BookmarkPlaylistItem.playlist_id,
            func.count(models.BookmarkPlaylistItem.id).label("cnt"),
        )
        .filter(models.BookmarkPlaylistItem.playlist_id.in_(pl_ids))
        .group_by(models.BookmarkPlaylistItem.playlist_id)
        .all()
    )
    counts = {row[0]: row[1] for row in counts_query}

    result = []
    for pl in playlists:
        result.append(
            schemas.PlaylistResponse(
                id=pl.id,
                student_id=pl.student_id,
                name=pl.name,
                description=pl.description,
                color=pl.color,
                is_default=pl.is_default,
                item_count=counts.get(pl.id, 0),
                created_at=pl.created_at,
                updated_at=pl.updated_at,
            )
        )
    return result


@router.post("/playlists", response_model=schemas.PlaylistResponse, status_code=201)
def create_playlist(
    body: schemas.PlaylistCreate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tạo mới một Playlist (YouTube-style) cho học sinh.
    - Hỗ trợ 'initial_bookmark_id': Tự động lưu ngay bài toán vào danh sách phát sau khi tạo.
    """
    if current_user.get("role") not in ("STUDENT", "MONITOR"):
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể tạo danh sách phát.")

    student_id = current_user["id"]
    name_clean = body.name.strip()
    if not name_clean:
        raise HTTPException(status_code=400, detail="Tên danh sách phát không được để trống.")

    # Kiểm tra trùng tên playlist của học sinh
    existing = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.student_id == student_id,
            func.lower(models.BookmarkPlaylist.name) == name_clean.lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Bạn đã có danh sách bài toán tên '{name_clean}'.")

    # Kiểm tra initial_bookmark_id nếu có
    if body.initial_bookmark_id:
        bm = (
            db.query(models.ProblemBookmark)
            .filter(
                models.ProblemBookmark.id == body.initial_bookmark_id,
                models.ProblemBookmark.student_id == student_id,
            )
            .first()
        )
        if not bm:
            raise HTTPException(status_code=404, detail="Bài toán cần thêm không tồn tại hoặc không thuộc về bạn.")

    playlist = models.BookmarkPlaylist(
        id=uuid.uuid4().hex,
        student_id=student_id,
        name=name_clean,
        description=body.description,
        color=body.color or "#F59E0B",
        is_default=False,
    )
    db.add(playlist)
    db.flush()

    item_count = 0
    if body.initial_bookmark_id:
        item = models.BookmarkPlaylistItem(
            id=uuid.uuid4().hex,
            playlist_id=playlist.id,
            bookmark_id=body.initial_bookmark_id,
            position=0,
        )
        db.add(item)
        item_count = 1

    db.commit()
    db.refresh(playlist)

    return schemas.PlaylistResponse(
        id=playlist.id,
        student_id=playlist.student_id,
        name=playlist.name,
        description=playlist.description,
        color=playlist.color,
        is_default=playlist.is_default,
        item_count=item_count,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at,
    )


@router.get("/playlists/{playlist_id}", response_model=schemas.PlaylistDetailResponse)
def get_playlist_detail(
    playlist_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết một Playlist kèm danh sách các bài toán bên trong."""
    student_id = current_user["id"]
    pl = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.id == playlist_id,
            models.BookmarkPlaylist.student_id == student_id,
        )
        .first()
    )
    if not pl:
        raise HTTPException(status_code=404, detail="Danh sách phát không tồn tại.")

    items_query = (
        db.query(models.ProblemBookmark)
        .join(models.BookmarkPlaylistItem, models.BookmarkPlaylistItem.bookmark_id == models.ProblemBookmark.id)
        .filter(models.BookmarkPlaylistItem.playlist_id == playlist_id)
        .order_by(models.BookmarkPlaylistItem.added_at.desc())
        .all()
    )

    session_ids = [b.session_id for b in items_query]
    sessions = {
        s.id: s for s in db.query(models.Session).filter(models.Session.id.in_(session_ids)).all()
    }

    bm_ids = [b.id for b in items_query]
    bm_to_playlists = collections.defaultdict(list)
    if bm_ids:
        pl_items = (
            db.query(
                models.BookmarkPlaylistItem.bookmark_id,
                models.BookmarkPlaylistItem.playlist_id,
            )
            .filter(models.BookmarkPlaylistItem.bookmark_id.in_(bm_ids))
            .all()
        )
        for b_id, p_id in pl_items:
            bm_to_playlists[b_id].append(p_id)

    bookmark_responses = []
    for bm in items_query:
        sess = sessions.get(bm.session_id)
        bookmark_responses.append(
            _to_bookmark_response(
                bm,
                db,
                session_title=sess.title if sess else None,
                playlist_ids=bm_to_playlists.get(bm.id, []),
            )
        )

    return schemas.PlaylistDetailResponse(
        id=pl.id,
        student_id=pl.student_id,
        name=pl.name,
        description=pl.description,
        color=pl.color,
        is_default=pl.is_default,
        item_count=len(bookmark_responses),
        created_at=pl.created_at,
        updated_at=pl.updated_at,
        items=bookmark_responses,
    )


@router.patch("/playlists/{playlist_id}", response_model=schemas.PlaylistResponse)
def update_playlist(
    playlist_id: str,
    body: schemas.PlaylistUpdate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật tên, mô tả hoặc màu của Playlist."""
    student_id = current_user["id"]
    pl = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.id == playlist_id,
            models.BookmarkPlaylist.student_id == student_id,
        )
        .first()
    )
    if not pl:
        raise HTTPException(status_code=404, detail="Danh sách phát không tồn tại.")

    if body.name is not None:
        name_clean = body.name.strip()
        if not name_clean:
            raise HTTPException(status_code=400, detail="Tên danh sách phát không được để trống.")
        duplicate = (
            db.query(models.BookmarkPlaylist)
            .filter(
                models.BookmarkPlaylist.student_id == student_id,
                models.BookmarkPlaylist.id != playlist_id,
                func.lower(models.BookmarkPlaylist.name) == name_clean.lower(),
            )
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail=f"Bạn đã có danh sách bài toán tên '{name_clean}'.")
        pl.name = name_clean

    if body.description is not None:
        pl.description = body.description

    if body.color is not None:
        pl.color = body.color

    db.commit()
    db.refresh(pl)

    cnt = (
        db.query(func.count(models.BookmarkPlaylistItem.id))
        .filter(models.BookmarkPlaylistItem.playlist_id == playlist_id)
        .scalar()
    ) or 0

    return schemas.PlaylistResponse(
        id=pl.id,
        student_id=pl.student_id,
        name=pl.name,
        description=pl.description,
        color=pl.color,
        is_default=pl.is_default,
        item_count=cnt,
        created_at=pl.created_at,
        updated_at=pl.updated_at,
    )


@router.delete("/playlists/{playlist_id}", status_code=204)
def delete_playlist(
    playlist_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Xóa một Playlist.
    Chỉ xóa danh sách phát và các liên kết; các bài toán gốc trong Sổ Tay vẫn được bảo toàn.
    """
    student_id = current_user["id"]
    pl = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.id == playlist_id,
            models.BookmarkPlaylist.student_id == student_id,
        )
        .first()
    )
    if not pl:
        raise HTTPException(status_code=404, detail="Danh sách phát không tồn tại.")

    db.delete(pl)
    db.commit()


@router.post("/playlists/{playlist_id}/items", status_code=201)
def add_item_to_playlist(
    playlist_id: str,
    body: schemas.PlaylistItemAdd,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Thêm một bài toán vào Playlist (YouTube-style checkbox)."""
    student_id = current_user["id"]
    pl = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.id == playlist_id,
            models.BookmarkPlaylist.student_id == student_id,
        )
        .first()
    )
    if not pl:
        raise HTTPException(status_code=404, detail="Danh sách phát không tồn tại.")

    bm = (
        db.query(models.ProblemBookmark)
        .filter(
            models.ProblemBookmark.id == body.bookmark_id,
            models.ProblemBookmark.student_id == student_id,
        )
        .first()
    )
    if not bm:
        raise HTTPException(status_code=404, detail="Bài toán không tồn tại hoặc không thuộc về bạn.")

    existing_item = (
        db.query(models.BookmarkPlaylistItem)
        .filter(
            models.BookmarkPlaylistItem.playlist_id == playlist_id,
            models.BookmarkPlaylistItem.bookmark_id == body.bookmark_id,
        )
        .first()
    )
    if not existing_item:
        item = models.BookmarkPlaylistItem(
            id=uuid.uuid4().hex,
            playlist_id=playlist_id,
            bookmark_id=body.bookmark_id,
            position=0,
        )
        db.add(item)
        db.commit()

    return {
        "message": "Đã thêm bài toán vào danh sách phát.",
        "playlist_id": playlist_id,
        "bookmark_id": body.bookmark_id,
    }


@router.delete("/playlists/{playlist_id}/items/{bookmark_id}", status_code=204)
def remove_item_from_playlist(
    playlist_id: str,
    bookmark_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa một bài toán khỏi Playlist."""
    student_id = current_user["id"]
    pl = (
        db.query(models.BookmarkPlaylist)
        .filter(
            models.BookmarkPlaylist.id == playlist_id,
            models.BookmarkPlaylist.student_id == student_id,
        )
        .first()
    )
    if not pl:
        raise HTTPException(status_code=404, detail="Danh sách phát không tồn tại.")

    item = (
        db.query(models.BookmarkPlaylistItem)
        .filter(
            models.BookmarkPlaylistItem.playlist_id == playlist_id,
            models.BookmarkPlaylistItem.bookmark_id == bookmark_id,
        )
        .first()
    )
    if item:
        db.delete(item)
        db.commit()


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
    return _to_bookmark_response(bm, db, session_title=session.title if session else None)


# ==============================================================================
# PATCH /bookmarks/{bookmark_id} — Cập nhật tiêu đề, ghi chú hoặc playlist
# ==============================================================================

# Giữ alias BookmarkNoteUpdate để tương thích ngược nếu có import ngoài
BookmarkNoteUpdate = schemas.BookmarkUpdate


@router.patch("/{bookmark_id}", response_model=schemas.BookmarkResponse)
def update_bookmark(
    bookmark_id: str,
    body: schemas.BookmarkUpdate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cập nhật thông tin bookmark (US 7.2 & US 8.2):
    - Tên bài toán (title) do học sinh tự đặt hoặc sửa lại theo ý mình
    - Ghi chú (note)
    - Danh sách các playlist bài này thuộc về (playlist_ids)
    """
    student_id = current_user["id"]

    bm = db.query(models.ProblemBookmark).filter(models.ProblemBookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark không tồn tại.")
    if bm.student_id != student_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa bookmark này.")

    if body.title is not None:
        clean_title = body.title.strip() if body.title.strip() else None
        bm.title = clean_title
        # US 8.1 - T8.4: Đồng bộ custom_title vào bảng independence_scores
        score_rec = (
            db.query(models.IndependenceScore)
            .filter(
                models.IndependenceScore.student_id == bm.student_id,
                models.IndependenceScore.session_id == bm.session_id,
            )
            .order_by(models.IndependenceScore.created_at.desc())
            .first()
        )
        if score_rec:
            score_rec.custom_title = clean_title

    if body.note is not None:
        bm.note = body.note

    if body.playlist_ids is not None:
        # Xác thực các playlist đều thuộc quyền sở hữu của học sinh
        valid_pls = (
            db.query(models.BookmarkPlaylist.id)
            .filter(
                models.BookmarkPlaylist.id.in_(body.playlist_ids),
                models.BookmarkPlaylist.student_id == student_id,
            )
            .all()
        )
        valid_pids = {row[0] for row in valid_pls}

        curr_items = (
            db.query(models.BookmarkPlaylistItem)
            .filter(models.BookmarkPlaylistItem.bookmark_id == bookmark_id)
            .all()
        )
        curr_pids = {item.playlist_id for item in curr_items}

        # Xóa các playlist bị uncheck
        for item in curr_items:
            if item.playlist_id not in valid_pids:
                db.delete(item)

        # Thêm các playlist mới được check
        for pid in valid_pids - curr_pids:
            db.add(
                models.BookmarkPlaylistItem(
                    id=uuid.uuid4().hex,
                    playlist_id=pid,
                    bookmark_id=bookmark_id,
                )
            )

    db.commit()
    db.refresh(bm)

    session = db.query(models.Session).filter(models.Session.id == bm.session_id).first()
    return _to_bookmark_response(bm, db, session_title=session.title if session else None)


# Alias tương thích hàm cũ
update_bookmark_note = update_bookmark


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
    Tự động cascade xóa khỏi tất cả các danh sách phát liên kết.
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

