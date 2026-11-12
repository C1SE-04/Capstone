"""
US 10.4 - Task T10.4.1:
Bộ kiểm thử System Prompt 2 tầng & Giao thức Thẻ ẩn AUDIT_AGENT.

Chạy:
    python -m pytest backend/test/test_prompt_audit_tag.py -v
"""

import os
import sys
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from router import TEACHER_SYSTEM_INSTRUCTION


def test_system_instruction_contains_audit_protocol():
    """Kiểm tra TEACHER_SYSTEM_INSTRUCTION chứa đầy đủ định nghĩa Giao thức Thẻ ẩn."""
    assert "CƠ CHẾ THẨM ĐỊNH NGẦM 2 LỚP & GIAO THỨC THẺ ẨN" in TEACHER_SYSTEM_INSTRUCTION
    assert "<!-- AUDIT_AGENT: <AGENT_NAME> -->" in TEACHER_SYSTEM_INSTRUCTION or "<!-- AUDIT_AGENT:" in TEACHER_SYSTEM_INSTRUCTION
    assert "MISCONCEPTION" in TEACHER_SYSTEM_INSTRUCTION
    assert "KNOWLEDGE_TRACING" in TEACHER_SYSTEM_INSTRUCTION
    assert "SAFETY" in TEACHER_SYSTEM_INSTRUCTION
    assert "SCAFFOLDING" in TEACHER_SYSTEM_INSTRUCTION


def test_system_instruction_forbids_technical_terms():
    """Kiểm tra Guardrail cấm tuyệt đối lộ thuật ngữ kỹ thuật trong lời giảng gửi học sinh."""
    assert "TUYỆT ĐỐI KHÔNG nhắc đến các thuật ngữ kỹ thuật" in TEACHER_SYSTEM_INSTRUCTION
    assert "Orchestrator" in TEACHER_SYSTEM_INSTRUCTION
    assert "Routing" in TEACHER_SYSTEM_INSTRUCTION


def test_system_instruction_forbids_tag_when_correct():
    """Kiểm tra quy tắc cấm gắn thẻ ẩn khi phân loại đã chuẩn xác (chống False Flagging)."""
    assert "Nếu phân luồng đã CHUẨN XÁC: TUYỆT ĐỐI KHÔNG đính kèm bất kỳ thẻ ẩn nào" in TEACHER_SYSTEM_INSTRUCTION


def test_system_instruction_forbids_echo_tagging_and_protects_short_answers():
    """Kiểm tra nguyên tắc cấm Echo Tagging và bảo vệ câu trả lời ngắn đa lượt."""
    assert "TUYỆT ĐỐI KHÔNG gắn thẻ trùng với vai trò hiện tại" in TEACHER_SYSTEM_INSTRUCTION
    assert "BẢO VỆ CÂU TRẢ LỜI NGẮN TRONG HỘI THOẠI" in TEACHER_SYSTEM_INSTRUCTION
    assert "DANH MỤC AGENT HỢP LỆ DUY NHẤT" in TEACHER_SYSTEM_INSTRUCTION



def test_audit_regex_pattern_compatibility():
    """Kiểm tra Regex chuẩn sẽ dùng ở Task T10.4.2 bóc tách chính xác thẻ ẩn do Prompt tạo ra."""
    audit_regex = re.compile(r"<!--\s*AUDIT_AGENT:\s*([A-Z_]+)\s*-->", re.IGNORECASE)

    sample_output_with_tag = (
        "Chào em! Khi nhân hai phân số, ta lấy tử số nhân với tử số và mẫu số nhân với mẫu số nhé.\n"
        "<!-- AUDIT_AGENT: MISCONCEPTION -->"
    )
    match = audit_regex.search(sample_output_with_tag)
    assert match is not None
    assert match.group(1).upper() == "MISCONCEPTION"

    clean_text = audit_regex.sub("", sample_output_with_tag).strip()
    assert clean_text == "Chào em! Khi nhân hai phân số, ta lấy tử số nhân với tử số và mẫu số nhân với mẫu số nhé."
    assert "<!-- AUDIT_AGENT:" not in clean_text


def test_no_conflict_with_comprehension_check():
    """Kiểm tra thẻ ẩn AUDIT_AGENT không xung đột với thẻ [COMPREHENSION_CHECK] hiện có."""
    output = (
        "Chuẩn rồi em! [COMPREHENSION_CHECK]\n"
        "<!-- AUDIT_AGENT: SCAFFOLDING -->"
    )
    assert "[COMPREHENSION_CHECK]" in output
    assert "<!-- AUDIT_AGENT: SCAFFOLDING -->" in output

    audit_regex = re.compile(r"<!--\s*AUDIT_AGENT:\s*([A-Z_]+)\s*-->", re.IGNORECASE)
    cleaned = audit_regex.sub("", output).strip()
    assert cleaned == "Chuẩn rồi em! [COMPREHENSION_CHECK]"


def test_reviewer_compatibility_with_audit_tag():
    """Kiểm tra LocalReviewerAgent không bị đánh lừa cấu trúc câu hỏi khi có thẻ AUDIT_AGENT."""
    from agents.reviewer import LocalReviewerAgent
    reviewer = LocalReviewerAgent()

    # Phản hồi từ Gemini gồm câu hỏi gợi mở + thẻ ẩn ở dòng cuối
    raw_ai_reply = (
        "Chào em! Để nhân hai phân số, ta nhân tử với tử và mẫu với mẫu chứ không nhân chéo. "
        "Em thử áp dụng tính 1/3 nhân 2/5 bằng bao nhiêu nhỉ?\n"
        "<!-- AUDIT_AGENT: MISCONCEPTION -->"
    )
    
    # Mô phỏng bóc tách trong router.py trước khi đưa vào reviewer
    audit_regex = re.compile(r"<!--\s*AUDIT_AGENT:\s*([A-Z_]+)\s*-->", re.IGNORECASE)
    audit_match = audit_regex.search(raw_ai_reply)
    assert audit_match is not None
    assert audit_match.group(1).upper() == "MISCONCEPTION"

    clean_for_reviewer = audit_regex.sub("", raw_ai_reply).strip()
    
    # Reviewer phải phê duyệt câu hỏi Socratic này (không bị fail Lớp 1)
    res = reviewer.review(
        student_question="nhân 2 phân số là nhân chéo hả thầy",
        expected_answer="",
        scaffolding_response=clean_for_reviewer,
        has_comprehension=False
    )
    assert res["is_approved"] is True
    assert "Cấu trúc Socratic hợp lệ" in res["reasoning"]


