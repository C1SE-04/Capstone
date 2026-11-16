"""
File: backend/services/rate_limiter_service.py
Mô tả: Service lõi Quản trị Lưu lượng & Chống Lạm dụng Tài nguyên Đa tầng (Multi-tier Rate Limiter)
Dự án: Nền tảng Gia sư Toán Socratic Thông minh (SocraticKid)
Tác giả: Kỹ sư [Thống]
User Story: US 11.1 - Task #357 (T11.1.0) & Task #359 (T11.1.2)

Kiến trúc & Tính năng chính:
    1. Thuật toán Redis Sliding Window Log (ZSET):
       - Khắc phục triệt để lỗi dồn spike ở ranh giới 2 phút của Fixed Window.
       - Tự động dọn dẹp các mốc cũ quá 60s bằng ZREMRANGEBYSCORE.
       - Tính toán chính xác số giây cần chờ (Retry-After) dựa vào mốc request cũ nhất trong cửa sổ.
    2. Hạn mức Đa tầng (Multi-tier Defense):
       - Tầng Cá nhân (Student Chat): Cấu hình động theo `student_rate_limit` từ Admin Settings (US 10.3).
       - Tầng Toàn hệ thống (Global Gemini Quota): Khóa trần Max 14 RPM để bảo vệ quota Gemini Free Tier 15 RPM.
       - Tầng Sư phạm (Socratic Cool-Down): Bắt buộc chờ tối thiểu 5s từ khi AI trả lời xong, chống spam nút gửi.
    3. Chuẩn hóa Quốc tế RFC 6585 & Industry Headers:
       - Header: Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset.
    4. Cơ chế Controlled Fail-Open (Phục hồi có kiểm soát):
       - Khi Redis gặp sự cố, tự động kích hoạt bộ nhớ In-Memory RAM tạm thời trên FastAPI để chống bot,
         tuyệt đối không mở toang cửa để bot càn quét làm cháy quota Gemini.
"""

import time
import math
import uuid
import logging
from typing import Dict, Any, Tuple, Optional
from collections import defaultdict
import threading

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ==============================================================================
# HẰNG SỐ CẤU HÌNH MẶC ĐỊNH
# ==============================================================================
DEFAULT_STUDENT_RATE_LIMIT = 30       # 30 requests / phút / học sinh
GLOBAL_GEMINI_RPM_LIMIT = 14          # Tối đa 14 RPM toàn hệ thống (dành 1 RPM an toàn dưới trần 15 RPM)
DEFAULT_WINDOW_SECONDS = 60           # Cửa sổ trượt 60 giây (1 phút)
DEFAULT_SOCRATIC_COOLDOWN_SECONDS = 5.0 # Tối thiểu 5 giây giữa 2 câu hỏi liên tiếp


