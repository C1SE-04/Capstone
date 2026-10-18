"use client";

/**
 * File: components/monitor/IndependenceChart.tsx
 * Task: T6.9 [Thiên] [FE] — Tích hợp Line chart điểm Independence trên Parent Dashboard
 * Mô tả:
 *  - Nhận mảng lịch sử điểm Independence từ API /independence/summary
 *  - Vẽ Line chart (Recharts) hiển thị xu hướng điểm tự lực theo thời gian
 *  - Hiện đường tham chiếu trung bình, tooltip chi tiết và empty state
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { format, parseISO } from "date-fns";
import { vi } from "date-fns/locale";
import { Brain } from "lucide-react";

// --- Types ---

export interface IndependencePoint {
  /** ISO datetime string (created_at từ API) */
  date: string;
  score: number;
  evaluation: string;
}

interface IndependenceChartProps {
  data: IndependencePoint[];
  isLoading?: boolean;
}

// --- Custom Tooltip ---

interface TooltipPayloadItem {
  payload: {
    fullDate: string;
    score: number;
    evaluation: string;
  };
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const { fullDate, score, evaluation } = payload[0].payload;
  const color =
    score >= 80
      ? "text-emerald-600"
      : score >= 60
      ? "text-amber-600"
      : score >= 40
      ? "text-orange-600"
      : "text-red-500";

  return (
    <div className="bg-white rounded-xl border border-[#F1CCA6] shadow-md p-3 text-sm min-w-[170px]">
      <p className="text-xs font-semibold text-[#C1762A] mb-1">{fullDate}</p>
      <div className="flex items-baseline gap-1">
        <span className={`text-2xl font-black ${color}`}>{score}</span>
        <span className="text-xs text-[#8C4905] font-bold">/100</span>
      </div>
      <p className="text-xs text-[#8C4905]/80 mt-0.5 font-medium">{evaluation}</p>
    </div>
  );
}

// --- Main Component ---

export function IndependenceChart({
  data,
  isLoading = false,
}: IndependenceChartProps) {
  // Sắp xếp tăng dần theo ngày, chuẩn hóa nhãn
  const chartData = [...data]
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
    .map((item) => ({
      ...item,
      label: format(parseISO(item.date), "dd/MM", { locale: vi }),
      fullDate: format(parseISO(item.date), "EEEE, dd/MM/yyyy HH:mm", {
        locale: vi,
      }),
    }));

  const avgScore =
    chartData.length > 0
      ? Math.round(
          chartData.reduce((sum, d) => sum + d.score, 0) / chartData.length
        )
      : 0;

  const getAvgBadge = (avg: number) => {
    if (avg >= 80)
      return {
        label: "Tự lập xuất sắc",
        cls: "bg-emerald-50 text-emerald-700 border-emerald-200",
      };
    if (avg >= 60)
      return {
        label: "Tự lập tốt",
        cls: "bg-amber-50 text-amber-700 border-amber-200",
      };
    if (avg >= 40)
      return {
        label: "Tự lập đang tiến bộ",
        cls: "bg-orange-50 text-orange-700 border-orange-200",
      };
    return {
      label: "Cần tiến bộ",
      cls: "bg-red-50 text-red-600 border-red-200",
    };
  };

  const badge = getAvgBadge(avgScore);

  return (
    <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mt-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#8C4905] rounded-full inline-block" />
          <Brain size={18} className="text-[#C1762A]" />
          Điểm Tự Lực theo thời gian
        </h2>

        {!isLoading && chartData.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#8C4905] bg-[#F7ECE1] px-3 py-1 rounded-full border border-[#F1CCA6]">
              TB {avgScore}/100
            </span>
            <span
              className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${badge.cls}`}
            >
              {badge.label}
            </span>
          </div>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="h-[300px] flex items-center justify-center text-[#C1762A]">
          <svg
            className="animate-spin h-6 w-6"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && chartData.length === 0 && (
        <div className="h-[300px] flex flex-col items-center justify-center gap-3 text-[#C1762A]">
          <div className="w-16 h-16 rounded-2xl bg-[#F7ECE1] flex items-center justify-center">
            <Brain size={32} className="opacity-40" />
          </div>
          <p className="text-sm font-semibold text-[#8C4905]">
            Chưa có dữ liệu điểm tự lực
          </p>
          <p className="text-xs text-[#C1762A]/70 text-center max-w-[200px]">
            Điểm sẽ xuất hiện sau khi học sinh hoàn thành bài toán đầu tiên
          </p>
        </div>
      )}

      {/* Chart */}
      {!isLoading && chartData.length > 0 && (
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 20, right: 40, left: 0, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="#F1CCA6"
              />
              <XAxis
                dataKey="label"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#8C4905", fontWeight: 600, fontSize: 11 }}
                dy={10}
              />
              <YAxis
                domain={[0, 100]}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#C1762A", fontSize: 12 }}
                tickFormatter={(v) => `${v}đ`}
                width={36}
              />

              {/* Đường trung bình tham chiếu */}
              <ReferenceLine
                y={avgScore}
                stroke="#C1762A"
                strokeDasharray="5 4"
                strokeWidth={1.5}
                label={{
                  value: `TB ${avgScore}đ`,
                  position: "insideRight",
                  fill: "#C1762A",
                  fontSize: 11,
                  fontWeight: 700,
                  dy: -8,
                }}
              />

              <Tooltip content={<CustomTooltip />} />

              <Line
                type="monotone"
                dataKey="score"
                stroke="#8C4905"
                strokeWidth={3}
                dot={{
                  r: 4,
                  fill: "#C1762A",
                  strokeWidth: 2,
                  stroke: "#fff",
                }}
                activeDot={{
                  r: 7,
                  fill: "#8C4905",
                  stroke: "#F7ECE1",
                  strokeWidth: 3,
                }}
                animationDuration={900}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Legend */}
      {!isLoading && chartData.length > 0 && (
        <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-[#F1CCA6]">
          <div className="flex items-center gap-1.5 text-xs text-[#8C4905] font-medium">
            <span className="w-6 h-0.5 bg-[#8C4905] rounded-full inline-block" />
            Điểm mỗi bài
          </div>
          <div className="flex items-center gap-1.5 text-xs text-[#C1762A] font-medium">
            <span
              className="w-6 inline-block"
              style={{
                borderTop: "2px dashed #C1762A",
                display: "inline-block",
              }}
            />
            Điểm trung bình
          </div>
          <div className="ml-auto text-xs text-[#C1762A]/70">
            {chartData.length} bài hoàn thành
          </div>
        </div>
      )}
    </section>
  );
}
