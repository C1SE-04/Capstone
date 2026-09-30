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

import logging
from fastapi import Depends, HTTPException, Request
import redis.asyncio as aioredis
from redis_client import get_redis

logger = logging.getLogger(__name__)

# ---- Cấu hình Rate-limit ----
GUEST_MAX_REQUESTS = 10     # Tối đa 10 câu
GUEST_WINDOW_SECONDS = 86400  # Trong vòng 24h (= 24 * 60 * 60 giây)


async def check_guest_rate_limit(
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    FastAPI Dependency: Kiểm tra và cập nhật rate-limit cho Guest users.

    Cách dùng trong router:
        @router.post("/chat/orchestrator")
        async def chat(..., _: None = Depends(check_guest_rate_limit)):
            ...

    - Nếu session_id KHÔNG bắt đầu bằng "guest-": bỏ qua (cho đăng nhập bình thường).
    - Nếu số lần gọi vượt GUEST_MAX_REQUESTS: raise HTTP 429.
    - Nếu Redis lỗi/offline: ghi log warning rồi cho qua (fail-open).
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

    redis_key = f"guest_rate_limit:{session_id}"

    try:
        # Tăng biến đếm lên 1 (INCR tự tạo key mới với giá trị 1 nếu chưa tồn tại)
        current_count = await redis.incr(redis_key)

        # Chỉ set TTL khi đây là lần đầu tiên (tránh reset đồng hồ ở mỗi request)
        if current_count == 1:
            await redis.expire(redis_key, GUEST_WINDOW_SECONDS)

        # Kiểm tra đã vượt giới hạn chưa
        if current_count > GUEST_MAX_REQUESTS:
            # Giảm lại biến đếm vì lần gọi này bị chặn (không tốn lượt hợp lệ)
            await redis.decr(redis_key)
            
            # Tính thời gian còn lại (giây) để thông báo cho người dùng
            ttl = await redis.ttl(redis_key)
            hours_left = ttl // 3600
            minutes_left = (ttl % 3600) // 60

            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Bạn đã sử dụng hết {GUEST_MAX_REQUESTS} câu hỏi miễn phí trong 24 giờ. "
                        f"Vui lòng đăng ký tài khoản để tiếp tục học không giới hạn, "
                        f"hoặc thử lại sau {hours_left} giờ {minutes_left} phút."
                    ),
                    "limit": GUEST_MAX_REQUESTS,
                    "current_count": current_count - 1,  # số thực tế đã dùng
                    "retry_after_seconds": ttl,
                }
            )

        logger.info(
            f"[RateLimit] Guest session '{session_id}': "
            f"{current_count}/{GUEST_MAX_REQUESTS} requests used (TTL: {await redis.ttl(redis_key)}s)"
        )

    except HTTPException:
        # Cho phép HTTPException truyền lên tiếp (không bắt nuốt)
        raise
    except Exception as e:
        # Redis offline hoặc lỗi khác → fail-open (cho qua, ghi log cảnh báo)
        logger.warning(
            f"[RateLimit] Redis không khả dụng, bỏ qua rate-limit cho '{session_id}': {e}"
        )
