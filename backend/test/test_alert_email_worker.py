# test/test_alert_email_worker.py
# US 8.1 - Task T8.7: Kiểm thử Background Worker gửi Email Cảnh Báo Phụ Huynh tự động (Dual Alert)

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
import schemas
from database import get_db
from services.email_service import get_sent_emails, clear_sent_emails
from agents.email_alert_generator import censor_sensitive_words
from workers.alert_email_worker import (
    resolve_problem_display_title,
    process_safety_alerts,
    process_academic_alerts,
    process_email_alerts_once,
)


@pytest.fixture(autouse=True)
def clean_sent_emails_fixture():
    clear_sent_emails()
    yield
    clear_sent_emails()


class TestAlertEmailWorker:
    """Bộ kiểm thử cho Dual Email Alert Worker (US 8.1)."""

    def test_01_censor_sensitive_words_filter(self):
        """Kiểm duyệt làm sạch từ ngữ thô tục / chửi thề (AC 8.1.6)."""
        raw_text_1 = "Bài toán này vcl, khó như lồn vậy!"
        censored_1 = censor_sensitive_words(raw_text_1)
        assert "vcl" not in censored_1
        assert "v*" in censored_1 or "v**" in censored_1
        assert "l*" in censored_1

        raw_text_2 = "Thưa thầy con không hiểu câu 3"
        censored_2 = censor_sensitive_words(raw_text_2)
        assert censored_2 == raw_text_2

    def test_02_resolve_problem_title_custom_vs_friendly(self):
        """
        Quy tắc sư phạm cốt lõi US 8.1:
        1. Nếu học sinh CÓ lưu sổ tay & tự gõ tên riêng:
           -> Hiển thị đúng tên con tự đặt (VD: 'Toán tuổi mẹ con khó nhằn')
        2. Nếu học sinh KHÔNG lưu sổ tay (hoặc để trống):
           -> Tự động dùng tên chuẩn sư phạm do AI sinh ra (friendly_parent_title)
        """
        db: Session = next(get_db())
        uid = uuid.uuid4().hex[:6]
        student_id = f"std_title_test_{uid}"

        # Trường hợp 1: Có custom_title do học sinh tự gõ
        score_custom = models.IndependenceScore(
            student_id=student_id,
            score=50,
            custom_title="Toán tuổi mẹ con khó nhằn",
            friendly_parent_title="[Lớp 5] Toán có lời văn – Tìm hai số khi biết tổng và tỉ số",
        )
        display_1, c_title_1, f_title_1 = resolve_problem_display_title(
            db=db, student_id=student_id, score=score_custom, student_grade=5
        )
        assert display_1 == "Toán tuổi mẹ con khó nhằn"
        assert c_title_1 == "Toán tuổi mẹ con khó nhằn"

        # Trường hợp 2: Không có custom_title -> Dùng friendly_parent_title
        score_default = models.IndependenceScore(
            student_id=student_id,
            score=45,
            custom_title=None,
            friendly_parent_title="[Lớp 5] Chuyển động đều – Bài toán hai chuyển động ngược chiều",
        )
        display_2, c_title_2, f_title_2 = resolve_problem_display_title(
            db=db, student_id=student_id, score=score_default, student_grade=5
        )
        assert display_2 == "[Lớp 5] Chuyển động đều – Bài toán hai chuyển động ngược chiều"
        assert c_title_2 is None

    def test_03_process_safety_alerts_success(self):
        """AC 8.1.6: Học sinh dùng từ thô tục -> Phụ huynh nhận email cảnh báo trong vòng 5 phút."""
        db: Session = next(get_db())
        uid = uuid.uuid4().hex[:8]

        # 1. Tạo student & parent & link
        parent = models.User(email=f"parent_safety_{uid}@example.com", role="MONITOR")
        student = models.User(email=f"student_safety_{uid}@example.com", role="STUDENT", grade=6)
        db.add_all([parent, student])
        db.commit()

        link = models.ParentStudentLink(parent_id=parent.id, student_id=student.id, student_nickname="Bé Bi")
        db.add(link)

        # 2. Tạo OrchestratorLog vi phạm an toàn với notify_parent=True
        log = models.OrchestratorLog(
            user_id=student.id,
            user_query="Đồ bot ngu, bài này làm đéo gì hiểu!",
            target_agent="SAFETY_AGENT",
            reason="Phát hiện ngôn từ thô tục profanity",
            notify_parent=True,
            parent_notified_at=None,
        )
        db.add(log)
        db.commit()

        try:
            # 3. Chạy worker xử lý cảnh báo ngôn từ
            count = process_safety_alerts(db)
            assert count == 1

            # 4. Kiểm tra email đã được gửi
            emails = get_sent_emails()
            assert len(emails) >= 1
            sent_mail = next((m for m in emails if m["to_email"] == parent.email), None)
            assert sent_mail is not None
            assert "SAFETY_ALERT" in sent_mail["category"]
            assert sent_mail["status"] == "SENT"

            # 5. Kiểm tra log đã được đóng dấu parent_notified_at trong DB
            db.refresh(log)
            assert log.parent_notified_at is not None

            # 6. Kiểm tra ParentAlertLog đã ghi vết
            alert_log = (
                db.query(models.ParentAlertLog)
                .filter(models.ParentAlertLog.student_id == student.id, models.ParentAlertLog.alert_type == "SAFETY")
                .first()
            )
            assert alert_log is not None
            assert alert_log.recipient_email == parent.email

            # 7. Chạy lại lần 2 không được gửi trùng (idempotent)
            clear_sent_emails()
            count_2 = process_safety_alerts(db)
            assert count_2 == 0
            assert len(get_sent_emails()) == 0

        finally:
            db.query(models.ParentAlertLog).filter(models.ParentAlertLog.student_id == student.id).delete()
            db.query(models.OrchestratorLog).filter(models.OrchestratorLog.id == log.id).delete()
            db.query(models.ParentStudentLink).filter(models.ParentStudentLink.student_id == student.id).delete()
            db.query(models.User).filter(models.User.id.in_([student.id, parent.id])).delete()
            db.commit()

    def test_04_process_academic_alerts_with_custom_titles(self):
        """
        AC 8.1.5: Học sinh giải 3 bài liên tiếp có điểm tự lập < 60đ
        -> Phụ huynh nhận email thông báo kèm tóm tắt và lời khuyên sư phạm trong vòng 5 phút.
        Đảm bảo tên bài con tự đặt hiển thị chính xác trong email!
        """
        db: Session = next(get_db())
        uid = uuid.uuid4().hex[:8]

        parent = models.User(email=f"parent_acad_{uid}@example.com", role="MONITOR")
        student = models.User(email=f"student_acad_{uid}@example.com", role="STUDENT", grade=5)
        db.add_all([parent, student])
        db.commit()

        link = models.ParentStudentLink(parent_id=parent.id, student_id=student.id, student_nickname="Minh Khang")
        db.add(link)

        # Tạo phiên học cho học sinh
        session_obj = models.Session(user_id=student.id, title="Phiên học Toán ôn tập")
        db.add(session_obj)
        db.commit()

        # Tạo 3 bài giải liên tiếp điểm < 60
        # Bài 1: Con tự đặt tên riêng
        score_1 = models.IndependenceScore(
            session_id=session_obj.id,
            student_id=student.id,
            score=45,
            hints_used=2,
            not_understood_count=1,
            custom_title="Toán tuổi mẹ con khó nhằn",
            friendly_parent_title="[Lớp 5] Toán có lời văn – Bài toán tỉ số",
        )
        # Bài 2: Con tự đặt tên riêng
        score_2 = models.IndependenceScore(
            session_id=session_obj.id,
            student_id=student.id,
            score=50,
            hints_used=3,
            not_understood_count=2,
            custom_title="Bài hình học thầy Long dặn",
            friendly_parent_title="[Lớp 5] Hình học – Diện tích hình tam giác",
        )
        # Bài 3: Không tự đặt -> dùng tên AI chuẩn sư phạm
        score_3 = models.IndependenceScore(
            session_id=session_obj.id,
            student_id=student.id,
            score=40,
            hints_used=4,
            not_understood_count=3,
            custom_title=None,
            friendly_parent_title="[Lớp 5] Chuyển động đều – Bài toán hai chuyển động ngược chiều",
        )
        db.add_all([score_1, score_2, score_3])
        db.commit()

        try:
            # Chạy worker xử lý cảnh báo học tập
            count = process_academic_alerts(db, cooldown_hours=24)
            assert count == 1

            emails = get_sent_emails()
            assert len(emails) >= 1
            sent_mail = next((m for m in emails if m["to_email"] == parent.email), None)
            assert sent_mail is not None
            assert "ACADEMIC_ALERT" in sent_mail["category"]

            # Kiểm tra trong ParentAlertLog
            alert_log = (
                db.query(models.ParentAlertLog)
                .filter(models.ParentAlertLog.student_id == student.id, models.ParentAlertLog.alert_type == "ACADEMIC")
                .first()
            )
            assert alert_log is not None
            assert alert_log.recipient_email == parent.email

            # Chạy lại ngay lập tức -> bị chặn bởi cooldown
            clear_sent_emails()
            count_2 = process_academic_alerts(db, cooldown_hours=24)
            assert count_2 == 0
            assert len(get_sent_emails()) == 0

        finally:
            db.query(models.ParentAlertLog).filter(models.ParentAlertLog.student_id == student.id).delete()
            db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == student.id).delete()
            db.query(models.Session).filter(models.Session.id == session_obj.id).delete()
            db.query(models.ParentStudentLink).filter(models.ParentStudentLink.student_id == student.id).delete()
            db.query(models.User).filter(models.User.id.in_([student.id, parent.id])).delete()
            db.commit()

    def test_05_process_email_alerts_once_combined(self):
        """Kiểm tra hàm điều phối tổng process_email_alerts_once."""
        db: Session = next(get_db())
        results = process_email_alerts_once(db)
        assert "safety_alerts" in results
        assert "academic_alerts" in results
        assert isinstance(results["safety_alerts"], int)
        assert isinstance(results["academic_alerts"], int)
