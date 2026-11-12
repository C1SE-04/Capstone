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
    _hour_bucket,
    _flush_events,
    flush_metrics_to_db,
    ensure_baseline_metrics,
    _COUNTER_TTL_SECONDS,
    _accumulator,
)
import auth
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

ADMIN_USER_ID = "c8bb335bcbe24b859d10d740afbacaf4"
ADMIN_TOKEN = auth.create_access_token({
    "sub": ADMIN_USER_ID,
    "email": "admin@socratickid.edu.vn",
    "role": "ADMIN",
    "session_version": 1,
})
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

STUDENT_TOKEN = auth.create_access_token({
    "sub": "student_test_123",
    "email": "student@socratickid.edu.vn",
    "role": "STUDENT",
    "session_version": 1,
})
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}


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

            # Test Admin KPI polling endpoints không tự đếm chính mình
            for kpi_path in ("/admin/kpi/overview", "/admin/kpi/throughput", "/admin/metrics/overview"):
                mock_req_kpi = MagicMock()
                mock_req_kpi.url.path = kpi_path
                mock_req_kpi.method = "GET"
                await middleware.dispatch(mock_req_kpi, AsyncMock(return_value=MagicMock(status_code=200)))
                assert telemetry_queue.empty()

        asyncio.run(_run())


# ==============================================================================
# T10.2.2: GEMINI TELEMETRY & TTFT TESTS
# ==============================================================================

class TestT10_2_2_GeminiTelemetry:
    """Kiểm tra tính chi phí, thu thập usage_metadata và đo TTFT."""

    def test_calc_cost_usd(self):
        """Kiểm tra công thức tính chi phí USD theo bảng giá từng model (3.x & LTS)."""
        # gemini-3.8-flash: prompt $0.10/1M, comp $0.40/1M
        cost_3_8 = _calc_cost_usd(1_000_000, 1_000_000, "gemini-3.8-flash")
        assert cost_3_8 == pytest.approx(0.50, rel=1e-3)

        # gemini-3.1-flash-lite: prompt $0.030/1M, comp $0.12/1M
        cost_3_1_lite = _calc_cost_usd(1_000_000, 1_000_000, "gemini-3.1-flash-lite")
        assert cost_3_1_lite == pytest.approx(0.15, rel=1e-3)

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
            assert call_dict[f"rpm:chat:{minute}"] == 1
            assert call_dict[f"rpm:eval:{minute}"] == 1
            assert call_dict[f"rpm:other:{minute}"] == 1
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


# ==============================================================================
# T10.2.4: 60-SECOND DATABASE BATCH AGGREGATION & SLA INCIDENTS TESTS
# ==============================================================================

