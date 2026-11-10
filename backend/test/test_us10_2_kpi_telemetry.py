"""
Unit and Integration Tests for US 10.2 (Tasks T10.2.0 - T10.2.3)
Admin KPI Observability Dashboard Infrastructure
================================================================
Test suite covers:
  - T10.2.0: Database models and DDL for system_metrics_hourly,
             system_agent_metrics_hourly, system_incidents_log.
  - T10.2.1: TelemetryMiddleware, endpoint classification, non-blocking queue.
  - T10.2.2: Gemini telemetry wrappers, TTFT measurement, token counting, cost calculation.
  - T10.2.3: Upstash Redis batch worker, RPM/TPM/5xx counters, TTL expiry, fail-safety.
"""

import sys
import os
import time
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from sqlalchemy import inspect

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
import models
from middleware.telemetry_middleware import (
    TelemetryMiddleware,
    _classify_endpoint,
    telemetry_queue,
)
from middleware.gemini_telemetry import (
    _calc_cost_usd,
    _push_token_event,
    stream_with_telemetry,
    generate_with_telemetry,
    _MODEL_PRICING,
)
from workers.telemetry_batch_worker import (
    _minute_bucket,
    _flush_events,
    _COUNTER_TTL_SECONDS,
)


# ==============================================================================
# T10.2.0: DATABASE & MODEL TESTS
# ==============================================================================

class TestT10_2_0_DatabaseModels:
    """Kiểm tra cấu trúc 3 bảng và ORM models của US 10.2."""

    def test_database_tables_exist(self):
        """Kiểm tra 3 bảng tồn tại trong cơ sở dữ liệu Neon."""
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        assert "system_metrics_hourly" in tables
        assert "system_agent_metrics_hourly" in tables
        assert "system_incidents_log" in tables

    def test_system_metrics_hourly_columns(self):
        """Kiểm tra các cột của bảng system_metrics_hourly."""
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("system_metrics_hourly")}

        expected_cols = {
            "id", "bucket_timestamp", "total_requests", "chat_requests",
            "eval_requests", "auth_requests", "other_requests",
            "prompt_tokens", "completion_tokens", "total_tokens",
            "estimated_cost_usd", "avg_latency_ms", "p50_latency_ms",
            "p95_latency_ms", "p99_latency_ms", "avg_ttft_ms",
            "status_2xx_count", "status_4xx_count", "status_5xx_count",
            "gemini_429_count", "failover_count", "redis_cache_hits",
            "redis_cache_misses", "peak_concurrent_sse", "created_at"
        }
        for col in expected_cols:
            assert col in cols, f"Thiếu cột {col} trong bảng system_metrics_hourly"

    def test_system_agent_metrics_hourly_columns(self):
        """Kiểm tra các cột của bảng system_agent_metrics_hourly."""
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("system_agent_metrics_hourly")}

        expected_cols = {
            "id", "bucket_timestamp", "agent_name", "model_name",
            "request_count", "prompt_tokens", "completion_tokens",
            "total_cost_usd", "avg_latency_ms", "error_count"
        }
        for col in expected_cols:
            assert col in cols, f"Thiếu cột {col} trong bảng system_agent_metrics_hourly"

    def test_system_incidents_log_columns(self):
        """Kiểm tra các cột của bảng system_incidents_log."""
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("system_incidents_log")}

        expected_cols = {
            "id", "incident_type", "severity", "metric_name",
            "threshold_value", "actual_value", "message", "status",
            "triggered_at", "resolved_at"
        }
        for col in expected_cols:
            assert col in cols, f"Thiếu cột {col} trong bảng system_incidents_log"

    def test_orm_models_crud(self):
        """Kiểm tra các ORM models có thể khởi tạo và commit/rollback an toàn."""
        db = SessionLocal()
        try:
            # Tạo incident test
            incident = models.SystemIncidentLog(
                id="test_incident_001",
                incident_type="HIGH_LATENCY",
                severity="WARNING",
                metric_name="p95_latency_ms",
                threshold_value=1800.0,
                actual_value=2150.0,
                message="Độ trễ P95 vượt ngưỡng 1800ms",
                status="ACTIVE",
            )
            db.add(incident)
            db.commit()

            # Query lại
            found = db.query(models.SystemIncidentLog).filter_by(id="test_incident_001").first()
            assert found is not None
            assert found.metric_name == "p95_latency_ms"
            assert float(found.threshold_value) == 1800.0

            # Cleanup
            db.delete(found)
            db.commit()
        finally:
            db.close()


# ==============================================================================
# T10.2.1: TELEMETRY MIDDLEWARE TESTS
# ==============================================================================

