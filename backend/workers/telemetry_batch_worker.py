"""
US 10.2 - Telemetry Batch Worker: Redis Counters & Hourly DB Rollup (T10.2.3 & T10.2.4)
========================================================================================
1. T10.2.3: Tiêu thụ telemetry_queue mỗi 1 giây và cập nhật Redis counters:
     - rpm:{minute}            : Số request mỗi phút (TTL 5400s)
     - tpm:{minute}            : Số token mỗi phút
     - errors:5xx:{minute}     : Số lỗi HTTP 5xx mỗi phút

2. T10.2.4: FastAPI BackgroundTask tự động gom số liệu từ Redis / Accumulator và
   ghi batch xuống Neon PostgreSQL (system_metrics_hourly & system_agent_metrics_hourly)
   mỗi 60 giây (không dùng Celery).

3. Đánh giá ngưỡng SLA và ghi nhận sự cố (system_incidents_log):
     - 5xx error rate > 2%  -> Kích hoạt Incident ERROR_SPIKE (CRITICAL)
     - P95 latency > 1800ms -> Kích hoạt Incident HIGH_LATENCY (WARNING)
     - Tự động RESOLVED khi các chỉ số trở về bình thường.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from sqlalchemy import text
from upstash_redis.asyncio import Redis

from middleware.telemetry_middleware import telemetry_queue
from database import SessionLocal
import models

load_dotenv()

# TTL của counter key trên Redis: 90 phút (5400 giây)
_COUNTER_TTL_SECONDS = 5400

# Chu kỳ kiểm tra queue: 1 giây
_POLL_INTERVAL_SECONDS = 1.0

# Chu kỳ ghi batch xuống Database: 60 giây (T10.2.4)
_DB_FLUSH_INTERVAL_SECONDS = 60.0

# Ngưỡng SLA
_SLA_P95_MAX_MS = 1800
_SLA_ERROR_5XX_MAX_RATE = 0.02  # 2%


def _get_upstash_redis() -> Optional[Redis]:
    """Khởi tạo Upstash Redis REST client từ biến môi trường."""
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

    if not rest_url or not rest_token:
        return None

    return Redis(url=rest_url, token=rest_token, allow_telemetry=False)


def _minute_bucket(dt: Optional[datetime] = None) -> str:
    """Trả về mốc phút hiện tại dạng YYYY-MM-DDTHH:MM (UTC)."""
    now = dt or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M")


def _hour_bucket(dt: Optional[datetime] = None) -> datetime:
    """Trả về mốc giờ hiện tại (phút=0, giây=0, microsecond=0, UTC)."""
    now = dt or datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0)


def _calc_percentile(data: List[int], percentile: float) -> int:
    """Tính phân vị từ danh sách số nguyên không cần thư viện ngoài."""
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * (percentile / 100.0))
    idx = min(idx, len(s) - 1)
    return s[idx]


# ==============================================================================
# In-Memory Accumulator cho giờ hiện tại (Rolling Delta Buffer)
# ==============================================================================
class HourlyAccumulator:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_requests = 0
        self.chat_requests = 0
        self.eval_requests = 0
        self.auth_requests = 0
        self.other_requests = 0

        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.estimated_cost_usd = 0.0

        self.latencies: List[int] = []
        self.ttfts: List[int] = []

        self.status_2xx_count = 0
        self.status_4xx_count = 0
        self.status_5xx_count = 0
        self.gemini_429_count = 0
        self.failover_count = 0

        self.redis_cache_hits = 0
        self.redis_cache_misses = 0
        self.peak_concurrent_sse = 0

        # Dict (agent_name, model_name) -> metrics
        self.agent_stats: Dict[tuple, Dict[str, Any]] = {}

    def add_cache_event(self, hit: bool):
        if hit:
            self.redis_cache_hits += 1
        else:
            self.redis_cache_misses += 1

    def observe_sse_session(self, active_sessions: int):
        if active_sessions > self.peak_concurrent_sse:
            self.peak_concurrent_sse = active_sessions

    def add_failover_event(self, is_429: bool = False):
        self.failover_count += 1
        if is_429:
            self.gemini_429_count += 1

    def add_error_429_event(self):
        self.gemini_429_count += 1

    def snapshot_and_reset(self) -> "HourlyAccumulator":
        snap = HourlyAccumulator()
        for k, v in self.__dict__.items():
            if k == "agent_stats":
                snap.agent_stats = {
                    ak: {**av, "latencies": list(av["latencies"])}
                    for ak, av in v.items()
                }
            elif isinstance(v, list):
                setattr(snap, k, list(v))
            else:
                setattr(snap, k, v)
        self.reset()
        return snap

    def add_http_event(self, event: dict):
        self.total_requests += 1
        group = event.get("endpoint_group", "other")
        if group == "chat":
            self.chat_requests += 1
        elif group == "eval":
            self.eval_requests += 1
        elif group == "auth":
            self.auth_requests += 1
        else:
            self.other_requests += 1

        status = event.get("status_code", 200)
        if 200 <= status < 300:
            self.status_2xx_count += 1
        elif status == 429:
            self.status_4xx_count += 1
            self.gemini_429_count += 1
        elif 400 <= status < 500:
            self.status_4xx_count += 1
        elif status >= 500:
            self.status_5xx_count += 1

        lat = event.get("latency_ms", 0)
        if len(self.latencies) < 3000:
            self.latencies.append(lat)

    def add_token_event(self, event: dict):
        p_tokens = event.get("prompt_tokens", 0)
        c_tokens = event.get("completion_tokens", 0)
        t_tokens = event.get("total_tokens", p_tokens + c_tokens)
        cost = event.get("cost_usd", 0.0)

        self.prompt_tokens += p_tokens
        self.completion_tokens += c_tokens
        self.total_tokens += t_tokens
        self.estimated_cost_usd += cost

        ttft = event.get("ttft_ms")
        if ttft is not None and len(self.ttfts) < 3000:
            self.ttfts.append(ttft)

        # Agent breakdown
        agent_name = event.get("agent_name", "Chat")
        model_name = event.get("model_name", "gemini-3.1-flash-lite")
        key = (agent_name, model_name)
        if key not in self.agent_stats:
            self.agent_stats[key] = {
                "request_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost_usd": 0.0,
                "latencies": [],
                "error_count": 0,
            }
        ag = self.agent_stats[key]
        ag["request_count"] += 1
        ag["prompt_tokens"] += p_tokens
        ag["completion_tokens"] += c_tokens
        ag["total_cost_usd"] += cost
        if ttft is not None:
            ag["latencies"].append(ttft)


_accumulator = HourlyAccumulator()

# In-memory rolling minute counters (dự phòng tức thì khi Redis offline hoặc giữa chu kỳ batch)
_live_minute_counters: Dict[str, Dict[str, int]] = {}


def get_live_minute_stats(minute_str: Optional[str] = None) -> Dict[str, int]:
    """Đọc số liệu RPM/TPM/Error của 1 phút từ bộ nhớ cục bộ."""
    key = minute_str or _minute_bucket()
    return _live_minute_counters.get(key, {
        "rpm": 0, "chat": 0, "eval": 0, "auth": 0, "other": 0,
        "tpm": 0, "err4xx": 0, "err429": 0, "err5xx": 0,
    })


def get_live_accumulator_snapshot() -> Dict[str, Any]:
    """Trả về ảnh chụp nhanh các delta chưa flush xuống DB để KPI API cộng dồn tức thì."""
    lats = _accumulator.latencies
    ttfts = _accumulator.ttfts
    agent_stats_list = []
    for (ag_name, mod_name), ag_data in _accumulator.agent_stats.items():
        ag_lats = ag_data["latencies"]
        agent_stats_list.append({
            "agent_name": ag_name,
            "model_name": mod_name,
            "request_count": ag_data["request_count"],
            "prompt_tokens": ag_data["prompt_tokens"],
            "completion_tokens": ag_data["completion_tokens"],
            "total_cost_usd": ag_data["total_cost_usd"],
            "avg_latency_ms": int(sum(ag_lats) / len(ag_lats)) if ag_lats else 0,
            "error_count": ag_data["error_count"],
        })

    return {
        "total_requests": _accumulator.total_requests,
        "chat_requests": _accumulator.chat_requests,
        "eval_requests": _accumulator.eval_requests,
        "auth_requests": _accumulator.auth_requests,
        "other_requests": _accumulator.other_requests,
        "prompt_tokens": _accumulator.prompt_tokens,
        "completion_tokens": _accumulator.completion_tokens,
        "total_tokens": _accumulator.total_tokens,
        "estimated_cost_usd": _accumulator.estimated_cost_usd,
        "avg_latency_ms": int(sum(lats) / len(lats)) if lats else 0,
        "p50_latency_ms": _calc_percentile(lats, 50.0) if lats else 0,
        "p95_latency_ms": _calc_percentile(lats, 95.0) if lats else 0,
        "p99_latency_ms": _calc_percentile(lats, 99.0) if lats else 0,
        "avg_ttft_ms": int(sum(ttfts) / len(ttfts)) if ttfts else 0,
        "status_2xx_count": _accumulator.status_2xx_count,
        "status_4xx_count": _accumulator.status_4xx_count,
        "status_5xx_count": _accumulator.status_5xx_count,
        "gemini_429_count": _accumulator.gemini_429_count,
        "failover_count": _accumulator.failover_count,
        "redis_cache_hits": _accumulator.redis_cache_hits,
        "redis_cache_misses": _accumulator.redis_cache_misses,
        "peak_concurrent_sse": _accumulator.peak_concurrent_sse,
        "agent_stats": agent_stats_list,
    }


# ==============================================================================
# FLUSH VÀO REDIS (T10.2.3)
# ==============================================================================
async def _flush_events(redis: Optional[Redis], events: list[dict]) -> None:
    """Cập nhật Redis counters rpm, tpm, errors:5xx và nạp vào in-memory accumulator."""
    if not events:
        return

    minute = _minute_bucket()
    rpm_key = f"rpm:{minute}"
    tpm_key = f"tpm:{minute}"
    err5xx_key = f"errors:5xx:{minute}"

    rpm_delta = 0
    group_deltas = {"chat": 0, "eval": 0, "auth": 0, "other": 0}
    tpm_delta = 0
    err4xx_delta = 0
    err429_delta = 0
    err5xx_delta = 0

    for ev in events:
        ev_type = ev.get("type")
        if ev_type == "token_usage":
            tpm_delta += ev.get("total_tokens", 0)
            _accumulator.add_token_event(ev)
        elif ev_type == "cache_event":
            _accumulator.add_cache_event(bool(ev.get("hit", False)))
        elif ev_type == "sse_peak":
            _accumulator.observe_sse_session(int(ev.get("active_sessions", 0) or 0))
        elif ev_type == "failover":
            _accumulator.add_failover_event(is_429=bool(ev.get("is_429", False)))
        elif ev_type == "error_429":
            err429_delta += 1
            _accumulator.add_error_429_event()
        else:
            rpm_delta += 1
            grp = ev.get("endpoint_group", "other")
            if grp not in group_deltas:
                grp = "other"
            group_deltas[grp] += 1

            sc = ev.get("status_code", 200)
            if sc == 429:
                err429_delta += 1
                err4xx_delta += 1
            elif 400 <= sc < 500:
                err4xx_delta += 1
            elif sc >= 500:
                err5xx_delta += 1
            _accumulator.add_http_event(ev)

    # Cập nhật in-memory minute counter (giữ tối đa 90 phút gần nhất)
    if minute not in _live_minute_counters:
        _live_minute_counters[minute] = {
            "rpm": 0, "chat": 0, "eval": 0, "auth": 0, "other": 0,
            "tpm": 0, "err4xx": 0, "err429": 0, "err5xx": 0,
        }
        if len(_live_minute_counters) > 90:
            oldest_key = sorted(_live_minute_counters.keys())[0]
            _live_minute_counters.pop(oldest_key, None)

    bucket_mem = _live_minute_counters[minute]
    bucket_mem["rpm"] += rpm_delta
    for grp_k, grp_v in group_deltas.items():
        bucket_mem[grp_k] = bucket_mem.get(grp_k, 0) + grp_v
    bucket_mem["tpm"] += tpm_delta
    bucket_mem["err4xx"] += err4xx_delta
    bucket_mem["err429"] += err429_delta
    bucket_mem["err5xx"] += err5xx_delta

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
        print(f"[TelemetryWorker] Lỗi khi ghi Redis: {err}")


# ==============================================================================
# GHI BATCH XUỐNG DATABASE MỖI 60 GIÂY (T10.2.4)
# ==============================================================================
def flush_metrics_to_db(db_session=None) -> Dict[str, Any]:
    """
    Gom số liệu từ _accumulator và upsert xuống 2 bảng:
      - system_metrics_hourly
      - system_agent_metrics_hourly
    Đồng thời kiểm tra ngưỡng SLA và cập nhật system_incidents_log.
    Hàm này có thể gọi trực tiếp trong test hoặc qua periodic worker.
    """
    # Snapshot số liệu hiện tại và reset accumulator in-place để giữ nguyên singleton reference
    snap = _accumulator.snapshot_and_reset()

    bucket_ts = _hour_bucket()

    # Tính toán latency percentiles
    avg_lat = int(sum(snap.latencies) / len(snap.latencies)) if snap.latencies else 0
    p50_lat = _calc_percentile(snap.latencies, 50.0) if snap.latencies else 0
    p95_lat = _calc_percentile(snap.latencies, 95.0) if snap.latencies else 0
    p99_lat = _calc_percentile(snap.latencies, 99.0) if snap.latencies else 0
    avg_ttft = int(sum(snap.ttfts) / len(snap.ttfts)) if snap.ttfts else 0

    should_close_db = False
    db = db_session
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        # 1. UPSERT vào system_metrics_hourly
        upsert_metrics_sql = text("""
            INSERT INTO system_metrics_hourly (
                bucket_timestamp, total_requests, chat_requests, eval_requests, auth_requests, other_requests,
                prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd,
                avg_latency_ms, p50_latency_ms, p95_latency_ms, p99_latency_ms, avg_ttft_ms,
                status_2xx_count, status_4xx_count, status_5xx_count, gemini_429_count, failover_count,
                redis_cache_hits, redis_cache_misses, peak_concurrent_sse
            ) VALUES (
                :bucket_ts, :total_requests, :chat_requests, :eval_requests, :auth_requests, :other_requests,
                :prompt_tokens, :completion_tokens, :total_tokens, :estimated_cost_usd,
                :avg_latency_ms, :p50_latency_ms, :p95_latency_ms, :p99_latency_ms, :avg_ttft_ms,
                :status_2xx_count, :status_4xx_count, :status_5xx_count, :gemini_429_count, :failover_count,
                :redis_cache_hits, :redis_cache_misses, :peak_concurrent_sse
            )
            ON CONFLICT (bucket_timestamp) DO UPDATE SET
                total_requests = system_metrics_hourly.total_requests + EXCLUDED.total_requests,
                chat_requests = system_metrics_hourly.chat_requests + EXCLUDED.chat_requests,
                eval_requests = system_metrics_hourly.eval_requests + EXCLUDED.eval_requests,
                auth_requests = system_metrics_hourly.auth_requests + EXCLUDED.auth_requests,
                other_requests = system_metrics_hourly.other_requests + EXCLUDED.other_requests,
                prompt_tokens = system_metrics_hourly.prompt_tokens + EXCLUDED.prompt_tokens,
                completion_tokens = system_metrics_hourly.completion_tokens + EXCLUDED.completion_tokens,
                total_tokens = system_metrics_hourly.total_tokens + EXCLUDED.total_tokens,
                estimated_cost_usd = system_metrics_hourly.estimated_cost_usd + EXCLUDED.estimated_cost_usd,
                avg_latency_ms = CASE WHEN EXCLUDED.avg_latency_ms > 0 THEN EXCLUDED.avg_latency_ms ELSE system_metrics_hourly.avg_latency_ms END,
                p50_latency_ms = CASE WHEN EXCLUDED.p50_latency_ms > 0 THEN EXCLUDED.p50_latency_ms ELSE system_metrics_hourly.p50_latency_ms END,
                p95_latency_ms = CASE WHEN EXCLUDED.p95_latency_ms > 0 THEN EXCLUDED.p95_latency_ms ELSE system_metrics_hourly.p95_latency_ms END,
                p99_latency_ms = CASE WHEN EXCLUDED.p99_latency_ms > 0 THEN EXCLUDED.p99_latency_ms ELSE system_metrics_hourly.p99_latency_ms END,
                avg_ttft_ms = CASE WHEN EXCLUDED.avg_ttft_ms > 0 THEN EXCLUDED.avg_ttft_ms ELSE system_metrics_hourly.avg_ttft_ms END,
                status_2xx_count = system_metrics_hourly.status_2xx_count + EXCLUDED.status_2xx_count,
                status_4xx_count = system_metrics_hourly.status_4xx_count + EXCLUDED.status_4xx_count,
                status_5xx_count = system_metrics_hourly.status_5xx_count + EXCLUDED.status_5xx_count,
                gemini_429_count = system_metrics_hourly.gemini_429_count + EXCLUDED.gemini_429_count,
                failover_count = system_metrics_hourly.failover_count + EXCLUDED.failover_count,
                redis_cache_hits = system_metrics_hourly.redis_cache_hits + EXCLUDED.redis_cache_hits,
                redis_cache_misses = system_metrics_hourly.redis_cache_misses + EXCLUDED.redis_cache_misses,
                peak_concurrent_sse = GREATEST(system_metrics_hourly.peak_concurrent_sse, EXCLUDED.peak_concurrent_sse);
        """)

        db.execute(
            upsert_metrics_sql,
            {
                "bucket_ts": bucket_ts,
                "total_requests": snap.total_requests,
                "chat_requests": snap.chat_requests,
                "eval_requests": snap.eval_requests,
                "auth_requests": snap.auth_requests,
                "other_requests": snap.other_requests,
                "prompt_tokens": snap.prompt_tokens,
                "completion_tokens": snap.completion_tokens,
                "total_tokens": snap.total_tokens,
                "estimated_cost_usd": round(snap.estimated_cost_usd, 6),
                "avg_latency_ms": avg_lat,
                "p50_latency_ms": p50_lat,
                "p95_latency_ms": p95_lat,
                "p99_latency_ms": p99_lat,
                "avg_ttft_ms": avg_ttft,
                "status_2xx_count": snap.status_2xx_count,
                "status_4xx_count": snap.status_4xx_count,
                "status_5xx_count": snap.status_5xx_count,
                "gemini_429_count": snap.gemini_429_count,
                "failover_count": snap.failover_count,
                "redis_cache_hits": snap.redis_cache_hits,
                "redis_cache_misses": snap.redis_cache_misses,
                "peak_concurrent_sse": snap.peak_concurrent_sse,
            },
        )

        # 2. UPSERT vào system_agent_metrics_hourly
        upsert_agent_sql = text("""
            INSERT INTO system_agent_metrics_hourly (
                bucket_timestamp, agent_name, model_name, request_count,
                prompt_tokens, completion_tokens, total_cost_usd, avg_latency_ms, error_count
            ) VALUES (
                :bucket_ts, :agent_name, :model_name, :request_count,
                :prompt_tokens, :completion_tokens, :total_cost_usd, :avg_latency_ms, :error_count
            )
            ON CONFLICT (bucket_timestamp, agent_name, model_name) DO UPDATE SET
                request_count = system_agent_metrics_hourly.request_count + EXCLUDED.request_count,
                prompt_tokens = system_agent_metrics_hourly.prompt_tokens + EXCLUDED.prompt_tokens,
                completion_tokens = system_agent_metrics_hourly.completion_tokens + EXCLUDED.completion_tokens,
                total_cost_usd = system_agent_metrics_hourly.total_cost_usd + EXCLUDED.total_cost_usd,
                avg_latency_ms = CASE WHEN EXCLUDED.avg_latency_ms > 0 THEN EXCLUDED.avg_latency_ms ELSE system_agent_metrics_hourly.avg_latency_ms END,
                error_count = system_agent_metrics_hourly.error_count + EXCLUDED.error_count;
        """)

        for (ag_name, mod_name), ag_data in snap.agent_stats.items():
            ag_avg_lat = int(sum(ag_data["latencies"]) / len(ag_data["latencies"])) if ag_data["latencies"] else 0
            db.execute(
                upsert_agent_sql,
                {
                    "bucket_ts": bucket_ts,
                    "agent_name": ag_name,
                    "model_name": mod_name,
                    "request_count": ag_data["request_count"],
                    "prompt_tokens": ag_data["prompt_tokens"],
                    "completion_tokens": ag_data["completion_tokens"],
                    "total_cost_usd": round(ag_data["total_cost_usd"], 6),
                    "avg_latency_ms": ag_avg_lat,
                    "error_count": ag_data["error_count"],
                },
            )

        # 3. ĐÁNH GIÁ NGƯỠNG SLA & GHI NHẬN SỰ CỐ
        # Đảm bảo session nạp lại dữ liệu mới nhất sau câu lệnh execute raw SQL
        db.expire_all()
        row = db.query(models.SystemMetricsHourly).filter_by(bucket_timestamp=bucket_ts).first()

        # Tính tỷ lệ 5xx và P95 trên cả cửa sổ batch 60s gần nhất lẫn giờ tích lũy
        snap_err_rate = (snap.status_5xx_count / snap.total_requests) if snap.total_requests >= 5 else 0.0
        row_err_rate = (row.status_5xx_count / row.total_requests) if (row and row.total_requests >= 5) else 0.0
        effective_err_rate = max(snap_err_rate, row_err_rate)

        effective_p95 = max(p95_lat, row.p95_latency_ms if row else 0)

        if (row and row.total_requests >= 5) or snap.total_requests >= 5:
            # Rule 1: Lỗi 5xx vượt quá 2%
            if effective_err_rate > _SLA_ERROR_5XX_MAX_RATE:
                _trigger_or_update_incident(
                    db,
                    incident_type="ERROR_SPIKE",
                    severity="CRITICAL",
                    metric_name="status_5xx_rate",
                    threshold=2.0,
                    actual=round(effective_err_rate * 100, 2),
                    message=f"Tỷ lệ lỗi máy chủ (5xx) đạt {round(effective_err_rate * 100, 1)}%, vượt ngưỡng an toàn 2.0%",
                )
            elif snap.total_requests >= 5 and snap_err_rate <= _SLA_ERROR_5XX_MAX_RATE and row_err_rate <= _SLA_ERROR_5XX_MAX_RATE:
                _resolve_incident_if_active(db, "ERROR_SPIKE")

            # Rule 2: P95 latency vượt 1800ms
            if effective_p95 > _SLA_P95_MAX_MS:
                _trigger_or_update_incident(
                    db,
                    incident_type="HIGH_LATENCY",
                    severity="WARNING",
                    metric_name="p95_latency_ms",
                    threshold=1800.0,
                    actual=float(effective_p95),
                    message=f"Độ trễ phản hồi P95 đạt {effective_p95}ms, vượt ngưỡng SLA 1800ms",
                )
            elif snap.total_requests >= 5 and p95_lat <= _SLA_P95_MAX_MS and (not row or row.p95_latency_ms <= _SLA_P95_MAX_MS):
                _resolve_incident_if_active(db, "HIGH_LATENCY")

        db.commit()
        return {
            "status": "success",
            "bucket_timestamp": bucket_ts.isoformat(),
            "flushed_requests": snap.total_requests,
            "flushed_tokens": snap.total_tokens,
        }

    except Exception as e:
        db.rollback()
        print(f"[TelemetryWorker] Lỗi khi ghi batch xuống database: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if should_close_db:
            db.close()


def _trigger_or_update_incident(
    db, incident_type: str, severity: str, metric_name: str, threshold: float, actual: float, message: str
):
    """Tạo mới hoặc cập nhật sự cố SLA đang ACTIVE."""
    active = (
        db.query(models.SystemIncidentLog)
        .filter_by(incident_type=incident_type, status="ACTIVE")
        .first()
    )
    if active:
        active.actual_value = actual
        active.message = message
    else:
        new_inc = models.SystemIncidentLog(
            id=f"inc_{uuid.uuid4().hex[:12]}",
            incident_type=incident_type,
            severity=severity,
            metric_name=metric_name,
            threshold_value=threshold,
            actual_value=actual,
            message=message,
            status="ACTIVE",
        )
        db.add(new_inc)


def _resolve_incident_if_active(db, incident_type: str):
    """Đánh dấu RESOLVED cho sự cố đã trở lại bình thường."""
    active_incidents = (
        db.query(models.SystemIncidentLog)
        .filter_by(incident_type=incident_type, status="ACTIVE")
        .all()
    )
    now = datetime.now(timezone.utc)
    for inc in active_incidents:
        inc.status = "RESOLVED"
        inc.resolved_at = now


# ==============================================================================
# REAL TELEMETRY ONLY — TẮT SEEDER DỮ LIỆU GIẢ LẬP
# ==============================================================================
def ensure_baseline_metrics(db=None):
    """
    Đã vô hiệu hóa synthetic baseline seeder để đảm bảo Dashboard chỉ hiển thị
    100% số liệu thực tế đo được từ TelemetryMiddleware, Redis và Gemini SDK.
    """
    return {
        "status": "disabled",
        "seeded_hours": 0,
        "message": "Real telemetry mode active - synthetic baseline seeding disabled.",
    }


# ==============================================================================
# WORKER LOOPS
# ==============================================================================
async def start_telemetry_worker() -> None:
    """
    1. Vòng lặp 1 giây: Tiêu thụ telemetry_queue và cập nhật Redis counters.
    2. Vòng lặp 60 giây: Ghi batch xuống Neon PostgreSQL (T10.2.4).
    """
    redis = _get_upstash_redis()
    print("[TelemetryWorker] ✅ Đã khởi động Telemetry Batch Worker (100% Real Telemetry Mode).")

    last_db_flush_time = asyncio.get_event_loop().time()

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

            # T10.2.4: Ghi batch xuống Database mỗi 60 giây
            current_time = asyncio.get_event_loop().time()
            if current_time - last_db_flush_time >= _DB_FLUSH_INTERVAL_SECONDS:
                last_db_flush_time = current_time
                flush_metrics_to_db()

        except Exception as err:
            print(f"[TelemetryWorker] Lỗi không xác định: {err}")

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
