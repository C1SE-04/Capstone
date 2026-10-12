"use client";

/**
 * File: components/monitor/ActivityHeatmap.tsx
 * Task: T6.6 — [Thiên] [FE] Code UI component <ActivityHeatmap />
 * Mô tả: Biểu đồ nhiệt hoạt động học theo ngày cho Parent Dashboard.
 * - Hiển thị mật độ học tập mỗi ngày trong khoảng thời gian (7d / 30d).
 * - Màu sắc thay đổi theo số phút học: trắng → cam nhạt → cam → nâu.
 * - Tooltip khi hover hiển thị ngày + số phút học.
 * - Hỗ trợ prop `data` dạng mock (UI tĩnh), sẵn sàng ráp API sau.
 */

import React, { useState, useMemo } from "react";
import { format, parseISO, startOfWeek, eachDayOfInterval, subDays } from "date-fns";
import { vi } from "date-fns/locale";
import { Activity } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface HeatmapDay {
  date: string;    // ISO "2026-10-01"
  minutes: number; // phút học trong ngày đó (0 = không học)
}

interface ActivityHeatmapProps {
  data: HeatmapDay[];
  title?: string;
  isLoading?: boolean;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Trả về màu nền ô dựa trên số phút học */
function getHeatColor(minutes: number): {
  bg: string;
  border: string;
  label: string;
} {
  if (minutes === 0) return { bg: "#F7ECE1", border: "#F1CCA6", label: "Không học" };
  if (minutes <= 20) return { bg: "#FDE8C8", border: "#F5C98A", label: "Học ít" };
  if (minutes <= 45) return { bg: "#F0A85A", border: "#E5913B", label: "Học vừa" };
  if (minutes <= 75) return { bg: "#C1762A", border: "#A8601F", label: "Học nhiều" };
  return { bg: "#8C4905", border: "#6B3704", label: "Học rất nhiều" };
}

/** Tạo mock data N ngày ngẫu nhiên dùng để demo UI tĩnh */
export function generateMockHeatmapData(days = 30): HeatmapDay[] {
  const today = new Date();
  return Array.from({ length: days }, (_, i) => {
    const date = subDays(today, days - 1 - i);
    // Ngẫu nhiên có học hay không (70% ngày có học)
    const studied = Math.random() > 0.3;
    const minutes = studied ? Math.floor(Math.random() * 100) + 5 : 0;
    return {
      date: format(date, "yyyy-MM-dd"),
      minutes,
    };
  });
}

// ─── Component chính ─────────────────────────────────────────────────────────

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  day: HeatmapDay | null;
}

