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
        label: "Mới bắt đầu",
        color: "text-stone-700 bg-stone-50 border-stone-200",
      };
    }
    if (score >= 80) {
      return {
        label: "Tự lập xuất sắc",
        color: "text-emerald-700 bg-emerald-50 border-emerald-200",
      };
    }
    if (score >= 60) {
      return {
        label: "Tự lập tốt",
        color: "text-amber-800 bg-amber-50 border-amber-200",
      };
    }
    if (score >= 40) {
      return {
        label: "Đang tiến bộ",
        color: "text-orange-800 bg-orange-50 border-orange-200",
      };
    }
    return {
      label: "Cần rèn luyện thêm",
      color: "text-rose-800 bg-rose-50 border-rose-200",
    };
  };

  const levelInfo = getLevelBadge(averageScore);

  return (
    <div
      className={cn(
        "rounded-xl bg-white p-2.5 border border-[#F1CCA6]/70 shadow-2xs transition-all duration-200 hover:border-[#C1762A]/40",
        className
      )}
    >
      {/* Header gọn gàng: Tiêu đề + Điểm số trên cùng 1 hàng */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5 min-w-0">
          <div className="w-5 h-5 rounded-md bg-[#F7ECE1] flex items-center justify-center text-[#8C4905] shrink-0">
            {averageScore >= 80 ? (
              <Trophy className="w-3 h-3 text-[#C1762A]" />
            ) : averageScore >= 60 ? (
              <Award className="w-3 h-3 text-[#C1762A]" />
            ) : (
              <Sparkles className="w-3 h-3 text-[#C1762A]" />
            )}
          </div>
          <span className="text-[11px] font-bold text-stone-900 truncate">
            Điểm tự lực
          </span>
        </div>

        {/* Điểm số */}
        <div className="text-right shrink-0">
          <span className="text-sm font-extrabold text-[#8C4905] tabular-nums tracking-tight">
            {isLoading ? "--" : averageScore}
          </span>
          <span className="text-[10px] font-semibold text-stone-400 ml-0.5">/100</span>
        </div>
      </div>

      {/* Progress Bar siêu gọn */}
      <div className="w-full h-1.5 bg-[#F7ECE1] rounded-full overflow-hidden mb-1.5">
        <div
          className="h-full rounded-full bg-[#C1762A] transition-all duration-500 ease-out"
          style={{ width: `${Math.min(100, Math.max(averageScore > 0 ? averageScore : 0, 0))}%` }}
        />
      </div>

      {/* Footer nhỏ gọn */}
      <div className="flex items-center justify-between text-[10px] leading-none">
        <span
          className={cn(
            "inline-flex items-center px-1.5 py-0.5 rounded font-medium text-[9.5px]",
            averageScore >= 80
              ? "bg-emerald-50 text-emerald-700"
              : averageScore >= 60
              ? "bg-amber-50 text-amber-700"
              : "bg-stone-100 text-stone-600"
          )}
        >
          {levelInfo.label.replace(/[^\p{L}\s]/gu, "").trim()}
        </span>

        <span className="text-[10px] font-medium text-stone-500 tabular-nums">
          {isLoading ? (
            "--"
          ) : totalCompleted > 0 ? (
            <>
              <strong className="text-stone-700 font-semibold">{totalCompleted}</strong> bài xong
            </>
          ) : (
            "0 bài"
          )}
        </span>
      </div>

      {/* Thông báo điểm mới về real-time */}
      {recentGain && (
        <div className="mt-2.5 pt-2 border-t border-stone-100 flex items-center justify-between animate-in fade-in slide-in-from-top-1 duration-300">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>{recentGain.text}</span>
          </div>
          <span className="text-[10px] text-stone-400 font-medium">Đã cập nhật</span>
        </div>
      )}
    </div>
  );
}
