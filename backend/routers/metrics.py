# Task #121, #168, #169: API thống kê thời gian học theo tuần/tháng và Quản lý Active Interval
# US 6.3: Thông Báo Idle & Dừng Tính Giờ Học
# - #168: Sửa API api/metrics: Chỉ cộng các khoảng active_seconds thực sự (exclude thời gian idle)
# - #169: Nhận timestamp restart từ FE khi học sinh bấm "Đang học" → ghi nhận khoảng active mới vào DB

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, extract
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
import models
import schemas
import dependencies
from database import get_db

router = APIRouter(tags=["Metrics"])

IDLE_THRESHOLD_SECONDS = 600  # 10 phút (US 6.3: sau 10 phút không tương tác là tính idle)


def update_session_active_interval(
    db: Session,
    session_id: str,
    timestamp: Optional[datetime] = None,
) -> Optional[models.SessionActiveInterval]:
    """
    Cập nhật hoặc ghi nhận khoảng thời gian active cho một session chat (Task #168 & #169).
    - Nếu chưa có khoảng active nào: Tạo khoảng mới với start_time = end_time = timestamp.
    - Nếu khoảng gần nhất cách timestamp <= IDLE_THRESHOLD_SECONDS (10 phút):
        Kéo dài end_time và cập nhật active_seconds.
    - Nếu khoảng gần nhất cách timestamp > IDLE_THRESHOLD_SECONDS (học sinh đã idle quá 10 phút):
        Chốt khoảng cũ, mở một khoảng active mới từ timestamp này.
    """
    if not session_id:
        return None

    now_utc = timestamp or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    if not session_obj:
        return None

    user_id = session_obj.user_id

    # Lấy interval gần nhất của session này
    latest_interval = (
        db.query(models.SessionActiveInterval)
        .filter(models.SessionActiveInterval.session_id == session_id)
        .order_by(models.SessionActiveInterval.end_time.desc())
        .first()
    )

    if not latest_interval:
        new_interval = models.SessionActiveInterval(
            session_id=session_id,
            user_id=user_id,
            start_time=now_utc,
            end_time=now_utc,
            active_seconds=0,
        )
        db.add(new_interval)
        db.commit()
        db.refresh(new_interval)
        return new_interval

    last_end = latest_interval.end_time
    if last_end.tzinfo is None:
        last_end = last_end.replace(tzinfo=timezone.utc)

    gap_seconds = (now_utc - last_end).total_seconds()

    if gap_seconds <= IDLE_THRESHOLD_SECONDS:
        # Vẫn trong phiên active (< 10 phút idle) -> cập nhật end_time và active_seconds
        latest_interval.end_time = now_utc
        start_t = latest_interval.start_time
        if start_t.tzinfo is None:
            start_t = start_t.replace(tzinfo=timezone.utc)
        duration = max(0, int((now_utc - start_t).total_seconds()))
        latest_interval.active_seconds = duration
        db.commit()
        db.refresh(latest_interval)
        return latest_interval
    else:
        # Học sinh đã idle > 10 phút mà không có restart trước đó.
        # Khoảng cũ đã kết thúc ở last_end. Tạo khoảng active mới từ now_utc
        new_interval = models.SessionActiveInterval(
            session_id=session_id,
            user_id=user_id,
            start_time=now_utc,
            end_time=now_utc,
            active_seconds=0,
        )
        db.add(new_interval)
        db.commit()
        db.refresh(new_interval)
        return new_interval


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


