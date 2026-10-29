/**
 * File: components/dashboard/YourRankCard.tsx
 * Mô tả: Thẻ hiển thị vị trí xếp hạng của học sinh đang đăng nhập (Current User Rank Card) - US 8.2 & Task 8.15.
 * - Hiển thị thứ hạng hiện tại, số ngày streak, kỷ lục cao nhất.
 * - Thanh tiến độ tới mốc tiến hóa ngọn lửa tiếp theo.
 * - Lời động viên sư phạm truyền cảm hứng.
 */

"use client";

import React from "react";
import { StreakLeaderboardItem } from "@/types/leaderboard";
import { getStreakMilestone, getNextStreakMilestone } from "@/lib/streakMilestones";
import { Trophy, Flame, Target, Sparkles, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface YourRankCardProps {
  currentUserEntry?: StreakLeaderboardItem | null;
  totalParticipants: number;
}

export function YourRankCard({
  currentUserEntry,
  totalParticipants,
}: YourRankCardProps) {
  if (!currentUserEntry) {
    return (
      <div className="bg-white/80 backdrop-blur-md rounded-2xl p-5 border border-[#F1CCA6] shadow-sm mb-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-amber-100 flex items-center justify-center text-amber-700 font-bold shrink-0">
            🌱
          </div>
          <div>
            <h4 className="font-extrabold text-[#8C4905] text-base">
              Bạn chưa có mặt trên Bảng xếp hạng
            </h4>
            <p className="text-stone-600 text-sm">
              Hãy học bài và giải toán hôm nay để thắp sáng ngọn lửa streak đầu tiên!
            </p>
          </div>
        </div>
      </div>
    );
  }

  const streak = currentUserEntry.streak_days;
  const maxStreak = currentUserEntry.max_streak || streak;
  const milestone = getStreakMilestone(maxStreak);
  const { nextMilestone, daysRemaining } = getNextStreakMilestone(maxStreak);

  // Tính phần trăm tiến độ đến mốc kỷ lục tiếp theo
  let progressPercent = 100;
  if (nextMilestone) {
    const prevMinDays = milestone.minDays;
    const nextMinDays = nextMilestone.minDays;
    const span = nextMinDays - prevMinDays;
    const currentProgress = maxStreak - prevMinDays;
    progressPercent = Math.min(100, Math.max(0, Math.round((currentProgress / span) * 100)));
  }

  // Lời nhắn khích lệ dựa trên thứ hạng
  let motivationalMessage = "Tiếp tục duy trì thói quen học tập mỗi ngày để thăng hạng nhé!";
  if (currentUserEntry.rank === 1) {
    motivationalMessage = "👑 Tuyệt đỉnh! Bạn đang dẫn đầu bảng xếp hạng! Hãy giữ vững phong độ!";
  } else if (currentUserEntry.rank <= 3) {
    motivationalMessage = "🎉 Xuất sắc! Bạn đang đứng trên bục vinh danh Top 3 danh giá!";
  } else if (currentUserEntry.rank <= 10) {
    motivationalMessage = "💪 Thật tuyệt vời! Bạn đang ở trong Top 10 cao nhất bảng xếp hạng!";
  }

  return (
    <div className="bg-gradient-to-r from-amber-500/10 via-[#F7ECE1] to-orange-500/10 rounded-2xl p-4 md:p-6 border-2 border-[#C1762A]/40 shadow-sm mb-6 relative overflow-hidden">
      {/* Background glow watermark */}
      <div className="absolute -right-8 -bottom-8 opacity-10 pointer-events-none text-[#8C4905]">
        <Flame size={160} />
      </div>

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
        {/* Profile & Rank */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl overflow-hidden border-2 border-[#C1762A] shadow-md bg-white">
              <img
                src={
                  currentUserEntry.avatar ||
                  `https://api.dicebear.com/7.x/bottts/svg?seed=${currentUserEntry.student_id}`
                }
                alt={currentUserEntry.display_name}
                className="w-full h-full object-cover"
              />
            </div>
            <span className="absolute -bottom-1 -right-1 bg-[#8C4905] text-white text-[10px] font-black px-1.5 py-0.5 rounded-md shadow-xs">
              #{currentUserEntry.rank}
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-extrabold text-[#8C4905] text-lg">
                {currentUserEntry.display_name} (Bạn)
              </h4>
              <span className="bg-[#C1762A] text-white text-xs font-bold px-2 py-0.5 rounded-full">
                Hạng #{currentUserEntry.rank} / {totalParticipants}
              </span>
            </div>
            <p className="text-xs md:text-sm text-stone-600 mt-0.5 font-medium">
              {motivationalMessage}
            </p>
          </div>
        </div>

        {/* Streak Stats */}
        <div className="flex items-center gap-3 sm:gap-4 shrink-0 bg-white/80 backdrop-blur-xs p-3 rounded-xl border border-[#F1CCA6]">
          <div className="text-center px-2">
            <div className="flex items-center justify-center gap-1 text-amber-600">
              <Trophy size={18} className="fill-current text-amber-500" />
              <span className="font-extrabold text-lg md:text-xl text-[#8C4905] tabular-nums">
                {maxStreak}
              </span>
            </div>
            <span className="text-[11px] font-bold text-amber-800">Kỷ lục</span>
          </div>

          <div className="h-8 w-px bg-stone-200" />

          <div className="text-center px-2">
            <div className="flex items-center justify-center gap-1 text-[#C1762A]">
              <Flame size={18} className="fill-current text-orange-500" />
              <span className="font-extrabold text-lg md:text-xl text-[#8C4905] tabular-nums">
                {streak}
              </span>
            </div>
            <span className="text-[11px] font-semibold text-stone-500">Chuỗi hiện tại</span>
          </div>

          <div className="h-8 w-px bg-stone-200" />

          <div className="text-center px-2">
            <div className="flex items-center justify-center gap-1">
              <span className="text-base">{milestone.emoji}</span>
              <span className="font-bold text-xs text-[#8C4905] truncate max-w-[80px]">
                {milestone.name}
              </span>
            </div>
            <span className="text-[11px] font-semibold text-stone-500">Cấp lửa</span>
          </div>
        </div>
      </div>

      {/* Progress to Next Milestone */}
      {nextMilestone && (
        <div className="mt-4 pt-4 border-t border-[#F1CCA6]/60 relative z-10">
          <div className="flex items-center justify-between text-xs mb-1.5 font-semibold">
            <span className="text-[#8C4905] flex items-center gap-1.5">
              <Target size={14} className="text-[#C1762A]" />
              Tiếp theo: <strong className="text-orange-600">{nextMilestone.name}</strong> ({nextMilestone.emoji})
            </span>
            <span className="text-[#C1762A]">
              Còn <strong>{daysRemaining}</strong> ngày nữa
            </span>
          </div>

          <div className="w-full h-2.5 bg-stone-200/80 rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
