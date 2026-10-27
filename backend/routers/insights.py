# routers/insights.py
# US 7.3 (Task T7.8): Background service quét dữ liệu tuần, gọi Gemini sinh AI Insights, lưu vào parent_ai_insights
# US 7.4 (Task T7.9): Logic tính Streak + API kiểm tra và trao Huy Hiệu (Badge)

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date

import models
import schemas
import dependencies
from database import get_db
from agents.parent_insights_prompt import generate_parent_learning_insights
from routers.metrics import calculate_student_streak, _verify_access_to_student

router = APIRouter(tags=["Insights & Badges"])


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _get_student_weekly_data(student_id: str, days: int, db: Session) -> dict:
    """
    Quét dữ liệu học tập của học sinh trong `days` ngày gần nhất.
    Trả về dict gồm: total_problems, avg_independence_score, total_hints_used,
    total_not_understood_count, topic_breakdown (phân tích theo tiêu đề session).
    """
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # ── 1. Tổng số bài hoàn thành (independence_scores) ───────────────────
    score_rows = (
        db.query(models.IndependenceScore, models.Session)
        .join(models.Session, models.IndependenceScore.session_id == models.Session.id)
        .filter(
            models.IndependenceScore.student_id == student_id,
            cast(models.IndependenceScore.created_at, Date) >= start_date,
            cast(models.IndependenceScore.created_at, Date) <= today,
        )
        .all()
    )

    if not score_rows:
        return {
            "total_problems": 0,
            "avg_independence_score": 0.0,
            "total_hints_used": 0,
            "total_not_understood_count": 0,
            "topic_breakdown": [],
        }

    total_hints = sum(s.hints_used for s, _ in score_rows)
    total_not_understood = sum(s.not_understood_count for s, _ in score_rows)
    avg_score = sum(s.score for s, _ in score_rows) / len(score_rows)

    # ── 2. Phân tích theo nhóm (topic = tiêu đề session) ──────────────────
    topic_map: dict[str, dict] = {}
    for score, session in score_rows:
        topic = session.title or "Toán tổng hợp"
        if topic not in topic_map:
            topic_map[topic] = {
                "topic_name": topic,
                "problems_solved": 0,
                "total_score": 0,
                "hints_used": 0,
                "not_understood": 0,
            }
        topic_map[topic]["problems_solved"] += 1
        topic_map[topic]["total_score"] += score.score
        topic_map[topic]["hints_used"] += score.hints_used
        topic_map[topic]["not_understood"] += score.not_understood_count

    topic_breakdown = []
    for t in topic_map.values():
        avg_ind = t["total_score"] / t["problems_solved"] if t["problems_solved"] > 0 else 0
        topic_breakdown.append({
            "topic_name": t["topic_name"],
            "problems_solved": t["problems_solved"],
            "avg_independence": round(avg_ind, 1),
            "hints_used": t["hints_used"],
            "not_understood": t["not_understood"],
        })

    return {
        "total_problems": len(score_rows),
        "avg_independence_score": round(avg_score, 1),
        "total_hints_used": total_hints,
        "total_not_understood_count": total_not_understood,
        "topic_breakdown": topic_breakdown,
    }


