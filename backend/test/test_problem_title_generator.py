import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import re

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.problem_title_generator import (
    generate_friendly_problem_title,
    _heuristic_title_fallback
)


class TestProblemTitleGenerator(unittest.TestCase):

    def test_title_format_regex_structure(self):
        """Kiểm tra mọi tiêu đề sinh ra phải chuẩn regex: [Lớp X] [Chủ đề] – [Dạng toán]."""
        sample_problem = "Tìm hai số khi biết tổng là 100 và hiệu là 20"
        result = _heuristic_title_fallback(sample_problem, grade=4)
        
        pattern = r"^\[Lớp [4-9]\] .+ – .+$"
        self.assertTrue(
            bool(re.match(pattern, result.friendly_parent_title)),
            f"Tiêu đề không đúng định dạng quy chuẩn: {result.friendly_parent_title}"
        )
        self.assertEqual(result.grade, 4)
        self.assertEqual(result.topic, "Toán có lời văn")

    def test_fallback_motion_problem_grade_5(self):
        """Kiểm tra bài toán chuyển động đều được gán đúng Lớp 5 và chủ đề Chuyển động đều."""
        problem = "Một ô tô đi từ A đến B với vận tốc 45 km/h, đi ngược chiều với xe máy."
        result = _heuristic_title_fallback(problem, grade=5)
        
        self.assertEqual(result.grade, 5)
        self.assertEqual(result.topic, "Chuyển động đều")
        self.assertIn("[Lớp 5]", result.friendly_parent_title)
        self.assertIn("Chuyển động đều", result.friendly_parent_title)

    def test_fallback_geometry_rectangle_grade_4(self):
        """Kiểm tra bài toán diện tích hình chữ nhật gán đúng Hình học."""
        problem = "Tính diện tích hình chữ nhật có chiều dài 15cm và chiều rộng 8cm."
        result = _heuristic_title_fallback(problem, grade=4)
        
        self.assertEqual(result.grade, 4)
        self.assertEqual(result.topic, "Hình học")
        self.assertIn("chu vi và diện tích", result.subtopic_type.lower())

    def test_fallback_algebra_grade_9(self):
        """Kiểm tra bài toán phương trình bậc hai nhận diện đúng Đại số Lớp 9."""
        problem = "Giải phương trình bậc hai: 2x^2 - 7x + 3 = 0"
        result = _heuristic_title_fallback(problem, grade=9)
        
        self.assertEqual(result.grade, 9)
        self.assertEqual(result.topic, "Đại số")
        self.assertIn("[Lớp 9]", result.friendly_parent_title)

    @patch("google.generativeai.GenerativeModel")
    def test_gemini_mock_generate_title_success(self, mock_model_class):
        """Giả lập phản hồi thành công từ Gemini API theo định dạng JSON chuẩn."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json_str = '''{
            "friendly_parent_title": "[Lớp 5] Phân số – Tìm phân số của một số",
            "grade": 5,
            "topic": "Phân số",
            "subtopic_type": "Tìm phân số của một số",
            "short_summary": "Tìm 2/3 của 45 quả cam"
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_instance

        res = generate_friendly_problem_title(
            problem_text="Một rổ cam có 45 quả, mẹ đem biếu bà 2/3 số cam. Hỏi mẹ biếu bà bao nhiêu quả cam?",
            grade=5,
            api_key="fake-test-key"
        )

        self.assertFalse(res.is_fallback)
        self.assertEqual(res.friendly_parent_title, "[Lớp 5] Phân số – Tìm phân số của một số")
        self.assertEqual(res.grade, 5)
        self.assertEqual(res.topic, "Phân số")

    def test_empty_problem_returns_safe_fallback(self):
        """Kiểm tra khi đề bài rỗng, hệ thống không bị crash mà trả về tiêu đề dự phòng an toàn."""
        res = generate_friendly_problem_title("", grade=4)
        self.assertTrue(res.is_fallback)
        self.assertIn("[Lớp 4]", res.friendly_parent_title)


if __name__ == "__main__":
    unittest.main()