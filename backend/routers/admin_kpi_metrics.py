"""
US 10.2 (Task T10.2.5): Router Quản Trị Hệ Thống KPI & Observability Hub
========================================================================
Cung cấp 8 endpoints chuyên biệt phục vụ Admin System KPI Dashboard:
  1. GET /admin/kpi/overview         : 4 thẻ KPI tổng hợp (Requests, Tokens & Cost, Latency/TTFT, Lỗi)
  2. GET /admin/kpi/throughput       : Biểu đồ lưu lượng Throughput (Phút RPM, Giờ RPH, Ngày Daily)
  3. GET /admin/kpi/tokens           : Tiêu thụ Token (Prompt vs Completion) & Chi phí theo 4 model AI
  4. GET /admin/kpi/latency          : Độ trễ phân vị P50, P95, P99 và chỉ số TTFT (Time To First Token)
  5. GET /admin/kpi/agents           : Biểu đồ Donut phân bổ 6 phân hệ Agent (Chat, Classifier, Flashcard, ParentReport, Email, Fallback)
  6. GET /admin/kpi/traffic-heatmap  : Bản đồ nhiệt giờ cao điểm Peak Traffic Heatmap (7 ngày x 24 giờ)
  7. GET /admin/kpi/infrastructure   : Sức chứa hạ tầng (Neon DB Pool, Redis Hit/Miss, Active SSE Sessions)
  8. GET /admin/kpi/incidents        : Trạng thái vi phạm ngưỡng SLA (5xx > 2%, P95 > 1800ms) phục vụ Banner đỏ
  +. GET /admin/kpi/export           : Xuất toàn bộ báo cáo KPI dạng CSV / JSON
"""

import csv
import io
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, desc, func

from database import get_db, SessionLocal
import models
import schemas
import dependencies
from middleware.telemetry_middleware import get_active_sse_sessions
from workers.telemetry_batch_worker import (
    _get_upstash_redis,
    _minute_bucket,
    _hour_bucket,
    get_live_minute_stats,
    get_live_accumulator_snapshot,
)

router = APIRouter(tags=["Admin KPI Metrics & Observability"])

# Tỷ giá quy đổi cố định USD -> VND
USD_TO_VND_RATE = 25450.0

# Bảng giá thực tế các Model Google Gemini (USD / 1M tokens)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # 6 Model Configuration Roles (US 10.3)
    "gemini-3.8-flash": {
        "prompt": 0.10,
        "completion": 0.40,
        "pricing_label": "$0.10 / 1M prompt, $0.40 / 1M completion",
    },
    "gemini-3.5-flash": {
        "prompt": 0.075,
        "completion": 0.30,
        "pricing_label": "$0.075 / 1M prompt, $0.30 / 1M completion",
    },
    "gemini-3.5-flash-lite": {
        "prompt": 0.0375,
        "completion": 0.15,
        "pricing_label": "$0.0375 / 1M prompt, $0.15 / 1M completion",
    },
    "gemini-3.1-flash-lite": {
        "prompt": 0.030,
        "completion": 0.12,
        "pricing_label": "$0.030 / 1M prompt, $0.12 / 1M completion",
    },
    # Legacy / LTS models
    "gemini-2.5-flash": {
        "prompt": 0.075,
        "completion": 0.30,
        "pricing_label": "$0.075 / 1M prompt, $0.30 / 1M completion",
    },
    "gemini-2.0-flash": {
        "prompt": 0.075,
        "completion": 0.30,
        "pricing_label": "$0.075 / 1M prompt, $0.30 / 1M completion",
    },
    "gemini-2.0-flash-lite": {
        "prompt": 0.0375,
        "completion": 0.15,
        "pricing_label": "$0.0375 / 1M prompt, $0.15 / 1M completion",
    },
    "gemini-1.5-pro": {
        "prompt": 1.25,
        "completion": 5.00,
        "pricing_label": "$1.25 / 1M prompt, $5.00 / 1M completion",
    },
    "default": {
        "prompt": 0.075,
        "completion": 0.30,
        "pricing_label": "$0.075 / 1M prompt, $0.30 / 1M completion",
    },
}


def _get_configured_models() -> Dict[str, str]:
    """Đọc 6 model phân hệ đang cấu hình từ SystemConfigService (US 10.3)."""
    defaults = {
        "primary_model": "gemini-3.8-flash",
        "classifier_model": "gemini-3.1-flash-lite",
        "flashcard_model": "gemini-3.5-flash-lite",
        "parent_insight_model": "gemini-3.5-flash",
        "email_model": "gemini-3.1-flash-lite",
        "backup_model": "gemini-3.5-flash-lite",
    }
    try:
        from services.system_config_service import get_system_settings
        cfg = get_system_settings()
        return {k: (cfg.get(k) or v) for k, v in defaults.items()}
    except Exception:
        return defaults


def _calc_tokens_cost(prompt_tokens: int, completion_tokens: int, model_name: str) -> tuple[float, int]:
    """Tính chi phí USD và VND theo model."""
    pricing = MODEL_PRICING.get(model_name, MODEL_PRICING["default"])
    cost_usd = (prompt_tokens / 1_000_000.0) * pricing["prompt"] + (completion_tokens / 1_000_000.0) * pricing["completion"]
    cost_usd = round(cost_usd, 6)
    cost_vnd = int(round(cost_usd * USD_TO_VND_RATE))
    return cost_usd, cost_vnd


TZ_VN = timezone(timedelta(hours=7))


def _to_vn_time(dt: datetime) -> datetime:
    """Chuyển đổi datetime (naive UTC hoặc aware) sang giờ Việt Nam (UTC+7)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_VN)


def _vn_day_start_utc(days_ago: int = 0) -> tuple[datetime, Any]:
    """Trả về (mốc 00:00 giờ VN dưới dạng UTC, ngày theo giờ VN) cách đây days_ago ngày."""
    now_vn = _to_vn_time(datetime.now(timezone.utc))
    target_vn_date = now_vn.date() - timedelta(days=days_ago)
    start_vn = datetime.combine(target_vn_date, datetime.min.time(), tzinfo=TZ_VN)
    return start_vn.astimezone(timezone.utc), target_vn_date


def _to_utc_hour(dt: datetime) -> datetime:
    """Chuẩn hóa timestamp về đầu giờ UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)


_SUBSYSTEM_SPECS = [
    {
        "id": "Chat",
        "role_name": "Chat Socratic Chính",
        "agent_title": "Gia Sư Socratic (Chat)",
        "description": "Đối thoại sư phạm gợi mở 2-4 câu, bám sát sách giáo khoa Toán 4-9",
        "cfg_key": "primary_model",
        "color": "#C1762A",
        "icon": "MessageSquare",
    },
    {
        "id": "Classifier",
        "role_name": "Phân Loại SGK & Tiêu Đề",
        "agent_title": "Phân Loại Bài Toán & Đặt Tên",
        "description": "Nhận diện chuyên đề SGK và đặt tên bài toán thân thiện",
        "cfg_key": "classifier_model",
        "color": "#8C4905",
        "icon": "Layers",
    },
    {
        "id": "Flashcard",
        "role_name": "Sổ Tay & Flashcard",
        "agent_title": "Sổ Tay & Thẻ Ghi Nhớ (Flashcard)",
        "description": "Trích xuất công thức trọng tâm và tóm tắt bước giải vào sổ tay",
        "cfg_key": "flashcard_model",
        "color": "#2563EB",
        "icon": "BookOpen",
    },
    {
        "id": "ParentReport",
        "role_name": "Báo Cáo Phụ Huynh",
        "agent_title": "Báo Cáo Phụ Huynh (Parent Insights)",
        "description": "Quét toàn bộ lịch sử tuần để đánh giá tính tự lập gửi phụ huynh",
        "cfg_key": "parent_insight_model",
        "color": "#10B981",
        "icon": "GraduationCap",
    },
    {
        "id": "Email",
        "role_name": "Email Cảnh Báo PH",
        "agent_title": "Email Cảnh Báo Phụ Huynh",
        "description": "Soạn và gửi email cảnh báo học tập / an toàn tới phụ huynh",
        "cfg_key": "email_model",
        "color": "#F59E0B",
        "icon": "ShieldAlert",
    },
    {
        "id": "Fallback",
        "role_name": "Dự Phòng Failover",
        "agent_title": "Dự Phòng & Failover",
        "description": "Mô hình dự phòng & Failover khi model chính gặp sự cố",
        "cfg_key": "backup_model",
        "color": "#6B7280",
        "icon": "Cpu",
    },
]


