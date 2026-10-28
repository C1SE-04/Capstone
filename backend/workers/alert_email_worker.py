# workers/alert_email_worker.py
# US 8.1 - Task T8.7: Background Worker gửi Email Cảnh Báo Phụ Huynh tự động trong 5 phút

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from database import SessionLocal
from services.email_service import (
    send_email,
    render_academic_alert_html,
    render_safety_alert_html,
)
from agents.email_alert_generator import (
    generate_academic_alert_email,
    generate_safety_alert_email,
)
from agents.problem_title_generator import generate_friendly_problem_title


def resolve_problem_display_title(
    db: Session,
    student_id: str,
    score: models.IndependenceScore,
    student_grade: int = 5
) -> Tuple[str, Optional[str], str]:
    """
    Xác định tên bài toán hiển thị cho Phụ Huynh theo đúng quy tắc sư phạm US 8.1:
    1. Nếu bài đó học sinh CÓ lưu vào sổ tay & tự gõ tên riêng (custom_title):
       -> Hiển thị đúng tên con tự đặt (VD: "Toán tuổi mẹ con khó nhằn", "Bài hình học thầy Long dặn")
    2. Nếu bài đó học sinh KHÔNG bấm lưu vào sổ tay (hoặc có lưu nhưng để trống tên):
       -> Tự động dùng tên chuẩn sư phạm do AI sinh ra (friendly_parent_title)
          (VD: "[Lớp 5] Chuyển động đều – Bài toán hai chuyển động ngược chiều")

    Trả về tuple: (display_title, resolved_custom_title, resolved_friendly_title)
    """
    resolved_custom_title: Optional[str] = None

    # 1. Kiểm tra custom_title trực tiếp trên bản ghi independence_scores
    if score.custom_title and score.custom_title.strip():
        resolved_custom_title = score.custom_title.strip()
    elif score.session_id:
        # Tra cứu từ bảng problem_bookmarks xem học sinh có bookmark bài này và đặt tên riêng không
        matching_bms = (
            db.query(models.ProblemBookmark)
            .filter(
                models.ProblemBookmark.student_id == student_id,
                models.ProblemBookmark.session_id == score.session_id,
            )
            .all()
        )
        for bm in matching_bms:
            if bm.title and bm.title.strip():
                bm_title = bm.title.strip()
                # Phân biệt tên do con tự đặt vs tên mẫu sư phạm mặc định
                # Tên AI chuẩn sư phạm luôn có dạng: [Lớp X] ... – ...
                is_ai_pattern = bm_title.startswith("[Lớp ") and " – " in bm_title
                if not is_ai_pattern:
                    resolved_custom_title = bm_title
                    break

    # 2. Tên chuẩn sư phạm (friendly_parent_title) do AI sinh ra
    resolved_friendly_title: str = ""
    if score.friendly_parent_title and score.friendly_parent_title.strip():
        resolved_friendly_title = score.friendly_parent_title.strip()
    else:
        prob_text = (
            score.problem_text
            or "Bài toán luyện tập môn Toán"
        )
        try:
            auto_title_obj = generate_friendly_problem_title(
                problem_text=prob_text,
                grade=student_grade
            )
            resolved_friendly_title = auto_title_obj.friendly_parent_title
        except Exception:
            resolved_friendly_title = f"[Lớp {student_grade}] Toán học – Luyện tập chung"

        # Cache lại vào database để không phải sinh lại nhiều lần
        score.friendly_parent_title = resolved_friendly_title
        try:
            db.commit()
        except Exception:
            db.rollback()

    # Tiêu đề bài toán hiển thị: Ưu tiên tên con tự đặt, fallback về tên AI chuẩn sư phạm
    display_title = resolved_custom_title if resolved_custom_title else resolved_friendly_title
    return display_title, resolved_custom_title, resolved_friendly_title


