"""
US 9.3 - Task T9.12:
Bộ kiểm thử tính toàn vẹn cấu trúc grade_curriculum.json (phân nhóm {"1": [...], "2": [...]})
và tính tương thích ngược của các module loader.

Chạy:
    cd backend
    pytest test/test_grade_curriculum_semester.py -v
"""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_prompts import (
    _load_curriculum_from_file,
    _load_curriculum,
    _get_grade_context,
    get_curriculum_by_grade_and_semester,
)
from agents.problem_title_generator import _heuristic_title_fallback


def test_01_json_file_exists_and_valid():
    """Kiểm tra file grade_curriculum.json tồn tại và parse thành JSON dict hợp lệ."""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "agents",
        "grade_curriculum.json",
    )
    assert os.path.exists(json_path), f"Không tìm thấy file: {json_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, dict)
    expected_grades = {"4", "5", "6", "7", "8", "9"}
    assert expected_grades.issubset(set(data.keys())), "Thiếu khối lớp trong grade_curriculum.json"


def test_02_all_grades_have_two_semesters_with_data():
    """Kiểm tra mỗi khối lớp đều có 2 keys '1' và '2' với số lượng bài học cân đối."""
    curriculum = _load_curriculum_from_file()
    assert len(curriculum) >= 6

    total_topics = 0
    for grade_str, sem_dict in curriculum.items():
        assert isinstance(sem_dict, dict), f"Lớp {grade_str} không phải là dictionary phân nhóm"
        assert "1" in sem_dict, f"Lớp {grade_str} thiếu key '1' (Học kỳ 1)"
        assert "2" in sem_dict, f"Lớp {grade_str} thiếu key '2' (Học kỳ 2)"

        s1_list = sem_dict["1"]
        s2_list = sem_dict["2"]

        assert isinstance(s1_list, list), f"HK1 lớp {grade_str} không phải list"
        assert isinstance(s2_list, list), f"HK2 lớp {grade_str} không phải list"

        # Đảm bảo mỗi học kỳ có ít nhất 10 bài học
        assert len(s1_list) >= 10, f"Lớp {grade_str} HK1 có quá ít bài ({len(s1_list)})"
        assert len(s2_list) >= 10, f"Lớp {grade_str} HK2 có quá ít bài ({len(s2_list)})"

        for topic in s1_list + s2_list:
            total_topics += 1
            assert isinstance(topic, str), f"Tên bài học không phải chuỗi: {topic}"
            assert len(topic.strip()) > 0, "Tên bài học bị rỗng"

    assert total_topics >= 200, f"Tổng số bài học phải >= 200, thực tế có: {total_topics}"


def test_03_helper_get_curriculum_by_semester():
    """Kiểm tra hàm helper get_curriculum_by_grade_and_semester phân loại chuẩn xác O(1)."""
    # Lớp 8 HK1: Phải có hằng đẳng thức, đa thức
    g8_s1 = get_curriculum_by_grade_and_semester(8, semester=1)
    assert len(g8_s1) > 0
    s1_topics_text = " ".join(g8_s1)
    assert "Đa thức" in s1_topics_text or "Hằng đẳng thức" in s1_topics_text

    # Lớp 8 HK2: Phải có phương trình bậc nhất một ẩn, hàm số bậc nhất
    g8_s2 = get_curriculum_by_grade_and_semester(8, semester=2)
    assert len(g8_s2) > 0
    s2_topics_text = " ".join(g8_s2)
    assert "Phương trình" in s2_topics_text or "Hàm số" in s2_topics_text

    # Lấy toàn bộ lớp 8 (semester=None)
    g8_all = get_curriculum_by_grade_and_semester(8, semester=None)
    assert len(g8_all) == len(g8_s1) + len(g8_s2)


def test_04_backward_compatibility_grade_context():
    """Kiểm tra hàm _get_grade_context không quăng lỗi và trả về văn bản chứa tên bài học chuẩn."""
    context_text = _get_grade_context(8)
    assert isinstance(context_text, str)
    assert "Lớp 8" in context_text
    assert "Lớp 4" in context_text
    assert "Đa thức" in context_text


def test_05_backward_compatibility_problem_title_fallback():
    """Kiểm tra bộ tạo tên bài tự đặt vẫn quét chuyên đề chuẩn xác không gặp lỗi type."""
    res = _heuristic_title_fallback("Giải phương trình bậc nhất: 3x - 5 = 10", grade=8)
    assert res is not None
    assert res.grade == 8
    assert len(res.friendly_parent_title) > 0
