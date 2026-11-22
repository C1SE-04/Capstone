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
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
            <CheckCircle2 size={22} className="stroke-[2.2]" />
          </div>
          <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-0.5 rounded-full flex items-center gap-1 border border-emerald-100">
            <TrendingUp size={12} /> <span className="tabular-nums">{metrics.completedChange || "+12%"}</span>
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Tổng bài hoàn thành
          </p>
          <p className="text-2xl font-black text-[#8C4905] leading-none">
            <span className="tabular-nums">{isLoading ? "..." : metrics.completedProblems}</span>{" "}
            <span className="text-base font-bold text-[#8C4905]">bài</span>
          </p>
          <p className="text-xs text-[#7A3E04] mt-1.5">Các bài toán đã giải xong</p>
        </div>
      </div>

      {/* THẺ 2: Điểm Independence trung bình */}
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
            <Brain size={22} className="stroke-[2.2]" />
          </div>
          <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${badge.bg}`}>
            {badge.label}
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Điểm Tự Lực (Independence)
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-black text-[#8C4905] leading-none tabular-nums">
              {isLoading ? "..." : metrics.independenceScore}
            </span>
            <span className="text-sm font-bold text-[#C1762A]">/100</span>
          </div>
          <p className="text-xs text-[#7A3E04] mt-1.5">
            {metrics.independenceLevel || "Ít phụ thuộc vào gợi ý"}
          </p>
        </div>
      </div>

      {/* THẺ 3: Chuỗi học liên tiếp (Streak) */}
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-orange-100/80 flex items-center justify-center text-orange-600 shadow-inner">
            <Flame size={22} className="stroke-[2.2] fill-orange-500" />
          </div>
          <span className="text-[11px] font-semibold text-orange-700 bg-orange-50 px-2.5 py-0.5 rounded-full border border-orange-200">
            Kỷ lục: <strong className="tabular-nums font-bold">{metrics.maxStreak ?? metrics.currentStreak}</strong> ngày
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Chuỗi học liên tục
          </p>
          <p className="text-2xl font-black text-[#8C4905] leading-none">
            <span className="tabular-nums">{isLoading ? "..." : metrics.currentStreak}</span>{" "}
            <span className="text-base font-bold text-[#8C4905]">ngày</span>
          </p>
          <p className="text-xs text-[#7A3E04] mt-1.5">Duy trì tương tác mỗi ngày</p>
        </div>
      </div>

      {/* THẺ 4: Tổng giờ học */}
      <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
        <div className="flex items-start justify-between">
          <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
            <Clock size={22} className="stroke-[2.2]" />
          </div>
          <span className="text-[11px] font-semibold text-[#8C4905] bg-[#F7ECE1] px-2.5 py-0.5 rounded-full border border-[#F1CCA6]">
            ~<strong className="tabular-nums font-bold">{metrics.avgMinutesPerDay}</strong>p / ngày
          </span>
        </div>
        <div className="mt-4">
          <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
            Tổng thời gian học
          </p>
          <p className="text-2xl font-black text-[#8C4905] leading-none">
            <span className="tabular-nums">{isLoading ? "..." : metrics.totalStudyHours}</span>{" "}
            <span className="text-base font-bold text-[#8C4905]">giờ</span>
          </p>
          <p className="text-xs text-[#7A3E04] mt-1.5">Chỉ tính thời gian hoạt động thực</p>
        </div>
      </div>
    </section>
  );
}