def _aggregate_subsystem_metrics(
    db: Session,
    start_dt: datetime,
    live_snap: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Tổng hợp số liệu thực tế của 6 phân hệ từ bảng system_agent_metrics_hourly
    cộng dồn phần live chưa flush trong bộ đệm. Không dùng dữ liệu giả lập.
    """
    rows = (
        db.query(
            models.SystemAgentMetricsHourly.agent_name,
            models.SystemAgentMetricsHourly.model_name,
            func.sum(models.SystemAgentMetricsHourly.request_count).label("reqs"),
            func.sum(models.SystemAgentMetricsHourly.prompt_tokens).label("prompt_tok"),
            func.sum(models.SystemAgentMetricsHourly.completion_tokens).label("comp_tok"),
            func.sum(models.SystemAgentMetricsHourly.total_cost_usd).label("cost_usd"),
            func.avg(models.SystemAgentMetricsHourly.avg_latency_ms).label("avg_lat"),
        )
        .filter(models.SystemAgentMetricsHourly.bucket_timestamp >= start_dt)
        .group_by(
            models.SystemAgentMetricsHourly.agent_name,
            models.SystemAgentMetricsHourly.model_name,
        )
        .all()
    )

    cfg_models = _get_configured_models()
    agg_by_agent: Dict[str, Dict[str, Any]] = {}

    def _accumulate(agent_id: str, mod_name: str, reqs: int, p_tok: int, c_tok: int, cost_usd: float, avg_lat: int):
        entry = agg_by_agent.setdefault(agent_id, {
            "request_count": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            "lat_weighted_sum": 0,
            "lat_count": 0,
            "model_reqs": {},
        })
        entry["request_count"] += reqs
        entry["prompt_tokens"] += p_tok
        entry["completion_tokens"] += c_tok
        entry["cost_usd"] += cost_usd
        if avg_lat > 0 and reqs > 0:
            entry["lat_weighted_sum"] += avg_lat * reqs
            entry["lat_count"] += reqs
        if mod_name and reqs > 0:
            entry["model_reqs"][mod_name] = entry["model_reqs"].get(mod_name, 0) + reqs

    for r in rows:
        _accumulate(
            r.agent_name,
            r.model_name,
            int(r.reqs or 0),
            int(r.prompt_tok or 0),
            int(r.comp_tok or 0),
            float(r.cost_usd or 0.0),
            int(r.avg_lat or 0),
        )

    for ag in live_snap.get("agent_stats", []):
        _accumulate(
            ag["agent_name"],
            ag["model_name"],
            int(ag.get("request_count", 0)),
            int(ag.get("prompt_tokens", 0)),
            int(ag.get("completion_tokens", 0)),
            float(ag.get("total_cost_usd", 0.0)),
            int(ag.get("avg_latency_ms", 0)),
        )

    raw_items: List[Dict[str, Any]] = []
    model_breakdown: Dict[str, Dict[str, Any]] = {}

    for spec in _SUBSYSTEM_SPECS:
        ag_id = spec["id"]
        assigned_model = cfg_models[spec["cfg_key"]]
        ag_data = agg_by_agent.get(ag_id, {})

        reqs = ag_data.get("request_count", 0)
        p_tok = ag_data.get("prompt_tokens", 0)
        c_tok = ag_data.get("completion_tokens", 0)
        t_tok = p_tok + c_tok
        c_usd = ag_data.get("cost_usd", 0.0)
        if c_usd == 0.0 and t_tok > 0:
            c_usd, _ = _calc_tokens_cost(p_tok, c_tok, assigned_model)
        c_vnd = int(round(c_usd * USD_TO_VND_RATE))

        model_reqs = ag_data.get("model_reqs", {})
        if model_reqs:
            used_model = max(model_reqs.items(), key=lambda kv: kv[1])[0]
        else:
            used_model = assigned_model

        lat_count = ag_data.get("lat_count", 0)
        avg_lat = int(round(ag_data["lat_weighted_sum"] / lat_count)) if lat_count > 0 else 0
        pricing_info = MODEL_PRICING.get(used_model, MODEL_PRICING["default"])

        raw_items.append({
            "spec": spec,
            "model_used": used_model,
            "request_count": reqs,
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "total_tokens": t_tok,
            "cost_usd": c_usd,
            "cost_vnd": c_vnd,
            "avg_latency_ms": avg_lat,
            "pricing": pricing_info.get("pricing_label", "$0.075 / 1M prompt, $0.30 / 1M completion"),
        })

        mb = model_breakdown.setdefault(used_model, {
            "name": used_model,
            "roles": [],
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "tokens": 0,
            "cost_usd": 0.0,
            "cost_vnd": 0,
            "percentage": 0.0,
            "pricing": pricing_info.get("pricing_label", "$0.075 / 1M prompt, $0.30 / 1M completion"),
        })
        mb["roles"].append(spec["role_name"])
        mb["prompt_tokens"] += p_tok
        mb["completion_tokens"] += c_tok
        mb["tokens"] += t_tok
        mb["cost_usd"] = round(mb["cost_usd"] + c_usd, 6)
        mb["cost_vnd"] = int(round(mb["cost_usd"] * USD_TO_VND_RATE))

    total_reqs = sum(item["request_count"] for item in raw_items)
    total_tokens = sum(item["total_tokens"] for item in raw_items)
    total_prompt = sum(item["prompt_tokens"] for item in raw_items)
    total_comp = sum(item["completion_tokens"] for item in raw_items)
    total_cost_usd = sum(item["cost_usd"] for item in raw_items)

    six_model_breakdown: List[Dict[str, Any]] = []
    agents_list: List[Dict[str, Any]] = []

    for item in raw_items:
        spec = item["spec"]
        req_pct = round((item["request_count"] / total_reqs) * 100, 1) if total_reqs > 0 else 0.0
        tok_pct = round((item["total_tokens"] / total_tokens) * 100, 1) if total_tokens > 0 else 0.0
        # Nếu chỉ có request HTTP hoặc token thực chưa phân biệt được, ưu tiên tok_pct khi có token
        share_pct = tok_pct if total_tokens > 0 else req_pct

        six_model_breakdown.append({
            "role_id": spec["id"],
            "role_name": spec["role_name"],
            "model_name": item["model_used"],
            "request_count": item["request_count"],
            "prompt_tokens": item["prompt_tokens"],
            "completion_tokens": item["completion_tokens"],
            "total_tokens": item["total_tokens"],
            "percentage": share_pct,
            "cost_usd": round(item["cost_usd"], 4),
            "cost_vnd": item["cost_vnd"],
            "pricing": item["pricing"],
            "color": spec["color"],
        })

        agents_list.append({
            "id": spec["id"],
            "name": spec["agent_title"],
            "description": spec["description"],
            "model_used": item["model_used"],
            "request_count": item["request_count"],
            "prompt_tokens": item["prompt_tokens"],
            "completion_tokens": item["completion_tokens"],
            "total_tokens": item["total_tokens"],
            "cost_usd": round(item["cost_usd"], 4),
            "cost_vnd": item["cost_vnd"],
            "avg_latency_ms": item["avg_latency_ms"],
            "request_percentage": req_pct,
            "token_percentage": tok_pct,
            "color": spec["color"],
        })

    for mb in model_breakdown.values():
        mb["cost_usd"] = round(mb["cost_usd"], 4)
        mb["percentage"] = round((mb["tokens"] / total_tokens) * 100, 1) if total_tokens > 0 else 0.0

    return {
        "six_model_breakdown": six_model_breakdown,
        "model_breakdown": model_breakdown,
        "agents": agents_list,
        "total_requests": total_reqs,
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_comp,
        "total_cost_usd": total_cost_usd,
    }


# ==============================================================================
# 1. GET /overview : 4 Thẻ KPI Tổng Hợp Đầu Trang
# ==============================================================================
@router.get("/admin/kpi/overview")
@router.get("/admin/metrics/overview")
async def get_kpi_overview(
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-01 & AC-KPI-02:
    Trả về số liệu 4 thẻ KPI tổng quan hệ thống hôm nay (DB + Live In-Memory Delta):
      1. Lưu lượng (Total Requests hôm nay, RPM hiện tại)
      2. Tiêu thụ Token & Chi phí API (Prompt/Completion Tokens, USD, VND)
      3. Độ trễ & SLA (P50, P95, TTFT)
      4. Độ tin cậy & Hạ tầng (Tỷ lệ thành công %, Lỗi 2xx/4xx/429/5xx, Active SSE)
    """
    now = datetime.now(timezone.utc)
    start_of_today, _ = _vn_day_start_utc(0)

    # 1. Đọc số liệu tích lũy hôm nay theo giờ VN (00:00 UTC+7) + live unsaved delta trong bộ đệm
    rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_of_today)
        .all()
    )
    live_snap = get_live_accumulator_snapshot()

    db_requests = sum(r.total_requests for r in rows)
    db_chat = sum(r.chat_requests for r in rows)
    db_eval = sum(r.eval_requests for r in rows)
    db_auth = sum(r.auth_requests for r in rows)
    db_other = sum(r.other_requests for r in rows)

    tot_requests = db_requests + live_snap["total_requests"]
    tot_chat = db_chat + live_snap["chat_requests"]
    tot_eval = db_eval + live_snap["eval_requests"]
    tot_auth = db_auth + live_snap["auth_requests"]
    tot_other = db_other + live_snap["other_requests"]

    # So sánh tăng trưởng thực tế với ngày hôm qua theo giờ VN
    start_of_yesterday, _ = _vn_day_start_utc(1)
    yesterday_requests = (
        db.query(func.sum(models.SystemMetricsHourly.total_requests))
        .filter(
            models.SystemMetricsHourly.bucket_timestamp >= start_of_yesterday,
            models.SystemMetricsHourly.bucket_timestamp < start_of_today,
        )
        .scalar()
        or 0
    )
    if yesterday_requests > 0:
        requests_growth_pct = round(((tot_requests - yesterday_requests) / yesterday_requests) * 100, 1)
    else:
        requests_growth_pct = 0.0

    db_prompt = sum(r.prompt_tokens for r in rows)
    db_comp = sum(r.completion_tokens for r in rows)
    tot_prompt = db_prompt + live_snap["prompt_tokens"]
    tot_completion = db_comp + live_snap["completion_tokens"]
    tot_tokens = tot_prompt + tot_completion

    tot_cost_usd = sum(float(r.estimated_cost_usd or 0) for r in rows) + float(live_snap["estimated_cost_usd"])
    tot_cost_vnd = int(round(tot_cost_usd * USD_TO_VND_RATE))

    # Latency percentiles thực tế hôm nay (DB + Live unsaved)
    p50_list = [r.p50_latency_ms for r in rows if r.p50_latency_ms > 0]
    p95_list = [r.p95_latency_ms for r in rows if r.p95_latency_ms > 0]
    p99_list = [r.p99_latency_ms for r in rows if r.p99_latency_ms > 0]
    ttft_list = [r.avg_ttft_ms for r in rows if r.avg_ttft_ms > 0]

    if live_snap.get("total_requests", 0) > 0:
        if live_snap.get("p50_latency_ms", 0) > 0:
            p50_list.append(live_snap["p50_latency_ms"])
        if live_snap.get("p95_latency_ms", 0) > 0:
            p95_list.append(live_snap["p95_latency_ms"])
        if live_snap.get("p99_latency_ms", 0) > 0:
            p99_list.append(live_snap["p99_latency_ms"])
    if live_snap.get("avg_ttft_ms", 0) > 0:
        ttft_list.append(live_snap["avg_ttft_ms"])

    p50_ms = int(sum(p50_list) / len(p50_list)) if p50_list else 0
    p95_ms = int(sum(p95_list) / len(p95_list)) if p95_list else 0
    p99_ms = int(sum(p99_list) / len(p99_list)) if p99_list else 0
    avg_ttft_ms = int(sum(ttft_list) / len(ttft_list)) if ttft_list else 0
    avg_lat = int((p50_ms + p95_ms) / 2) if (p50_ms or p95_ms) else 0

    # Phân phối mã lỗi HTTP thực tế (Client 4xx, Quota 429, Server 5xx)
    tot_4xx = sum(r.status_4xx_count for r in rows) + live_snap["status_4xx_count"]
    tot_5xx = sum(r.status_5xx_count for r in rows) + live_snap["status_5xx_count"]
    tot_429 = sum(r.gemini_429_count for r in rows) + live_snap["gemini_429_count"]
    tot_2xx = sum(r.status_2xx_count for r in rows) + live_snap["status_2xx_count"]

    if tot_requests > 0:
        error_rate_pct = round((tot_5xx / tot_requests) * 100, 2)
        client_error_rate_pct = round(((tot_4xx + tot_429) / tot_requests) * 100, 2)
        success_rate_pct = round((tot_2xx / tot_requests) * 100, 2)
    else:
        error_rate_pct = 0.0
        client_error_rate_pct = 0.0
        success_rate_pct = 0.0

    # 2. Đọc Live RPM & TPM từ Upstash Redis + bộ nhớ cục bộ cho phút hiện tại
    m_bucket = _minute_bucket(now)
    mem_stats = get_live_minute_stats(m_bucket)
    redis = _get_upstash_redis()
    redis_rpm = 0
    redis_tpm = 0
    if redis:
        try:
            val_rpm = await redis.get(f"rpm:{m_bucket}")
            redis_rpm = int(val_rpm) if val_rpm else 0
            val_tpm = await redis.get(f"tpm:{m_bucket}")
            redis_tpm = int(val_tpm) if val_tpm else 0
        except Exception:
            pass

    live_rpm = max(redis_rpm, mem_stats["rpm"])
    live_tpm = max(redis_tpm, mem_stats["tpm"])

    # Active SSE streaming sessions
    active_sse = get_active_sse_sessions()

    # Trạng thái tổng quan hệ thống
    system_health = "HEALTHY"
    if (tot_requests >= 5 and error_rate_pct > 2.0) or tot_5xx > 20:
        system_health = "CRITICAL"
    elif p95_ms > 1800:
        system_health = "DEGRADED"

    return {
        "status": "success",
        "timestamp": now.isoformat(),
        # Thẻ 1: Throughput
        "throughput": {
            "total_requests_today": tot_requests,
            "rpm_current": live_rpm,
            "requests_growth_pct": requests_growth_pct,
            "chat_requests": tot_chat,
            "eval_requests": tot_eval,
            "auth_requests": tot_auth,
            "other_requests": tot_other,
        },
        # Thẻ 2: Token & Cost
        "tokens_and_cost": {
            "total_tokens_today": tot_tokens,
            "prompt_tokens_today": tot_prompt,
            "completion_tokens_today": tot_completion,
            "tpm_current": live_tpm,
            "cost_usd_today": round(tot_cost_usd, 4),
            "cost_vnd_today": tot_cost_vnd,
            "cost_projection_month_usd": round(tot_cost_usd * 30, 2),
            "cost_projection_month_vnd": int(round(tot_cost_usd * 30 * USD_TO_VND_RATE)),
        },
        # Thẻ 3: Latency & SLA
        "latency_and_sla": {
            "avg_latency_ms": avg_lat,
            "p50_latency_ms": p50_ms,
            "p95_latency_ms": p95_ms,
            "p99_latency_ms": p99_ms,
            "current_ttft_ms": avg_ttft_ms,
            "p50_status": "optimal" if p50_ms < 800 else "high",
            "p95_status": "optimal" if p95_ms < 1800 else "high",
            "ttft_status": "optimal" if avg_ttft_ms < 500 else "acceptable",
        },
        # Thẻ 4: Reliability & HTTP Status Matrix
        "reliability": {
            "success_rate_pct": success_rate_pct,
            "error_rate_pct": error_rate_pct,
            "client_error_rate_pct": client_error_rate_pct,
            "status_2xx_count_today": tot_2xx,
            "status_4xx_count_today": tot_4xx,
            "status_5xx_count_today": tot_5xx,
            "gemini_429_count_today": tot_429,
            "active_sse_sessions": active_sse,
            "system_health": system_health,
        },
    }


