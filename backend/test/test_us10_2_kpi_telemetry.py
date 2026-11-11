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
        # Nạp dữ liệu giả vào accumulator
        _accumulator.reset()
        _accumulator.add_http_event({"status_code": 200, "latency_ms": 320, "endpoint_group": "chat"})
        _accumulator.add_http_event({"status_code": 200, "latency_ms": 450, "endpoint_group": "eval"})
        _accumulator.add_http_event({"status_code": 500, "latency_ms": 1200, "endpoint_group": "other"})
        _accumulator.add_token_event({
            "type": "token_usage",
            "prompt_tokens": 400,
            "completion_tokens": 150,
            "total_tokens": 550,
            "cost_usd": 0.00015,
            "agent_name": "Chat",
            "model_name": "gemini-2.5-flash",
            "ttft_ms": 380,
        })

        db = SessionLocal()
        try:
            result = flush_metrics_to_db(db)
            assert result["status"] == "success"
            assert result["flushed_requests"] == 3
            assert result["flushed_tokens"] == 550

            # Kiểm tra bản ghi trong system_metrics_hourly
            bucket_ts = _hour_bucket()
            row = db.query(models.SystemMetricsHourly).filter_by(bucket_timestamp=bucket_ts).first()
            assert row is not None
            assert row.total_requests >= 3
            assert row.chat_requests >= 1
            assert row.total_tokens >= 550
        finally:
            db.close()

    def test_sla_incident_trigger_on_5xx_rate(self):
        """AC-KPI-07: Kiểm tra khi lỗi 5xx vượt 2%, hệ thống tự tạo incident ERROR_SPIKE."""
        _accumulator.reset()
        # Nạp 10 requests với 2 request lỗi 500 -> tỷ lệ lỗi 20% > 2%
        for _ in range(8):
            _accumulator.add_http_event({"status_code": 200, "latency_ms": 250, "endpoint_group": "chat"})
        for _ in range(2):
            _accumulator.add_http_event({"status_code": 500, "latency_ms": 950, "endpoint_group": "chat"})

        db = SessionLocal()
        try:
            flush_metrics_to_db(db)

            # Kiểm tra bảng system_incidents_log có bản ghi ACTIVE
            inc = (
                db.query(models.SystemIncidentLog)
                .filter_by(incident_type="ERROR_SPIKE", status="ACTIVE")
                .first()
            )
            assert inc is not None
            assert inc.severity == "CRITICAL"
            assert float(inc.threshold_value) == 2.0
            assert float(inc.actual_value) > 2.0

            # Cleanup
            db.delete(inc)
            db.commit()
        finally:
            db.close()

    def test_ensure_baseline_metrics(self):
        """Kiểm tra seeder baseline nạp tối thiểu 24 giờ dữ liệu lịch sử."""
        db = SessionLocal()
        try:
            ensure_baseline_metrics(db)
            count = db.query(models.SystemMetricsHourly).count()
            assert count >= 24
        finally:
            db.close()


# ==============================================================================
# T10.2.5: ADMIN KPI METRICS API TESTS (8 ENDPOINTS)
# ==============================================================================

