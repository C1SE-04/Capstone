"use client";

/**
 * File: app/dashboard/monitor/page.tsx
 * Mô tả: Trang chính của Dashboard Phụ huynh (MONITOR).
 * - Bộ lọc theo tuần (tuần trước/sau), không cho chọn qua tuần tương lai.
 * - Biểu đồ line chart số giờ học trong tuần.
 * - Thống kê số giờ học (tổng) và số câu hỏi trung bình.
 * - Dữ liệu thật từ API /metrics/study-time
 */

import { useState, useMemo, useEffect, useCallback } from "react";
import { useMonitorContext } from "./layout";
import { useSession } from "next-auth/react";
import { StatCard } from "@/components/monitor/StatCard";
import { UserPlus, ChevronLeft, ChevronRight, Clock, HelpCircle } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  format,
  addWeeks,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  parseISO,
} from "date-fns";
import { vi } from "date-fns/locale";

// Shape dữ liệu trả về từ API
interface DayMetric {
  date: string;       // "2026-10-06"
  minutes: number;
}

interface MetricsResponse {
  mode: string;
  week_start: string;
  week_end: string;
  data: DayMetric[];
  total_minutes: number;
}

// Shape sau khi xử lý cho chart
interface ChartItem {
  date: Date;
  dayName: string;
  shortName: string;
  fullDate: string;
  hours: number;
  minutes: number;
}