@router.post("/metrics/restart", response_model=schemas.RestartMetricResponse)
def restart_study_session(
    body: schemas.RestartMetricRequest,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Task #169 (US 6.3): Nhận timestamp restart từ FE khi học sinh bấm 'Đang học'
    -> Ghi nhận khoảng active mới vào DB.
    """
    user_id = current_user["id"]

    # 1. Xác định mốc thời gian restart
    if body.restart_time:
        try:
            dt_str = body.restart_time.replace("Z", "+00:00")
            restart_dt = datetime.fromisoformat(dt_str)
        except Exception:
            restart_dt = datetime.now(timezone.utc)
    elif body.timestamp:
        try:
            restart_dt = datetime.fromtimestamp(body.timestamp, tz=timezone.utc)
        except Exception:
            restart_dt = datetime.now(timezone.utc)
    elif body.timestamp_ms:
        try:
            restart_dt = datetime.fromtimestamp(body.timestamp_ms / 1000.0, tz=timezone.utc)
        except Exception:
            restart_dt = datetime.now(timezone.utc)
    else:
        restart_dt = datetime.now(timezone.utc)

    if restart_dt.tzinfo is None:
        restart_dt = restart_dt.replace(tzinfo=timezone.utc)

    # 2. Tìm hoặc liên kết session phù hợp
    target_session = None
    if body.session_id:
        target_session = (
            db.query(models.Session)
            .filter(models.Session.id == body.session_id)
            .first()
        )

    if not target_session:
        target_session = (
            db.query(models.Session)
            .filter(models.Session.user_id == user_id)
            .order_by(models.Session.updated_at.desc())
            .first()
        )

    if not target_session:
        target_session = models.Session(
            user_id=user_id,
            title="Phiên học tự động"
        )
        db.add(target_session)
        db.commit()
        db.refresh(target_session)

    # 3. Ghi nhận khoảng active mới vào DB (Task #169)
    new_interval = models.SessionActiveInterval(
        session_id=target_session.id,
        user_id=user_id,
        start_time=restart_dt,
        end_time=restart_dt,
        active_seconds=0,
    )
    db.add(new_interval)
    target_session.updated_at = restart_dt
    db.commit()
    db.refresh(new_interval)

    return schemas.RestartMetricResponse(
        success=True,
        message="Đã ghi nhận khoảng active mới vào DB thành công.",
        session_id=target_session.id,
        interval_id=new_interval.id,
        start_time=new_interval.start_time.isoformat(),
        active_seconds=new_interval.active_seconds,
    )


@router.get("/metrics/study-time")
def get_study_time_metrics(
    student_id: str = Query(..., description="ID của học sinh cần xem"),
    mode: str = Query("weekly", description="'weekly' hoặc 'monthly'"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD), mặc định là đầu tuần/tháng hiện tại"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Task #168: Sửa API api/metrics:
    Thay vì tính end_time - start_time toàn session, chỉ cộng các khoảng active_seconds
    thực sự từ bảng session_active_intervals (exclude thời gian idle).

    - **weekly**: Trả về số phút học của từng ngày trong tuần (7 ngày).
    - **monthly**: Trả về số phút học của từng tuần trong tháng (4-5 tuần).
    """
    # 1. Kiểm tra quyền
    _verify_access_to_student(current_user, student_id, db)

    today = date.today()

    if mode == "weekly":
        # Tính ngày đầu tuần (Thứ 2) của tuần được chọn
        if start_date:
            week_start = start_date - timedelta(days=start_date.weekday())
        else:
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)  # Chủ Nhật

        # 1. Query tổng active_seconds từ session_active_intervals (Task #168)
        interval_rows = (
            db.query(
                cast(models.SessionActiveInterval.start_time, Date).label("day"),
                func.coalesce(func.sum(models.SessionActiveInterval.active_seconds), 0).label("total_seconds"),
            )
            .filter(
                models.SessionActiveInterval.user_id == student_id,
                cast(models.SessionActiveInterval.start_time, Date) >= week_start,
                cast(models.SessionActiveInterval.start_time, Date) <= week_end,
            )
            .group_by(cast(models.SessionActiveInterval.start_time, Date))
            .all()
        )

        # 2. Hỗ trợ phiên cũ chưa có khoảng active (fallback legacy)
        recorded_session_subquery = (
            db.query(models.SessionActiveInterval.session_id)
            .filter(models.SessionActiveInterval.user_id == student_id)
            .distinct()
        )

        legacy_rows = (
            db.query(
                cast(models.Session.created_at, Date).label("day"),
                func.coalesce(
                    func.sum(
                        func.extract("epoch", models.Session.updated_at)
                        - func.extract("epoch", models.Session.created_at)
                    ),
                    0,
                ).label("total_seconds"),
            )
            .filter(
                models.Session.user_id == student_id,
                cast(models.Session.created_at, Date) >= week_start,
                cast(models.Session.created_at, Date) <= week_end,
                ~models.Session.id.in_(recorded_session_subquery),
            )
            .group_by(cast(models.Session.created_at, Date))
            .all()
        )

        data_map: dict[str, int] = {}
        for r in interval_rows:
            d_str = str(r.day)
            secs = float(r.total_seconds or 0)
            data_map[d_str] = data_map.get(d_str, 0) + max(0, round(secs / 60))

        for r in legacy_rows:
            d_str = str(r.day)
            secs = float(r.total_seconds or 0)
            data_map[d_str] = data_map.get(d_str, 0) + max(0, round(secs / 60))

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
        if start_date:
            month_start = start_date.replace(day=1)
        else:
            month_start = today.replace(day=1)

        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1, day=1) - timedelta(days=1)

        # 1. Query tổng active_seconds từ session_active_intervals (Task #168)
        interval_rows = (
            db.query(
                cast(models.SessionActiveInterval.start_time, Date).label("day"),
                func.coalesce(func.sum(models.SessionActiveInterval.active_seconds), 0).label("total_seconds"),
            )
            .filter(
                models.SessionActiveInterval.user_id == student_id,
                cast(models.SessionActiveInterval.start_time, Date) >= month_start,
                cast(models.SessionActiveInterval.start_time, Date) <= month_end,
            )
            .group_by(cast(models.SessionActiveInterval.start_time, Date))
            .all()
        )

        recorded_session_subquery = (
            db.query(models.SessionActiveInterval.session_id)
            .filter(models.SessionActiveInterval.user_id == student_id)
            .distinct()
        )

        legacy_rows = (
            db.query(
                cast(models.Session.created_at, Date).label("day"),
                func.coalesce(
                    func.sum(
                        func.extract("epoch", models.Session.updated_at)
                        - func.extract("epoch", models.Session.created_at)
                    ),
                    0,
                ).label("total_seconds"),
            )
            .filter(
                models.Session.user_id == student_id,
                cast(models.Session.created_at, Date) >= month_start,
                cast(models.Session.created_at, Date) <= month_end,
                ~models.Session.id.in_(recorded_session_subquery),
            )
            .group_by(cast(models.Session.created_at, Date))
            .all()
        )

        data_map: dict[str, int] = {}
        for r in interval_rows:
            d_str = str(r.day)
            secs = float(r.total_seconds or 0)
            data_map[d_str] = data_map.get(d_str, 0) + max(0, round(secs / 60))

        for r in legacy_rows:
            d_str = str(r.day)
            secs = float(r.total_seconds or 0)
            data_map[d_str] = data_map.get(d_str, 0) + max(0, round(secs / 60))

        # Gom lại theo tuần trong tháng
        weekly_buckets: dict[int, dict] = {}
        current = month_start
        while current <= month_end:
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