class TestT10_2_4_DatabaseAggregation:
    """Kiểm tra chức năng gom batch và ghi xuống Neon PostgreSQL mỗi 60 giây."""

    def test_flush_metrics_to_db_upsert(self):
        """Kiểm tra flush_metrics_to_db ghi đúng số liệu tích lũy vào system_metrics_hourly."""
        _accumulator.reset()
        _accumulator.add_http_event({"status_code": 200, "latency_ms": 320, "endpoint_group": "chat"})
        _accumulator.add_http_event({"status_code": 200, "latency_ms": 450, "endpoint_group": "eval"})
        _accumulator.add_http_event({"status_code": 500, "latency_ms": 1200, "endpoint_group": "other"})
        _accumulator.add_cache_event(True)
        _accumulator.add_cache_event(False)
        _accumulator.observe_sse_session(3)
        _accumulator.add_token_event({
            "type": "token_usage",
            "prompt_tokens": 400,
            "completion_tokens": 150,
            "total_tokens": 550,
            "cost_usd": 0.00015,
            "agent_name": "Chat",
            "model_name": "gemini-3.8-flash",
            "ttft_ms": 380,
        })

        test_bucket = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        db = SessionLocal()
        try:
            with patch("workers.telemetry_batch_worker._hour_bucket", return_value=test_bucket):
                result = flush_metrics_to_db(db)
            assert result["status"] == "success"
            assert result["flushed_requests"] == 3
            assert result["flushed_tokens"] == 550

            row = db.query(models.SystemMetricsHourly).filter_by(bucket_timestamp=test_bucket).first()
            assert row is not None
            assert row.total_requests == 3
            assert row.chat_requests == 1
            assert row.total_tokens == 550
            assert row.redis_cache_hits == 1
            assert row.redis_cache_misses == 1
            assert row.peak_concurrent_sse == 3
        finally:
            db.query(models.SystemAgentMetricsHourly).filter_by(bucket_timestamp=test_bucket).delete(synchronize_session=False)
            db.query(models.SystemMetricsHourly).filter_by(bucket_timestamp=test_bucket).delete(synchronize_session=False)
            db.commit()
            db.close()

    def test_sla_incident_trigger_on_5xx_rate(self):
        """AC-KPI-07: Kiểm tra khi lỗi 5xx vượt 2%, hệ thống tự tạo incident ERROR_SPIKE."""
        _accumulator.reset()
        for _ in range(8):
            _accumulator.add_http_event({"status_code": 200, "latency_ms": 250, "endpoint_group": "chat"})
        for _ in range(2):
            _accumulator.add_http_event({"status_code": 500, "latency_ms": 950, "endpoint_group": "chat"})

        test_bucket = datetime(2099, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        db = SessionLocal()
        try:
            with patch("workers.telemetry_batch_worker._hour_bucket", return_value=test_bucket):
                flush_metrics_to_db(db)

            inc = (
                db.query(models.SystemIncidentLog)
                .filter_by(incident_type="ERROR_SPIKE", status="ACTIVE")
                .first()
            )
            assert inc is not None
            assert inc.severity == "CRITICAL"
            assert float(inc.threshold_value) == 2.0
            assert float(inc.actual_value) > 2.0

            db.delete(inc)
            db.commit()
        finally:
            db.query(models.SystemAgentMetricsHourly).filter_by(bucket_timestamp=test_bucket).delete(synchronize_session=False)
            db.query(models.SystemMetricsHourly).filter_by(bucket_timestamp=test_bucket).delete(synchronize_session=False)
            db.commit()
            db.close()

    def test_ensure_baseline_metrics(self):
        """Kiểm tra synthetic baseline seeder đã tắt (100% Real Telemetry Mode)."""
        db = SessionLocal()
        try:
            before_count = db.query(models.SystemMetricsHourly).count()
            res = ensure_baseline_metrics(db)
            after_count = db.query(models.SystemMetricsHourly).count()
            assert res["status"] == "disabled"
            assert res["seeded_hours"] == 0
            assert after_count == before_count
        finally:
            db.close()


# ==============================================================================
# T10.2.5: ADMIN KPI METRICS API TESTS (8 ENDPOINTS - REAL TELEMETRY ONLY)
# ==============================================================================

def _seed_live_sample_events():
    """Nạp các telemetry events thật vào _accumulator và _live_minute_counters để kiểm chứng API."""
    from workers.telemetry_batch_worker import _live_minute_counters

    _accumulator.reset()
    _live_minute_counters.clear()

    events = [
        {"status_code": 200, "latency_ms": 210, "endpoint_group": "chat"},
        {"status_code": 200, "latency_ms": 340, "endpoint_group": "eval"},
        {"status_code": 422, "latency_ms": 95, "endpoint_group": "auth"},
        {"type": "cache_event", "hit": True},
        {"type": "cache_event", "hit": False},
        {"type": "sse_peak", "active_sessions": 2},
        {"type": "token_usage", "prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700, "cost_usd": 0.00013, "agent_name": "Chat", "model_name": "gemini-3.8-flash", "ttft_ms": 240},
        {"type": "token_usage", "prompt_tokens": 180, "completion_tokens": 45, "total_tokens": 225, "cost_usd": 0.000011, "agent_name": "Classifier", "model_name": "gemini-3.1-flash-lite", "ttft_ms": None},
        {"type": "token_usage", "prompt_tokens": 120, "completion_tokens": 60, "total_tokens": 180, "cost_usd": 0.000013, "agent_name": "Flashcard", "model_name": "gemini-3.5-flash-lite", "ttft_ms": None},
        {"type": "token_usage", "prompt_tokens": 300, "completion_tokens": 100, "total_tokens": 400, "cost_usd": 0.000052, "agent_name": "ParentReport", "model_name": "gemini-3.5-flash", "ttft_ms": None},
        {"type": "token_usage", "prompt_tokens": 90, "completion_tokens": 35, "total_tokens": 125, "cost_usd": 0.000007, "agent_name": "Email", "model_name": "gemini-3.1-flash-lite", "ttft_ms": None},
        {"type": "token_usage", "prompt_tokens": 60, "completion_tokens": 20, "total_tokens": 80, "cost_usd": 0.000005, "agent_name": "Fallback", "model_name": "gemini-3.5-flash-lite", "ttft_ms": None},
    ]
    asyncio.run(_flush_events(None, events))


class TestT10_2_5_AdminKpiMetricsAPI:
    """Kiểm tra toàn bộ 8 endpoints của router admin_kpi_metrics.py với dữ liệu thật."""

    def setup_method(self):
        from workers.telemetry_batch_worker import _live_minute_counters
        while not telemetry_queue.empty():
            try:
                telemetry_queue.get_nowait()
            except Exception:
                break
        _accumulator.reset()
        _live_minute_counters.clear()

    def teardown_method(self):
        from workers.telemetry_batch_worker import _live_minute_counters
        while not telemetry_queue.empty():
            try:
                telemetry_queue.get_nowait()
            except Exception:
                break
        _accumulator.reset()
        _live_minute_counters.clear()

    def test_01_rbac_student_forbidden(self):
        """Học sinh gọi API KPI Admin phải nhận 403 Forbidden."""
        res = client.get("/admin/kpi/overview", headers=STUDENT_HEADERS)
        assert res.status_code == 403

    def test_02_rbac_unauthenticated_unauthorized(self):
        """Chưa đăng nhập gọi API KPI Admin phải nhận 401 Unauthorized."""
        res = client.get("/admin/kpi/overview")
        assert res.status_code == 401

    def test_03_get_overview_success(self):
        """Endpoint 1: GET /admin/kpi/overview phản ánh chính xác tổng DB + live delta."""
        before = client.get("/admin/kpi/overview", headers=ADMIN_HEADERS).json()
        _seed_live_sample_events()
        after = client.get("/admin/kpi/overview", headers=ADMIN_HEADERS).json()

        assert after["status"] == "success"
        # +3 requests tu _seed_live_sample_events + 1 request (before overview) tu TestClient middleware
        assert after["throughput"]["total_requests_today"] >= before["throughput"]["total_requests_today"] + 3
        assert after["tokens_and_cost"]["total_tokens_today"] == before["tokens_and_cost"]["total_tokens_today"] + 1710
        assert after["tokens_and_cost"]["prompt_tokens_today"] == before["tokens_and_cost"]["prompt_tokens_today"] + 1250
        assert after["tokens_and_cost"]["completion_tokens_today"] == before["tokens_and_cost"]["completion_tokens_today"] + 460
        assert after["tokens_and_cost"]["cost_vnd_today"] >= before["tokens_and_cost"]["cost_vnd_today"]
        assert after["reliability"]["status_4xx_count_today"] == before["reliability"]["status_4xx_count_today"] + 1
        assert after["latency_and_sla"]["p50_status"] in ("optimal", "high")

    def test_04_get_throughput_minute_and_hourly(self):
        """Endpoint 2: GET /admin/kpi/throughput trả 60 phút thật (0 khi rỗng), 24 giờ và daily theo giờ VN (UTC+7)."""
        from datetime import datetime, timezone, timedelta
        now_vn = datetime.now(timezone(timedelta(hours=7)))

        res_min = client.get("/admin/kpi/throughput?range=1h&granularity=minute", headers=ADMIN_HEADERS)
        assert res_min.status_code == 200
        data_min = res_min.json()
        assert data_min["granularity"] == "minute"
        assert len(data_min["items"]) == 60
        assert "display_time" in data_min["items"][0]
        assert data_min["items"][-1]["timestamp"].endswith("+07:00")
        assert data_min["items"][-1]["display_time"] == now_vn.strftime("%H:%M")

        res_hour = client.get("/admin/kpi/throughput?range=24h", headers=ADMIN_HEADERS)
        assert res_hour.status_code == 200
        data_hour = res_hour.json()
        assert data_hour["granularity"] == "hour"
        assert len(data_hour["items"]) == 24
        assert data_hour["items"][-1]["timestamp"].endswith("+07:00")
        assert data_hour["items"][-1]["display_time"] == now_vn.strftime("%H:00")

        res_day = client.get("/admin/kpi/throughput?range=7d", headers=ADMIN_HEADERS)
        assert res_day.status_code == 200
        data_day = res_day.json()
        assert data_day["granularity"] == "day"
        assert len(data_day["items"]) == 7
        assert data_day["items"][-1]["display_time"] == now_vn.strftime("%d/%m")

        # Đảm bảo khi RAM _live_minute_counters rỗng, đọc phân loại chat từ Redis rpm:chat:{minute}
        cur_bucket = _minute_bucket()
        fake_kv = {f"rpm:{cur_bucket}": "2", f"rpm:chat:{cur_bucket}": "2"}
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = lambda k: fake_kv.get(k)
        mock_redis.mget.side_effect = lambda *keys: [fake_kv.get(k) for k in keys]
        with patch("routers.admin_kpi_metrics._get_upstash_redis", return_value=mock_redis), \
             patch("routers.admin_kpi_metrics.get_live_minute_stats", return_value={"rpm": 0, "chat": 0, "eval": 0, "auth": 0, "other": 0, "tpm": 0, "err4xx": 0, "err429": 0, "err5xx": 0}):
            res_redis_grp = client.get("/admin/kpi/throughput?range=1h&granularity=minute", headers=ADMIN_HEADERS)
            assert res_redis_grp.status_code == 200
            last_pt = res_redis_grp.json()["items"][-1]
            assert last_pt["requests"] == 2
            assert last_pt["chat_requests"] == 2
            assert last_pt["other_requests"] == 0

    def test_05_get_tokens_breakdown(self):
        """Endpoint 3: GET /admin/kpi/tokens tính chính xác 6 phân hệ model AI từ sự kiện thật."""
        _seed_live_sample_events()
        res = client.get("/admin/kpi/tokens?days=14", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "six_model_breakdown" in data
        assert len(data["six_model_breakdown"]) == 6
        assert "model_breakdown" in data
        assert len(data["model_breakdown"]) >= 1
        assert data["total_tokens"] >= 1710
        assert data["total_cost_usd"] > 0
        assert data["total_cost_vnd"] >= 0

        chat_item = next(x for x in data["six_model_breakdown"] if x["role_id"] == "Chat")
        assert chat_item["total_tokens"] >= 700

    def test_06_get_latency_percentiles(self):
        """Endpoint 4: GET /admin/kpi/latency trả về 24 điểm giờ thật theo giờ VN (UTC+7) và đồng hồ TTFT."""
        from datetime import datetime, timezone, timedelta
        now_vn = datetime.now(timezone(timedelta(hours=7)))
        _seed_live_sample_events()
        res = client.get("/admin/kpi/latency?range=24h", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "overall_p50_ms" in data
        assert "overall_p95_ms" in data
        assert "overall_p99_ms" in data
        assert "current_ttft_ms" in data
        assert data["ttft_status"] in ("green", "yellow", "red")
        assert len(data["items"]) == 24
        assert data["items"][-1]["timestamp"].endswith("+07:00")
        assert data["items"][-1]["display_time"] == now_vn.strftime("%H:00")

    def test_07_get_agents_distribution(self):
        """Endpoint 5: GET /admin/kpi/agents phân bổ thật 6 phân hệ (Chat..Fallback)."""
        _seed_live_sample_events()
        res = client.get("/admin/kpi/agents", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total_subsystems"] == 6
        agent_names = [a["id"] for a in data["agents"]]
        assert set(agent_names) == {"Chat", "Classifier", "Flashcard", "ParentReport", "Email", "Fallback"}
        pct_sum = sum(a["request_percentage"] for a in data["agents"])
        assert 99.0 <= pct_sum <= 101.0

    def test_08_get_traffic_heatmap(self):
        """Endpoint 6: GET /admin/kpi/traffic-heatmap trả về 168 ô nhiệt 7x24 từ DB + live."""
        res = client.get("/admin/kpi/traffic-heatmap", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total_cells"] == 168
        assert "peak_traffic" in data
        assert data["peak_traffic"]["day"] in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    def test_09_get_infrastructure(self):
        """Endpoint 7: GET /admin/kpi/infrastructure trả về kết nối Neon DB, Cache Hit/Miss và SSE thật."""
        _seed_live_sample_events()
        res = client.get("/admin/kpi/infrastructure", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["neon_connections_max"] == 20
        assert data["neon_connections_active"] <= 20
        assert data["redis_cache_hits"] >= 1
        assert data["redis_cache_misses"] >= 1
        assert data["redis_hit_rate_pct"] >= 0
        assert data["active_sse_sessions"] >= 0
        assert len(data["services"]) == 4

    def test_10_get_incidents(self):
        """Endpoint 8: GET /admin/kpi/incidents trả về thông tin banner SLA."""
        res = client.get("/admin/kpi/incidents", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "has_active_incidents" in data
        assert "active_incidents" in data

    def test_11_export_kpi_csv_and_json(self):
        """Endpoint 9: GET /admin/kpi/export xuất báo cáo CSV và JSON có header tải file."""
        res_csv = client.get("/admin/kpi/export?format=csv&days=7", headers=ADMIN_HEADERS)
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "attachment; filename=" in res_csv.headers["content-disposition"]
        for expected_col in (b"Timestamp (UTC+7)", b"Tong Requests", b"P99 Latency (ms)", b"HTTP 4xx", b"HTTP 429", b"Peak Concurrent SSE"):
            assert expected_col in res_csv.content

        res_json = client.get("/admin/kpi/export?format=json&days=7", headers=ADMIN_HEADERS)
        assert res_json.status_code == 200
        assert res_json.json()["report_name"] == "SocraticKid_Admin_KPI_Report"

    def test_12_zero_state_no_mock_fallbacks(self):
        """Đảm bảo khi DB rỗng và chưa có traffic, Dashboard trả về đúng 0 (không mock)."""
        from database import get_db

        class _EmptyQuery:
            def filter(self, *args, **kwargs):
                return self
            def group_by(self, *args, **kwargs):
                return self
            def order_by(self, *args, **kwargs):
                return self
            def limit(self, *args, **kwargs):
                return self
            def all(self):
                return []
            def first(self):
                return None
            def scalar(self):
                return 0

        class _EmptyScalarResult:
            def scalar(self):
                return 0

        class _EmptyDB:
            def query(self, *args, **kwargs):
                return _EmptyQuery()
            def execute(self, *args, **kwargs):
                return _EmptyScalarResult()

        app.dependency_overrides[get_db] = lambda: _EmptyDB()
        try:
            with patch("routers.admin_kpi_metrics._get_upstash_redis", return_value=None):
                ov = client.get("/admin/kpi/overview", headers=ADMIN_HEADERS).json()
                assert ov["throughput"]["total_requests_today"] == 0
                assert ov["tokens_and_cost"]["total_tokens_today"] == 0
                assert ov["tokens_and_cost"]["cost_usd_today"] == 0
                assert ov["latency_and_sla"]["p50_latency_ms"] == 0
                assert ov["latency_and_sla"]["p95_latency_ms"] == 0
                assert ov["latency_and_sla"]["current_ttft_ms"] == 0
                assert ov["reliability"]["active_sse_sessions"] == 0

                hm = client.get("/admin/kpi/traffic-heatmap", headers=ADMIN_HEADERS).json()
                assert hm["total_cells"] == 168
                assert all(c["requests"] == 0 and c["intensity"] == 0 for c in hm["heatmap"])

                ag = client.get("/admin/kpi/agents", headers=ADMIN_HEADERS).json()
                assert ag["total_requests"] == 0
                assert ag["total_tokens"] == 0
                assert all(a["request_count"] == 0 and a["request_percentage"] == 0.0 for a in ag["agents"])

                inf = client.get("/admin/kpi/infrastructure", headers=ADMIN_HEADERS).json()
                assert inf["redis_cache_hits"] == 0
                assert inf["redis_cache_misses"] == 0
                assert inf["redis_hit_rate_pct"] == 0.0
                assert inf["active_sse_sessions"] == 0
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_13_real_telemetry_producers_kwargs_and_429(self):
        """Kiểm tra generate_with_telemetry truyền **kwargs (generation_config) và bắt lỗi 429."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 42
        mock_response.usage_metadata.candidates_token_count = 18
        mock_model.generate_content.return_value = mock_response

        while not telemetry_queue.empty():
            telemetry_queue.get_nowait()

        res = generate_with_telemetry(
            mock_model, "Test prompt", "gemini-3.1-flash-lite", "Email", generation_config={"temperature": 0.2}
        )
        assert res is mock_response
        mock_model.generate_content.assert_called_once_with(
            "Test prompt", stream=False, generation_config={"temperature": 0.2}
        )
        ev = telemetry_queue.get_nowait()
        assert ev["agent_name"] == "Email"
        assert ev["total_tokens"] == 60

        # Kiểm tra 429 detection
        mock_err_model = MagicMock()
        mock_err_model.generate_content.side_effect = RuntimeError("429 ResourceExhausted quota limit")
        with pytest.raises(RuntimeError):
            generate_with_telemetry(mock_err_model, "Test", "gemini-3.8-flash", "Chat")
        ev_429 = telemetry_queue.get_nowait()
        assert ev_429["type"] == "error_429"

        # Kiểm tra HTTP 429 tách biệt khỏi HTTP 4xx (không đếm đúp trong c4xx + c429)
        _accumulator.reset()
        _accumulator.add_http_event({"status_code": 422, "latency_ms": 20, "endpoint_group": "chat"})
        _accumulator.add_http_event({"status_code": 429, "latency_ms": 15, "endpoint_group": "chat"})
        assert _accumulator.status_4xx_count == 1
        assert _accumulator.gemini_429_count == 1



if __name__ == "__main__":
    pytest.main(["-v", __file__])