class TestT10_2_1_TelemetryMiddleware:
    """Kiểm tra TelemetryMiddleware và phân loại endpoint."""

    def test_classify_endpoint(self):
        """Kiểm tra logic phân loại endpoint API."""
        assert _classify_endpoint("/chat") == "chat"
        assert _classify_endpoint("/chat/stream") == "chat"
        assert _classify_endpoint("/chat/history") == "chat"
        assert _classify_endpoint("/independence/evaluate") == "eval"
        assert _classify_endpoint("/auth/login") == "auth"
        assert _classify_endpoint("/auth/register") == "auth"
        assert _classify_endpoint("/metrics/streak-leaderboard") == "other"
        assert _classify_endpoint("/upload/image") == "other"

    def test_telemetry_middleware_records_event(self):
        """Kiểm tra Middleware ghi nhận event và không làm gián đoạn response."""
        async def _run():
            # Dọn sạch queue trước test
            while not telemetry_queue.empty():
                telemetry_queue.get_nowait()

            middleware = TelemetryMiddleware(app=MagicMock())

            # Mock request & call_next
            mock_request = MagicMock()
            mock_request.url.path = "/chat/stream"
            mock_request.method = "POST"

            mock_response = MagicMock()
            mock_response.status_code = 200

            async def fake_call_next(req):
                await asyncio.sleep(0.01)  # Giả lập xử lý 10ms
                return mock_response

            res = await middleware.dispatch(mock_request, fake_call_next)
            assert res.status_code == 200

            # Kiểm tra event đã được push vào telemetry_queue
            assert not telemetry_queue.empty()
            event = telemetry_queue.get_nowait()
            assert event["status_code"] == 200
            assert event["endpoint_group"] == "chat"
            assert event["latency_ms"] >= 8  # Ít nhất ~10ms

        asyncio.run(_run())

    def test_telemetry_middleware_skips_health_and_options(self):
        """Kiểm tra Middleware bỏ qua các đường dẫn hạ tầng /health và method OPTIONS."""
        async def _run():
            while not telemetry_queue.empty():
                telemetry_queue.get_nowait()

            middleware = TelemetryMiddleware(app=MagicMock())

            # Test OPTIONS
            mock_req_options = MagicMock()
            mock_req_options.url.path = "/chat"
            mock_req_options.method = "OPTIONS"
            await middleware.dispatch(mock_req_options, AsyncMock(return_value=MagicMock(status_code=204)))
            assert telemetry_queue.empty()

            # Test /health
            mock_req_health = MagicMock()
            mock_req_health.url.path = "/health"
            mock_req_health.method = "GET"
            await middleware.dispatch(mock_req_health, AsyncMock(return_value=MagicMock(status_code=200)))
            assert telemetry_queue.empty()

        asyncio.run(_run())


# ==============================================================================
# T10.2.2: GEMINI TELEMETRY & TTFT TESTS
# ==============================================================================

class TestT10_2_2_GeminiTelemetry:
    """Kiểm tra tính chi phí, thu thập usage_metadata và đo TTFT."""

    def test_calc_cost_usd(self):
        """Kiểm tra công thức tính chi phí USD theo bảng giá từng model."""
        # gemini-2.5-flash: prompt $0.075/1M, comp $0.30/1M
        cost_2_5 = _calc_cost_usd(1_000_000, 1_000_000, "gemini-2.5-flash")
        assert cost_2_5 == pytest.approx(0.375, rel=1e-3)

        # gemini-2.0-flash-lite: prompt $0.0375/1M, comp $0.15/1M
        cost_lite = _calc_cost_usd(1_000_000, 1_000_000, "gemini-2.0-flash-lite")
        assert cost_lite == pytest.approx(0.1875, rel=1e-3)

        # gemini-1.5-pro: prompt $1.25/1M, comp $5.00/1M
        cost_pro = _calc_cost_usd(1_000_000, 1_000_000, "gemini-1.5-pro")
        assert cost_pro == pytest.approx(6.25, rel=1e-3)

    def test_push_token_event(self):
        """Kiểm tra hàm _push_token_event đẩy đúng định dạng sự kiện vào queue."""
        while not telemetry_queue.empty():
            telemetry_queue.get_nowait()

        _push_token_event(
            prompt_tokens=150,
            completion_tokens=80,
            model_name="gemini-2.0-flash-lite",
            agent_name="Classifier",
            ttft_ms=120,
        )

        assert not telemetry_queue.empty()
        ev = telemetry_queue.get_nowait()
        assert ev["type"] == "token_usage"
        assert ev["prompt_tokens"] == 150
        assert ev["completion_tokens"] == 80
        assert ev["total_tokens"] == 230
        assert ev["model_name"] == "gemini-2.0-flash-lite"
        assert ev["agent_name"] == "Classifier"
        assert ev["ttft_ms"] == 120
        assert ev["cost_usd"] > 0

    def test_stream_with_telemetry(self):
        """Kiểm tra stream_with_telemetry đo TTFT và nạp usage_metadata."""
        while not telemetry_queue.empty():
            telemetry_queue.get_nowait()

        # Tạo mock chunks
        class FakeChunk:
            def __init__(self, text):
                self.text = text

        chunk1 = FakeChunk("Chào ")
        chunk2 = FakeChunk("em, ")
        chunk3 = FakeChunk("thầy giúp gì?")

        class FakeStreamResponse:
            def __init__(self):
                self.chunks = [chunk1, chunk2, chunk3]
                self.usage_metadata = MagicMock()
                self.usage_metadata.prompt_token_count = 45
                self.usage_metadata.candidates_token_count = 20

            def __iter__(self):
                return iter(self.chunks)

        fake_model = MagicMock()
        fake_model.generate_content.return_value = FakeStreamResponse()

        # Gọi stream wrapper
        chunks_collected = list(
            stream_with_telemetry(
                fake_model,
                call_payload="test payload",
                model_name="gemini-2.5-flash",
                agent_name="Chat",
            )
        )

        # Kiểm tra nội dung text trả về đầy đủ
        assert chunks_collected == ["Chào ", "em, ", "thầy giúp gì?"]

        # Kiểm tra event telemetry được sinh ra
        assert not telemetry_queue.empty()
        ev = telemetry_queue.get_nowait()
        assert ev["type"] == "token_usage"
        assert ev["prompt_tokens"] == 45
        assert ev["completion_tokens"] == 20
        assert ev["total_tokens"] == 65
        assert ev["agent_name"] == "Chat"
        assert ev["ttft_ms"] is not None
        assert ev["ttft_ms"] >= 0

    def test_generate_with_telemetry(self):
        """Kiểm tra generate_with_telemetry (non-streaming) thu thập metadata."""
        while not telemetry_queue.empty():
            telemetry_queue.get_nowait()

        fake_response = MagicMock()
        fake_response.text = "Phản hồi non-stream"
        fake_response.usage_metadata.prompt_token_count = 100
        fake_response.usage_metadata.candidates_token_count = 50

        fake_model = MagicMock()
        fake_model.generate_content.return_value = fake_response

        res = generate_with_telemetry(
            fake_model,
            call_payload="test",
            model_name="gemini-2.0-flash-lite",
            agent_name="ParentReport",
        )

        assert res.text == "Phản hồi non-stream"
        assert not telemetry_queue.empty()
        ev = telemetry_queue.get_nowait()
        assert ev["type"] == "token_usage"
        assert ev["prompt_tokens"] == 100
        assert ev["completion_tokens"] == 50
        assert ev["agent_name"] == "ParentReport"
        assert ev["ttft_ms"] is None


