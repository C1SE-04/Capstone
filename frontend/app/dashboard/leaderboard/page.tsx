/**
 * File: app/dashboard/leaderboard/page.tsx
 * Mô tả: Trang Bảng Xếp Hạng Chuỗi Ngày Học (Streak Leaderboard) - US 8.2 & Task 8.15.
 * - Hiển thị Top học sinh có chuỗi ngày học liên tục cao nhất.
 * - Bộ lọc tối giản & chuẩn xác: Lọc theo Khối lớp (Lớp 4 -> 9) hoặc xem Toàn Server.
 * - Bục vinh danh Top 3 (Gold, Silver, Bronze Podium).
 * - Thẻ vị trí xếp hạng của học sinh hiện tại (YourRankCard).
 * - Bảng danh sách thứ hạng chi tiết và giải thích 7 mốc tiến hóa ngọn lửa.
 * - Bảo vệ quyền riêng tư: 100% không lộ email hay thông tin cá nhân nhạy cảm.
 */

"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import {
  Trophy,
  Flame,
  Users,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  ChevronRight,
  Info,
} from "lucide-react";
import {
  StreakLeaderboardResponse,
  StreakLeaderboardItem,
  GradeFilter,
} from "@/types/leaderboard";
import { STREAK_MILESTONES } from "@/lib/streakMilestones";
import { LeaderboardPodium } from "@/components/dashboard/LeaderboardPodium";
import { YourRankCard } from "@/components/dashboard/YourRankCard";
import { LeaderboardTable } from "@/components/dashboard/LeaderboardTable";
import { authFetch } from "@/lib/authFetch";
import { cn } from "@/lib/utils";

const GRADE_OPTIONS: { label: string; value: GradeFilter }[] = [
  { label: "Toàn Server", value: "ALL" },
  { label: "Khối 4", value: 4 },
  { label: "Khối 5", value: 5 },
  { label: "Khối 6", value: 6 },
  { label: "Khối 7", value: 7 },
  { label: "Khối 8", value: 8 },
  { label: "Khối 9", value: 9 },
];

