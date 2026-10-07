"use client";

/**
 * File: components/monitor/StudentOverviewCard.tsx
 * Mô tả: Thẻ hiển thị thống kê tổng quan của 1 học sinh (lớp, số buổi chat, môn gần nhất).
 * Dùng trong Dashboard Phụ huynh.
 */

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}

export function StatCard({ icon, label, value, sub, color = "bg-[#F7ECE1]" }: StatCardProps) {
  return (
    <div className={`${color} rounded-2xl p-5 flex items-start gap-4 border border-[#F1CCA6]`}>
      <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center shadow-sm shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">{label}</p>
        <p className="text-2xl font-black text-[#8C4905] leading-none">{value}</p>
        {sub && <p className="text-xs text-[#C1762A]/70 mt-1">{sub}</p>}
      </div>
    </div>
  );
}
