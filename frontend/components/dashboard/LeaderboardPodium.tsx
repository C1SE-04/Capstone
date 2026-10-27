/**
 * File: components/dashboard/LeaderboardPodium.tsx
 * Mô tả: Bục vinh danh Top 3 học sinh xuất sắc nhất (Gold, Silver, Bronze) - US 8.2 & Task 8.15.
 * - Thiết kế 3D bậc thang: Hạng 2 (Bạc - trái), Hạng 1 (Vàng - giữa cao nhất), Hạng 3 (Đồng - phải).
 * - Hiển thị Avatar, Vương miện, Cấp độ ngọn lửa tiến hóa, Số ngày streak rực rỡ.
 */

"use client";

import React from "react";
import { StreakLeaderboardItem } from "@/types/leaderboard";
import { getStreakMilestone } from "@/lib/streakMilestones";
import { Crown, Flame, Trophy, Award, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface LeaderboardPodiumProps {
  topThree: StreakLeaderboardItem[];
}

export function LeaderboardPodium({ topThree }: LeaderboardPodiumProps) {
  if (!topThree || topThree.length === 0) return null;

  const first = topThree.find((item) => item.rank === 1) || topThree[0];
  const second = topThree.find((item) => item.rank === 2) || (topThree.length > 1 ? topThree[1] : null);
  const third = topThree.find((item) => item.rank === 3) || (topThree.length > 2 ? topThree[2] : null);

  const renderPodiumStep = (
    item: StreakLeaderboardItem | null,
    position: "first" | "second" | "third"
  ) => {
    if (!item) {
      return (
        <div className="flex-1 flex flex-col items-center justify-end opacity-40">
          <div className="w-16 h-16 rounded-full border-2 border-dashed border-[#C1762A]/40 flex items-center justify-center text-stone-400 mb-2">
            ?
          </div>
          <div className="w-full bg-[#F1CCA6]/40 rounded-t-2xl h-24 flex items-center justify-center text-xs text-[#8C4905]/60 font-semibold">
            Đang chờ
          </div>
        </div>
      );
    }

    const milestone = getStreakMilestone(item.streak_days);

    const config = {
      first: {
        height: "h-44 md:h-52",
        order: "order-2",
        avatarSize: "w-20 h-20 md:w-24 md:h-24",
        border: "border-4 border-amber-400 ring-4 ring-amber-300/50 shadow-xl shadow-amber-300/30",
        podiumBg: "bg-gradient-to-b from-amber-400 via-amber-300 to-amber-200",
        label: "Hạng 1",
        labelColor: "bg-amber-600 text-white",
        medalIcon: <Crown className="text-amber-500 fill-amber-400 w-8 h-8 md:w-9 md:h-9 -top-6 animate-bounce" />,
      },
      second: {
        height: "h-32 md:h-38",
        order: "order-1",
        avatarSize: "w-16 h-16 md:w-20 md:h-20",
        border: "border-4 border-slate-300 ring-2 ring-slate-200 shadow-md",
        podiumBg: "bg-gradient-to-b from-slate-200 via-slate-300 to-slate-200",
        label: "Hạng 2",
        labelColor: "bg-slate-600 text-white",
        medalIcon: <Award className="text-slate-500 w-6 h-6 -top-4" />,
      },
      third: {
        height: "h-24 md:h-30",
        order: "order-3",
        avatarSize: "w-16 h-16 md:w-20 md:h-20",
        border: "border-4 border-amber-700/60 ring-2 ring-amber-600/30 shadow-md",
        podiumBg: "bg-gradient-to-b from-amber-200 via-[#F1CCA6] to-[#E6B88A]",
        label: "Hạng 3",
        labelColor: "bg-amber-800 text-white",
        medalIcon: <Award className="text-amber-700 w-6 h-6 -top-4" />,
      },
    }[position];

    return (
      <div className={cn("flex-1 flex flex-col items-center justify-end z-10", config.order)}>
        {/* Avatar & Crown */}
        <div className="relative flex flex-col items-center mb-3">
          <div className="absolute -top-7 md:-top-8">{config.medalIcon}</div>
          <div
            className={cn(
              "rounded-full overflow-hidden bg-white relative transition-transform duration-200 hover:scale-105",
              config.avatarSize,
              config.border
            )}
          >
            <img
              src={item.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${item.student_id}`}
              alt={item.display_name}
              className="w-full h-full object-cover"
            />
          </div>
          {item.is_current_user && (
            <span className="absolute -bottom-2 bg-[#8C4905] text-white text-[10px] font-black px-2 py-0.5 rounded-full shadow-sm">
              Bạn
            </span>
          )}
        </div>

        {/* Tên & Lớp */}
        <div className="text-center mb-2 px-1 w-full">
          <p className="font-extrabold text-sm md:text-base text-[#8C4905] truncate max-w-[110px] md:max-w-[140px] mx-auto">
            {item.display_name}
          </p>
          <div className="flex items-center justify-center gap-1 mt-0.5">
            {item.grade ? (
              <span className="text-[11px] font-semibold text-[#C1762A] bg-white/70 px-1.5 py-0.2 rounded-md border border-[#F1CCA6]">
                Lớp {item.grade}
              </span>
            ) : null}
            <span className={cn("text-[11px] font-bold px-1.5 py-0.2 rounded-md", milestone.badgeBg, milestone.textColor)}>
              {milestone.emoji} {item.streak_days}d
            </span>
          </div>
        </div>

        {/* Bục Bậc Thang Podium */}
        <div
          className={cn(
            "w-full rounded-t-2xl flex flex-col items-center justify-between p-2 shadow-lg border-t-2 border-white/60 relative overflow-hidden transition-all duration-300",
            config.height,
            config.podiumBg
          )}
        >
          {/* Huy hiệu thứ hạng */}
          <span
            className={cn(
              "text-xs md:text-sm font-black px-3 py-1 rounded-full shadow-sm tracking-wider uppercase",
              config.labelColor
            )}
          >
            {config.label}
          </span>

          {/* Ngọn lửa & Số ngày streak */}
          <div className="flex flex-col items-center justify-center my-auto">
            <div className="flex items-center gap-1.5 bg-white/90 backdrop-blur-xs px-2.5 py-1 rounded-xl shadow-xs">
              <Flame size={20} className={cn(milestone.flameColor, "shrink-0 fill-current")} />
              <span className="font-black text-base md:text-lg text-[#8C4905]">
                {item.streak_days}
              </span>
              <span className="text-[11px] font-semibold text-stone-600 hidden sm:inline">ngày</span>
            </div>
            <span className="text-[11px] font-medium text-[#8C4905]/80 mt-1 italic hidden md:inline">
              {milestone.name}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-gradient-to-b from-[#FFF8F0] to-[#F1CCA6]/40 rounded-3xl p-4 md:p-6 border border-[#F1CCA6] shadow-sm mb-8">
      <div className="flex items-center justify-center gap-2 mb-4">
        <Sparkles className="text-amber-500 w-5 h-5 animate-pulse" />
        <h3 className="text-lg md:text-xl font-black text-[#8C4905] tracking-tight uppercase">
          Bục Vinh Danh Top 3
        </h3>
        <Sparkles className="text-amber-500 w-5 h-5 animate-pulse" />
      </div>

      {/* Podium grid */}
      <div className="flex items-end justify-center gap-2 md:gap-4 max-w-lg mx-auto pt-6">
        {renderPodiumStep(second, "second")}
        {renderPodiumStep(first, "first")}
        {renderPodiumStep(third, "third")}
      </div>
    </div>
  );
}