def process_safety_alerts(db: Session) -> int:
    """
    Quét bảng orchestrator_logs tìm các log vi phạm an toàn ngôn từ (notify_parent=True)
    chưa gửi thông báo (parent_notified_at is None), sinh nội dung email và gửi cho phụ huynh.
    """
    unnotified_logs = (
        db.query(models.OrchestratorLog)
        .filter(
            models.OrchestratorLog.notify_parent == True,
            models.OrchestratorLog.parent_notified_at.is_(None)
        )
        .order_by(models.OrchestratorLog.created_at.asc())
        .all()
    )

    if not unnotified_logs:
        return 0

    processed_count = 0
    now_utc = datetime.now(timezone.utc)

    for log in unnotified_logs:
        try:
            # 1. Xác định học sinh gửi tin nhắn
            student_id = log.user_id
            if not student_id and log.session_id:
                session_obj = db.query(models.Session).filter(models.Session.id == log.session_id).first()
                if session_obj:
                    student_id = session_obj.user_id

            student = db.query(models.User).filter(models.User.id == student_id).first() if student_id else None

            # 2. Tìm danh sách phụ huynh được liên kết
            parents: List[models.User] = []
            student_nickname: Optional[str] = None
            if student:
                links = db.query(models.ParentStudentLink).filter(models.ParentStudentLink.student_id == student.id).all()
                if links:
                    parent_ids = [l.parent_id for l in links]
                    parents = db.query(models.User).filter(models.User.id.in_(parent_ids)).all()
                    student_nickname = links[0].student_nickname

            student_name = student_nickname or (student.email.split("@")[0] if student else "Học sinh")
            grade = student.grade if (student and student.grade) else 5

            # 3. Phân loại vi phạm
            reason_str = (log.reason or "").lower()
            violation_type = "PROFANITY" if any(k in reason_str for k in ("profan", "tục", "chửi")) else "TOXIC_LANGUAGE"

            incident_time_str = log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else now_utc.strftime("%Y-%m-%d %H:%M:%S")

            # 4. Sinh nội dung email cảnh báo ngôn từ qua AI Generator
            req = schemas.SafetyAlertGenerateRequest(
                student_id=student_id or "anonymous",
                student_name=student_name,
                grade=grade,
                violation_type=violation_type,
                original_message=log.user_query,
                incident_time=incident_time_str,
            )
            email_result = generate_safety_alert_email(request_data=req)

            # 5. Gửi email tới tất cả phụ huynh được liên kết
            if parents:
                html_body = render_safety_alert_html(email_result.model_dump())
                text_body = (
                    f"Thông báo nhắc nhở ngôn từ SocraticKid\n\n"
                    f"Học sinh: {student_name} (Lớp {grade})\n"
                    f"Trích đoạn kiểm duyệt: {email_result.censored_snippet}\n"
                    f"Phân tích: {email_result.context_analysis}\n"
                    f"Định hướng: {email_result.tone_guidance_for_parent}\n"
                )

                for parent in parents:
                    send_email(
                        to_email=parent.email,
                        subject=email_result.email_subject,
                        text_content=text_body,
                        html_content=html_body,
                        category="SAFETY_ALERT",
                    )

                    # Ghi vết lịch sử thông báo
                    alert_log = models.ParentAlertLog(
                        student_id=student.id,
                        parent_id=parent.id,
                        alert_type="SAFETY",
                        recipient_email=parent.email,
                        subject=email_result.email_subject,
                        email_body=html_body,
                        trigger_reason=log.reason or "Vi phạm quy tắc ngôn từ trong chat",
                    )
                    db.add(alert_log)

            # 6. Đánh dấu log đã được thông báo để không gửi lại
            log.parent_notified_at = now_utc
            db.commit()
            processed_count += 1
            print(f"[AlertWorker] 🛡️ Đã xử lý cảnh báo ngôn từ log {log.id} (Học sinh: {student_name})")

        except Exception as e:
            db.rollback()
            print(f"[AlertWorker] ❌ Lỗi khi xử lý safety alert log {log.id}: {e}")

    return processed_count