export function ActivityHeatmap({
  data,
  title = "Lịch hoạt động học tập",
  isLoading = false,
}: ActivityHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    day: null,
  });

  // Nhóm data thành các tuần (mỗi cột = 1 tuần, mỗi hàng = 1 ngày trong tuần)
  const weeks = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Sắp xếp data theo thứ tự ngày tăng dần
    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));

    // Tạo map tra cứu nhanh
    const dataMap: Record<string, number> = {};
    sortedData.forEach((d) => {
      dataMap[d.date] = d.minutes;
    });

    // Lấy khoảng ngày
    const firstDate = parseISO(sortedData[0].date);
    const lastDate = parseISO(sortedData[sortedData.length - 1].date);

    // Tìm ngày đầu tuần của ngày đầu tiên (Thứ 2)
    const startDay = startOfWeek(firstDate, { weekStartsOn: 1 });

    // Tạo tất cả các ngày từ đầu tuần đến ngày cuối cùng
    const allDays = eachDayOfInterval({ start: startDay, end: lastDate });

    // Nhóm thành tuần (mỗi tuần = 7 ngày, bắt đầu từ Thứ 2)
    const grouped: (HeatmapDay | null)[][] = [];
    let currentWeek: (HeatmapDay | null)[] = [];

    allDays.forEach((day) => {
      const dayOfWeek = day.getDay(); // 0=CN, 1=T2...6=T7
      const adjustedDow = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // 0=T2...6=CN

      // Đầu tuần mới (Thứ 2) → đẩy tuần cũ vào và bắt đầu tuần mới
      if (adjustedDow === 0 && currentWeek.length > 0) {
        grouped.push(currentWeek);
        currentWeek = [];
      }

      const dateStr = format(day, "yyyy-MM-dd");
      const isInRange = dateStr >= sortedData[0].date && dateStr <= sortedData[sortedData.length - 1].date;

      currentWeek.push(
        isInRange
          ? { date: dateStr, minutes: dataMap[dateStr] ?? 0 }
          : null
      );
    });

    if (currentWeek.length > 0) grouped.push(currentWeek);

    return grouped;
  }, [data]);

  // Nhãn tháng (tối ưu khoảng cách tránh đè chữ)
  const monthLabels = useMemo(() => {
    if (!data || data.length === 0) return [];
    const labels: { label: string; weekIndex: number }[] = [];
    let lastMonth = -1;
    let lastWeekIdx = -999;

    weeks.forEach((week, wi) => {
      const firstReal = week.find((d) => d !== null);
      if (!firstReal) return;
      const date = parseISO(firstReal.date);
      const month = date.getMonth();

      // Chỉ thêm nhãn khi sang tháng mới VÀ cách nhãn trước tối thiểu 3 tuần để không đè chữ
      if (month !== lastMonth) {
        if (wi - lastWeekIdx >= 3 || lastWeekIdx === -999) {
          labels.push({
            label: `Tháng ${month + 1}`,
            weekIndex: wi,
          });
          lastMonth = month;
          lastWeekIdx = wi;
        }
      }
    });
    return labels;
  }, [weeks, data]);

  // Thống kê nhanh
  const stats = useMemo(() => {
    if (!data || data.length === 0) return { activeDays: 0, totalMinutes: 0, maxMinutes: 0 };
    const activeDays = data.filter((d) => d.minutes > 0).length;
    const totalMinutes = data.reduce((s, d) => s + d.minutes, 0);
    const maxMinutes = Math.max(...data.map((d) => d.minutes));
    return { activeDays, totalMinutes, maxMinutes };
  }, [data]);

  const DAY_LABELS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const todayStr = format(new Date(), "yyyy-MM-dd");

  // --- Loading skeleton ---
  if (isLoading) {
    return (
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mt-6">
        <div className="flex items-center gap-2 mb-6">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          <span className="text-lg font-bold text-[#8C4905]">{title}</span>
          <svg className="animate-spin h-4 w-4 text-[#C1762A] ml-2" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <div className="animate-pulse flex gap-1.5">
          {Array.from({ length: 5 }).map((_, wi) => (
            <div key={wi} className="flex flex-col gap-1.5">
              {Array.from({ length: 7 }).map((_, di) => (
                <div key={di} className="w-8 h-8 rounded-md bg-[#F7ECE1]" />
              ))}
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mt-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          <Activity size={18} className="text-[#C1762A]" />
          {title}
        </h2>

        {/* Quick stats pills */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-[#F7ECE1] px-3 py-1.5 rounded-xl border border-[#F1CCA6]">
            <span className="text-xs font-black text-[#8C4905]">{stats.activeDays}</span>
            <span className="text-[10px] font-semibold text-[#C1762A]">ngày học</span>
          </div>
          <div className="flex items-center gap-1.5 bg-[#F7ECE1] px-3 py-1.5 rounded-xl border border-[#F1CCA6]">
            <span className="text-xs font-black text-[#8C4905]">{(stats.totalMinutes / 60).toFixed(1)}h</span>
            <span className="text-[10px] font-semibold text-[#C1762A]">tổng giờ</span>
          </div>
          <div className="flex items-center gap-1.5 bg-[#F7ECE1] px-3 py-1.5 rounded-xl border border-[#F1CCA6]">
            <span className="text-xs font-black text-[#8C4905]">{stats.maxMinutes}p</span>
            <span className="text-[10px] font-semibold text-[#C1762A]">ngày nhiều nhất</span>
          </div>
        </div>
      </div>

      {/* Heatmap grid */}
      <div className="relative overflow-x-auto pb-2">
        {/* Fixed tooltip — theo con trỏ */}
        {tooltip.visible && tooltip.day && (
          <div
            className="fixed z-50 pointer-events-none"
            style={{ left: tooltip.x + 14, top: tooltip.y - 56 }}
          >
            <div
              className="text-white text-xs rounded-xl px-3.5 py-2.5 shadow-2xl whitespace-nowrap"
              style={{ background: "linear-gradient(135deg, #3D1E08, #6B3704)" }}
            >
              <p className="font-bold text-sm">
                {format(parseISO(tooltip.day.date), "EEEE, dd/MM/yyyy", { locale: vi })}
              </p>
              <p className="text-[#F1CCA6] mt-0.5">
                {tooltip.day.minutes > 0
                  ? `🎯 ${tooltip.day.minutes} phút học`
                  : "😴 Chưa có hoạt động"}
              </p>
            </div>
          </div>
        )}

        <div className="flex gap-1.5 min-w-max">
          {/* Nhãn ngày trong tuần (cột trái cố định) */}
          <div className="flex flex-col gap-1.5 mr-1 pt-7">
            {DAY_LABELS.map((label) => (
              <div key={label} className="h-8 flex items-center justify-end">
                <span className="text-[10px] font-bold text-[#C1762A] w-5 text-right select-none">
                  {label}
                </span>
              </div>
            ))}
          </div>

          {/* Cột tuần */}
          <div className="flex flex-col">
            {/* Nhãn tháng */}
            <div className="flex gap-1.5 mb-1.5 h-6 relative">
              {weeks.map((_, wi) => {
                const monthLabel = monthLabels.find((m) => m.weekIndex === wi);
                return (
                  <div key={wi} className="w-8 flex-shrink-0 relative">
                    {monthLabel && (
                      <span className="absolute left-0 top-0 text-[10px] font-bold text-[#8C4905] whitespace-nowrap select-none capitalize">
                        {monthLabel.label}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Grid ô ngày */}
            <div className="flex gap-1.5">
              {weeks.map((week, wi) => (
                <div key={wi} className="flex flex-col gap-1.5">
                  {Array.from({ length: 7 }).map((_, di) => {
                    const day = week[di] ?? null;

                    if (!day) {
                      return (
                        <div
                          key={di}
                          className="w-8 h-8 rounded-md"
                          style={{ opacity: 0 }}
                        />
                      );
                    }

                    const colors = getHeatColor(day.minutes);
                    const isToday = day.date === todayStr;

                    return (
                      <div
                        key={di}
                        className="w-8 h-8 rounded-md cursor-pointer transition-transform duration-100 hover:scale-110 hover:shadow-lg relative"
                        style={{
                          backgroundColor: colors.bg,
                          border: `1.5px solid ${isToday ? "#8C4905" : colors.border}`,
                          boxShadow: isToday ? "0 0 0 2.5px #C1762A66" : undefined,
                        }}
                        onMouseEnter={(e) =>
                          setTooltip({ visible: true, x: e.clientX, y: e.clientY, day })
                        }
                        onMouseMove={(e) =>
                          setTooltip((prev) => ({ ...prev, x: e.clientX, y: e.clientY }))
                        }
                        onMouseLeave={() =>
                          setTooltip((prev) => ({ ...prev, visible: false, day: null }))
                        }
                        role="button"
                        aria-label={`${day.date}: ${day.minutes} phút học`}
                      >
                        {/* Chấm nhỏ đánh dấu hôm nay */}
                        {isToday && (
                          <div className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[#8C4905]" />
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-5 justify-end">
        <span className="text-[10px] font-semibold text-[#C1762A] select-none">Ít</span>
        {[0, 15, 40, 70, 100].map((mins, i) => {
          const c = getHeatColor(mins);
          return (
            <div
              key={i}
              title={c.label}
              className="w-5 h-5 rounded-sm transition-transform hover:scale-125 cursor-default"
              style={{ backgroundColor: c.bg, border: `1.5px solid ${c.border}` }}
            />
          );
        })}
        <span className="text-[10px] font-semibold text-[#C1762A] select-none">Nhiều</span>
      </div>
    </section>
  );
}