# ==============================================================================
# T10.2.3: UPSTASH REDIS BATCH WORKER TESTS
# ==============================================================================

class TestT10_2_3_UpstashRedisCounters:
    """Kiểm tra cập nhật counter Redis (rpm, tpm, 5xx) và worker."""

    def test_minute_bucket_format(self):
        """Kiểm tra format mốc phút YYYY-MM-DDTHH:MM."""
        bucket = _minute_bucket()
        # Ví dụ: 2026-11-09T13:45
        assert len(bucket) == 16
        assert "T" in bucket
        parts = bucket.split("T")
        assert len(parts[0].split("-")) == 3
        assert len(parts[1].split(":")) == 2

    def test_flush_events_increments_redis_counters(self):
        """Kiểm tra _flush_events tăng đúng số lượng RPM, TPM và 5xx."""
        async def _run():
            mock_redis = AsyncMock()

            events = [
                # 2 requests HTTP 200
                {"status_code": 200, "latency_ms": 150, "endpoint_group": "chat"},
                {"status_code": 200, "latency_ms": 200, "endpoint_group": "eval"},
                # 1 request HTTP 500 (Server Error)
                {"status_code": 500, "latency_ms": 300, "endpoint_group": "other"},
                # 1 token usage event
                {"type": "token_usage", "total_tokens": 1250},
            ]

            await _flush_events(mock_redis, events)

            # Kiểm tra incrby được gọi cho rpm, tpm, errors:5xx
            calls = [c.args[0] for c in mock_redis.incrby.call_args_list]
            minute = _minute_bucket()

            assert f"rpm:{minute}" in calls
            assert f"tpm:{minute}" in calls
            assert f"errors:5xx:{minute}" in calls

            # Kiểm tra giá trị tăng:
            # rpm: 3 (có 3 http request)
            # tpm: 1250 (1 token event có 1250 tokens)
            # errors:5xx: 1 (có 1 request mã 500)
            call_dict = {c.args[0]: c.args[1] for c in mock_redis.incrby.call_args_list}
            assert call_dict[f"rpm:{minute}"] == 3
            assert call_dict[f"tpm:{minute}"] == 1250
            assert call_dict[f"errors:5xx:{minute}"] == 1

            # Kiểm tra expire được gọi với TTL 5400s
            for c in mock_redis.expire.call_args_list:
                assert c.args[1] == _COUNTER_TTL_SECONDS

        asyncio.run(_run())

    def test_flush_events_handles_redis_none_or_exception(self):
        """Kiểm tra _flush_events xử lý fail-safe khi Redis bị lỗi hoặc rớt kết nối."""
        async def _run():
            # Trường hợp 1: Redis là None
            events = [{"status_code": 200, "latency_ms": 50}]
            await _flush_events(None, events)  # Không được văng lỗi

            # Trường hợp 2: Redis ném Exception (ví dụ mất mạng)
            mock_redis = AsyncMock()
            mock_redis.incrby.side_effect = ConnectionError("Redis down")
            await _flush_events(mock_redis, events)  # Không được văng lỗi

        asyncio.run(_run())


if __name__ == "__main__":
    pytest.main(["-v", __file__])
