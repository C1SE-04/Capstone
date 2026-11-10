"""
Unit & Integration Tests for US 10.3 (Task T10.3.3)
Tích Hợp SystemConfigService Vào AI Runtime 5 Agent Files
========================================================
Test suite covers:
  - T10.3.3: backend/router.py đọc primary_model, temperature, max_output_tokens động từ SystemConfigService
  - T10.3.3: problem_classifier.py đọc classifier_model động từ SystemConfigService
  - T10.3.3: email_alert_generator.py đọc email_model động từ SystemConfigService
  - T10.3.3: flashcard_prompt.py đọc flashcard_model động từ SystemConfigService
  - T10.3.3: parent_insights_prompt.py đọc parent_insight_model động từ SystemConfigService
  - T10.3.3: Xóa bỏ 100% fallback cũ gemini-1.5-flash trong backend
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import router
import schemas
from agents import (
    problem_classifier,
    email_alert_generator,
    flashcard_prompt,
    parent_insights_prompt,
)


class TestUS10_3_AgentConfigIntegration(unittest.TestCase):
    """Kiểm thử tích hợp SystemConfigService vào 5 agent files."""

    @patch("services.system_config_service.get_system_settings")
    def test_router_reads_dynamic_primary_model(self, mock_get_settings):
        """1. Router đọc primary_model và lưu model_used vào meta (AC-SET-02)."""
        mock_get_settings.return_value = {
            "primary_model": "gemini-3.5-flash",
            "temperature": 0.25,
            "top_p": 0.85,
            "max_output_tokens": 768,
        }

        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_cls, \
             patch("router.stream_with_telemetry", return_value=["Xin ", "chao ", "em."]), \
             patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaFakeKey"}):

            mock_model_instance = MagicMock()
            mock_model_cls.return_value = mock_model_instance

            meta = {}
            gen = router.agent_router(
                target_agent="EXPLAIN_AGENT",
                task_description="Gợi mở nhẹ nhàng",
                history_text="",
                user_query="x + 5 = 12",
                expected_answer="7",
                grade_level=5,
                meta=meta,
            )

            # Khởi động generator
            try:
                next(gen)
            except StopIteration:
                pass

            # Xác thực GenerativeModel được khởi tạo với model động
            mock_model_cls.assert_called_once()
            call_kwargs = mock_model_cls.call_args.kwargs
            self.assertEqual(call_kwargs.get("model_name"), "gemini-3.5-flash")
            self.assertEqual(meta.get("model_used"), "gemini-3.5-flash")

    @patch("services.system_config_service.get_system_settings")
    def test_problem_classifier_reads_classifier_model(self, mock_get_settings):
        """2. Problem Classifier đọc classifier_model động."""
        mock_get_settings.return_value = {
            "classifier_model": "gemini-3.1-flash-lite",
        }

        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_cls, \
             patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaFakeKey"}):

            mock_resp = MagicMock()
            mock_resp.text = '{"category": "NEW_TOPIC", "confidence_score": 0.95, "reasoning": "Bài mới", "matched_problem": null, "is_repeated_query": false, "repeat_count": 1, "gentle_reminder": null, "pedagogical_recommendation": "Khuyến nghị", "friendly_parent_title": "[Lớp 5] Phân số – Cộng hai phân số"}'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_resp
            mock_model_cls.return_value = mock_instance

            res = problem_classifier.classify_problem(
                current_problem="Tính 1/2 + 1/3",
                history_problems=[],
                grade=5,
            )

            self.assertEqual(mock_model_cls.call_args.kwargs.get("model_name"), "gemini-3.1-flash-lite")
            self.assertEqual(res.category, "NEW_TOPIC")

    @patch("services.system_config_service.get_system_settings")
    def test_email_alert_generator_reads_email_model(self, mock_get_settings):
        """3. Email Alert Generator đọc email_model động (không dùng gemini-1.5-flash)."""
        mock_get_settings.return_value = {
            "email_model": "gemini-3.1-flash-lite",
        }

        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_cls, \
             patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaFakeKey"}):

            mock_resp = MagicMock()
            mock_resp.text = '{"alert_type": "ACADEMIC_ALERT", "email_subject": "Cảnh báo học tập", "email_body_html": "<p>Nội dung</p>", "recommended_actions_for_parent": ["Giúp con học"], "pedagogical_notes": "Cần cố gắng", "severity_level": "WARNING"}'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_resp
            mock_model_cls.return_value = mock_instance

            req = schemas.AcademicAlertGenerateRequest(
                student_id="std_01",
                student_name="Bé An",
                grade=5,
                trigger_reason="Điểm thấp liên tục",
                consecutive_low_scores_count=3,
                recent_problems=[],
                average_recent_score=35.0,
                difficult_topics=["Phân số"],
            )
            res = email_alert_generator.generate_academic_alert_email(req)

            self.assertEqual(mock_model_cls.call_args.kwargs.get("model_name"), "gemini-3.1-flash-lite")
            self.assertEqual(res.alert_type, "ACADEMIC_ALERT")

    @patch("services.system_config_service.get_system_settings")
    def test_flashcard_prompt_reads_flashcard_model(self, mock_get_settings):
        """4. Flashcard Prompt đọc flashcard_model động."""
        mock_get_settings.return_value = {
            "flashcard_model": "gemini-3.5-flash-lite",
        }

        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_cls, \
             patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaFakeKey"}):

            mock_resp = MagicMock()
            mock_resp.text = '{"problem_statement": "$2x = 10$", "key_takeaway": "$x = 5$", "final_answer": "$x = 5$", "topic_tag": "Tìm X"}'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_resp
            mock_model_cls.return_value = mock_instance

            res = flashcard_prompt.generate_flashcard_content(
                messages=[{"sender_type": "USER", "content": "Tìm x: 2x = 10"}]
            )

            self.assertEqual(mock_model_cls.call_args.kwargs.get("model_name"), "gemini-3.5-flash-lite")
            self.assertEqual(res.topic_tag, "Tìm X")

    @patch("services.system_config_service.get_system_settings")
    def test_parent_insights_prompt_reads_parent_insight_model(self, mock_get_settings):
        """5. Parent Insights Prompt đọc parent_insight_model động."""
        mock_get_settings.return_value = {
            "parent_insight_model": "gemini-3.5-flash",
        }

        with patch("google.generativeai.configure"), \
             patch("google.generativeai.GenerativeModel") as mock_model_cls, \
             patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaFakeKey"}):

            mock_resp = MagicMock()
            mock_resp.text = '{"summary": "Học sinh tiến bộ tốt", "strengths": ["Tự lập"], "weak_points": [], "recommendations": ["Tiếp tục phát huy"], "mastery_assessment": "Tự lập tốt"}'
            mock_instance = MagicMock()
            mock_instance.generate_content.return_value = mock_resp
            mock_model_cls.return_value = mock_instance

            res = parent_insights_prompt.generate_parent_learning_insights(
                student_name="Bé An",
                grade_level=5,
                period_description="Tuần này",
                total_problems_completed=5,
                average_independence_score=85.0,
                total_hints_used=2,
                total_not_understood_count=1,
                topic_breakdown=[],
            )

            self.assertEqual(mock_model_cls.call_args.kwargs.get("model_name"), "gemini-3.5-flash")
            self.assertEqual(res.get("mastery_assessment"), "Tự lập tốt")

    def test_zero_gemini_1_5_flash_occurrences(self):
        """6. Khẳng định không còn bất kỳ dòng code nào chứa gemini-1.5-flash trong 5 agent và router."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target_files = [
            os.path.join(backend_dir, "router.py"),
            os.path.join(backend_dir, "agents", "problem_classifier.py"),
            os.path.join(backend_dir, "agents", "email_alert_generator.py"),
            os.path.join(backend_dir, "agents", "flashcard_prompt.py"),
            os.path.join(backend_dir, "agents", "parent_insights_prompt.py"),
            os.path.join(backend_dir, "routers", "admin_mock.py"),
        ]

        found_occurrences = []
        for file_path in target_files:
            if not os.path.exists(file_path):
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "gemini-1.5-flash" in content:
                    found_occurrences.append(file_path)

        self.assertEqual(found_occurrences, [], f"Phát hiện gemini-1.5-flash còn tồn tại trong: {found_occurrences}")


if __name__ == "__main__":
    unittest.main()
