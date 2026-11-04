"""
US 9.5 (Task T9.18): Router Quản Trị Báo Lỗi & Sự Cố Hệ Thống (Incident Hub)
=============================================================================
Cung cấp các API:
  - GET   /admin/errors                     : Tra cứu sự cố hệ thống & báo lỗi học sinh (phân trang, lọc đa năng, search user)
  - GET   /admin/errors/{error_id}          : Xem chi tiết 1 sự cố (Drawer trượt)
  - PATCH /admin/errors/{error_id}/resolve  : Đổi trạng thái sự cố sang "RESOLVED"
  - POST  /api/errors/report-user-issue     : Học sinh bấm cờ 🚩 báo lỗi bài toán/AI (kèm debounce chống spam)
"""

import math
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from database import get_db
import models
import schemas
import dependencies

router = APIRouter(tags=["Admin System Errors & Incident Hub"])

# Bộ nhớ tạm (in-memory) phục vụ debounce nhanh chống spam theo IP hoặc User ID
_REPORT_DEBOUNCE_CACHE: dict = {}
DEBOUNCE_WINDOW_SECONDS = 30


def _clean_debounce_cache():
    """Dọn dẹp các cache key quá hạn trong bộ nhớ."""
    now = datetime.now(timezone.utc)
    expired_keys = [k for k, exp in _REPORT_DEBOUNCE_CACHE.items() if exp < now]
    for k in expired_keys:
        _REPORT_DEBOUNCE_CACHE.pop(k, None)


def _map_system_error_response(record: models.SystemError) -> schemas.SystemErrorItemResponse:
    """Chuyển đổi ORM Model thành Pydantic Schema kèm thông tin tài khoản người dùng."""
    username = record.user.username if record.user else None
    email = record.user_email or (record.user.email if record.user else None)

    return schemas.SystemErrorItemResponse(
        id=record.id,
        error_code=record.error_code,
        error_type=record.error_type,
        severity=record.severity,
        message=record.message,
        stack_trace=record.stack_trace,
        endpoint=record.endpoint,
        request_payload=record.request_payload,
        user_id=record.user_id,
        user_email=email,
        username=username,
        status=record.status,
        resolved_at=record.resolved_at,
        resolved_by=record.resolved_by,
        resolved_note=record.resolved_note,
        created_at=record.created_at,
    )


# ==============================================================================
# 1. API Học Sinh Báo Lỗi Bài Toán (Flag 🚩 Button)
# ==============================================================================

