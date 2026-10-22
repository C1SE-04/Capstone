# Task #159 & #160 (US 6.1): Đo lường Điểm Tự Lực (Independence Score)
# - #159: Code API api/independence tiếp nhận điểm từ AI và lưu vào DB
# - #160: Sửa luồng bấm "Đã hiểu" trong API /chat: kích hoạt tính điểm và lưu kết quả

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, date, timezone
from typing import Optional, List
import models
import schemas
import dependencies
from database import get_db

router = APIRouter(tags=["Independence"])


def calculate_independence_score(hints_used: int, not_understood_count: int) -> dict:
    """
    Thuật toán barem tính điểm tự lực (Independence Score) - Thang điểm 10 đến 100:
    - 0 gợi ý: 100đ
    - 1 gợi ý: 90đ
    - 2 gợi ý: 80đ
    - Mỗi hint dùng thêm: -10đ
    - Mỗi lần bấm 'Chưa hiểu': -15đ
    - Điểm sàn: 10đ, điểm trần: 100đ
    """
    deduction = (hints_used * 10) + (not_understood_count * 15)
    raw_score = 100 - deduction
    score = max(10, min(100, raw_score))

    if score >= 80:
        level = "Tự lập xuất sắc (ít dùng gợi ý)"
    elif score >= 60:
        level = "Tự lập tốt (dùng 1-2 gợi ý)"
    elif score >= 40:
        level = "Đang tiến bộ (cần một số gợi ý)"
    else:
        level = "Cần thêm hỗ trợ sư phạm"

    return {
        "score": score,
        "hints_used": hints_used,
        "not_understood_count": not_understood_count,
        "level": level,
    }


def save_independence_score(
    db: Session,
    session_id: str,
    student_id: Optional[str] = None,
    custom_score: Optional[int] = None,
    custom_hints: Optional[int] = None,
    custom_not_understood: Optional[int] = None,
    custom_evaluation: Optional[str] = None,
) -> models.IndependenceScore:
    """
    Kích hoạt tính điểm và lưu bản ghi Independence vào DB (Task #159 & #160).
    Sau khi lưu điểm thành công, reset hint_count và consecutive_wrong_count để sẵn sàng cho bài toán mới.
    """
    # 1. Tìm session và user
    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    resolved_student_id = student_id
    if not resolved_student_id:
        if session_obj:
            resolved_student_id = session_obj.user_id
        else:
            resolved_student_id = "guest-user-id"

    # 2. Lấy bộ đếm hiện tại của session
    stats = (
        db.query(models.SessionStats)
        .filter(models.SessionStats.session_id == session_id)
        .first()
    )

    hints_used = custom_hints if custom_hints is not None else (stats.hint_count if stats else 0)
    not_understood = (
        custom_not_understood
        if custom_not_understood is not None
        else (stats.not_understood_count if stats else 0)
    )

    # 3. Tính điểm theo barem nếu chưa có điểm tuỳ chỉnh
    if custom_score is not None:
        score = max(0, min(100, custom_score))
        evaluation = (
            custom_evaluation
            or calculate_independence_score(hints_used, not_understood)["level"]
        )
    else:
        calc_result = calculate_independence_score(hints_used, not_understood)
        score = calc_result["score"]
        evaluation = custom_evaluation or calc_result["level"]

    # 4. Lưu bản ghi vào bảng independence_scores
    record = models.IndependenceScore(
        session_id=session_id,
        student_id=resolved_student_id,
        score=score,
        hints_used=hints_used,
        not_understood_count=not_understood,
        evaluation=evaluation,
    )
    db.add(record)

    # 5. Reset bộ đếm gợi ý của bài toán hiện tại trong session_stats
    if stats:
        stats.consecutive_wrong_count = 0
        stats.hint_count = 0

    db.commit()
    db.refresh(record)
    return record


