"""
US 10.2 - Telemetry: Thu thập Token Usage & TTFT từ Gemini (T10.2.2)
======================================================================
Module này cung cấp các hàm wrapper để gọi Gemini API và tự động
ghi nhận:
  - prompt_tokens, completion_tokens (từ response.usage_metadata)
  - TTFT – Time To First Token (ms, chỉ áp dụng cho streaming)

Dữ liệu được đẩy vào telemetry_queue để TelemetryBatchWorker gom ghi
Redis và DB mà không làm chậm luồng phản hồi học sinh.

Cách dùng trong router.py:
    from middleware.telemetry_middleware import telemetry_queue
    from middleware.gemini_telemetry import stream_with_telemetry, generate_with_telemetry
"""

import time
import asyncio
from typing import Generator, Any, Optional

from middleware.telemetry_middleware import telemetry_queue


# Giá tiền mỗi 1 triệu token theo bảng giá Gemini API thực tế (USD)
# Nguồn: https://ai.google.dev/gemini-api/docs/models/gemini#gemini-2.5-flash
_MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {
        "prompt": 0.075,       # USD / 1M prompt tokens
        "completion": 0.30,    # USD / 1M completion tokens
    },
    "gemini-2.0-flash": {
        "prompt": 0.075,
        "completion": 0.30,
    },
    "gemini-2.0-flash-lite": {
        "prompt": 0.0375,
        "completion": 0.15,
    },
    "gemini-1.5-pro": {
        "prompt": 1.25,
        "completion": 5.00,
    },
    # Fallback cho các model không có trong bảng
    "default": {
        "prompt": 0.075,
        "completion": 0.30,
    },
}


def _calc_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str,
) -> float:
    """
    Tính chi phí API ước tính (USD) dựa trên số token và model.
    Làm tròn 6 chữ số thập phân.
    """
    pricing = _MODEL_PRICING.get(model_name, _MODEL_PRICING["default"])
    cost = (
        (prompt_tokens / 1_000_000) * pricing["prompt"]
        + (completion_tokens / 1_000_000) * pricing["completion"]
    )
    return round(cost, 6)


def _push_token_event(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str,
    agent_name: str,
    ttft_ms: Optional[int] = None,
) -> None:
    """
    Đẩy sự kiện token usage vào telemetry_queue bất đồng bộ.
    Không làm block nếu queue đầy.
    """
    cost_usd = _calc_cost_usd(prompt_tokens, completion_tokens, model_name)

    event = {
        "type": "token_usage",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": cost_usd,
        "model_name": model_name,
        "agent_name": agent_name,   # 'Chat' | 'Classifier' | 'Flashcard' | 'ParentReport' | 'Email' | 'Fallback'
        "ttft_ms": ttft_ms,         # None nếu là non-streaming
    }
    try:
        telemetry_queue.put_nowait(event)
    except Exception:
        # Queue đầy hoặc lỗi bất ngờ: im lặng, không làm ảnh hưởng luồng chat
        pass


def stream_with_telemetry(
    model: Any,
    call_payload: Any,
    model_name: str,
    agent_name: str,
) -> Generator[str, None, None]:
    """
    Wrapper cho model.generate_content(stream=True).

    Đo TTFT (thời gian nhận được chunk chữ đầu tiên) và thu thập
    usage_metadata sau khi stream kết thúc, rồi đẩy vào telemetry_queue.

    Trả về generator text chunk giống hệt gọi Gemini stream thông thường.

    Ví dụ dùng trong router.py:
        for chunk_text in stream_with_telemetry(model, call_payload, model_name, "Chat"):
            yield chunk_text
    """
    start_time = time.perf_counter()
    ttft_ms: Optional[int] = None
    prompt_tokens = 0
    completion_tokens = 0

    response = model.generate_content(call_payload, stream=True)

    for chunk in response:
        # Đo TTFT tại chunk chữ đầu tiên có nội dung thực
        if ttft_ms is None and chunk.text:
            ttft_ms = int((time.perf_counter() - start_time) * 1000)

        if chunk.text:
            yield chunk.text

    # Sau khi stream kết thúc, đọc usage_metadata
    # Gemini SDK tích lũy metadata vào response.usage_metadata sau khi stream xong
    try:
        meta = response.usage_metadata
        if meta:
            prompt_tokens = meta.prompt_token_count or 0
            completion_tokens = meta.candidates_token_count or 0
    except Exception:
        pass

    _push_token_event(prompt_tokens, completion_tokens, model_name, agent_name, ttft_ms)


def generate_with_telemetry(
    model: Any,
    call_payload: Any,
    model_name: str,
    agent_name: str,
) -> Any:
    """
    Wrapper cho model.generate_content(stream=False).

    Thu thập usage_metadata và đẩy vào telemetry_queue.
    Trả về response object gốc để caller dùng bình thường.

    Ví dụ dùng trong router.py:
        response = generate_with_telemetry(model, call_payload, model_name, "Chat")
        text = response.text
    """
    response = model.generate_content(call_payload, stream=False)

    prompt_tokens = 0
    completion_tokens = 0
    try:
        meta = response.usage_metadata
        if meta:
            prompt_tokens = meta.prompt_token_count or 0
            completion_tokens = meta.candidates_token_count or 0
    except Exception:
        pass

    _push_token_event(prompt_tokens, completion_tokens, model_name, agent_name, ttft_ms=None)

    return response

