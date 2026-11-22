# routers/admin_message_logs.py
# US 10.4 (Task T10.4.7): Nhật ký Tin nhắn — hiển thị toàn bộ tin nhắn thực của học sinh
# kèm agent được chọn, lý do điều phối, và thông tin phụ huynh

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, datetime, timezone

import dependencies
from database import get_db
from schemas import (
    MessageLogItem,
    MessageLogListResponse,
    MessageLogStats,
    MessageLogConversationItem,
    MessageLogConversationResponse,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin - Nhật ký Tin nhắn"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Build filter SQL fragments
# ─────────────────────────────────────────────────────────────────────────────

def _build_filters(
    agent: Optional[str],
    search: Optional[str],
    student_id: Optional[str],
    date_from: Optional[date],
    date_to: Optional[date],
) -> tuple[str, dict]:
    """Trả về (WHERE clause phụ, params dict) để inject vào query chính."""
    conditions = []
    params: dict = {}

    if agent and agent.strip():
        # Hỗ trợ cả "SCAFFOLDING", "SCAFFOLDING_AGENT" và "UNLOGGED" (tin cũ chưa có log)
        agent_val = agent.upper().strip()
        if agent_val in ("UNLOGGED", "NULL", "CHUA_LOG", "CHUA_GHI_LOG", "UNKNOWN_AGENT"):
            conditions.append("ol.target_agent IS NULL")
        else:
            if not agent_val.endswith("_AGENT"):
                agent_val += "_AGENT"
            conditions.append("ol.target_agent = :agent_filter")
            params["agent_filter"] = agent_val

    if search and search.strip():
        conditions.append("m.content ILIKE :search_kw")
        params["search_kw"] = f"%{search.strip()}%"

    if student_id and student_id.strip():
        conditions.append("u.id = :student_id")
        params["student_id"] = student_id.strip()

    if date_from:
        conditions.append("m.created_at >= :date_from")
        params["date_from"] = datetime(date_from.year, date_from.month, date_from.day, 0, 0, 0, tzinfo=timezone.utc)

    if date_to:
        conditions.append("m.created_at < :date_to_excl")
        # Lấy đến cuối ngày date_to
        params["date_to_excl"] = datetime(date_to.year, date_to.month, date_to.day + 1, 0, 0, 0, tzinfo=timezone.utc)

    where_extra = (" AND " + " AND ".join(conditions)) if conditions else ""
    return where_extra, params


# ─────────────────────────────────────────────────────────────────────────────
# BASE QUERY — messages JOIN sessions JOIN users LEFT JOIN LATERAL orchestrator_logs
# ─────────────────────────────────────────────────────────────────────────────

_BASE_SELECT = """
    SELECT
        m.id::text                 AS msg_id,
        m.content                  AS student_question,
        m.created_at               AS msg_time,
        u.id::text                 AS user_id,
        u.username                 AS student_name,
        u.email                    AS student_email,
        u.grade,
        s.id::text                 AS session_id,
        s.title                    AS session_title,
        ol.id::text                AS log_id,
        ol.target_agent,
        ol.reason                  AS routing_reason,
        ol.notify_parent
    FROM messages m
    JOIN sessions s   ON m.session_id = s.id
    JOIN users u      ON s.user_id = u.id
    LEFT JOIN LATERAL (
        SELECT id, target_agent, reason, notify_parent
        FROM orchestrator_logs ol2
        WHERE ol2.session_id = m.session_id
          AND ol2.user_query  = m.content
        ORDER BY ol2.created_at DESC
        LIMIT 1
    ) ol ON TRUE
    WHERE m.sender_type = 'USER'
      AND u.role = 'STUDENT'
"""


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/message-logs  — Danh sách tin nhắn có phân trang & filter
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/message-logs", response_model=MessageLogListResponse)
async def get_message_logs(
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    page_size: int = Query(20, ge=5, le=100, description="Số dòng mỗi trang"),
    agent: Optional[str] = Query(None, description="Lọc theo agent: SCAFFOLDING | MISCONCEPTION | SAFETY | KNOWLEDGE_TRACING"),
    search: Optional[str] = Query(None, description="Tìm theo nội dung câu hỏi"),
    student_id: Optional[str] = Query(None, description="Lọc theo ID học sinh"),
    date_from: Optional[date] = Query(None, description="Từ ngày (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Đến ngày (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: dict = Depends(dependencies.require_role(["ADMIN"])),
):
    where_extra, params = _build_filters(agent, search, student_id, date_from, date_to)

    # Count total
    count_sql = text(f"SELECT COUNT(*) FROM ({_BASE_SELECT}{where_extra}) AS sub")
    total: int = db.execute(count_sql, params).scalar() or 0

    # Data page
    offset = (page - 1) * page_size
    data_sql = text(
        f"{_BASE_SELECT}{where_extra}"
        f" ORDER BY m.created_at DESC"
        f" OFFSET :offset LIMIT :page_size"
    )
    params["offset"] = offset
    params["page_size"] = page_size

    rows = db.execute(data_sql, params).mappings().all()

    items = [
        MessageLogItem(
            msg_id=str(r["msg_id"]),
            student_question=r["student_question"] or "",
            msg_time=r["msg_time"],
            user_id=str(r["user_id"]),
            student_name=r["student_name"] or "",
            student_email=r["student_email"],
            grade=r["grade"],
            session_id=str(r["session_id"]),
            session_title=r["session_title"],
            log_id=str(r["log_id"]) if r["log_id"] else None,
            target_agent=r["target_agent"],
            routing_reason=r["routing_reason"],
            notify_parent=r["notify_parent"],
        )
        for r in rows
    ]

    return MessageLogListResponse(
        success=True,
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/message-logs/stats  — KPI cards
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/message-logs/stats", response_model=MessageLogStats)
async def get_message_log_stats(
    db: Session = Depends(get_db),
    _: dict = Depends(dependencies.require_role(["ADMIN"])),
):
    # Tổng tin nhắn hôm nay
    today_sql = text("""
        SELECT COUNT(*) FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE m.sender_type = 'USER'
          AND u.role = 'STUDENT'
          AND m.created_at >= CURRENT_DATE
    """)
    total_today: int = db.execute(today_sql).scalar() or 0

    # Tổng tất cả
    all_sql = text("""
        SELECT COUNT(*) FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE m.sender_type = 'USER'
          AND u.role = 'STUDENT'
    """)
    total_all: int = db.execute(all_sql).scalar() or 0

    # Phân bổ theo agent (toàn bộ)
    dist_sql = text("""
        SELECT
            COALESCE(ol.target_agent, 'UNLOGGED') AS agent,
            COUNT(*) AS cnt
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        LEFT JOIN LATERAL (
            SELECT target_agent
            FROM orchestrator_logs ol2
            WHERE ol2.session_id = m.session_id
              AND ol2.user_query  = m.content
            ORDER BY ol2.created_at DESC
            LIMIT 1
        ) ol ON TRUE
        WHERE m.sender_type = 'USER'
          AND u.role = 'STUDENT'
        GROUP BY COALESCE(ol.target_agent, 'UNLOGGED')
    """)
    dist_rows = db.execute(dist_sql).mappings().all()
    agent_distribution: dict[str, int] = {r["agent"]: r["cnt"] for r in dist_rows}

    # Tin nhắn có cảnh báo phụ huynh hôm nay
    alert_sql = text("""
        SELECT COUNT(*) FROM orchestrator_logs
        WHERE notify_parent = TRUE
          AND created_at >= CURRENT_DATE
    """)
    parent_alerts_today: int = db.execute(alert_sql).scalar() or 0

    # Tổng phiên học hôm nay
    sessions_today_sql = text("""
        SELECT COUNT(DISTINCT s.id) FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE u.role = 'STUDENT'
          AND s.created_at >= CURRENT_DATE
    """)
    sessions_today: int = db.execute(sessions_today_sql).scalar() or 0

    return MessageLogStats(
        total_today=total_today,
        total_all=total_all,
        agent_distribution=agent_distribution,
        parent_alerts_today=parent_alerts_today,
        sessions_today=sessions_today,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/message-logs/{msg_id}/conversation  — Chi tiết cuộc hội thoại
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/message-logs/{msg_id}/conversation", response_model=MessageLogConversationResponse)
async def get_message_conversation(
    msg_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(dependencies.require_role(["ADMIN"])),
):
    # Lấy session_id của tin nhắn
    session_sql = text("""
        SELECT m.session_id, s.title, u.username, u.email, u.grade
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE m.id = :msg_id
        LIMIT 1
    """)
    meta = db.execute(session_sql, {"msg_id": msg_id}).mappings().first()
    if not meta:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin nhắn")

    session_id = meta["session_id"]

    # Lấy toàn bộ messages trong session đó
    conv_sql = text("""
        SELECT
            m.id          AS msg_id,
            m.sender_type,
            m.content,
            m.created_at,
            m.attachment_url
        FROM messages m
        WHERE m.session_id = :session_id
        ORDER BY m.created_at ASC
    """)
    conv_rows = db.execute(conv_sql, {"session_id": session_id}).mappings().all()

    messages_out = [
        MessageLogConversationItem(
            msg_id=str(r["msg_id"]),
            sender_type=r["sender_type"],
            content=r["content"] or "",
            created_at=r["created_at"],
            attachment_url=r["attachment_url"],
        )
        for r in conv_rows
    ]

    return MessageLogConversationResponse(
        success=True,
        session_id=str(session_id),
        session_title=meta["title"],
        student_name=meta["username"],
        student_email=meta["email"],
        grade=meta["grade"],
        messages=messages_out,
    )

