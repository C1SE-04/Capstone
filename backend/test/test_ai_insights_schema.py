import unittest
from datetime import datetime, timezone
import sys
import os
from pydantic import ValidationError

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from schemas import (
    AiInsightReportResponse,
    TopicBreakdownItem,
    AiInsightGenerateRequest,
    ParentAiInsightResponse,
)
from agents.parent_insights_prompt import generate_parent_learning_insights

class TestAiInsightsSchema(unittest.TestCase):

    def test_valid_ai_insight_report_response(self):
        """Kiểm tra Pydantic parse thành công dữ liệu hợp lệ từ Gemini."""
        raw_data = {
            "summary": "Em Bảo Nam hoàn thành xuất sắc 8 bài toán.",
            "strengths": ["Tư duy hình học tốt", "Tính toán phân số nhanh"],
            "weak_points": ["Cần thêm thời gian ở toán có lời văn"],
            "recommendations": ["Khuyến khích con vẽ sơ đồ ra nháp"],
            "mastery_assessment": "Tự lập tốt",
        }
        report = AiInsightReportResponse.model_validate(raw_data)
        self.assertEqual(report.summary, raw_data["summary"])
        self.assertEqual(len(report.strengths), 2)
        self.assertEqual(report.mastery_assessment, "Tự lập tốt")
        self.assertFalse(report.is_fallback)

    def test_missing_summary_raises_validation_error(self):
        """Kiểm tra nếu thiếu trường 'summary' bắt buộc thì Pydantic phải báo lỗi ValidationError."""
        invalid_data = {
            "strengths": ["Rất chăm chỉ"],
            "weak_points": [],
            "recommendations": []
        }
        with self.assertRaises(ValidationError):
            AiInsightReportResponse.model_validate(invalid_data)

    def test_default_values_for_empty_lists(self):
        """Kiểm tra các trường list tự động gán [] nếu không được truyền vào."""
        minimal_data = {
            "summary": "Tóm tắt ngắn gọn",
        }
        report = AiInsightReportResponse.model_validate(minimal_data)
        self.assertEqual(report.strengths, [])
        self.assertEqual(report.weak_points, [])
        self.assertEqual(report.recommendations, [])
        self.assertEqual(report.mastery_assessment, "Đang tiến bộ")

    def test_parent_ai_insight_response_nesting(self):
        """Kiểm tra Schema lồng ghép dành cho API GET /parent/insights của Thống và Thiên."""
        insight_data = AiInsightReportResponse(
            summary="Tiến bộ vượt bậc",
            strengths=["Tự lập cao"],
            weak_points=[],
            recommendations=["Duy trì thói quen học"],
            mastery_assessment="Tự lập xuất sắc"
        )
        parent_response = ParentAiInsightResponse(
            student_id="student_123",
            student_name="Bảo Nam",
            period_description="Tuần 3 tháng 10",
            insight=insight_data,
            created_at=datetime.now(timezone.utc)
        )
        self.assertEqual(parent_response.student_id, "student_123")
        self.assertEqual(parent_response.insight.mastery_assessment, "Tự lập xuất sắc")

    def test_generate_insights_returns_schema_conformant_dict(self):
        """Kiểm tra hàm generate_parent_learning_insights luôn trả về dữ liệu thỏa mãn Schema."""
        # Gọi không có API key -> kích hoạt fallback
        result = generate_parent_learning_insights(
            student_name="Tuấn Kiệt",
            grade_level=6,
            period_description="7 ngày qua",
            total_problems_completed=5,
            average_independence_score=62.0,
            total_hints_used=6,
            total_not_understood_count=2,
            topic_breakdown=[],
            api_key=None
        )
        # Validate dict trả về
        report = AiInsightReportResponse.model_validate(result)
        self.assertTrue(report.is_fallback)
        self.assertIn("Tuấn Kiệt", report.summary)
        self.assertEqual(report.mastery_assessment, "Tự lập tốt")


if __name__ == "__main__":
    unittest.main()