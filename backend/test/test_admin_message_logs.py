# test/test_admin_message_logs.py
# Kiểm thử đơn vị và tích hợp cho API Nhật ký Tin nhắn (US 10.4 - Task T10.4.7)

import pytest
import asyncio
from database import SessionLocal
from routers.admin_message_logs import (
    get_message_logs,
    get_message_log_stats,
    get_message_conversation,
    _build_filters,
)
from datetime import date


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


def test_build_filters_helper():
    """Kiểm tra helper sinh câu WHERE và params cho filter."""
    where, params = _build_filters(
        agent="SCAFFOLDING",
        search="3x + 10",
        student_id="std_123",
        date_from=date(2026, 11, 1),
        date_to=date(2026, 11, 12),
    )
    assert "ol.target_agent = :agent_filter" in where
    assert params["agent_filter"] == "SCAFFOLDING_AGENT"
    assert "m.content ILIKE :search_kw" in where
    assert params["search_kw"] == "%3x + 10%"
    assert "u.id = :student_id" in where
    assert params["student_id"] == "std_123"
    assert "m.created_at >= :date_from" in where
    assert "m.created_at < :date_to_excl" in where


def test_get_message_log_stats(db_session):
    """Kiểm tra API trả về số liệu thống kê KPI từ cơ sở dữ liệu thực."""
    stats = asyncio.run(get_message_log_stats(db=db_session, _={}))
    assert stats.total_all >= 0
    assert stats.total_today >= 0
    assert stats.parent_alerts_today >= 0
    assert isinstance(stats.agent_distribution, dict)


def test_get_message_logs_pagination(db_session):
    """Kiểm tra phân trang danh sách tin nhắn."""
    res = asyncio.run(get_message_logs(
        page=1,
        page_size=10,
        agent=None,
        search=None,
        student_id=None,
        date_from=None,
        date_to=None,
        db=db_session,
        _={},
    ))
    assert res.success is True
    assert res.page == 1
    assert res.page_size == 10
    assert res.total >= len(res.items)
    assert len(res.items) <= 10

    if res.items:
        first = res.items[0]
        assert hasattr(first, "msg_id")
        assert hasattr(first, "student_question")
        assert hasattr(first, "student_name")
        assert hasattr(first, "target_agent")


def test_get_message_conversation(db_session):
    """Kiểm tra lấy chi tiết toàn bộ hội thoại theo msg_id."""
    res = asyncio.run(get_message_logs(
        page=1,
        page_size=1,
        agent=None,
        search=None,
        student_id=None,
        date_from=None,
        date_to=None,
        db=db_session,
        _={},
    ))
    if not res.items:
        pytest.skip("Chưa có tin nhắn trong database để test hội thoại")

    msg_id = res.items[0].msg_id
    conv = asyncio.run(get_message_conversation(msg_id=msg_id, db=db_session, _={}))
    assert conv.success is True
    assert conv.session_id is not None
    assert isinstance(conv.messages, list)
    assert len(conv.messages) >= 1