# ==============================================================================
# 2. GET /throughput : Biểu Đồ Lưu Lượng (RPM 60m / RPH 24h / Daily 7d-30d)
# ==============================================================================
@router.get("/admin/kpi/throughput")
@router.get("/admin/metrics/throughput")
async def get_kpi_throughput(
    range_param: str = Query("24h", alias="range", description="1h | 24h | 7d | 30d"),
    granularity: Optional[str] = Query(None, description="minute | hour | day"),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-01:
    - Khi chọn chế độ xem theo phút trong 60 phút gần nhất (range=1h hoặc granularity=minute):
      Dashboard trả về mảng 60 điểm phút. Phút hiện tại đọc trực tiếp từ Redis `rpm:{minute}`.
      Khi học sinh gửi 3 câu chat, polling tiếp theo thấy ngay RPM tăng đúng 3 request!
    - Khi chọn range=24h: trả về 24 điểm giờ RPH.
    - Khi chọn range=7d hoặc 30d: trả về daily rollup.
    """
    now = datetime.now(timezone.utc)
    live_snap = get_live_accumulator_snapshot()

    # 1. Chế độ THEO PHÚT (60 phút gần nhất) — 100% Real Redis + Live Minute Memory
    if range_param == "1h" or granularity == "minute":
        redis = _get_upstash_redis()
        items = []
        minute_points = [now - timedelta(minutes=i) for i in range(59, -1, -1)]
        minute_keys = [_minute_bucket(t_pt) for t_pt in minute_points]

        # Đọc 60 phút từ Redis (1 lệnh mget cho lịch sử + get phút hiện tại)
        redis_rpm_map: Dict[str, int] = {}
        cur_min_str = minute_keys[-1]
        if redis:
            try:
                val_cur = await redis.get(f"rpm:{cur_min_str}")
                if isinstance(val_cur, (int, str)) and str(val_cur).isdigit():
                    redis_rpm_map[cur_min_str] = int(val_cur)
            except Exception:
                pass
            try:
                if hasattr(redis, "mget"):
                    hist_vals = await redis.mget(*[f"rpm:{k}" for k in minute_keys[:-1]])
                    if isinstance(hist_vals, (list, tuple)):
                        for k, v in zip(minute_keys[:-1], hist_vals):
                            if isinstance(v, (int, str)) and str(v).isdigit():
                                redis_rpm_map[k] = int(v)
            except Exception:
                pass

        live_cur_rpm = max(
            redis_rpm_map.get(cur_min_str, 0),
            get_live_minute_stats(cur_min_str)["rpm"],
        )

        # Sinh chuỗi 60 phút thực tế theo giờ Việt Nam (UTC+7)
        for idx, t_point in enumerate(minute_points):
            m_str = minute_keys[idx]
            t_point_vn = _to_vn_time(t_point)
            disp_time = t_point_vn.strftime("%H:%M")
            mem_m = get_live_minute_stats(m_str)

            mem_rpm = mem_m.get("rpm", 0)
            rpm_val = max(redis_rpm_map.get(m_str, 0), mem_rpm)

            chat_r = mem_m.get("chat", 0)
            eval_r = mem_m.get("eval", 0)
            auth_r = mem_m.get("auth", 0)
            other_r = mem_m.get("other", 0)
            if rpm_val > (chat_r + eval_r + auth_r + other_r):
                other_r += rpm_val - (chat_r + eval_r + auth_r + other_r)

            items.append({
                "timestamp": t_point_vn.isoformat(),
                "display_time": disp_time,
                "is_current_minute": idx == len(minute_points) - 1,
                "requests": rpm_val,
                "chat_requests": chat_r,
                "eval_requests": eval_r,
                "auth_requests": auth_r,
                "other_requests": other_r,
                "errors_4xx": mem_m.get("err4xx", 0),
                "errors_429": mem_m.get("err429", 0),
                "errors_5xx": mem_m.get("err5xx", 0),
            })

        peak_rpm = max((x["requests"] for x in items), default=0)
        return {
            "range": "1h",
            "granularity": "minute",
            "peak_rpm": peak_rpm,
            "current_rpm": live_cur_rpm,
            "total_requests": sum(x["requests"] for x in items),
            "items": items,
        }

    # 2. Chế độ THEO NGÀY (7d / 30d) — gom theo ngày giờ Việt Nam (UTC+7)
    if range_param in ("7d", "30d") or granularity == "day":
        days = 30 if range_param == "30d" else 7
        start_dt, _ = _vn_day_start_utc(days - 1)
        _, today_vn_date = _vn_day_start_utc(0)

        rows = (
            db.query(models.SystemMetricsHourly)
            .filter(models.SystemMetricsHourly.bucket_timestamp >= start_dt)
            .all()
        )

        day_map: Dict[Any, Dict[str, int]] = {}
        for r in rows:
            d_key = _to_vn_time(r.bucket_timestamp).date()
            bucket = day_map.setdefault(d_key, {
                "requests": 0, "chat_requests": 0, "eval_requests": 0, "auth_requests": 0, "other_requests": 0
            })
            bucket["requests"] += int(r.total_requests or 0)
            bucket["chat_requests"] += int(r.chat_requests or 0)
            bucket["eval_requests"] += int(r.eval_requests or 0)
            bucket["auth_requests"] += int(r.auth_requests or 0)
            bucket["other_requests"] += int(r.other_requests or 0)

        # Cộng dồn delta live chưa flush vào ngày hôm nay theo giờ VN
        today_entry = day_map.setdefault(today_vn_date, {
            "requests": 0, "chat_requests": 0, "eval_requests": 0, "auth_requests": 0, "other_requests": 0
        })
        today_entry["requests"] += live_snap["total_requests"]
        today_entry["chat_requests"] += live_snap["chat_requests"]
        today_entry["eval_requests"] += live_snap["eval_requests"]
        today_entry["auth_requests"] += live_snap["auth_requests"]
        today_entry["other_requests"] += live_snap["other_requests"]

        items = []
        for d in range(days - 1, -1, -1):
            day_date = today_vn_date - timedelta(days=d)
            day_dt = datetime.combine(day_date, datetime.min.time(), tzinfo=TZ_VN)
            stats = day_map.get(day_date, {
                "requests": 0, "chat_requests": 0, "eval_requests": 0, "auth_requests": 0, "other_requests": 0
            })
            items.append({
                "timestamp": day_dt.isoformat(),
                "display_time": day_dt.strftime("%d/%m"),
                "requests": stats["requests"],
                "chat_requests": stats["chat_requests"],
                "eval_requests": stats["eval_requests"],
                "auth_requests": stats["auth_requests"],
                "other_requests": stats["other_requests"],
            })

        return {
            "range": range_param,
            "granularity": "day",
            "total_requests": sum(x["requests"] for x in items),
            "items": items,
        }

    # 3. Chế độ MẶC ĐỊNH: THEO GIỜ (24 giờ gần nhất) — hiển thị theo giờ Việt Nam (UTC+7)
    cur_hour = _hour_bucket(now)
    start_24h = cur_hour - timedelta(hours=23)
    rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_24h)
        .order_by(models.SystemMetricsHourly.bucket_timestamp)
        .all()
    )

    hour_map: Dict[datetime, Dict[str, int]] = {}
    for r in rows:
        h_key = _to_utc_hour(r.bucket_timestamp)
        hour_map[h_key] = {
            "requests": r.total_requests,
            "chat_requests": r.chat_requests,
            "eval_requests": r.eval_requests,
            "auth_requests": r.auth_requests,
            "other_requests": r.other_requests,
        }

    cur_entry = hour_map.setdefault(cur_hour, {
        "requests": 0, "chat_requests": 0, "eval_requests": 0, "auth_requests": 0, "other_requests": 0
    })
    cur_entry["requests"] += live_snap["total_requests"]
    cur_entry["chat_requests"] += live_snap["chat_requests"]
    cur_entry["eval_requests"] += live_snap["eval_requests"]
    cur_entry["auth_requests"] += live_snap["auth_requests"]
    cur_entry["other_requests"] += live_snap["other_requests"]

    items = []
    for h_offset in range(23, -1, -1):
        h_dt = cur_hour - timedelta(hours=h_offset)
        h_dt_vn = _to_vn_time(h_dt)
        stats = hour_map.get(h_dt, {
            "requests": 0, "chat_requests": 0, "eval_requests": 0, "auth_requests": 0, "other_requests": 0
        })
        items.append({
            "timestamp": h_dt_vn.isoformat(),
            "display_time": h_dt_vn.strftime("%H:00"),
            "requests": stats["requests"],
            "chat_requests": stats["chat_requests"],
            "eval_requests": stats["eval_requests"],
            "auth_requests": stats["auth_requests"],
            "other_requests": stats["other_requests"],
        })

    return {
        "range": "24h",
        "granularity": "hour",
        "total_requests": sum(x["requests"] for x in items),
        "items": items,
    }


# ==============================================================================
# 3. GET /tokens : Tiêu Thụ Token & Chi Phí API (4 Model Google Gemini)
# ==============================================================================
@router.get("/admin/kpi/tokens")
@router.get("/admin/metrics/tokens")
def get_kpi_tokens(
    days: int = Query(14, ge=1, le=30, description="Số ngày thống kê (1, 7, 14, 30)"),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-01 & AC-KPI-02:
    - Trả về số liệu chuỗi ngày Prompt Tokens (Input) và Completion Tokens (Output).
    - Tính chi phí USD và quy đổi VND theo bảng giá 4 model AI thực tế:
        gemini-2.5-flash, gemini-2.0-flash, gemini-2.0-flash-lite, gemini-1.5-pro.
    """
    start_dt, _ = _vn_day_start_utc(days - 1)
    _, today_vn_date = _vn_day_start_utc(0)
    live_snap = get_live_accumulator_snapshot()

    rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_dt)
        .all()
    )

    day_map: Dict[Any, Dict[str, Any]] = {}
    for r in rows:
        d_key = _to_vn_time(r.bucket_timestamp).date()
        bucket = day_map.setdefault(d_key, {
            "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "sessions_count": 0, "latencies": []
        })
        bucket["prompt_tokens"] += int(r.prompt_tokens or 0)
        bucket["completion_tokens"] += int(r.completion_tokens or 0)
        bucket["cost_usd"] += float(r.estimated_cost_usd or 0.0)
        bucket["sessions_count"] += int(r.total_requests or 0)
        if r.avg_latency_ms is not None and r.avg_latency_ms > 0:
            bucket["latencies"].append(int(r.avg_latency_ms))

    # Cộng dồn phần live chưa flush vào ngày hôm nay theo giờ VN
    today_entry = day_map.setdefault(today_vn_date, {
        "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "sessions_count": 0, "latencies": []
    })
    today_entry["prompt_tokens"] += live_snap["prompt_tokens"]
    today_entry["completion_tokens"] += live_snap["completion_tokens"]
    today_entry["cost_usd"] += float(live_snap["estimated_cost_usd"])
    today_entry["sessions_count"] += live_snap["total_requests"]
    if not today_entry["latencies"] and live_snap.get("avg_latency_ms", 0) > 0:
        today_entry["latencies"].append(int(live_snap["avg_latency_ms"]))

    items = []
    tot_prompt = 0
    tot_comp = 0
    tot_cost_usd = 0.0

    for d in range(days - 1, -1, -1):
        day_date = today_vn_date - timedelta(days=d)
        day_dt = datetime.combine(day_date, datetime.min.time(), tzinfo=TZ_VN)
        entry = day_map.get(day_date, {
            "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "sessions_count": 0, "latencies": []
        })
        p = entry["prompt_tokens"]
        c = entry["completion_tokens"]
        tot = p + c
        c_usd = entry["cost_usd"]
        c_vnd = int(round(c_usd * USD_TO_VND_RATE))
        lats = entry["latencies"]
        avg_lat_day = int(sum(lats) / len(lats)) if lats else 0

        tot_prompt += p
        tot_comp += c
        tot_cost_usd += c_usd

        items.append({
            "date": day_dt.strftime("%Y-%m-%d"),
            "display_date": day_dt.strftime("%d/%m"),
            "prompt_tokens": p,
            "completion_tokens": c,
            "total_tokens": tot,
            "cost_usd": round(c_usd, 4),
            "cost_vnd": c_vnd,
            "sessions_count": entry["sessions_count"],
            "latency_ms": avg_lat_day,
        })

    # Phân rã 6 phân hệ & model hoàn toàn từ dữ liệu thực (SystemAgentMetricsHourly + live)
    sub_agg = _aggregate_subsystem_metrics(db, start_dt, live_snap)
    total_tokens_all = tot_prompt + tot_comp
    effective_total_cost_usd = tot_cost_usd if tot_cost_usd > 0 else sub_agg["total_cost_usd"]

    return {
        "days": days,
        "total_prompt_tokens": tot_prompt,
        "total_completion_tokens": tot_comp,
        "total_tokens": total_tokens_all,
        "total_cost_usd": round(effective_total_cost_usd, 4),
        "total_cost_vnd": int(round(effective_total_cost_usd * USD_TO_VND_RATE)),
        "six_model_breakdown": sub_agg["six_model_breakdown"],
        "model_breakdown": sub_agg["model_breakdown"],
        "items": items,
    }


