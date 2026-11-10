"""
US 10.2 - Script Migration: Hệ thống bảng KPI Telemetry (T10.2.0)
===================================================================
Tạo 3 bảng phục vụ Admin KPI Observability Dashboard:
  1. system_metrics_hourly   – Tổng hợp hiệu năng theo giờ (Throughput, Token, Latency, Lỗi)
  2. system_agent_metrics_hourly – Phân rã lưu lượng theo 6 phân hệ (Agent) và model AI
  3. system_incidents_log    – Nhật ký sự cố vi phạm ngưỡng SLA

Chạy:
    python backend/scripts/migrate_system_metrics.py
"""

import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from database import engine


# ==============================================================================
# Bảng 1: system_metrics_hourly
# Lưu tổng hợp hiệu năng toàn hệ thống mỗi giờ.
# bucket_timestamp: đầu mốc giờ UTC (VD: 2026-11-09 14:00:00+00)
# ==============================================================================
_DDL_METRICS_HOURLY = """
CREATE TABLE IF NOT EXISTS system_metrics_hourly (
    id                      BIGSERIAL       PRIMARY KEY,
    -- Mốc thời gian của giờ tương ứng (đầu giờ, múi giờ UTC)
    bucket_timestamp        TIMESTAMPTZ     NOT NULL,

    -- Throughput: số lượng request theo từng nhóm endpoint
    total_requests          INTEGER         NOT NULL DEFAULT 0,
    chat_requests           INTEGER         NOT NULL DEFAULT 0,   -- /chat/stream
    eval_requests           INTEGER         NOT NULL DEFAULT 0,   -- /independence/evaluate
    auth_requests           INTEGER         NOT NULL DEFAULT 0,   -- /auth/*
    other_requests          INTEGER         NOT NULL DEFAULT 0,   -- các endpoint còn lại

    -- Token tiêu thụ AI (lấy từ Gemini response.usage_metadata)
    prompt_tokens           BIGINT          NOT NULL DEFAULT 0,
    completion_tokens       BIGINT          NOT NULL DEFAULT 0,
    total_tokens            BIGINT          NOT NULL DEFAULT 0,
    -- Chi phí ước tính (USD) theo bảng giá Gemini API thực tế
    estimated_cost_usd      NUMERIC(12, 6)  NOT NULL DEFAULT 0.000000,

    -- Latency phân vị (milliseconds, End-to-End)
    avg_latency_ms          INTEGER         NOT NULL DEFAULT 0,
    p50_latency_ms          INTEGER         NOT NULL DEFAULT 0,
    p95_latency_ms          INTEGER         NOT NULL DEFAULT 0,
    p99_latency_ms          INTEGER         NOT NULL DEFAULT 0,
    -- Time To First Token: thời gian tới chunk SSE đầu tiên (ms)
    avg_ttft_ms             INTEGER         NOT NULL DEFAULT 0,

    -- Phân phối mã HTTP status
    status_2xx_count        INTEGER         NOT NULL DEFAULT 0,
    status_4xx_count        INTEGER         NOT NULL DEFAULT 0,
    status_5xx_count        INTEGER         NOT NULL DEFAULT 0,
    -- Đếm riêng lỗi quota Gemini API (429 Too Many Requests)
    gemini_429_count        INTEGER         NOT NULL DEFAULT 0,
    -- Số lần hệ thống kích hoạt mô hình dự phòng (Failover Cascade)
    failover_count          INTEGER         NOT NULL DEFAULT 0,

    -- Hạ tầng Redis cache
    redis_cache_hits        INTEGER         NOT NULL DEFAULT 0,
    redis_cache_misses      INTEGER         NOT NULL DEFAULT 0,
    -- Đỉnh phiên SSE đồng thời trong giờ đó
    peak_concurrent_sse     INTEGER         NOT NULL DEFAULT 0,

    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- Unique index đảm bảo mỗi giờ chỉ có 1 bản ghi tổng hợp
CREATE UNIQUE INDEX IF NOT EXISTS uq_metrics_hourly_bucket
    ON system_metrics_hourly (bucket_timestamp);

-- Index cho query theo thời gian (DESC) phục vụ biểu đồ
CREATE INDEX IF NOT EXISTS ix_metrics_hourly_bucket_desc
    ON system_metrics_hourly (bucket_timestamp DESC);
"""