def _generate_and_save_insight(student_id: str, student_name: str, grade_level: int, db: Session) -> schemas.WeeklyInsightServiceResult:
    """
    Hàm core của background service:
    1. Quét dữ liệu 7 ngày gần nhất của học sinh.
    2. Skip nếu không có bài nào.
    3. Gọi Gemini sinh báo cáo AI.
    4. Lưu kết quả vào bảng parent_ai_insights.
    """
    SCAN_DAYS = 7
    today_dt = datetime.now(timezone.utc)
    period_start = today_dt - timedelta(days=SCAN_DAYS - 1)

    # ── Bước 1: Thu thập dữ liệu tuần ─────────────────────────────────────
    weekly_data = _get_student_weekly_data(student_id, SCAN_DAYS, db)

    # ── Bước 2: Skip nếu không có bài nào trong tuần ──────────────────────
    if weekly_data["total_problems"] == 0:
        return schemas.WeeklyInsightServiceResult(
            student_id=student_id,
            student_name=student_name,
            status="skipped",
            reason="Học sinh chưa hoàn thành bài nào trong 7 ngày qua.",
        )

    period_desc = f"{period_start.strftime('%d/%m')} – {today_dt.strftime('%d/%m/%Y')}"

    # ── Bước 3: Gọi Gemini sinh báo cáo ───────────────────────────────────
    try:
        report_dict = generate_parent_learning_insights(
            student_name=student_name,
            grade_level=grade_level,
            period_description=period_desc,
            total_problems_completed=weekly_data["total_problems"],
            average_independence_score=weekly_data["avg_independence_score"],
            total_hints_used=weekly_data["total_hints_used"],
            total_not_understood_count=weekly_data["total_not_understood_count"],
            topic_breakdown=weekly_data["topic_breakdown"],
        )
        is_fallback = report_dict.get("is_fallback", False)
    except Exception as e:
        return schemas.WeeklyInsightServiceResult(
            student_id=student_id,
            student_name=student_name,
            status="error",
            reason=f"Lỗi khi gọi Gemini: {str(e)}",
        )

    # ── Bước 4: Lưu vào bảng parent_ai_insights ───────────────────────────
    insight_record = models.ParentAiInsight(
        id=uuid.uuid4().hex,
        student_id=student_id,
        period_start=period_start,
        period_end=today_dt,
        report_json=json.dumps(report_dict, ensure_ascii=False),
        avg_independence_score=round(weekly_data["avg_independence_score"]),
        total_problems=weekly_data["total_problems"],
        is_fallback=is_fallback,
    )
    db.add(insight_record)
    db.commit()
    db.refresh(insight_record)

    return schemas.WeeklyInsightServiceResult(
        student_id=student_id,
        student_name=student_name,
        status="success",
        is_fallback=is_fallback,
        insight_id=insight_record.id,
    )


# ==============================================================================
# US 7.3: BACKGROUND SERVICE ENDPOINTS
# ==============================================================================

