"use client";

/**
 * File: components/monitor/IndependenceChart.tsx
 * Task: T6.9 — Biểu đồ Điểm Tự Lực theo tuần (Parent Dashboard)
 *
 * Logic:
 *  - Luôn hiện đủ 7 ngày Thứ 2 → CN theo tuần đang xem (weekStart, weekEnd)
 *  - Ngày không học (chưa có bài nào ấn "Đã hiểu"): điểm tự lực = 0đ
 *  - Ngày có học: tính điểm tự lực trung bình của các bài hoàn thành trong ngày đó
 *  - Đường biểu đồ nối liền mạch cả 7 ngày với hiệu ứng cong mềm mại (monotone), dot tròn ở các ngày đồng bộ với Biểu đồ thời gian học
 *  - Tooltip hiển thị chi tiết: ngày đó mấy bài, điểm tự lực trung bình ngày đó là bao nhiêu (hoặc 0đ - chưa có bài tập)
 *  - Đường nét đứt tham chiếu = điểm TB của các bài đã học trong tuần
 */

import { useMemo } from "react";
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
import { Brain } from "lucide-react";

// --- Types ---

export interface IndependencePoint {
  date: string; // ISO datetime string (created_at từ API)
  score: number;
  evaluation: string;
}

interface IndependenceChartProps {
  data: IndependencePoint[];
  isLoading?: boolean;
  weekStart?: Date;
  weekEnd?: Date;
}

// Tên thứ hiển thị trên trục X
const DAY_LABELS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"];

