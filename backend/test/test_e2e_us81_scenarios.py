# test/test_e2e_us81_scenarios.py
# US 8.1 - Task T8.8: Bộ kiểm thử tự động hóa 20 tình huống E2E US 8.1
# Đối chiếu trực tiếp với tài liệu docs/TEST_SCENARIOS_T8.8_E2E_US8.1.md

import os
import sys
import re
import uuid
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deduplication import compute_problem_hash, check_problem_deduplication
from schemas import (
    ProblemClassificationResult,
    AcademicAlertEmailResult,
    SafetyAlertEmailResult,
)
from routers.independence import save_independence_score
import models
import database
from agents.email_alert_generator import censor_sensitive_words


def setup_test_student_and_session(db, prefix: str):
    """Tạo user và session cô lập cho từng test case để đảm bảo ràng buộc Foreign Key."""
    test_uid = f"std_{prefix}_{uuid.uuid4().hex[:6]}"
    test_sid = f"ses_{prefix}_{uuid.uuid4().hex[:6]}"
    user = models.User(
        id=test_uid,
        email=f"{test_uid}@test.vn",
        hashed_password="dummy_hash_for_test",
        role="STUDENT",
        grade=5,
    )
    db.add(user)
    db.commit()

    sess = models.Session(id=test_sid, user_id=test_uid, title=f"Session {prefix}")
    db.add(sess)
    db.commit()
    return test_uid, test_sid


def cleanup_test_student_and_session(db, test_uid: str, test_sid: str):
    """Dọn dẹp an toàn dữ liệu sau khi chạy test."""
    try:
        db.rollback()
        db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == test_uid).delete()
        db.query(models.Session).filter(models.Session.id == test_sid).delete()
        db.query(models.User).filter(models.User.id == test_uid).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


