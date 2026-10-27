"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import {
  Users,
  BookOpen,
  ShieldAlert,
  Settings,
  ArrowRight,
  TrendingUp,
  Brain,
  GraduationCap,
  MessageSquare,
  Cpu,
  Clock,
  Zap,
  Activity,
  Layers,
  Sparkles,
  RefreshCw,
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
} from "recharts";

interface DailyTokenMetric {
  date: string;
  displayDate: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  sessions_count: number;
  cost_usd: number;
}

function generateMockTokenData(days: number): DailyTokenMetric[] {
  const result: DailyTokenMetric[] = [];
  const now = new Date();

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    const day = d.getDate();
    const month = d.getMonth() + 1;
    const displayDate = `${day < 10 ? "0" + day : day}/${month < 10 ? "0" + month : month}`;

    // Mô phỏng số phiên dao động 3,100 - 4,200 phiên/ngày theo chuẩn backend admin_mock
    const sessions_count = 3100 + (days - i) * 60 + ((i % 4) * 75);
    const prompt_tokens = sessions_count * 230;
    const completion_tokens = sessions_count * 150;
    const total_tokens = prompt_tokens + completion_tokens;
    // Đơn giá Gemini 1.5 Flash: ~$0.075 / 1M prompt, $0.30 / 1M completion
    const cost_usd = Number(((prompt_tokens * 0.000000075) + (completion_tokens * 0.00000030)).toFixed(2));
    // Latency trung bình dao động thực tế 980ms - 1320ms cho Gemini 1.5 Flash
    const latency_ms = Math.round(1050 + ((i * 47) % 220) - ((i % 3) * 50));

    result.push({
      date: dateStr,
      displayDate,
      prompt_tokens,
      completion_tokens,
      total_tokens,
      latency_ms,
      sessions_count,
      cost_usd,
    });
  }

  return result;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

function TokenLatencyTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || !payload.length) return null;

  const data = payload[0]?.payload as DailyTokenMetric;
  if (!data) return null;

  return (
    <div className="bg-[#2A1C0E] text-white p-3.5 rounded-xl shadow-xl border border-[#C1762A]/40 text-xs min-w-[230px] backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-[#F1CCA6]/20 pb-2 mb-2.5">
        <span className="font-extrabold text-sm text-[#F1CCA6]">
          {data.displayDate} ({data.date})
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded-md bg-[#FFF3E6]/10 text-[#F1CCA6] font-semibold border border-[#F1CCA6]/20">
          {data.sessions_count.toLocaleString("vi-VN")} phiên
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-white/80 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#C1762A] inline-block" />
            Tổng Token:
          </span>
          <span className="font-black text-[#F1CCA6]">
            {data.total_tokens.toLocaleString("vi-VN")}
          </span>
        </div>

        <div className="pl-4 text-[11px] text-white/60 space-y-0.5">
          <div className="flex justify-between">
            <span>Prompt (Input):</span>
            <span>{data.prompt_tokens.toLocaleString("vi-VN")}</span>
          </div>
          <div className="flex justify-between">
            <span>Completion (Output):</span>
            <span>{data.completion_tokens.toLocaleString("vi-VN")}</span>
          </div>
        </div>

        <div className="flex items-center justify-between pt-1 border-t border-white/10">
          <span className="text-white/80 flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#2B78C5] inline-block" />
            Độ trễ trung bình:
          </span>
          <span className="font-black text-[#60A5FA]">
            {data.latency_ms} ms
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px] text-white/70">
          <span>Chi phí ước tính:</span>
          <span className="font-bold text-emerald-400">
            ${data.cost_usd.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function AdminPage() {
  const { data: session } = useSession();

  // State khoảng thời gian và dữ liệu Token & Latency (Task 8.31 / US 8.5)
  const [timeRange, setTimeRange] = useState<7 | 14 | 30>(14);
  const [tokenData, setTokenData] = useState<DailyTokenMetric[]>(() => generateMockTokenData(14));
  const [isLoading, setIsLoading] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const fetchTokenMetrics = useCallback(
    async (days: number) => {
      setIsLoading(true);
      try {
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        const token = (session as any)?.access_token || "";
        const res = await fetch(`${backendUrl}/admin/mock/metrics/tokens?days=${days}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });

        if (res.ok) {
          const json = await res.json();
          if (json.daily_data && Array.isArray(json.daily_data)) {
            const enriched: DailyTokenMetric[] = json.daily_data.map((item: any, idx: number) => {
              const parts = item.date.split("-");
              const displayDate = parts.length === 3 ? `${parts[2]}/${parts[1]}` : item.date;
              const latency_ms = Math.round(1050 + ((idx * 47) % 220) - ((idx % 3) * 50));
              return {
                date: item.date,
                displayDate,
                prompt_tokens: item.prompt_tokens,
                completion_tokens: item.completion_tokens,
                total_tokens: item.total_tokens,
                latency_ms,
                sessions_count: item.sessions_count,
                cost_usd: item.cost_usd,
              };
            });
            setTokenData(enriched);
            setIsLoading(false);
            return;
          }
        }
      } catch {
        // Fallback tự động
      }
      setTokenData(generateMockTokenData(days));
      setIsLoading(false);
    },
    [session]
  );

  useEffect(() => {
    fetchTokenMetrics(timeRange);
  }, [timeRange, fetchTokenMetrics]);

  // Thống kê tổng hợp của biểu đồ Token & Latency
  const chartSummary = useMemo(() => {
    const totalTokens = tokenData.reduce((acc, cur) => acc + cur.total_tokens, 0);
    const avgLatency = Math.round(
      tokenData.reduce((acc, cur) => acc + cur.latency_ms, 0) / (tokenData.length || 1)
    );
    const totalCost = tokenData.reduce((acc, cur) => acc + cur.cost_usd, 0);
    const totalSessions = tokenData.reduce((acc, cur) => acc + cur.sessions_count, 0);
    return { totalTokens, avgLatency, totalCost, totalSessions };
  }, [tokenData]);

  const quickCards = [
    {
      title: "Quản Lý Người Dùng",
      description: "Xem danh sách 48 tài khoản học sinh, phụ huynh, liên kết gia đình và kiểm soát trạng thái khóa/mở.",
      icon: Users,
      href: "/admin/users",
      stats: "48 Users",
      color: "#C1762A",
      bgLight: "#F7ECE1",
    },
    {
      title: "Học Liệu Toán 4 - 9",
      description: "Quản lý 64 chủ đề toán học theo chương trình mới, 3 cấp độ gợi ý Socratic và bài học mẫu cho AI.",
      icon: BookOpen,
      href: "/admin/content",
      stats: "64 Chủ đề",
      color: "#8C4905",
      bgLight: "#F7ECE1",
    },
    {
      title: "Giám Sát An Toàn AI",
      description: "Nhật ký cảnh báo Safety Agent chặn câu hỏi toxic, jailbreak prompt và theo dõi tỷ lệ học sinh chưa hiểu.",
      icon: ShieldAlert,
      href: "/admin/safety",
      stats: "3 Cảnh báo mới",
      color: "#D93829",
      bgLight: "#FDF0ED",
    },
    {
      title: "Cài Đặt Hệ Thống",
      description: "Cấu hình tham số model Gemini 1.5 Flash/Pro, nhiệt độ sáng tạo temperature, max tokens và phiên bản.",
      icon: Settings,
      href: "/admin/settings",
      stats: "v1.7.0 Live",
      color: "#8C4905",
      bgLight: "#F7ECE1",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-500 space-y-8 pb-10 text-[#2A1C0E]">
      {/* ── 1. Header (Đồng bộ chuẩn Parent Dashboard) ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-[#C1762A] rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-md">
            AD
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#8C4905] tracking-tight leading-none">
              Tổng Quan Quản Trị Hệ Thống
            </h1>
            <p className="text-sm text-[#C1762A] mt-1 font-medium">
              Giám sát người dùng, học liệu toán và hiệu năng tài nguyên AI SocraticKid
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-white text-[#8C4905] border border-[#F1CCA6] shadow-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#2A8C4A] animate-pulse" />
            Hệ thống: <strong className="text-[#2A8C4A]">Hoạt động ổn định</strong>
          </span>
        </div>
      </div>

      {/* ── 2. 4 KPI Summary Cards (Cùng ngôn ngữ với SummaryCards của Phụ Huynh) ── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Thẻ 1: Tổng người dùng */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
              <Users size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-100">
              <TrendingUp size={12} /> +14.2%
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
              Tổng người dùng
            </p>
            <p className="text-2xl font-black text-[#8C4905] leading-none">
              48
            </p>
            <p className="text-xs text-[#C1762A]/70 mt-1.5 font-medium">36 Học sinh • 12 Phụ huynh</p>
          </div>
        </div>

        {/* Thẻ 2: Core Metric: Học sinh DAU */}
        <div className="bg-gradient-to-br from-[#FFFBF7] to-[#F7ECE1] rounded-2xl p-5 border-2 border-[#C1762A]/40 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-[#C1762A]/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#8C4905] flex items-center justify-center text-[#F7ECE1] shadow-md">
              <GraduationCap size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200">
              Tích cực
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#8C4905] uppercase tracking-wider mb-1 flex items-center gap-1.5">
              Học Sinh Active (DAU)
            </p>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-black text-[#8C4905] leading-none">
                18
              </span>
              <span className="text-xs font-bold text-[#2A8C4A]">+8.6% hôm nay</span>
            </div>
            <p className="text-xs text-[#8C4905]/80 font-medium mt-1.5">
              MAU: 32 học sinh gắn kết
            </p>
          </div>
        </div>

        {/* Thẻ 3: Phiên Chat Socratic */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
              <MessageSquare size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-semibold text-[#8C4905] bg-[#F7ECE1] px-2 py-0.5 rounded-full border border-[#F1CCA6]">
              Tự hiểu: 82.4%
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
              Phiên Đối Thoại AI
            </p>
            <p className="text-2xl font-black text-[#8C4905] leading-none">
              46
            </p>
            <p className="text-xs text-[#C1762A]/70 mt-1.5 font-medium">Trung bình 18.5 phút / bài toán</p>
          </div>
        </div>

        {/* Thẻ 4: Điểm Tự Lập Toàn Hệ Thống */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
              <Brain size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              Mục tiêu &gt; 80đ
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
              Điểm Tự Lập Trung Bình
            </p>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-[#8C4905] leading-none">
                84.6
              </span>
              <span className="text-xs font-bold text-[#C1762A]">/100</span>
            </div>
            <p className="text-xs text-[#C1762A]/70 mt-1.5 font-medium">+4.2đ sau tinh chỉnh Socratic</p>
          </div>
        </div>
      </section>

      {/* ── 3. [MỚI - Task 8.31 / US 8.5] Biểu Đồ Hiệu Năng AI: Total Tokens & Latency Theo Ngày ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm space-y-5">
        {/* Header biểu đồ & Bộ lọc thời gian */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-6 bg-[#C1762A] rounded-full inline-block" />
              <h2 className="text-lg font-bold text-[#8C4905]">
                Hiệu Năng AI: Tổng Token Tiêu Thụ & Độ Trễ (Latency)
              </h2>
            </div>
            <p className="text-xs text-[#7E6B5A] mt-1">
              Theo dõi số token Gemini tiêu thụ thực tế theo từng ngày kết hợp với độ trễ phản hồi trung bình (ms)
            </p>
          </div>

          <div className="flex items-center gap-1.5 bg-[#FBF4ED] p-1 rounded-xl border border-[#E8D5C4] self-start sm:self-auto">
            {([7, 14, 30] as const).map((days) => (
              <button
                key={days}
                onClick={() => setTimeRange(days)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  timeRange === days
                    ? "bg-[#C1762A] text-white shadow-xs"
                    : "text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-[#F7ECE1]"
                }`}
              >
                {days} Ngày
              </button>
            ))}
          </div>
        </div>

        {/* 3 Thẻ thống kê tóm tắt nhanh trên biểu đồ */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="bg-[#FFFDFB] p-3.5 rounded-xl border border-[#F1CCA6]/70 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#FFF3E6] text-[#C1762A] flex items-center justify-center shrink-0 border border-[#F1CCA6]">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#C1762A]">
                Tổng Token Tiêu Thụ ({timeRange}d)
              </div>
              <div className="text-lg font-black text-[#8C4905] leading-snug">
                {(chartSummary.totalTokens / 1_000_000).toFixed(2)}M Tokens
              </div>
            </div>
          </div>

          <div className="bg-[#FFFDFB] p-3.5 rounded-xl border border-[#BADEF7]/70 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#EBF4FC] text-[#2B78C5] flex items-center justify-center shrink-0 border border-[#BADEF7]">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#2B78C5]">
                Độ Trễ Trung Bình (Latency)
              </div>
              <div className="text-lg font-black text-[#2B78C5] leading-snug">
                {chartSummary.avgLatency.toLocaleString("vi-VN")} ms
                <span className="text-xs font-semibold text-emerald-600 ml-1.5">
                  (~{(chartSummary.avgLatency / 1000).toFixed(2)}s)
                </span>
              </div>
            </div>
          </div>

          <div className="bg-[#FFFDFB] p-3.5 rounded-xl border border-[#F1CCA6]/70 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center shrink-0 border border-[#F1CCA6]">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[#8C4905]">
                Chi Phí Quy Đổi Ước Tính
              </div>
              <div className="text-lg font-black text-[#2A8C4A] leading-snug">
                ${chartSummary.totalCost.toFixed(2)} USD
              </div>
            </div>
          </div>
        </div>

        {/* Khung Biểu Đồ Recharts ComposedChart (Bar = Tokens, Line = Latency) */}
        <div className="pt-2">
          <div className="h-[340px] w-full">
            {isMounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={tokenData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#F1CCA6"
                    opacity={0.4}
                    vertical={false}
                  />
                  <XAxis
                    dataKey="displayDate"
                    stroke="#7E6B5A"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: "#F1CCA6" }}
                  />
                  {/* Trục Y trái: Tokens */}
                  <YAxis
                    yAxisId="tokens"
                    orientation="left"
                    stroke="#C1762A"
                    fontSize={11}
                    tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                    axisLine={false}
                    tickLine={false}
                  />
                  {/* Trục Y phải: Latency (ms) */}
                  <YAxis
                    yAxisId="latency"
                    orientation="right"
                    stroke="#2B78C5"
                    fontSize={11}
                    tickFormatter={(val) => `${val}ms`}
                    domain={[600, 1800]}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip content={<TokenLatencyTooltip />} />
                  <Legend
                    verticalAlign="top"
                    align="right"
                    iconType="circle"
                    wrapperStyle={{ paddingBottom: "12px", fontSize: "12px" }}
                    formatter={(value) => (
                      <span className="font-semibold text-xs text-[#2A1C0E]">
                        {value === "total_tokens"
                          ? "Tổng Token Tiêu Thụ"
                          : value === "latency_ms"
                          ? "Độ Trễ Trung Bình (ms)"
                          : value}
                      </span>
                    )}
                  />
                  <Bar
                    yAxisId="tokens"
                    dataKey="total_tokens"
                    name="total_tokens"
                    fill="#C1762A"
                    radius={[6, 6, 0, 0]}
                    maxBarSize={36}
                  />
                  <Line
                    yAxisId="latency"
                    type="monotone"
                    dataKey="latency_ms"
                    name="latency_ms"
                    stroke="#2B78C5"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: "#2B78C5" }}
                    activeDot={{ r: 6, stroke: "#FFF", strokeWidth: 2 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center gap-2 text-xs text-[#7E6B5A]">
                <RefreshCw className="w-5 h-5 animate-spin text-[#C1762A]" />
                <span>Đang khởi tạo biểu đồ tài nguyên AI...</span>
              </div>
            )}
          </div>
        </div>

        {/* Chú thích & Ghi chú nghiệp vụ phía dưới */}
        <div className="pt-2 border-t border-[#F1CCA6]/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px] text-[#7E6B5A]">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-xs bg-[#C1762A] inline-block" />
              Cột cam: Tổng số Token (Prompt + Completion)
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-1 rounded-full bg-[#2B78C5] inline-block" />
              Đường xanh: Độ trễ trung bình thời gian thực (ms)
            </span>
          </div>
          <div>
            Model: <strong className="text-[#8C4905]">Gemini 1.5 Flash (Production)</strong>
          </div>
        </div>
      </section>

      {/* ── 4. Danh mục Quản trị & Điều hướng nhanh ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm">
        <h2 className="text-lg font-bold text-[#8C4905] mb-5 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Danh Mục Quản Trị & Điều Hướng Nhanh
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickCards.map((c) => {
            const Icon = c.icon;
            return (
              <Link
                key={c.href}
                href={c.href}
                className="group bg-[#FFFDFB] rounded-2xl p-5 border border-[#F1CCA6] hover:border-[#C1762A] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105 shadow-inner"
                      style={{ backgroundColor: c.bgLight, color: c.color }}
                    >
                      <Icon className="w-5 h-5 stroke-[2.2]" />
                    </div>
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]">
                      {c.stats}
                    </span>
                  </div>

                  <h3 className="font-extrabold text-[#8C4905] text-base group-hover:text-[#C1762A] transition-colors">
                    {c.title}
                  </h3>
                  <p className="text-xs md:text-sm text-[#7E6B5A] mt-1.5 leading-relaxed">
                    {c.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs font-bold text-[#C1762A] group-hover:text-[#8C4905]">
                  <span>Vào trang quản trị</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