@router.post("/insights/generate", response_model=schemas.WeeklyInsightBatchResponse)
def trigger_weekly_insights_batch(
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.3 (Task T7.8):
    Background service quét toàn bộ học sinh trong hệ thống, sinh AI Insights cho từng em.

    - Chỉ Admin / MONITOR mới được gọi API này để kích hoạt batch.
    - Với mỗi học sinh: quét dữ liệu 7 ngày, gọi Gemini, lưu vào parent_ai_insights.
    - Skip học sinh nào không có bài hoàn thành trong tuần.

    Thường được gọi tự động mỗi tuần 1 lần (cron job / scheduler).
    """
    role = current_user.get("role")
    if role not in ("MONITOR", "ADMIN"):
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh hoặc Admin mới có thể kích hoạt dịch vụ này.")

    # Lấy tất cả học sinh có ít nhất 1 bài hoàn thành
    student_rows = (
        db.query(models.User)
        .filter(models.User.role == "STUDENT")
        .all()
    )

    results: list[schemas.WeeklyInsightServiceResult] = []
    success_count = skipped_count = error_count = 0

    for student in student_rows:
        student_name = student.email.split("@")[0]  # Dùng tên email nếu không có tên thật
        grade_level = student.grade or 5  # Mặc định lớp 5 nếu chưa điền

        result = _generate_and_save_insight(
            student_id=student.id,
            student_name=student_name,
            grade_level=grade_level,
            db=db,
        )
        results.append(result)

        if result.status == "success":
            success_count += 1
        elif result.status == "skipped":
            skipped_count += 1
        else:
            error_count += 1

    return schemas.WeeklyInsightBatchResponse(
        total_students=len(student_rows),
        success_count=success_count,
        skipped_count=skipped_count,
        error_count=error_count,
        results=results,
    )


@router.post("/insights/generate/{student_id}", response_model=schemas.WeeklyInsightServiceResult)
def trigger_insight_for_student(
    student_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.3 (Task T7.8):
    Kích hoạt sinh AI Insights cho MỘT học sinh cụ thể.
    Phụ huynh chỉ được gọi cho học sinh đã liên kết với mình.
    """
    # Kiểm tra quyền
    role = current_user.get("role")
    if role == "MONITOR":
        link = (
            db.query(models.ParentStudentLink)
            .filter(
                models.ParentStudentLink.parent_id == current_user["id"],
                models.ParentStudentLink.student_id == student_id,
            )
            .first()
        )
        if not link:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem dữ liệu của học sinh này.")
    elif role != "ADMIN":
        raise HTTPException(status_code=403, detail="Không có quyền truy cập.")

    # Lấy thông tin học sinh
    student = db.query(models.User).filter(models.User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy học sinh.")

    student_name = student.email.split("@")[0]
    grade_level = student.grade or 5

    return _generate_and_save_insight(
        student_id=student_id,
        student_name=student_name,
        grade_level=grade_level,
        db=db,
    )


@router.get("/insights/{student_id}", response_model=schemas.ParentAiInsightResponse)
def get_latest_insight(
    student_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.3 (Task T7.8):
    Lấy báo cáo AI Insights mới nhất của một học sinh từ bảng parent_ai_insights.
    Phụ huynh xem báo cáo trên Dashboard — không cần gọi Gemini lại.
    """
    _verify_access_to_student(current_user, student_id, db)

    # Lấy record mới nhất
    record = (
        db.query(models.ParentAiInsight)
        .filter(models.ParentAiInsight.student_id == student_id)
        .order_by(models.ParentAiInsight.created_at.desc())
        .first()
    )

    if not record:
        # Nếu chưa có insight nào, sinh ngay từ dữ liệu hiện tại
        student = db.query(models.User).filter(models.User.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Không tìm thấy học sinh.")

        student_name = student.email.split("@")[0]
        grade_level = student.grade or 5
        result = _generate_and_save_insight(student_id, student_name, grade_level, db)

        if result.status == "skipped":
            # Trả về báo cáo rỗng / mặc định
            from agents.parent_insights_prompt import _fallback_insights
            fallback = _fallback_insights(student_name=student_name, total_problems=0, score=0.0)
            return schemas.ParentAiInsightResponse(
                student_id=student_id,
                student_name=student_name,
                period_description="Chưa có dữ liệu học tập",
                insight=schemas.AiInsightReportResponse(**fallback),
                created_at=datetime.now(timezone.utc),
            )

        # Đọc lại record vừa lưu
        record = (
            db.query(models.ParentAiInsight)
            .filter(models.ParentAiInsight.student_id == student_id)
            .order_by(models.ParentAiInsight.created_at.desc())
            .first()
        )

    # Parse JSON báo cáo
    report_data = json.loads(record.report_json)
    period_start_str = record.period_start.strftime("%d/%m")
    period_end_str = record.period_end.strftime("%d/%m/%Y")
    period_desc = f"{period_start_str} – {period_end_str}"

    student = db.query(models.User).filter(models.User.id == student_id).first()
    student_name = student.email.split("@")[0] if student else student_id

    return schemas.ParentAiInsightResponse(
        student_id=student_id,
        student_name=student_name,
        period_description=period_desc,
        insight=schemas.AiInsightReportResponse(**report_data),
        created_at=record.created_at,
    )


# ==============================================================================
# US 7.4: BADGE SYSTEM ENDPOINTS
# ==============================================================================

def _unlock_badges_for_student(student_id: str, db: Session) -> list[models.StudentBadge]:
    """
    Hàm lõi kiểm tra và trao huy hiệu mới cho học sinh.
    1. Tính các chỉ số hiện tại: streak, total_problems, avg_independence.
    2. So sánh với ngưỡng trong BADGE_CATALOG.
    3. Trao những huy hiệu chưa nhận (INSERT IGNORE via try/except).
    Trả về danh sách huy hiệu VỪA mở khóa.
    """
    # ── Lấy các chỉ số hiện tại ─────────────────────────────────────────
    current_streak, _ = calculate_student_streak(student_id, db)

    total_problems = (
        db.query(func.count(models.IndependenceScore.id))
        .filter(models.IndependenceScore.student_id == student_id)
        .scalar()
    ) or 0

    avg_score_raw = (
        db.query(func.avg(models.IndependenceScore.score))
        .filter(models.IndependenceScore.student_id == student_id)
        .scalar()
    )
    avg_independence = round(float(avg_score_raw)) if avg_score_raw is not None else 0

    # ── Lấy danh sách badge đã có ────────────────────────────────────────
    existing_keys = {
        row.badge_key
        for row in db.query(models.StudentBadge.badge_key)
        .filter(models.StudentBadge.student_id == student_id)
        .all()
    }

    newly_unlocked: list[models.StudentBadge] = []

    for badge_key, info in models.BADGE_CATALOG.items():
        # Bỏ qua nếu đã có
        if badge_key in existing_keys:
            continue

        threshold = info["threshold"]
        category = info["category"]

        # Kiểm tra điều kiện mở khóa theo từng loại huy hiệu
        if category == "streak" and current_streak >= threshold:
            eligible = True
        elif category == "problems" and total_problems >= threshold:
            eligible = True
        elif category == "independence" and avg_independence >= threshold:
            eligible = True
        else:
            eligible = False

        if not eligible:
            continue

        # Trao huy hiệu
        new_badge = models.StudentBadge(
            id=uuid.uuid4().hex,
            student_id=student_id,
            badge_key=badge_key,
            badge_name=info["name"],
            badge_description=info["description"],
            category=category,
        )
        db.add(new_badge)
        try:
            db.flush()   # Ghi vào transaction, phát hiện lỗi unique sớm
            newly_unlocked.append(new_badge)
        except Exception:
            db.rollback()

    db.commit()
    return newly_unlocked


@router.post("/badges/check", response_model=schemas.BadgeCheckResponse)
def check_and_award_badges(
    student_id: Optional[str] = Query(None, description="ID học sinh. STUDENT tự check bỏ trống, MONITOR truyền ID con."),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.4 (Task T7.9):
    Kiểm tra và trao huy hiệu mới khi học sinh đạt ngưỡng.
    - STUDENT: gọi không cần truyền student_id (tự check chính mình).
    - MONITOR: truyền student_id của con để check.

    Trả về:
    - newly_unlocked: Danh sách huy hiệu VỪA được mở trong lần gọi này.
    - all_badges: Toàn bộ huy hiệu học sinh đang có.
    - Các chỉ số hiện tại: streak, total_problems, avg_independence_score.
    """
    role = current_user.get("role")
    uid = current_user["id"]

    # Xác định target_student_id
    if role == "STUDENT":
        target_student_id = uid
    elif role == "MONITOR":
        if not student_id:
            raise HTTPException(status_code=422, detail="MONITOR phải truyền student_id.")
        link = (
            db.query(models.ParentStudentLink)
            .filter(
                models.ParentStudentLink.parent_id == uid,
                models.ParentStudentLink.student_id == student_id,
            )
            .first()
        )
        if not link:
            raise HTTPException(status_code=403, detail="Bạn không có quyền xem dữ liệu của học sinh này.")
        target_student_id = student_id
    else:
        raise HTTPException(status_code=403, detail="Role không được phép.")

    # Kiểm tra và trao huy hiệu mới
    newly_unlocked_models = _unlock_badges_for_student(target_student_id, db)

    # Lấy toàn bộ huy hiệu hiện có
    all_badges_models = (
        db.query(models.StudentBadge)
        .filter(models.StudentBadge.student_id == target_student_id)
        .order_by(models.StudentBadge.unlocked_at.asc())
        .all()
    )

    # Lấy lại thống kê để trả về
    current_streak, max_streak = calculate_student_streak(target_student_id, db)

    total_problems = (
        db.query(func.count(models.IndependenceScore.id))
        .filter(models.IndependenceScore.student_id == target_student_id)
        .scalar()
    ) or 0

    avg_score_raw = (
        db.query(func.avg(models.IndependenceScore.score))
        .filter(models.IndependenceScore.student_id == target_student_id)
        .scalar()
    )
    avg_independence = round(float(avg_score_raw)) if avg_score_raw is not None else 0

    return schemas.BadgeCheckResponse(
        student_id=target_student_id,
        newly_unlocked=[schemas.BadgeResponse.model_validate(b) for b in newly_unlocked_models],
        all_badges=[schemas.BadgeResponse.model_validate(b) for b in all_badges_models],
        current_streak=current_streak,
        max_streak=max_streak,
        total_problems=total_problems,
        avg_independence_score=avg_independence,
    )


@router.get("/badges/{student_id}", response_model=schemas.BadgeCheckResponse)
def get_student_badges(
    student_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.4 (Task T7.9):
    Lấy toàn bộ huy hiệu một học sinh đang sở hữu (không trao thêm).
    """
    _verify_access_to_student(current_user, student_id, db)

    all_badges_models = (
        db.query(models.StudentBadge)
        .filter(models.StudentBadge.student_id == student_id)
        .order_by(models.StudentBadge.unlocked_at.asc())
        .all()
    )

    current_streak, max_streak = calculate_student_streak(student_id, db)

    total_problems = (
        db.query(func.count(models.IndependenceScore.id))
        .filter(models.IndependenceScore.student_id == student_id)
        .scalar()
    ) or 0

    avg_score_raw = (
        db.query(func.avg(models.IndependenceScore.score))
        .filter(models.IndependenceScore.student_id == student_id)
        .scalar()
    )
    avg_independence = round(float(avg_score_raw)) if avg_score_raw is not None else 0

    return schemas.BadgeCheckResponse(
        student_id=student_id,
        newly_unlocked=[],
        all_badges=[schemas.BadgeResponse.model_validate(b) for b in all_badges_models],
        current_streak=current_streak,
        max_streak=max_streak,
        total_problems=total_problems,
        avg_independence_score=avg_independence,
    )

# ==============================================================================
# US 8.1 - Task T8.6: Preview API cho 2 Loại Email Alert (Học Tập & Ngôn Từ)
# ==============================================================================
from agents.email_alert_generator import (
    generate_academic_alert_email,
    generate_safety_alert_email,
)

@router.post("/parent/alerts/preview-academic", response_model=schemas.AcademicAlertEmailResult)
def preview_academic_alert_email(
    payload: schemas.AcademicAlertGenerateRequest,
    current_user: dict = Depends(dependencies.get_current_user)
):
    """
    API xem trước nội dung Email Cảnh Báo Học Tập Yếu do AI sinh ra (Task T8.6).
    Cho phép Phụ huynh hoặc Admin xem thử nội dung email trước khi hệ thống gửi thật.
    """
    result = generate_academic_alert_email(request_data=payload)
    return result


@router.post("/parent/alerts/preview-safety", response_model=schemas.SafetyAlertEmailResult)
def preview_safety_alert_email(
    payload: schemas.SafetyAlertGenerateRequest,
    current_user: dict = Depends(dependencies.get_current_user)
):
    """
    API xem trước nội dung Email Cảnh Báo Ngôn Từ do AI sinh ra (Task T8.6).
    Đảm bảo trích đoạn vi phạm được kiểm duyệt che mờ và có lời khuyên tâm lý chuẩn mực.
    """
    result = generate_safety_alert_email(request_data=payload)
    return result