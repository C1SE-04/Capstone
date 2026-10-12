"use client";

import React from "react";
import { Calendar } from "lucide-react";

export type TimeRange = "7d" | "30d";

interface TimeRangeFilterProps {
  value: TimeRange;
  onChange: (val: TimeRange) => void;
}

export function TimeRangeFilter({ value, onChange }: TimeRangeFilterProps) {
  return (
    <div className="flex items-center gap-2 bg-white px-3.5 py-2 rounded-xl border border-[#F1CCA6] shadow-sm hover:border-[#C1762A] transition-colors">
      <Calendar size={18} className="text-[#C1762A] shrink-0" />
      <span className="text-xs font-semibold text-[#8C4905] hidden sm:inline">Phạm vi:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as TimeRange)}
        aria-label="Chọn khoảng thời gian lọc"
        className="bg-transparent text-sm font-bold text-[#8C4905] focus:outline-none cursor-pointer pr-1 py-0.5"
      >
        <option value="7d">7 ngày gần nhất</option>
        <option value="30d">30 ngày gần nhất</option>
      </select>
    </div>
  );
}
