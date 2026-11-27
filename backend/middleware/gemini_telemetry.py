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

from middleware.telemetry_middleware import telemetry_queue, push_error_429_event


def _is_429_exception(err: Exception) -> bool:
    """Kiểm tra ngoại lệ có phải lỗi rate-limit / quota 429 từ Gemini hay không."""
    if getattr(err, "code", None) == 429:
        return True
    err_str = str(err).lower()
    return (
        "429" in err_str
        or "resource_exhausted" in err_str
        or "resourceexhausted" in err_str
        or "quota" in err_str
    )


def extract_finish_reason(response_or_chunk: Any) -> Optional[int]:
    """
    Trích xuất mã finish_reason từ Gemini response hoặc stream chunk.
    An toàn với MagicMock, FakeChunk, FakeStreamResponse không có candidates.
    Trả về int (VD: 1=STOP, 2=MAX_TOKENS, 3=SAFETY) hoặc None.
    """
    if response_or_chunk is None:
        return None
    try:
        candidates = getattr(response_or_chunk, "candidates", None)
        if not candidates or not hasattr(candidates, "__getitem__"):
            return None
        first = candidates[0]
        if first is None:
            return None
        fr = getattr(first, "finish_reason", None)
        if fr is None or isinstance(fr, bool):
            return None
        if isinstance(fr, int):
            return fr
        fr_val = getattr(fr, "value", None)
        if isinstance(fr_val, int) and not isinstance(fr_val, bool):
            return fr_val
        fr_name = getattr(fr, "name", None)
        if isinstance(fr_name, str):
            name_up = fr_name.upper()
            if "MAX_TOKENS" in name_up:
                return 2
            if "STOP" in name_up:
                return 1
            if "SAFETY" in name_up:
                return 3
        if isinstance(fr, str):
            s_up = fr.strip().upper()
            if s_up.isdigit():
                return int(s_up)
            if "MAX_TOKENS" in s_up:
                return 2
            if "STOP" in s_up:
                return 1
            if "SAFETY" in s_up:
                return 3
    except Exception:
        return None
    return None


def _safe_chunk_text(chunk: Any) -> str:
    """Đọc chunk.text an toàn, tránh ValueError khi chunk cuối MAX_TOKENS không có text part."""
    try:
        txt = chunk.text
        if txt is None:
            return ""
        return txt if isinstance(txt, str) else str(txt)
    except Exception:
        return ""


