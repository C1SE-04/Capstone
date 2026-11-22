import unittest
from unittest.mock import patch, MagicMock
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from deduplication import (
    compute_problem_hash,
    check_problem_deduplication
)
from routers.independence import save_independence_score
from schemas import ProblemClassificationResult
import models
from database import engine
from sqlalchemy.orm import sessionmaker

TestSessionLocal = sessionmaker(bind=engine)

class TestDeduplicationBackend(unittest.TestCase):

    def setUp(self):
        self.db = TestSessionLocal()
        self.test_student_id = "test-student-dedup-01"
        self.test_session_id = "test-session-dedup-01"

        # Dọn dẹp dữ liệu test cũ nếu có
        self._clean_up()

        # Tạo user và session hợp lệ để thỏa mãn ràng buộc khóa ngoại (Foreign Key)
        user = models.User(
            id=self.test_student_id,
            email="test_dedup_student@socratickid.local",
            hashed_password="dummy_hash_for_test",
            role="STUDENT",
            grade=5,
        )
        self.db.add(user)
        self.db.commit()

        session = models.Session(
            id=self.test_session_id,
            user_id=self.test_student_id,
            title="Phiên giải toán test deduplication",
        )
        self.db.add(session)
        self.db.commit()

    def _clean_up(self):
        try:
            self.db.rollback()
            self.db.query(models.IndependenceScore).filter(
                models.IndependenceScore.student_id == self.test_student_id
            ).delete()
            self.db.query(models.Session).filter(
                models.Session.id == self.test_session_id
            ).delete()
            self.db.query(models.User).filter(
                models.User.id == self.test_student_id
            ).delete()
            self.db.commit()
        except Exception:
            self.db.rollback()

    def tearDown(self):
        self._clean_up()
        self.db.close()

    def test_compute_problem_hash_normalization(self):
        """Kiểm tra hàm băm SHA-256 chuẩn hóa: khác chữ hoa/thường hoặc khoảng trắng vẫn ra cùng hash."""
        text1 = "Tìm x biết: 2x + 4 = 10"
        text2 = "  tìm X biết:   2x + 4 = 10. "
        hash1 = compute_problem_hash(text1)
        hash2 = compute_problem_hash(text2)
        
        self.assertEqual(len(hash1), 64)
        self.assertEqual(hash1, hash2, "Hai câu đề bài giống nhau về câu chữ phải sinh ra cùng 1 SHA-256 hash.")

    def test_fast_path_exact_duplicate_without_gemini(self):
        """Kiểm tra Fast-path: Đề bài trùng hash lập tức nhận diện EXACT_DUPLICATE mà không gọi Gemini."""
        problem = "Tìm x biết 3x - 5 = 10"
        prob_hash = compute_problem_hash(problem)

        # Giả lập đã có 1 bài toán hoàn thành trước đó trong DB
        old_record = models.IndependenceScore(
            session_id=self.test_session_id,
            student_id=self.test_student_id,
            score=90,
            problem_text=problem,
            problem_hash=prob_hash,
            category="NEW_TOPIC",
            is_duplicate=False
        )
        self.db.add(old_record)
        self.db.commit()

        # Gọi kiểm tra bài lặp (Fast-path)
        result = check_problem_deduplication(
            db=self.db,
            student_id=self.test_student_id,
            current_problem=problem
        )

        self.assertEqual(result.category, "EXACT_DUPLICATE")
        self.assertTrue(result.is_repeated_query)
        self.assertIsNotNone(result.gentle_reminder)
        self.assertIn("thử sức bài nâng cao", result.gentle_reminder)

    @patch("deduplication.classify_problem")
    def test_slow_path_isomorphic_practice_marked_correctly(self, mock_classify):
        """Kiểm tra bài cùng dạng đổi số được gán nhãn ISOMORPHIC_PRACTICE và is_duplicate=False."""
        mock_classify.return_value = ProblemClassificationResult(
            category="ISOMORPHIC_PRACTICE",
            confidence_score=0.9,
            reasoning="Cùng dạng Tìm hai số biết tổng và hiệu nhưng thay đổi số liệu.",
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Ghi nhận luyện tập củng cố."
        )

        record = save_independence_score(
            db=self.db,
            session_id=self.test_session_id,
            student_id=self.test_student_id,
            custom_score=85,
            problem_text_input="Tìm hai số biết tổng là 80 và hiệu là 20"
        )

        self.assertEqual(record.category, "ISOMORPHIC_PRACTICE")
        self.assertFalse(record.is_duplicate, "Bài luyện tập củng cố KHÔNG phải là bài trùng lặp rác.")

    def test_deduplication_blocks_total_completed_increment(self):
        """Kiểm tra AC 8.1.1: Hoàn thành bài trùng lặp thì total_completed KHÔNG TĂNG THÊM."""
        problem = "Tính diện tích hình chữ nhật có dài 6cm rộng 4cm"

        # Lần 1: Giải bài lần đầu tiên -> Tính là 1 bài hoàn thành
        rec1 = save_independence_score(
            db=self.db,
            session_id=self.test_session_id,
            student_id=self.test_student_id,
            custom_score=100,
            problem_text_input=problem
        )
        self.assertFalse(rec1.is_duplicate)

        # Lần 2: Học sinh giải lại y hệt đề bài trên -> Bị đánh dấu is_duplicate=True
        rec2 = save_independence_score(
            db=self.db,
            session_id=self.test_session_id,
            student_id=self.test_student_id,
            custom_score=100,
            problem_text_input=problem
        )
        self.assertTrue(rec2.is_duplicate)
        self.assertEqual(rec2.category, "EXACT_DUPLICATE")

        # Đếm số bài hoàn thành thực chất (lọc bỏ is_duplicate=True)
        total_completed = (
            self.db.query(models.IndependenceScore)
            .filter(
                models.IndependenceScore.student_id == self.test_student_id,
                models.IndependenceScore.is_duplicate == False
            )
            .count()
        )
        self.assertEqual(total_completed, 1, "Thẻ tổng số bài hoàn thành PHẢI giữ nguyên là 1, không được tăng lên 2!")


if __name__ == "__main__":
    unittest.main()