@router.get("/metrics")
def get_metrics_alias(
    student_id: str = Query(..., description="ID của học sinh cần xem"),
    mode: str = Query("weekly", description="'weekly' hoặc 'monthly'"),
    start_date: Optional[date] = Query(None, description="Ngày bắt đầu (YYYY-MM-DD)"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """Alias cho /metrics/study-time để tương thích với mọi router path."""
    return get_study_time_metrics(
        student_id=student_id,
        mode=mode,
        start_date=start_date,
        current_user=current_user,
        db=db,
    )


# ==============================================================================
# US 7.1 (Task T7.4 & T7.5): NÂNG CẤP TOÀN DIỆN DASHBOARD PHỤ HUYNH
# ==============================================================================

def calculate_student_streak(student_id: str, db: Session) -> tuple[int, int]:
    """
    Tính chuỗi ngày học liên tục (current_streak, max_streak).
    Một ngày được ghi nhận có hoạt động học nếu:
    - Có ít nhất 1 khoảng active trong session_active_intervals
    - HOẶC có bản ghi bài toán hoàn thành trong independence_scores
    - HOẶC có session học tạo trong ngày
    """
    # 1. Các ngày từ session_active_intervals
    interval_dates = (
        db.query(cast(models.SessionActiveInterval.start_time, Date).label("d"))
        .filter(models.SessionActiveInterval.user_id == student_id)
        .distinct()
        .all()
    )

    # 2. Các ngày từ independence_scores
    score_dates = (
        db.query(cast(models.IndependenceScore.created_at, Date).label("d"))
        .filter(models.IndependenceScore.student_id == student_id)
        .distinct()
        .all()
    )

    # 3. Các ngày từ sessions (legacy)
    session_dates = (
        db.query(cast(models.Session.created_at, Date).label("d"))
        .filter(models.Session.user_id == student_id)
        .distinct()
        .all()
    )

    all_dates: set[date] = set()
    for row in interval_dates:
        if row.d:
            all_dates.add(row.d)
    for row in score_dates:
        if row.d:
            all_dates.add(row.d)
    for row in session_dates:
        if row.d:
            all_dates.add(row.d)

    if not all_dates:
        return 0, 0

    sorted_dates = sorted(all_dates, reverse=True)
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 4. Tính current_streak:
    # Nếu ngày học gần nhất là hôm nay: đếm từ hôm nay lùi về trước.
    # Nếu ngày học gần nhất là hôm qua: đếm từ hôm qua lùi về trước (vì ngày hôm nay vẫn đang diễn ra).
    # Nếu ngày gần nhất < hôm qua: streak đã đứt (current_streak = 0).
    current_streak = 0
    if sorted_dates[0] == today:
        current_streak = 1
        expected = yesterday
        for d in sorted_dates[1:]:
            if d == expected:
                current_streak += 1
                expected -= timedelta(days=1)
            else:
                break
    elif sorted_dates[0] == yesterday:
        current_streak = 1
        expected = yesterday - timedelta(days=1)
        for d in sorted_dates[1:]:
            if d == expected:
                current_streak += 1
                expected -= timedelta(days=1)
            else:
                break
    else:
        current_streak = 0

    # 5. Tính max_streak (chuỗi ngày liên tiếp kỷ lục trong toàn bộ lịch sử)
    asc_dates = sorted(all_dates)
    max_streak = 1
    running = 1
    for i in range(1, len(asc_dates)):
        if asc_dates[i] == asc_dates[i - 1] + timedelta(days=1):
            running += 1
            if running > max_streak:
                max_streak = running
        elif asc_dates[i] > asc_dates[i - 1] + timedelta(days=1):
            running = 1

    return current_streak, max(max_streak, current_streak)


@router.get("/metrics/heatmap", response_model=schemas.ActivityHeatmapResponse)
def get_activity_heatmap(
    student_id: str = Query(..., description="ID của học sinh cần xem"),
    weeks: int = Query(24, ge=1, le=52, description="Số tuần cần quét (16 - 24 tuần, mặc định 24 tuần ~ 168 ngày)"),
    days: Optional[int] = Query(None, ge=7, le=365, description="Số ngày cần quét (ưu tiên hơn weeks nếu truyền)"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.1 - Task T7.4:
    API quét bảng session_active_intervals tính tổng thời gian active từng ngày trong 16-24 tuần.
    - Chuẩn format GitHub Contribution Graph: mảng các ngày liên tục kèm số phút tương tác thực tế.
    - Tự động gán 5 mức nhiệt intensity_level (0 - 4) chuẩn bảng màu Socratic / GitHub.
    - Có fallback hỗ trợ phiên học cũ trước khi có bảng session_active_intervals.
    """
    # 1. Kiểm tra quyền truy cập (STUDENT xem chính mình, MONITOR xem học sinh liên kết)
    _verify_access_to_student(current_user, student_id, db)

    total_days = days if days is not None else (weeks * 7)
    today = date.today()
    start_date = today - timedelta(days=total_days - 1)
    end_date = today

    # 2. Query tổng active_seconds từ session_active_intervals
    interval_rows = (
        db.query(
            cast(models.SessionActiveInterval.start_time, Date).label("day"),
            func.coalesce(func.sum(models.SessionActiveInterval.active_seconds), 0).label("total_seconds"),
        )
        .filter(
            models.SessionActiveInterval.user_id == student_id,
            cast(models.SessionActiveInterval.start_time, Date) >= start_date,
            cast(models.SessionActiveInterval.start_time, Date) <= end_date,
        )
        .group_by(cast(models.SessionActiveInterval.start_time, Date))
        .all()
    )

    # 3. Fallback cho các session cũ chưa có record trong session_active_intervals
    recorded_session_subquery = (
        db.query(models.SessionActiveInterval.session_id)
        .filter(models.SessionActiveInterval.user_id == student_id)
        .distinct()
    )

    legacy_rows = (
        db.query(
            cast(models.Session.created_at, Date).label("day"),
            func.coalesce(
                func.sum(
                    func.extract("epoch", models.Session.updated_at)
                    - func.extract("epoch", models.Session.created_at)
                ),
                0,
            ).label("total_seconds"),
        )
        .filter(
            models.Session.user_id == student_id,
            cast(models.Session.created_at, Date) >= start_date,
            cast(models.Session.created_at, Date) <= end_date,
            ~models.Session.id.in_(recorded_session_subquery),
        )
        .group_by(cast(models.Session.created_at, Date))
        .all()
    )

    data_map: dict[str, int] = {}
    for r in interval_rows:
        d_str = str(r.day)
        secs = float(r.total_seconds or 0)
        data_map[d_str] = data_map.get(d_str, 0) + max(0, round(secs / 60))

    for r in legacy_rows:
        d_str = str(r.day)
        secs = float(r.total_seconds or 0)
        data_map[d_str] = data_map.get(d_str, 0) + max(0, round(secs / 60))

    # 4. Sinh đầy đủ chuỗi ngày liên tục từ start_date đến end_date (112 - 168 ngày)
    heatmap_days: list[schemas.HeatmapDayItem] = []
    total_active_mins = 0

    for i in range(total_days):
        d = start_date + timedelta(days=i)
        d_str = str(d)
        mins = data_map.get(d_str, 0)
        total_active_mins += mins

        # Phân loại 5 cấp độ mật độ (intensity_level: 0 -> 4) chuẩn GitHub / Socratic
        if mins <= 0:
            intensity = 0       # Không học
        elif mins <= 20:
            intensity = 1       # 1 - 20 phút
        elif mins <= 45:
            intensity = 2       # 21 - 45 phút
        elif mins <= 75:
            intensity = 3       # 46 - 75 phút
        else:
            intensity = 4       # > 75 phút

        heatmap_days.append(
            schemas.HeatmapDayItem(
                date=d_str,
                minutes=mins,
                active_minutes=mins,
                intensity_level=intensity,
            )
        )

    return schemas.ActivityHeatmapResponse(
        student_id=student_id,
        weeks=round(total_days / 7),
        days=total_days,
        start_date=str(start_date),
        end_date=str(end_date),
        total_active_minutes=total_active_mins,
        total_study_hours=round(total_active_mins / 60, 1),
        data=heatmap_days,
    )


@router.get("/metrics/summary", response_model=schemas.SummaryCardsResponse)
def get_summary_metrics(
    student_id: str = Query(..., description="ID của học sinh cần xem"),
    time_range: str = Query("7d", description="Khoảng thời gian: '7d', '30d' hoặc 'all'"),
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 7.1 - Task T7.5:
    API tính toán 100% số liệu thật từ Database thay thế mock data cho Summary Cards:
    - completed_problems: Tổng số bài hoàn thành quét từ bảng independence_scores
    - completed_change: Tỷ lệ tăng/giảm so với chu kỳ trước (+15%, -8%, v.v.)
    - independence_score & level: Điểm tự lực trung bình và đánh giá theo barem chuẩn 80-60-40
    - current_streak & max_streak: Chuỗi ngày học liên tục thật tính từ các mốc hoạt động
    - total_study_hours & avg_minutes_per_day: Thời gian học thực tế (loại bỏ idle)
    """
    # 1. Kiểm tra quyền truy cập
    _verify_access_to_student(current_user, student_id, db)

    today = date.today()

    if time_range == "7d":
        start_date = today - timedelta(days=6)
        prev_start = start_date - timedelta(days=7)
        prev_end = start_date - timedelta(days=1)
    elif time_range == "30d":
        start_date = today - timedelta(days=29)
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date - timedelta(days=1)
    else:  # "all"
        start_date = date(2020, 1, 1)
        prev_start = None
        prev_end = None

    # 2. Tổng số bài toán hoàn thành từ bảng independence_scores
    completed_problems = (
        db.query(func.count(models.IndependenceScore.id))
        .filter(
            models.IndependenceScore.student_id == student_id,
            cast(models.IndependenceScore.created_at, Date) >= start_date,
            cast(models.IndependenceScore.created_at, Date) <= today,
        )
        .scalar()
    ) or 0

    # 3. Tính tỷ lệ thay đổi (completed_change) so với chu kỳ tương đương trước đó
    if prev_start and prev_end:
        prev_completed = (
            db.query(func.count(models.IndependenceScore.id))
            .filter(
                models.IndependenceScore.student_id == student_id,
                cast(models.IndependenceScore.created_at, Date) >= prev_start,
                cast(models.IndependenceScore.created_at, Date) <= prev_end,
            )
            .scalar()
        ) or 0

        if prev_completed == 0:
            completed_change = f"+{completed_problems} bài" if completed_problems > 0 else "+0%"
        else:
            diff = completed_problems - prev_completed
            pct = round((diff / prev_completed) * 100)
            completed_change = f"{'+' if pct >= 0 else ''}{pct}%"
    else:
        completed_change = "+0%"

    # 4. Điểm Independence trung bình và phân loại mức độ theo barem 80 - 60 - 40
    score_query = (
        db.query(func.avg(models.IndependenceScore.score))
        .filter(
            models.IndependenceScore.student_id == student_id,
            cast(models.IndependenceScore.created_at, Date) >= start_date,
            cast(models.IndependenceScore.created_at, Date) <= today,
        )
        .scalar()
    )

    if score_query is not None:
        avg_score = round(float(score_query))
    else:
        # Fallback điểm trung bình all-time nếu kỳ này chưa giải bài nào
        all_time_score = (
            db.query(func.avg(models.IndependenceScore.score))
            .filter(models.IndependenceScore.student_id == student_id)
            .scalar()
        )
        avg_score = round(float(all_time_score)) if all_time_score is not None else 0

    if avg_score >= 80:
        independence_level = "Tự lập xuất sắc (ít dùng gợi ý)"
    elif avg_score >= 60:
        independence_level = "Tự lập tốt (dùng 1-2 gợi ý)"
    elif avg_score >= 40:
        independence_level = "Đang tiến bộ (cần một số gợi ý)"
    elif avg_score > 0:
        independence_level = "Cần thêm hỗ trợ sư phạm"
    else:
        independence_level = "Chưa có dữ liệu"

    # 5. Tính chuỗi ngày học Streak thật từ DB
    current_streak, max_streak = calculate_student_streak(student_id, db)

    # 6. Tính thời gian học thực tế (active_seconds loại trừ idle)
    total_active_seconds = (
        db.query(func.coalesce(func.sum(models.SessionActiveInterval.active_seconds), 0))
        .filter(
            models.SessionActiveInterval.user_id == student_id,
            cast(models.SessionActiveInterval.start_time, Date) >= start_date,
            cast(models.SessionActiveInterval.start_time, Date) <= today,
        )
        .scalar()
    ) or 0

    recorded_session_subquery = (
        db.query(models.SessionActiveInterval.session_id)
        .filter(models.SessionActiveInterval.user_id == student_id)
        .distinct()
    )
    legacy_seconds = (
        db.query(
            func.coalesce(
                func.sum(
                    func.extract("epoch", models.Session.updated_at)
                    - func.extract("epoch", models.Session.created_at)
                ),
                0,
            )
        )
        .filter(
            models.Session.user_id == student_id,
            cast(models.Session.created_at, Date) >= start_date,
            cast(models.Session.created_at, Date) <= today,
            ~models.Session.id.in_(recorded_session_subquery),
        )
        .scalar()
    ) or 0

    total_seconds = float(total_active_seconds) + float(legacy_seconds)
    total_active_minutes = max(0, round(total_seconds / 60))
    total_study_hours = round(total_active_minutes / 60, 1)

    # Đếm số ngày có học thực tế trong chu kỳ
    active_days_count = (
        db.query(cast(models.SessionActiveInterval.start_time, Date))
        .filter(
            models.SessionActiveInterval.user_id == student_id,
            cast(models.SessionActiveInterval.start_time, Date) >= start_date,
            cast(models.SessionActiveInterval.start_time, Date) <= today,
        )
        .distinct()
        .count()
    )
    avg_minutes_per_day = round(total_active_minutes / active_days_count) if active_days_count > 0 else 0

    return schemas.SummaryCardsResponse(
        student_id=student_id,
        time_range=time_range,
        start_date=str(start_date),
        end_date=str(today),
        # Snake_case
        completed_problems=completed_problems,
        completed_change=completed_change,
        independence_score=avg_score,
        independence_level=independence_level,
        current_streak=current_streak,
        max_streak=max_streak,
        total_study_hours=total_study_hours,
        avg_minutes_per_day=avg_minutes_per_day,
        total_active_minutes=total_active_minutes,
        # CamelCase
        completedProblems=completed_problems,
        completedChange=completed_change,
        independenceScore=avg_score,
        independenceLevel=independence_level,
        currentStreak=current_streak,
        maxStreak=max_streak,
        totalStudyHours=total_study_hours,
        avgMinutesPerDay=avg_minutes_per_day,
    )
