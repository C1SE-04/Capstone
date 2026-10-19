"use client";

/**
 * File: components/monitor/ActivityHeatmap.tsx
 * Task: T6.6 / Refactor: Biểu đồ nhiệt hoạt động học tập theo chuẩn GitHub Contribution Graph
 * - Cấu trúc lưới 7 hàng (T2 - CN), kích thước ô 11px x 11px bo góc nhẹ 2px, khoảng cách 3px chuẩn GitHub.
 * - Chỉ hiện nhãn T2, T4, T6 (Mon, Wed, Fri) bên trái để giao diện tinh gọn, không rối mắt.
 * - Nhãn tháng ở hàng trên cùng được canh thẳng hàng với tuần bắt đầu của tháng.
 * - 5 cấp độ màu hiển thị mật độ học tập (Hỗ trợ chuyển đổi giữa Bảng màu Cam Socratic và Xanh Lá GitHub).
 * - Tooltip nổi hiển thị chi tiết số phút và thứ/ngày/tháng.
 * - Chú giải (Legend) "Ít" -> "Nhiều" ở góc dưới bên phải chuẩn GitHub.
 */

import React, { useState, useMemo } from "react";
import {
  format,
  parseISO,
  startOfWeek,
  endOfWeek,
  eachDayOfInterval,
  subDays,
  subWeeks,
  isAfter,
  isToday,
} from "date-fns";
import { vi } from "date-fns/locale";
import { Activity, Sparkles, Check } from "lucide-react";
import { cn } from "@/lib/utils";

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

// ─── Color Palettes ──────────────────────────────────────────────────────────

type PaletteType = "socratic" | "github";

interface HeatColor {
  bg: string;
  border: string;
  label: string;
}

const PALETTES: Record<PaletteType, HeatColor[]> = {
  // Bảng màu Cam ấm áp chuẩn thương hiệu SocraticKid
  socratic: [
    { bg: "#F4EBE2", border: "#E8DDD2", label: "Không học" },
    { bg: "#FDE6C4", border: "#F5C789", label: "1 - 20 phút" },
    { bg: "#F5A64E", border: "#E69136", label: "21 - 45 phút" },
    { bg: "#C1762A", border: "#A45E1B", label: "46 - 75 phút" },
    { bg: "#8C4905", border: "#693502", label: "> 75 phút" },
  ],
  // Bảng màu Xanh Lá biểu tượng của GitHub Contribution Graph
  github: [
    { bg: "#EBEDF0", border: "#D0D7DE", label: "Không học" },
    { bg: "#9BE9A8", border: "#7BC96F", label: "1 - 20 phút" },
    { bg: "#40C463", border: "#34A051", label: "21 - 45 phút" },
    { bg: "#30A14E", border: "#238636", label: "46 - 75 phút" },
    { bg: "#216E39", border: "#196127", label: "> 75 phút" },
  ],
};

function getHeatColorByMinutes(minutes: number, palette: PaletteType): HeatColor {
  const p = PALETTES[palette];
  if (minutes <= 0) return p[0];
  if (minutes <= 20) return p[1];
  if (minutes <= 45) return p[2];
  if (minutes <= 75) return p[3];
  return p[4];
}

// ─── Mock Data Generator ────────────────────────────────────────────────────

/**
 * Tạo mock data N ngày gần nhất kết thúc vào hôm nay
 * Mặc định tạo ~24 tuần (168 ngày) để biểu đồ hiển thị rộng rãi, đẹp mắt giống GitHub
 */
export function generateMockHeatmapData(days = 168): HeatmapDay[] {
  const today = new Date();
  return Array.from({ length: days }, (_, i) => {
    const date = subDays(today, days - 1 - i);
    // 65% ngày có hoạt động học
    const studied = Math.random() > 0.35;
    const minutes = studied ? Math.floor(Math.random() * 95) + 10 : 0;
    return {
      date: format(date, "yyyy-MM-dd"),
      minutes,
    };
  });
}

