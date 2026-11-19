"""
File: backend/dependencies/rate_limit.py
Mô tả: FastAPI Dependency – Rate-limiting 10 câu / 24h cho Guest users qua Redis.

Task: [BE] Xây dựng Middleware/Dependency rate-limit 10 câu/24h qua Redis

Cơ chế hoạt động:
    1. Chỉ áp dụng với request có session_id bắt đầu bằng "guest-".
    2. Dùng Guest-ID làm key trong Redis: "guest_rate_limit:<session_id>"
    3. Mỗi lần gọi: INCR key (tăng số đếm lên 1).
    4. Nếu đây là lần đầu tiên (INCR trả về 1): gắn thêm EXPIRE 86400 giây (24h).
    5. Nếu số đếm > GUEST_MAX_REQUESTS: raise HTTP 429 Too Many Requests.
    6. Nếu Redis không khả dụng: cho qua bình thường (fail-open) — tránh block user vì lỗi hạ tầng.
"""

import time
import logging
from fastapi import Depends, HTTPException, Request
import redis.asyncio as aioredis
from redis_client import get_redis
from database import get_db
from sqlalchemy.orm import Session
from services.rate_limiter_service import RateLimiterService, _fallback_memory_limiter
import services.system_config_service as system_config_service

logger = logging.getLogger(__name__)

# ---- Cấu hình Rate-limit mặc định ----
GUEST_MAX_REQUESTS = 10     # Tối đa mặc định 10 câu (nếu DB chưa cấu hình)
GUEST_WINDOW_SECONDS = 86400  # Trong vòng 24h (= 24 * 60 * 60 giây)


async def check_guest_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    FastAPI Dependency: Kiểm tra và cập nhật rate-limit động cho Guest users theo Admin Settings.

    - Nếu session_id KHÔNG bắt đầu bằng "guest-": bỏ qua (cho học sinh đăng nhập).
    - Lấy cấu hình guest_rate_limit từ hệ thống (mặc định 10 câu/ngày).
    - Nếu số lần gọi vượt guest_rate_limit: raise HTTP 429.
    - Hỗ trợ Fail-Open / RAM Fallback khi Redis gặp sự cố.
    """
    # Đọc body JSON để lấy session_id (request body chỉ đọc được 1 lần, phải cache lại)
    try:
        body = await request.json()
        session_id: str = body.get("session_id", "")
    except Exception:
        # Nếu parse body thất bại → bỏ qua rate-limit, để router tự xử lý lỗi đó
        return

    # Chỉ giới hạn Guest session (session_id bắt đầu bằng "guest-")
    if not session_id.startswith("guest-"):
        return

    # Lấy cấu hình động từ Admin Settings (US 10.3 / US 11.1)
    try:
        sys_settings = system_config_service.get_system_settings(db)
        guest_max = int(sys_settings.get("guest_rate_limit", GUEST_MAX_REQUESTS))
    except Exception:
        guest_max = GUEST_MAX_REQUESTS

    # Lấy IP của người dùng (hỗ trợ cả trường hợp chạy sau Nginx/Proxy)
    client_ip = request.client.host
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    # Dùng IP thay vì session_id để chặn mánh khoé ẩn danh / xoá cache
    redis_key = f"guest_rate_limit_ip:{client_ip}"

    try:
        # Tăng biến đếm lên 1 (INCR tự tạo key mới với giá trị 1 nếu chưa tồn tại)
        current_count = await redis.incr(redis_key)

        # Chỉ set TTL khi đây là lần đầu tiên (tránh reset đồng hồ ở mỗi request)
        if current_count == 1:
            await redis.expire(redis_key, GUEST_WINDOW_SECONDS)

        # Kiểm tra đã vượt giới hạn chưa
        if current_count > guest_max:
            # Giảm lại biến đếm vì lần gọi này bị chặn (không tốn lượt hợp lệ)
            await redis.decr(redis_key)
            
            # Tính thời gian còn lại (giây) để thông báo cho người dùng
            ttl = await redis.ttl(redis_key)
            hours_left = max(0, ttl // 3600)
            minutes_left = max(1, (ttl % 3600) // 60)

            reset_at = int(time.time() + ttl)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "reason": "GUEST_LIMIT",
                    "message": (
                        f"Bạn đã sử dụng hết {guest_max} câu hỏi miễn phí trong 24 giờ. "
                        f"Vui lòng đăng ký tài khoản để tiếp tục học không giới hạn, "
                        f"hoặc thử lại sau {hours_left} giờ {minutes_left} phút."
                    ),
                    "limit": guest_max,
                    "remaining": 0,
                    "current_count": current_count - 1,  # số thực tế đã dùng
                    "retry_after_seconds": ttl,
                    "reset_at": reset_at,
                },
                headers=RateLimiterService.build_rate_limit_headers(
                    limit=guest_max,
                    remaining=0,
                    retry_after=ttl,
                    reset_at=reset_at,
                ),
            )

        logger.info(
            f"[RateLimit] Guest session '{session_id}': "
            f"{current_count}/{guest_max} requests used (TTL: {await redis.ttl(redis_key)}s)"
        )

    except HTTPException:
        # Cho phép HTTPException truyền lên tiếp (không bắt nuốt)
        raise
    except Exception as e:
        # Redis offline hoặc lỗi khác → dùng In-Memory RAM Fallback
        logger.warning(
            f"[RateLimit] Redis không khả dụng ({e}), chuyển sang In-Memory RAM fallback cho '{session_id}'"
        )
        is_ok, rem, retry = _fallback_memory_limiter.check_and_add(
            redis_key, limit=guest_max, window_seconds=GUEST_WINDOW_SECONDS
        )
        if not is_ok:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "reason": "GUEST_LIMIT",
                    "message": f"Bạn đã sử dụng hết {guest_max} câu hỏi dùng thử hôm nay. Vui lòng đăng ký để tiếp tục.",
                    "limit": guest_max,
                    "remaining": 0,
                    "retry_after_seconds": retry,
                }
            )
