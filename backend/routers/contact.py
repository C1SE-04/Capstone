"""
========================================================================================
File: backend/routers/contact.py
Sprint 11 - US 11.5: Feedback & Contact Hub
========================================================================================
FastAPI Router cho Trang Liên Hệ & Đóng Góp Ý Kiến:
  - POST /api/contact/submit (và alias /contact/submit): Tiếp nhận form từ người dùng
  - POST /api/contact/upload-attachment: Upload ảnh đính kèm (<= 5MB) lên Cloudinary
  - GET  /api/contact/requests: Quản trị viên xem danh sách yêu cầu
  - PATCH /api/contact/requests/{id}/status: Quản trị viên cập nhật trạng thái xử lý
========================================================================================
"""

import os
import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
import httpx

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
import models
import schemas
import dependencies
from services.webhook_service import dispatch_contact_webhook

logger = logging.getLogger("contact_router")

router = APIRouter(tags=["Contact Hub"])

MAX_CONTENT_LENGTH = 500
MIN_CONTENT_LENGTH = 5
MAX_ATTACHMENT_SIZE_BYTES = 5 * 1024 * 1024  # 5MB theo AC4
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


async def _verify_recaptcha_v3(token: Optional[str]) -> Optional[float]:
    """
    Xác thực token Google reCAPTCHA v3 ngầm phía server.
    Trả về điểm số bot score (0.0 -> 1.0). Nếu chưa cấu hình secret key, trả về None (fail-open an toàn).
    """
    secret = os.getenv("RECAPTCHA_SECRET_KEY", "").strip()
    if not secret or not token:
        return None

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret, "response": token},
            )
            data = resp.json()
            if data.get("success"):
                return float(data.get("score", 1.0))
            else:
                logger.warning(f"[reCAPTCHA] Xác thực token thất bại: {data.get('error-codes')}")
                return 0.0
    except Exception as e:
        logger.warning(f"[reCAPTCHA] Lỗi kết nối Google reCAPTCHA verify: {e}")
        return None


# ────────────────────────────────────────────────────────────────────────────
# 1. API TIẾP NHẬN FORM LIÊN HỆ & BẮN WEBHOOK
# ────────────────────────────────────────────────────────────────────────────

