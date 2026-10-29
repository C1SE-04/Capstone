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
  Lock,
  X,
} from "lucide-react";
import {
  StreakLeaderboardResponse,
  StreakLeaderboardItem,
  GradeFilter,
} from "@/types/leaderboard";
import { STREAK_MILESTONES } from "@/lib/streakMilestones";
import { FigmaStreakFlame, STREAK_TIERS } from "@/components/chat/StreakBadge";
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

  // Tính số ngày streak đã đạt được cao nhất của học sinh (để mở khóa các mốc)
  const userStreak = Math.max(
    currentUserEntry?.max_streak ?? 0,
    currentUserEntry?.streak_days ?? 0,
    (session?.user as any)?.streak_days ?? 0,
    (session?.user as any)?.max_streak ?? 0
  );
  const unlockedCount = STREAK_MILESTONES.slice(1).filter((m) => userStreak >= m.minDays).length;

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

      {/* Guide 7 Mốc Lửa Tiến Hóa (Collapsible Showcase - Gọn gàng, trải dài 1 hàng không xuống dòng) */}
      {showMilestonesGuide && (
        <div className="bg-white rounded-2xl p-3.5 sm:p-4.5 border border-[#F1CCA6] shadow-sm mb-6 animate-in slide-in-from-top-3 duration-200">
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-extrabold text-[#8C4905] text-sm sm:text-base flex items-center gap-1.5">
                <Sparkles size={16} className="text-amber-500 shrink-0" />
                Hệ thống 7 mốc tiến hóa Ngọn Lửa Streak
              </h3>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]">
                Kỷ lục của bạn: <strong>{userStreak}</strong> ngày ({unlockedCount}/7 mốc đã mở)
              </span>
            </div>
            <button
              onClick={() => setShowMilestonesGuide(false)}
              className="text-stone-400 hover:text-stone-700 hover:bg-stone-100 p-1.5 rounded-xl transition-colors shrink-0"
              title="Đóng"
            >
              <X size={16} />
            </button>
          </div>
          <p className="text-xs text-stone-500 mb-3">
            Học bài và giải toán kiên trì mỗi ngày cùng Thầy Socratic để thắp sáng và mở khóa các mốc ngọn lửa:
          </p>

          {/* Dải 7 mốc lửa trải dài trên 1 hàng không xuống dòng */}
          <div className="overflow-x-auto pb-1.5 pt-0.5 -mx-1 px-1 scrollbar-none">
            <div className="grid grid-cols-7 gap-2 min-w-[560px] sm:min-w-0">
              {STREAK_MILESTONES.slice(1).map((m) => {
                const isUnlocked = userStreak >= m.minDays;
                const tierConfig = STREAK_TIERS.find((t) => t.minDays === m.minDays);

                if (isUnlocked) {
                  return (
                    <div
                      key={m.tier}
                      className={cn(
                        "group relative p-2.5 rounded-xl border flex flex-col items-center justify-between min-h-[114px] text-center shadow-xs transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-pointer",
                        m.badgeBg,
                        m.badgeBorder
                      )}
                      title={`${m.name}: ${m.description} (Đã mở khóa!)`}
                    >
                      {/* Icon lửa SVG ở trên */}
                      <div className="w-10 h-10 sm:w-11 sm:h-11 flex items-center justify-center relative">
                        {tierConfig && (
                          <FigmaStreakFlame
                            tier={tierConfig}
                            className="w-8 h-8 sm:w-9 sm:h-9 transition-transform duration-200 group-hover:scale-110"
                          />
                        )}
                      </div>

                      {/* Số ngày & tên mốc ở dưới */}
                      <div className="flex flex-col items-center w-full mt-1">
                        <span className="font-black text-xs sm:text-sm text-stone-800 tracking-tight leading-tight">
                          {m.minDays} ngày
                        </span>
                        <span
                          className={cn(
                            "text-[10px] sm:text-[11px] font-bold truncate max-w-full block leading-tight mt-0.5",
                            m.textColor
                          )}
                        >
                          {m.name}
                        </span>
                        <span className="text-[9px] font-bold text-emerald-700 bg-emerald-100/90 border border-emerald-300/60 px-1.5 py-0.5 rounded-full mt-1.5 leading-none shadow-2xs">
                          Đã mở
                        </span>
                      </div>
                    </div>
                  );
                }

                return (
                  <div
                    key={m.tier}
                    className="relative p-2.5 rounded-xl border border-stone-200/90 bg-stone-100/90 flex flex-col items-center justify-between min-h-[114px] text-center select-none overflow-hidden"
                    title={`Cần đạt chuỗi ${m.minDays} ngày để mở khóa (Hiện tại: ${userStreak}/${m.minDays} ngày)`}
                  >
                    {/* Khung skeleton xám với icon cái khóa ở phía trước */}
                    <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-stone-200/80 border border-stone-300/60 flex items-center justify-center relative shadow-2xs">
                      {tierConfig && (
                        <div className="w-6 h-6 sm:w-7 sm:h-7 opacity-15 grayscale blur-[1.5px] pointer-events-none">
                          <FigmaStreakFlame tier={tierConfig} className="w-full h-full" />
                        </div>
                      )}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-6 h-6 rounded-lg bg-white/95 shadow-xs border border-stone-200 flex items-center justify-center">
                          <Lock size={12} className="text-stone-500" />
                        </div>
                      </div>
                    </div>

                    {/* Số ngày & tên mốc ở dưới */}
                    <div className="flex flex-col items-center w-full mt-1">
                      <span className="font-extrabold text-xs sm:text-sm text-stone-400 tracking-tight leading-tight">
                        {m.minDays} ngày
                      </span>
                      <span className="text-[10px] sm:text-[11px] font-medium text-stone-400 truncate max-w-full block leading-tight mt-0.5">
                        {m.name}
                      </span>
                      <span className="text-[9px] font-medium text-stone-400 bg-stone-200/80 px-1.5 py-0.5 rounded-full mt-1.5 leading-none">
                        Khóa
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
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