@router.post(
    "/api/errors/report-user-issue",
    response_model=schemas.ReportUserIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/errors/report-user-issue",
    response_model=schemas.ReportUserIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_user_issue(
    body: schemas.ReportUserIssueRequest,
    request: Request,
    current_user: Optional[dict] = Depends(dependencies.get_optional_current_user),
    db: Session = Depends(get_db),
):
    """
    US 9.5 - AC 9.5.1:
    Tiếp nhận báo lỗi từ học sinh khi bấm nút cờ 🚩 bên cạnh tin nhắn AI.
    - Phân loại: USER_REPORT
    - Nhãn màu: INFO
    - Chống spam (Debounce): Giới hạn 1 báo lỗi / 30s cho cùng 1 câu hỏi/người dùng.
    """
    _clean_debounce_cache()

    user_id = current_user["id"] if current_user else None
    user_email = current_user.get("email") if current_user else None
    client_ip = request.client.host if request.client else "unknown"

    # Tạo debounce key
    target_key = f"{user_id or client_ip}:{body.message_id or body.reason}"
    now = datetime.now(timezone.utc)

    # 1. Kiểm tra cache debounce in-memory
    if target_key in _REPORT_DEBOUNCE_CACHE and _REPORT_DEBOUNCE_CACHE[target_key] > now:
        remaining = int((_REPORT_DEBOUNCE_CACHE[target_key] - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Em đã gửi báo lỗi cho câu này rồi. Vui lòng chờ {max(1, remaining)} giây để gửi phản hồi tiếp nhé!",
        )

    # 2. Kiểm tra thêm trong DB nếu cùng user_id và cùng message_id trong 30s
    if user_id:
        cutoff = now - timedelta(seconds=DEBOUNCE_WINDOW_SECONDS)
        recent_in_db = (
            db.query(models.SystemError)
            .filter(
                models.SystemError.user_id == user_id,
                models.SystemError.error_type == "USER_REPORT",
                models.SystemError.created_at >= cutoff,
            )
            .first()
        )
        if recent_in_db and body.message_id and body.message_id in (recent_in_db.request_payload or ""):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Em đã gửi báo lỗi cho câu này rồi. Hệ thống đã ghi nhận phản hồi của em!",
            )

    # Đăng ký debounce key
    _REPORT_DEBOUNCE_CACHE[target_key] = now + timedelta(seconds=DEBOUNCE_WINDOW_SECONDS)

    # Đóng gói payload chi tiết
    payload_dict = {
        "reason": body.reason,
        "detail": body.detail,
        "message_id": body.message_id,
        "session_id": body.session_id,
        "client_context": body.client_context,
        "reported_at": now.isoformat(),
    }

    # Sinh mã lỗi định danh người dùng
    error_code = f"UR_{uuid.uuid4().hex[:8].upper()}"
    detail_suffix = f" - {body.detail}" if body.detail else ""
    summary_message = f"[Báo lỗi học sinh] {body.reason}{detail_suffix}"

    error_record = models.SystemError(
        id=uuid.uuid4().hex,
        error_code=error_code,
        error_type="USER_REPORT",
        severity="INFO",  # AC 9.5.4: Nhãn xanh dương INFO
        message=summary_message,
        stack_trace=None,
        endpoint=body.endpoint or "/chat/message",
        request_payload=json.dumps(payload_dict, ensure_ascii=False),
        user_id=user_id,
        user_email=user_email,
        status="OPEN",
    )

    db.add(error_record)
    db.commit()
    db.refresh(error_record)

    return schemas.ReportUserIssueResponse(
        success=True,
        message="Cảm ơn em đã gửi phản hồi!",
        error_id=error_record.id,
        error_code=error_record.error_code,
    )


# ==============================================================================
# 2. API Quản Trị Sự Cố (Admin Incident Hub)
# ==============================================================================

@router.get(
    "/admin/errors",
    response_model=schemas.SystemErrorsListResponse,
)
@router.get(
    "/api/admin/errors",
    response_model=schemas.SystemErrorsListResponse,
)
def list_system_errors(
    page: int = Query(1, ge=1, description="Số trang hiện tại"),
    limit: int = Query(20, ge=1, le=100, description="Số lượng sự cố trên mỗi trang"),
    search: Optional[str] = Query(None, description="Tìm theo User ID, Email, Username, Mã lỗi, Thông điệp"),
    error_type: Optional[str] = Query(None, description="Lọc loại lỗi: CRASH_500 | AI_TIMEOUT | USER_REPORT | SMTP_ERROR | ALL"),
    severity: Optional[str] = Query(None, description="Lọc mức độ nghiêm trọng: CRITICAL | WARNING | INFO | ALL"),
    status_filter: Optional[str] = Query(None, alias="status", description="Lọc trạng thái: OPEN | RESOLVED | ALL"),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    US 9.5 - AC 9.5.2 & AC 9.5.3:
    Tra cứu danh sách sự cố hệ thống và phản ánh của người dùng:
      - Sắp xếp mới nhất lên đầu bảng (created_at DESC).
      - Lọc theo loại lỗi (CRASH_500, AI_TIMEOUT, USER_REPORT).
      - Lọc theo mức độ nghiêm trọng (CRITICAL, WARNING, INFO).
      - Lọc theo trạng thái (OPEN, RESOLVED).
      - Tìm kiếm tức thì theo User ID hoặc Email học sinh (AC 9.5.3).
    """
    query = db.query(models.SystemError)

    # 1. Lọc theo trạng thái (status)
    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(models.SystemError.status == status_filter.upper())

    # 2. Lọc theo phân loại lỗi (error_type)
    if error_type and error_type.upper() != "ALL":
        query = query.filter(models.SystemError.error_type == error_type.upper())

    # 3. Lọc theo mức độ nghiêm trọng (severity)
    if severity and severity.upper() != "ALL":
        query = query.filter(models.SystemError.severity == severity.upper())

    # 4. Tìm kiếm từ khóa (AC 9.5.3)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.outerjoin(models.User, models.SystemError.user_id == models.User.id).filter(
            or_(
                models.SystemError.user_id.ilike(term),
                models.SystemError.user_email.ilike(term),
                models.SystemError.error_code.ilike(term),
                models.SystemError.message.ilike(term),
                models.User.username.ilike(term),
                models.User.email.ilike(term),
            )
        )

    total = query.count()
    total_pages = max(1, math.ceil(total / limit))
    offset = (page - 1) * limit

    # Mới nhất xuất hiện ngay đầu bảng theo AC 9.5.2
    records = query.order_by(models.SystemError.created_at.desc()).offset(offset).limit(limit).all()

    items = [_map_system_error_response(r) for r in records]

    return schemas.SystemErrorsListResponse(
        success=True,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
        items=items,
    )


@router.get(
    "/admin/errors/{error_id}",
    response_model=schemas.SystemErrorItemResponse,
)
@router.get(
    "/api/admin/errors/{error_id}",
    response_model=schemas.SystemErrorItemResponse,
)
def get_system_error_detail(
    error_id: str,
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    US 9.5 - AC 9.5.5:
    Xem chi tiết sự cố hệ thống phục vụ hiển thị Drawer trượt bên phải:
    User context, request payload và Full Stack Trace.
    """
    record = db.query(models.SystemError).filter(models.SystemError.id == error_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông tin sự cố với mã ID này.",
        )

    return _map_system_error_response(record)


@router.patch(
    "/admin/errors/{error_id}/resolve",
    response_model=schemas.SystemErrorItemResponse,
)
@router.patch(
    "/admin/errors/{error_id}",
    response_model=schemas.SystemErrorItemResponse,
)
@router.patch(
    "/api/admin/errors/{error_id}/resolve",
    response_model=schemas.SystemErrorItemResponse,
)
def resolve_system_error(
    error_id: str,
    body: Optional[schemas.ResolveErrorRequest] = None,
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    US 9.5 - AC 9.5.6:
    Admin bấm nút "Đánh dấu đã xử lý" trên Drawer -> Đổi trạng thái sang "RESOLVED" tức thì.
    """
    record = db.query(models.SystemError).filter(models.SystemError.id == error_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy sự cố cần xử lý.",
        )

    record.status = "RESOLVED"
    record.resolved_at = datetime.now(timezone.utc)
    admin_id = current_user.get("id")
    if admin_id and db.query(models.User.id).filter(models.User.id == str(admin_id)).first():
        record.resolved_by = str(admin_id)
    else:
        record.resolved_by = None
    if body and body.resolved_note:
        record.resolved_note = body.resolved_note

    db.commit()
    db.refresh(record)

    return _map_system_error_response(record)