def process_academic_alerts(db: Session, cooldown_hours: int = 24) -> int:
    """
    Quét danh sách học sinh có kết quả học tập gặp khó khăn:
    - 3 bài liên tiếp có điểm tự lập < 60đ
    - Hoặc tỷ lệ 'Chưa hiểu' tăng đột biến (>= 3 lần trong 3 bài gần nhất)
    Tuân thủ quy tắc hiển thị tên bài do con tự đặt hoặc tên AI chuẩn sư phạm.
    """
    students = db.query(models.User).filter(models.User.role == "STUDENT").all()
    if not students:
        return 0

    processed_count = 0
    now_utc = datetime.now(timezone.utc)

    for student in students:
        try:
            # 1. Tìm phụ huynh của học sinh
            links = db.query(models.ParentStudentLink).filter(models.ParentStudentLink.student_id == student.id).all()
            if not links:
                continue

            parent_ids = [l.parent_id for l in links]
            parents = db.query(models.User).filter(models.User.id.in_(parent_ids)).all()
            if not parents:
                continue

            # 2. Lấy 3 bài tập gần đây nhất
            recent_scores = (
                db.query(models.IndependenceScore)
                .filter(models.IndependenceScore.student_id == student.id)
                .order_by(models.IndependenceScore.created_at.desc())
                .limit(3)
                .all()
            )

            if len(recent_scores) < 3:
                continue

            # 3. Kiểm tra điều kiện kích hoạt Cảnh báo Học tập
            has_3_consecutive_low = all(s.score < 60 for s in recent_scores)
            total_not_understood = sum((s.not_understood_count or 0) for s in recent_scores)
            has_not_understood_spike = total_not_understood >= 3

            if not (has_3_consecutive_low or has_not_understood_spike):
                continue

            # 4. Kiểm tra Cooldown để tránh gửi email dồn dập trong 5 phút
            last_alert = (
                db.query(models.ParentAlertLog)
                .filter(
                    models.ParentAlertLog.student_id == student.id,
                    models.ParentAlertLog.alert_type == "ACADEMIC"
                )
                .order_by(models.ParentAlertLog.created_at.desc())
                .first()
            )

            if last_alert:
                # Nếu bài mới nhất được làm trước thời điểm gửi email gần nhất -> đã thông báo rồi
                if recent_scores[0].created_at and last_alert.created_at >= recent_scores[0].created_at:
                    continue
                # Nếu vẫn còn trong khoảng cooldown tính theo giờ -> bỏ qua
                time_diff = now_utc - (last_alert.created_at if last_alert.created_at.tzinfo else last_alert.created_at.replace(tzinfo=timezone.utc))
                if time_diff.total_seconds() < cooldown_hours * 3600:
                    continue

            # 5. Xác định tên bài toán theo đúng quy tắc US 8.1
            student_grade = student.grade or 5
            problems_summary: List[schemas.AcademicProblemSummary] = []

            for s in recent_scores:
                disp_title, c_title, f_title = resolve_problem_display_title(
                    db=db,
                    student_id=student.id,
                    score=s,
                    student_grade=student_grade
                )
                problems_summary.append(
                    schemas.AcademicProblemSummary(
                        problem_title=disp_title,
                        score=s.score,
                        hints_used=s.hints_used or 0,
                        not_understood_count=s.not_understood_count or 0,
                        created_at=s.created_at.strftime("%Y-%m-%d") if s.created_at else None
                    )
                )

            avg_score = round(sum(s.score for s in recent_scores) / len(recent_scores), 1)
            trigger_reason = (
                "Học sinh có điểm tự lập dưới 60 trong 3 bài liên tiếp"
                if has_3_consecutive_low
                else "Tỷ lệ Chưa hiểu tăng đột biến trong các bài gần đây"
            )

            student_name = links[0].student_nickname or student.email.split("@")[0]

            # 6. Gọi Gemini sinh email Cảnh Báo Học Tập
            req = schemas.AcademicAlertGenerateRequest(
                student_id=student.id,
                student_name=student_name,
                grade=student_grade,
                trigger_reason=trigger_reason,
                consecutive_low_scores_count=3 if has_3_consecutive_low else 0,
                recent_problems=problems_summary,
                average_recent_score=avg_score,
            )
            email_result = generate_academic_alert_email(request_data=req)

            # 7. Gửi email và lưu nhật ký
            html_body = render_academic_alert_html(email_result.model_dump())
            text_body = (
                f"SocraticKid – Thông báo đồng hành học tập cùng con\n\n"
                f"Học sinh: {student_name} (Lớp {student_grade})\n"
                f"Lý do: {trigger_reason}\n"
                f"Tóm tắt: {email_result.summary}\n"
                f"Khúc mắc tư duy: {email_result.learning_gap_analysis}\n"
                f"Điểm tích cực: {email_result.strengths_observed}\n"
                f"Lời khuyên cho phụ huynh: {', '.join(email_result.actionable_parent_advice)}\n"
            )

            for parent in parents:
                send_email(
                    to_email=parent.email,
                    subject=email_result.email_subject,
                    text_content=text_body,
                    html_content=html_body,
                    category="ACADEMIC_ALERT",
                )

                alert_log = models.ParentAlertLog(
                    student_id=student.id,
                    parent_id=parent.id,
                    alert_type="ACADEMIC",
                    recipient_email=parent.email,
                    subject=email_result.email_subject,
                    email_body=html_body,
                    trigger_reason=trigger_reason,
                )
                db.add(alert_log)

            db.commit()
            processed_count += 1
            print(f"[AlertWorker] 📚 Đã gửi email cảnh báo học tập cho phụ huynh học sinh {student_name}")

        except Exception as e:
            db.rollback()
            print(f"[AlertWorker] ❌ Lỗi khi xử lý academic alert cho học sinh {student.id}: {e}")

    return processed_count


def process_email_alerts_once(db: Session, cooldown_hours: int = 24) -> Dict[str, int]:
    """Chạy một chu kỳ quét và gửi email (cho phép gọi đồng bộ trong test hoặc scheduler)."""
    safety_count = process_safety_alerts(db)
    academic_count = process_academic_alerts(db, cooldown_hours=cooldown_hours)
    return {
        "safety_alerts": safety_count,
        "academic_alerts": academic_count,
    }


async def schedule_alert_email_worker(interval_seconds: int = 300):
    """
    Background worker chạy định kỳ (mặc định mỗi 300s = 5 phút)
    tự động gửi email cảnh báo kép cho phụ huynh.
    """
    print(f"[AlertWorker] 🚀 Khởi động Background Alert Email Worker (chu kỳ {interval_seconds} giây)...")
    while True:
        try:
            db = SessionLocal()
            try:
                counts = process_email_alerts_once(db)
                if counts["safety_alerts"] > 0 or counts["academic_alerts"] > 0:
                    print(f"[AlertWorker] 🔔 Chu kỳ 5 phút hoàn tất: Đã gửi {counts['safety_alerts']} cảnh báo ngôn từ & {counts['academic_alerts']} cảnh báo học tập.")
            finally:
                db.close()
        except Exception as e:
            print(f"[AlertWorker] ⚠️ Lỗi trong chu kỳ worker: {e}")

        await asyncio.sleep(interval_seconds)