# ==============================================================================
# Bảng 2: system_agent_metrics_hourly
# Phân rã lưu lượng và token theo 6 phân hệ Agent và model AI cụ thể.
#
# Các agent_name hợp lệ trong SocraticKid:
#   - Chat        : Socratic Tutor Agent (router.py – luồng hội thoại chính)
#   - Classifier  : Problem Classifier & Title Generator
#   - Flashcard   : Flashcard & Bookmark Agent
#   - ParentReport: Parent Insights Agent (AI báo cáo phụ huynh)
#   - Email       : Alert Email Worker (Brevo/SMTP)
#   - Fallback    : Local Heuristic / Failover khi Gemini API lỗi
#
# Các model_name hợp lệ (4 model đang dùng thực tế trong dự án):
#   - gemini-2.5-flash           : Model chat chính (Socratic Tutor)
#   - gemini-2.0-flash           : Model chat dự phòng tier-1
#   - gemini-2.0-flash-lite      : Sub-Agent phụ trợ (Classifier, Title, Rubric)
#   - gemini-1.5-pro             : Parent Insights Agent (cần context window 2M)
# ==============================================================================
_DDL_AGENT_METRICS_HOURLY = """
CREATE TABLE IF NOT EXISTS system_agent_metrics_hourly (
    id                      BIGSERIAL       PRIMARY KEY,
    bucket_timestamp        TIMESTAMPTZ     NOT NULL,

    -- Tên phân hệ Agent: Chat | Classifier | Flashcard | ParentReport | Email | Fallback
    agent_name              VARCHAR(64)     NOT NULL,
    -- Model AI thực tế:
    --   gemini-2.5-flash       (Chat chính)
    --   gemini-2.0-flash       (Chat dự phòng)
    --   gemini-2.0-flash-lite  (Sub-Agent phụ trợ)
    --   gemini-1.5-pro         (Parent Insights – context 2M tokens)
    model_name              VARCHAR(64)     NOT NULL,

    request_count           INTEGER         NOT NULL DEFAULT 0,
    prompt_tokens           BIGINT          NOT NULL DEFAULT 0,
    completion_tokens       BIGINT          NOT NULL DEFAULT 0,
    total_cost_usd          NUMERIC(12, 6)  NOT NULL DEFAULT 0.000000,
    avg_latency_ms          INTEGER         NOT NULL DEFAULT 0,
    error_count             INTEGER         NOT NULL DEFAULT 0
);

-- Index phục vụ query biểu đồ Donut theo agent và bucket
CREATE INDEX IF NOT EXISTS ix_agent_metrics_bucket_agent
    ON system_agent_metrics_hourly (bucket_timestamp DESC, agent_name);

-- Unique constraint: 1 cặp (bucket, agent, model) chỉ có 1 bản ghi
CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_metrics_bucket_agent_model
    ON system_agent_metrics_hourly (bucket_timestamp, agent_name, model_name);
"""


# ==============================================================================
# Bảng 3: system_incidents_log
# Nhật ký sự cố tự động khi vi phạm ngưỡng SLA (latency, error rate, quota...).
# Dashboard hiển thị banner đỏ dựa trên các bản ghi ACTIVE trong bảng này.
# ==============================================================================
_DDL_INCIDENTS_LOG = """
CREATE TABLE IF NOT EXISTS system_incidents_log (
    id                      VARCHAR(64)     PRIMARY KEY,
    -- Phân loại sự cố: HIGH_LATENCY | ERROR_SPIKE | QUOTA_EXCEEDED | DB_POOL_EXHAUSTED
    incident_type           VARCHAR(32)     NOT NULL,
    -- Mức độ: WARNING | CRITICAL
    severity                VARCHAR(16)     NOT NULL,
    -- Tên chỉ số vi phạm (VD: p95_latency_ms, status_5xx_rate, gemini_429_count)
    metric_name             VARCHAR(64)     NOT NULL,
    -- Giá trị ngưỡng được cấu hình (VD: 1800 ms với P95)
    threshold_value         NUMERIC(12, 2)  NOT NULL,
    -- Giá trị thực tế đo được tại thời điểm sự cố
    actual_value            NUMERIC(12, 2)  NOT NULL,
    -- Thông điệp mô tả sự cố (hiển thị trên banner Admin Dashboard)
    message                 TEXT            NOT NULL,
    -- Trạng thái xử lý: ACTIVE | RESOLVED
    status                  VARCHAR(16)     NOT NULL DEFAULT 'ACTIVE',
    triggered_at            TIMESTAMPTZ     NOT NULL DEFAULT now(),
    -- Thời điểm sự cố tự khắc phục hoặc Admin đánh dấu giải quyết
    resolved_at             TIMESTAMPTZ
);

-- Index phục vụ query banner cảnh báo đang ACTIVE
CREATE INDEX IF NOT EXISTS ix_incidents_active_triggered
    ON system_incidents_log (status, triggered_at DESC);
"""


def run_migration():
    print("=" * 65)
    print("  US 10.2 Migration: Hệ thống bảng KPI Telemetry (T10.2.0)")
    print("=" * 65)

    with engine.begin() as conn:
        print("\n[1/3] Tạo bảng system_metrics_hourly ...")
        conn.execute(text(_DDL_METRICS_HOURLY))
        print("      ✓ Thành công.")

        print("[2/3] Tạo bảng system_agent_metrics_hourly ...")
        conn.execute(text(_DDL_AGENT_METRICS_HOURLY))
        print("      ✓ Thành công.")

        print("[3/3] Tạo bảng system_incidents_log ...")
        conn.execute(text(_DDL_INCIDENTS_LOG))
        print("      ✓ Thành công.")

    # Kiểm tra xác nhận sau migration
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required_tables = [
        "system_metrics_hourly",
        "system_agent_metrics_hourly",
        "system_incidents_log",
    ]
    for table in required_tables:
        assert table in tables, f"Lỗi: Bảng '{table}' không tồn tại sau migration!"
        cols = [c["name"] for c in inspector.get_columns(table)]
        print(f"\n      Cột của {table}: {cols}")

    print("\n✅ Migration US 10.2 hoàn tất thành công!")


if __name__ == "__main__":
    run_migration()

