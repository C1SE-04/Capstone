"use client";

import React from "react";
import { CheckCircle2, Brain, Flame, Clock, TrendingUp } from "lucide-react";

export interface SummaryMetrics {
  completedProblems: number;
  completedChange?: string;
  independenceScore: number;
  independenceLevel: string;
  currentStreak: number;
  maxStreak?: number;
  totalStudyHours: number;
  avgMinutesPerDay: number;
}

interface SummaryCardsProps {
  metrics: SummaryMetrics;
  isLoading?: boolean;
}

export function SummaryCards({ metrics, isLoading = false }: SummaryCardsProps) {
  const getIndependenceBadge = (score: number) => {
    if (score >= 80) return { label: "Xuất sắc", bg: "bg-emerald-50 text-emerald-700 border-emerald-200" };
    if (score >= 65) return { label: "Khá tự lập", bg: "bg-amber-50 text-amber-700 border-amber-200" };
    return { label: "Cần hỗ trợ", bg: "bg-orange-50 text-orange-700 border-orange-200" };
  };

  const badge = getIndependenceBadge(metrics.independenceScore);

  return (
    <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      {/* THẺ 1: Tổng bài hoàn thành */}
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
            <CheckCircle2 size={22} className="stroke-[2.2]" />
          </div>
          <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-100">
            <TrendingUp size={12} /> {metrics.completedChange || "+12%"}
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Tổng bài hoàn thành
          </p>
          <p className="text-2xl font-black text-[#8C4905] leading-none">
            {isLoading ? "..." : `${metrics.completedProblems} bài`}
          </p>
          <p className="text-xs text-[#C1762A]/70 mt-1.5">Các bài toán đã giải xong</p>
        </div>
      </div>

      {/* THẺ 2: Điểm Independence trung bình (CORE METRIC SPRINT 6) */}
      <div className="bg-gradient-to-br from-[#FFFBF7] to-[#F7ECE1] rounded-2xl p-5 border-2 border-[#C1762A]/40 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between relative overflow-hidden">
        <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-[#C1762A]/5 rounded-full blur-xl pointer-events-none" />
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-[#8C4905] flex items-center justify-center text-[#F7ECE1] shadow-md">
            <Brain size={22} className="stroke-[2.2]" />
          </div>
          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${badge.bg}`}>
            {badge.label}
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#8C4905] uppercase tracking-wider mb-1 flex items-center gap-1.5">
            Điểm Tự Lực (Independence)
          </p>
          <div className="flex items-baseline gap-1.5">
            <span className="text-3xl font-black text-[#8C4905] leading-none">
              {isLoading ? "..." : metrics.independenceScore}
            </span>
            <span className="text-sm font-bold text-[#C1762A]">/100</span>
          </div>
          <p className="text-xs text-[#8C4905]/80 font-medium mt-1.5">
            {metrics.independenceLevel || "Ít phụ thuộc vào gợi ý"}
          </p>
        </div>
      </div>

      {/* THẺ 3: Chuỗi học liên tiếp (Streak) */}
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-orange-100/80 flex items-center justify-center text-orange-600 shadow-inner">
            <Flame size={22} className="stroke-[2.2] fill-orange-500" />
          </div>
          <span className="text-[11px] font-semibold text-orange-700 bg-orange-50 px-2 py-0.5 rounded-full border border-orange-200">
            Kỷ lục: {metrics.maxStreak ?? metrics.currentStreak} ngày
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Chuỗi học liên tục
          </p>
          <p className="text-2xl font-black text-[#8C4905] leading-none">
            {isLoading ? "..." : `${metrics.currentStreak} ngày`}
          </p>
          <p className="text-xs text-[#C1762A]/70 mt-1.5">Duy trì tương tác mỗi ngày</p>
        </div>
      </div>

      {/* THẺ 4: Tổng giờ học */}
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
            <Clock size={22} className="stroke-[2.2]" />
          </div>
          <span className="text-[11px] font-semibold text-[#8C4905] bg-[#F7ECE1] px-2 py-0.5 rounded-full border border-[#F1CCA6]">
            ~{metrics.avgMinutesPerDay}p / ngày
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Tổng thời gian học
          </p>
          <p className="text-2xl font-black text-[#8C4905] leading-none">
            {isLoading ? "..." : `${metrics.totalStudyHours} giờ`}
          </p>
          <p className="text-xs text-[#C1762A]/70 mt-1.5">Chỉ tính thời gian hoạt động thực</p>
        </div>
      </div>
    </section>
  );
}