export default function LeaderboardPage() {
  const { data: session } = useSession();
  const [selectedGrade, setSelectedGrade] = useState<GradeFilter>("ALL");
  const [data, setData] = useState<StreakLeaderboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showMilestonesGuide, setShowMilestonesGuide] = useState<boolean>(false);

  // Khởi tạo bộ lọc theo khối lớp của học sinh nếu có
  useEffect(() => {
    const studentGrade = (session?.user as any)?.grade_level;
    if (studentGrade && studentGrade >= 4 && studentGrade <= 9) {
      setSelectedGrade(studentGrade as GradeFilter);
    }
  }, [session]);

  // Fetch API bảng xếp hạng
  const fetchLeaderboard = useCallback(
    async (grade: GradeFilter, isManualRefresh = false) => {
      if (isManualRefresh) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setErrorMessage(null);

      try {
        const queryParams = new URLSearchParams();
        if (grade !== "ALL") {
          queryParams.set("grade", grade.toString());
        }
        queryParams.set("limit", "50");

        // Gọi qua BFF proxy /api/metrics/streak-leaderboard
        const res = await fetch(`/api/metrics/streak-leaderboard?${queryParams.toString()}`);

        if (res.ok) {
          const json: StreakLeaderboardResponse = await res.json();
          setData(json);
        } else if (res.status === 401) {
          // Thử fallback trực tiếp authFetch tới Backend
          const BACKEND_URL =
            process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
          const fallbackRes = await authFetch(
            `${BACKEND_URL}/metrics/streak-leaderboard?${queryParams.toString()}`
          );
          if (fallbackRes.ok) {
            const fallbackJson: StreakLeaderboardResponse = await fallbackRes.json();
            setData(fallbackJson);
          } else {
            setErrorMessage("Vui lòng đăng nhập lại để xem bảng xếp hạng.");
          }
        } else {
          const errData = await res.json().catch(() => ({}));
          setErrorMessage(
            errData.error || `Không thể tải bảng xếp hạng (Mã lỗi ${res.status}).`
          );
        }
      } catch (err: any) {
        console.error("Lỗi tải bảng xếp hạng:", err);
        setErrorMessage("Lỗi kết nối tới máy chủ. Vui lòng kiểm tra lại mạng!");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchLeaderboard(selectedGrade);
  }, [selectedGrade, fetchLeaderboard]);

  const handleGradeChange = (grade: GradeFilter) => {
    setSelectedGrade(grade);
  };

  const handleRefresh = () => {
    fetchLeaderboard(selectedGrade, true);
  };

  const leaderboardItems = data?.leaderboard || [];
  const topThree = leaderboardItems.slice(0, 3);
  const totalParticipants = data?.total_participants || 0;
  const currentUserEntry = data?.current_user_entry;

  return (
    <div className="max-w-6xl mx-auto flex flex-col min-h-full pb-12 animate-in fade-in duration-500">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="p-2 rounded-2xl bg-[#C1762A]/15 text-[#8C4905]">
              <Trophy size={26} className="text-[#C1762A]" />
            </span>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#8C4905] tracking-tight">
              Bảng Xếp Hạng Chuỗi Học Tập
            </h1>
          </div>
          <p className="text-sm md:text-base text-[#C1762A] font-medium">
            Xếp hạng theo kỷ lục chuỗi ngày học bền bỉ nhất — Càng kiên trì, ngọn lửa càng rực sáng!
          </p>
        </div>

        {/* Nút Refresh & Nút Hướng dẫn */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => setShowMilestonesGuide(!showMilestonesGuide)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold bg-white text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F7ECE1]/60 transition-colors shadow-2xs"
          >
            <Info size={16} className="text-[#C1762A]" />
            <span>7 Mốc Lửa</span>
          </button>

          <button
            onClick={handleRefresh}
            disabled={isLoading || isRefreshing}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold bg-[#C1762A] text-white hover:bg-[#8C4905] disabled:opacity-50 transition-all shadow-xs active:scale-95"
            title="Làm mới dữ liệu"
          >
            <RefreshCw
              size={16}
              className={cn("transition-transform", isRefreshing && "animate-spin")}
            />
            <span>{isRefreshing ? "Đang tải..." : "Làm mới"}</span>
          </button>
        </div>
      </div>

      {/* Guide 7 Mốc Lửa Tiến Hóa (Collapsible) */}
      {showMilestonesGuide && (
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm mb-6 animate-in slide-in-from-top-3 duration-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-extrabold text-[#8C4905] text-sm md:text-base flex items-center gap-2">
              <Sparkles size={18} className="text-amber-500" />
              Hệ thống 7 mốc tiến hóa Ngọn Lửa Streak
            </h3>
            <button
              onClick={() => setShowMilestonesGuide(false)}
              className="text-stone-400 hover:text-stone-600 text-xs font-semibold"
            >
              Đóng
            </button>
          </div>
          <p className="text-xs text-stone-600 mb-4">
            Mỗi ngày bạn giải toán hoặc học bài cùng Thầy Socratic, chuỗi ngày học sẽ tăng lên 1 và ngọn lửa sẽ tiến hóa qua các mốc kỳ diệu:
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-4 gap-2.5">
            {STREAK_MILESTONES.slice(1).map((m) => (
              <div
                key={m.tier}
                className={cn(
                  "p-2.5 rounded-xl border flex flex-col justify-between",
                  m.badgeBg,
                  m.badgeBorder
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-base">{m.emoji}</span>
                  <span className="text-[10px] font-black px-1.5 py-0.5 rounded bg-white/80 text-stone-700">
                    {m.minDays} ngày+
                  </span>
                </div>
                <p className={cn("font-bold text-xs", m.textColor)}>{m.name}</p>
                <p className="text-[10px] text-stone-500 mt-1 line-clamp-2">{m.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grade Filter Bar */}
      <div className="bg-white rounded-2xl p-2.5 border border-[#F1CCA6] shadow-xs mb-6 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 px-1 max-w-full">
          {GRADE_OPTIONS.map((opt) => {
            const isActive = selectedGrade === opt.value;
            return (
              <button
                key={opt.label}
                onClick={() => handleGradeChange(opt.value)}
                className={cn(
                  "px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold whitespace-nowrap transition-all duration-150 select-none",
                  isActive
                    ? "bg-[#C1762A] text-white shadow-xs scale-102"
                    : "text-[#8C4905] hover:bg-[#F7ECE1] hover:text-[#CB6600]"
                )}
              >
                {opt.label}
              </button>
            );
          })}
        </div>

        {/* Tổng số người tham gia */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 bg-[#F7ECE1]/60 rounded-xl text-xs font-semibold text-[#8C4905]">
          <Users size={14} className="text-[#C1762A]" />
          <span>
            <strong>{totalParticipants}</strong> học sinh
          </span>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="space-y-4 animate-pulse">
          <div className="h-64 bg-white/60 rounded-3xl border border-[#F1CCA6]" />
          <div className="h-28 bg-white/60 rounded-2xl border border-[#F1CCA6]" />
          <div className="h-80 bg-white/60 rounded-3xl border border-[#F1CCA6]" />
        </div>
      )}

      {/* Error State */}
      {!isLoading && errorMessage && (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center text-rose-800 my-4 shadow-xs">
          <p className="font-bold mb-2">Đã xảy ra sự cố</p>
          <p className="text-sm text-rose-600 mb-4">{errorMessage}</p>
          <button
            onClick={() => fetchLeaderboard(selectedGrade)}
            className="px-4 py-2 bg-rose-600 text-white rounded-xl text-sm font-bold hover:bg-rose-700 transition-colors"
          >
            Thử lại
          </button>
        </div>
      )}

      {/* Content when loaded */}
      {!isLoading && !errorMessage && (
        <>
          {/* Top 3 Podium */}
          {topThree.length > 0 && <LeaderboardPodium topThree={topThree} />}

          {/* Current User Standing Card */}
          <YourRankCard
            currentUserEntry={currentUserEntry}
            totalParticipants={totalParticipants}
          />

          {/* Detailed Leaderboard Table */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3 px-1">
              <h3 className="text-lg font-extrabold text-[#8C4905] flex items-center gap-2">
                <span className="bg-[#C1762A] w-2 h-6 rounded-full inline-block" />
                Danh sách chi tiết
                <span className="text-xs font-semibold text-stone-500">
                  (Top {leaderboardItems.length})
                </span>
              </h3>
            </div>

            <LeaderboardTable items={leaderboardItems} />
          </div>

          {/* Privacy Footnote */}
          <div className="flex items-center justify-center gap-2 text-xs text-[#8C4905]/70 bg-white/50 backdrop-blur-xs p-3 rounded-xl border border-[#F1CCA6]/50">
            <ShieldCheck size={16} className="text-emerald-600 shrink-0" />
            <span>
              <strong>Bảo mật thông tin:</strong> Tên hiển thị được viết tắt và ảnh đại diện ngẫu nhiên
              nhằm bảo vệ quyền riêng tư của học sinh theo tiêu chuẩn Sprint 8.
            </span>
          </div>
        </>
      )}
    </div>
  );
}
