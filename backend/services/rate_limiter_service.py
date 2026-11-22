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

from fastapi import HTTPException, Request

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
        self._login_failures: Dict[str, Tuple[int, float]] = {}  # key -> (count, expire_at)
        self._lockouts: Dict[str, float] = {}                    # key -> expire_at

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

    def get_lockout(self, key: str) -> Optional[int]:
        now = time.time()
        with self._lock:
            expire_at = self._lockouts.get(key)
            if expire_at and expire_at > now:
                return max(1, math.ceil(expire_at - now))
            elif expire_at:
                del self._lockouts[key]
            return None

    def set_lockout(self, key: str, duration_seconds: int) -> None:
        with self._lock:
            self._lockouts[key] = time.time() + duration_seconds

    def record_failure(self, key: str, window_seconds: int = 900) -> int:
        now = time.time()
        with self._lock:
            curr = self._login_failures.get(key)
            if curr and curr[1] > now:
                new_count = curr[0] + 1
                self._login_failures[key] = (new_count, curr[1])
                return new_count
            else:
                self._login_failures[key] = (1, now + window_seconds)
                return 1

    def clear_key(self, key: str) -> None:
        with self._lock:
            self._login_failures.pop(key, None)
            self._lockouts.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._history.clear()
            self._cooldowns.clear()
            self._login_failures.clear()
            self._lockouts.clear()


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

    # --------------------------------------------------------------------------
    # 4. CHỐNG TẤN CÔNG DÒ MẬT KHẨU ĐA TẦNG (ANTI-BRUTE-FORCE 3 LỚP) - TASK #360
    # --------------------------------------------------------------------------
    MAX_LOGIN_ATTEMPTS = 5             # Tối đa 5 lần thử sai theo (Username + IP)
    LOGIN_LOCKOUT_SECONDS = 180        # Tạm khóa 3 phút (180s) theo yêu cầu người dùng
    MAX_FAILED_LOGINS_PER_IP = 20      # Tối đa 20 lần thử sai từ 1 IP trên toàn hệ thống
    IP_LOCKOUT_SECONDS = 1800          # Tạm khóa IP 30 phút (1800s)
    MULTI_IP_FAILURE_THRESHOLD = 10    # Ngưỡng phát hiện botnet xoay IP

    @staticmethod
    def extract_client_ip(request: Optional[Request]) -> str:
        """
        Trích xuất client IP an toàn từ Request headers (X-Real-IP, X-Forwarded-For) hoặc TCP host.
        Khắc phục triệt để lỗ hổng IP Spoofing qua reverse proxy.
        """
        if not request:
            return "127.0.0.1"

        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip and x_real_ip.strip():
            return x_real_ip.strip()

        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for and x_forwarded_for.strip():
            first_ip = x_forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip

        if request.client and request.client.host:
            return request.client.host

        return "127.0.0.1"

    @classmethod
    async def check_login_lockout(
        cls,
        redis_client: Any,
        username: str,
        client_ip: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Kiểm tra xem máy hoặc tài khoản có đang trong thời gian bị tạm khóa hay không.
        Kiểm tra 2 cấp:
        - Cấp 1: Toàn bộ IP có bị khóa do càn quét nhiều tài khoản không (auth:lockout_ip:{client_ip})
        - Cấp 2: Cặp (Username + IP) có bị khóa không (auth:lockout:{username}:{client_ip})

        Returns:
            Tuple[bool, Optional[Dict[str, Any]]]: (is_locked, lockout_info)
        """
        now_ts = time.time()
        normalized_user = username.lower().strip()
        ip_lock_key = f"auth:lockout_ip:{client_ip}"
        user_ip_lock_key = f"auth:lockout:{normalized_user}:{client_ip}"

        try:
            if redis_client is not None:
                # 1. Kiểm tra khóa IP toàn cục
                ip_ttl = await redis_client.ttl(ip_lock_key)
                if ip_ttl and ip_ttl > 0:
                    minutes = math.ceil(ip_ttl / 60)
                    return True, {
                        "reason": "IP_LOCKOUT",
                        "message": (
                            f"Địa chỉ mạng này tạm thời bị khóa do có quá nhiều lần đăng nhập thất bại. "
                            f"Vui lòng thử lại sau {minutes} phút ({ip_ttl} giây)."
                        ),
                        "retry_after": ip_ttl,
                        "reset_at": int(now_ts + ip_ttl),
                    }

                # 2. Kiểm tra khóa cặp (Username + IP)
                user_ip_ttl = await redis_client.ttl(user_ip_lock_key)
                if user_ip_ttl and user_ip_ttl > 0:
                    minutes = math.ceil(user_ip_ttl / 60)
                    return True, {
                        "reason": "AUTH_BRUTE_FORCE",
                        "message": (
                            f"Tài khoản '{username}' tạm thời bị khóa trên thiết bị này do nhập sai mật khẩu 5 lần. "
                            f"Vui lòng thử lại sau {minutes} phút ({user_ip_ttl} giây)."
                        ),
                        "retry_after": user_ip_ttl,
                        "reset_at": int(now_ts + user_ip_ttl),
                    }
        except Exception as e:
            logger.warning(f"[RateLimiter] Lỗi đọc Redis lockout ({e}), kiểm tra RAM fallback")

        # Fallback RAM (Fail-Closed cho Auth để đảm bảo an ninh máy chủ)
        ip_ram_ttl = _fallback_memory_limiter.get_lockout(ip_lock_key)
        if ip_ram_ttl is not None and ip_ram_ttl > 0:
            return True, {
                "reason": "IP_LOCKOUT",
                "message": f"Địa chỉ mạng tạm thời bị khóa. Vui lòng thử lại sau {ip_ram_ttl} giây.",
                "retry_after": ip_ram_ttl,
                "reset_at": int(now_ts + ip_ram_ttl),
            }

        user_ram_ttl = _fallback_memory_limiter.get_lockout(user_ip_lock_key)
        if user_ram_ttl is not None and user_ram_ttl > 0:
            return True, {
                "reason": "AUTH_BRUTE_FORCE",
                "message": f"Tài khoản '{username}' tạm thời bị khóa. Vui lòng thử lại sau {user_ram_ttl} giây.",
                "retry_after": user_ram_ttl,
                "reset_at": int(now_ts + user_ram_ttl),
            }

        return False, None

    @classmethod
    async def record_login_failure(
        cls,
        redis_client: Any,
        username: str,
        client_ip: str,
    ) -> Dict[str, Any]:
        """
        Ghi nhận một lần đăng nhập sai và cập nhật bộ đếm phòng thủ 3 lớp.
        Returns:
            Dict: {is_locked, reason, message, remaining_attempts, retry_after, reset_at, progressive_delay}
        """
        now_ts = time.time()
        normalized_user = username.lower().strip()
        ip_fail_key = f"auth:failed_ip:{client_ip}"
        ip_lock_key = f"auth:lockout_ip:{client_ip}"
        user_ip_fail_key = f"auth:failed:{normalized_user}:{client_ip}"
        user_ip_lock_key = f"auth:lockout:{normalized_user}:{client_ip}"
        user_global_fail_key = f"auth:failed_user:{normalized_user}"

        try:
            if redis_client is not None:
                # Lớp 2: Kiểm tra tổng số lần sai từ IP này trên mọi tài khoản
                ip_fails = await redis_client.incr(ip_fail_key)
                if ip_fails == 1:
                    await redis_client.expire(ip_fail_key, cls.LOGIN_LOCKOUT_SECONDS)
                if ip_fails >= cls.MAX_FAILED_LOGINS_PER_IP:
                    await redis_client.set(ip_lock_key, "1", ex=cls.IP_LOCKOUT_SECONDS)
                    return {
                        "is_locked": True,
                        "reason": "IP_LOCKOUT",
                        "message": (
                            f"Địa chỉ IP của bạn đã bị khóa trong {cls.IP_LOCKOUT_SECONDS // 60} phút "
                            f"do có hơn {cls.MAX_FAILED_LOGINS_PER_IP} lần đăng nhập sai."
                        ),
                        "retry_after": cls.IP_LOCKOUT_SECONDS,
                        "reset_at": int(now_ts + cls.IP_LOCKOUT_SECONDS),
                        "remaining_attempts": 0,
                        "progressive_delay": False,
                    }

                # Lớp 3: Theo dõi số lần sai của tài khoản này từ mọi IP (không khóa cứng, phát hiện xoay proxy)
                user_global_fails = await redis_client.incr(user_global_fail_key)
                if user_global_fails == 1:
                    await redis_client.expire(user_global_fail_key, 600)
                apply_progressive_delay = (user_global_fails >= cls.MULTI_IP_FAILURE_THRESHOLD)

                # Lớp 1: Đếm số lần sai theo cặp (Username + IP)
                user_ip_fails = await redis_client.incr(user_ip_fail_key)
                if user_ip_fails == 1:
                    await redis_client.expire(user_ip_fail_key, cls.LOGIN_LOCKOUT_SECONDS)

                if user_ip_fails >= cls.MAX_LOGIN_ATTEMPTS:
                    await redis_client.set(user_ip_lock_key, "1", ex=cls.LOGIN_LOCKOUT_SECONDS)
                    _fallback_memory_limiter.set_lockout(user_ip_lock_key, cls.LOGIN_LOCKOUT_SECONDS)
                    return {
                        "is_locked": True,
                        "reason": "AUTH_BRUTE_FORCE",
                        "message": (
                            f"Bạn đã nhập sai mật khẩu {cls.MAX_LOGIN_ATTEMPTS} lần liên tiếp. "
                            f"Tài khoản tạm thời bị khóa trong {cls.LOGIN_LOCKOUT_SECONDS // 60} phút."
                        ),
                        "retry_after": cls.LOGIN_LOCKOUT_SECONDS,
                        "reset_at": int(now_ts + cls.LOGIN_LOCKOUT_SECONDS),
                        "remaining_attempts": 0,
                        "progressive_delay": apply_progressive_delay,
                    }
                else:
                    remaining = cls.MAX_LOGIN_ATTEMPTS - user_ip_fails
                    return {
                        "is_locked": False,
                        "reason": "INVALID_CREDENTIALS",
                        "message": (
                            f"Tên tài khoản/email hoặc mật khẩu không đúng. "
                            f"Bạn còn {remaining} lần thử trước khi bị tạm khóa {cls.LOGIN_LOCKOUT_SECONDS // 60} phút."
                        ),
                        "remaining_attempts": remaining,
                        "retry_after": 0,
                        "reset_at": 0,
                        "progressive_delay": apply_progressive_delay,
                    }
        except Exception as e:
            logger.warning(f"[RateLimiter] Lỗi ghi nhận thất bại vào Redis ({e}), chuyển sang RAM fallback")

        # Fallback RAM
        ram_fails = _fallback_memory_limiter.record_failure(user_ip_fail_key, cls.LOGIN_LOCKOUT_SECONDS)
        if ram_fails >= cls.MAX_LOGIN_ATTEMPTS:
            _fallback_memory_limiter.set_lockout(user_ip_lock_key, cls.LOGIN_LOCKOUT_SECONDS)
            return {
                "is_locked": True,
                "reason": "AUTH_BRUTE_FORCE",
                "message": f"Bạn đã nhập sai mật khẩu 5 lần. Tài khoản tạm khóa {cls.LOGIN_LOCKOUT_SECONDS // 60} phút.",
                "retry_after": cls.LOGIN_LOCKOUT_SECONDS,
                "reset_at": int(now_ts + cls.LOGIN_LOCKOUT_SECONDS),
                "remaining_attempts": 0,
                "progressive_delay": False,
            }
        else:
            remaining = cls.MAX_LOGIN_ATTEMPTS - ram_fails
            return {
                "is_locked": False,
                "reason": "INVALID_CREDENTIALS",
                "message": f"Tên tài khoản hoặc mật khẩu không đúng. Còn {remaining} lần thử.",
                "remaining_attempts": remaining,
                "retry_after": 0,
                "reset_at": 0,
                "progressive_delay": False,
            }

    @classmethod
    async def clear_login_failures(
        cls,
        redis_client: Any,
        username: str,
        client_ip: str,
    ) -> None:
        """
        Xóa sạch lịch sử thử sai của cặp (Username + IP) khi đăng nhập thành công.
        """
        normalized_user = username.lower().strip()
        user_ip_fail_key = f"auth:failed:{normalized_user}:{client_ip}"
        user_ip_lock_key = f"auth:lockout:{normalized_user}:{client_ip}"

        try:
            if redis_client is not None:
                await redis_client.delete(user_ip_fail_key, user_ip_lock_key)
        except Exception as e:
            logger.warning(f"[RateLimiter] Lỗi xóa key sau login thành công: {e}")

        _fallback_memory_limiter.clear_key(user_ip_fail_key)
        _fallback_memory_limiter.clear_key(user_ip_lock_key)

    @classmethod
    def reset_in_memory_state(cls) -> None:
        """Xóa sạch cache trong RAM phục vụ viết Unit Test."""
        _fallback_memory_limiter.reset()