# ==============================================================================
# BỘ NHỚ RAM DỰ PHÒNG (CONTROLLED FAIL-OPEN IN-MEMORY CACHE)
# Sử dụng khi kết nối Redis gặp sự cố mạng hoặc offline
# ==============================================================================
class _InMemorySlidingWindow:
    """Bộ đếm sliding window trong RAM có Thread-Lock để bảo vệ khi Redis offline."""
    def __init__(self):
        self._lock = threading.Lock()
        self._history: Dict[str, list] = defaultdict(list)
        self._cooldowns: Dict[str, float] = {}

    def check_and_add(self, key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            # Loại bỏ các mốc thời gian ngoài cửa sổ trượt
            self._history[key] = [t for t in self._history[key] if t > cutoff]
            count = len(self._history[key])

            if count < limit:
                self._history[key].append(now)
                remaining = limit - (count + 1)
                return True, remaining, 0
            else:
                oldest = self._history[key][0] if self._history[key] else now
                retry_after = max(1, math.ceil(oldest + window_seconds - now))
                return False, 0, retry_after

    def set_cooldown(self, session_id: str, ts: float) -> None:
        with self._lock:
            self._cooldowns[session_id] = ts

    def get_cooldown(self, session_id: str) -> Optional[float]:
        with self._lock:
            return self._cooldowns.get(session_id)

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._cooldowns.clear()


_fallback_memory_limiter = _InMemorySlidingWindow()


# ==============================================================================
# CLASS DỊCH VỤ RATE LIMITER SERVICE
# ==============================================================================
class RateLimiterService:
    """Service kiểm soát lưu lượng và thực thi rate limiting cho hệ thống."""

    @staticmethod
    def build_rate_limit_headers(
        limit: int, 
        remaining: int, 
        retry_after: int, 
        reset_at: int
    ) -> Dict[str, str]:
        """
        Sinh ra bộ 4 HTTP Headers chuẩn hóa:
        - Retry-After (RFC 6585)
        - X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset (Industry Standard)
        """
        return {
            "Retry-After": str(max(1, retry_after)) if retry_after > 0 else "0",
            "X-RateLimit-Limit": str(max(0, limit)),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(reset_at),
        }

    @staticmethod
    def create_429_exception(
        reason: str,
        message: str,
        limit: int,
        remaining: int,
        retry_after: int,
        reset_at: int,
    ) -> HTTPException:
        """Tạo đối tượng HTTPException(429) chuẩn hóa với payload JSON và Response Headers."""
        headers = RateLimiterService.build_rate_limit_headers(
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
            reset_at=reset_at,
        )
        return HTTPException(
            status_code=429,
            detail={
                "error": "rate_limit_exceeded",
                "reason": reason,
                "message": message,
                "limit": limit,
                "remaining": remaining,
                "retry_after_seconds": retry_after,
                "reset_at": reset_at,
            },
            headers=headers,
        )

    # --------------------------------------------------------------------------
    # 1. THUẬT TOÁN REDIS SLIDING WINDOW LOG
    # --------------------------------------------------------------------------
    @classmethod
    async def check_sliding_window(
        cls,
        redis_client: Any,
        key: str,
        limit: int,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Kiểm tra và ghi nhận request theo thuật toán Redis Sliding Window Log (ZSET).
        
        Args:
            redis_client: Redis async connection
            key: Tên key Redis (ví dụ: 'ratelimit:student:usr-123:chat')
            limit: Số request tối đa được phép trong cửa sổ
            window_seconds: Kích thước cửa sổ trượt (mặc định 60 giây)

        Returns:
            Tuple[bool, Dict[str, Any]]: (is_allowed, info_dict)
            info_dict chứa: {allowed, limit, remaining, retry_after, reset_at, current_count}
        """
        now_ts = time.time()
        now_ms = int(now_ts * 1000)
        window_ms = window_seconds * 1000
        cutoff_ms = now_ms - window_ms
        unique_member = f"{now_ms}:{uuid.uuid4().hex[:6]}"

        try:
            # Bước 1: Dùng pipeline thực thi nguyên tử trên Redis
            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff_ms)              # Xóa các request cũ ngoài cửa sổ
            pipe.zcard(key)                                       # Đếm số request trong cửa sổ
            pipe.zrange(key, 0, 0, withscores=True)              # Lấy request cũ nhất để tính Retry-After
            results = await pipe.execute()

            current_count = int(results[1])
            oldest_entries = results[2]

            # Bước 2: Kiểm tra hạn mức
            if current_count < limit:
                # Vẫn còn hạn mức -> Cho qua và ghi nhận request mới
                pipe_add = redis_client.pipeline()
                pipe_add.zadd(key, {unique_member: now_ms})
                pipe_add.expire(key, window_seconds + 5)          # TTL tự xóa key khi không có request
                await pipe_add.execute()

                remaining = limit - (current_count + 1)
                reset_at = int(now_ts + window_seconds)
                return True, {
                    "allowed": True,
                    "limit": limit,
                    "remaining": remaining,
                    "retry_after": 0,
                    "reset_at": reset_at,
                    "current_count": current_count + 1,
                }
            else:
                # Đã chạm trần hạn mức -> Tính chính xác thời gian cần chờ
                if oldest_entries and len(oldest_entries) > 0:
                    oldest_score = float(oldest_entries[0][1])
                    retry_after = max(1, math.ceil((oldest_score + window_ms - now_ms) / 1000.0))
                    reset_at = int(math.ceil((oldest_score + window_ms) / 1000.0))
                else:
                    retry_after = window_seconds
                    reset_at = int(now_ts + window_seconds)

                return False, {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "retry_after": retry_after,
                    "reset_at": reset_at,
                    "current_count": current_count,
                }

        except Exception as e:
            # Cơ chế Controlled Fail-Open: Nếu Redis offline, kích hoạt In-Memory RAM Fallback
            logger.warning(
                f"[RateLimiter] Lỗi kết nối Redis ({e}), kích hoạt Controlled Fail-Open In-Memory cho key '{key}'"
            )
            is_allowed, rem, retry = _fallback_memory_limiter.check_and_add(
                key=key, limit=limit, window_seconds=window_seconds
            )
            return is_allowed, {
                "allowed": is_allowed,
                "limit": limit,
                "remaining": rem,
                "retry_after": retry,
                "reset_at": int(now_ts + (retry if retry > 0 else window_seconds)),
                "current_count": limit - rem,
                "fallback_mode": True,
            }

    # --------------------------------------------------------------------------
    # 2. GIỚI HẠN TOÀN HỆ THỐNG CHO GEMINI API (GLOBAL SYSTEM LIMIT)
    # --------------------------------------------------------------------------
    @classmethod
    async def check_global_system_limit(
        cls,
        redis_client: Any,
        global_limit: int = GLOBAL_GEMINI_RPM_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Kiểm tra tổng lưu lượng gọi Gemini trên toàn hệ thống (Max 14 RPM).
        Bảo vệ sống còn cho Google Gemini Free Tier khi có nhiều học sinh cùng vào học.
        """
        key = "ratelimit:global:gemini_chat"
        return await cls.check_sliding_window(
            redis_client=redis_client,
            key=key,
            limit=global_limit,
            window_seconds=window_seconds,
        )

    # --------------------------------------------------------------------------
    # 3. QUY TẮC SƯ PHẠM SOCRATIC COOL-DOWN (Tối thiểu 5 giây)
    # --------------------------------------------------------------------------
    @classmethod
    async def check_socratic_cooldown(
        cls,
        redis_client: Any,
        session_id: str,
        cooldown_seconds: float = DEFAULT_SOCRATIC_COOLDOWN_SECONDS,
    ) -> Tuple[bool, int, float]:
        """
        Kiểm tra khoảng cách thời gian từ lúc AI hoàn tất câu trả lời gần nhất.
        
        Returns:
            Tuple[bool, int, float]: (is_allowed, retry_after_seconds, delta_t_seconds)
            - is_allowed = True: Đã qua đủ 5 giây, cho phép gửi tiếp.
            - is_allowed = False: Chưa đủ 5 giây, trả về số giây cần chờ thêm.
        """
        key = f"cooldown:session:{session_id}:last_done"
        now_ts = time.time()

        try:
            val = None
            if redis_client is not None:
                try:
                    val = await redis_client.get(key)
                except Exception:
                    val = None

            # Nếu Redis không có hoặc lỗi -> kiểm tra in-memory fallback
            if not val:
                mem_ts = _fallback_memory_limiter.get_cooldown(session_id)
                if mem_ts is not None:
                    val = str(mem_ts)

            if not val:
                # Chưa từng có câu trả lời nào trước đó (câu đầu tiên của session) -> Cho qua
                return True, 0, 999.0

            last_done_ts = float(val)
            delta_t = now_ts - last_done_ts

            if delta_t < cooldown_seconds:
                retry_after = max(1, math.ceil(cooldown_seconds - delta_t))
                return False, retry_after, delta_t

            return True, 0, delta_t

        except Exception as e:
            logger.warning(f"[RateLimiter] Lỗi đọc cool-down ({e}), cho qua (fail-open an toàn)")
            return True, 0, 999.0

    @classmethod
    async def record_ai_completion(
        cls,
        redis_client: Any,
        session_id: str,
        ttl_seconds: int = 120,
    ) -> None:
        """
        Ghi nhận mốc thời gian hoàn tất sinh chuỗi (Stream [DONE]) của AI vào Redis (Async).
        Mốc này là căn cứ để tính 5 giây Socratic Cool-Down cho câu hỏi tiếp theo.
        """
        key = f"cooldown:session:{session_id}:last_done"
        now_ts = time.time()
        # Luôn lưu vào in-memory fallback
        _fallback_memory_limiter.set_cooldown(session_id, now_ts)

        if redis_client is not None:
            try:
                await redis_client.set(key, str(now_ts), ex=ttl_seconds)
                logger.debug(f"[RateLimiter] Async recorded AI completion cho session '{session_id}' tại {now_ts}")
            except Exception as e:
                logger.warning(f"[RateLimiter] Không thể ghi completion timestamp vào Redis: {e}")

    @classmethod
    def record_ai_completion_sync(
        cls,
        session_id: str,
        ttl_seconds: int = 120,
    ) -> None:
        """
        Ghi nhận đồng bộ mốc hoàn tất của AI (dùng trong finally block của StreamingResponse).
        Hỗ trợ cả Sync Redis Client lẫn In-Memory Fallback.
        """
        now_ts = time.time()
        # 1. Luôn cập nhật in-memory cache ngay lập tức
        _fallback_memory_limiter.set_cooldown(session_id, now_ts)

        # 2. Cố gắng ghi vào Redis đồng bộ qua _get_sync_redis()
        try:
            from services.system_config_service import _get_sync_redis
            client = _get_sync_redis()
            if client is not None:
                key = f"cooldown:session:{session_id}:last_done"
                client.set(key, str(now_ts), ex=ttl_seconds)
        except Exception as err:
            logger.debug(f"[RateLimiter] Sync record cool-down fallback to RAM: {err}")

    @classmethod
    def reset_in_memory_state(cls) -> None:
        """Xóa sạch cache trong RAM phục vụ viết Unit Test."""
        _fallback_memory_limiter.reset()