// Lấy "YYYY-MM-DD" theo giờ Việt Nam (UTC+7) từ một ISO string
function toVNDateKey(isoStr: string): string {
  const utcMs = new Date(isoStr).getTime();
  const vnMs = utcMs + 7 * 60 * 60 * 1000;
  const vnDate = new Date(vnMs);
  const yyyy = vnDate.getUTCFullYear();
  const mm = String(vnDate.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(vnDate.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

// Format Date thành YYYY-MM-DD theo local (weekStart/weekEnd từ date-fns)
function toLocalDateKey(d: Date): string {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

// Format ngày: "Thứ Năm, 22/10/2026"
function formatVNDate(d: Date): string {
  const dayNames = ["Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"];
  const dow = dayNames[d.getDay()];
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dow}, ${dd}/${mm}/${yyyy}`;
}

// --- Custom Tooltip ---

interface ChartDayItem {
  date: Date;
  shortLabel: string;   // "Thứ 2", ..., "CN"
  dateLabel: string;    // "22/10"
  fullDateLabel: string; // "Thứ Năm, 22/10/2026"
  score: number;        // 0 nếu không học, hoặc điểm trung bình ngày
  count: number;        // số bài hoàn thành trong ngày
  avgEvaluation: string;
}

interface TooltipPayload {
  payload: ChartDayItem;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0].payload;

  if (item.count === 0) {
    return (
      <div className="bg-white rounded-xl border border-[#F1CCA6] shadow-lg p-3.5 min-w-[200px]">
        <p className="text-xs font-bold text-[#C1762A] mb-1.5">{item.fullDateLabel}</p>
        <div className="flex items-baseline gap-1 mb-1">
          <span className="text-2xl font-black text-stone-400">0</span>
          <span className="text-xs text-stone-400 font-bold">/100đ</span>
        </div>
        <p className="text-xs text-stone-500 italic mb-1.5">Chưa có bài tập hoàn thành trong ngày</p>
        <div className="border-t border-[#F1CCA6]/40 pt-1.5">
          <p className="text-[11px] text-stone-400 font-medium">
            Số bài hoàn thành: <span className="font-bold">0 bài</span>
          </p>
        </div>
      </div>
    );
  }

  const score = item.score;
  const colorCls =
    score >= 80
      ? "text-emerald-600"
      : score >= 60
      ? "text-amber-600"
      : score >= 40
      ? "text-orange-600"
      : "text-red-500";

  return (
    <div className="bg-white rounded-xl border border-[#F1CCA6] shadow-lg p-3.5 min-w-[210px]">
      <p className="text-xs font-bold text-[#C1762A] mb-1.5">{item.fullDateLabel}</p>
      <div className="flex items-baseline gap-1 mb-0.5">
        <span className={`text-2xl font-black ${colorCls}`}>{score}</span>
        <span className="text-xs text-[#8C4905] font-bold">/100đ</span>
      </div>
      <p className="text-xs font-semibold text-[#8C4905]/85 mb-1.5">{item.avgEvaluation}</p>
      <div className="border-t border-[#F1CCA6]/50 pt-1.5">
        <p className="text-[11px] text-[#C1762A] font-semibold">
          📚 Đã hoàn thành: <span className="font-bold text-[#8C4905]">{item.count} bài</span>
        </p>
      </div>
    </div>
  );
}

// --- Main Component ---

export function IndependenceChart({
  data,
  isLoading = false,
  weekStart,
  weekEnd,
}: IndependenceChartProps) {
  // Bước 1: Gom điểm theo ngày VN (UTC+7)
  const dailyMap = useMemo(() => {
    const map: Record<string, { totalScore: number; count: number }> = {};
    data.forEach((item) => {
      if (!item.date) return;
      try {
        const key = toVNDateKey(item.date);
        if (!map[key]) map[key] = { totalScore: 0, count: 0 };
        map[key].totalScore += item.score;
        map[key].count += 1;
      } catch {
        // ignore invalid dates
      }
    });
    return map;
  }, [data]);

  // Bước 2: Tạo 7 điểm dữ liệu cho tuần (Thứ 2 → CN)
  // Ngày không học thì điểm = 0đ để tạo đường nối trực quan
  const chartData: ChartDayItem[] = useMemo(() => {
    if (!weekStart || !weekEnd) return [];

    const result: ChartDayItem[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      const key = toLocalDateKey(d);
      const group = dailyMap[key];
      const count = group ? group.count : 0;
      const avgScore = count > 0 ? Math.round(group.totalScore / count) : 0;

      let avgEvaluation = "Chưa có bài tập";
      if (count > 0) {
        if (avgScore >= 80) avgEvaluation = "Tự lập xuất sắc";
        else if (avgScore >= 60) avgEvaluation = "Tự lập tốt";
        else if (avgScore >= 40) avgEvaluation = "Đang tiến bộ";
        else avgEvaluation = "Cần thêm hỗ trợ";
      }

      result.push({
        date: d,
        shortLabel: DAY_LABELS[i],
        dateLabel: `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`,
        fullDateLabel: formatVNDate(d),
        score: avgScore,
        count,
        avgEvaluation,
      });
    }
    return result;
  }, [weekStart, weekEnd, dailyMap]);

  // Tổng bài hoàn thành và điểm TB các bài trong tuần
  const totalCompleted = data.length;
  const avgWeekScore = useMemo(() => {
    if (totalCompleted === 0) return 0;
    return Math.round(data.reduce((s, d) => s + d.score, 0) / totalCompleted);
  }, [data, totalCompleted]);

  const getBadge = (avg: number) => {
    if (avg >= 80) return { label: "Tự lập xuất sắc", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" };
    if (avg >= 60) return { label: "Tự lập tốt", cls: "bg-amber-50 text-amber-700 border-amber-200" };
    if (avg >= 40) return { label: "Tự lập đang tiến bộ", cls: "bg-orange-50 text-orange-700 border-orange-200" };
    return { label: "Cần tiến bộ", cls: "bg-red-50 text-red-600 border-red-200" };
  };
  const badge = getBadge(avgWeekScore);

  const hasChartData = chartData.length === 7;

  return (
    <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mt-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#8C4905] rounded-full inline-block" />
          <Brain size={18} className="text-[#C1762A]" />
          Điểm Tự Lực theo thời gian
        </h2>
        {!isLoading && totalCompleted > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#8C4905] bg-[#F7ECE1] px-3 py-1 rounded-full border border-[#F1CCA6]">
              TB {avgWeekScore}/100
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${badge.cls}`}>
              {badge.label}
            </span>
          </div>
        )}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="h-[350px] flex items-center justify-center text-[#C1762A]">
          <svg className="animate-spin h-6 w-6" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )}

      {/* Chart — chiều cao 350px chuẩn như Biểu đồ thời gian học */}
      {!isLoading && hasChartData && (
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1CCA6" />
              <XAxis
                dataKey="shortLabel"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#8C4905", fontWeight: 600, fontSize: 12 }}
                dy={10}
              />
              <YAxis
                domain={[0, 100]}
                ticks={[0, 25, 50, 75, 100]}
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#C1762A", fontSize: 12 }}
                tickFormatter={(v) => `${v}đ`}
                width={40}
              />

              {/* Đường nét đứt tham chiếu điểm TB tuần */}
              {totalCompleted > 0 && (
                <ReferenceLine
                  y={avgWeekScore}
                  stroke="#C1762A"
                  strokeDasharray="5 4"
                  strokeWidth={1.5}
                  label={{
                    value: `TB ${avgWeekScore}đ`,
                    position: "insideRight",
                    fill: "#C1762A",
                    fontSize: 11,
                    fontWeight: 700,
                    dy: -8,
                  }}
                />
              )}

              <Tooltip content={<CustomTooltip />} />

              {/* Đường biểu đồ uốn lượn monotone, chấm dot ở mọi ngày đồng bộ với biểu đồ thời gian học */}
              <Line
                type="monotone"
                dataKey="score"
                stroke="#C1762A"
                strokeWidth={4}
                dot={{ r: 4, fill: "#8C4905", strokeWidth: 2, stroke: "#fff" }}
                activeDot={{ r: 6, fill: "#C1762A", stroke: "#F7ECE1", strokeWidth: 3 }}
                animationDuration={1000}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Empty state khi không có tuần hợp lệ */}
      {!isLoading && !hasChartData && (
        <div className="h-[350px] flex flex-col items-center justify-center gap-3 text-[#C1762A]">
          <div className="w-16 h-16 rounded-2xl bg-[#F7ECE1] flex items-center justify-center">
            <Brain size={32} className="opacity-40" />
          </div>
          <p className="text-sm font-semibold text-[#8C4905]">Chưa có dữ liệu điểm tự lực</p>
        </div>
      )}

      {/* Legend */}
      {!isLoading && hasChartData && (
        <div className="flex flex-wrap items-center gap-4 mt-4 pt-4 border-t border-[#F1CCA6]">
          <div className="flex items-center gap-1.5 text-xs text-[#8C4905] font-medium">
            <span className="w-6 h-0.5 bg-[#C1762A] rounded-full inline-block" />
            Điểm TB mỗi ngày
          </div>
          {totalCompleted > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-[#C1762A] font-medium">
              <span
                className="w-6 inline-block"
                style={{ borderTop: "2px dashed #C1762A", display: "inline-block" }}
              />
              Điểm TB cả tuần ({avgWeekScore}đ)
            </div>
          )}
          <div className="ml-auto text-xs text-[#C1762A]/70 font-medium">
            {totalCompleted > 0
              ? `${totalCompleted} bài hoàn thành trong tuần`
              : "Chưa có bài hoàn thành trong tuần này"}
          </div>
        </div>
      )}
    </section>
  );
}