export default function MonitorPage() {
  const { selectedStudent } = useMonitorContext();
  const { data: session } = useSession();

  // State quản lý tuần đang xem (0: tuần hiện tại, -1: tuần trước, v.v...)
  const [weekOffset, setWeekOffset] = useState(0);
  const [chartData, setChartData] = useState<ChartItem[]>([]);
  const [totalMinutes, setTotalMinutes] = useState(0);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);

  // Tính toán thời gian của tuần đang chọn
  const { weekStart, weekEnd, isCurrentWeek } = useMemo(() => {
    const today = new Date();
    const targetWeek = addWeeks(today, weekOffset);
    const start = startOfWeek(targetWeek, { weekStartsOn: 1 });
    const end = endOfWeek(targetWeek, { weekStartsOn: 1 });
    const current = weekOffset === 0;
    return { weekStart: start, weekEnd: end, isCurrentWeek: current };
  }, [weekOffset]);

  // Fetch dữ liệu thật từ API
  const fetchMetrics = useCallback(async () => {
    if (!selectedStudent || !session?.access_token) return;

    setIsLoadingMetrics(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const startDateStr = format(weekStart, "yyyy-MM-dd");

      const res = await fetch(
        `${backendUrl}/metrics/study-time?student_id=${selectedStudent.student_id}&mode=weekly&start_date=${startDateStr}`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      if (!res.ok) throw new Error("Fetch metrics failed");

      const json: MetricsResponse = await res.json();

      // Chuyển data API → ChartItem (kèm tên ngày tiếng Việt)
      const days = eachDayOfInterval({ start: weekStart, end: weekEnd });
      const dataMap: Record<string, number> = {};
      json.data.forEach((item) => {
        dataMap[item.date] = item.minutes;
      });

      const processed: ChartItem[] = days.map((day) => {
        const dateStr = format(day, "yyyy-MM-dd");
        const mins = dataMap[dateStr] ?? 0;
        return {
          date: day,
          dayName: format(day, "EEEE", { locale: vi }),
          shortName: format(day, "E", { locale: vi }),
          fullDate: format(day, "dd/MM/yyyy"),
          hours: Math.round((mins / 60) * 10) / 10,
          minutes: mins,
        };
      });

      setChartData(processed);
      setTotalMinutes(json.total_minutes);
    } catch (err) {
      console.error("Lỗi fetch metrics:", err);
      // Fallback: hiển thị mảng rỗng
      const days = eachDayOfInterval({ start: weekStart, end: weekEnd });
      setChartData(
        days.map((day) => ({
          date: day,
          dayName: format(day, "EEEE", { locale: vi }),
          shortName: format(day, "E", { locale: vi }),
          fullDate: format(day, "dd/MM/yyyy"),
          hours: 0,
          minutes: 0,
        }))
      );
      setTotalMinutes(0);
    } finally {
      setIsLoadingMetrics(false);
    }
  }, [selectedStudent, session?.access_token, weekStart, weekEnd]);

  // Trigger fetch khi đổi học sinh hoặc tuần
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  // Tổng hợp số liệu
  const totalHours = (totalMinutes / 60).toFixed(1);

  const avgMinutesPerActiveDay = useMemo(() => {
    const activeDays = chartData.filter((d) => d.minutes > 0);
    if (activeDays.length === 0) return 0;
    return Math.round(totalMinutes / activeDays.length);
  }, [chartData, totalMinutes]);

  const handlePrevWeek = () => setWeekOffset((prev) => prev - 1);
  const handleNextWeek = () => {
    if (!isCurrentWeek) setWeekOffset((prev) => prev + 1);
  };

  // --- RENDERING ---

  if (!selectedStudent) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
        <div className="w-20 h-20 bg-[#F1CCA6] rounded-3xl flex items-center justify-center">
          <UserPlus size={36} className="text-[#C1762A]" />
        </div>
        <h2 className="text-2xl font-extrabold text-[#8C4905]">
          Chưa có học sinh nào
        </h2>
        <p className="text-[#C1762A] max-w-xs leading-relaxed">
          Nhấn <span className="font-bold text-[#8C4905]">&quot;Thêm con&quot;</span> ở
          thanh bên trái để liên kết.
        </p>
      </div>
    );
  }

  const displayName = selectedStudent.nickname || selectedStudent.email.split("@")[0];

  return (
    <div className="max-w-5xl mx-auto animate-in fade-in duration-500 pb-10">
      {/* Header & Filter */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 bg-[#C1762A] rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-md">
              {displayName.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-3xl font-extrabold text-[#8C4905] tracking-tight leading-none">
                {displayName}
              </h1>
              <p className="text-sm text-[#C1762A] mt-1">{selectedStudent.email}</p>
            </div>
          </div>
        </div>

        {/* Weekly Filter Controls */}
        <div className="flex items-center gap-4 bg-white px-4 py-2 rounded-xl border border-[#F1CCA6] shadow-sm">
          <button
            onClick={handlePrevWeek}
            className="p-1.5 rounded-lg text-[#8C4905] hover:bg-[#F7ECE1] transition-colors"
          >
            <ChevronLeft size={20} />
          </button>

          <div className="text-sm font-bold text-[#8C4905] min-w-[140px] text-center">
            {format(weekStart, "dd/MM")} - {format(weekEnd, "dd/MM/yyyy")}
            {isCurrentWeek && <span className="block text-xs text-[#C1762A] font-medium">(Tuần này)</span>}
          </div>

          <button
            onClick={handleNextWeek}
            disabled={isCurrentWeek}
            className={`p-1.5 rounded-lg transition-colors ${
              isCurrentWeek
                ? "text-gray-300 cursor-not-allowed"
                : "text-[#8C4905] hover:bg-[#F7ECE1]"
            }`}
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {/* Thẻ thống kê */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <StatCard
          icon={<Clock size={24} className="text-[#C1762A]" />}
          label="Tổng thời gian học (Tuần)"
          value={isLoadingMetrics ? "..." : `${totalHours} giờ`}
          color="bg-white"
        />
        <StatCard
          icon={<HelpCircle size={24} className="text-[#C1762A]" />}
          label="Thời gian học trung bình/ngày"
          value={isLoadingMetrics ? "..." : `~${avgMinutesPerActiveDay} phút/ngày`}
          color="bg-white"
        />
      </section>

      {/* Biểu đồ */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm">
        <h2 className="text-lg font-bold text-[#8C4905] mb-6 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Biểu đồ thời gian học
          {isLoadingMetrics && (
            <svg className="animate-spin h-4 w-4 text-[#C1762A] ml-2" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
          )}
        </h2>

        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1CCA6" />
              <XAxis
                dataKey="shortName"
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#8C4905', fontWeight: 600, fontSize: 12 }}
                dy={10}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: '#C1762A', fontSize: 12 }}
                tickFormatter={(value) => `${value}h`}
              />
              <Tooltip
                contentStyle={{ borderRadius: '12px', border: '1px solid #F1CCA6', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                labelStyle={{ fontWeight: 'bold', color: '#8C4905', marginBottom: '4px' }}
                formatter={(value) => [`${value ?? 0} giờ`, 'Thời gian học']}
                labelFormatter={(label, payload) => {
                  if (payload && payload.length > 0) {
                    return (payload[0] as { payload: { fullDate: string } }).payload.fullDate;
                  }
                  return label;
                }}
              />
              <Line
                type="monotone"
                dataKey="hours"
                stroke="#C1762A"
                strokeWidth={4}
                dot={{ r: 4, fill: "#8C4905", strokeWidth: 2, stroke: "#fff" }}
                activeDot={{ r: 6, fill: "#C1762A", stroke: "#F7ECE1", strokeWidth: 3 }}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