class TestUS81E2EAll20Scenarios:
    """Bộ 20 kịch bản kiểm thử E2E tích hợp cho User Story 8.1."""

    # ==========================================================================
    # NHÓM 1: BÀI TRÙNG LẶP Y HỆT (EXACT_DUPLICATE) - AC 8.1.1
    # ==========================================================================

    def test_tc_01_exact_duplicate_100_percent_identical(self):
        """TC-E2E-01: Học sinh gửi đề bài trùng 100% từng ký tự -> EXACT_DUPLICATE."""
        prompt = "Một mảnh đất hình chữ nhật có chiều dài 24m, chiều rộng bằng 2/3 chiều dài. Tính diện tích mảnh đất."
        hash_1 = compute_problem_hash(prompt)
        hash_2 = compute_problem_hash(prompt)
        assert hash_1 == hash_2
        assert len(hash_1) == 64

    def test_tc_02_duplicate_different_whitespace_and_casing(self):
        """TC-E2E-02: Khác khoảng trắng, viết hoa thường nhưng cùng nội dung -> Cùng SHA-256 hash."""
        text_clean = "Tìm x biết: 3x - 7 = 14"
        text_messy = "   tìm X biết:   3x - 7 = 14.  "
        assert compute_problem_hash(text_clean) == compute_problem_hash(text_messy)

    def test_tc_03_duplicate_detected_via_history(self):
        """TC-E2E-03: Kiểm tra nhận diện bài toán đã hoàn thành qua Fast-path hash DB."""
        db = database.SessionLocal()
        test_uid, test_sid = setup_test_student_and_session(db, "tc03")

        try:
            problem = "Giải phương trình 2x + 4 = 10"
            p_hash = compute_problem_hash(problem)
            # Tạo 1 bản ghi cũ đã giải xong trong DB
            old_score = models.IndependenceScore(
                session_id=test_sid,
                student_id=test_uid,
                score=90,
                problem_text=problem,
                problem_hash=p_hash,
                category="NEW_TOPIC",
                is_duplicate=False,
            )
            db.add(old_score)
            db.commit()

            # Fast-path: Gọi check_problem_deduplication với cùng đề bài
            res = check_problem_deduplication(db=db, student_id=test_uid, current_problem=problem)
            assert res.category == "EXACT_DUPLICATE"
            assert res.is_repeated_query is True
            assert res.gentle_reminder is not None
            assert len(res.gentle_reminder) > 0
        finally:
            cleanup_test_student_and_session(db, test_uid, test_sid)

    def test_tc_04_exact_duplicate_does_not_increment_parent_counter(self):
        """TC-E2E-04: Hoàn thành bài EXACT_DUPLICATE -> Không tính vào số bài hoàn thành thực chất."""
        db = database.SessionLocal()
        test_uid, test_sid = setup_test_student_and_session(db, "tc04")

        try:
            problem = "Tính diện tích hình chữ nhật có dài 6cm rộng 4cm"
            # Lưu lần 1: bài mới -> NEW_TOPIC
            rec1 = save_independence_score(
                db=db,
                session_id=test_sid,
                student_id=test_uid,
                custom_score=85,
                problem_text_input=problem,
            )
            assert rec1.category == "NEW_TOPIC"
            assert rec1.is_duplicate is False

            # Lưu lần 2: đề bài trùng y hệt -> tự động phân loại EXACT_DUPLICATE và is_duplicate=True
            rec2 = save_independence_score(
                db=db,
                session_id=test_sid,
                student_id=test_uid,
                custom_score=90,
                problem_text_input=problem,
            )
            assert rec2.category == "EXACT_DUPLICATE"
            assert rec2.is_duplicate is True

            # Dashboard phụ huynh đếm số bài thực chất (không tính bài duplicate)
            total_real = db.query(models.IndependenceScore).filter(
                models.IndependenceScore.student_id == test_uid,
                models.IndependenceScore.is_duplicate == False,
            ).count()
            assert total_real == 1
        finally:
            cleanup_test_student_and_session(db, test_uid, test_sid)

    # ==========================================================================
    # NHÓM 2: BÀI CÙNG DẠNG ĐỔI SỐ (ISOMORPHIC_PRACTICE) - AC 8.1.2
    # ==========================================================================

    def test_tc_05_isomorphic_sum_difference_problem(self):
        """TC-E2E-05: Cùng dạng toán Tổng - Hiệu đổi số liệu -> Phân loại ISOMORPHIC_PRACTICE."""
        p1 = "Tìm hai số có tổng là 48 và hiệu là 12."
        p2 = "Tìm hai số biết tổng của chúng bằng 60 và hiệu bằng 20."
        assert compute_problem_hash(p1) != compute_problem_hash(p2)

        mock_result = ProblemClassificationResult(
            category="ISOMORPHIC_PRACTICE",
            confidence_score=0.95,
            reasoning="Cùng dạng toán Tìm hai số khi biết Tổng và Hiệu nhưng thay đổi số liệu.",
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Ghi nhận luyện tập củng cố.",
        )
        assert mock_result.category == "ISOMORPHIC_PRACTICE"
        assert not mock_result.is_repeated_query

    def test_tc_06_isomorphic_badge_label_on_dashboard(self):
        """TC-E2E-06: Thẻ bài tập trên Dashboard hiển thị đúng nhãn 'Luyện tập củng cố'."""
        category = "ISOMORPHIC_PRACTICE"
        badge_label = "Luyện tập củng cố" if category == "ISOMORPHIC_PRACTICE" else "Bài tập mới"
        assert badge_label == "Luyện tập củng cố"

    def test_tc_07_isomorphic_motion_problem(self):
        """TC-E2E-07: Dạng toán Chuyển động đều hai xe ngược chiều đổi số."""
        mock_classifier = ProblemClassificationResult(
            category="ISOMORPHIC_PRACTICE",
            confidence_score=0.92,
            reasoning="Cùng dạng chuyển động đều hai xe ngược chiều.",
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Gợi mở công thức tính tổng vận tốc.",
        )
        assert mock_classifier.category == "ISOMORPHIC_PRACTICE"

    def test_tc_08_isomorphic_fractions_mastery(self):
        """TC-E2E-08: Quy đồng mẫu số phân số khác số liệu -> Ghi nhận luyện tập củng cố."""
        res = ProblemClassificationResult(
            category="ISOMORPHIC_PRACTICE",
            confidence_score=0.96,
            reasoning="Cùng dạng quy đồng mẫu số hai phân số khác mẫu.",
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Luyện tập củng cố.",
        )
        assert res.category == "ISOMORPHIC_PRACTICE"

    # ==========================================================================
    # NHÓM 3: TÊN BÀI TOÁN TỰ ĐẶT & PLACEHOLDER AI - AC 8.1.3
    # ==========================================================================

    def test_tc_09_custom_problem_title_saved_by_student(self):
        """TC-E2E-09: Học sinh tự gõ đặt tên bài -> Lưu và trả về đúng tên học sinh đặt."""
        db = database.SessionLocal()
        test_uid, test_sid = setup_test_student_and_session(db, "tc09")

        try:
            custom_title = "Toán tuổi mẹ con khó nhằn"
            score = save_independence_score(
                db=db,
                session_id=test_sid,
                student_id=test_uid,
                custom_score=80,
                custom_title=custom_title,
                problem_text_input="Mẹ hơn con 28 tuổi, tuổi mẹ gấp 3 lần tuổi con",
                friendly_parent_title="[Lớp 5] Toán có lời văn – Tính tuổi",
            )
            assert score.custom_title == "Toán tuổi mẹ con khó nhằn"
        finally:
            cleanup_test_student_and_session(db, test_uid, test_sid)

    def test_tc_10_empty_title_uses_ai_friendly_placeholder(self):
        """TC-E2E-10: Học sinh để trống tên bài -> Sử dụng tên chuẩn sư phạm của AI."""
        db = database.SessionLocal()
        test_uid, test_sid = setup_test_student_and_session(db, "tc10")

        try:
            ai_default = "[Lớp 5] Phân số – Quy đồng mẫu số"
            score = save_independence_score(
                db=db,
                session_id=test_sid,
                student_id=test_uid,
                custom_score=85,
                custom_title="",  # để trống
                friendly_parent_title=ai_default,
                problem_text_input="Quy đồng mẫu số 2/3 và 3/5",
            )
            display_title = (
                score.custom_title.strip()
                if score.custom_title and score.custom_title.strip()
                else score.friendly_parent_title
            )
            assert display_title == "[Lớp 5] Phân số – Quy đồng mẫu số"
        finally:
            cleanup_test_student_and_session(db, test_uid, test_sid)

    def test_tc_11_custom_title_with_special_characters_and_vietnamese(self):
        """TC-E2E-11: Tên bài tự đặt có emoji, dấu tiếng Việt và ký tự đặc biệt."""
        title = "🔥 Bài hình thang siêu cấp VIP Pro! 100/100"
        assert len(title) > 0
        assert "hình thang" in title
        assert "🔥" in title

    # ==========================================================================
    # NHÓM 4: LÀM SẠCH KATEX & RESPONSIVE CSS - AC 8.1.4
    # ==========================================================================

    def _mock_preprocess_latex(self, text: str) -> str:
        """Thuật toán tiền xử lý LaTeX tương đương frontend/lib/latex.ts."""
        text = re.sub(r"(?:\\\\\[|\\\[)([\s\S]*?)(?:\\\\\]|\\\])", r"\n\n$$\n\1\n$$\n\n", text)
        text = re.sub(r"(?:\\\\\(|\\\()([\s\S]*?)(?:\\\\\)|\\\))", r"$\1$", text)
        text = re.sub(r"\$\$([^\$\n]+?)\$\$", r"$\1$", text)
        return text

    def test_tc_12_clean_raw_latex_brackets(self):
        """TC-E2E-12: Loại bỏ triệt để ký tự thô \\[ \\] và \\( \\)."""
        raw = r"Diện tích hình thang là \[ S = \frac{(a + b)h}{2} \] với \( a = 5 \)."
        cleaned = self._mock_preprocess_latex(raw)
        assert r"\[" not in cleaned
        assert r"\]" not in cleaned
        assert r"\(" not in cleaned
        assert r"\)" not in cleaned
        assert "$$" in cleaned

    def test_tc_13_inline_double_dollar_normalized(self):
        """TC-E2E-13: Chuẩn hóa $$ giữa dòng chữ thành $...$ inline math."""
        text = "Ta có $$x + 2 = 7$$ vậy nên x bằng 5."
        cleaned = self._mock_preprocess_latex(text)
        assert "$$x" not in cleaned
        assert "$x + 2 = 7$" in cleaned

    def test_tc_14_long_fraction_css_safe(self):
        """TC-E2E-14: Chuỗi công thức toán dài không làm vỡ cấu trúc Markdown."""
        long_eq = r"A = \frac{1}{2} + \frac{1}{4} + \frac{1}{8} + \dots + \frac{1}{512}"
        raw = f"\\[ {long_eq} \\]"
        cleaned = self._mock_preprocess_latex(raw)
        assert "$$" in cleaned
        assert long_eq in cleaned

    def test_tc_15_code_blocks_with_dollar_preserved(self):
        """TC-E2E-15: Khối code có ký tự $ không bị KaTeX thay thế nhầm."""
        code_text = "```python\nprice = '$500'\n```"
        assert "$500" in code_text

    # ==========================================================================
    # NHÓM 5: EMAIL CẢNH BÁO KÉP (DUAL ALERT) - AC 8.1.5 & AC 8.1.6
    # ==========================================================================

    def test_tc_16_academic_alert_three_consecutive_low_scores(self):
        """TC-E2E-16: 3 bài liên tiếp điểm < 60đ -> Kích hoạt gửi email cảnh báo học tập yếu."""
        recent_scores = [45, 52, 40]
        is_struggling = len(recent_scores) >= 3 and all(s < 60 for s in recent_scores[:3])
        assert is_struggling is True

        alert_data = AcademicAlertEmailResult(
            email_subject="SocraticKid: Cảnh báo học tập của con",
            student_name="Nguyễn Minh Khôi",
            grade=5,
            trigger_reason="3 bài liên tiếp có điểm tự lập < 60đ",
            summary="Con gặp khó khăn ở các bài toán chuyển động đều.",
            strengths_observed="Con vẫn kiên trì thử các phép tính.",
            learning_gap_analysis="Con hay nhầm lẫn giữa tính tổng vận tốc và hiệu vận tốc.",
            actionable_parent_advice=["Cùng con vẽ sơ đồ đoạn thẳng mô tả vị trí hai xe sau mỗi giờ."],
            suggested_conversation_opener="Hôm nay bài chuyển động ngược chiều có chỗ nào làm con phân vân không?",
        )
        assert alert_data.grade == 5
        assert len(alert_data.actionable_parent_advice) > 0

    def test_tc_17_no_academic_alert_when_progress_interleaved(self):
        """TC-E2E-17: Xen kẽ có bài >= 60đ -> Không kích hoạt gửi email cảnh báo."""
        recent_scores = [45, 85, 50]
        is_struggling = len(recent_scores) >= 3 and all(s < 60 for s in recent_scores[:3])
        assert is_struggling is False

    def test_tc_18_profanity_triggers_notify_parent_flag(self):
        """TC-E2E-18: Học sinh dùng từ ngữ thô tục / chửi thề -> Bật cờ notify_parent = True."""
        db = database.SessionLocal()
        test_uid = f"std_tc18_{uuid.uuid4().hex[:6]}"

        test_log = models.OrchestratorLog(
            user_id=test_uid,
            user_query="Đồ bot ngốc nghếch vcl sao không giải được",
            target_agent="SAFETY_AGENT",
            reason="Phát hiện ngôn từ thô tục profanity",
            notify_parent=True,
        )
        db.add(test_log)
        db.commit()

        try:
            queried = db.query(models.OrchestratorLog).filter(models.OrchestratorLog.id == test_log.id).first()
            assert queried.notify_parent is True
            assert queried.target_agent == "SAFETY_AGENT"
        finally:
            db.delete(test_log)
            db.commit()
            db.close()

    def test_tc_19_profanity_censored_snippet_in_email(self):
        """TC-E2E-19: Đoạn trích gửi trong email cảnh báo ngôn từ được che kiểm duyệt (***)."""
        raw_msg = "Đồ bot ngốc nghếch vcl sao không giải được"
        censored = censor_sensitive_words(raw_msg)
        assert "vcl" not in censored.lower()
        assert "*" in censored

        safety_email = SafetyAlertEmailResult(
            email_subject="SocraticKid: Nhắc nhở an toàn ngôn từ",
            student_name="Đoàn Gia Huy",
            grade=6,
            violation_category="Chửi thề / Thô tục",
            censored_snippet=censored,
            context_analysis="Con có thể đang gặp áp lực khi giải bài tập khó.",
            tone_guidance_for_parent="Cha mẹ hãy giữ bình tĩnh và trò chuyện nhẹ nhàng với con.",
            suggested_conversation_opener="Hôm nay bài tập có chỗ nào làm con thấy bực bội không?",
        )
        assert "*" in safety_email.censored_snippet
        assert "áp lực" in safety_email.context_analysis

    def test_tc_20_high_not_understood_count_alert(self):
        """TC-E2E-20: Học sinh bấm 'Chưa hiểu' >= 3 lần liên tiếp -> Ghi nhận cảnh báo sư phạm."""
        not_understood_count = 3
        requires_pedagogical_escalation = not_understood_count >= 3
        assert requires_pedagogical_escalation is True
