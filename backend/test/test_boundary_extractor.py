import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.boundary_extractor import (
    extract_problem_boundary,
    _heuristic_boundary_fallback,
    _format_conversation_for_gemini,
    BOUNDARY_EXTRACTION_SYSTEM_INSTRUCTION
)
from schemas import ProblemBoundaryResult

class TestBoundaryExtractor(unittest.TestCase):

    def setUp(self):
        # Kịch bản 1: Học sinh giải trọn vẹn 1 bài đơn giản
        self.single_problem_messages = [
            {"sender_type": "USER", "content": "Tìm x biết 2x + 4 = 10"},
            {"sender_type": "AGENT_TUTOR", "content": "Em hãy chuyển 4 sang vế phải xem nào."},
            {"sender_type": "USER", "content": "Dạ 2x = 6, nên x = 3 ạ"},
            {"sender_type": "AGENT_TUTOR", "content": "Chính xác! Em làm rất tốt!"}
        ]

        # Kịch bản 2: Học sinh bỏ dở bài 1, nhảy sang bài 2 (Cốt lõi T7.15)
        self.abandoned_problem_messages = [
            {"sender_type": "USER", "content": "Giải giúp em bài hình học: Cho tam giác ABC vuông tại A có AB=3, AC=4. Tính BC."},
            {"sender_type": "AGENT_TUTOR", "content": "Em nhớ định lý nào liên quan tam giác vuông không?"},
            {"sender_type": "USER", "content": "Khó quá em bỏ qua bài này. Thầy giải bài này đi: Tính 1/2 + 1/3"}, # Index 2: Đổi bài!
            {"sender_type": "AGENT_TUTOR", "content": "Được rồi, để cộng hai phân số khác mẫu, ta làm gì nhỉ?"},
            {"sender_type": "USER", "content": "Quy đồng mẫu số thành 3/6 + 2/6 = 5/6 ạ"},
            {"sender_type": "AGENT_TUTOR", "content": "Xuất sắc! Đáp án là 5/6!"}
        ]

        # Kịch bản 3: Có lời chào xã giao mở đầu
        self.greetings_messages = [
            {"sender_type": "USER", "content": "Chào thầy ạ"},
            {"sender_type": "AGENT_TUTOR", "content": "Chào em, hôm nay em cần thầy hỗ trợ bài toán nào?"},
            {"sender_type": "USER", "content": "Tìm số trung bình cộng của 10 và 20"},
            {"sender_type": "AGENT_TUTOR", "content": "Em cộng hai số rồi chia cho mấy?"},
            {"sender_type": "USER", "content": "Dạ chia cho 2 được 15 ạ"},
            {"sender_type": "AGENT_TUTOR", "content": "Chính xác rồi em!"}
        ]

    def test_system_instruction_contains_core_rules(self):
        """Kiểm tra System Instruction có chứa đầy đủ quy tắc ranh giới và bỏ dở bài."""
        instruction = BOUNDARY_EXTRACTION_SYSTEM_INSTRUCTION
        self.assertIn("RANH GIỚI CỦA BÀI TOÁN VỪA HOÀN THÀNH", instruction)
        self.assertIn("ABANDONED PROBLEMS", instruction)
        self.assertIn("LOẠI BỎ TIN NHẮN RÁC", instruction)
        self.assertIn("JSON", instruction)

    def test_format_conversation_for_gemini(self):
        """Kiểm tra format hội thoại đánh số index đầy đủ."""
        formatted = _format_conversation_for_gemini(self.single_problem_messages)
        self.assertIn("[0] USER: Tìm x biết 2x + 4 = 10", formatted)
        self.assertIn("[3] AGENT_TUTOR: Chính xác! Em làm rất tốt!", formatted)

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_extract_boundary_with_abandoned_problem_mock(self, mock_generate):
        """Kiểm tra Gemini nhận diện đúng bài đổi giữa chừng và loại bỏ tin nhắn bài 1."""
        mock_ai_output = {
            "extracted_problem": "Tính 1/2 + 1/3",
            "boundary_start_index": 2,
            "boundary_end_index": 5,
            "has_abandoned_problem": True,
            "abandoned_problem_summary": "Học sinh bỏ dở bài toán hình học tam giác vuông Pytago."
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_ai_output, ensure_ascii=False)
        mock_generate.return_value = mock_response

        result = extract_problem_boundary(self.abandoned_problem_messages, api_key="fake-test-key")

        self.assertIsInstance(result, ProblemBoundaryResult)
        self.assertEqual(result.boundary_start_index, 2)
        self.assertEqual(result.boundary_end_index, 5)
        self.assertEqual(result.extracted_problem, "Tính 1/2 + 1/3")
        self.assertTrue(result.has_abandoned_problem)
        # filtered_messages chỉ có 4 tin nhắn (từ index 2 đến 5), loại bỏ hoàn toàn index 0 và 1!
        self.assertEqual(len(result.filtered_messages), 4)
        self.assertEqual(result.filtered_messages[0].content, "Khó quá em bỏ qua bài này. Thầy giải bài này đi: Tính 1/2 + 1/3")

    def test_heuristic_fallback_detects_topic_switch(self):
        """Kiểm tra thuật toán Heuristic Fallback tự phát hiện đổi bài khi không có API Key."""
        result = _heuristic_boundary_fallback(self.abandoned_problem_messages, reason="Không có API Key")
        self.assertTrue(result.is_fallback)
        self.assertTrue(result.has_abandoned_problem)
        self.assertEqual(result.boundary_start_index, 2)
        self.assertEqual(len(result.filtered_messages), 4)

    def test_heuristic_fallback_filters_greetings(self):
        """Kiểm tra Heuristic Fallback tự loại bỏ câu 'Chào thầy ạ' ở đầu phiên."""
        result = _heuristic_boundary_fallback(self.greetings_messages, reason="Test greetings")
        # index 0 là 'Chào thầy ạ' -> bỏ qua, bắt đầu từ index 2
        self.assertEqual(result.boundary_start_index, 2)
        self.assertIn("Tìm số trung bình cộng", result.extracted_problem)


if __name__ == "__main__":
    unittest.main()