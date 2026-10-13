import unittest
import os
import sys

# Thêm thư mục backend vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.independence_evaluator import (
    evaluate_independence,
    calculate_independence_score,
    calculate_time_penalty,
)


class TestIndependenceAlgorithm(unittest.TestCase):
    def test_perfect_score_zero_hints(self):
        """0 gợi ý, 0 chưa hiểu, thời gian 120s -> 100 điểm tuyệt đối."""
        res = evaluate_independence(hints_used=0, not_understood_count=0, solving_time_seconds=120)
        self.assertEqual(res.score, 100)
        self.assertIn("Tự lập xuất sắc", res.level)

    def test_one_hint(self):
        """1 gợi ý -> 95 điểm."""
        res = evaluate_independence(hints_used=1, not_understood_count=0, solving_time_seconds=200)
        self.assertEqual(res.score, 95)
        self.assertEqual(res.hint_penalty, 5)

    def test_two_hints(self):
        """2 gợi ý -> 90 điểm."""
        res = evaluate_independence(hints_used=2, not_understood_count=0, solving_time_seconds=250)
        self.assertEqual(res.score, 90)
        self.assertEqual(res.hint_penalty, 10)
        self.assertIn("Tự lập xuất sắc", res.level)

    def test_acceptance_criteria_ac2(self):
        """
        AC2 trong content_sprint.md:
        Dùng 2 hints + bấm 'Chưa hiểu' 3 lần:
        100 - (2 * 5) - (3 * 10) = 100 - 10 - 30 = 60 điểm (Tự lập tốt).
        """
        res = evaluate_independence(hints_used=2, not_understood_count=3, solving_time_seconds=400)
        self.assertEqual(res.score, 60)
        self.assertEqual(res.hint_penalty, 10)
        self.assertEqual(res.struggle_penalty, 30)
        self.assertIn("Tự lập tốt", res.level)

    def test_many_struggles_need_support(self):
        """Dùng 2 hints + bấm 'Chưa hiểu' 7 lần: 100 - 10 - 70 = 20 điểm (< 40đ) -> Cần thêm hỗ trợ."""
        res = evaluate_independence(hints_used=2, not_understood_count=7, solving_time_seconds=400)
        self.assertEqual(res.score, 20)
        self.assertIn("Cần thêm hỗ trợ", res.level)

    def test_floor_score_limit(self):
        """Dùng quá nhiều gợi ý (10 hints, 10 chưa hiểu) -> điểm không âm, giữ sàn 10 điểm."""
        res = evaluate_independence(hints_used=10, not_understood_count=10, solving_time_seconds=500)
        self.assertEqual(res.score, 10)
        self.assertIn("Cần thêm hỗ trợ", res.level)

    def test_time_penalty_over_15_minutes(self):
        """Học sinh ngâm bài > 15 phút (1000s) bị trừ 5 điểm."""
        self.assertEqual(calculate_time_penalty(1000), 5)
        res = evaluate_independence(hints_used=1, not_understood_count=0, solving_time_seconds=1000)
        # 100 - 5 (hint) - 5 (time) = 90
        self.assertEqual(res.score, 90)

    def test_time_penalty_over_30_minutes(self):
        """Học sinh ngâm bài > 30 phút (2000s) bị trừ 10 điểm."""
        self.assertEqual(calculate_time_penalty(2000), 10)
        res = evaluate_independence(hints_used=0, not_understood_count=0, solving_time_seconds=2000)
        # 100 - 10 (time) = 90
        self.assertEqual(res.score, 90)

    def test_dict_output_helper(self):
        """Kiểm tra hàm helper calculate_independence_score trả về đúng cấu trúc dict."""
        data = calculate_independence_score(hints_used=1, not_understood_count=1, solving_time_seconds=180)
        self.assertIn("score", data)
        self.assertIn("level", data)
        self.assertIn("penalties", data)
        # 100 - 5 - 10 = 85
        self.assertEqual(data["score"], 85)


if __name__ == "__main__":
    unittest.main()