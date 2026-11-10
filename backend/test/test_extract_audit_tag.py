"""
US 10.4 - Task T10.4.2:
Bộ kiểm thử Hàm bóc tách thẻ ẩn Regex, Bộ lọc Stream Sanitizer & Lưu DB audit_feedback_logs.

Chạy:
    python -m pytest backend/test/test_extract_audit_tag.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router import extract_audit_tag, sanitize_stream_chunks
from database import SessionLocal
import models
from orchestrator_bridge import save_audit_feedback_log


def test_extract_valid_audit_tags():
    """Kiểm tra bóc tách thành công 4 nhãn Agent hợp lệ."""
    for agent in ["MISCONCEPTION", "KNOWLEDGE_TRACING", "SAFETY", "SCAFFOLDING"]:
        raw = f"Lời giảng sư phạm của Thầy.\n<!-- AUDIT_AGENT: {agent} -->"
        clean, tag = extract_audit_tag(raw)
        assert tag == agent
        assert clean == "Lời giảng sư phạm của Thầy."
        assert "<!-- AUDIT_AGENT:" not in clean


def test_extract_tag_with_whitespace_variations():
    """Kiểm tra độ linh hoạt của Regex với các biến thể khoảng trắng và chữ thường."""
    variations = [
        ("Câu trả lời.\n<!--AUDIT_AGENT:MISCONCEPTION-->", "MISCONCEPTION"),
        ("Câu trả lời.\n<!--  AUDIT_AGENT :  SAFETY  -->", "SAFETY"),
        ("Câu trả lời.\n<!-- audit_agent: knowledge_tracing -->", "KNOWLEDGE_TRACING"),
        ("Câu trả lời.\n<!-- AUDIT_AGENT: SCAFFOLDING_AGENT -->", "SCAFFOLDING"),
    ]
    for raw, expected in variations:
        clean, tag = extract_audit_tag(raw)
        assert tag == expected
        assert clean == "Câu trả lời."


def test_no_tag_returns_none():
    """Kiểm tra khi phản hồi không có thẻ ẩn thì trả về None và giữ nguyên văn bản."""
    raw = "Chào em, hôm nay em muốn hỏi bài toán nào?"
    clean, tag = extract_audit_tag(raw)
    assert tag is None
    assert clean == raw


def test_invalid_agent_ignored():
    """Kiểm tra các nhãn không nằm trong danh mục bị bỏ qua an toàn."""
    raw = "Lời giảng.\n<!-- AUDIT_AGENT: UNKNOWN_AGENT -->"
    clean, tag = extract_audit_tag(raw)
    assert tag is None
    assert clean == "Lời giảng."


def test_extract_last_tag_when_multiple():
    """Kiểm tra nếu mô hình sinh nhiều thẻ ẩn thì luôn ưu tiên lấy thẻ cuối cùng."""
    raw = "Đoạn 1.\n<!-- AUDIT_AGENT: SAFETY -->\nĐoạn 2.\n<!-- AUDIT_AGENT: MISCONCEPTION -->"
    clean, tag = extract_audit_tag(raw)
    assert tag == "MISCONCEPTION"
    assert clean == "Đoạn 1.\n\nĐoạn 2."
    assert "<!-- AUDIT_AGENT:" not in clean


def test_sanitize_stream_chunks_fragmented_tags():
    """
    Kiểm tra Lookahead Holding Buffer của sanitize_stream_chunks:
    Thẻ ẩn bị vỡ qua nhiều chunk không bao giờ bị rò rỉ ra ngoài [AC-AL-01].
    """
    # Mô phỏng Gemini stream bị chặt token ở vị trí hiểm hóc
    chunks = [
        "Chào em, ",
        "bài toán này giải như sau.\n",
        "<!-- AUD",
        "IT_AGENT: ",
        "MISCONCEPTION",
        " -->"
    ]
    streamed_output = "".join(list(sanitize_stream_chunks(chunks)))
    assert streamed_output.strip() == "Chào em, bài toán này giải như sau."
    assert "<!--" not in streamed_output
    assert "AUDIT_AGENT" not in streamed_output


def test_sanitize_stream_math_symbols_preserved():
    """Kiểm tra ký hiệu toán học như '<' hoặc khoảng '[0; 10]' không bị nuốt mất."""
    chunks = [
        "Vì x < 5 ",
        "và x thuộc đoạn [1; 4] ",
        "nên bài toán có 4 nghiệm."
    ]
    streamed_output = "".join(list(sanitize_stream_chunks(chunks)))
    assert "x < 5" in streamed_output
    assert "[1; 4]" in streamed_output
    assert streamed_output == "Vì x < 5 và x thuộc đoạn [1; 4] nên bài toán có 4 nghiệm."


def test_db_persistence_when_different():
    """Kiểm tra ghi nhận thành công vào bảng audit_feedback_logs khi nhãn khác nhau."""
    db = SessionLocal()
    test_query = "nhân 2 phân số là nhân chéo hả thầy (Unit Test T10.4.2 Single)"
    try:
        save_audit_feedback_log(
            db=db,
            user_query=test_query,
            predicted_agent="SCAFFOLDING",
            suggested_agent="MISCONCEPTION",
        )
        
        # Truy vấn kiểm tra
        log = (
            db.query(models.AuditFeedbackLog)
            .filter(models.AuditFeedbackLog.user_query == test_query)
            .order_by(models.AuditFeedbackLog.id.desc())
            .first()
        )
        assert log is not None
        assert log.predicted_agent == "SCAFFOLDING"
        assert log.suggested_agent == "MISCONCEPTION"
        assert log.status == "PENDING"
        
        # Dọn dẹp bản ghi kiểm thử
        db.delete(log)
        db.commit()
    finally:
        db.close()


def test_db_skip_when_same_agent():
    """Kiểm tra không lưu vào DB nếu suggested trùng với predicted (chống Echo Tagging)."""
    db = SessionLocal()
    test_query = "câu hỏi trùng nhãn (Unit Test T10.4.2)"
    try:
        save_audit_feedback_log(
            db=db,
            user_query=test_query,
            predicted_agent="SCAFFOLDING",
            suggested_agent="SCAFFOLDING",
        )
        
        log = (
            db.query(models.AuditFeedbackLog)
            .filter(models.AuditFeedbackLog.user_query == test_query)
            .first()
        )
        assert log is None
    finally:
        db.close()


def test_db_deduplication_pending():
    """Kiểm tra cơ chế chống spam: Không lưu trùng 2 bản ghi PENDING cùng nội dung."""
    db = SessionLocal()
    test_query = "câu hỏi kiểm tra trùng lặp deduplication (Unit Test T10.4.2)"
    try:
        # Lần 1: Lưu thành công
        save_audit_feedback_log(
            db=db,
            user_query=test_query,
            predicted_agent="SCAFFOLDING",
            suggested_agent="MISCONCEPTION",
        )
        
        # Lần 2: Cùng query và agent -> phải bị chặn deduplication
        save_audit_feedback_log(
            db=db,
            user_query=test_query,
            predicted_agent="SCAFFOLDING",
            suggested_agent="MISCONCEPTION",
        )
        
        count = (
            db.query(models.AuditFeedbackLog)
            .filter(models.AuditFeedbackLog.user_query == test_query)
            .count()
        )
        assert count == 1, f"Kỳ vọng 1 bản ghi duy nhất nhưng có {count}"
        
        # Dọn dẹp
        db.query(models.AuditFeedbackLog).filter(models.AuditFeedbackLog.user_query == test_query).delete()
        db.commit()
    finally:
        db.close()


def test_db_auto_session_when_none():
    """Kiểm tra save_audit_feedback_log tự mở session độc lập khi db=None (cho BackgroundTasks)."""
    test_query = "câu hỏi chạy background task với db=None (Unit Test T10.4.2)"
    save_audit_feedback_log(
        db=None,
        user_query=test_query,
        predicted_agent="SCAFFOLDING",
        suggested_agent="SAFETY",
    )
    
    # Kiểm tra bằng một session khác
    db = SessionLocal()
    try:
        log = (
            db.query(models.AuditFeedbackLog)
            .filter(models.AuditFeedbackLog.user_query == test_query)
            .first()
        )
        assert log is not None
        assert log.suggested_agent == "SAFETY"
        
        # Dọn dẹp
        db.delete(log)
        db.commit()
    finally:
        db.close()
