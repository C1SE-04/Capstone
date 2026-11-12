/**
 * File: components/dashboard/LeaderboardTable.tsx
 * Mô tả: Bảng danh sách xếp hạng chuỗi ngày học chi tiết - US 8.2 & US 9.4 (T9.14).
 * - Danh sách học sinh với thứ hạng, avatar, display_name (ẩn danh an toàn), khối lớp,
 *   cấp độ ngọn lửa 7 mốc, kỷ lục chuỗi ngày, và chuỗi hiện tại.
 * - Hàng của học sinh hiện tại được đánh dấu nổi bật với nhãn "Bạn".
 * - Hiển thị empty state thân thiện khi tìm kiếm không có kết quả: "Không tìm thấy học sinh nào phù hợp".
 */

"use client";

import React from "react";
import { StreakLeaderboardItem } from "@/types/leaderboard";
import { getStreakMilestone } from "@/lib/streakMilestones";
import { MilestoneFlameIcon } from "@/components/dashboard/MilestoneFlameIcon";
import { Flame, Trophy, Crown, Award, Medal, ShieldCheck, Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface LeaderboardTableProps {
  items: StreakLeaderboardItem[];
  searchQuery?: string;
}

export function LeaderboardTable({ items, searchQuery }: LeaderboardTableProps) {
  if (!items || items.length === 0) {
    if (searchQuery && searchQuery.trim()) {
      return (
        <div className="bg-white rounded-2xl p-8 border border-[#F1CCA6] text-center shadow-xs animate-in fade-in duration-200">
          <div className="w-16 h-16 mx-auto mb-3 rounded-full bg-[#F7ECE1] flex items-center justify-center text-[#C1762A]">
            <Search size={32} />
          </div>
          <h4 className="text-base font-bold text-[#8C4905]">Không tìm thấy học sinh nào phù hợp</h4>
          <p className="text-sm text-stone-500 mt-1">
            Không có học sinh nào khớp với từ khóa &ldquo;{searchQuery}&rdquo;. Hãy thử tìm với tên khác nhé!
          </p>
        </div>
      );
    }

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
        <div className="w-8 h-8 rounded-full bg-[#E7E5E4] text-[#44403C] font-black flex items-center justify-center shadow-xs ring-2 ring-[#D6D3D1]">
          <Award size={18} className="text-[#57534E]" />
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
        <div className="w-8 h-8 rounded-full bg-[#F1CCA6]/60 text-[#8C4905] font-black text-sm flex items-center justify-center tabular-nums">
          #{rank}
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-full text-[#7A3E04]/60 font-bold text-sm flex items-center justify-center tabular-nums">
        {rank}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-3xl border border-[#F1CCA6] shadow-sm overflow-hidden">
      {/* Table Header */}
      <div className="hidden sm:grid sm:grid-cols-12 px-6 py-4 bg-[#F1CCA6]/30 border-b border-[#F1CCA6] text-xs font-bold text-[#8C4905] uppercase tracking-wider">
        <div className="col-span-1 text-center">Hạng</div>
        <div className="col-span-4">Học sinh</div>
        <div className="col-span-3 text-center">Cấp độ ngọn lửa</div>
        <div className="col-span-2 text-center">Kỷ lục</div>
        <div className="col-span-2 text-right">Chuỗi ngày</div>
      </div>

      {/* Rows */}
      <div className="divide-y divide-[#F1CCA6]/40">
        {items.map((item) => {
          const record = item.max_streak ?? item.streak_days ?? 0;
          const milestone = getStreakMilestone(record);

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
              <div className="flex items-center gap-3 sm:col-span-4 w-full">
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

              {/* Cột Cấp độ ngọn lửa (dựa trên Kỷ lục đạt được) - Vector thực tế thay vì emoji */}
              <div className="sm:col-span-3 sm:text-center w-full flex sm:justify-center items-center">
                <div
                  className={cn(
                    "inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs border transition-transform",
                    record >= 3 ? "font-bold shadow-2xs hover:scale-102" : "font-medium opacity-85",
                    milestone.badgeBg,
                    milestone.badgeBorder,
                    milestone.textColor
                  )}
                >
                  <MilestoneFlameIcon record={record} className={record >= 3 ? "w-5 h-5" : "w-4 h-4"} />
                  <span>{milestone.name}</span>
                </div>
              </div>

              {/* Cột Kỷ lục (Tiêu chí xếp hạng chính) */}
              <div className="sm:col-span-2 sm:text-center w-full flex sm:justify-center items-center justify-between">
                <span className="sm:hidden text-xs font-bold text-[#8C4905]">Kỷ lục:</span>
                <div className="inline-flex items-center gap-1.5 bg-gradient-to-r from-amber-100 to-amber-50 px-3 py-1 rounded-xl border border-amber-300 shadow-2xs">
                  <Trophy size={14} className="text-amber-600 fill-amber-400 shrink-0" />
                  <span className="font-extrabold text-sm sm:text-base text-[#8C4905] tabular-nums">
                    {record}
                  </span>
                  <span className="text-xs font-bold text-amber-800">ngày</span>
                </div>
              </div>

              {/* Cột Chuỗi ngày hiện tại */}
              <div className="sm:col-span-2 sm:text-right w-full flex sm:justify-end items-center justify-between pt-1 sm:pt-0 border-t sm:border-0 border-stone-100">
                <span className="sm:hidden text-xs font-semibold text-[#8C4905]">Chuỗi hiện tại:</span>
                <div className="inline-flex items-center gap-1.5 bg-[#F7ECE1] px-2.5 py-1 rounded-xl border border-[#F1CCA6]">
                  <Flame size={14} className={cn("fill-current", item.streak_days > 0 ? "text-orange-500" : "text-stone-300")} />
                  <span className="font-bold text-sm text-[#8C4905] tabular-nums">
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