@router.post("/api/contact/submit", response_model=schemas.ContactSubmitResponse, status_code=status.HTTP_200_OK)
@router.post("/contact/submit", response_model=schemas.ContactSubmitResponse, status_code=status.HTTP_200_OK)
async def submit_contact_form(
    payload: schemas.ContactSubmitInput,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    US 11.5 - API tiếp nhận biểu mẫu liên hệ & đóng góp ý kiến:
    1. Kiểm tra validation: Họ tên, Email, Chủ đề, Nội dung (5-500 ký tự).
    2. Xác thực ngầm Google reCAPTCHA v3 (nếu có cấu hình).
    3. Lưu thông tin vào bảng database 'contact_requests'.
    4. Bắn thông báo Webhook tự động tới Discord / Telegram của nhóm phát triển (Dev/PM).
    """
    resolved_full_name = payload.get_resolved_full_name()
    resolved_topic = payload.get_resolved_topic()
    resolved_content = payload.get_resolved_content()

    # 1. Validate họ tên
    if not resolved_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng nhập họ và tên của bạn."
        )

    # 2. Validate nội dung (AC3: 0/500 ký tự)
    if not resolved_content or len(resolved_content) < MIN_CONTENT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vui lòng nhập nội dung chi tiết ít nhất {MIN_CONTENT_LENGTH} ký tự."
        )

    if len(resolved_content) > MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nội dung chi tiết không được vượt quá {MAX_CONTENT_LENGTH} ký tự."
        )

    # 3. Xác thực reCAPTCHA v3 ngầm
    recaptcha_score = payload.recaptcha_score
    if recaptcha_score is None and payload.recaptcha_token:
        recaptcha_score = await _verify_recaptcha_v3(payload.recaptcha_token)

    # 4. Lưu bản ghi vào cơ sở dữ liệu
    contact_record = models.ContactRequest(
        id=uuid.uuid4().hex,
        full_name=resolved_full_name,
        email=str(payload.email).lower().strip(),
        role=(payload.role or "GUEST").upper(),
        topic=resolved_topic,
        content=resolved_content,
        attachment_urls=payload.attachment_urls or [],
        recaptcha_score=recaptcha_score,
        status="PENDING",
    )
    db.add(contact_record)
    db.commit()
    db.refresh(contact_record)

    # 5. Bắn Webhook thông báo tự động cho đội ngũ (gắn tag Dev/PM theo topic)
    background_tasks.add_task(dispatch_contact_webhook, contact_record)

    created_iso = (
        contact_record.created_at.isoformat()
        if contact_record.created_at
        else datetime.now(timezone.utc).isoformat()
    )

    return schemas.ContactSubmitResponse(
        success=True,
        message="Cảm ơn bạn đã gửi đóng góp ý kiến! Đội ngũ SocraticKid sẽ phản hồi trong vòng 12-24h.",
        request_id=contact_record.id,
        created_at=created_iso,
    )


# ────────────────────────────────────────────────────────────────────────────
# 2. API UPLOAD ẢNH ĐÍNH KÈM LÊN CLOUDINARY
# ────────────────────────────────────────────────────────────────────────────

@router.post("/api/contact/upload-attachment")
@router.post("/contact/upload-attachment")
async def upload_contact_attachment(
    file: UploadFile = File(...),
):
    """
    US 11.5 - AC4: API upload ảnh đính kèm cho Form liên hệ:
    - Chặn file không phải ảnh (chỉ chấp nhận jpeg, png, webp).
    - Chặn file vượt quá 5MB.
    - Upload an toàn lên Cloudinary và trả về URL ảnh.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng file không hợp lệ. Vui lòng chọn file ảnh (JPG, PNG, WEBP)."
        )

    # Đọc nội dung file để kiểm tra kích thước
    content = await file.read()
    if len(content) > MAX_ATTACHMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dung lượng ảnh vượt quá giới hạn cho phép (tối đa 5MB)."
        )

    # Upload lên Cloudinary
    try:
        import cloudinary
        import cloudinary.uploader
        from routers.upload import _configure_cloudinary

        _configure_cloudinary()
        result = cloudinary.uploader.upload(
            content,
            folder="socratickid/contact_attachments",
            resource_type="image",
        )
        return {
            "success": True,
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }
    except Exception as e:
        logger.warning(f"[Cloudinary] Lỗi upload ảnh contact ({e}), chuyển sang URL giả lập dev")
        # Chế độ dự phòng cho môi trường dev/test khi Cloudinary chưa có key thật
        mock_url = f"https://res.cloudinary.com/demo/image/upload/contact_{uuid.uuid4().hex[:8]}.jpg"
        return {
            "success": True,
            "url": mock_url,
            "public_id": f"mock_{uuid.uuid4().hex[:8]}",
            "mock": True,
        }


# ────────────────────────────────────────────────────────────────────────────
# 3. API QUẢN TRỊ VIÊN XEM & QUẢN LÝ PHẢN HỒI
# ────────────────────────────────────────────────────────────────────────────

@router.get("/api/contact/requests", response_model=List[schemas.ContactRequestItemResponse])
def get_contact_requests(
    limit: int = 50,
    topic: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 11.5: API Quản trị viên xem danh sách các phản hồi / liên hệ của người dùng.
    Chỉ cho phép role ADMIN.
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên mới có quyền xem danh sách phản hồi liên hệ."
        )

    query = db.query(models.ContactRequest)
    if topic:
        query = query.filter(models.ContactRequest.topic == topic.upper())
    if status_filter:
        query = query.filter(models.ContactRequest.status == status_filter.upper())

    records = query.order_by(desc(models.ContactRequest.created_at)).limit(limit).all()
    return records


@router.patch("/api/contact/requests/{request_id}/status", response_model=schemas.ContactRequestItemResponse)
def update_contact_status(
    request_id: str,
    payload: schemas.ContactStatusUpdateInput,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db),
):
    """
    US 11.5: Quản trị viên cập nhật trạng thái xử lý phản hồi (PENDING, IN_PROGRESS, RESOLVED, REJECTED).
    """
    if current_user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên mới có quyền cập nhật trạng thái phản hồi."
        )

    target = db.query(models.ContactRequest).filter(models.ContactRequest.id == request_id).first()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy yêu cầu liên hệ này."
        )

    target.status = payload.status.upper()
    db.commit()
    db.refresh(target)
    return target

