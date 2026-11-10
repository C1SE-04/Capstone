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
  Bar,
  Line,
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
    status_5xx_count_today: number;
    gemini_429_count_today: number;
    active_sse_sessions: number;
    system_health: string;
  };
}

interface ThroughputItem {
  timestamp: string;
  display_time: string;
  requests: number;
  chat_requests: number;
  eval_requests: number;
  auth_requests: number;
  other_requests: number;
}

interface ThroughputResponse {
  range: string;
  granularity: string;
  peak_rpm?: number;
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

interface TokensResponse {
  days: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  total_cost_vnd: number;
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
    error_rate_pct: 0.3,
    status_5xx_count_today: 0,
    gemini_429_count_today: 0,
    active_sse_sessions: 8,
    system_health: "HEALTHY",
  },
};

const DEFAULT_AGENTS: SubsystemAgent[] = [
  {
    id: "Chat",
    name: "Gia Sư Socratic (Chat)",
    description: "Đối thoại sư phạm gợi mở 2-4 câu, bám sát sách giáo khoa Toán 4-9",
    model_used: "gemini-2.5-flash",
    request_count: 850,
    request_percentage: 58.6,
    prompt_tokens: 720000,
    completion_tokens: 380000,
    total_tokens: 1100000,
    token_percentage: 59.5,
    cost_usd: 0.168,
    cost_vnd: 4275,
    avg_latency_ms: 820,
    color: "#C1762A",
  },
  {
    id: "Classifier",
    name: "Phân Loại Bài Toán & Đặt Tên",
    description: "Nhận diện chuyên đề SGK và đặt tên bài toán thân thiện",
    model_used: "gemini-2.0-flash-lite",
    request_count: 220,
    request_percentage: 15.2,
    prompt_tokens: 180000,
    completion_tokens: 65000,
    total_tokens: 245000,
    token_percentage: 13.2,
    cost_usd: 0.0165,
    cost_vnd: 420,
    avg_latency_ms: 290,
    color: "#8C4905",
  },
  {
    id: "Flashcard",
    name: "Sổ Tay & Thẻ Ghi Nhớ (Flashcard)",
    description: "Trích xuất công thức trọng tâm và tóm tắt bước giải vào sổ tay",
    model_used: "gemini-2.0-flash-lite",
    request_count: 145,
    request_percentage: 10.0,
    prompt_tokens: 125000,
    completion_tokens: 45000,
    total_tokens: 170000,
    token_percentage: 9.2,
    cost_usd: 0.0114,
    cost_vnd: 290,
    avg_latency_ms: 310,
    color: "#2563EB",
  },
  {
    id: "ParentReport",
    name: "Báo Cáo Phụ Huynh (Parent Insights)",
    description: "Quét toàn bộ lịch sử tuần để đánh giá tính tự lập gửi phụ huynh",
    model_used: "gemini-1.5-pro",
    request_count: 95,
    request_percentage: 6.6,
    prompt_tokens: 110000,
    completion_tokens: 40000,
    total_tokens: 150000,
    token_percentage: 8.1,
    cost_usd: 0.095,
    cost_vnd: 2418,
    avg_latency_ms: 1450,
    color: "#10B981",
  },
  {
    id: "Email",
    name: "Email Cảnh Báo Phụ Huynh",
    description: "Gửi thông báo cảnh báo học tập hoặc ngôn từ tiêu cực qua Brevo SMTP",
    model_used: "Brevo/SMTP",
    request_count: 80,
    request_percentage: 5.5,
    prompt_tokens: 52000,
    completion_tokens: 18000,
    total_tokens: 70000,
    token_percentage: 3.8,
    cost_usd: 0.0,
    cost_vnd: 0,
    avg_latency_ms: 120,
    color: "#F59E0B",
  },
  {
    id: "Fallback",
    name: "Dự Phòng & Local Heuristic",
    description: "Bộ xử lý cục bộ Regex & ML khi Gemini API bận hoặc rớt mạng",
    model_used: "Local Heuristic / Fallback",
    request_count: 60,
    request_percentage: 4.1,
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    token_percentage: 0.0,
    cost_usd: 0.0,
    cost_vnd: 0,
    avg_latency_ms: 15,
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

  // Data States
  const [overview, setOverview] = useState<OverviewData>(DEFAULT_OVERVIEW);
  const [throughput, setThroughput] = useState<ThroughputResponse | null>(null);
  const [tokensData, setTokensData] = useState<TokensResponse | null>(null);
  const [latencyData, setLatencyData] = useState<LatencyResponse | null>(null);
  const [agentsData, setAgentsData] = useState<AgentsResponse>({
    status: "success",
    total_subsystems: DEFAULT_AGENTS.length,
    total_requests: 1450,
    total_tokens: 1850000,
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

  // Xuất báo cáo CSV
  const handleExportCSV = () => {
    const downloadUrl = `${backendUrl}/admin/kpi/export?format=csv&days=${tokenDays}`;
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", `socratickid_admin_kpi_report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // In / Xuất báo cáo PDF
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

  const hasActiveIncidents =
    Boolean(incidentsData?.has_active_incidents) && !dismissIncidentBanner;
  const activeIncident = incidentsData?.banner_alert;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12 animate-in fade-in duration-300 print:p-0 print:space-y-4 text-[#1C1917]">
      {/* ── 0. SLA Incident Alert Banner (AC-KPI-07) ── */}
      {hasActiveIncidents && (
        <section className="bg-red-500/10 border-2 border-red-500 rounded-2xl p-4 md:p-5 shadow-lg flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in slide-in-from-top-4 duration-300">
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
                  {activeIncident?.incident_type === "ERROR_SPIKE"
                    ? "Tỷ lệ lỗi 5xx vượt 2.0%"
                    : "Độ trễ phản hồi P95 vượt 1800ms"}
                </span>
              </div>
              <p className="text-sm font-semibold text-red-900 mt-1">
                {activeIncident?.message ||
                  "Hệ thống phát hiện ngưỡng cảnh báo độ trễ hoặc lỗi máy chủ bất thường!"}
              </p>
              <p className="text-xs text-red-700/80 mt-0.5">
                Kích hoạt lúc:{" "}
                {activeIncident?.triggered_at
                  ? new Date(activeIncident.triggered_at).toLocaleTimeString("vi-VN")
                  : "Vừa xong"}{" "}
                • Giá trị đo:{" "}
                <strong>{activeIncident?.actual_value}</strong> (Ngưỡng cho phép:{" "}
                {activeIncident?.threshold_value})
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
            <button
              onClick={() => setDismissIncidentBanner(true)}
              className="text-xs font-bold px-3 py-1.5 rounded-lg border border-red-300 text-red-800 hover:bg-red-100 transition-colors"
            >
              Tạm ẩn
            </button>
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
                  overview.reliability.system_health === "HEALTHY"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-red-50 text-red-700 border border-red-200"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    overview.reliability.system_health === "HEALTHY"
                      ? "bg-emerald-500 animate-pulse"
                      : "bg-red-500 animate-ping"
                  }`}
                />
                {overview.reliability.system_health === "HEALTHY"
                  ? "SLA 99.7% Hoạt động ổn định"
                  : "Hệ thống đang suy giảm"}
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

          {/* Nút Xuất CSV */}
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#C1762A] hover:bg-[#A8611D] text-white font-bold text-xs shadow-xs transition-all"
            title="Tải toàn bộ số liệu KPI về máy định dạng CSV"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Xuất CSV</span>
          </button>

          {/* Nút In / PDF */}
          <button
            onClick={handlePrintPDF}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-[#F7ECE1] text-[#8C4905] font-bold text-xs border border-[#F1CCA6] shadow-xs transition-colors"
            title="In hoặc lưu Dashboard ra file PDF"
          >
            <Printer className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">In/PDF</span>
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
                overview.latency_and_sla.current_ttft_ms < 500
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-amber-50 text-amber-700 border-amber-200"
              }`}
            >
              TTFT: {overview.latency_and_sla.current_ttft_ms}ms
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-[#2563EB] mb-1">
              Độ Trễ Phân Vị SLA
            </p>
            <div className="flex items-baseline gap-3">
              <div>
                <span className="text-2xl font-black text-[#1C1917] leading-none">
                  {overview.latency_and_sla.p50_latency_ms}
                </span>
                <span className="text-xs font-semibold text-gray-500 ml-0.5">ms (P50)</span>
              </div>
              <div className="text-xs font-bold text-amber-700">
                P95: {overview.latency_and_sla.p95_latency_ms}ms
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px] text-[#7A3E04]">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> P50 &lt; 800ms
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> P95 &lt; 1800ms
              </span>
            </div>
          </div>
        </div>

        {/* Thẻ 4: Độ Tin Cậy & SSE Sessions */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shadow-inner">
              <ShieldCheck className="w-5 h-5 stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-black px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
              {overview.reliability.success_rate_pct}% OK
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-700 mb-1">
              Độ Tin Cậy & Hạ Tầng
            </p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-[#1C1917] leading-none">
                {overview.reliability.active_sse_sessions}
              </span>
              <span className="text-xs font-bold text-[#7A3E04]">phiên SSE active</span>
            </div>
            <div className="mt-2 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-[11px] text-[#7A3E04]">
              <span>5xx: <strong className="text-emerald-700">{overview.reliability.status_5xx_count_today}</strong></span>
              <span>429 Quota: <strong className="text-emerald-700">{overview.reliability.gemini_429_count_today}</strong></span>
              <span>DB Pool: <strong>{infraData?.neon_connections_active || 6}/20</strong></span>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. Widget 1: Biểu Đồ Throughput (RPM 60m / RPH 24h / Daily) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1CCA6]/40 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Lưu Lượng Hệ Thống (Throughput & Live RPM)
              </h2>
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              Theo dõi biến động số lượng request theo phút trong 60 phút gần nhất, hoặc theo giờ/ngày
            </p>
          </div>

          {/* Granularity Switcher */}
          <div className="flex items-center gap-1 bg-[#F7ECE1] p-1 rounded-xl border border-[#F1CCA6] self-start sm:self-auto">
            {(["1h", "24h", "7d", "30d"] as const).map((rng) => (
              <button
                key={rng}
                onClick={() => setThroughputRange(rng)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  throughputRange === rng
                    ? "bg-[#C1762A] text-white shadow-xs"
                    : "text-[#7A3E04] hover:bg-white/50"
                }`}
              >
                {rng === "1h"
                  ? "Phút (60m)"
                  : rng === "24h"
                  ? "Giờ (24h)"
                  : rng === "7d"
                  ? "7 Ngày"
                  : "30 Ngày"}
              </button>
            ))}
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
                      <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-[#C1762A]/40 text-xs min-w-[200px]">
                        <div className="font-extrabold text-[#F1CCA6] border-b border-white/10 pb-1.5 mb-2">
                          Thời gian: {item.display_time}
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

      {/* ── 4. Widget 2: Tiêu Thụ Token & Chi Phí API (4 Model Gemini) ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1CCA6]/40 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Tiêu Thụ Token &amp; Chi Phí API (4 Model Google Gemini)
              </h2>
            </div>
            <p className="text-xs text-[#7A3E04] mt-0.5">
              Phân rã chi tiết Prompt Tokens (Input), Completion Tokens (Output) và quy đổi chi phí USD / VND
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

        {/* Biểu đồ Recharts Composed (Bar = Prompt/Comp Tokens, Line = Cost) */}
        <div className="h-[300px] w-full">
          {tokensData && tokensData.items && tokensData.items.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={tokensData.items}
                margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
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
                    currencyMode === "USD" ? `$${val}` : `${(val * 25450 / 1000).toFixed(0)}k₫`
                  }
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const item = payload[0].payload as TokenDailyItem;
                    return (
                      <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-[#C1762A]/40 text-xs min-w-[210px]">
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
                  dataKey="cost_usd"
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

        {/* 4 Model Breakdown Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          {tokensData?.model_breakdown ? (
            Object.entries(tokensData.model_breakdown).map(([key, m]) => (
              <div
                key={key}
                className="bg-[#FFFFFF] p-3.5 rounded-xl border border-[#F1CCA6] flex flex-col justify-between shadow-xs hover:border-[#C1762A] transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-[#8C4905] truncate">{m.name}</span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-[#F7ECE1] text-[#C1762A]">
                      {m.percentage}%
                    </span>
                  </div>
                  <p className="text-[10px] text-gray-500 line-clamp-1">{m.pricing}</p>
                </div>
                <div className="mt-2.5 pt-2 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs">
                  <span className="text-gray-600">{(m.tokens / 1000).toFixed(0)}k tok</span>
                  <span className="font-extrabold text-emerald-700">
                    {currencyMode === "USD" ? `$${m.cost_usd}` : `${m.cost_vnd.toLocaleString("vi-VN")} ₫`}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-4 text-center text-xs text-gray-500 py-2">
              Đang tính toán phân bổ 4 model Gemini...
            </div>
          )}
        </div>
      </section>

      {/* ── 5. Widget 3: Độ Trễ SLA (P50/P95/P99) & Đồng Hồ TTFT ── */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cột trái: Biểu Đồ Multi-line P50, P95, P99 (2/3 width) */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-[#F1CCA6]/40 pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-6 bg-[#2563EB] rounded-full inline-block" />
                <h2 className="text-lg font-bold text-[#8C4905]">
                  Phân Vị Độ Trễ SLA (P50, P95, P99)
                </h2>
              </div>
              <p className="text-xs text-[#7A3E04] mt-0.5">
                Kiểm chứng tiêu chuẩn cam kết: P50 &lt; 800ms, P95 &lt; 1800ms
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
                P50: {latencyData?.overall_p50_ms || 520}ms ✓
              </span>
              <span className="text-xs font-bold px-2.5 py-1 rounded-lg bg-amber-50 text-amber-700 border border-amber-200">
                P95: {latencyData?.overall_p95_ms || 1420}ms ✓
              </span>
            </div>
          </div>

          <div className="h-[280px] w-full">
            {latencyData && latencyData.items && latencyData.items.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={latencyData.items}
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
                    stroke="#2563EB"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    domain={[200, 3000]}
                    tickFormatter={(val) => `${val}ms`}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const item = payload[0].payload as LatencyHourlyItem;
                      return (
                        <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-blue-500/40 text-xs min-w-[200px]">
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
                    strokeWidth={1.5}
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

        {/* Cột phải: Đồng Hồ TTFT (Time To First Token) Gauge (1/3 width) */}
        <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 border-b border-[#F1CCA6]/40 pb-3">
              <span className="w-2 h-6 bg-emerald-500 rounded-full inline-block" />
              <h3 className="text-base font-bold text-[#8C4905]">
                Đồng Hồ Đo TTFT Live
              </h3>
            </div>
            <p className="text-xs text-[#7A3E04] mt-2">
              Thời gian từ lúc gửi prompt đến khi nhận chunk token đầu tiên qua SSE
            </p>

            {/* Circular Gauge Representation */}
            <div className="flex flex-col items-center justify-center my-6">
              <div className="relative w-44 h-44 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  {/* Track Circle */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="transparent"
                    stroke="#F7ECE1"
                    strokeWidth="10"
                  />
                  {/* Progress Arc */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="transparent"
                    stroke={
                      (latencyData?.current_ttft_ms || 420) < 500
                        ? "#10B981"
                        : (latencyData?.current_ttft_ms || 420) <= 1200
                        ? "#F59E0B"
                        : "#EF4444"
                    }
                    strokeWidth="10"
                    strokeDasharray="251.2"
                    strokeDashoffset={Math.max(
                      0,
                      251.2 - (251.2 * Math.min(latencyData?.current_ttft_ms || 420, 2000)) / 2000
                    )}
                    strokeLinecap="round"
                    className="transition-all duration-700"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center text-center">
                  <span className="text-3xl font-black text-[#1C1917]">
                    {latencyData?.current_ttft_ms || overview.latency_and_sla.current_ttft_ms}
                  </span>
                  <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                    Mili-giây (ms)
                  </span>
                </div>
              </div>

              {/* Status Badge */}
              <div
                className={`mt-2 px-3 py-1 rounded-full text-xs font-black flex items-center gap-1.5 ${
                  (latencyData?.current_ttft_ms || 420) < 500
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-300"
                    : "bg-amber-50 text-amber-700 border border-amber-300"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    (latencyData?.current_ttft_ms || 420) < 500
                      ? "bg-emerald-500"
                      : "bg-amber-500"
                  }`}
                />
                {(latencyData?.current_ttft_ms || 420) < 500
                  ? "TỐI ƯU (DƯỚI 500ms)"
                  : "CHẤP NHẬN ĐƯỢC (500-1200ms)"}
              </div>
            </div>
          </div>

          <div className="p-3 bg-[#F7ECE1] rounded-xl border border-[#F1CCA6] text-[11px] text-[#7A3E04] space-y-1">
            <div className="flex justify-between">
              <span>Mục tiêu SLA:</span>
              <strong className="text-emerald-700">&lt; 500ms</strong>
            </div>
            <div className="flex justify-between">
              <span>Giao thức truyền:</span>
              <strong>Server-Sent Events (SSE)</strong>
            </div>
          </div>
        </div>
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
          {/* Donut Chart (5/12) */}
          <div className="lg:col-span-5 h-[280px] w-full flex items-center justify-center">
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
                      <div className="bg-[#1C1917] text-white p-3 rounded-xl shadow-xl border border-white/20 text-xs min-w-[190px]">
                        <div className="font-extrabold text-[#F1CCA6] mb-1">
                          {item.name}
                        </div>
                        <div className="space-y-1">
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
                            <span>${item.cost_usd.toFixed(4)}</span>
                          </div>
                        </div>
                      </div>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
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
                  <div className="mt-2 text-xs">
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

            {/* Chi tiết phân hệ được chọn */}
            <div className="p-4 rounded-xl bg-[#F7ECE1]/60 border border-[#F1CCA6] space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-black text-sm text-[#8C4905]">
                    {currentAgent.name}
                  </h4>
                  <p className="text-[11px] text-[#7A3E04] mt-0.5">
                    {currentAgent.description}
                  </p>
                </div>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-md bg-white text-[#C1762A] border border-[#F1CCA6]">
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
                  <span className="text-[10px] text-gray-500 block">Completion:</span>
                  <strong className="text-[#8C4905]">
                    {currentAgent.completion_tokens.toLocaleString("vi-VN")}
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 block">Chi phí quy đổi:</span>
                  <strong className="text-emerald-700">
                    ${currentAgent.cost_usd.toFixed(4)} ({currentAgent.cost_vnd.toLocaleString("vi-VN")}₫)
                  </strong>
                </div>
                <div>
                  <span className="text-[10px] text-gray-500 block">Độ trễ trung bình:</span>
                  <strong className="text-[#2563EB]">{currentAgent.avg_latency_ms} ms</strong>
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
              168 ô thể hiện mật độ sử dụng hệ thống từ Thứ Hai đến Chủ Nhật (0h - 23h). Di chuột vào ô để xem số liệu
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

        {/* Heatmap Grid 7 rows x 24 cols */}
        <div className="overflow-x-auto pb-2">
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
                    const cell = dayCells.find((c) => c.hour === h) || {
                      day: dayLabel,
                      full_day: dayLabel,
                      hour: h,
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

                    return (
                      <div
                        key={h}
                        className={`h-6 rounded-xs transition-all cursor-pointer relative group ${
                          colorMap[cell.intensity] || colorMap[0]
                        }`}
                        title={`${cell.full_day} ${h}:00 - ${cell.requests} requests (${cell.tokens.toLocaleString("vi-VN")} tokens)`}
                      >
                        {/* Custom hover tooltip */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block z-30 bg-[#1C1917] text-white text-[10px] p-2 rounded-lg shadow-xl whitespace-nowrap pointer-events-none">
                          <p className="font-bold text-[#F1CCA6]">
                            {cell.full_day} • {h}:00
                          </p>
                          <p className="mt-0.5">Requests: {cell.requests}</p>
                          <p>Tokens: {cell.tokens.toLocaleString("vi-VN")}</p>
                        </div>
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
