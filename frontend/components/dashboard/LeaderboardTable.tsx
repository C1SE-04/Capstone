/**
 * File: components/dashboard/LeaderboardTable.tsx
 * Mô tả: Bảng danh sách xếp hạng chuỗi ngày học chi tiết - US 8.2 & Task 8.15.
 * - Danh sách học sinh với thứ hạng, avatar, display_name (ẩn danh an toàn), khối lớp,
 *   cấp độ ngọn lửa 7 mốc, kỷ lục chuỗi ngày, và chuỗi hiện tại.
 * - Hàng của học sinh hiện tại được đánh dấu nổi bật với nhãn "Bạn".
 */

"use client";

import React from "react";
import { StreakLeaderboardItem } from "@/types/leaderboard";
import { getStreakMilestone } from "@/lib/streakMilestones";
import { Flame, Trophy, Crown, Award, Medal, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

interface LeaderboardTableProps {
  items: StreakLeaderboardItem[];
}

export function LeaderboardTable({ items }: LeaderboardTableProps) {
  if (!items || items.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-8 border border-[#F1CCA6] text-center shadow-xs">
        <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-[#F7ECE1] flex items-center justify-center text-[#C1762A]">
          <Flame size={32} />
        </div>
        <h4 className="text-base font-bold text-[#8C4905]">Chưa có dữ liệu xếp hạng</h4>
        <p className="text-sm text-stone-500 mt-1">
          Hãy là người đầu tiên bắt đầu chuỗi ngày học để ghi danh trên bảng vàng!
        </p>
      </div>
    );
  }

  const renderRankBadge = (rank: number) => {
    if (rank === 1) {
      return (
        <div className="w-8 h-8 rounded-full bg-amber-400 text-amber-950 font-black flex items-center justify-center shadow-xs ring-2 ring-amber-300">
          <Crown size={18} className="fill-current text-amber-950" />
        </div>
      );
    }
    if (rank === 2) {
      return (
        <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-800 font-black flex items-center justify-center shadow-xs ring-2 ring-slate-300">
          <Award size={18} className="text-slate-700" />
        </div>
      );
    }
    if (rank === 3) {
      return (
        <div className="w-8 h-8 rounded-full bg-amber-700/80 text-white font-black flex items-center justify-center shadow-xs ring-2 ring-amber-600/50">
          <Award size={18} className="text-amber-100" />
        </div>
      );
    }
    if (rank <= 10) {
      return (
        <div className="w-8 h-8 rounded-full bg-[#F1CCA6]/60 text-[#8C4905] font-black text-sm flex items-center justify-center">
          #{rank}
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-full text-stone-400 font-bold text-sm flex items-center justify-center">
        {rank}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-3xl border border-[#F1CCA6] shadow-sm overflow-hidden">
      {/* Table Header */}
      <div className="hidden sm:grid sm:grid-cols-12 px-6 py-4 bg-[#F1CCA6]/30 border-b border-[#F1CCA6] text-xs font-bold text-[#8C4905] uppercase tracking-wider">
        <div className="col-span-1 text-center">Hạng</div>
        <div className="col-span-5">Học sinh</div>
        <div className="col-span-3 text-center">Cấp độ ngọn lửa</div>
        <div className="col-span-1 text-center">Kỷ lục</div>
        <div className="col-span-2 text-right">Chuỗi ngày</div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-[#F1CCA6]/40">
        {items.map((item) => {
          const milestone = getStreakMilestone(item.streak_days);

          return (
            <div
              key={item.student_id}
              className={cn(
                "flex flex-col sm:grid sm:grid-cols-12 items-start sm:items-center px-4 sm:px-6 py-3.5 transition-colors gap-2 sm:gap-0",
                item.is_current_user
                  ? "bg-amber-50/70 hover:bg-amber-100/60 ring-2 ring-inset ring-amber-400/80"
                  : "hover:bg-[#F7ECE1]/40"
              )}
            >
              {/* Cột Thứ hạng */}
              <div className="flex items-center gap-3 sm:col-span-1 sm:justify-center">
                {renderRankBadge(item.rank)}
                <span className="sm:hidden text-xs font-bold text-stone-400">
                  Hạng #{item.rank}
                </span>
              </div>

              {/* Cột Học sinh */}
              <div className="flex items-center gap-3 sm:col-span-5 w-full">
                <div className="relative shrink-0">
                  <div className="w-10 h-10 rounded-full overflow-hidden bg-stone-100 border border-[#F1CCA6]">
                    <img
                      src={
                        item.avatar ||
                        `https://api.dicebear.com/7.x/bottts/svg?seed=${item.student_id}`
                      }
                      alt={item.display_name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  {item.rank <= 3 && (
                    <span className="absolute -top-1 -right-1 text-xs">
                      {item.rank === 1 ? "🥇" : item.rank === 2 ? "🥈" : "🥉"}
                    </span>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-sm sm:text-base text-[#8C4905] truncate">
                      {item.display_name}
                    </p>
                    {item.is_current_user && (
                      <span className="bg-[#8C4905] text-white text-[10px] font-black px-2 py-0.5 rounded-full shrink-0">
                        Bạn
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    {item.grade ? (
                      <span className="text-[11px] font-semibold text-[#C1762A] bg-[#F7ECE1] px-1.5 py-0.2 rounded">
                        Lớp {item.grade}
                      </span>
                    ) : (
                      <span className="text-[11px] text-stone-400">Học sinh</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Cột Cấp độ ngọn lửa */}
              <div className="sm:col-span-3 sm:text-center w-full flex sm:justify-center items-center">
                <div
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold border",
                    milestone.badgeBg,
                    milestone.badgeBorder,
                    milestone.textColor
                  )}
                >
                  <Flame size={14} className={cn("fill-current", milestone.flameColor)} />
                  <span>
                    {milestone.emoji} {milestone.name}
                  </span>
                </div>
              </div>

              {/* Cột Kỷ lục (Max Streak) */}
              <div className="sm:col-span-1 sm:text-center text-xs font-semibold text-stone-600 flex sm:justify-center items-center gap-1">
                <Trophy size={13} className="text-amber-500 sm:hidden" />
                <span className="sm:hidden text-stone-400">Kỷ lục:</span>
                <span className="tabular-nums font-bold text-stone-700">
                  {item.max_streak || item.streak_days}
                </span>
                <span className="sm:hidden text-stone-400">ngày</span>
              </div>

              {/* Cột Chuỗi ngày hiện tại */}
              <div className="sm:col-span-2 sm:text-right w-full flex sm:justify-end items-center justify-between pt-1 sm:pt-0 border-t sm:border-0 border-stone-100">
                <span className="sm:hidden text-xs font-semibold text-[#8C4905]">Chuỗi hiện tại:</span>
                <div className="inline-flex items-center gap-1.5 bg-[#F7ECE1] px-3 py-1 rounded-xl border border-[#F1CCA6]">
                  <Flame size={16} className="fill-current text-orange-500" />
                  <span className="font-extrabold text-base text-[#8C4905] tabular-nums">
                    {item.streak_days}
                  </span>
                  <span className="text-xs font-semibold text-stone-600">ngày</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