@router.post("/independence", status_code=status.HTTP_201_CREATED)
def record_independence_score(
    body: schemas.IndependenceRecordCreate,
    current_user: Optional[dict] = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Task #159: Tiếp nhận điểm số Independence từ AI hoặc Client và lưu vào DB.
    """
    student_id = body.student_id or (current_user["id"] if current_user else None)

    record = save_independence_score(
        db=db,
        session_id=body.session_id,
        student_id=student_id,
        custom_score=body.score,
        custom_hints=body.hints_used,
        custom_not_understood=body.not_understood_count,
        custom_evaluation=body.evaluation,
    )

    return {
        "success": True,
        "message": "Đã ghi nhận điểm Independence vào tiến trình học tập.",
        "data": {
            "id": record.id,
            "session_id": record.session_id,
            "student_id": record.student_id,
            "score": record.score,
            "hints_used": record.hints_used,
            "not_understood_count": record.not_understood_count,
            "evaluation": record.evaluation,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        },
    }


@router.get("/independence", response_model=List[schemas.IndependenceRecordResponse])
def get_independence_history(
    student_id: Optional[str] = Query(None, description="ID học sinh cần xem"),
    limit: int = Query(30, ge=1, le=100),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Truy xuất lịch sử điểm số Independence theo từng bài toán / phiên học.
    """
    target_id = student_id or current_user["id"]

    records = (
        db.query(models.IndependenceScore)
        .filter(models.IndependenceScore.student_id == target_id)
        .order_by(models.IndependenceScore.created_at.desc())
        .limit(limit)
        .all()
    )
    return records


@router.get("/independence/summary", response_model=schemas.IndependenceSummaryResponse)
def get_independence_summary(
    student_id: Optional[str] = Query(None, description="ID học sinh"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Ngày kết thúc (YYYY-MM-DD)"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tổng hợp điểm tự lực trung bình và lịch sử phục vụ Dashboard Phụ huynh (Summary Cards & Line Chart).
    Hỗ trợ lọc theo khoảng thời gian tuần (start_date, end_date).
    """
    target_id = student_id or current_user["id"]

    query = db.query(models.IndependenceScore).filter(
        models.IndependenceScore.student_id == target_id
    )
    if start_date:
        query = query.filter(cast(models.IndependenceScore.created_at, Date) >= start_date)
    if end_date:
        query = query.filter(cast(models.IndependenceScore.created_at, Date) <= end_date)

    # 1. Tính điểm trung bình và tổng số bài hoàn thành
    stats_query = (
        db.query(
            func.count(models.IndependenceScore.id).label("total_completed"),
            func.avg(models.IndependenceScore.score).label("avg_score"),
        )
        .filter(models.IndependenceScore.student_id == target_id)
    )
    if start_date:
        stats_query = stats_query.filter(cast(models.IndependenceScore.created_at, Date) >= start_date)
    if end_date:
        stats_query = stats_query.filter(cast(models.IndependenceScore.created_at, Date) <= end_date)

    stats_row = stats_query.one()

    total_completed = stats_row.total_completed or 0
    avg_score = round(float(stats_row.avg_score), 1) if stats_row.avg_score is not None else 0.0

    # 2. Lấy bài gần nhất
    latest_record = (
        query
        .order_by(models.IndependenceScore.created_at.desc())
        .first()
    )
    latest_score = latest_record.score if latest_record else None

    # 3. Phân loại mức độ theo thang điểm tự lực
    if avg_score >= 80:
        level = "Tự lập xuất sắc"
    elif avg_score >= 60:
        level = "Tự lập tốt"
    elif avg_score >= 40:
        level = "Tự lập đang tiến bộ"
    elif total_completed > 0:
        level = "Cần tiến bộ"
    else:
        level = "Chưa có dữ liệu"

    # 4. Lấy danh sách bản ghi cho Line Chart (tối đa 100 bản ghi)
    history = (
        query
        .order_by(models.IndependenceScore.created_at.asc())
        .limit(100)
        .all()
    )

    return schemas.IndependenceSummaryResponse(
        student_id=target_id,
        average_score=avg_score,
        total_completed=total_completed,
        latest_score=latest_score,
        evaluation_level=level,
        history=history,
    )