// ─── Component Chính ────────────────────────────────────────────────────────

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
  const [palette, setPalette] = useState<PaletteType>("socratic");
  const [tooltip, setTooltip] = useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    day: null,
  });

  const today = useMemo(() => new Date(), []);
  const todayStr = useMemo(() => format(today, "yyyy-MM-dd"), [today]);

  // Chuẩn hóa data và chia thành các cột tuần (mỗi cột 7 ngày: T2 -> CN)
  const { weeks, monthLabels, stats } = useMemo(() => {
    if (!data || data.length === 0) {
      return {
        weeks: [],
        monthLabels: [],
        stats: { activeDays: 0, totalMinutes: 0, maxMinutes: 0, totalDays: 0 },
      };
    }

    const sortedData = [...data].sort((a, b) => a.date.localeCompare(b.date));
    const dataMap = new Map<string, number>();
    let totalMinutes = 0;
    let activeDays = 0;
    let maxMinutes = 0;

    sortedData.forEach((d) => {
      dataMap.set(d.date, d.minutes);
      if (d.minutes > 0) {
        activeDays += 1;
        totalMinutes += d.minutes;
        if (d.minutes > maxMinutes) maxMinutes = d.minutes;
      }
    });

    // Ngày đầu tiên và ngày cuối cùng
    const firstDate = parseISO(sortedData[0].date);
    const lastDate = parseISO(sortedData[sortedData.length - 1].date);

    // Canh chỉnh tuần: bắt đầu từ Thứ Hai của tuần đầu tiên đến Chủ Nhật của tuần cuối cùng
    const startDate = startOfWeek(firstDate, { weekStartsOn: 1 });
    const endDate = endOfWeek(lastDate, { weekStartsOn: 1 });

    const allIntervalDays = eachDayOfInterval({ start: startDate, end: endDate });

    // Gom thành các cột tuần (mỗi cột 7 ngày: Thứ 2 = index 0, ..., Chủ Nhật = index 6)
    const groupedWeeks: (HeatmapDay | null)[][] = [];
    let currentWeek: (HeatmapDay | null)[] = [];

    allIntervalDays.forEach((d) => {
      const dateStr = format(d, "yyyy-MM-dd");
      const dayOfWeek = d.getDay(); // 0=CN, 1=T2...6=T7
      const adjustedDow = dayOfWeek === 0 ? 6 : dayOfWeek - 1; // 0=T2, ..., 6=CN

      if (adjustedDow === 0 && currentWeek.length > 0) {
        groupedWeeks.push(currentWeek);
        currentWeek = [];
      }

      // Không hiển thị ngày trong tương lai (sau hôm nay)
      const isFuture = isAfter(d, today);

      if (isFuture) {
        currentWeek.push(null);
      } else {
        const minutes = dataMap.get(dateStr) ?? 0;
        currentWeek.push({
          date: dateStr,
          minutes,
        });
      }
    });

    if (currentWeek.length > 0) {
      while (currentWeek.length < 7) {
        currentWeek.push(null);
      }
      groupedWeeks.push(currentWeek);
    }

    // Tính nhãn tháng (chỉ hiện khi bắt đầu tháng mới và cách nhau tối thiểu 2 tuần)
    const mLabels: { label: string; colIndex: number }[] = [];
    let lastMonth = -1;
    let lastColIndex = -999;

    groupedWeeks.forEach((week, colIdx) => {
      const firstValidDay = week.find((d) => d !== null);
      if (!firstValidDay) return;

      const dateObj = parseISO(firstValidDay.date);
      const m = dateObj.getMonth();

      if (m !== lastMonth) {
        if (colIdx - lastColIndex >= 2 || lastColIndex === -999) {
          mLabels.push({
            label: `Thg ${m + 1}`,
            colIndex: colIdx,
          });
          lastMonth = m;
          lastColIndex = colIdx;
        }
      }
    });

    return {
      weeks: groupedWeeks,
      monthLabels: mLabels,
      stats: {
        activeDays,
        totalMinutes,
        maxMinutes,
        totalDays: sortedData.length,
      },
    };
  }, [data, today]);

  // Loading skeleton
  if (isLoading) {
    return (
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mt-6 animate-pulse">
        <div className="h-6 w-56 bg-[#F7ECE1] rounded-md mb-6" />
        <div className="flex gap-1">
          {Array.from({ length: 20 }).map((_, i) => (
            <div key={i} className="flex flex-col gap-1">
              {Array.from({ length: 7 }).map((_, j) => (
                <div key={j} className="w-[17px] h-[17px] rounded-[3px] bg-[#F7ECE1]" />
              ))}
            </div>
          ))}
        </div>
      </section>
    );
  }

  // Nhãn thứ chuẩn GitHub: Chỉ hiển thị Thứ Hai (T2), Thứ Tư (T4), Thứ Sáu (T6)
  const DAY_ROWS = [
    { label: "T2", index: 0 },
    { label: "", index: 1 },
    { label: "T4", index: 2 },
    { label: "", index: 3 },
    { label: "T6", index: 4 },
    { label: "", index: 5 },
    { label: "", index: 6 },
  ];

  // Kích thước ô to rõ ràng, dễ nhìn hơn (17px) và khoảng cách 4px
  const CELL_SIZE = 17;
  const CELL_GAP = 4;

  return (
    <section className="bg-white rounded-2xl border border-[#F1CCA6]/80 p-5 md:p-6 shadow-sm mt-6">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-5 bg-[#C1762A] rounded-full inline-block" />
            <h2 className="text-base md:text-lg font-bold text-[#8C4905] flex items-center gap-2">
              <Activity size={18} className="text-[#C1762A]" />
              {title}
            </h2>
          </div>
          <p className="text-xs text-[#C1762A] mt-1 ml-3.5">
            <span className="font-bold text-[#8C4905]">{stats.activeDays}</span> ngày học trong {weeks.length} tuần qua • Tổng cộng{" "}
            <span className="font-bold text-[#8C4905]">{(stats.totalMinutes / 60).toFixed(1)}</span> giờ học
          </p>
        </div>

        {/* Cụm công cụ bên phải: Chuyển đổi bảng màu Cam / Xanh GitHub */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="flex items-center bg-[#F7ECE1] p-1 rounded-xl border border-[#F1CCA6] text-xs">
            <button
              onClick={() => setPalette("socratic")}
              className={cn(
                "px-2.5 py-1 rounded-lg font-semibold transition-all text-xs cursor-pointer",
                palette === "socratic"
                  ? "bg-[#C1762A] text-white shadow-sm"
                  : "text-[#8C4905] hover:text-[#C1762A]"
              )}
            >
              Cam Socratic
            </button>
            <button
              onClick={() => setPalette("github")}
              className={cn(
                "px-2.5 py-1 rounded-lg font-semibold transition-all text-xs cursor-pointer flex items-center gap-1",
                palette === "github"
                  ? "bg-[#216E39] text-white shadow-sm"
                  : "text-[#8C4905] hover:text-[#216E39]"
              )}
            >
              Xanh GitHub
            </button>
          </div>
        </div>
      </div>

      {/* ── Heatmap Grid Container chuẩn GitHub (To, rộng rãi, dễ nhìn) ── */}
      <div className="relative overflow-x-auto pb-2 pt-1 select-none">
        {/* Tooltip nổi chuẩn GitHub */}
        {tooltip.visible && tooltip.day && (
          <div
            className="fixed z-50 pointer-events-none transform -translate-x-1/2 -translate-y-full"
            style={{
              left: tooltip.x,
              top: tooltip.y - 10,
            }}
          >
            <div className="bg-gray-900/95 text-white text-xs rounded-xl px-3 py-2 shadow-2xl whitespace-nowrap border border-white/10 backdrop-blur-sm animate-in fade-in zoom-in-95 duration-150">
              <span className="font-bold text-amber-300">
                {tooltip.day.minutes > 0
                  ? `${tooltip.day.minutes} phút học`
                  : "Không có hoạt động học"}
              </span>
              <span className="text-gray-300 ml-1.5">
                vào {format(parseISO(tooltip.day.date), "EEEE, dd/MM/yyyy", { locale: vi })}
              </span>
            </div>
          </div>
        )}

        <div className="inline-block min-w-max p-3 rounded-2xl bg-[#FDF8F3]/60 border border-[#F1CCA6]/40">
          <div className="flex">
            {/* Nhãn Thứ bên trái (T2, T4, T6 to rõ ràng) */}
            <div className="flex flex-col pr-3 text-xs font-semibold text-gray-500 pt-[26px]">
              {DAY_ROWS.map((row, i) => (
                <div
                  key={i}
                  style={{
                    height: `${CELL_SIZE}px`,
                    marginBottom: i < 6 ? `${CELL_GAP}px` : "0px",
                  }}
                  className="flex items-center justify-end w-5 leading-none"
                >
                  {row.label}
                </div>
              ))}
            </div>

            {/* Cột các tuần và nhãn tháng phía trên */}
            <div className="flex flex-col">
              {/* Nhãn tháng phía trên cùng (to, đậm nét) */}
              <div
                className="relative h-5 mb-1.5 text-xs font-bold text-gray-700"
                style={{
                  width: `${weeks.length * (CELL_SIZE + CELL_GAP)}px`,
                }}
              >
                {monthLabels.map((m) => (
                  <span
                    key={m.colIndex}
                    className="absolute top-0 leading-none"
                    style={{
                      left: `${m.colIndex * (CELL_SIZE + CELL_GAP)}px`,
                    }}
                  >
                    {m.label}
                  </span>
                ))}
              </div>

              {/* Lưới các ô vuông (Grid columns to rõ 17px) */}
              <div className="flex" style={{ gap: `${CELL_GAP}px` }}>
                {weeks.map((week, colIdx) => (
                  <div
                    key={colIdx}
                    className="flex flex-col"
                    style={{ gap: `${CELL_GAP}px` }}
                  >
                    {week.map((day, rowIdx) => {
                      if (!day) {
                        return (
                          <div
                            key={rowIdx}
                            style={{
                              width: `${CELL_SIZE}px`,
                              height: `${CELL_SIZE}px`,
                            }}
                            className="opacity-0 pointer-events-none"
                          />
                        );
                      }

                      const color = getHeatColorByMinutes(day.minutes, palette);
                      const isCurrentDay = day.date === todayStr;

                      return (
                        <div
                          key={rowIdx}
                          style={{
                            width: `${CELL_SIZE}px`,
                            height: `${CELL_SIZE}px`,
                            backgroundColor: color.bg,
                            border: `1.5px solid ${isCurrentDay ? (palette === "socratic" ? "#8C4905" : "#216E39") : color.border}`,
                            boxShadow: isCurrentDay
                              ? `0 0 0 2px ${palette === "socratic" ? "#C1762A66" : "#40C46366"}`
                              : undefined,
                          }}
                          className={cn(
                            "rounded-[3px] transition-all duration-100 cursor-pointer relative",
                            "hover:scale-125 hover:z-20 hover:shadow-md"
                          )}
                          onMouseEnter={(e) =>
                            setTooltip({
                              visible: true,
                              x: e.clientX,
                              y: e.clientY,
                              day,
                            })
                          }
                          onMouseMove={(e) =>
                            setTooltip((prev) => ({
                              ...prev,
                              x: e.clientX,
                              y: e.clientY,
                            }))
                          }
                          onMouseLeave={() =>
                            setTooltip((prev) => ({
                              ...prev,
                              visible: false,
                              day: null,
                            }))
                          }
                          role="button"
                          aria-label={`${day.date}: ${day.minutes} phút học`}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ── Chú giải (Legend) to rõ ràng ở góc dưới bên phải ── */}
          <div className="flex items-center justify-end gap-2 mt-4 text-xs text-gray-600 font-semibold">
            <span>Ít</span>
            <div className="flex items-center gap-[4px] mx-1">
              {PALETTES[palette].map((item, idx) => (
                <div
                  key={idx}
                  title={item.label}
                  style={{
                    width: `${CELL_SIZE}px`,
                    height: `${CELL_SIZE}px`,
                    backgroundColor: item.bg,
                    border: `1.5px solid ${item.border}`,
                  }}
                  className="rounded-[3px]"
                />
              ))}
            </div>
            <span>Nhiều</span>
          </div>
        </div>
      </div>
    </section>
  );
}
