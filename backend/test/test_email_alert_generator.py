import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from schemas import (
    AcademicAlertGenerateRequest,
    AcademicAlertEmailResult,
    AcademicProblemSummary,
    SafetyAlertGenerateRequest,
    SafetyAlertEmailResult,
)
from agents.email_alert_generator import (
    censor_sensitive_words,
    generate_academic_alert_email,
    generate_safety_alert_email,
    _fallback_academic_alert,
    _fallback_safety_alert,
)


class TestEmailAlertGenerator(unittest.TestCase):

    def test_censor_sensitive_words_masks_profanity(self):
        """Kiểm tra bộ lọc che mờ chính xác các từ tục tĩu từ PROFANITY_LIST."""
        sample_text = "Bài này khó vcl, làm mãi đệt ra bực vãi lồn mẹ mày"
        censored = censor_sensitive_words(sample_text)
        
        self.assertNotIn("vcl", censored)
        self.assertNotIn("vãi lồn", censored)
        self.assertNotIn("đệt", censored)
        self.assertNotIn("mẹ mày", censored)
        self.assertIn("v**", censored)
        self.assertIn("đ**", censored)

    def test_academic_alert_fallback_structure(self):
        """Kiểm tra cấu trúc và tính hợp lệ của email cảnh báo học tập fallback."""
        req = AcademicAlertGenerateRequest(
            student_id="std_123",
            student_name="Minh Quân",
            grade=5,
            consecutive_low_scores_count=3,
            average_recent_score=45.0,
            difficult_topics=["Phân số", "Toán chuyển động đều"]
        )
        res = _fallback_academic_alert(req)
        
        self.assertTrue(res.is_fallback)
        self.assertEqual(res.alert_type, "ACADEMIC_ALERT")
        self.assertEqual(res.student_name, "Minh Quân")
        self.assertEqual(res.grade, 5)
        self.assertIn("Minh Quân", res.email_subject)
        self.assertGreater(len(res.actionable_parent_advice), 0)
        self.assertTrue(bool(res.suggested_conversation_opener))

    def test_safety_alert_fallback_structure(self):
        """Kiểm tra email cảnh báo ngôn từ fallback tự động che mờ từ thô."""
        req = SafetyAlertGenerateRequest(
            student_id="std_123",
            student_name="Bảo Trâm",
            grade=7,
            original_message="Đm bài này làm mãi không ra bực vcl"
        )
        res = _fallback_safety_alert(req)
        
        self.assertTrue(res.is_fallback)
        self.assertEqual(res.alert_type, "SAFETY_ALERT")
        self.assertNotIn("Đm", res.censored_snippet)
        self.assertNotIn("vcl", res.censored_snippet)
        self.assertIn("Bảo Trâm", res.email_subject)
        self.assertGreater(len(res.actionable_parent_advice), 0)

    @patch("google.generativeai.GenerativeModel")
    def test_mock_gemini_academic_alert_success(self, mock_model_class):
        """Giả lập phản hồi thành công từ Gemini API cho email cảnh báo học tập."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "alert_type": "ACADEMIC_ALERT",
            "email_subject": "[SocraticKid] Đồng hành cùng bé Hải Đăng môn Toán Lớp 4",
            "student_name": "Hải Đăng",
            "grade": 4,
            "trigger_reason": "3 bài liên tiếp dưới 60 điểm",
            "summary": "Hải Đăng đang gặp chút bỡ ngỡ với dạng toán tìm hai số khi biết tổng và hiệu.",
            "strengths_observed": "Con rất kiên trì và không nản lòng khi gặp phép tính dài.",
            "learning_gap_analysis": "Con chưa quen biểu diễn sơ đồ đoạn thẳng ra giấy nháp.",
            "actionable_parent_advice": [
                "Cùng con vẽ sơ đồ đoạn thẳng ra nháp",
                "Khích lệ con đọc to đề bài 2 lần"
            ],
            "suggested_conversation_opener": "Hôm nay làm bài toán có chỗ nào vui không con kể bố nghe với!"
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_instance

        req = AcademicAlertGenerateRequest(
            student_id="std_001",
            student_name="Hải Đăng",
            grade=4,
            average_recent_score=50.0
        )
        res = generate_academic_alert_email(req, api_key="fake-test-key")

        self.assertFalse(res.is_fallback)
        self.assertEqual(res.student_name, "Hải Đăng")
        self.assertEqual(res.alert_type, "ACADEMIC_ALERT")
        self.assertEqual(len(res.actionable_parent_advice), 2)

    @patch("google.generativeai.GenerativeModel")
    def test_mock_gemini_safety_alert_success(self, mock_model_class):
        """Giả lập phản hồi thành công từ Gemini API cho email cảnh báo ngôn từ."""
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "alert_type": "SAFETY_ALERT",
            "email_subject": "[SocraticKid] Phối hợp đồng hành cùng bé Tuấn Kiệt",
            "student_name": "Tuấn Kiệt",
            "grade": 6,
            "violation_category": "Ngôn từ chưa phù hợp trong giờ học",
            "censored_snippet": "đ** hiểu bài này",
            "context_analysis": "Con đang cảm thấy bế tắc trước bài toán phân số nâng cao.",
            "tone_guidance_for_parent": "Cha mẹ hãy lắng nghe con với sự thấu cảm, không quát mắng.",
            "actionable_parent_advice": [
                "Hỏi thăm khó khăn của con một cách nhẹ nhàng",
                "Cho con giải lao 5 phút uống nước khi thấy con căng thẳng"
            ],
            "suggested_conversation_opener": "Bố thấy bài toán hôm nay có vẻ hóc búa, con có cần bố ngồi cùng không?"
        }'''
        mock_instance.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_instance

        req = SafetyAlertGenerateRequest(
            student_id="std_002",
            student_name="Tuấn Kiệt",
            grade=6,
            original_message="địt hiểu bài này"
        )
        res = generate_safety_alert_email(req, api_key="fake-test-key")

        self.assertFalse(res.is_fallback)
        self.assertEqual(res.alert_type, "SAFETY_ALERT")
        self.assertNotIn("địt", res.censored_snippet)

    def test_missing_api_key_returns_fallback_safely(self):
        """Kiểm tra khi không có API key, hệ thống không bị crash mà trả về fallback an toàn."""
        req = AcademicAlertGenerateRequest(
            student_id="std_test",
            student_name="Gia Bảo",
            grade=5
        )
        with patch.dict(os.environ, {}, clear=True):
            res = generate_academic_alert_email(req, api_key=None)
            self.assertTrue(res.is_fallback)
            self.assertIn("Gia Bảo", res.email_subject)


if __name__ == "__main__":
    unittest.main()