class TestT10_2_5_AdminKpiMetricsAPI:
    """Kiểm tra toàn bộ 8 endpoints của router admin_kpi_metrics.py."""

    def test_01_rbac_student_forbidden(self):
        """Học sinh gọi API KPI Admin phải nhận 403 Forbidden."""
        res = client.get("/admin/kpi/overview", headers=STUDENT_HEADERS)
        assert res.status_code == 403

    def test_02_rbac_unauthenticated_unauthorized(self):
        """Chưa đăng nhập gọi API KPI Admin phải nhận 401 Unauthorized."""
        res = client.get("/admin/kpi/overview")
        assert res.status_code == 401

    def test_03_get_overview_success(self):
        """Endpoint 1: GET /admin/kpi/overview trả về 4 thẻ KPI tổng quan và ma trận HTTP."""
        res = client.get("/admin/kpi/overview", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "throughput" in data
        assert "tokens_and_cost" in data
        assert "latency_and_sla" in data
        assert "reliability" in data
        assert "status_2xx_count_today" in data["reliability"]
        assert "status_4xx_count_today" in data["reliability"]
        assert "status_5xx_count_today" in data["reliability"]
        assert "gemini_429_count_today" in data["reliability"]
        assert data["tokens_and_cost"]["cost_vnd_today"] > 0
        assert data["latency_and_sla"]["p50_status"] in ("optimal", "high")

    def test_04_get_throughput_minute_and_hourly(self):
        """Endpoint 2: GET /admin/kpi/throughput hỗ trợ chế độ theo phút và theo giờ."""
        # Chế độ 60 phút
        res_min = client.get("/admin/kpi/throughput?range=1h&granularity=minute", headers=ADMIN_HEADERS)
        assert res_min.status_code == 200
        data_min = res_min.json()
        assert data_min["granularity"] == "minute"
        assert len(data_min["items"]) == 60
        assert "display_time" in data_min["items"][0]

        # Chế độ 24 giờ
        res_hour = client.get("/admin/kpi/throughput?range=24h", headers=ADMIN_HEADERS)
        assert res_hour.status_code == 200
        data_hour = res_hour.json()
        assert data_hour["granularity"] == "hour"
        assert len(data_hour["items"]) > 0

    def test_05_get_tokens_breakdown(self):
        """Endpoint 3: GET /admin/kpi/tokens trả về tiêu thụ và chi phí 6 phân hệ model AI."""
        res = client.get("/admin/kpi/tokens?days=14", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "six_model_breakdown" in data
        assert len(data["six_model_breakdown"]) == 6
        assert "model_breakdown" in data
        assert len(data["model_breakdown"]) >= 1
        assert data["total_tokens"] > 0
        assert data["total_cost_usd"] > 0
        assert data["total_cost_vnd"] > 0

    def test_06_get_latency_percentiles(self):
        """Endpoint 4: GET /admin/kpi/latency trả về P50, P95, P99 và đồng hồ TTFT."""
        res = client.get("/admin/kpi/latency?range=24h", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "overall_p50_ms" in data
        assert "overall_p95_ms" in data
        assert "overall_p99_ms" in data
        assert "current_ttft_ms" in data
        assert data["ttft_status"] in ("green", "yellow", "red")
        assert len(data["items"]) > 0

    def test_07_get_agents_distribution(self):
        """Endpoint 5: GET /admin/kpi/agents trả về biểu đồ Donut 6 phân hệ và tỷ lệ chuẩn."""
        res = client.get("/admin/kpi/agents", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total_subsystems"] == 6
        agent_names = [a["id"] for a in data["agents"]]
        assert "Chat" in agent_names
        assert "Classifier" in agent_names
        assert "Flashcard" in agent_names
        assert "ParentReport" in agent_names
        assert "Email" in agent_names
        assert "Fallback" in agent_names
        pct_sum = sum(a["request_percentage"] for a in data["agents"])
        assert 99.0 <= pct_sum <= 101.0

    def test_08_get_traffic_heatmap(self):
        """Endpoint 6: GET /admin/kpi/traffic-heatmap trả về 168 ô nhiệt 7x24."""
        res = client.get("/admin/kpi/traffic-heatmap", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total_cells"] == 168
        assert "peak_traffic" in data
        assert data["peak_traffic"]["day"] in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]

    def test_09_get_infrastructure(self):
        """Endpoint 7: GET /admin/kpi/infrastructure trả về kết nối Neon DB và Redis."""
        res = client.get("/admin/kpi/infrastructure", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["neon_connections_max"] == 20
        assert data["neon_connections_active"] <= 20
        assert data["redis_hit_rate_pct"] >= 0
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
        # Test CSV
        res_csv = client.get("/admin/kpi/export?format=csv&days=7", headers=ADMIN_HEADERS)
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "attachment; filename=" in res_csv.headers["content-disposition"]
        assert b"Tong Requests" in res_csv.content

        # Test JSON
        res_json = client.get("/admin/kpi/export?format=json&days=7", headers=ADMIN_HEADERS)
        assert res_json.status_code == 200
        assert res_json.json()["report_name"] == "SocraticKid_Admin_KPI_Report"



if __name__ == "__main__":
    pytest.main(["-v", __file__])
