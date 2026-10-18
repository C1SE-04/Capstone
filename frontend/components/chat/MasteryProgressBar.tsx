"use client";

/**
 * File: components/chat/MasteryProgressBar.tsx
 * Task: T6.5 – US 6.1 (Đo lường Điểm Tự Lực & Dashboard Phụ Huynh Nâng Cao)
 *
 * Mô tả:
 *   Thanh tiến trình Mastery hiển thị trên Sidebar Chat:
 *   - Hiển thị điểm số tự lực (Independence / Mastery Score) trung bình và số bài đã hoàn thành.
 *   - Lắng nghe sự kiện toàn cục "INDEPENDENCE_SCORE_UPDATED" để cập nhật real-time ngay khi
 *     học sinh bấm "Đã hiểu" và backend trả về điểm số mới.
 *   - Có animation tăng điểm, huy hiệu mức độ tự lập và thông báo điểm bài vừa hoàn thành.
 */

import { useState, useEffect, useCallback } from "react";
import { Sparkles, Trophy, Award, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

export const INDEPENDENCE_SCORE_UPDATED_EVENT = "INDEPENDENCE_SCORE_UPDATED";

export interface IndependenceScorePayload {
  id?: string;
  score: number;
  hints_used?: number;
  not_understood_count?: number;
  evaluation?: string;
  created_at?: string;
}

interface MasteryProgressBarProps {
  className?: string;
}

export function MasteryProgressBar({ className }: MasteryProgressBarProps) {
  const [averageScore, setAverageScore] = useState<number>(0);
  const [totalCompleted, setTotalCompleted] = useState<number>(0);
  const [evaluationLevel, setEvaluationLevel] = useState<string>("Bắt đầu học để tính điểm");
  const [latestScore, setLatestScore] = useState<number | null>(null);
  const [recentGain, setRecentGain] = useState<{ score: number; text: string } | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Fetch dữ liệu tổng hợp ban đầu từ API
  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch("/api/independence/summary");
      if (res.ok) {
        const data = await res.json();
        setAverageScore(typeof data.average_score === "number" ? Math.round(data.average_score) : 0);
        setTotalCompleted(typeof data.total_completed === "number" ? data.total_completed : 0);
        if (data.evaluation_level) setEvaluationLevel(data.evaluation_level);
        if (data.latest_score !== undefined) setLatestScore(data.latest_score);
      }
    } catch (err) {
      console.warn("[MasteryProgressBar] Lỗi tải điểm tự lực:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // Lắng nghe sự kiện cập nhật điểm real-time khi học sinh bấm "Đã hiểu" (T6.4 -> T6.5)
  useEffect(() => {
    const handleScoreUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<IndependenceScorePayload>;
      const detail = customEvent.detail;
      if (!detail || typeof detail.score !== "number") return;

      const newScore = detail.score;
      setLatestScore(newScore);

      // Hiển thị pill chúc mừng điểm bài vừa xong trong 5 giây
      setRecentGain({
        score: newScore,
        text: `+${newScore}đ bài vừa xong!`,
      });

      // Tăng số bài hoàn thành tạm thời trong UI
      setTotalCompleted((prev) => prev + 1);

      // Đồng bộ lại dữ liệu chuẩn từ database
      setTimeout(() => {
        fetchSummary();
      }, 800);

      const timer = setTimeout(() => {
        setRecentGain(null);
      }, 5000);

      return () => clearTimeout(timer);
    };

    window.addEventListener(INDEPENDENCE_SCORE_UPDATED_EVENT, handleScoreUpdate);
    return () => {
      window.removeEventListener(INDEPENDENCE_SCORE_UPDATED_EVENT, handleScoreUpdate);
    };
  }, [fetchSummary]);

  // Xác định màu sắc và mức độ theo thang điểm tự lực từ DB
  const getLevelBadge = (score: number) => {
    if (totalCompleted === 0 && score === 0) {
      return {
        label: "Mới bắt đầu 🌱",
        color: "text-stone-700 bg-stone-50 border-stone-200",
      };
    }
    if (score >= 80) {
      return {
        label: "Tự lập xuất sắc 🌟",
        color: "text-emerald-700 bg-emerald-50 border-emerald-200",
      };
    }
    if (score >= 60) {
      return {
        label: "Tự lập tốt 👍",
        color: "text-amber-800 bg-amber-50 border-amber-200",
      };
    }
    if (score >= 40) {
      return {
        label: "Tự lập đang tiến bộ 📈",
        color: "text-orange-800 bg-orange-50 border-orange-200",
      };
    }
    return {
      label: "Cần tiến bộ 💡",
      color: "text-rose-800 bg-rose-50 border-rose-200",
    };
  };

  const levelInfo = getLevelBadge(averageScore);

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#FFFDF9] via-[#FAF1E6] to-[#F5E6D3] p-3.5 border border-[#F1CCA6] shadow-xs transition-all duration-300 hover:shadow-md group",
        className
      )}
    >
      {/* Họa tiết trang trí góc trên */}
      <div className="absolute -top-6 -right-6 w-16 h-16 bg-[#F7AD62]/15 rounded-full blur-xl pointer-events-none" />

      {/* Header: Icon + Tiêu đề + Điểm số */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-[#C1762A] to-[#F7AD62] flex items-center justify-center text-white shadow-xs">
            {averageScore >= 80 ? (
              <Trophy className="w-4 h-4 text-amber-100" />
            ) : averageScore >= 60 ? (
              <Award className="w-4 h-4 text-amber-100" />
            ) : (
              <Sparkles className="w-4 h-4 text-amber-100" />
            )}
          </div>
          <div>
            <span className="block text-[10px] font-bold text-[#8C4905]/70 uppercase tracking-wider leading-none">
              Tiến trình tự lực
            </span>
            <span className="text-xs font-black text-[#8C4905]">
              Mastery Score
            </span>
          </div>
        </div>

        {/* Điểm số */}
        <div className="text-right">
          <div className="flex items-baseline justify-end gap-0.5">
            <span className="text-base font-black text-[#8C4905] tabular-nums">
              {isLoading ? "--" : averageScore}
            </span>
            <span className="text-[10px] font-bold text-[#C1762A]">/100</span>
          </div>
        </div>
      </div>

      {/* Progress Bar với shimmer animation */}
      <div className="relative w-full h-2.5 bg-white/90 rounded-full overflow-hidden border border-[#F1CCA6]/60 p-[1.5px] shadow-inner mb-2">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[#F7AD62] via-[#E07A5F] to-[#C1762A] transition-all duration-1000 ease-out relative"
          style={{ width: `${Math.min(100, Math.max(averageScore > 0 ? averageScore : 4, 4))}%` }}
        >
          {/* Vệt sáng chuyển động */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/35 to-transparent animate-pulse" />
        </div>
      </div>

      {/* Thông tin mức độ & số bài hoàn thành */}
      <div className="flex items-center justify-between text-[11px] leading-tight">
        <span
          className={cn(
            "px-2 py-0.5 rounded-full font-bold border text-[10px] transition-all",
            levelInfo.color
          )}
        >
          {levelInfo.label}
        </span>

        <span className="text-[10px] font-semibold text-[#8C4905]/80 tabular-nums">
          {totalCompleted} bài xong
        </span>
      </div>

      {/* Thông báo điểm mới về real-time */}
      {recentGain && (
        <div className="mt-2 pt-1.5 border-t border-[#F1CCA6]/40 flex items-center justify-between animate-in fade-in slide-in-from-top-1 duration-300">
          <div className="flex items-center gap-1 text-[11px] font-bold text-emerald-700">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>{recentGain.text}</span>
          </div>
          <span className="text-[10px] text-[#8C4905]/60 font-medium">Đã lưu DB</span>
        </div>
      )}
    </div>
  );
}
