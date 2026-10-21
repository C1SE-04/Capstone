import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from agents.flashcard_prompt import (
    generate_flashcard_content,
    _fallback_flashcard,
    _format_chat_for_flashcard,
    FLASHCARD_EXTRACTION_SYSTEM_INSTRUCTION
)
from schemas import FlashcardContent

class TestFlashcardPrompt(unittest.TestCase):

    def setUp(self):
        self.sample_math_chat = [
            {"sender_type": "USER", "content": "Tìm x biết: 3x - 5 = 10"},
            {"sender_type": "AGENT_TUTOR", "content": "Em hãy chuyển -5 sang vế phải thành gì nào?"},
            {"sender_type": "USER", "content": "Dạ thành 3x = 15 ạ"},
            {"sender_type": "AGENT_TUTOR", "content": "Vậy x bằng bao nhiêu em nhỉ?"},
            {"sender_type": "USER", "content": "x = 15 : 3 = 5 ạ"},
            {"sender_type": "AGENT_TUTOR", "content": "Rất chính xác! Đáp số chốt là x = 5!"}
        ]

    def test_system_instruction_contains_core_pedagogy(self):
        """Kiểm tra System Instruction có đủ 4 trường mục tiêu và quy tắc LaTeX."""
        instruction = FLASHCARD_EXTRACTION_SYSTEM_INSTRUCTION
        self.assertIn("THẺ FLASHCARD ÔN TẬP THÔNG MINH", instruction)
        self.assertIn("problem_statement", instruction)
        self.assertIn("key_takeaway", instruction)
        self.assertIn("final_answer", instruction)
        self.assertIn("topic_tag", instruction)
        self.assertIn("JSON", instruction)

    def test_format_chat_for_flashcard(self):
        """Kiểm tra hàm nối hội thoại rõ ràng theo lượt người nói."""
        formatted = _format_chat_for_flashcard(self.sample_math_chat)
        self.assertIn("USER: Tìm x biết: 3x - 5 = 10", formatted)
        self.assertIn("AGENT_TUTOR: Rất chính xác! Đáp số chốt là x = 5!", formatted)

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_generate_flashcard_content_success(self, mock_generate):
        """Kiểm tra Gemini đúc kết thành công Thẻ Flashcard đúng chuẩn Pydantic."""
        mock_output = {
            "problem_statement": "Tìm $x$ biết: $3x - 5 = 10$",
            "key_takeaway": "Quy tắc chuyển vế đổi dấu: Chuyển $-5$ sang vế phải thành $+5$, sau đó tìm $x$ bằng phép chia.",
            "final_answer": "$x = 5$",
            "topic_tag": "Tìm X"
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_output, ensure_ascii=False)
        mock_generate.return_value = mock_response

        flashcard = generate_flashcard_content(self.sample_math_chat, api_key="fake-key")

        self.assertIsInstance(flashcard, FlashcardContent)
        self.assertEqual(flashcard.final_answer, "$x = 5$")
        self.assertEqual(flashcard.topic_tag, "Tìm X")
        self.assertIn("chuyển vế đổi dấu", flashcard.key_takeaway)
        self.assertFalse(flashcard.is_fallback)

    def test_fallback_flashcard_when_no_api_key(self):
        """Kiểm tra cơ chế fallback an toàn khi không có API Key."""
        flashcard = _fallback_flashcard(problem_text="Tính 1/2 + 1/3")
        self.assertTrue(flashcard.is_fallback)
        self.assertEqual(flashcard.problem_statement, "Tính 1/2 + 1/3")
        self.assertIn("Đọc kỹ đề bài", flashcard.key_takeaway)


if __name__ == "__main__":
    unittest.main()