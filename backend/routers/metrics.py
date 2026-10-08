# Task #121: API thống kê thời gian học theo tuần/tháng
# Phục vụ Parent Dashboard (Monitor) và Student Dashboard

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, extract
from datetime import date, datetime, timedelta
from typing import Optional, List
import models
import dependencies
from database import get_db

router = APIRouter(tags=["Metrics"])


def _verify_access_to_student(current_user: dict, student_id: str, db: Session):
    """
    Kiểm tra quyền truy cập dữ liệu của một học sinh.
    - STUDENT chỉ xem được chính mình.
    - MONITOR chỉ xem được học sinh đã liên kết.
    """
    role = current_user["role"]
    uid = current_user["id"]

    if role == "STUDENT":
        if uid != student_id:
            raise HTTPException(status_code=403, detail="Bạn chỉ được xem dữ liệu của chính mình.")
        return

    if role == "MONITOR":
        link = (
            db.query(models.ParentStudentLink)
            .filter(
                models.ParentStudentLink.parent_id == uid,
                models.ParentStudentLink.student_id == student_id,
            )
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền xem dữ liệu của học sinh này.",
            )
        return

    raise HTTPException(status_code=403, detail="Role không được phép truy cập API này.")


@router.get("/metrics/study-time")
def get_study_time_metrics(
    student_id: str = Query(..., description="ID của học sinh cần xem"),
    mode: str = Query("weekly", description="'weekly' hoặc 'monthly'"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD), mặc định là đầu tuần/tháng hiện tại"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tổng hợp dữ liệu thời gian học của một học sinh theo tuần hoặc tháng.

    - **weekly**: Trả về số phút học của từng ngày trong tuần (7 ngày).
    - **monthly**: Trả về số phút học của từng tuần trong tháng (4-5 tuần).

    Dữ liệu được tính bằng `updated_at - created_at` của mỗi Session chat.
    Phụ huynh chỉ được xem học sinh đã liên kết. Học sinh chỉ xem chính mình.
    """
    # 1. Kiểm tra quyền
    _verify_access_to_student(current_user, student_id, db)

    today = date.today()

    if mode == "weekly":
        # Tính ngày đầu tuần (Thứ 2) của tuần được chọn
        if start_date:
            # Kéo về Thứ 2 của tuần chứa start_date
            week_start = start_date - timedelta(days=start_date.weekday())
        else:
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)  # Chủ Nhật

        # Query: tổng (EPOCH seconds) của mỗi ngày trong khoảng tuần
        rows = (
            db.query(
                cast(models.Session.created_at, Date).label("day"),
                func.sum(
                    func.extract("epoch", models.Session.updated_at)
                    - func.extract("epoch", models.Session.created_at)
                ).label("total_seconds"),
            )
            .filter(
                models.Session.user_id == student_id,
                cast(models.Session.created_at, Date) >= week_start,
                cast(models.Session.created_at, Date) <= week_end,
            )
            .group_by(cast(models.Session.created_at, Date))
            .all()
        )

        # Map kết quả ra dict {date_str: minutes}
        data_map = {str(r.day): max(0, round(r.total_seconds / 60)) for r in rows}

        # Sinh đủ 7 ngày, ngày nào không có thì = 0
        daily_data = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            daily_data.append({
                "date": str(d),
                "minutes": data_map.get(str(d), 0),
            })

        return {
            "mode": "weekly",
            "week_start": str(week_start),
            "week_end": str(week_end),
            "data": daily_data,
            "total_minutes": sum(item["minutes"] for item in daily_data),
        }

    elif mode == "monthly":
        # Tính ngày đầu tháng được chọn
        if start_date:
            month_start = start_date.replace(day=1)
        else:
            month_start = today.replace(day=1)

        # Tính ngày cuối tháng
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)

        # Query tổng giây học theo từng ngày trong tháng
        rows = (
            db.query(
                cast(models.Session.created_at, Date).label("day"),
                func.sum(
                    func.extract("epoch", models.Session.updated_at)
                    - func.extract("epoch", models.Session.created_at)
                ).label("total_seconds"),
            )
            .filter(
                models.Session.user_id == student_id,
                cast(models.Session.created_at, Date) >= month_start,
                cast(models.Session.created_at, Date) <= month_end,
            )
            .group_by(cast(models.Session.created_at, Date))
            .all()
        )

        data_map = {str(r.day): max(0, round(r.total_seconds / 60)) for r in rows}

        # Gom lại theo tuần trong tháng
        weekly_buckets: dict[int, dict] = {}
        current = month_start
        while current <= month_end:
            # Tuần thứ mấy trong tháng (1-indexed)
            week_num = ((current.day - 1) // 7) + 1
            if week_num not in weekly_buckets:
                w_start = current
                weekly_buckets[week_num] = {
                    "week": week_num,
                    "week_label": f"Tuần {week_num}",
                    "week_start": str(w_start),
                    "minutes": 0,
                }
            weekly_buckets[week_num]["minutes"] += data_map.get(str(current), 0)
            current += timedelta(days=1)

        monthly_data = list(weekly_buckets.values())

        return {
            "mode": "monthly",
            "month_start": str(month_start),
            "month_end": str(month_end),
            "data": monthly_data,
            "total_minutes": sum(item["minutes"] for item in monthly_data),
        }

    else:
        raise HTTPException(status_code=422, detail="mode phải là 'weekly' hoặc 'monthly'.")
