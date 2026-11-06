"""
US 9.3 - Task T9.13:
Bộ kiểm thử Prompt Kịch bản Thăm dò Sư phạm (Socratic Progressive Probe & Summer Probe).

Chạy:
    cd backend
    python -m pytest test/test_socratic_probe.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import _build_task_description
from agents.agent_prompts import build_timeline_context_for_prompt


def test_socratic_probe_task_description_hk1():
    """Kiểm tra task_description tạo ra đúng chỉ đạo Socratic Probe cho bài cùng HK1."""
    # Giả lập tháng 10 (HK1)
    tl = build_timeline_context_for_prompt(student_grade=7, override_month=10)
    assert "Đang Học kỳ 1" in tl["timeline_label"]
    assert "SOCRATIC PROBE" in tl["scenario_guide"]
    assert "Ở trường thầy cô đã dạy đến bài này chưa" in tl["scenario_guide"]
    assert "TUYỆT ĐỐI KHÔNG" in tl["scenario_guide"]


def test_summer_probe_task_description():
    """Kiểm tra task_description tạo ra đúng chỉ đạo Summer Probe cho tháng 7 hè."""
    tl = build_timeline_context_for_prompt(student_grade=8, override_month=7)
    assert "Kỳ nghỉ hè" in tl["timeline_label"]
    assert "SUMMER PROBE" in tl["scenario_guide"]
    assert "Kỳ nghỉ hè này em đang chuẩn bị học trước" in tl["scenario_guide"]
    assert "TUYỆT ĐỐI KHÔNG giải bài hoặc đưa ra phép tính toán học ngay trong lượt này" in tl["scenario_guide"]


def test_socratic_probe_task_description_hk2():
    """Kiểm tra task_description tạo ra đúng chỉ đạo cho HK2 (Tháng 3)."""
    tl = build_timeline_context_for_prompt(student_grade=8, override_month=3)
    assert "Đang Học kỳ 2" in tl["timeline_label"]
    assert "KỊCH BẢN A" in tl["scenario_guide"]
    assert "Ở trường thầy cô đã dạy đến bài này chưa" in tl["scenario_guide"]


def test_orchestrator_builds_probe_task_description():
    """Kiểm tra orchestrator._build_task_description khi học sinh tuyên bố chưa học."""
    desc = _build_task_description(
        agent="SCAFFOLDING",
        message="em chưa học bài này thầy ơi",
        problem_context=None,
        student_grade=7
    )
    assert "HỌC SINH TUYÊN BỐ CHƯA HỌC" in desc
    assert "CHỈ ĐẠO SƯ PHẠM BẮT BUỘC (SOCRATIC PROBE GUIDELINES)" in desc
    assert "BẠN PHẢI DỪNG LẠI Ở CÂU HỎI THĂM DÒ" in desc
    assert "TUYỆT ĐỐI KHÔNG GIẢI BÀI HOẶC ĐẶT PHÉP TÍNH TOÁN NGAY TRONG LƯỢT NÀY!" in desc

