import unittest
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.independence_evaluator import (
    load_independence_rubric,
    export_independence_json,
)


class TestIndependenceJsonExport(unittest.TestCase):
    def test_load_rubric_file(self):
        """Kiểm tra đọc file independence_rubric.json thành công và đúng cấu trúc."""
        rubric = load_independence_rubric()
        self.assertIn("scoring_rules", rubric)
        self.assertIn("mastery_levels", rubric)
        self.assertEqual(rubric["scoring_rules"]["hint_penalty"], 5)
        self.assertEqual(rubric["scoring_rules"]["struggle_penalty"], 10)
        self.assertEqual(rubric["scoring_rules"]["floor_score"], 10)

    def test_export_json_validity(self):
        """Kiểm tra export_independence_json xuất chuỗi JSON hợp lệ, parse lại được."""
        json_str = export_independence_json(
            hints_used=1,
            not_understood_count=1,
            solving_time_seconds=200,
            session_id="test-session-123",
            student_id="test-student-456",
        )
        self.assertIsInstance(json_str, str)

        data = json.loads(json_str)
        self.assertEqual(data["session_id"], "test-session-123")
        self.assertEqual(data["student_id"], "test-student-456")
        self.assertEqual(data["score"], 85)
        self.assertIn("evaluated_at", data)
        self.assertIn("penalties", data)
        self.assertEqual(data["penalties"]["hint_penalty"], 5)
        self.assertEqual(data["penalties"]["struggle_penalty"], 10)

    def test_export_json_ac2_scenario(self):
        """Kiểm tra xuất JSON cho kịch bản AC2: 2 hints + 3 chưa hiểu -> 60 điểm."""
        json_str = export_independence_json(
            hints_used=2,
            not_understood_count=3,
            solving_time_seconds=300,
        )
        data = json.loads(json_str)
        self.assertEqual(data["score"], 60)
        self.assertIn("Tự lập tốt", data["level"])
        self.assertFalse(data["quick_answer_warning"])

    def test_export_json_quick_warning(self):
        """Kiểm tra xuất JSON có cờ cảnh báo giải siêu tốc (< 15s, 0 hint)."""
        json_str = export_independence_json(
            hints_used=0,
            not_understood_count=0,
            solving_time_seconds=10,
        )
        data = json.loads(json_str)
        self.assertEqual(data["score"], 100)
        self.assertTrue(data["quick_answer_warning"])


if __name__ == "__main__":
    unittest.main()