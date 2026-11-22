/**
 * File: components/dashboard/MilestoneFlameIcon.tsx
 * Mô tả: Component hiển thị biểu tượng ngọn lửa thực tế chuẩn vector (Figma)
 * thay thế hoàn toàn cho emoji trên toàn bộ Bảng Xếp Hạng (US 8.2 & US 9.4).
 */

"use client";

import React from "react";
import { FigmaStreakFlame, STREAK_TIERS } from "@/components/chat/StreakBadge";
import { Flame } from "lucide-react";
import { cn } from "@/lib/utils";

interface MilestoneFlameIconProps {
  /** Số ngày streak hoặc kỷ lục streak để xác định tier */
  record?: number;
  className?: string;
}

export function MilestoneFlameIcon({
  record = 0,
  className = "w-5 h-5",
}: MilestoneFlameIconProps) {
  // Tìm cấu hình tier tương ứng từ mốc 3 ngày trở lên (trích xuất trực tiếp từ bản vẽ Figma)
  const tierConfig = STREAK_TIERS.find((t) => record >= t.minDays);

  if (tierConfig) {
    return (
      <div className={cn("shrink-0 flex items-center justify-center", className)}>
        <FigmaStreakFlame tier={tierConfig} className="w-full h-full" />
      </div>
    );
  }

  // Khi chưa đạt mốc 3 ngày (0 - 2 ngày): Không có ngọn lửa sáng, hiển thị icon lửa xám chưa thắp
  return (
    <div className={cn("shrink-0 flex items-center justify-center text-stone-300", className)}>
      <Flame className="w-full h-full text-stone-300 stroke-[1.8] fill-stone-200/50" />
    </div>
  );
}
