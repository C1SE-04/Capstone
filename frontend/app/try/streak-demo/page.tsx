"use client";

import React, { useState } from "react";
import {
  StreakBadge,
  STREAK_TIERS,
  getStreakTier,
  FigmaStreakFlame,
} from "@/components/chat/StreakBadge";
import { ArrowLeft, Flame } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

const DEMO_STREAKS = [0, 1, 2, 3, 10, 30, 60, 100, 200, 365];

export default function StreakDemoPage() {
  const [customStreak, setCustomStreak] = useState(42);

  return (
    <div className="min-h-screen bg-[#F7ECE1] p-6 md:p-10">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-10">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm text-[#8C4905] hover:text-[#C1762A] font-medium mb-6 transition-colors"
        >
          <ArrowLeft size={16} />
          Quay về trang chủ
        </Link>

        <div className="flex items-center gap-3 mb-2">
          <Flame size={28} className="text-[#C1762A] fill-[#C1762A]" />
          <h1 className="text-3xl font-extrabold text-[#8C4905] tracking-tight">
            Demo 7 Mốc Tiến Hóa Ngọn Lửa Streak 🔥
          </h1>
        </div>
        <p className="text-[#8C4905]/70 text-base max-w-2xl">
          Task T8.9 — Mỗi mốc ngày học liên tục sẽ biến ngọn lửa thành một cấp độ mới 
          với màu sắc, hiệu ứng và phụ kiện riêng biệt theo đúng bản Figma T8.35.
        </p>
      </div>

      {/* Grid hiển thị tất cả 7 mốc + trạng thái 0, 1, 2 ngày */}
      <div className="max-w-4xl mx-auto">
        <h2 className="text-lg font-bold text-[#8C4905] mb-4">
          Tất cả các mốc tiến hóa
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-12">
          {DEMO_STREAKS.map((days) => {
            const tier = getStreakTier(days);
            return (
              <div
                key={days}
                className="flex flex-col items-center gap-3 p-5 bg-white rounded-2xl border border-[#F1CCA6]/60 shadow-sm hover:shadow-md transition-shadow"
              >
                {/* Icon lửa zoom lớn chuẩn Figma - chỉ hiện khi đạt từ mốc 3 ngày */}
                <div
                  className={cn(
                    "w-14 h-14 flex items-center justify-center p-2 rounded-2xl border shadow-inner",
                    tier
                      ? "bg-[#FFF8F3] border-[#F1CCA6]/40 " + tier.animationClass
                      : "bg-stone-50 border-stone-200"
                  )}
                >
                  {tier ? (
                    <FigmaStreakFlame tier={tier} />
                  ) : (
                    <span className="text-stone-300 text-sm font-semibold select-none">
                      —
                    </span>
                  )}
                </div>

                {/* Badge thực tế */}
                <StreakBadge streak={days} />

                {/* Thông tin tier */}
                <div className="text-center">
                  <p className="text-xs font-bold text-stone-800 mb-0.5">
                    {days} ngày
                  </p>
                  <p
                    className="text-[11px] font-semibold"
                    style={{ color: tier?.labelColor ?? "#A8A29E" }}
                  >
                    {tier?.name ?? "Chưa đạt mốc (chưa có lửa)"}
                  </p>
                  {tier && (
                    <div className="flex items-center justify-center gap-1.5 mt-2">
                      <div
                        className="w-3 h-3 rounded-full border"
                        style={{
                          backgroundColor: tier.flamePrimary,
                          borderColor: tier.flamePrimary,
                        }}
                      />
                      <div
                        className="w-3 h-3 rounded-full border"
                        style={{
                          backgroundColor: tier.flameCore,
                          borderColor: tier.labelColor,
                        }}
                      />
                    </div>
                  )}
                  {tier?.accessoryIcon && (
                    <p className="text-[10px] text-stone-400 mt-1">
                      Phụ kiện: {tier.accessoryIcon === "crown" ? "👑" : tier.accessoryIcon === "star" ? "⭐" : "✨"}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Slider custom để thử bất kỳ số ngày nào */}
        <h2 className="text-lg font-bold text-[#8C4905] mb-4">
          Thử với bất kỳ số ngày nào
        </h2>
        <div className="bg-white rounded-2xl border border-[#F1CCA6]/60 p-6 shadow-sm mb-12">
          <div className="flex flex-col sm:flex-row items-center gap-6">
            {/* Slider */}
            <div className="flex-1 w-full">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-semibold text-[#8C4905]">
                  Số ngày streak:
                </label>
                <span
                  className="text-2xl font-extrabold tabular-nums"
                  style={{ color: getStreakTier(customStreak)?.labelColor ?? "#A8A29E" }}
                >
                  {customStreak}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={400}
                value={customStreak}
                onChange={(e) => setCustomStreak(Number(e.target.value))}
                className="w-full h-2 bg-[#F1CCA6] rounded-lg appearance-none cursor-pointer accent-[#C1762A]"
              />
              <div className="flex justify-between text-[10px] text-stone-400 mt-1 px-0.5">
                <span>0</span>
                <span>3</span>
                <span>10</span>
                <span>30</span>
                <span>60</span>
                <span>100</span>
                <span>200</span>
                <span>365</span>
                <span>400</span>
              </div>
            </div>

            {/* Badge preview */}
            <div className="flex flex-col items-center gap-2.5 min-w-[150px]">
              <div
                className={cn(
                  "w-16 h-16 flex items-center justify-center p-2 rounded-2xl border shadow-inner",
                  getStreakTier(customStreak)
                    ? "bg-[#FFF8F3] border-[#F1CCA6]/50 " + getStreakTier(customStreak)!.animationClass
                    : "bg-stone-50 border-stone-200"
                )}
              >
                {getStreakTier(customStreak) ? (
                  <FigmaStreakFlame tier={getStreakTier(customStreak)!} />
                ) : (
                  <span className="text-stone-300 text-base font-semibold select-none">
                    —
                  </span>
                )}
              </div>
              <StreakBadge streak={customStreak} />
              <p
                className="text-xs font-semibold"
                style={{ color: getStreakTier(customStreak)?.labelColor ?? "#A8A29E" }}
              >
                {getStreakTier(customStreak)?.name ?? "Chưa đạt mốc"}
              </p>
            </div>
          </div>
        </div>

        {/* Quick buttons */}
        <h2 className="text-lg font-bold text-[#8C4905] mb-4">
          Nhảy nhanh đến mốc
        </h2>
        <div className="flex flex-wrap gap-2 mb-12">
          {DEMO_STREAKS.map((days) => {
            const tier = getStreakTier(days);
            const isActive = customStreak === days;
            return (
              <button
                key={days}
                onClick={() => setCustomStreak(days)}
                className="px-4 py-2 rounded-xl text-sm font-semibold border transition-all active:scale-95"
                style={{
                  backgroundColor: isActive ? (tier?.flamePrimary ?? "#C1762A") : "white",
                  color: isActive ? "white" : (tier?.labelColor ?? "#78716C"),
                  borderColor: tier?.flamePrimary ?? "#E7E5E4",
                }}
              >
                {days} ngày
              </button>
            );
          })}
        </div>

        {/* Bảng thông số chi tiết */}
        <h2 className="text-lg font-bold text-[#8C4905] mb-4">
          Bảng thông số 7 Tiers (Figma Specs)
        </h2>
        <div className="overflow-x-auto bg-white rounded-2xl border border-[#F1CCA6]/60 shadow-sm mb-12">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-stone-100">
                <th className="text-left p-3 font-bold text-[#8C4905]">Mốc</th>
                <th className="text-left p-3 font-bold text-[#8C4905]">Tên</th>
                <th className="text-left p-3 font-bold text-[#8C4905]">Màu lửa</th>
                <th className="text-left p-3 font-bold text-[#8C4905]">Tâm lửa</th>
                <th className="text-left p-3 font-bold text-[#8C4905]">Animation</th>
                <th className="text-left p-3 font-bold text-[#8C4905]">Phụ kiện</th>
              </tr>
            </thead>
            <tbody>
              {STREAK_TIERS.slice().reverse().map((tier) => (
                <tr key={tier.minDays} className="border-b border-stone-50 hover:bg-[#F7ECE1]/30 transition-colors">
                  <td className="p-3 font-bold" style={{ color: tier.labelColor }}>
                    {tier.minDays}+ ngày
                  </td>
                  <td className="p-3 font-semibold text-stone-700">{tier.name}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-4 h-4 rounded-full border"
                        style={{ backgroundColor: tier.flamePrimary, borderColor: tier.flamePrimary }}
                      />
                      <code className="text-[10px] text-stone-500">{tier.flamePrimary}</code>
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-4 h-4 rounded-full border"
                        style={{ backgroundColor: tier.flameCore, borderColor: tier.labelColor }}
                      />
                      <code className="text-[10px] text-stone-500">{tier.flameCore}</code>
                    </div>
                  </td>
                  <td className="p-3">
                    <code className="text-[10px] bg-stone-50 px-1.5 py-0.5 rounded text-stone-600">
                      {tier.animationClass}
                    </code>
                  </td>
                  <td className="p-3 text-center text-base">
                    {tier.accessoryIcon === "crown" ? "👑" : tier.accessoryIcon === "star" ? "⭐" : tier.accessoryIcon === "sparkles" ? "✨" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Nguyên bản Figma Canvas Export */}
        <h2 className="text-lg font-bold text-[#8C4905] mb-4">
          Bản vẽ gốc xuất từ Figma (1920 x 906)
        </h2>
        <div className="bg-white rounded-2xl border border-[#F1CCA6]/60 p-4 shadow-sm overflow-x-auto mb-12">
          <p className="text-xs text-stone-500 mb-3">
            Toàn bộ 7 mốc ngọn lửa trong ứng dụng được trích xuất trực tiếp từng vector path Bézier từ bản vẽ này:
          </p>
          <div className="border border-stone-200 rounded-xl overflow-hidden bg-stone-50">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/streak-tiers-figma.svg"
              alt="Bản vẽ gốc 7 mốc ngọn lửa Figma"
              className="w-full h-auto min-w-[700px]"
            />
          </div>
        </div>

        <p className="text-center text-xs text-stone-400 mt-8 mb-4">
          Trang demo tạm thời — Xóa sau khi nghiệm thu Task T8.9
        </p>
      </div>
    </div>
  );
}
