import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.problem_classifier import (
    classify_problem,
    _heuristic_classification_fallback,
    _format_history_for_gemini,
    PROBLEM_CLASSIFICATION_SYSTEM_INSTRUCTION
)
from schemas import ProblemClassificationResult

class TestProblemClassifier(unittest.TestCase):

    def setUp(self):
        # Lịch sử các bài toán học sinh đã giải
        self.sample_history = [
            "Tìm hai số biết tổng là 50 và hiệu là 10.",
            "Tìm x biết: 2x + 4 = 10",
            "Tính diện tích hình chữ nhật có chiều dài 8cm, chiều rộng 5cm."
        ]

    def test_system_instruction_contains_core_pedagogy(self):
        """Kiểm tra System Instruction có đủ 3 nhóm phân loại và câu nhắc nhở nhẹ nhàng."""
        instruction = PROBLEM_CLASSIFICATION_SYSTEM_INSTRUCTION
        self.assertIn("EXACT_DUPLICATE", instruction)
        self.assertIn("ISOMORPHIC_PRACTICE", instruction)
        self.assertIn("NEW_TOPIC", instruction)
        self.assertIn("Thầy thấy em đã giải rất tốt bài này rồi", instruction)
        self.assertIn("JSON", instruction)

    def test_classify_first_problem_always_new_topic(self):
        """Kiểm tra bài đầu tiên khi chưa có lịch sử luôn trả về NEW_TOPIC mà không tốn token."""
        result = classify_problem(
            current_problem="Tính diện tích hình tròn bán kính 3cm",
            history_problems=[]
        )
        self.assertIsInstance(result, ProblemClassificationResult)
        self.assertEqual(result.category, "NEW_TOPIC")
        self.assertEqual(result.repeat_count, 1)
        self.assertFalse(result.is_repeated_query)
        self.assertFalse(result.is_fallback)

    def test_format_history_for_gemini(self):
        """Kiểm tra hàm format lịch sử đánh số index rõ ràng."""
        formatted = _format_history_for_gemini(self.sample_history)
        self.assertIn("[1] Tìm hai số biết tổng là 50 và hiệu là 10.", formatted)
        self.assertIn("[2] Tìm x biết: 2x + 4 = 10", formatted)

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_classify_isomorphic_practice_mock(self, mock_generate):
        """Kiểm tra Gemini nhận diện đúng bài cùng dạng đổi số (ISOMORPHIC_PRACTICE)."""
        mock_output = {
            "category": "ISOMORPHIC_PRACTICE",
            "confidence_score": 0.95,
            "reasoning": "Cùng dạng toán Tìm hai số khi biết Tổng và Hiệu, chỉ đổi số liệu từ 50 và 10 sang 70 và 20.",
            "matched_problem": "Tìm hai số biết tổng là 50 và hiệu là 10.",
            "is_repeated_query": False,
            "repeat_count": 1,
            "gentle_reminder": None,
            "pedagogical_recommendation": "Ghi nhận luyện tập củng cố, tăng chỉ số thành thạo dạng bài, không tính trùng chuyên đề mới."
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_output, ensure_ascii=False)
        mock_generate.return_value = mock_response

        current_prob = "Tìm hai số biết tổng là 70 và hiệu là 20."
        result = classify_problem(current_prob, self.sample_history, api_key="fake-test-key")

        self.assertIsInstance(result, ProblemClassificationResult)
        self.assertEqual(result.category, "ISOMORPHIC_PRACTICE")
        self.assertIn("Tổng và Hiệu", result.reasoning)
        self.assertFalse(result.is_fallback)

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_classify_exact_duplicate_mock(self, mock_generate):
        """Kiểm tra Gemini nhận diện đúng bài trùng lặp y hệt (EXACT_DUPLICATE) kèm lời nhắc nhở."""
        mock_output = {
            "category": "EXACT_DUPLICATE",
            "confidence_score": 1.0,
            "reasoning": "Đề bài trùng khớp 100% với bài số 2 trong lịch sử.",
            "matched_problem": "Tìm x biết: 2x + 4 = 10",
            "is_repeated_query": True,
            "repeat_count": 2,
            "gentle_reminder": "Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?",
            "pedagogical_recommendation": "Bỏ qua cộng dồn vào tổng bài hoàn thành, khuyến khích học sinh thử sức bài nâng cao."
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_output, ensure_ascii=False)
        mock_generate.return_value = mock_response

        current_prob = "Tìm x biết: 2x + 4 = 10"
        result = classify_problem(current_prob, self.sample_history, api_key="fake-test-key")

        self.assertIsInstance(result, ProblemClassificationResult)
        self.assertEqual(result.category, "EXACT_DUPLICATE")
        self.assertTrue(result.is_repeated_query)
        self.assertEqual(result.repeat_count, 2)
        self.assertIsNotNone(result.gentle_reminder)
        self.assertIn("thử sức bài nâng cao", result.gentle_reminder)

    def test_heuristic_fallback_scenarios(self):
        """Kiểm tra thuật toán Heuristic Fallback khi không có API Key cho cả 3 trường hợp."""
        # 1. Trùng khớp 100% -> EXACT_DUPLICATE
        dup_result = _heuristic_classification_fallback(
            current_problem="Tìm x biết: 2x + 4 = 10",
            history_problems=self.sample_history,
            reason="No API Key"
        )
        self.assertTrue(dup_result.is_fallback)
        self.assertEqual(dup_result.category, "EXACT_DUPLICATE")
        self.assertIsNotNone(dup_result.gentle_reminder)

        # 2. Cùng dạng đổi số -> ISOMORPHIC_PRACTICE
        iso_result = _heuristic_classification_fallback(
            current_problem="Tìm hai số biết tổng là 100 và hiệu là 30",
            history_problems=self.sample_history,
            reason="No API Key"
        )
        self.assertTrue(iso_result.is_fallback)
        self.assertEqual(iso_result.category, "ISOMORPHIC_PRACTICE")

        # 3. Dạng mới hoàn toàn -> NEW_TOPIC
        new_result = _heuristic_classification_fallback(
            current_problem="Cho tam giác ABC vuông tại A có AB=3, AC=4. Tính cạnh huyền BC.",
            history_problems=self.sample_history,
            reason="No API Key"
        )
        self.assertTrue(new_result.is_fallback)
        self.assertEqual(new_result.category, "NEW_TOPIC")


if __name__ == "__main__":
    unittest.main()