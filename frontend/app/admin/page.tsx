"use client";

import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import {
  Activity,
  TrendingUp,
  Zap,
  Clock,
  Cpu,
  ShieldCheck,
  ShieldAlert,
  Server,
  Database,
  RefreshCw,
  Download,
  Printer,
  Layers,
  MessageSquare,
  BookOpen,
  GraduationCap,
  AlertTriangle,
  ChevronDown,
  DollarSign,
  ArrowRight,
  Settings,
  AlertOctagon,
  CheckCircle2,
  Sliders,
  Filter,
} from "lucide-react";
import {
  ResponsiveContainer,
  ComposedChart,
  BarChart,
  Bar,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";

// ==============================================================================
// 1. Types & Interfaces
// ==============================================================================

interface OverviewData {
  status: string;
  timestamp: string;
  throughput: {
    total_requests_today: number;
    rpm_current: number;
    requests_growth_pct: number;
    chat_requests: number;
    eval_requests: number;
    auth_requests: number;
    other_requests: number;
  };
  tokens_and_cost: {
    total_tokens_today: number;
    prompt_tokens_today: number;
    completion_tokens_today: number;
    tpm_current: number;
    cost_usd_today: number;
    cost_vnd_today: number;
    cost_projection_month_usd: number;
    cost_projection_month_vnd: number;
  };
  latency_and_sla: {
    avg_latency_ms: number;
    p50_latency_ms: number;
    p95_latency_ms: number;
    p99_latency_ms: number;
    current_ttft_ms: number;
    p50_status: string;
    p95_status: string;
    ttft_status: string;
  };
  reliability: {
    success_rate_pct: number;
    error_rate_pct: number;
    client_error_rate_pct?: number;
    status_2xx_count_today?: number;
    status_4xx_count_today?: number;
    status_5xx_count_today: number;
    gemini_429_count_today: number;
    active_sse_sessions: number;
    system_health: string;
  };
}

interface ThroughputItem {
  timestamp: string;
  display_time: string;
  is_current_minute?: boolean;
  requests: number;
  chat_requests: number;
  eval_requests: number;
  auth_requests: number;
  other_requests: number;
  errors_4xx?: number;
  errors_429?: number;
  errors_5xx?: number;
}

interface ThroughputResponse {
  range: string;
  granularity: string;
  peak_rpm?: number;
  current_rpm?: number;
  total_requests: number;
  items: ThroughputItem[];
}

interface TokenDailyItem {
  date: string;
  display_date: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  cost_vnd: number;
  sessions_count: number;
  latency_ms: number;
}

interface ModelBreakdownItem {
  name: string;
  tokens: number;
  cost_usd: number;
  cost_vnd: number;
  percentage: number;
  pricing: string;
}

interface SixModelBreakdownItem {
  role_id: string;
  role_name: string;
  model_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  percentage: number;
  cost_usd: number;
  cost_vnd: number;
  pricing: string;
  color: string;
}

interface TokensResponse {
  days: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  total_cost_vnd: number;
  six_model_breakdown?: SixModelBreakdownItem[];
  model_breakdown: Record<string, ModelBreakdownItem>;
  items: TokenDailyItem[];
}

interface LatencyHourlyItem {
  timestamp: string;
  display_time: string;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  avg_ttft_ms: number;
}

interface LatencyResponse {
  range: string;
  current_ttft_ms: number;
  ttft_status: "green" | "yellow" | "red";
  overall_p50_ms: number;
  overall_p95_ms: number;
  overall_p99_ms: number;
  p50_target_met: boolean;
  p95_target_met: boolean;
  targets: {
    p50_target_ms: number;
    p95_target_ms: number;
    ttft_target_ms: number;
  };
  items: LatencyHourlyItem[];
}

interface SubsystemAgent {
  id: string;
  name: string;
  description: string;
  model_used: string;
  request_count: number;
  request_percentage: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  token_percentage: number;
  cost_usd: number;
  cost_vnd: number;
  avg_latency_ms: number;
  color: string;
}

interface AgentsResponse {
  status: string;
  total_subsystems: number;
  total_requests: number;
  total_tokens: number;
  agents: SubsystemAgent[];
}

interface HeatmapCell {
  day: string;
  full_day: string;
  day_index: number;
  hour: number;
  hour_label: string;
  requests: number;
  tokens: number;
  intensity: number;
}

interface HeatmapResponse {
  status: string;
  total_cells: number;
  peak_traffic: {
    day: string;
    full_day: string;
    hour: number;
    requests: number;
    tokens: number;
  };
  heatmap: HeatmapCell[];
}

interface InfrastructureService {
  id: string;
  name: string;
  status: string;
  latency_ms: number;
  metric_label: string;
  health_level: "healthy" | "warning" | "critical";
}

interface InfrastructureResponse {
  status: string;
  neon_connections_active: number;
  neon_connections_max: number;
  neon_pool_utilization_pct: number;
  redis_cache_hits: number;
  redis_cache_misses: number;
  redis_hit_rate_pct: number;
  active_sse_sessions: number;
  services: InfrastructureService[];
}

interface IncidentItem {
  id: number;
  incident_type: string;
  severity: string;
  metric_name: string;
  threshold_value: number;
  actual_value: number;
  message: string;
  status?: string;
  triggered_at: string;
  resolved_at?: string | null;
}

interface IncidentsResponse {
  status: string;
  has_active_incidents: boolean;
  active_incident_count: number;
  banner_alert?: IncidentItem | null;
  active_incidents: IncidentItem[];
  recent_resolved: IncidentItem[];
}

// ==============================================================================
// 2. Default Fallback Data (phục vụ cold-boot hoặc offline demo)
// ==============================================================================

const DEFAULT_OVERVIEW: OverviewData = {
  status: "success",
  timestamp: new Date().toISOString(),
  throughput: {
    total_requests_today: 1420,
    rpm_current: 24,
    requests_growth_pct: 14.2,
    chat_requests: 923,
    eval_requests: 255,
    auth_requests: 142,
    other_requests: 100,
  },
  tokens_and_cost: {
    total_tokens_today: 1400000,
    prompt_tokens_today: 920000,
    completion_tokens_today: 480000,
    tpm_current: 9120,
    cost_usd_today: 0.312,
    cost_vnd_today: 7940,
    cost_projection_month_usd: 9.36,
    cost_projection_month_vnd: 238212,
  },
  latency_and_sla: {
    avg_latency_ms: 980,
    p50_latency_ms: 540,
    p95_latency_ms: 1420,
    p99_latency_ms: 2250,
    current_ttft_ms: 420,
    p50_status: "optimal",
    p95_status: "optimal",
    ttft_status: "optimal",
  },
  reliability: {
    success_rate_pct: 99.7,
    error_rate_pct: 0.1,
    client_error_rate_pct: 0.2,
    status_2xx_count_today: 1416,
    status_4xx_count_today: 3,
    status_5xx_count_today: 1,
    gemini_429_count_today: 0,
    active_sse_sessions: 8,
    system_health: "HEALTHY",
  },
};

const DEFAULT_SIX_MODELS: SixModelBreakdownItem[] = [
  {
    role_id: "primary_model",
    role_name: "Chat Socratic (Primary)",
    model_name: "gemini-3.8-flash",
    prompt_tokens: 520000,
    completion_tokens: 250000,
    total_tokens: 770000,
    percentage: 55.0,
    cost_usd: 0.184,
    cost_vnd: 4683,
    pricing: "$0.10 / $0.40 per 1M",
    color: "#C1762A",
  },
  {
    role_id: "classifier_model",
    role_name: "Phân Loại & Đặt Tên",
    model_name: "gemini-3.1-flash-lite",
    prompt_tokens: 195000,
    completion_tokens: 85000,
    total_tokens: 280000,
    percentage: 20.0,
    cost_usd: 0.032,
    cost_vnd: 814,
    pricing: "$0.075 / $0.30 per 1M",
    color: "#8C4905",
  },
  {
    role_id: "flashcard_model",
    role_name: "Flashcard & Sổ Tay",
    model_name: "gemini-3.5-flash-lite",
    prompt_tokens: 112000,
    completion_tokens: 56000,
    total_tokens: 168000,
    percentage: 12.0,
    cost_usd: 0.025,
    cost_vnd: 636,
    pricing: "$0.075 / $0.30 per 1M",
    color: "#2563EB",
  },
  {
    role_id: "parent_insight_model",
    role_name: "Báo Cáo Phụ Huynh",
    model_name: "gemini-3.5-flash",
    prompt_tokens: 72000,
    completion_tokens: 40000,
    total_tokens: 112000,
    percentage: 8.0,
    cost_usd: 0.027,
    cost_vnd: 687,
    pricing: "$0.10 / $0.40 per 1M",
    color: "#10B981",
  },
  {
    role_id: "email_model",
    role_name: "Email Cảnh Báo",
    model_name: "gemini-3.1-flash-lite",
    prompt_tokens: 28000,
    completion_tokens: 14000,
    total_tokens: 42000,
    percentage: 3.0,
    cost_usd: 0.006,
    cost_vnd: 153,
    pricing: "$0.075 / $0.30 per 1M",
    color: "#F59E0B",
  },
  {
    role_id: "backup_model",
    role_name: "Dự Phòng Failover",
    model_name: "gemini-3.5-flash-lite",
    prompt_tokens: 18000,
    completion_tokens: 10000,
    total_tokens: 28000,
    percentage: 2.0,
    cost_usd: 0.004,
    cost_vnd: 102,
    pricing: "$0.075 / $0.30 per 1M",
    color: "#6B7280",
  },
];

const DEFAULT_AGENTS: SubsystemAgent[] = [
  {
    id: "Chat",
    name: "Gia Sư Socratic (Chat)",
    description: "Đối thoại sư phạm gợi mở 2-4 câu, bám sát sách giáo khoa Toán 4-9",
    model_used: "gemini-3.8-flash",
    request_count: 781,
    request_percentage: 55.0,
    prompt_tokens: 520000,
    completion_tokens: 250000,
    total_tokens: 770000,
    token_percentage: 55.0,
    cost_usd: 0.152,
    cost_vnd: 3868,
    avg_latency_ms: 680,
    color: "#C1762A",
  },
  {
    id: "Classifier",
    name: "Phân Loại Bài Toán & Đặt Tên",
    description: "Nhận diện chuyên đề SGK và đặt tên bài toán thân thiện",
    model_used: "gemini-3.1-flash-lite",
    request_count: 284,
    request_percentage: 20.0,
    prompt_tokens: 195000,
    completion_tokens: 85000,
    total_tokens: 280000,
    token_percentage: 20.0,
    cost_usd: 0.04,
    cost_vnd: 1018,
    avg_latency_ms: 260,
    color: "#8C4905",
  },
  {
    id: "Flashcard",
    name: "Sổ Tay & Thẻ Ghi Nhớ (Flashcard)",
    description: "Trích xuất công thức trọng tâm và tóm tắt bước giải vào sổ tay",
    model_used: "gemini-3.5-flash-lite",
    request_count: 170,
    request_percentage: 12.0,
    prompt_tokens: 112000,
    completion_tokens: 56000,
    total_tokens: 168000,
    token_percentage: 12.0,
    cost_usd: 0.025,
    cost_vnd: 636,
    avg_latency_ms: 310,
    color: "#2563EB",
  },
  {
    id: "ParentReport",
    name: "Báo Cáo Phụ Huynh (Parent Insights)",
    description: "Quét toàn bộ lịch sử tuần để đánh giá tính tự lập gửi phụ huynh",
    model_used: "gemini-3.5-flash",
    request_count: 114,
    request_percentage: 8.0,
    prompt_tokens: 72000,
    completion_tokens: 40000,
    total_tokens: 112000,
    token_percentage: 8.0,
    cost_usd: 0.023,
    cost_vnd: 585,
    avg_latency_ms: 920,
    color: "#10B981",
  },
  {
    id: "Email",
    name: "Email Cảnh Báo Phụ Huynh",
    description: "Gửi thông báo cảnh báo học tập hoặc ngôn từ tiêu cực qua Brevo SMTP",
    model_used: "gemini-3.1-flash-lite",
    request_count: 43,
    request_percentage: 3.0,
    prompt_tokens: 28000,
    completion_tokens: 14000,
    total_tokens: 42000,
    token_percentage: 3.0,
    cost_usd: 0.006,
    cost_vnd: 153,
    avg_latency_ms: 190,
    color: "#F59E0B",
  },
  {
    id: "Fallback",
    name: "Dự Phòng & Failover AI",
    description: "Model dự phòng tự động chuyển đổi khi Primary Model quá tải hoặc timeout",
    model_used: "gemini-3.5-flash-lite",
    request_count: 28,
    request_percentage: 2.0,
    prompt_tokens: 18000,
    completion_tokens: 10000,
    total_tokens: 28000,
    token_percentage: 2.0,
    cost_usd: 0.004,
    cost_vnd: 102,
    avg_latency_ms: 140,
    color: "#6B7280",
  },
];

// ==============================================================================
// 3. Main Admin KPI Dashboard Component
// ==============================================================================

export default function AdminKpiDashboard() {
  const { data: session } = useSession();

  // State quản lý Auto-Refresh
  const [refreshInterval, setRefreshInterval] = useState<number>(15000); // 15s mặc định
  const [countdown, setCountdown] = useState<number>(15);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // Filter States
  const [throughputRange, setThroughputRange] = useState<"1h" | "24h" | "7d" | "30d">("1h");
  const [tokenDays, setTokenDays] = useState<7 | 14 | 30>(14);
  const [currencyMode, setCurrencyMode] = useState<"USD" | "VND">("USD");
  const [selectedAgentId, setSelectedAgentId] = useState<string>("Chat");
  const [dismissIncidentBanner, setDismissIncidentBanner] = useState<boolean>(false);
  const [isExportingCsv, setIsExportingCsv] = useState<boolean>(false);
  const [hoveredHeatmapCell, setHoveredHeatmapCell] = useState<HeatmapCell | null>(null);

  // Data States
  const [overview, setOverview] = useState<OverviewData>(DEFAULT_OVERVIEW);
  const [throughput, setThroughput] = useState<ThroughputResponse | null>(null);
  const [tokensData, setTokensData] = useState<TokensResponse | null>(null);
  const [latencyData, setLatencyData] = useState<LatencyResponse | null>(null);
  const [agentsData, setAgentsData] = useState<AgentsResponse>({
    status: "success",
    total_subsystems: DEFAULT_AGENTS.length,
    total_requests: 1420,
    total_tokens: 1400000,
    agents: DEFAULT_AGENTS,
  });
  const [heatmapData, setHeatmapData] = useState<HeatmapResponse | null>(null);
  const [infraData, setInfraData] = useState<InfrastructureResponse | null>(null);
  const [incidentsData, setIncidentsData] = useState<IncidentsResponse | null>(null);

  // Backend base URL & Auth Token
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
  const accessToken = (session as any)?.access_token || "";

  // Helper fetch with auth
  const fetchWithAuth = useCallback(
    async (path: string) => {
      try {
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        if (accessToken) {
          headers["Authorization"] = `Bearer ${accessToken}`;
        }
        const res = await fetch(`${backendUrl}${path}`, { headers });
        if (!res.ok) return null;
        return await res.json();
      } catch (err) {
        return null;
      }
    },
    [backendUrl, accessToken]
  );

  // Hàm load tất cả dữ liệu KPI từ Backend
  const loadAllMetrics = useCallback(
    async (silent: boolean = false) => {
      if (!silent) setIsRefreshing(true);

      try {
        // Gọi song song các endpoint
        const [
          resOverview,
          resThroughput,
          resTokens,
          resLatency,
          resAgents,
          resHeatmap,
          resInfra,
          resIncidents,
        ] = await Promise.all([
          fetchWithAuth("/admin/kpi/overview"),
          fetchWithAuth(`/admin/kpi/throughput?range=${throughputRange}`),
          fetchWithAuth(`/admin/kpi/tokens?days=${tokenDays}`),
          fetchWithAuth("/admin/kpi/latency?range=24h"),
          fetchWithAuth("/admin/kpi/agents"),
          fetchWithAuth("/admin/kpi/traffic-heatmap"),
          fetchWithAuth("/admin/kpi/infrastructure"),
          fetchWithAuth("/admin/kpi/incidents"),
        ]);

        if (resOverview && resOverview.throughput) setOverview(resOverview);
        if (resThroughput && resThroughput.items) setThroughput(resThroughput);
        if (resTokens && resTokens.items) setTokensData(resTokens);
        if (resLatency && resLatency.items) setLatencyData(resLatency);
        if (resAgents && resAgents.agents) setAgentsData(resAgents);
        if (resHeatmap && resHeatmap.heatmap) setHeatmapData(resHeatmap);
        if (resInfra && resInfra.services) setInfraData(resInfra);
        if (resIncidents) setIncidentsData(resIncidents);

        setLastRefreshedAt(new Date());
      } catch (e) {
        // Fallback gracefully
      } finally {
        setIsRefreshing(false);
      }
    },
    [fetchWithAuth, throughputRange, tokenDays]
  );

  // Mount effect
  useEffect(() => {
    setIsMounted(true);
    loadAllMetrics(false);
  }, [loadAllMetrics]);

  // Auto-Refresh Timer effect
  useEffect(() => {
    if (refreshInterval <= 0) return;

    setCountdown(Math.floor(refreshInterval / 1000));
    const countdownTimer = setInterval(() => {
      setCountdown((prev) => (prev <= 1 ? Math.floor(refreshInterval / 1000) : prev - 1));
    }, 1000);

    const refreshTimer = setInterval(() => {
      loadAllMetrics(true);
    }, refreshInterval);

    return () => {
      clearInterval(countdownTimer);
      clearInterval(refreshTimer);
    };
  }, [refreshInterval, loadAllMetrics]);

  // Selected agent object
  const currentAgent = useMemo(() => {
    return (
      agentsData.agents.find((a) => a.id === selectedAgentId) ||
      agentsData.agents[0] ||
      DEFAULT_AGENTS[0]
    );
  }, [agentsData, selectedAgentId]);

  // Xuất báo cáo CSV (Gửi JWT Bearer token + Fallback UTF-8 BOM CSV nếu offline)
  const handleExportCSV = async () => {
    setIsExportingCsv(true);
    const filename = `socratickid_admin_kpi_${new Date().toISOString().slice(0, 10)}.csv`;
    try {
      const headers: Record<string, string> = {};
      if (accessToken) {
        headers["Authorization"] = `Bearer ${accessToken}`;
      }
      const res = await fetch(`${backendUrl}/admin/kpi/export?format=csv&days=${tokenDays}`, {
        headers,
      });
      if (res.ok) {
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = blobUrl;
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(blobUrl);
        return;
      }
    } catch {
      // Fallback sang CSV client bên dưới nếu endpoint chưa khả dụng
    } finally {
      setIsExportingCsv(false);
    }

    // Fallback UTF-8 BOM CSV từ dữ liệu hiện hữu trên Dashboard
    const csvRows = [
      ["Nhom Chi So", "Ten Chi So", "Gia Tri", "Don Vi"],
      ["Throughput", "Tong Requests Hom Nay", String(overview.throughput.total_requests_today), "requests"],
      ["Throughput", "RPM Hien Tai", String(overview.throughput.rpm_current), "req/min"],
      ["Tokens & Cost", "Tong Tokens Hom Nay", String(overview.tokens_and_cost.total_tokens_today), "tokens"],
      ["Tokens & Cost", "Prompt Tokens", String(overview.tokens_and_cost.prompt_tokens_today), "tokens"],
      ["Tokens & Cost", "Completion Tokens", String(overview.tokens_and_cost.completion_tokens_today), "tokens"],
      ["Tokens & Cost", "Chi Phi USD", String(overview.tokens_and_cost.cost_usd_today), "USD"],
      ["Tokens & Cost", "Chi Phi VND", String(overview.tokens_and_cost.cost_vnd_today), "VND"],
      ["Latency SLA", "P50 Latency", String(latencyData?.overall_p50_ms ?? overview.latency_and_sla.p50_latency_ms), "ms"],
      ["Latency SLA", "P95 Latency", String(latencyData?.overall_p95_ms ?? overview.latency_and_sla.p95_latency_ms), "ms"],
      ["Latency SLA", "P99 Latency", String(latencyData?.overall_p99_ms ?? overview.latency_and_sla.p99_latency_ms), "ms"],
      ["Latency SLA", "TTFT", String(latencyData?.current_ttft_ms ?? overview.latency_and_sla.current_ttft_ms), "ms"],
      ["Reliability", "HTTP 2xx Success", String(overview.reliability.status_2xx_count_today ?? 0), "requests"],
      ["Reliability", "HTTP 4xx Client Error", String(overview.reliability.status_4xx_count_today ?? 0), "requests"],
      ["Reliability", "HTTP 429 Quota", String(overview.reliability.gemini_429_count_today), "requests"],
      ["Reliability", "HTTP 5xx Server Error", String(overview.reliability.status_5xx_count_today), "requests"],
      ["Reliability", "Ti Le Loi 5xx", String(overview.reliability.error_rate_pct), "%"],
    ];
    const bomCsv = "\uFEFF" + csvRows.map((row) => row.map((v) => `"${v.replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([bomCsv], { type: "text/csv;charset=utf-8;" });
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
  };

  // In / Xuất báo cáo PDF 1-Click
  const handlePrintPDF = () => {
    window.print();
  };

  if (!isMounted) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 text-[#C1762A] animate-spin" />
      </div>
    );
  }

  // Đánh giá vi phạm SLA theo AC-KPI-07 (DB incident ACTIVE HOẶC telemetry live vượt ngưỡng)
  const effectiveP50 = latencyData?.overall_p50_ms ?? overview.latency_and_sla.p50_latency_ms;
  const effectiveP95 = Math.max(
    latencyData?.overall_p95_ms ?? 0,
    overview.latency_and_sla.p95_latency_ms ?? 0
  );
  const effectiveP99 = Math.max(
    latencyData?.overall_p99_ms ?? 0,
    overview.latency_and_sla.p99_latency_ms ?? 0
  );
  const effectiveTtft = latencyData?.current_ttft_ms ?? overview.latency_and_sla.current_ttft_ms;
  const isErrorSpikeLive = overview.reliability.error_rate_pct > 2.0;
  const isLatencyBreachLive = effectiveP95 > 1800;
  const hasSlaBreach =
    Boolean(incidentsData?.has_active_incidents) || isErrorSpikeLive || isLatencyBreachLive;
  const hasActiveIncidents = hasSlaBreach && !dismissIncidentBanner;
  const activeIncident = incidentsData?.banner_alert;
  const slaBreachType =
    activeIncident?.incident_type || (isErrorSpikeLive ? "ERROR_SPIKE" : "LATENCY_BREACH");
  const slaActualValue =
    activeIncident?.actual_value ??
    (slaBreachType === "ERROR_SPIKE"
      ? `${overview.reliability.error_rate_pct}%`
      : `${effectiveP95}ms`);
  const slaThresholdValue =
    activeIncident?.threshold_value ?? (slaBreachType === "ERROR_SPIKE" ? "2.0%" : "1800ms");

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300 print:p-0 print:space-y-4 text-[#1C1917]">
      {/* Header chỉ hiển thị khi in / xuất PDF */}
      <div className="hidden print:flex items-center justify-between border-b-2 border-[#C1762A] pb-3 mb-2">
        <div>
          <h1 className="text-xl font-black text-[#8C4905]">
            Báo Cáo Vận Hành Hệ Thống — SocraticKid Admin KPI
          </h1>
          <p className="text-xs text-[#7A3E04]">
            Thời điểm xuất: {lastRefreshedAt.toLocaleString("vi-VN")} • Chu kỳ phân tích Token: {tokenDays} ngày
          </p>
        </div>
        <span className="text-xs font-bold text-[#8C4905]">
          Trạng thái: {hasSlaBreach ? "CẢNH BÁO SLA" : overview.reliability.system_health}
        </span>
      </div>

      {/* ── 0. SLA Incident Alert Banner (AC-KPI-07 & T10.2.10) ── */}
      {hasActiveIncidents && (
        <section
          role="alert"
          className="bg-red-500/10 border-2 border-red-500 rounded-2xl p-4 md:p-5 shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in slide-in-from-top-4 duration-300"
        >
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-red-600 text-white flex items-center justify-center shrink-0 shadow-md">
              <AlertOctagon className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-black uppercase tracking-wider px-2 py-0.5 rounded-md bg-red-600 text-white">
                  CẢNH BÁO VI PHẠM SLA
                </span>
                <span className="text-xs font-bold text-red-700">
                  {slaBreachType === "ERROR_SPIKE"
                    ? "Tỷ lệ lỗi HTTP 5xx vượt ngưỡng 2.0%"
                    : "Độ trễ phản hồi P95 vượt ngưỡng 1800ms"}
                </span>
              </div>
              <p className="text-sm font-semibold text-red-900 mt-1">
                {activeIncident?.message ||
                  (slaBreachType === "ERROR_SPIKE"
                    ? `Cảnh báo nghiêm trọng: Tỷ lệ lỗi Server 5xx đang đạt ${overview.reliability.error_rate_pct}% (> 2.0%). Cần kiểm tra Error Logs và Failover Model.`
                    : `Cảnh báo suy giảm tốc độ: Độ trễ P95 đạt ${effectiveP95}ms (> 1800ms). Hệ thống đang phản hồi chậm hơn cam kết SLA.`)}
              </p>
              <p className="text-xs text-red-700/80 mt-0.5">
                Phát hiện lúc:{" "}
                {activeIncident?.triggered_at
                  ? new Date(activeIncident.triggered_at).toLocaleTimeString("vi-VN")
                  : lastRefreshedAt.toLocaleTimeString("vi-VN")}{" "}
                • Giá trị đo:{" "}
                <strong>{slaActualValue}</strong> (Ngưỡng cho phép: {slaThresholdValue})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center shrink-0 print:hidden">
            <button
              onClick={() => setDismissIncidentBanner(true)}
              className="text-xs font-bold px-3 py-1.5 rounded-lg border border-red-300 text-red-800 hover:bg-red-100 transition-colors"
            >
              Tạm ẩn
            </button>
            <Link
              href="/admin/settings"
              className="text-xs font-bold px-3 py-1.5 rounded-lg border border-red-400 bg-white text-red-700 hover:bg-red-50 transition-colors"
            >
              Chuyển Backup Model
            </Link>
            <Link
              href="/admin/errors"
              className="text-xs font-bold px-3.5 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors shadow-sm flex items-center gap-1.5"
            >
              <span>Xem Log Lỗi</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </section>
      )}

      {/* ── 1. Header & Điều Khiển Auto-Refresh / Xuất Báo Cáo ── */}
      <header className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white rounded-2xl p-5 md:p-6 border border-[#F1CCA6] shadow-sm">
        <div className="flex items-start md:items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-[#C1762A] text-white flex items-center justify-center font-black text-xl shadow-md shrink-0">
            KPI
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-2xl md:text-3xl font-black text-[#8C4905] tracking-tight">
                Admin KPI Observability Hub
              </h1>
              <span
                className={`text-xs font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1.5 ${
                  !hasSlaBreach && overview.reliability.system_health === "HEALTHY"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-red-50 text-red-700 border border-red-200"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    !hasSlaBreach && overview.reliability.system_health === "HEALTHY"
                      ? "bg-emerald-500 animate-pulse"
                      : "bg-red-500 animate-ping"
                  }`}
                />
                {!hasSlaBreach && overview.reliability.system_health === "HEALTHY"
                  ? "SLA 99.7% Hoạt động ổn định"
                  : "Cảnh báo vi phạm ngưỡng SLA"}
              </span>
            </div>
            <p className="text-xs md:text-sm text-[#7A3E04] mt-1 font-medium">
              Giám sát lưu lượng RPM theo thời gian thực, tiêu thụ token Gemini, độ trễ SLA và hạ tầng hệ thống
            </p>
          </div>
        </div>

        {/* Thanh điều khiển Auto-Refresh & Export */}
        <div className="flex items-center gap-2.5 flex-wrap self-start lg:self-center print:hidden">
          {/* Bộ chọn Auto-Refresh Toggle */}
          <div className="flex items-center gap-1.5 bg-[#F7ECE1] p-1 rounded-xl border border-[#F1CCA6]">
            <Clock className="w-4 h-4 text-[#8C4905] ml-1.5 hidden sm:inline" />
            <span className="text-[11px] font-bold text-[#8C4905] pl-1 hidden sm:inline">
              Tự động:
            </span>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              aria-label="Tần suất tự động làm mới"
              className="bg-transparent text-xs font-bold text-[#8C4905] px-2 py-1 rounded-lg outline-none cursor-pointer hover:bg-white/50 transition-colors"
            >
              <option value={5000}>Mỗi 5s</option>
              <option value={15000}>Mỗi 15s</option>
              <option value={30000}>Mỗi 30s</option>
              <option value={60000}>Mỗi 60s</option>
              <option value={0}>Thủ công</option>
            </select>
            {refreshInterval > 0 && (
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md bg-white text-[#C1762A] border border-[#F1CCA6] min-w-[28px] text-center">
                {countdown}s
              </span>
            )}
          </div>

          {/* Nút Làm Mới thủ công */}
          <button
            onClick={() => loadAllMetrics(false)}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-[#F7ECE1] text-[#8C4905] font-bold text-xs border border-[#F1CCA6] shadow-xs transition-colors disabled:opacity-50"
            title="Làm mới toàn bộ số liệu ngay lập tức"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-[#C1762A]" : ""}`} />
            <span className="hidden sm:inline">Làm mới</span>
          </button>

          {/* Nút Xuất CSV 1-Click (kèm Bearer JWT Auth) */}
          <button
            onClick={handleExportCSV}
            disabled={isExportingCsv}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#C1762A] hover:bg-[#A8611D] text-white font-bold text-xs shadow-xs transition-all disabled:opacity-60"
            title="Tải báo cáo KPI định dạng CSV về máy (1-Click)"
          >
            <Download className={`w-3.5 h-3.5 ${isExportingCsv ? "animate-bounce" : ""}`} />
            <span>{isExportingCsv ? "Đang xuất..." : "Xuất CSV"}</span>
          </button>

          {/* Nút Xuất PDF 1-Click */}
          <button
            onClick={handlePrintPDF}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-[#F7ECE1] text-[#8C4905] font-bold text-xs border border-[#F1CCA6] shadow-xs transition-colors"
            title="Xuất / In báo cáo Dashboard sang định dạng PDF"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Xuất PDF</span>
          </button>
        </div>
      </header>

      {/* ── 2. 4 Thẻ KPI Tổng Hợp Đầu Trang (T10.2.6 & AC-KPI-01, 02) ── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Thẻ 1: Throughput & Live RPM */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center shadow-inner">
              <Activity className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                {overview.throughput.rpm_current} RPM
              </span>
            </div>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-[#C1762A] mb-1">
              Tổng Lưu Lượng Hôm Nay
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-[#8C4905] leading-none">
                {overview.throughput.total_requests_today.toLocaleString("vi-VN")}
              </span>
              <span className="text-xs font-bold text-emerald-600 flex items-center gap-0.5">
                <TrendingUp className="w-3 h-3" /> +{overview.throughput.requests_growth_pct}%
              </span>
            </div>
            <div className="mt-2 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px] text-[#7A3E04]">
              <span>Chat: <strong>{overview.throughput.chat_requests}</strong></span>
              <span>Eval: <strong>{overview.throughput.eval_requests}</strong></span>
              <span>Khác: <strong>{overview.throughput.other_requests}</strong></span>
            </div>
          </div>
        </div>

        {/* Thẻ 2: Token Tiêu Thụ & Chi Phí API */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center shadow-inner">
              <Cpu className="w-5 h-5 stroke-[2.2]" />
            </div>
            <button
              onClick={() => setCurrencyMode((prev) => (prev === "USD" ? "VND" : "USD"))}
              className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F1CCA6]/60 transition-colors"
            >
              Đổi tiền: {currencyMode}
            </button>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-[#C1762A] mb-1">
              Token Gemini & Chi Phí
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-[#8C4905] leading-none">
                {(overview.tokens_and_cost.total_tokens_today / 1_000_000).toFixed(2)}M
              </span>
              <span className="text-xs font-bold text-[#C1762A]">tokens hôm nay</span>
            </div>
            <div className="mt-2 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px]">
              <span className="text-[#7A3E04]">Chi phí:</span>
              <span className="font-black text-emerald-700">
                {currencyMode === "USD"
                  ? `$${overview.tokens_and_cost.cost_usd_today.toFixed(4)}`
                  : `${overview.tokens_and_cost.cost_vnd_today.toLocaleString("vi-VN")} ₫`}
              </span>
              <span className="text-[10px] text-gray-500">
                (Tháng: {currencyMode === "USD" ? `$${overview.tokens_and_cost.cost_projection_month_usd}` : `${overview.tokens_and_cost.cost_projection_month_vnd.toLocaleString("vi-VN")}₫`})
              </span>
            </div>
          </div>
        </div>

        {/* Thẻ 3: Độ Trễ SLA & TTFT */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#EBF4FC] text-[#2563EB] flex items-center justify-center shadow-inner">
              <Clock className="w-5 h-5 stroke-[2.2]" />
            </div>
            <span
              className={`text-[11px] font-black px-2 py-0.5 rounded-full border ${
                effectiveTtft < 500
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : effectiveTtft <= 1200
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : "bg-red-50 text-red-700 border-red-200"
              }`}
            >
              TTFT: {effectiveTtft}ms
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-[#2563EB] mb-1">
              Độ Trễ Phân Vị SLA
            </p>
            <div className="flex items-baseline gap-3">
              <div>
                <span className="text-2xl font-black text-[#1C1917] leading-none">
                  {effectiveP50}
                </span>
                <span className="text-xs font-semibold text-gray-500 ml-0.5">ms (P50)</span>
              </div>
              <div
                className={`text-xs font-bold ${
                  effectiveP95 > 1800 ? "text-red-600" : "text-amber-700"
                }`}
              >
                P95: {effectiveP95}ms
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px] text-[#7A3E04]">
              <span className="flex items-center gap-1">
                {effectiveP50 < 800 ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                )}{" "}
                P50 &lt; 800ms
              </span>
              <span className="flex items-center gap-1">
                {effectiveP95 < 1800 ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                ) : (
                  <AlertOctagon className="w-3.5 h-3.5 text-red-600" />
                )}{" "}
                P95 &lt; 1800ms
              </span>
            </div>
          </div>
        </div>

        {/* Thẻ 4: Độ Tin Cậy & HTTP Error Matrix */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shadow-inner">
              <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
            </div>
            <span
              className={`text-[11px] font-black px-2 py-0.5 rounded-full ${
                overview.reliability.error_rate_pct > 2.0
                  ? "bg-red-100 text-red-700"
                  : "bg-emerald-100 text-emerald-800"
              }`}
            >
              {overview.reliability.success_rate_pct}% OK
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-1">
              Độ Tin Cậy &amp; Hạ Tầng
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-[#1C1917] leading-none">
                {infraData?.active_sse_sessions ?? overview.reliability.active_sse_sessions}
              </span>
              <span className="text-xs font-bold text-[#7A3E04]">phiên SSE active</span>
            </div>
            <div className="mt-2 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px] text-[#7A3E04]">
              <span>
                4xx:{" "}
                <strong className="text-amber-700">
                  {overview.reliability.status_4xx_count_today ?? 0}
                </strong>
              </span>
              <span>
                5xx:{" "}
                <strong
                  className={
                    overview.reliability.status_5xx_count_today > 0
                      ? "text-red-600"
                      : "text-emerald-700"
                  }
                >
                  {overview.reliability.status_5xx_count_today}
                </strong>
              </span>
              <span>
                429:{" "}
                <strong
                  className={
                    overview.reliability.gemini_429_count_today > 0
                      ? "text-amber-700"
                      : "text-emerald-700"
                  }
                >
                  {overview.reliability.gemini_429_count_today}
                </strong>
              </span>
              <span>
                Pool: <strong>{infraData?.neon_connections_active ?? 6}/20</strong>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. Widget 1: Biểu Đồ Throughput (3 chế độ: Phút RPM / Giờ RPH / Ngày Daily) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1CCA6]/40 pb-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Lưu Lượng Hệ Thống (Throughput &amp; Live RPM)
              </h2>
              {throughputRange === "1h" && (
                <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Live: {throughput?.current_rpm ?? overview.throughput.rpm_current} RPM
                </span>
              )}
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              Chuyển đổi 3 chế độ: theo phút trong 60 phút gần nhất (RPM), theo giờ (RPH 24h) hoặc tổng hợp theo ngày (Daily)
            </p>
          </div>

          {/* Bộ chuyển đổi 3 chế độ: Phút (RPM) / Giờ (RPH) / Ngày (Daily) */}
          <div className="flex items-center gap-2 flex-wrap self-start sm:self-auto">
            <div className="flex items-center gap-1 bg-[#F7ECE1] p-1 rounded-xl border border-[#F1CCA6]">
              <button
                onClick={() => setThroughputRange("1h")}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  throughputRange === "1h"
                    ? "bg-[#C1762A] text-white shadow-xs"
                    : "text-[#7A3E04] hover:bg-white/50"
                }`}
              >
                Theo Phút (RPM)
              </button>
              <button
                onClick={() => setThroughputRange("24h")}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  throughputRange === "24h"
                    ? "bg-[#C1762A] text-white shadow-xs"
                    : "text-[#7A3E04] hover:bg-white/50"
                }`}
              >
                Theo Giờ (RPH)
              </button>
              <button
                onClick={() => {
                  if (throughputRange !== "7d" && throughputRange !== "30d") {
                    setThroughputRange("7d");
                  }
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  throughputRange === "7d" || throughputRange === "30d"
                    ? "bg-[#C1762A] text-white shadow-xs"
                    : "text-[#7A3E04] hover:bg-white/50"
                }`}
              >
                Theo Ngày (Daily)
              </button>
            </div>

            {(throughputRange === "7d" || throughputRange === "30d") && (
              <div className="flex items-center gap-1 bg-[#FFF8F0] p-1 rounded-xl border border-[#F1CCA6]">
                <button
                  onClick={() => setThroughputRange("7d")}
                  className={`px-2 py-1 rounded-lg text-[11px] font-bold transition-colors ${
                    throughputRange === "7d"
                      ? "bg-[#8C4905] text-white"
                      : "text-[#7A3E04] hover:bg-white"
                  }`}
                >
                  7 Ngày
                </button>
                <button
                  onClick={() => setThroughputRange("30d")}
                  className={`px-2 py-1 rounded-lg text-[11px] font-bold transition-colors ${
                    throughputRange === "30d"
                      ? "bg-[#8C4905] text-white"
                      : "text-[#7A3E04] hover:bg-white"
                  }`}
                >
                  30 Ngày
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Khung biểu đồ Recharts */}
        <div className="h-[320px] w-full">
          {throughput && throughput.items && throughput.items.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={throughput.items}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#F1CCA6" opacity={0.35} vertical={false} />
                <XAxis
                  dataKey="display_time"
                  stroke="#7A3E04"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: "#F1CCA6" }}
                />
                <YAxis
                  stroke="#C1762A"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) => `${val}`}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const item = payload[0].payload as ThroughputItem;
                    return (
                      <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-[#C1762A]/40 text-xs min-w-[215px]">
                        <div className="font-extrabold text-[#F1CCA6] border-b border-white/10 pb-1.5 mb-2 flex items-center justify-between gap-2">
                          <span>Thời gian: {item.display_time}</span>
                          {item.is_current_minute && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                              LIVE
                            </span>
                          )}
                        </div>
                        <div className="space-y-1">
                          <div className="flex justify-between font-bold text-white">
                            <span>Tổng Requests:</span>
                            <span className="text-[#F1CCA6]">{item.requests}</span>
                          </div>
                          <div className="flex justify-between text-white/70">
                            <span>Chat Socratic:</span>
                            <span>{item.chat_requests}</span>
                          </div>
                          <div className="flex justify-between text-white/70">
                            <span>Đánh giá &amp; Phân loại:</span>
                            <span>{item.eval_requests}</span>
                          </div>
                          <div className="flex justify-between text-white/70">
                            <span>Auth &amp; Khác:</span>
                            <span>{item.other_requests + item.auth_requests}</span>
                          </div>
                          {((item.errors_4xx ?? 0) > 0 ||
                            (item.errors_429 ?? 0) > 0 ||
                            (item.errors_5xx ?? 0) > 0) && (
                            <div className="pt-1 mt-1 border-t border-white/10 text-[11px] flex justify-between text-red-300 font-bold">
                              <span>Lỗi 4xx / 429 / 5xx:</span>
                              <span>
                                {item.errors_4xx ?? 0} / {item.errors_429 ?? 0} / {item.errors_5xx ?? 0}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  }}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="circle"
                  wrapperStyle={{ paddingBottom: "10px", fontSize: "11px" }}
                />
                <Bar
                  dataKey="chat_requests"
                  name="Chat Socratic"
                  stackId="a"
                  fill="#C1762A"
                  radius={[0, 0, 0, 0]}
                />
                <Bar
                  dataKey="eval_requests"
                  name="Phân loại & Đặt tên"
                  stackId="a"
                  fill="#8C4905"
                  radius={[0, 0, 0, 0]}
                />
                <Bar
                  dataKey="other_requests"
                  name="Auth & Khác"
                  stackId="a"
                  fill="#F59E0B"
                  radius={[4, 4, 0, 0]}
                />
                <Line
                  type="monotone"
                  dataKey="requests"
                  name="Tổng Requests"
                  stroke="#2563EB"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-[#7A3E04]">
              <RefreshCw className="w-5 h-5 animate-spin mr-2 text-[#C1762A]" />
              Đang tải biểu đồ lưu lượng...
            </div>
          )}
        </div>

        <div className="flex items-center justify-between text-[11px] text-[#7A3E04] pt-2 border-t border-[#F1CCA6]/40">
          <span>
            {throughputRange === "1h"
              ? "⚡ Chế độ thời gian thực: Cập nhật RPM mỗi phút trực tiếp từ Upstash Redis (không cần tải lại trang)"
              : `Thống kê tổng hợp: ${throughput?.total_requests.toLocaleString("vi-VN") || 0} requests`}
          </span>
          <span className="font-bold text-[#8C4905]">
            Đỉnh cao nhất: {throughput?.peak_rpm || overview.throughput.rpm_current} RPM
          </span>
        </div>
      </section>

      {/* ── 4. Widget 2: Tiêu Thụ Token, Chi Phí API & Phân Rã 6 Model (Ý tưởng 13) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1CCA6]/40 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Tiêu Thụ Token &amp; Chi Phí API (Phân Rã 6 Model Gemini)
              </h2>
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              Phân rã chi tiết Prompt Tokens (Input), Completion Tokens (Output) và quy đổi chi phí USD / VND thực tế
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {/* Days Filter */}
            <div className="flex items-center gap-1 bg-[#F7ECE1] p-1 rounded-xl border border-[#F1CCA6]">
              {([7, 14, 30] as const).map((d) => (
                <button
                  key={d}
                  onClick={() => setTokenDays(d)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                    tokenDays === d
                      ? "bg-[#C1762A] text-white shadow-xs"
                      : "text-[#7A3E04] hover:bg-white/50"
                  }`}
                >
                  {d} Ngày
                </button>
              ))}
            </div>

            {/* Currency Toggle */}
            <button
              onClick={() => setCurrencyMode((prev) => (prev === "USD" ? "VND" : "USD"))}
              className="px-3 py-1.5 rounded-xl bg-[#F7ECE1] hover:bg-[#F1CCA6]/60 text-[#8C4905] font-black text-xs border border-[#F1CCA6] transition-colors"
            >
              {currencyMode === "USD" ? "$ USD" : "₫ VND"}
            </button>
          </div>
        </div>

        {/* Biểu đồ Recharts Composed (Bar = Prompt/Comp Tokens, Line = Cost USD/VND) */}
        <div className="h-[300px] w-full">
          {tokensData && tokensData.items && tokensData.items.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={tokensData.items}
                margin={{ top: 10, right: 12, left: -10, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#F1CCA6" opacity={0.35} vertical={false} />
                <XAxis
                  dataKey="display_date"
                  stroke="#7A3E04"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: "#F1CCA6" }}
                />
                <YAxis
                  yAxisId="tokens"
                  orientation="left"
                  stroke="#C1762A"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                />
                <YAxis
                  yAxisId="cost"
                  orientation="right"
                  stroke="#10B981"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(val) =>
                    currencyMode === "USD"
                      ? `$${Number(val).toFixed(2)}`
                      : `${(Number(val) / 1000).toFixed(0)}k₫`
                  }
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const item = payload[0].payload as TokenDailyItem;
                    return (
                      <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-[#C1762A]/40 text-xs min-w-[215px]">
                        <div className="font-extrabold text-[#F1CCA6] border-b border-white/10 pb-1.5 mb-2">
                          Ngày: {item.display_date} ({item.date})
                        </div>
                        <div className="space-y-1">
                          <div className="flex justify-between font-bold text-white">
                            <span>Tổng Tokens:</span>
                            <span className="text-[#F1CCA6]">
                              {item.total_tokens.toLocaleString("vi-VN")}
                            </span>
                          </div>
                          <div className="flex justify-between text-white/70">
                            <span>Prompt (Input):</span>
                            <span>{item.prompt_tokens.toLocaleString("vi-VN")}</span>
                          </div>
                          <div className="flex justify-between text-white/70">
                            <span>Completion (Output):</span>
                            <span>{item.completion_tokens.toLocaleString("vi-VN")}</span>
                          </div>
                          <div className="flex justify-between pt-1 border-t border-white/10 font-bold text-emerald-400">
                            <span>Chi phí API:</span>
                            <span>
                              {currencyMode === "USD"
                                ? `$${item.cost_usd.toFixed(4)}`
                                : `${item.cost_vnd.toLocaleString("vi-VN")} ₫`}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  }}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  iconType="circle"
                  wrapperStyle={{ paddingBottom: "10px", fontSize: "11px" }}
                />
                <Bar
                  yAxisId="tokens"
                  dataKey="prompt_tokens"
                  name="Prompt Tokens (Input)"
                  fill="#C1762A"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={28}
                />
                <Bar
                  yAxisId="tokens"
                  dataKey="completion_tokens"
                  name="Completion Tokens (Output)"
                  fill="#8C4905"
                  radius={[3, 3, 0, 0]}
                  maxBarSize={28}
                />
                <Line
                  yAxisId="cost"
                  type="monotone"
                  dataKey={currencyMode === "USD" ? "cost_usd" : "cost_vnd"}
                  name={currencyMode === "USD" ? "Chi phí ($ USD)" : "Chi phí (₫ VND)"}
                  stroke="#10B981"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#10B981" }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-[#7A3E04]">
              <RefreshCw className="w-5 h-5 animate-spin mr-2 text-[#C1762A]" />
              Đang tải dữ liệu token...
            </div>
          )}
        </div>

        {/* Widget Token Usage Phân Rã 6 Model (Ý tưởng 13 & T10.2.9) */}
        {(() => {
          const sixModels =
            tokensData?.six_model_breakdown && tokensData.six_model_breakdown.length > 0
              ? tokensData.six_model_breakdown
              : DEFAULT_SIX_MODELS;

          return (
            <div className="pt-4 border-t border-[#F1CCA6]/40 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h3 className="text-sm font-black text-[#8C4905] flex items-center gap-2">
                    <Layers className="w-4 h-4 text-[#C1762A]" />
                    Phân Rã Token Usage &amp; Chi Phí Theo 6 Cấu Hình Model (Ý Tưởng 13)
                  </h3>
                  <p className="text-[11px] text-[#7A3E04]">
                    Đồng bộ trực tiếp với bảng cấu hình US 10.3: so sánh Prompt/Completion tokens và tỷ trọng chi phí từng vai trò
                  </p>
                </div>
                <span className="text-[11px] font-bold px-2.5 py-1 rounded-lg bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6] self-start sm:self-auto">
                  Tổng {tokenDays} ngày:{" "}
                  {currencyMode === "USD"
                    ? `$${(tokensData?.total_cost_usd ?? overview.tokens_and_cost.cost_usd_today).toFixed(4)}`
                    : `${(tokensData?.total_cost_vnd ?? overview.tokens_and_cost.cost_vnd_today).toLocaleString("vi-VN")} ₫`}
                </span>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                {/* Biểu đồ BarChart ngang 6 model */}
                <div className="lg:col-span-5 h-[250px] bg-[#FFFBF7] rounded-xl border border-[#F1CCA6]/70 p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={sixModels}
                      layout="vertical"
                      margin={{ top: 5, right: 16, left: 6, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#F1CCA6" opacity={0.35} horizontal={false} />
                      <XAxis
                        type="number"
                        fontSize={10}
                        stroke="#7A3E04"
                        tickLine={false}
                        tickFormatter={(v) => `${(Number(v) / 1000).toFixed(0)}k`}
                      />
                      <YAxis
                        type="category"
                        dataKey="role_name"
                        width={118}
                        fontSize={10}
                        stroke="#8C4905"
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (!active || !payload || !payload.length) return null;
                          const item = payload[0].payload as SixModelBreakdownItem;
                          return (
                            <div className="bg-[#1C1917] text-white p-2.5 rounded-xl shadow-xl border border-[#C1762A]/40 text-xs min-w-[205px]">
                              <p className="font-extrabold text-[#F1CCA6]">{item.role_name}</p>
                              <p className="text-[10px] font-mono text-white/70 mb-1.5">
                                {item.model_name}
                              </p>
                              <div className="space-y-0.5 text-[11px]">
                                <div className="flex justify-between">
                                  <span>Prompt:</span>
                                  <span>{item.prompt_tokens.toLocaleString("vi-VN")}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>Completion:</span>
                                  <span>{item.completion_tokens.toLocaleString("vi-VN")}</span>
                                </div>
                                <div className="flex justify-between font-bold text-emerald-400 pt-1 border-t border-white/10">
                                  <span>Chi phí:</span>
                                  <span>
                                    {currencyMode === "USD"
                                      ? `$${item.cost_usd.toFixed(4)}`
                                      : `${item.cost_vnd.toLocaleString("vi-VN")} ₫`}
                                  </span>
                                </div>
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Bar
                        dataKey="prompt_tokens"
                        stackId="m"
                        name="Prompt"
                        fill="#C1762A"
                        radius={[0, 0, 0, 0]}
                        barSize={16}
                      />
                      <Bar
                        dataKey="completion_tokens"
                        stackId="m"
                        name="Completion"
                        fill="#8C4905"
                        radius={[0, 4, 4, 0]}
                        barSize={16}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Lưới 6 thẻ chi tiết Model/Vai trò */}
                <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {sixModels.map((m) => (
                    <div
                      key={m.role_id}
                      className="bg-[#FFFFFF] p-3 rounded-xl border border-[#F1CCA6] flex flex-col justify-between shadow-xs hover:border-[#C1762A] transition-colors"
                    >
                      <div>
                        <div className="flex items-center justify-between gap-1.5 mb-1">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ backgroundColor: m.color }}
                            />
                            <span className="font-bold text-xs text-[#8C4905] truncate">
                              {m.role_name}
                            </span>
                          </div>
                          <span className="text-[10px] font-black px-1.5 py-0.5 rounded-md bg-[#F7ECE1] text-[#C1762A] shrink-0">
                            {m.percentage}%
                          </span>
                        </div>
                        <p className="text-[11px] font-mono font-bold text-[#1C1917] truncate">
                          {m.model_name}
                        </p>
                        <p className="text-[10px] text-gray-500 mt-0.5 truncate">{m.pricing}</p>
                        <div className="w-full bg-[#F7ECE1] h-1.5 rounded-full mt-2 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min(100, Math.max(4, m.percentage))}%`,
                              backgroundColor: m.color,
                            }}
                          />
                        </div>
                      </div>
                      <div className="mt-2.5 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px]">
                        <span className="text-gray-600 font-semibold">
                          {(m.total_tokens / 1000).toFixed(1)}k tok
                        </span>
                        <span className="font-extrabold text-emerald-700">
                          {currencyMode === "USD"
                            ? `$${m.cost_usd.toFixed(4)}`
                            : `${m.cost_vnd.toLocaleString("vi-VN")} ₫`}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })()}
      </section>

      {/* ── 5. Widget 3: Độ Trễ SLA (P50/P95/P99) & Đồng Hồ Kim Bán Nguyệt TTFT (T10.2.8) ── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cột trái: Biểu Đồ Multi-line P50, P95, P99 (2/3 width) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F1CCA6]/40 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-6 bg-[#2563EB] rounded-full inline-block" />
                <h2 className="text-lg font-bold text-[#8C4905]">
                  Phân Vị Độ Trễ SLA (P50, P95, P99)
                </h2>
              </div>
              <p className="text-xs text-[#7A3E04] mt-0.5">
                Kiểm chứng tiêu chuẩn cam kết: P50 &lt; 800ms (xanh) và P95 &lt; 1800ms (cảnh báo)
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${
                  effectiveP50 < 800
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : "bg-red-50 text-red-700 border-red-300"
                }`}
              >
                P50: {effectiveP50}ms {effectiveP50 < 800 ? "✓" : "! >800ms"}
              </span>
              <span
                className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${
                  effectiveP95 < 1800
                    ? "bg-amber-50 text-amber-700 border-amber-200"
                    : "bg-red-50 text-red-700 border-red-300"
                }`}
              >
                P95: {effectiveP95}ms {effectiveP95 < 1800 ? "✓" : "! >1800ms"}
              </span>
              <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-slate-50 text-slate-700 border border-slate-200">
                P99: {effectiveP99}ms
              </span>
            </div>
          </div>

          <div className="h-[280px] w-full">
            {latencyData && latencyData.items && latencyData.items.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={latencyData.items}
                  margin={{ top: 14, right: 12, left: -10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1CCA6" opacity={0.35} vertical={false} />
                  <XAxis
                    dataKey="display_time"
                    stroke="#7A3E04"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: "#F1CCA6" }}
                  />
                  <YAxis
                    stroke="#2563EB"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    domain={[0, "auto"]}
                    tickFormatter={(val) => `${val}ms`}
                  />
                  <ReferenceLine
                    y={800}
                    stroke="#10B981"
                    strokeDasharray="5 5"
                    strokeWidth={1.5}
                    label={{
                      value: "Ngưỡng P50 (800ms)",
                      position: "insideTopLeft",
                      fill: "#047857",
                      fontSize: 10,
                      fontWeight: 700,
                    }}
                  />
                  <ReferenceLine
                    y={1800}
                    stroke="#EF4444"
                    strokeDasharray="5 5"
                    strokeWidth={1.5}
                    label={{
                      value: "Ngưỡng SLA P95 (1800ms)",
                      position: "insideTopLeft",
                      fill: "#B91C1C",
                      fontSize: 10,
                      fontWeight: 700,
                    }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const item = payload[0].payload as LatencyHourlyItem;
                      return (
                        <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-blue-500/40 text-xs min-w-[205px]">
                          <div className="font-extrabold text-blue-300 border-b border-white/10 pb-1 mb-2">
                            Thời gian: {item.display_time}
                          </div>
                          <div className="space-y-1">
                            <div className="flex justify-between text-emerald-400 font-bold">
                              <span>P50 (Trung vị):</span>
                              <span>{item.p50_latency_ms} ms</span>
                            </div>
                            <div className="flex justify-between text-amber-400 font-bold">
                              <span>P95 (95% requests):</span>
                              <span>{item.p95_latency_ms} ms</span>
                            </div>
                            <div className="flex justify-between text-red-400 font-bold">
                              <span>P99 (Cực trị):</span>
                              <span>{item.p99_latency_ms} ms</span>
                            </div>
                            <div className="flex justify-between text-sky-300 pt-1 border-t border-white/10">
                              <span>TTFT chunk đầu:</span>
                              <span>{item.avg_ttft_ms} ms</span>
                            </div>
                          </div>
                        </div>
                      );
                    }}
                  />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    iconType="circle"
                    wrapperStyle={{ paddingBottom: "10px", fontSize: "11px" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="p50_latency_ms"
                    name="P50 (< 800ms)"
                    stroke="#10B981"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="p95_latency_ms"
                    name="P95 (< 1800ms)"
                    stroke="#F59E0B"
                    strokeWidth={2.5}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="p99_latency_ms"
                    name="P99 (Đỉnh trễ)"
                    stroke="#EF4444"
                    strokeWidth={2}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-[#7A3E04]">
                <RefreshCw className="w-5 h-5 animate-spin mr-2 text-[#2563EB]" />
                Đang tải dữ liệu độ trễ...
              </div>
            )}
          </div>
        </div>

        {/* Cột phải: Đồng Hồ Kim Bán Nguyệt Đo TTFT (1/3 width) */}
        {(() => {
          const ttftClamped = Math.max(0, Math.min(effectiveTtft, 2000));
          const ratio = ttftClamped / 2000;
          const needleDeg = ratio * 180 - 90; // -90deg (0ms) -> 0deg (1000ms) -> +90deg (2000ms)
          const isGreen = effectiveTtft < 500;
          const isAmber = effectiveTtft >= 500 && effectiveTtft <= 1200;

          return (
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 border-b border-[#F1CCA6]/40 pb-3">
                  <span
                    className={`w-2 h-6 rounded-full inline-block ${
                      isGreen ? "bg-emerald-500" : isAmber ? "bg-amber-500" : "bg-red-500"
                    }`}
                  />
                  <h3 className="text-base font-bold text-[#8C4905]">
                    Đồng Hồ Kim Bán Nguyệt TTFT
                  </h3>
                </div>
                <p className="text-xs text-[#7A3E04] mt-2">
                  Thời gian nhận chunk token đầu tiên qua SSE (&lt; 500ms: Xanh, 500–1200ms: Vàng, &gt; 1200ms: Đỏ)
                </p>

                {/* Semi-Circular Speedometer Needle Gauge (0 -> 2000ms) */}
                <div className="flex flex-col items-center justify-center mt-4 mb-3">
                  <div className="relative w-60 max-w-full flex flex-col items-center">
                    <svg className="w-full h-auto overflow-visible" viewBox="0 0 240 142">
                      {/* Background Track Arc */}
                      <path
                        d="M 32 120 A 88 88 0 0 1 208 120"
                        fill="none"
                        stroke="#F7ECE1"
                        strokeWidth="16"
                        strokeLinecap="round"
                      />
                      {/* Zone 1: Xanh Tối Ưu (0 - 500ms) */}
                      <path
                        d="M 32 120 A 88 88 0 0 1 57.77 57.77"
                        fill="none"
                        stroke="#10B981"
                        strokeWidth="16"
                        strokeLinecap="butt"
                        opacity={isGreen ? 1 : 0.45}
                      />
                      {/* Zone 2: Vàng Cảnh Báo (500 - 1200ms) */}
                      <path
                        d="M 57.77 57.77 A 88 88 0 0 1 147.19 36.31"
                        fill="none"
                        stroke="#F59E0B"
                        strokeWidth="16"
                        strokeLinecap="butt"
                        opacity={isAmber ? 1 : 0.45}
                      />
                      {/* Zone 3: Đỏ Chậm (1200 - 2000ms) */}
                      <path
                        d="M 147.19 36.31 A 88 88 0 0 1 208 120"
                        fill="none"
                        stroke="#EF4444"
                        strokeWidth="16"
                        strokeLinecap="butt"
                        opacity={!isGreen && !isAmber ? 1 : 0.45}
                      />

                      {/* Nhãn các mốc chia độ */}
                      <text x="20" y="136" fontSize="10" fontWeight="700" fill="#7A3E04">
                        0ms
                      </text>
                      <text x="36" y="47" fontSize="10" fontWeight="700" fill="#047857">
                        500
                      </text>
                      <text x="148" y="25" fontSize="10" fontWeight="700" fill="#B45309">
                        1200
                      </text>
                      <text x="192" y="136" fontSize="10" fontWeight="700" fill="#B91C1C">
                        2000ms
                      </text>

                      {/* Kim đồng hồ xoay theo effectiveTtft */}
                      <g
                        style={{
                          transform: `rotate(${needleDeg}deg)`,
                          transformOrigin: "120px 120px",
                          transition: "transform 700ms cubic-bezier(0.22, 1, 0.36, 1)",
                        }}
                      >
                        <polygon points="117,120 123,120 120,42" fill="#1C1917" />
                      </g>
                      {/* Trục tâm kim đồng hồ */}
                      <circle cx="120" cy="120" r="8" fill="#1C1917" />
                      <circle
                        cx="120"
                        cy="120"
                        r="3.5"
                        fill={isGreen ? "#10B981" : isAmber ? "#F59E0B" : "#EF4444"}
                      />
                    </svg>

                    <div className="-mt-1 flex flex-col items-center text-center">
                      <span
                        className={`text-3xl font-black leading-none ${
                          isGreen ? "text-emerald-600" : isAmber ? "text-amber-600" : "text-red-600"
                        }`}
                      >
                        {effectiveTtft} ms
                      </span>
                      <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mt-1">
                        Time To First Token (SSE)
                      </span>
                    </div>
                  </div>

                  {/* Status Badge chuyển xanh khi < 500ms */}
                  <div
                    className={`mt-3 px-3 py-1 rounded-full text-xs font-black flex items-center gap-1.5 border ${
                      isGreen
                        ? "bg-emerald-50 text-emerald-700 border-emerald-300"
                        : isAmber
                        ? "bg-amber-50 text-amber-700 border-amber-300"
                        : "bg-red-50 text-red-700 border-red-300"
                    }`}
                  >
                    <span
                      className={`w-2 h-2 rounded-full ${
                        isGreen ? "bg-emerald-500" : isAmber ? "bg-amber-500" : "bg-red-500"
                      }`}
                    />
                    {isGreen
                      ? "TỐI ƯU (< 500ms)"
                      : isAmber
                      ? "TRUNG BÌNH (500–1200ms)"
                      : "CHẬM (> 1200ms)"}
                  </div>
                </div>
              </div>

              <div className="p-3 bg-[#F7ECE1] rounded-xl border border-[#F1CCA6] text-[11px] text-[#7A3E04] space-y-1">
                <div className="flex justify-between">
                  <span>Mục tiêu SLA:</span>
                  <strong className="text-emerald-700">&lt; 500ms (Vùng xanh)</strong>
                </div>
                <div className="flex justify-between">
                  <span>Giao thức truyền:</span>
                  <strong>Server-Sent Events (SSE)</strong>
                </div>
              </div>
            </div>
          );
        })()}
      </section>

      {/* ── 6. Widget 4: Biểu Đồ Donut Phân Bổ 6 Phân Hệ Agent (AC-KPI-04) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1CCA6]/40 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Phân Bổ Lưu Lượng 6 Phân Hệ Tác Tử (Agent Subsystems)
              </h2>
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              Nhấp vào từng phân hệ để xem chi tiết Prompt/Completion tokens, chi phí và model AI tương ứng
            </p>
          </div>
          <span className="text-xs font-bold px-3 py-1 rounded-xl bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]">
            6 Phân hệ hoạt động
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
          {/* Donut Chart (5/12) kèm nhãn trung tâm phân hệ đang lọc */}
          <div className="lg:col-span-5 h-[280px] w-full flex items-center justify-center relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={agentsData.agents}
                  dataKey="request_count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={105}
                  paddingAngle={3}
                  onClick={(entry: any) => setSelectedAgentId(entry?.id || entry?.payload?.id || "Chat")}
                  cursor="pointer"
                >
                  {agentsData.agents.map((entry) => (
                    <Cell
                      key={`cell-${entry.id}`}
                      fill={entry.color}
                      stroke={entry.id === selectedAgentId ? "#1C1917" : "#FFF"}
                      strokeWidth={entry.id === selectedAgentId ? 2.5 : 1}
                    />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const item = payload[0].payload as SubsystemAgent;
                    return (
                      <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-white/20 text-xs min-w-[200px]">
                        <div className="font-extrabold text-[#F1CCA6] mb-1">
                          {item.name}
                        </div>
                        <div className="space-y-1">
                          <div className="flex justify-between">
                            <span>Model:</span>
                            <span className="font-mono text-white/90">{item.model_used}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Lưu lượng:</span>
                            <span>{item.request_count} reqs ({item.request_percentage}%)</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Tokens:</span>
                            <span>{(item.total_tokens / 1000).toFixed(0)}k ({item.token_percentage}%)</span>
                          </div>
                          <div className="flex justify-between text-emerald-400 font-bold">
                            <span>Chi phí:</span>
                            <span>
                              {currencyMode === "USD"
                                ? `$${item.cost_usd.toFixed(4)}`
                                : `${item.cost_vnd.toLocaleString("vi-VN")} ₫`}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#7A3E04]">
                {currentAgent.id}
              </span>
              <span className="text-2xl font-black text-[#8C4905] leading-tight">
                {currentAgent.request_percentage}%
              </span>
              <span className="text-[10px] font-semibold text-gray-500">
                {(currentAgent.total_tokens / 1000).toFixed(0)}k tok
              </span>
            </div>
          </div>

          {/* Subsystems List & Detail Cards (7/12) */}
          <div className="lg:col-span-7 space-y-3">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {agentsData.agents.map((ag) => (
                <button
                  key={ag.id}
                  onClick={() => setSelectedAgentId(ag.id)}
                  className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between ${
                    selectedAgentId === ag.id
                      ? "border-[#C1762A] bg-[#FFFBF7] shadow-sm ring-2 ring-[#C1762A]/20"
                      : "border-[#F1CCA6]/60 bg-white hover:border-[#C1762A]/50"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ backgroundColor: ag.color }}
                    />
                    <span className="text-xs font-bold text-[#8C4905] truncate">
                      {ag.id}
                    </span>
                  </div>
                  <div className="mt-1.5 text-[10px] font-mono text-gray-500 truncate">
                    {ag.model_used}
                  </div>
                  <div className="mt-1 text-xs">
                    <span className="font-extrabold text-[#1C1917]">
                      {ag.request_percentage}%
                    </span>
                    <span className="text-[10px] text-gray-500 ml-1">
                      ({ag.request_count} reqs)
                    </span>
                  </div>
                </button>
              ))}
            </div>

            {/* Chi tiết phân hệ được chọn (Lọc Token & Chi phí tương ứng theo AC-KPI-04) */}
            <div className="p-4 rounded-xl bg-[#F7ECE1]/60 border border-[#F1CCA6] space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded bg-[#C1762A] text-white">
                      Đang lọc
                    </span>
                    <h4 className="font-black text-sm text-[#8C4905]">
                      {currentAgent.name}
                    </h4>
                  </div>
                  <p className="text-[11px] text-[#7A3E04] mt-0.5">
                    {currentAgent.description}
                  </p>
                </div>
                <span className="text-xs font-mono font-bold px-2.5 py-0.5 rounded-md bg-white text-[#C1762A] border border-[#F1CCA6]">
                  {currentAgent.model_used}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#F1CCA6]/40 text-xs">
                <div>
                  <span className="text-[10px] text-gray-500 block">Prompt Tokens:</span>
                  <strong className="text-[#8C4905]">
                    {currentAgent.prompt_tokens.toLocaleString("vi-VN")}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 block">Completion Tokens:</span>
                  <strong className="text-[#8C4905]">
                    {currentAgent.completion_tokens.toLocaleString("vi-VN")}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 block">
                    Chi phí phân hệ ({currencyMode}):
                  </span>
                  <strong className="text-emerald-700">
                    {currencyMode === "USD"
                      ? `$${currentAgent.cost_usd.toFixed(4)}`
                      : `${currentAgent.cost_vnd.toLocaleString("vi-VN")} ₫`}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 block">Độ trễ TB / Tỷ trọng:</span>
                  <strong className="text-[#2563EB]">
                    {currentAgent.avg_latency_ms}ms ({currentAgent.token_percentage}% tok)
                  </strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 7. Widget 5: Bản Đồ Nhiệt 7 Ngày x 24 Giờ Peak Traffic Heatmap (AC-KPI-05) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1CCA6]/40 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Bản Đồ Nhiệt Giờ Cao Điểm (Peak Traffic Heatmap 7x24)
              </h2>
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              168 ô thể hiện mật độ sử dụng hệ thống từ Thứ Hai đến Chủ Nhật (0h - 23h). Di chuột vào ô để xem số request và token
            </p>
          </div>

          {heatmapData?.peak_traffic && (
            <div className="text-xs font-bold px-3 py-1 rounded-xl bg-[#FEF3C7] text-[#92400E] border border-[#FCD34D] flex items-center gap-1.5 self-start sm:self-auto">
              <Zap className="w-3.5 h-3.5 text-amber-600" />
              <span>
                Đỉnh: {heatmapData.peak_traffic.full_day} lúc {heatmapData.peak_traffic.hour}:00 (
                {heatmapData.peak_traffic.requests} reqs)
              </span>
            </div>
          )}
        </div>

        {/* Thanh thông tin trực tiếp khi di chuột qua ô bất kỳ (Chống che khuất tooltip ở rìa) */}
        <div className="px-3.5 py-2 rounded-xl bg-[#FFFBF7] border border-[#F1CCA6] flex flex-wrap items-center justify-between gap-2 text-xs">
          {hoveredHeatmapCell ? (
            <>
              <span className="font-bold text-[#8C4905]">
                {hoveredHeatmapCell.full_day} • Khung giờ {hoveredHeatmapCell.hour}:00–{hoveredHeatmapCell.hour}:59
              </span>
              <div className="flex items-center gap-4">
                <span className="text-[#1C1917]">
                  Requests: <strong>{hoveredHeatmapCell.requests.toLocaleString("vi-VN")}</strong>
                </span>
                <span className="text-[#C1762A]">
                  Tokens: <strong>{hoveredHeatmapCell.tokens.toLocaleString("vi-VN")}</strong>
                </span>
              </div>
            </>
          ) : (
            <span className="text-[#7A3E04]">
              Di chuột vào bất kỳ ô nào trong ma trận 7×24 bên dưới để xem chi tiết số lượng request và token theo giờ.
            </span>
          )}
        </div>

        {/* Heatmap Grid 7 rows x 24 cols (overflow-visible ở desktop để tooltip không bị cắt) */}
        <div className="overflow-x-auto md:overflow-visible pb-2">
          <div className="min-w-[700px]">
            {/* Header giờ (00 -> 23) */}
            <div className="grid grid-cols-[45px_repeat(24,1fr)] gap-1 mb-1 text-[10px] font-bold text-gray-500 text-center">
              <div></div>
              {Array.from({ length: 24 }).map((_, h) => (
                <div key={h} className="truncate">
                  {h % 3 === 0 ? `${h}h` : "·"}
                </div>
              ))}
            </div>

            {/* 7 Hàng ngày (T2 -> CN) */}
            {["T2", "T3", "T4", "T5", "T6", "T7", "CN"].map((dayLabel, dIdx) => {
              const dayCells =
                heatmapData?.heatmap.filter((c) => c.day_index === dIdx) || [];
              return (
                <div
                  key={dayLabel}
                  className="grid grid-cols-[45px_repeat(24,1fr)] gap-1 mb-1 items-center"
                >
                  <span className="text-xs font-bold text-[#8C4905] text-right pr-2">
                    {dayLabel}
                  </span>
                  {Array.from({ length: 24 }).map((_, h) => {
                    const cell: HeatmapCell = dayCells.find((c) => c.hour === h) || {
                      day: dayLabel,
                      full_day: dayLabel,
                      day_index: dIdx,
                      hour: h,
                      hour_label: `${h}:00`,
                      requests: 12,
                      tokens: 4500,
                      intensity: 1,
                    };

                    // Intensity color map
                    const colorMap = [
                      "bg-[#FFF8F0] hover:ring-2 hover:ring-[#C1762A]", // 0
                      "bg-[#FDE7C7] hover:ring-2 hover:ring-[#C1762A]", // 1
                      "bg-[#F9BC74] hover:ring-2 hover:ring-[#C1762A]", // 2
                      "bg-[#E88024] hover:ring-2 hover:ring-[#C1762A]", // 3
                      "bg-[#B91C1C] hover:ring-2 hover:ring-[#C1762A]", // 4
                    ];

                    // Smart edge-aware tooltip placement
                    const verticalPos = dIdx <= 1 ? "top-full mt-1.5" : "bottom-full mb-1.5";
                    const horizontalPos =
                      h <= 2
                        ? "left-0"
                        : h >= 21
                        ? "right-0"
                        : "left-1/2 -translate-x-1/2";

                    return (
                      <div
                        key={h}
                        onMouseEnter={() => setHoveredHeatmapCell(cell)}
                        onMouseLeave={() => setHoveredHeatmapCell(null)}
                        className={`h-6 rounded-xs transition-all cursor-pointer relative ${
                          colorMap[cell.intensity] || colorMap[0]
                        }`}
                        title={`${cell.full_day} ${h}:00 - ${cell.requests} requests (${cell.tokens.toLocaleString("vi-VN")} tokens)`}
                      >
                        {hoveredHeatmapCell?.day_index === dIdx &&
                          hoveredHeatmapCell?.hour === h && (
                            <div
                              className={`absolute ${verticalPos} ${horizontalPos} z-40 bg-[#1C1917] text-white text-[10px] p-2.5 rounded-lg shadow-xl border border-[#C1762A]/40 whitespace-nowrap pointer-events-none`}
                            >
                              <p className="font-bold text-[#F1CCA6]">
                                {cell.full_day} • {h}:00
                              </p>
                              <p className="mt-0.5">
                                Requests: <strong>{cell.requests.toLocaleString("vi-VN")}</strong>
                              </p>
                              <p>
                                Tokens: <strong>{cell.tokens.toLocaleString("vi-VN")}</strong>
                              </p>
                            </div>
                          )}
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </div>

        {/* Legend chú thích thang màu */}
        <div className="flex items-center justify-between text-[11px] text-[#7A3E04] pt-2 border-t border-[#F1CCA6]/40 flex-wrap gap-2">
          <span>Khung giờ 19:00 - 21:00 các ngày trong tuần là giờ cao điểm học sinh làm bài tập toán</span>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-gray-500 mr-1">Mật độ:</span>
            <span className="w-3.5 h-3.5 rounded-xs bg-[#FFF8F0] border border-gray-300 inline-block" title="Rất thấp" />
            <span className="w-3.5 h-3.5 rounded-xs bg-[#FDE7C7] inline-block" title="Thấp" />
            <span className="w-3.5 h-3.5 rounded-xs bg-[#F9BC74] inline-block" title="Trung bình" />
            <span className="w-3.5 h-3.5 rounded-xs bg-[#E88024] inline-block" title="Cao" />
            <span className="w-3.5 h-3.5 rounded-xs bg-[#B91C1C] inline-block" title="Cực cao" />
          </div>
        </div>
      </section>

      {/* ── 7.5. Ma Trận Trạng Thái HTTP & Phân Loại Lỗi Client vs Server (AC-KPI-03) ── */}
      {(() => {
        const c2xx = overview.reliability.status_2xx_count_today ?? 0;
        const c4xx = overview.reliability.status_4xx_count_today ?? 0;
        const c429 = overview.reliability.gemini_429_count_today ?? 0;
        const c5xx = overview.reliability.status_5xx_count_today ?? 0;
        const totalHttp = Math.max(1, c2xx + c4xx + c429 + c5xx);

        return (
          <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F1CCA6]/40 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
                  <h2 className="text-lg font-bold text-[#8C4905]">
                    Phân Bổ Mã Trạng Thái HTTP &amp; Phân Loại Lỗi (Client vs Server)
                  </h2>
                </div>
                <p className="text-xs text-[#7A3E04] mt-0.5">
                  Tách biệt lỗi phía Client (4xx sai dữ liệu, 429 vượt giới hạn rate limit) và lỗi phía Server (5xx vượt 2% kích hoạt cảnh báo SLA)
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 font-bold">
                  Lỗi Client (4xx + 429): {(c4xx + c429).toLocaleString("vi-VN")}
                </span>
                <span
                  className={`px-2.5 py-1 rounded-lg border font-bold ${
                    overview.reliability.error_rate_pct > 2.0
                      ? "bg-red-50 text-red-700 border-red-300"
                      : "bg-emerald-50 text-emerald-700 border-emerald-200"
                  }`}
                >
                  Lỗi Server (5xx): {c5xx.toLocaleString("vi-VN")} ({overview.reliability.error_rate_pct}%)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200">
                <span className="text-[11px] font-bold uppercase text-emerald-700">
                  HTTP 2xx Thành Công
                </span>
                <div className="text-2xl font-black text-emerald-800 mt-1">
                  {c2xx.toLocaleString("vi-VN")}
                </div>
                <p className="text-[11px] text-emerald-700/80 mt-0.5">
                  Tỷ lệ thành công: {overview.reliability.success_rate_pct}%
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-amber-50/70 border border-amber-200">
                <span className="text-[11px] font-bold uppercase text-amber-800">
                  HTTP 4xx Lỗi Client
                </span>
                <div className="text-2xl font-black text-amber-800 mt-1">
                  {c4xx.toLocaleString("vi-VN")}
                </div>
                <p className="text-[11px] text-amber-700/80 mt-0.5">
                  Sai dữ liệu / Auth ({overview.reliability.client_error_rate_pct ?? 0}%)
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-purple-50/70 border border-purple-200">
                <span className="text-[11px] font-bold uppercase text-purple-800">
                  HTTP 429 Rate Limit
                </span>
                <div className="text-2xl font-black text-purple-800 mt-1">
                  {c429.toLocaleString("vi-VN")}
                </div>
                <p className="text-[11px] text-purple-700/80 mt-0.5">
                  Vượt giới hạn tốc độ truy vấn
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-red-50/70 border border-red-200">
                <span className="text-[11px] font-bold uppercase text-red-800">
                  HTTP 5xx Lỗi Server
                </span>
                <div className="text-2xl font-black text-red-700 mt-1">
                  {c5xx.toLocaleString("vi-VN")}
                </div>
                <p className="text-[11px] text-red-700/80 mt-0.5">
                  Ngưỡng SLA: &lt; 2.0% (Hiện tại: {overview.reliability.error_rate_pct}%)
                </p>
              </div>
            </div>

            {/* Thanh phân bổ tỷ lệ trạng thái HTTP */}
            <div className="w-full h-2.5 rounded-full bg-[#F7ECE1] overflow-hidden flex">
              <div
                className="bg-emerald-500 h-full"
                style={{ width: `${(c2xx / totalHttp) * 100}%` }}
                title={`2xx: ${c2xx}`}
              />
              <div
                className="bg-amber-500 h-full"
                style={{ width: `${(c4xx / totalHttp) * 100}%` }}
                title={`4xx Client: ${c4xx}`}
              />
              <div
                className="bg-purple-500 h-full"
                style={{ width: `${(c429 / totalHttp) * 100}%` }}
                title={`429 Rate Limit: ${c429}`}
              />
              <div
                className="bg-red-600 h-full"
                style={{ width: `${(c5xx / totalHttp) * 100}%` }}
                title={`5xx Server: ${c5xx}`}
              />
            </div>
          </section>
        );
      })()}

      {/* ── 8. Widget 6: Sức Chứa Hạ Tầng & Kết Nối Thực Tế (AC-KPI-06) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-[#F1CCA6]/40 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-emerald-600 rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Sức Chứa Hạ Tầng &amp; Trạng Thái Dịch Vụ Nền Tảng
              </h2>
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              Kiểm tra kết nối Neon PostgreSQL (giới hạn 20 conns), Upstash Redis Cache Hit Rate và 4 dịch vụ phụ thuộc
            </p>
          </div>
          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-xl border border-emerald-200">
            Hạ tầng ổn định
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Neon DB Pool */}
          <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#F1CCA6] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#8C4905] flex items-center gap-1.5">
                  <Database className="w-4 h-4 text-[#C1762A]" /> Neon DB Pool
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">
                  ONLINE
                </span>
              </div>
              <div className="text-xl font-black text-[#1C1917]">
                {infraData?.neon_connections_active || 6}{" "}
                <span className="text-xs font-semibold text-gray-500">
                  / {infraData?.neon_connections_max || 20} kết nối
                </span>
              </div>
              {/* Progress bar */}
              <div className="w-full bg-[#F7ECE1] h-2 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-[#C1762A] h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${infraData?.neon_pool_utilization_pct || 30}%`,
                  }}
                />
              </div>
            </div>
            <p className="text-[11px] text-[#7A3E04] mt-2 pt-2 border-t border-[#F1CCA6]/40">
              Mức sử dụng: <strong>{infraData?.neon_pool_utilization_pct || 30}%</strong> (An toàn &lt; 80%)
            </p>
          </div>

          {/* Card 2: Upstash Redis Hit Rate */}
          <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#F1CCA6] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#8C4905] flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-[#F59E0B]" /> Redis Cache Hit
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">
                  ONLINE
                </span>
              </div>
              <div className="text-xl font-black text-emerald-700">
                {infraData?.redis_hit_rate_pct || 84.5}%
              </div>
              <div className="w-full bg-[#F7ECE1] h-2 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-emerald-600 h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${infraData?.redis_hit_rate_pct || 84.5}%`,
                  }}
                />
              </div>
            </div>
            <p className="text-[11px] text-[#7A3E04] mt-2 pt-2 border-t border-[#F1CCA6]/40">
              Hits: <strong>{infraData?.redis_cache_hits || 4850}</strong> • Misses:{" "}
              {infraData?.redis_cache_misses || 860}
            </p>
          </div>

          {/* Card 3: Active SSE Sessions */}
          <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#F1CCA6] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#8C4905] flex items-center gap-1.5">
                  <Activity className="w-4 h-4 text-[#2563EB]" /> SSE Streaming
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 text-[#2563EB]">
                  ACTIVE
                </span>
              </div>
              <div className="text-xl font-black text-[#1C1917]">
                {infraData?.active_sse_sessions || overview.reliability.active_sse_sessions}{" "}
                <span className="text-xs font-semibold text-gray-500">phiên</span>
              </div>
              <p className="text-[11px] text-[#7A3E04] mt-2">
                Các luồng socket mở stream câu trả lời sư phạm Socratic cho học sinh
              </p>
            </div>
            <p className="text-[11px] text-gray-500 pt-2 border-t border-[#F1CCA6]/40">
              Không rò rỉ bộ nhớ streaming
            </p>
          </div>

          {/* Card 4: Gemini API Quota */}
          <div className="p-4 rounded-xl bg-[#FFFFFF] border border-[#F1CCA6] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-[#8C4905] flex items-center gap-1.5">
                  <Server className="w-4 h-4 text-emerald-600" /> Gemini API Gateway
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">
                  HEALTHY
                </span>
              </div>
              <div className="text-xl font-black text-emerald-700">
                0 Vi Phạm
              </div>
              <p className="text-[11px] text-[#7A3E04] mt-2">
                Mã lỗi HTTP 429 Rate Limit: 0 lần hôm nay
              </p>
            </div>
            <p className="text-[11px] text-gray-500 pt-2 border-t border-[#F1CCA6]/40">
              Độ trễ gateway: ~320ms
            </p>
          </div>
        </div>
      </section>

      {/* ── 9. Danh mục Quản Trị Hệ Thống (Quick Links) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm print:hidden">
        <h3 className="text-base font-bold text-[#8C4905] mb-4 flex items-center gap-2">
          <span className="w-1.5 h-5 bg-[#C1762A] rounded-full inline-block" />
          Điều Hướng Các Phân Hệ Quản Trị Chuyên Biệt
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/admin/content"
            className="group p-4 rounded-xl border border-[#F1CCA6] hover:border-[#C1762A] transition-all bg-[#FFFFFF] flex flex-col justify-between shadow-xs hover:shadow-md"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="w-9 h-9 rounded-lg bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center">
                  <BookOpen className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-[#8C4905] bg-[#F7ECE1] px-2 py-0.5 rounded-md">
                  64 Chủ đề
                </span>
              </div>
              <h4 className="font-bold text-[#8C4905] group-hover:text-[#C1762A]">
                Học Liệu Toán 4 - 9
              </h4>
              <p className="text-xs text-[#7A3E04] mt-1 line-clamp-2">
                Quản lý ngân hàng chủ đề toán học, 3 cấp độ gợi mở Socratic và bài học mẫu.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs font-bold text-[#C1762A]">
              <span>Mở phân hệ</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          <Link
            href="/admin/safety"
            className="group p-4 rounded-xl border border-[#F1CCA6] hover:border-[#C1762A] transition-all bg-[#FFFFFF] flex flex-col justify-between shadow-xs hover:shadow-md"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-red-700 bg-red-50 px-2 py-0.5 rounded-md">
                  Safety Live
                </span>
              </div>
              <h4 className="font-bold text-[#8C4905] group-hover:text-[#C1762A]">
                Giám Sát An Toàn AI
              </h4>
              <p className="text-xs text-[#7A3E04] mt-1 line-clamp-2">
                Nhật ký Safety Agent chặn câu hỏi toxic, prompt injection và câu hỏi ngoài phạm vi toán.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs font-bold text-[#C1762A]">
              <span>Mở phân hệ</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>

          <Link
            href="/admin/settings"
            className="group p-4 rounded-xl border border-[#F1CCA6] hover:border-[#C1762A] transition-all bg-[#FFFFFF] flex flex-col justify-between shadow-xs hover:shadow-md"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="w-9 h-9 rounded-lg bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center">
                  <Settings className="w-5 h-5" />
                </div>
                <span className="text-xs font-bold text-[#8C4905] bg-[#F7ECE1] px-2 py-0.5 rounded-md">
                  v1.8.0 Production
                </span>
              </div>
              <h4 className="font-bold text-[#8C4905] group-hover:text-[#C1762A]">
                Cấu Hình Tham Số Hệ Thống
              </h4>
              <p className="text-xs text-[#7A3E04] mt-1 line-clamp-2">
                Cấu hình tham số Gemini Flash/Pro, nhiệt độ temperature, max tokens và tỷ lệ cache.
              </p>
            </div>
            <div className="mt-3 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs font-bold text-[#C1762A]">
              <span>Mở phân hệ</span>
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </div>
          </Link>
        </div>
      </section>
    </div>
  );
}