# Giá tiền mỗi 1 triệu token theo bảng giá Gemini API thực tế (USD)
# Nguồn: https://ai.google.dev/gemini-api/docs/models/gemini#gemini-2.5-flash
_MODEL_PRICING: dict[str, dict[str, float]] = {
    # ── Bộ Model Hiện Hành (US 10.3 - 6 Phân Hệ) ─────────────────────────────
    "gemini-3.8-flash": {
        "prompt": 0.10,        # USD / 1M prompt tokens (Chat Socratic chính)
        "completion": 0.40,    # USD / 1M completion tokens
    },
    "gemini-3.5-flash": {
        "prompt": 0.075,       # USD / 1M prompt tokens (Báo cáo phụ huynh)
        "completion": 0.30,
    },
    "gemini-3.5-flash-lite": {
        "prompt": 0.0375,      # USD / 1M prompt tokens (Flashcard & Dự phòng)
        "completion": 0.15,
    },
    "gemini-3.1-flash-lite": {
        "prompt": 0.030,       # USD / 1M prompt tokens (Classifier & Email - siêu tiết kiệm)
        "completion": 0.12,
    },
    # ── Các Model Dự Phòng & Phiên Bản LTS ───────────────────────────────────
    "gemini-2.5-flash": {
        "prompt": 0.075,
        "completion": 0.30,
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
    finish_reason: Optional[int] = None,
) -> None:
    """
    Đẩy sự kiện token usage vào telemetry_queue bất đồng bộ.
    Không làm block nếu queue đầy.
    """
    cost_usd = _calc_cost_usd(prompt_tokens, completion_tokens, model_name)

    if finish_reason == 2:
        print(f"[GeminiTelemetry] ⚠️ MAX_TOKENS (finish_reason=2) | model={model_name} | agent={agent_name}")

    event = {
        "type": "token_usage",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": cost_usd,
        "model_name": model_name,
        "agent_name": agent_name,   # 'Chat' | 'Classifier' | 'Flashcard' | 'ParentReport' | 'Email' | 'Fallback'
        "ttft_ms": ttft_ms,         # None nếu là non-streaming
        "finish_reason": finish_reason,
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
    telemetry_meta: Optional[dict] = None,
    **kwargs: Any,
) -> Generator[str, None, None]:
    """
    Wrapper cho model.generate_content(stream=True).

    Đo TTFT (thời gian nhận được chunk chữ đầu tiên) và thu thập
    usage_metadata + finish_reason sau khi stream kết thúc, rồi đẩy vào telemetry_queue.

    Trả về generator text chunk giống hệt gọi Gemini stream thông thường.
    """
    start_time = time.perf_counter()
    ttft_ms: Optional[int] = None
    prompt_tokens = 0
    completion_tokens = 0
    finish_reason: Optional[int] = None

    try:
        kwargs.setdefault("request_options", {"timeout": 30, "retry": None})
        response = model.generate_content(call_payload, stream=True, **kwargs)

        for chunk in response:
            chunk_fr = extract_finish_reason(chunk)
            if chunk_fr is not None:
                finish_reason = chunk_fr

            chunk_text = _safe_chunk_text(chunk)
            # Đo TTFT tại chunk chữ đầu tiên có nội dung thực
            if ttft_ms is None and chunk_text:
                ttft_ms = int((time.perf_counter() - start_time) * 1000)

            if chunk_text:
                yield chunk_text

        if finish_reason is None:
            finish_reason = extract_finish_reason(response)

        if telemetry_meta is not None:
            telemetry_meta["finish_reason"] = finish_reason

        # Sau khi stream kết thúc, đọc usage_metadata
        # Gemini SDK tích lũy metadata vào response.usage_metadata sau khi stream xong
        try:
            meta = response.usage_metadata
            if meta:
                prompt_tokens = meta.prompt_token_count or 0
                completion_tokens = meta.candidates_token_count or 0
        except Exception:
            pass

        _push_token_event(
            prompt_tokens,
            completion_tokens,
            model_name,
            agent_name,
            ttft_ms,
            finish_reason=finish_reason,
        )
    except Exception as err:
        if _is_429_exception(err):
            push_error_429_event()
        raise


def generate_with_telemetry(
    model: Any,
    call_payload: Any,
    model_name: str,
    agent_name: str,
    telemetry_meta: Optional[dict] = None,
    **kwargs: Any,
) -> Any:
    """
    Wrapper cho model.generate_content(stream=False).

    Thu thập usage_metadata + finish_reason và đẩy vào telemetry_queue.
    Trả về response object gốc để caller dùng bình thường.
    """
    try:
        kwargs.setdefault("request_options", {"timeout": 30, "retry": None})
        response = model.generate_content(call_payload, stream=False, **kwargs)
    except Exception as err:
        if _is_429_exception(err):
            push_error_429_event()
        raise

    finish_reason = extract_finish_reason(response)
    if telemetry_meta is not None:
        telemetry_meta["finish_reason"] = finish_reason

    prompt_tokens = 0
    completion_tokens = 0
    try:
        meta = response.usage_metadata
        if meta:
            prompt_tokens = meta.prompt_token_count or 0
            completion_tokens = meta.candidates_token_count or 0
    except Exception:
        pass

    _push_token_event(
        prompt_tokens,
        completion_tokens,
        model_name,
        agent_name,
        ttft_ms=None,
        finish_reason=finish_reason,
    )

    return response

