/**
 * File: components/dashboard/MilestoneFlameIcon.tsx
 * Mô tả: Component hiển thị biểu tượng ngọn lửa thực tế chuẩn vector (Figma & Custom SVG)
 * thay thế hoàn toàn cho emoji trên toàn bộ Bảng Xếp Hạng (US 8.2 & US 9.4).
 */

"use client";

import React from "react";
import { FigmaStreakFlame, STREAK_TIERS } from "@/components/chat/StreakBadge";
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

  // Mốc 0 - Tia Lửa Mầm (0 - 2 ngày): Vector ngọn lửa mầm non độc quyền
  return (
    <div className={cn("shrink-0 flex items-center justify-center", className)}>
      <svg
        viewBox="0 0 24 24"
        className="w-full h-full"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ filter: "drop-shadow(0 0 2px rgba(245, 158, 11, 0.4))" }}
      >
        {/* Đốm lửa non */}
        <path
          d="M12 2C12.5 4.5 15.5 6.5 15.5 9.5C15.5 11.433 13.933 13 12 13C10.067 13 8.5 11.433 8.5 9.5C8.5 6.5 11.5 4.5 12 2Z"
          fill="#F59E0B"
        />
        <path
          d="M12 5.5C12.3 7 13.8 8.2 13.8 9.8C13.8 10.8 13 11.6 12 11.6C11 11.6 10.2 10.8 10.2 9.8C10.2 8.2 11.7 7 12 5.5Z"
          fill="#FEF08A"
        />
        {/* Thân và hai lá mầm xanh */}
        <path
          d="M12 13V21"
          stroke="#10B981"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
        <path
          d="M12 17C10.2 17 8.5 15.8 8 14.5C8 16.8 10 18.5 12 18.5"
          fill="#10B981"
        />
        <path
          d="M12 15.5C13.8 15.5 15.5 14.3 16 13C16 15.3 14 17 12 17"
          fill="#059669"
        />
      </svg>
    </div>
  );
}
