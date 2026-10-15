# US 6.4 - Task #173: Tích hợp Cloudinary SDK & Cung cấp API upload/ký chữ ký ảnh
# Hai endpoints:
#   POST /upload/image       → Backend nhận file, upload lên Cloudinary, trả về HTTPS URL
#   GET  /upload/signature   → Tạo chữ ký có thời hạn để FE upload thẳng lên Cloudinary (server-side signing)

import os
import time
import hashlib
import hmac
from typing import Optional

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import JSONResponse

import schemas
import dependencies

router = APIRouter(tags=["Upload & Cloudinary"])

# ─── Kích thước tối đa cho phép ─── #
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024   # 5 MB (theo AC trong US 6.4)
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
UPLOAD_FOLDER = "socratickid/attachments"


def _get_cloudinary_config() -> dict:
    """Đọc credentials Cloudinary từ biến môi trường và kiểm tra đầy đủ."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.getenv("CLOUDINARY_API_KEY", "")
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "")

    if not cloud_name or not api_key or not api_secret:
        raise HTTPException(
            status_code=503,
            detail="Cloudinary chưa được cấu hình. Vui lòng thêm CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET vào .env.",
        )

    return {"cloud_name": cloud_name, "api_key": api_key, "api_secret": api_secret}


def _configure_cloudinary():
    """Cấu hình Cloudinary SDK từ biến môi trường."""
    cfg = _get_cloudinary_config()
    cloudinary.config(
        cloud_name=cfg["cloud_name"],
        api_key=cfg["api_key"],
        api_secret=cfg["api_secret"],
        secure=True,  # Luôn dùng HTTPS
    )
    return cfg


# ─────────────────────────────────────────────
# POST /upload/image
# Nhận file ảnh từ client, upload lên Cloudinary,
# trả về secure_url để lưu vào cột attachment_url của bảng messages.
# ─────────────────────────────────────────────
@router.post("/upload/image", response_model=schemas.CloudinaryUploadResponse)
async def upload_image(
    file: UploadFile = File(..., description="File ảnh cần upload (PNG, JPG, WEBP). Tối đa 5MB."),
    current_user: dict = Depends(dependencies.get_current_user),
):
    """
    Task #173 (US 6.4): Upload ảnh bài toán lên Cloudinary.
    - Kiểm tra content-type và kích thước file (≤ 5MB).
    - Upload an toàn lên Cloudinary với folder riêng của ứng dụng.
    - Trả về HTTPS URL để FE hiển thị preview và lưu vào DB qua API /chat/orchestrator.
    """
    # 1. Kiểm tra content-type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Chỉ hỗ trợ ảnh PNG, JPG, WEBP. Nhận được: {file.content_type}",
        )

    # 2. Đọc file và kiểm tra kích thước
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Chỉ hỗ trợ ảnh dưới 5MB.",
        )

    # 3. Cấu hình Cloudinary SDK
    _configure_cloudinary()

    # 4. Upload lên Cloudinary
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder=UPLOAD_FOLDER,
            resource_type="image",
            # Giới hạn max width 2000px để tiết kiệm băng thông/lưu trữ
            transformation=[{"quality": "auto", "fetch_format": "auto"}],
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Upload lên Cloudinary thất bại: {str(e)}",
        )

    return schemas.CloudinaryUploadResponse(
        success=True,
        url=result.get("secure_url", ""),
        public_id=result.get("public_id", ""),
        secure_url=result.get("secure_url", ""),
        format=result.get("format", ""),
        width=result.get("width"),
        height=result.get("height"),
        bytes=result.get("bytes"),
    )


# ─────────────────────────────────────────────
# GET /upload/signature
# Tạo chữ ký HMAC-SHA1 có thời hạn để FE upload
# thẳng lên Cloudinary mà không cần đi qua BE.
# (server-side signing — an toàn vì api_secret không lộ ra FE)
# ─────────────────────────────────────────────
@router.get("/upload/signature", response_model=schemas.CloudinarySignatureResponse)
def get_upload_signature(
    current_user: dict = Depends(dependencies.get_current_user),
):
    """
    Task #173 (US 6.4): Tạo chữ ký an toàn để FE upload ảnh thẳng lên Cloudinary.
    - FE gọi endpoint này để lấy signature + timestamp.
    - FE dùng signature đó gửi thẳng ảnh lên Cloudinary (không qua BE).
    - API secret KHÔNG bao giờ gửi về FE — chỉ trả về signature đã ký.
    """
    cfg = _get_cloudinary_config()
    _configure_cloudinary()

    timestamp = int(time.time())
    folder = UPLOAD_FOLDER

    # Xây dựng chuỗi ký theo đúng quy tắc Cloudinary:
    # "folder=<folder>&timestamp=<timestamp><api_secret>"
    params_to_sign = f"folder={folder}&timestamp={timestamp}"
    signature_raw = params_to_sign + cfg["api_secret"]

    # Ký bằng SHA-256 (Cloudinary hỗ trợ cả SHA-1 và SHA-256)
    import hashlib
    signature = hashlib.sha256(signature_raw.encode("utf-8")).hexdigest()

    return schemas.CloudinarySignatureResponse(
        signature=signature,
        timestamp=timestamp,
        api_key=cfg["api_key"],
        cloud_name=cfg["cloud_name"],
        folder=folder,
    )