# ==============================================================================
# 4. GET /latency : Biểu Đồ Độ Trễ (P50, P95, P99) & Chỉ Số TTFT
# ==============================================================================
@router.get("/admin/kpi/latency")
@router.get("/admin/metrics/latency")
def get_kpi_latency(
    range_param: str = Query("24h", alias="range", description="24h"),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-02:
    - Biểu đồ độ trễ với đầy đủ 3 đường: P50 (xanh lá), P95 (vàng cam), P99 (đỏ).
    - Đo lường và kiểm chứng tiêu chuẩn: P50 < 800ms, P95 < 1800ms.
    - Đồng hồ TTFT (Time To First Token) chuyển màu xanh khi < 500ms.
    """
    now = datetime.now(timezone.utc)
    cur_hour = _hour_bucket(now)
    start_24h = cur_hour - timedelta(hours=23)
    live_snap = get_live_accumulator_snapshot()

    rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_24h)
        .order_by(models.SystemMetricsHourly.bucket_timestamp)
        .all()
    )

    hour_map: Dict[datetime, Dict[str, int]] = {}
    for r in rows:
        h_key = _to_utc_hour(r.bucket_timestamp)
        hour_map[h_key] = {
            "avg_latency_ms": r.avg_latency_ms or 0,
            "p50_latency_ms": r.p50_latency_ms or 0,
            "p95_latency_ms": r.p95_latency_ms or 0,
            "p99_latency_ms": r.p99_latency_ms or 0,
            "avg_ttft_ms": r.avg_ttft_ms or 0,
        }

    # Hợp nhất độ trễ live chưa flush vào khung giờ hiện tại
    if live_snap.get("total_requests", 0) > 0 or live_snap.get("avg_ttft_ms", 0) > 0:
        cur_entry = hour_map.setdefault(cur_hour, {
            "avg_latency_ms": 0, "p50_latency_ms": 0, "p95_latency_ms": 0, "p99_latency_ms": 0, "avg_ttft_ms": 0
        })
        for field in ("avg_latency_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "avg_ttft_ms"):
            if live_snap.get(field, 0) > 0:
                cur_entry[field] = live_snap[field]

    items = []
    p50_vals = []
    p95_vals = []
    p99_vals = []
    ttft_vals = []

    for h_offset in range(23, -1, -1):
        h_dt = cur_hour - timedelta(hours=h_offset)
        h_dt_vn = _to_vn_time(h_dt)
        entry = hour_map.get(h_dt, {
            "avg_latency_ms": 0, "p50_latency_ms": 0, "p95_latency_ms": 0, "p99_latency_ms": 0, "avg_ttft_ms": 0
        })
        p50 = entry["p50_latency_ms"]
        p95 = entry["p95_latency_ms"]
        p99 = entry["p99_latency_ms"]
        ttft = entry["avg_ttft_ms"]

        if p50 > 0:
            p50_vals.append(p50)
        if p95 > 0:
            p95_vals.append(p95)
        if p99 > 0:
            p99_vals.append(p99)
        if ttft > 0:
            ttft_vals.append(ttft)

        items.append({
            "timestamp": h_dt_vn.isoformat(),
            "display_time": h_dt_vn.strftime("%H:00"),
            "avg_latency_ms": entry["avg_latency_ms"],
            "p50_latency_ms": p50,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99,
            "avg_ttft_ms": ttft,
        })

    overall_p50 = int(sum(p50_vals) / len(p50_vals)) if p50_vals else 0
    overall_p95 = int(sum(p95_vals) / len(p95_vals)) if p95_vals else 0
    overall_p99 = int(sum(p99_vals) / len(p99_vals)) if p99_vals else 0
    current_ttft = int(sum(ttft_vals) / len(ttft_vals)) if ttft_vals else 0

    return {
        "range": "24h",
        "current_ttft_ms": current_ttft,
        "ttft_status": "green" if current_ttft < 500 else ("yellow" if current_ttft <= 1200 else "red"),
        "overall_p50_ms": overall_p50,
        "overall_p95_ms": overall_p95,
        "overall_p99_ms": overall_p99,
        "p50_target_met": overall_p50 < 800,
        "p95_target_met": overall_p95 < 1800,
        "targets": {
            "p50_target_ms": 800,
            "p95_target_ms": 1800,
            "ttft_target_ms": 500,
        },
        "items": items,
    }


# ==============================================================================
# 5. GET /agents : Biểu Đồ Donut Phân Bổ 6 Phân Hệ Agent
# ==============================================================================
@router.get("/admin/kpi/agents")
@router.get("/admin/metrics/agents")
def get_kpi_agents(
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-04:
    - Biểu đồ Donut phân bổ lưu lượng và mức sử dụng token của 6 phân hệ:
      Chat, Classifier, Flashcard, Báo cáo phụ huynh (ParentReport), Email, Dự phòng (Fallback).
    - Hỗ trợ khi Admin click vào từng phân hệ để xem chi tiết chi phí và model tương ứng.
    """
    now = datetime.now(timezone.utc)
    start_24h = now - timedelta(hours=24)
    live_snap = get_live_accumulator_snapshot()

    sub_agg = _aggregate_subsystem_metrics(db, start_24h, live_snap)
    agents_result = sub_agg["agents"]

    return {
        "status": "success",
        "total_subsystems": len(agents_result),
        "total_requests": sub_agg["total_requests"],
        "total_tokens": sub_agg["total_tokens"],
        "agents": agents_result,
    }


# ==============================================================================
# 6. GET /traffic-heatmap : Bản Đồ Nhiệt 7 Ngày x 24 Giờ (168 Ô)
# ==============================================================================
@router.get("/admin/kpi/traffic-heatmap")
@router.get("/admin/metrics/traffic-heatmap")
def get_kpi_traffic_heatmap(
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-05:
    - Bảng Heatmap gồm 7 ngày (Thứ 2 đến Chủ Nhật) và 24 giờ trong ngày (168 ô vuông).
    - Màu sắc thể hiện mật độ sử dụng hệ thống theo thời gian thực.
    - Tooltip chứa thông tin số lượng request và token tương ứng khi hover.
    """
    day_labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    full_day_names = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

    now_utc = datetime.now(timezone.utc)
    now_vn = _to_vn_time(now_utc)
    start_30d = now_utc - timedelta(days=30)

    # Khởi tạo lưới 7x24 = 168 ô trống (0 request, 0 token)
    grid: Dict[tuple, Dict[str, int]] = {
        (d_idx, h): {"requests": 0, "tokens": 0}
        for d_idx in range(7)
        for h in range(24)
    }

    rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_30d)
        .all()
    )
    for r in rows:
        ts_vn = _to_vn_time(r.bucket_timestamp)
        slot = grid[(ts_vn.weekday(), ts_vn.hour)]
        slot["requests"] += int(r.total_requests or 0)
        slot["tokens"] += int(r.total_tokens or 0)

    # Cộng dồn live delta chưa flush vào ô giờ Việt Nam hiện tại
    live_snap = get_live_accumulator_snapshot()
    cur_slot = grid[(now_vn.weekday(), now_vn.hour)]
    cur_slot["requests"] += int(live_snap.get("total_requests", 0))
    cur_slot["tokens"] += int(live_snap.get("total_tokens", 0))

    max_reqs = max((slot["requests"] for slot in grid.values()), default=0)

    cells = []
    peak_cell = {"day": "T2", "full_day": "Thứ Hai", "hour": 0, "requests": 0, "tokens": 0}

    for d_idx in range(7):
        d_short = day_labels[d_idx]
        d_full = full_day_names[d_idx]

        for h in range(24):
            slot = grid[(d_idx, h)]
            reqs = slot["requests"]
            tokens = slot["tokens"]

            if reqs == 0 or max_reqs == 0:
                intensity = 0
            else:
                ratio = reqs / max_reqs
                if ratio > 0.75:
                    intensity = 4
                elif ratio > 0.50:
                    intensity = 3
                elif ratio > 0.25:
                    intensity = 2
                else:
                    intensity = 1

            cell = {
                "day": d_short,
                "full_day": d_full,
                "day_index": d_idx,
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "requests": reqs,
                "tokens": tokens,
                "intensity": intensity,
            }
            cells.append(cell)

            if reqs > peak_cell["requests"]:
                peak_cell = {
                    "day": d_short,
                    "full_day": d_full,
                    "hour": h,
                    "requests": reqs,
                    "tokens": tokens,
                }

    return {
        "status": "success",
        "total_cells": len(cells),
        "peak_traffic": peak_cell,
        "heatmap": cells,
    }


# ==============================================================================
# 7. GET /infrastructure : Sức Chứa Hạ Tầng & Dịch Vụ
# ==============================================================================
@router.get("/admin/kpi/infrastructure")
@router.get("/admin/metrics/infrastructure")
async def get_kpi_infrastructure(
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-06:
    - Hiển thị số kết nối Neon PostgreSQL trên tổng giới hạn 20 kết nối.
    - Tỷ lệ Redis Cache Hit Rate và số phiên SSE đang hoạt động.
    - Trạng thái kiểm tra kết nối thực tế tới 4 dịch vụ nền tảng.
    """
    now = datetime.now(timezone.utc)
    start_of_today, _ = _vn_day_start_utc(0)
    live_snap = get_live_accumulator_snapshot()

    # 1. Đo kết nối Neon DB thật
    neon_active_conns = 0
    neon_max_conns = 20
    db_latency_ms = 0
    neon_status = "ONLINE"
    try:
        t0 = datetime.now()
        res = db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();")).scalar()
        db_latency_ms = max(1, int((datetime.now() - t0).total_seconds() * 1000))
        if res is not None:
            neon_active_conns = min(neon_max_conns, int(res))
    except Exception:
        neon_status = "OFFLINE"

    # 2. Đo Redis latency & Cache Hit Rate thật
    redis = _get_upstash_redis()
    redis_latency_ms = 0
    redis_status = "ONLINE" if redis else "OFFLINE"
    if redis:
        try:
            t0 = datetime.now()
            await redis.ping()
            redis_latency_ms = max(1, int((datetime.now() - t0).total_seconds() * 1000))
        except Exception:
            redis_status = "DEGRADED"

    today_rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_of_today)
        .all()
    )
    redis_hits = sum(r.redis_cache_hits or 0 for r in today_rows) + int(live_snap.get("redis_cache_hits", 0))
    redis_misses = sum(r.redis_cache_misses or 0 for r in today_rows) + int(live_snap.get("redis_cache_misses", 0))
    total_cache_checks = redis_hits + redis_misses
    redis_hit_rate_pct = round((redis_hits / total_cache_checks) * 100, 1) if total_cache_checks > 0 else 0.0

    # 3. Active SSE sessions & Peak SSE thật
    active_sse = get_active_sse_sessions()
    peak_sse_today = max(
        [r.peak_concurrent_sse or 0 for r in today_rows],
        default=0,
    )
    peak_sse_today = max(peak_sse_today, int(live_snap.get("peak_concurrent_sse", 0)), active_sse)

    # 4. Số liệu thật cho Gemini Gateway & Brevo Email
    ttft_list = [r.avg_ttft_ms for r in today_rows if (r.avg_ttft_ms or 0) > 0]
    if live_snap.get("avg_ttft_ms", 0) > 0:
        ttft_list.append(live_snap["avg_ttft_ms"])
    gemini_latency_ms = int(sum(ttft_list) / len(ttft_list)) if ttft_list else 0
    gemini_429_today = sum(r.gemini_429_count or 0 for r in today_rows) + int(live_snap.get("gemini_429_count", 0))
    gemini_configured = bool(os.getenv("GEMINI_API_KEY", "").strip())
    gemini_status = "DEGRADED" if gemini_429_today > 0 else ("ONLINE" if gemini_configured else "OFFLINE")

    email_rows = (
        db.query(models.SystemAgentMetricsHourly)
        .filter(
            models.SystemAgentMetricsHourly.bucket_timestamp >= start_of_today,
            models.SystemAgentMetricsHourly.agent_name == "Email",
        )
        .all()
    )
    email_reqs_today = sum(r.request_count or 0 for r in email_rows)
    email_lats = [r.avg_latency_ms for r in email_rows if (r.avg_latency_ms or 0) > 0]
    for ag in live_snap.get("agent_stats", []):
        if ag["agent_name"] == "Email":
            email_reqs_today += ag.get("request_count", 0)
            if ag.get("avg_latency_ms", 0) > 0:
                email_lats.append(ag["avg_latency_ms"])
    email_latency_ms = int(sum(email_lats) / len(email_lats)) if email_lats else 0
    brevo_configured = bool(os.getenv("BREVO_API_KEY", "").strip() or os.getenv("SMTP_HOST", "").strip())

    pool_util_pct = round((neon_active_conns / neon_max_conns) * 100, 1)

    services = [
        {
            "id": "neon_db",
            "name": "Neon PostgreSQL (Serverless)",
            "status": neon_status,
            "latency_ms": db_latency_ms,
            "metric_label": f"Pool: {neon_active_conns}/{neon_max_conns} ({pool_util_pct}%)",
            "health_level": "healthy" if (neon_status == "ONLINE" and pool_util_pct < 80) else "warning",
        },
        {
            "id": "upstash_redis",
            "name": "Upstash Redis (REST)",
            "status": redis_status,
            "latency_ms": redis_latency_ms,
            "metric_label": (
                f"Cache Hit: {redis_hit_rate_pct}% ({redis_hits} hits / {redis_misses} misses)"
                if total_cache_checks > 0
                else "Chưa có lượt truy cập cache hôm nay"
            ),
            "health_level": "healthy" if (redis_status == "ONLINE" and (total_cache_checks == 0 or redis_hit_rate_pct >= 75)) else "warning",
        },
        {
            "id": "gemini_api",
            "name": "Google Gemini API Gateway",
            "status": gemini_status,
            "latency_ms": gemini_latency_ms,
            "metric_label": f"Quota 429 hôm nay: {gemini_429_today} vi phạm",
            "health_level": "healthy" if (gemini_status == "ONLINE" and gemini_429_today == 0) else "warning",
        },
        {
            "id": "brevo_smtp",
            "name": "Brevo Email Notification",
            "status": "ONLINE" if brevo_configured else "UNCONFIGURED",
            "latency_ms": email_latency_ms,
            "metric_label": f"Email AI hôm nay: {email_reqs_today} lượt",
            "health_level": "healthy" if brevo_configured else "warning",
        },
    ]

    return {
        "status": "success",
        "neon_connections_active": neon_active_conns,
        "neon_connections_max": neon_max_conns,
        "neon_pool_utilization_pct": pool_util_pct,
        "redis_cache_hits": redis_hits,
        "redis_cache_misses": redis_misses,
        "redis_hit_rate_pct": redis_hit_rate_pct,
        "active_sse_sessions": active_sse,
        "peak_sse_sessions_today": peak_sse_today,
        "services": services,
    }


