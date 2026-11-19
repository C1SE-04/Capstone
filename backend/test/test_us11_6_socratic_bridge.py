"""
US 11.6: Kiểm thử luồng Socratic Bridge ("Bài A-B-C-D Socratic Bridge").
Xử lý các tình huống:
1. Phát hiện học sinh báo cô/thầy bỏ qua/không dạy/nhảy cóc (TEACHER_SKIPPED).
2. Tìm vị trí bài học trong curriculum (HK1 và HK2).
3. Phân loại câu trả lời thăm dò theo vị trí curriculum:
   - Học sinh học bài B (trước bài C) -> LEARN_NEW (Kịch bản B).
   - Học sinh học bài E (sau bài C) -> FORGOT_OLD (Kịch bản A).
   - Học sinh báo thầy cô bỏ qua -> TEACHER_SKIPPED (Kịch bản B kèm đồng cảm).
4. Orchestrator điều phối câu hỏi thăm dò mở kèm tên bài học sinh hỏi.
5. Orchestrator điều phối lượt phản hồi sau thăm dò kèm curriculum order.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import (
    _agent,
    _detect_uncovered_claim,
    _detect_teacher_skipped_phrase,
    _get_topic_position_in_curriculum,
    _classify_probe_reply_with_curriculum,
    _classify_probe_reply,
    _detect_probe_in_history,
)


def test_detect_teacher_skipped_phrase():
    """Kiểm tra nhận diện câu học sinh báo giáo viên bỏ qua / nhảy cóc bài."""
    skipped_samples = [
        "cô em không dạy bài đó",
        "thầy bỏ qua bài này rồi",
        "trường em nhảy cóc qua bài sau luôn",
        "bài này cô giảm tải không dạy",
        "thầy ko dạy bài này",
        "cô lướt qua bài đó luôn",
        "cô em ko dạy bài lũy thừa",
        "trường em không học bài này",
        "cô hay bỏ qua bài khó",
    ]
    for s in skipped_samples:
        assert _detect_teacher_skipped_phrase(s) is True, f"Failed for: {s}"

    not_skipped = [
        "em chưa học bài này",
        "bài này khó quá",
        "thầy ơi chỉ em bài này với",
        "em học đến bài lũy thừa rồi",
    ]
    for s in not_skipped:
        assert _detect_teacher_skipped_phrase(s) is False, f"Should be False for: {s}"


def test_get_topic_position_in_curriculum():
    """Kiểm tra tìm vị trí index bài học trong Lớp 6 HK1."""
    # Lớp 6 HK1:
    # Index 0: Tập hợp
    # Index 5: Lũy thừa với số mũ tự nhiên
    # Index 9: Số nguyên tố
    # Index 12: Tập hợp các số nguyên
    pos_tap_hop = _get_topic_position_in_curriculum("Tập hợp", 6, 1)
    pos_luy_thua = _get_topic_position_in_curriculum("lũy thừa", 6, 1)
    pos_so_nguyen_to = _get_topic_position_in_curriculum("số nguyên tố", 6, 1)
    pos_so_nguyen = _get_topic_position_in_curriculum("số nguyên", 6, 1)

    assert pos_tap_hop == 0
    assert pos_luy_thua == 5
    assert pos_so_nguyen_to == 9
    assert pos_so_nguyen >= 12
    assert pos_luy_thua < pos_so_nguyen_to < pos_so_nguyen


def test_classify_probe_reply_before_c():
    """
    Kịch bản 2.1: Học sinh hỏi bài C ('số nguyên tố', index 9),
    học sinh trả lời đang học đến bài B ('lũy thừa', index 5).
    Vì 5 < 9 -> Hệ thống nhận diện LEARN_NEW (chưa học tới, Kịch bản B).
    """
    reply = "trên trường em mới học đến bài lũy thừa thôi ạ"
    result = _classify_probe_reply_with_curriculum(
        message=reply,
        asked_topic="số nguyên tố",
        grade=6,
        semester=1,
    )
    assert result == "LEARN_NEW"


def test_classify_probe_reply_after_c():
    """
    Kịch bản 2.2: Học sinh hỏi bài C ('lũy thừa', index 5),
    học sinh trả lời trên trường đã học đến bài E ('số nguyên', index 12).
    Vì 12 > 5 -> Hệ thống nhận diện FORGOT_OLD (đã học qua nhưng có thể quên, Kịch bản A).
    """
    reply = "dạ trên trường em học đến bài số nguyên rồi thầy"
    result = _classify_probe_reply_with_curriculum(
        message=reply,
        asked_topic="lũy thừa",
        grade=6,
        semester=1,
    )
    assert result == "FORGOT_OLD"


def test_classify_probe_reply_teacher_skipped():
    """Học sinh phản hồi giáo viên bỏ qua bài -> TEACHER_SKIPPED."""
    reply = "cô em không dạy bài này, cô nhảy cóc qua bài sau rồi"
    result = _classify_probe_reply_with_curriculum(
        message=reply,
        asked_topic="lũy thừa",
        grade=6,
        semester=1,
    )
    assert result == "TEACHER_SKIPPED"


def test_orchestrator_uncovered_claim_routes_to_scaffolding():
    """Học sinh nói 'em chưa học bài này' -> Orchestrator điều phối SCAFFOLDING với probe."""
    res = _agent.route_sync(
        latest_message="hình như bài này em chưa học",
        student_grade=6,
    )
    assert res["selected_agent"] == "SCAFFOLDING"
    assert "PROBE_PENDING" in res["task_description"]
    assert "US 11.6" in res["task_description"]


def test_orchestrator_followup_probe_curriculum_order_injection():
    """Khi học sinh trả lời câu hỏi thăm dò, Orchestrator inject danh sách thứ tự bài và hướng dẫn Socratic Bridge."""
    history = (
        "[USER]: bài lũy thừa này làm sao ạ\n"
        "[AGENT]: Hiện tại trên trường em đã học đến bài nào rồi, bài lũy thừa này em đã học qua chưa? <!-- PROBE_PENDING -->\n"
    )
    res = _agent.route_sync(
        latest_message="dạ trên trường em mới học đến bài tập hợp thôi thầy",
        history_text=history,
        student_grade=6,
    )
    assert res["selected_agent"] == "SCAFFOLDING"
    assert "US 11.6 CURRICULUM ORDER" in res["task_description"]
    assert "KỊCH BẢN B" in res["task_description"] or "Kịch bản B" in res["task_description"]
    assert "KỊCH BẢN A" in res["task_description"] or "Kịch bản A" in res["task_description"]


def test_orchestrator_followup_teacher_skipped_handling():
    """Khi học sinh phản hồi cô bỏ qua bài, Orchestrator chỉ đạo đồng cảm và Kịch bản B."""
    history = (
        "[USER]: bài này em chưa học\n"
        "[AGENT]: Hiện tại trên trường em đã học đến bài nào rồi, bài này em đã học qua chưa? <!-- PROBE_PENDING -->\n"
    )
    res = _agent.route_sync(
        latest_message="cô em không dạy bài đó thầy ơi",
        history_text=history,
        student_grade=6,
    )
    assert res["selected_agent"] == "SCAFFOLDING"
    assert "TEACHER_SKIPPED" in res["routing_scratchpad"]
    assert "Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé" in res["task_description"]
