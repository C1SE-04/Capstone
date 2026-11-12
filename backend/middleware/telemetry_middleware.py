"""
US 10.2 - Telemetry Middleware (T10.2.1)
=========================================
Thu thập vi mô bất đồng bộ cho mỗi HTTP request đi qua FastAPI:
  - Thời gian End-to-End (latency_ms)
  - Mã HTTP status code
  - Route endpoint (path)
  - Phân loại vào nhóm: chat | eval | auth | other

Dữ liệu được đẩy vào asyncio.Queue để TelemetryBatchWorker (T10.2.3) gom và
ghi vào Redis + DB mà không làm chậm luồng phản hồi học sinh dù 1ms.

Cách tích hợp trong main.py:
    from middleware.telemetry_middleware import TelemetryMiddleware
    app.add_middleware(TelemetryMiddleware)
"""

import time
import asyncio
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Hàng đợi bất đồng bộ chia sẻ trong process — dung lượng tối đa 10.000 bản ghi.
# Nếu đầy, event mới sẽ bị bỏ qua (không block request chính).
telemetry_queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)

# Biến đếm số phiên streaming SSE active thời gian thực
_active_sse_sessions: int = 0


def increment_sse_session():
    global _active_sse_sessions
    _active_sse_sessions += 1
    try:
        telemetry_queue.put_nowait({
            "type": "sse_peak",
            "active_sessions": _active_sse_sessions,
        })
    except Exception:
        pass


def decrement_sse_session():
    global _active_sse_sessions
    if _active_sse_sessions > 0:
        _active_sse_sessions -= 1


def get_active_sse_sessions() -> int:
    return max(0, _active_sse_sessions)


def push_cache_event(hit: bool):
    """Ghi nhận sự kiện Redis Cache Hit / Miss vào queue bất đồng bộ."""
    try:
        telemetry_queue.put_nowait({
            "type": "cache_event",
            "hit": bool(hit),
        })
    except Exception:
        pass


def push_failover_event(is_429: bool = False):
    """Ghi nhận sự kiện chuyển sang model Dự phòng (Failover)."""
    try:
        telemetry_queue.put_nowait({
            "type": "failover",
            "is_429": bool(is_429),
        })
    except Exception:
        pass


def push_error_429_event():
    """Ghi nhận sự kiện lỗi Gemini 429 Quota / Rate limit."""
    try:
        telemetry_queue.put_nowait({
            "type": "error_429",
        })
    except Exception:
        pass


def _classify_endpoint(path: str) -> str:
    """
    Phân loại đường dẫn API vào 4 nhóm phục vụ thống kê biểu đồ cột.
    Trả về một trong: 'chat' | 'eval' | 'auth' | 'other'
    """
    if path == "/chat" or path.startswith("/chat/"):
        return "chat"
    if path.startswith("/independence"):
        return "eval"
    if path.startswith("/auth"):
        return "auth"
    return "other"


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware đo lường hiệu năng mỗi HTTP request.

    Chỉ ghi nhận các request thực sự (bỏ qua preflight OPTIONS và
    các path hạ tầng như /docs, /health, /openapi.json).

    Mỗi request hoàn tất sẽ đẩy 1 dict vào telemetry_queue:
        {
            "latency_ms": int,       # Tổng thời gian End-to-End (ms)
            "status_code": int,      # HTTP status code (200, 400, 500, ...)
            "endpoint_group": str,   # 'chat' | 'eval' | 'auth' | 'other'
        }
    """

    # Các path hạ tầng không cần đo lường
    _SKIP_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/health"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Bỏ qua preflight CORS và path hạ tầng
        if request.method == "OPTIONS" or path in self._SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Ghi nhận telemetry event bất đồng bộ — không block nếu queue đầy
        event = {
            "latency_ms": latency_ms,
            "status_code": response.status_code,
            "endpoint_group": _classify_endpoint(path),
        }
        try:
            telemetry_queue.put_nowait(event)
        except asyncio.QueueFull:
            # Queue đầy: bỏ qua event này, không làm ảnh hưởng response
            pass

        return response