# ==============================================================================
# 8. GET /incidents : Trạng Thái Cảnh Báo Ngưỡng SLA (Banner Đỏ)
# ==============================================================================
@router.get("/admin/kpi/incidents")
@router.get("/admin/metrics/incidents")
def get_kpi_incidents(
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-07:
    - Khi tỷ lệ lỗi 5xx vượt 2% hoặc P95 vượt 1800ms:
      Tự động hiển thị banner cảnh báo màu đỏ trên Admin Dashboard.
    - Cung cấp danh sách các sự cố đang ACTIVE và các sự cố đã RESOLVED gần đây.
    """
    active_records = (
        db.query(models.SystemIncidentLog)
        .filter(models.SystemIncidentLog.status == "ACTIVE")
        .order_by(desc(models.SystemIncidentLog.triggered_at))
        .all()
    )

    recent_resolved = (
        db.query(models.SystemIncidentLog)
        .filter(models.SystemIncidentLog.status == "RESOLVED")
        .order_by(desc(models.SystemIncidentLog.resolved_at))
        .limit(5)
        .all()
    )

    banner_alert = None
    if active_records:
        top_inc = active_records[0]
        banner_alert = {
            "id": top_inc.id,
            "severity": top_inc.severity,
            "incident_type": top_inc.incident_type,
            "metric_name": top_inc.metric_name,
            "threshold_value": float(top_inc.threshold_value),
            "actual_value": float(top_inc.actual_value),
            "message": top_inc.message,
            "triggered_at": _to_vn_time(top_inc.triggered_at).isoformat(),
        }

    return {
        "status": "success",
        "has_active_incidents": len(active_records) > 0,
        "active_incident_count": len(active_records),
        "banner_alert": banner_alert,
        "active_incidents": [
            {
                "id": inc.id,
                "incident_type": inc.incident_type,
                "severity": inc.severity,
                "metric_name": inc.metric_name,
                "threshold_value": float(inc.threshold_value),
                "actual_value": float(inc.actual_value),
                "message": inc.message,
                "status": inc.status,
                "triggered_at": _to_vn_time(inc.triggered_at).isoformat(),
            }
            for inc in active_records
        ],
        "recent_resolved": [
            {
                "id": inc.id,
                "incident_type": inc.incident_type,
                "severity": inc.severity,
                "metric_name": inc.metric_name,
                "message": inc.message,
                "resolved_at": _to_vn_time(inc.resolved_at).isoformat() if inc.resolved_at else None,
            }
            for inc in recent_resolved
        ],
    }


# ==============================================================================
# 9. GET /export : Xuất Toàn Bộ Báo Cáo KPI (CSV / JSON)
# ==============================================================================
@router.get("/admin/kpi/export")
@router.get("/admin/metrics/export")
def export_kpi_report(
    format_type: str = Query("csv", alias="format", description="csv | json"),
    days: int = Query(14, ge=1, le=30),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
    db: Session = Depends(get_db),
):
    """
    AC-KPI-07:
    - Khi Admin nhấn nút xuất báo cáo, trình duyệt tải file CSV hoặc JSON
      chứa đầy đủ số liệu KPI phục vụ lưu trữ nghiệm thu đồ án.
    """
    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(days=days)

    rows = (
        db.query(models.SystemMetricsHourly)
        .filter(models.SystemMetricsHourly.bucket_timestamp >= start_dt)
        .order_by(models.SystemMetricsHourly.bucket_timestamp)
        .all()
    )

    live_snap = get_live_accumulator_snapshot()
    cur_hour = _hour_bucket(now)
    export_rows = []
    cur_hour_merged = False

    for r in rows:
        is_cur = _to_utc_hour(r.bucket_timestamp) == cur_hour
        item = {
            "timestamp": _to_vn_time(r.bucket_timestamp).isoformat(),
            "total_requests": r.total_requests + (live_snap["total_requests"] if is_cur else 0),
            "chat_requests": r.chat_requests + (live_snap["chat_requests"] if is_cur else 0),
            "eval_requests": r.eval_requests + (live_snap["eval_requests"] if is_cur else 0),
            "auth_requests": r.auth_requests + (live_snap["auth_requests"] if is_cur else 0),
            "other_requests": r.other_requests + (live_snap["other_requests"] if is_cur else 0),
            "prompt_tokens": r.prompt_tokens + (live_snap["prompt_tokens"] if is_cur else 0),
            "completion_tokens": r.completion_tokens + (live_snap["completion_tokens"] if is_cur else 0),
            "total_tokens": r.total_tokens + (live_snap["total_tokens"] if is_cur else 0),
            "cost_usd": float(r.estimated_cost_usd or 0.0) + (float(live_snap["estimated_cost_usd"]) if is_cur else 0.0),
            "p50_latency_ms": live_snap["p50_latency_ms"] if (is_cur and live_snap.get("p50_latency_ms", 0) > 0) else r.p50_latency_ms,
            "p95_latency_ms": live_snap["p95_latency_ms"] if (is_cur and live_snap.get("p95_latency_ms", 0) > 0) else r.p95_latency_ms,
            "p99_latency_ms": live_snap["p99_latency_ms"] if (is_cur and live_snap.get("p99_latency_ms", 0) > 0) else r.p99_latency_ms,
            "avg_ttft_ms": live_snap["avg_ttft_ms"] if (is_cur and live_snap.get("avg_ttft_ms", 0) > 0) else r.avg_ttft_ms,
            "status_2xx": r.status_2xx_count + (live_snap["status_2xx_count"] if is_cur else 0),
            "status_4xx": r.status_4xx_count + (live_snap["status_4xx_count"] if is_cur else 0),
            "gemini_429": r.gemini_429_count + (live_snap["gemini_429_count"] if is_cur else 0),
            "status_5xx": r.status_5xx_count + (live_snap["status_5xx_count"] if is_cur else 0),
            "failover_count": r.failover_count + (live_snap["failover_count"] if is_cur else 0),
            "redis_cache_hits": r.redis_cache_hits + (live_snap["redis_cache_hits"] if is_cur else 0),
            "redis_cache_misses": r.redis_cache_misses + (live_snap["redis_cache_misses"] if is_cur else 0),
            "peak_concurrent_sse": max(r.peak_concurrent_sse or 0, live_snap["peak_concurrent_sse"] if is_cur else 0),
        }
        if is_cur:
            cur_hour_merged = True
        export_rows.append(item)

    if not cur_hour_merged and (live_snap["total_requests"] > 0 or live_snap["total_tokens"] > 0):
        export_rows.append({
            "timestamp": _to_vn_time(cur_hour).isoformat(),
            "total_requests": live_snap["total_requests"],
            "chat_requests": live_snap["chat_requests"],
            "eval_requests": live_snap["eval_requests"],
            "auth_requests": live_snap["auth_requests"],
            "other_requests": live_snap["other_requests"],
            "prompt_tokens": live_snap["prompt_tokens"],
            "completion_tokens": live_snap["completion_tokens"],
            "total_tokens": live_snap["total_tokens"],
            "cost_usd": float(live_snap["estimated_cost_usd"]),
            "p50_latency_ms": live_snap.get("p50_latency_ms", 0),
            "p95_latency_ms": live_snap.get("p95_latency_ms", 0),
            "p99_latency_ms": live_snap.get("p99_latency_ms", 0),
            "avg_ttft_ms": live_snap.get("avg_ttft_ms", 0),
            "status_2xx": live_snap["status_2xx_count"],
            "status_4xx": live_snap["status_4xx_count"],
            "gemini_429": live_snap["gemini_429_count"],
            "status_5xx": live_snap["status_5xx_count"],
            "failover_count": live_snap["failover_count"],
            "redis_cache_hits": live_snap["redis_cache_hits"],
            "redis_cache_misses": live_snap["redis_cache_misses"],
            "peak_concurrent_sse": live_snap["peak_concurrent_sse"],
        })

    now_vn = _to_vn_time(now)
    if format_type.lower() == "json":
        return JSONResponse(
            content={"report_name": "SocraticKid_Admin_KPI_Report", "generated_at": now_vn.isoformat(), "data": export_rows},
            headers={"Content-Disposition": f"attachment; filename=socratickid_kpi_report_{now_vn.strftime('%Y%m%d')}.json"},
        )

    # Xuất định dạng CSV đầy đủ toàn bộ chỉ số KPI theo giờ VN (UTC+7)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Timestamp (UTC+7)",
        "Tong Requests",
        "Chat Requests",
        "Eval Requests",
        "Auth Requests",
        "Other Requests",
        "Prompt Tokens",
        "Completion Tokens",
        "Tong Tokens",
        "Chi Phi USD ($)",
        "Chi Phi VND (d)",
        "P50 Latency (ms)",
        "P95 Latency (ms)",
        "P99 Latency (ms)",
        "TTFT (ms)",
        "HTTP 2xx",
        "HTTP 4xx",
        "HTTP 429",
        "HTTP 5xx",
        "Failover Count",
        "Redis Cache Hits",
        "Redis Cache Misses",
        "Peak Concurrent SSE",
    ])

    for item in export_rows:
        c_usd = float(item["cost_usd"])
        writer.writerow([
            item["timestamp"],
            item["total_requests"],
            item["chat_requests"],
            item["eval_requests"],
            item["auth_requests"],
            item["other_requests"],
            item["prompt_tokens"],
            item["completion_tokens"],
            item["total_tokens"],
            f"{c_usd:.4f}",
            int(round(c_usd * USD_TO_VND_RATE)),
            item["p50_latency_ms"],
            item["p95_latency_ms"],
            item["p99_latency_ms"],
            item["avg_ttft_ms"],
            item["status_2xx"],
            item["status_4xx"],
            item["gemini_429"],
            item["status_5xx"],
            item["failover_count"],
            item["redis_cache_hits"],
            item["redis_cache_misses"],
            item["peak_concurrent_sse"],
        ])

    csv_content = output.getvalue().encode("utf-8-sig")  # UTF-8 BOM để Excel đọc đúng tiếng Việt
    filename = f"socratickid_admin_kpi_report_{now_vn.strftime('%Y%m%d_%H%M')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
