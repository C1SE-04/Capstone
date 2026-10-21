"use client";

import React, { useState, useEffect } from "react";
import Lottie from "lottie-react";
import { Flame, Trophy, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface StreakBadgeProps {
  /** Số ngày học liên tục (nếu không truyền sẽ tự fetch từ API) */
  streak?: number;
  /** Kỷ lục chuỗi ngày học */
  maxStreak?: number;
  /** Callback khi click vào badge */
  onClick?: () => void;
  className?: string;
  /** Đường dẫn file lottie tùy chỉnh (mặc định /lottie/streak_flame.json hoặc /lottie/flame.json) */
  lottieSrc?: string;
}

export function StreakBadge({
  streak: initialStreak,
  maxStreak: initialMaxStreak,
  onClick,
  className,
  lottieSrc = "/lottie/streak_flame.json",
}: StreakBadgeProps) {
  const [streak, setStreak] = useState<number>(initialStreak ?? 0);
  const [maxStreak, setMaxStreak] = useState<number>(initialMaxStreak ?? 0);
  const [lottieAnimation, setLottieAnimation] = useState<object | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  // Cập nhật khi props từ ngoài thay đổi
  useEffect(() => {
    if (initialStreak !== undefined) setStreak(initialStreak);
    if (initialMaxStreak !== undefined) setMaxStreak(initialMaxStreak);
  }, [initialStreak, initialMaxStreak]);

  // Nếu không truyền streak từ ngoài, tự động query từ /api/metrics/summary
  useEffect(() => {
    if (initialStreak !== undefined) return;

    let isMounted = true;
    const fetchStreak = async () => {
      try {
        const res = await fetch("/api/metrics/summary?range_days=7");
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setStreak(data.currentStreak ?? data.current_streak ?? 0);
            setMaxStreak(data.maxStreak ?? data.max_streak ?? 0);
          }
        }
      } catch (err) {
        // Fallback im lặng nếu chưa đăng nhập hoặc offline
        console.debug("[StreakBadge] Không thể lấy streak từ metrics/summary:", err);
      }
    };

    fetchStreak();
    return () => {
      isMounted = false;
    };
  }, [initialStreak]);

  // Thử tải file Lottie hoạt hình ngọn lửa nếu có sẵn
  useEffect(() => {
    let isMounted = true;
    const loadLottie = async () => {
      const candidates = [lottieSrc, "/lottie/flame.json", "/lottie/fire.json"];
      for (const src of candidates) {
        try {
          const res = await fetch(src);
          if (res.ok) {
            const data = await res.json();
            if (isMounted && data && (data.layers || data.v)) {
              setLottieAnimation(data);
              return;
            }
          }
        } catch {
          // Bỏ qua và thử file tiếp theo
        }
      }
    };

    loadLottie();
    return () => {
      isMounted = false;
    };
  }, [lottieSrc]);

  const hasStreak = streak > 0;

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        type="button"
        onClick={onClick}
        aria-label={`Chuỗi ngày học: ${streak} ngày`}
        className={cn(
          "group flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all duration-150 border select-none cursor-pointer active:scale-95",
          hasStreak
            ? "bg-white text-stone-900 border-[#C1762A]/40 shadow-xs hover:border-[#C1762A] hover:bg-[#F7ECE1]/30"
            : "bg-white text-stone-400 border-stone-200 hover:border-stone-300 hover:text-stone-600",
          className
        )}
      >
        {/* Khối Hoạt hình Ngọn lửa */}
        <div className="relative w-4 h-4 flex items-center justify-center shrink-0">
          <Flame
            size={16}
            className={cn(
              "transition-colors duration-200",
              hasStreak
                ? "fill-[#C1762A] text-[#8C4905]"
                : "text-stone-300 fill-transparent"
            )}
          />
        </div>

        {/* Số ngày Streak */}
        <span
          className={cn(
            "font-bold tracking-tight text-sm tabular-nums",
            hasStreak ? "text-[#8C4905]" : "text-stone-400"
          )}
        >
          {streak}
        </span>

        {/* Nhãn chữ trên desktop */}
        <span className="hidden md:inline font-medium text-xs text-stone-600">
          ngày
        </span>
      </button>

      {/* Tooltip giải thích khi hover */}
      {showTooltip && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-56 p-3 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-[#F1CCA6] text-xs z-50 animate-in fade-in zoom-in-95 duration-200 pointer-events-none">
          <div className="flex items-center gap-1.5 font-bold text-[#8C4905] mb-1">
            <Sparkles size={14} className="text-amber-500" />
            <span>Chuỗi ngày học liên tục</span>
          </div>
          <p className="text-gray-600 mb-2 leading-relaxed">
            {hasStreak
              ? `Bạn đã học liên tục ${streak} ngày! Hãy duy trì mỗi ngày để giữ vững chuỗi học tập.`
              : "Học bài ngay hôm nay để bắt đầu chuỗi ngày học liên tục!"}
          </p>
          {maxStreak > 0 && (
            <div className="flex items-center gap-1.5 pt-1.5 border-t border-gray-100 text-[11px] text-[#C1762A] font-semibold">
              <Trophy size={13} className="text-amber-500" />
              <span>Kỷ lục cao nhất: {maxStreak} ngày</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
export default StreakBadge;
