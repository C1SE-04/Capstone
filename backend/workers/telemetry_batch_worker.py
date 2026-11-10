"""
US 10.2 - Telemetry Batch Worker: Redis Counters (T10.2.3)
===========================================================
Tiêu thụ telemetry_queue và cập nhật các bộ đếm tức thời trên Upstash Redis:
  - rpm:{minute}            : Số request mỗi phút (window phút hiện tại, TTL 90 phút)
  - tpm:{minute}            : Số token mỗi phút
  - errors:5xx:{minute}     : Số lỗi HTTP 5xx mỗi phút

Mỗi key được đặt TTL = 90 phút (5400s) để tự dọn dẹp trên Upstash.

Cách tích hợp trong main.py (startup_event):
    from workers.telemetry_batch_worker import start_telemetry_worker
    asyncio.create_task(start_telemetry_worker())
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from upstash_redis.asyncio import Redis

from middleware.telemetry_middleware import telemetry_queue

load_dotenv()

# TTL của counter key trên Redis: 90 phút (đủ bao quát 1 giờ + buffer)
_COUNTER_TTL_SECONDS = 5400  # 90 phút

# Chu kỳ kiểm tra queue: 1 giây
_POLL_INTERVAL_SECONDS = 1.0


def _get_upstash_redis() -> Optional[Redis]:
    """
    Khởi tạo Upstash Redis REST client từ biến môi trường.
    Trả về None nếu thiếu cấu hình (fail-safe).
    """
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

    if not rest_url or not rest_token:
        print("[TelemetryWorker] CẢNH BÁO: Thiếu UPSTASH_REDIS_REST_URL / TOKEN — counters sẽ bị bỏ qua.")
        return None

    return Redis(url=rest_url, token=rest_token, allow_telemetry=False)


def _minute_bucket() -> str:
    """
    Trả về chuỗi mốc phút hiện tại dạng YYYY-MM-DDTHH:MM (UTC).
    Dùng làm suffix cho Redis key: rpm:2026-11-09T14:35
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M")


async def _flush_events(redis: Optional[Redis], events: list[dict]) -> None:
    """
    Xử lý một batch events từ telemetry_queue và cập nhật Redis counters.

    Hai loại event:
      - latency/status event (từ TelemetryMiddleware):
            {"latency_ms": int, "status_code": int, "endpoint_group": str}
      - token_usage event (từ gemini_telemetry.py):
            {"type": "token_usage", "prompt_tokens": int, "completion_tokens": int, "total_tokens": int, ...}
    """
    if not events:
        return

    minute = _minute_bucket()
    rpm_key = f"rpm:{minute}"
    tpm_key = f"tpm:{minute}"
    err5xx_key = f"errors:5xx:{minute}"

    rpm_delta = 0
    tpm_delta = 0
    err5xx_delta = 0

    for ev in events:
        event_type = ev.get("type")

        if event_type == "token_usage":
            # Cộng dồn token vào TPM counter
            tpm_delta += ev.get("total_tokens", 0)

        else:
            # HTTP request event từ TelemetryMiddleware
            rpm_delta += 1
            status = ev.get("status_code", 200)
            if status >= 500:
                err5xx_delta += 1

    # Ghi lên Upstash Redis — fail-safe: bắt exception không để crash worker
    if redis is None:
        return

    try:
        if rpm_delta > 0:
            await redis.incrby(rpm_key, rpm_delta)
            await redis.expire(rpm_key, _COUNTER_TTL_SECONDS)

        if tpm_delta > 0:
            await redis.incrby(tpm_key, tpm_delta)
            await redis.expire(tpm_key, _COUNTER_TTL_SECONDS)

        if err5xx_delta > 0:
            await redis.incrby(err5xx_key, err5xx_delta)
            await redis.expire(err5xx_key, _COUNTER_TTL_SECONDS)

    except Exception as err:
        # Lỗi mạng Upstash: ghi log cảnh báo nhẹ, không làm crash worker
        print(f"[TelemetryWorker] Lỗi khi ghi Redis: {err}")


async def start_telemetry_worker() -> None:
    """
    Background coroutine tiêu thụ telemetry_queue và cập nhật Redis counters.
    Chạy vô tận; bỏ qua mọi lỗi đơn lẻ để không ảnh hưởng hoạt động hệ thống.

    Gọi từ startup_event của FastAPI:
        asyncio.create_task(start_telemetry_worker())
    """
    redis = _get_upstash_redis()
    print("[TelemetryWorker] ✅ Đã khởi động Telemetry Batch Worker.")

    while True:
        try:
            # Gom tối đa 100 events mỗi chu kỳ để tránh ngốn CPU
            batch: list[dict] = []
            while len(batch) < 100:
                try:
                    event = telemetry_queue.get_nowait()
                    batch.append(event)
                except asyncio.QueueEmpty:
                    break

            if batch:
                await _flush_events(redis, batch)

        except Exception as err:
            # Lỗi ngoài ý muốn: ghi log và tiếp tục vòng lặp
            print(f"[TelemetryWorker] Lỗi không xác định: {err}")

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)

