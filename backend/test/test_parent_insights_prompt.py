import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Thêm đường dẫn thư mục backend vào sys.path để import
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.parent_insights_prompt import (
    format_parent_insights_prompt,
    generate_parent_learning_insights,
    PARENT_INSIGHTS_SYSTEM_INSTRUCTION,
    _fallback_insights,
)

class TestParentInsightsPrompt(unittest.TestCase):
    
    def setUp(self):
        self.sample_topic_breakdown = [
            {
                "topic_name": "Phép cộng trừ phân số",
                "problems_solved": 5,
                "avg_independence": 88.0,
                "hints_used": 2,
                "not_understood": 0,
            },
            {
                "topic_name": "Toán tìm hai số khi biết Tổng và Tỉ số",
                "problems_solved": 3,
                "avg_independence": 45.0,
                "hints_used": 7,
                "not_understood": 3,
            }
        ]

    def test_format_parent_insights_prompt_contains_critical_data(self):
        """Kiểm tra chuỗi prompt sinh ra có đủ thông tin học sinh, dạng toán và điểm tự lực."""
        prompt = format_parent_insights_prompt(
            student_name="Bảo Nam",
            grade_level=5,
            period_description="Tuần 3 tháng 10",
            total_problems_completed=8,
            average_independence_score=71.8,
            total_hints_used=9,
            total_not_understood_count=3,
            topic_breakdown=self.sample_topic_breakdown,
        )

        self.assertIn("Bảo Nam", prompt)
        self.assertIn("Lớp 5", prompt)
        self.assertIn("71.8", prompt)
        self.assertIn("Phép cộng trừ phân số", prompt)
        self.assertIn("Toán tìm hai số khi biết Tổng và Tỉ số", prompt)
        self.assertIn("mastery_assessment", prompt)

    def test_system_instruction_pedagogical_rules(self):
        """Kiểm tra System Instruction có chứa đầy đủ các nguyên tắc sư phạm cốt lõi."""
        instruction = PARENT_INSIGHTS_SYSTEM_INSTRUCTION
        self.assertIn("Chuyên gia Cố vấn Sư phạm", instruction)
        self.assertIn("SANDWICH FEEDBACK", instruction)
        self.assertIn("TUYỆT ĐỐI KHÔNG", instruction)
        self.assertIn("JSON", instruction)

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_generate_parent_learning_insights_success(self, mock_generate):
        """Kiểm tra gọi Gemini thành công và phân tích đúng JSON cấu trúc 4 trường."""
        mock_ai_output = {
            "summary": "Em Bảo Nam đã hoàn thành 8 bài toán trong tuần với tinh thần học tập rất nghiêm túc.",
            "strengths": [
                "Nắm rất vững kỹ năng quy đồng mẫu số và tính toán phân số (điểm tự lực đạt 88/100).",
                "Có khả năng tư duy độc lập tốt ở các bài toán tính toán cơ bản."
            ],
            "weak_points": [
                "Con còn lúng túng khi xác định tỉ số trong các bài toán có lời văn, cần đến 7 lượt gợi ý."
            ],
            "recommendations": [
                "Cha mẹ hãy gợi ý con vẽ sơ đồ đoạn thẳng ra nháp để hình dung trực quan bài toán.",
                "Động viên con tiếp tục phát huy điểm mạnh ở phân số."
            ],
            "mastery_assessment": "Tự lập tốt"
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_ai_output, ensure_ascii=False)
        mock_generate.return_value = mock_response

        result = generate_parent_learning_insights(
            student_name="Bảo Nam",
            grade_level=5,
            period_description="Tuần 3 tháng 10",
            total_problems_completed=8,
            average_independence_score=71.8,
            total_hints_used=9,
            total_not_understood_count=3,
            topic_breakdown=self.sample_topic_breakdown,
            api_key="fake-test-key",
        )

        self.assertEqual(result["mastery_assessment"], "Tự lập tốt")
        self.assertEqual(len(result["strengths"]), 2)
        self.assertEqual(len(result["weak_points"]), 1)
        self.assertEqual(len(result["recommendations"]), 2)
        self.assertIn("Bảo Nam", result["summary"])

    def test_fallback_insights_when_no_api_key(self):
        """Kiểm tra cơ chế fallback dự phòng khi thiếu API Key môi trường."""
        result = _fallback_insights(
            student_name="Minh Triết",
            total_problems=10,
            score=85.5,
            reason="Môi trường test không có API key"
        )
        self.assertEqual(result["mastery_assessment"], "Tự lập xuất sắc")
        self.assertTrue(result["is_fallback"])
        self.assertIn("Minh Triết", result["summary"])
        self.assertGreater(len(result["strengths"]), 0)


if __name__ == "__main__":
    unittest.main()