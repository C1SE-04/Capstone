import unittest
import os
import sys

# Thêm thư mục backend vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas import (
    SummaryCardsMetric,
    IndependenceTrendPoint,
    ActivityHeatmapPoint,
    MasteryDistribution,
    ParentDashboardMetricsResponse,
)


class TestMetricsSchema(unittest.TestCase):
    def test_summary_cards_schema(self):
        """Kiểm tra schema 4 summary cards khởi tạo hợp lệ."""
        cards = SummaryCardsMetric(
            completed_problems=10,
            avg_independence_score=85.5,
            mastery_level="Tự lập xuất sắc (ít dùng gợi ý)",
            streak_days=5,
            total_active_minutes=150,
            total_active_hours=2.5,
        )
        self.assertEqual(cards.completed_problems, 10)
        self.assertEqual(cards.streak_days, 5)
        self.assertEqual(cards.total_active_hours, 2.5)

    def test_trend_point_schema(self):
        """Kiểm tra schema từng điểm dữ liệu vẽ Line Chart Recharts."""
        point = IndependenceTrendPoint(
            date="2026-10-12",
            display_date="12/10",
            score=90,
            problems_count=3,
            avg_hints=0.5,
        )
        self.assertEqual(point.score, 90)
        self.assertEqual(point.display_date, "12/10")

    def test_heatmap_point_schema(self):
        """Kiểm tra schema từng điểm dữ liệu Heatmap."""
        point = ActivityHeatmapPoint(
            date="2026-10-12",
            day_of_week="Thứ Hai",
            active_minutes=35,
            intensity_level=3,
        )
        self.assertEqual(point.intensity_level, 3)
        self.assertEqual(point.day_of_week, "Thứ Hai")

    def test_full_parent_metrics_response_schema(self):
        """Kiểm tra toàn bộ JSON payload tổng hợp của API Dashboard."""
        mock_payload = {
            "student_id": "student-test-01",
            "time_range": "7d",
            "start_date": "2026-10-06",
            "end_date": "2026-10-12",
            "summary_cards": {
                "completed_problems": 8,
                "avg_independence_score": 82.0,
                "mastery_level": "Tự lập xuất sắc (ít dùng gợi ý)",
                "streak_days": 3,
                "total_active_minutes": 120,
                "total_active_hours": 2.0,
            },
            "independence_trend": [
                {
                    "date": "2026-10-10",
                    "display_date": "10/10",
                    "score": 80,
                    "problems_count": 2,
                    "avg_hints": 1.0,
                },
                {
                    "date": "2026-10-12",
                    "display_date": "12/10",
                    "score": 90,
                    "problems_count": 3,
                    "avg_hints": 0.0,
                },
            ],
            "activity_heatmap": [
                {
                    "date": "2026-10-10",
                    "day_of_week": "Thứ Bảy",
                    "active_minutes": 40,
                    "intensity_level": 3,
                }
            ],
            "mastery_distribution": {
                "excellent_count": 5,
                "good_count": 2,
                "developing_count": 1,
                "needs_support_count": 0,
            },
        }

        response = ParentDashboardMetricsResponse(**mock_payload)
        self.assertEqual(response.student_id, "student-test-01")
        self.assertEqual(response.time_range, "7d")
        self.assertEqual(len(response.independence_trend), 2)
        self.assertEqual(response.summary_cards.completed_problems, 8)
        self.assertEqual(response.mastery_distribution.excellent_count, 5)


if __name__ == "__main__":
    unittest.main()