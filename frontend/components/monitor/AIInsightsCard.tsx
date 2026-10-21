"use client";

/**
 * File: components/monitor/AIInsightsCard.tsx
 * Mô tả: Khối nhận xét AI thông minh có icon trực quan, huy hiệu đánh giá và lời khuyên sư phạm (Task T7.7 / US 7.1).
 * - Tự động tải báo cáo nhận xét sư phạm từ API GET /insights/{student_id}.
 * - Cho phép phụ huynh bấm "Phân tích lại" (POST /insights/generate/{student_id}) để cập nhật ngay.
 * - Hiển thị 3 khối phân tích trực quan: Điểm mạnh, Dạng bài còn lúng túng, Lời khuyên thiết thực cho cha mẹ.
 * - Huy hiệu đánh giá tự lập trực quan (Tự lập xuất sắc, Tự lập tốt, Đang tiến bộ, Cần thêm hỗ trợ).
 */

import React, { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import {
  Sparkles,
  Brain,
  Award,
  CheckCircle2,
  TrendingUp,
  AlertCircle,
  Lightbulb,
  RefreshCw,
  Calendar,
  Compass,
  HeartHandshake,
  BookOpen,
  Info,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { vi } from "date-fns/locale";

export interface AiInsightReport {
  summary: string;
  strengths: string[];
  weak_points: string[];
  recommendations: string[];
  mastery_assessment?: string;
  is_fallback?: boolean;
  fallback_reason?: string | null;
}

export interface ParentAiInsightData {
  student_id: string;
  student_name?: string;
  period_description: string;
  insight: AiInsightReport;
  created_at?: string;
}

interface AIInsightsCardProps {
  studentId: string;
  studentName?: string;
}

export function AIInsightsCard({ studentId, studentName }: AIInsightsCardProps) {
  const { data: session } = useSession();

  const [insightData, setInsightData] = useState<ParentAiInsightData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  // Fetch báo cáo AI Insight mới nhất
  const fetchInsight = useCallback(async () => {
    if (!studentId || !session?.access_token) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch(`${backendUrl}/insights/${studentId}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        throw new Error(`Không thể tải nhận xét AI (Mã lỗi: ${res.status})`);
      }

      const data: ParentAiInsightData = await res.json();
      setInsightData(data);
    } catch (err: any) {
      console.error("[AIInsightsCard] Lỗi khi tải nhận xét:", err);
      setErrorMessage(
        err?.message || "Đã xảy ra lỗi khi kết nối với máy chủ AI."
      );
    } finally {
      setIsLoading(false);
    }
  }, [backendUrl, session?.access_token, studentId]);

  // Kích hoạt phân tích lại từ Gemini
  const handleRegenerate = async () => {
    if (!studentId || !session?.access_token || isGenerating) return;

    setIsGenerating(true);
    try {
      const res = await fetch(`${backendUrl}/insights/generate/${studentId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        throw new Error("Không thể tạo phân tích mới. Vui lòng thử lại sau.");
      }

      // Tải lại dữ liệu vừa sinh
      await fetchInsight();
    } catch (err: any) {
      console.error("[AIInsightsCard] Lỗi khi tạo phân tích lại:", err);
      alert(err?.message || "Không thể phân tích lại lúc này.");
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    fetchInsight();
  }, [fetchInsight]);

  // Cấu hình huy hiệu theo mức độ tự lập
  const getMasteryBadgeConfig = (assessment?: string) => {
    switch (assessment) {
      case "Tự lập xuất sắc":
        return {
          label: "Tự lập xuất sắc",
          subtitle: "Năng lực tự học & tư duy vượt trội",
          badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-300",
          icon: <Award className="w-5 h-5 text-emerald-600" />,
        };
      case "Tự lập tốt":
        return {
          label: "Tự lập tốt",
          subtitle: "Chủ động suy nghĩ và ít cần trợ giúp",
          badgeClass: "bg-sky-50 text-sky-800 border-sky-300",
          icon: <CheckCircle2 className="w-5 h-5 text-sky-600" />,
        };
      case "Cần thêm hỗ trợ sư phạm":
        return {
          label: "Cần thêm hỗ trợ",
          subtitle: "Cần đồng hành tháo gỡ các bước khó",
          badgeClass: "bg-rose-50 text-rose-800 border-rose-300",
          icon: <HeartHandshake className="w-5 h-5 text-rose-600" />,
        };
      case "Đang tiến bộ":
      default:
        return {
          label: assessment || "Đang tiến bộ",
          subtitle: "Đang duy trì phong độ và rèn luyện đều đặn",
          badgeClass: "bg-amber-50 text-amber-800 border-amber-300",
          icon: <TrendingUp className="w-5 h-5 text-amber-600" />,
        };
    }
  };

  // 1. TRẠNG THÁI LOADING SKELETON
  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mb-8 animate-pulse">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6 pb-6 border-b border-[#F7ECE1]">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-[#F7ECE1] rounded-2xl" />
            <div className="space-y-2">
              <div className="h-5 w-48 bg-[#F7ECE1] rounded-md" />
              <div className="h-3 w-32 bg-[#F7ECE1] rounded-md" />
            </div>
          </div>
          <div className="h-10 w-36 bg-[#F7ECE1] rounded-xl" />
        </div>
        <div className="h-20 bg-[#FFFBF7] rounded-xl mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-44 bg-[#F7ECE1]/60 rounded-xl" />
          <div className="h-44 bg-[#F7ECE1]/60 rounded-xl" />
          <div className="h-44 bg-[#F7ECE1]/60 rounded-xl" />
        </div>
      </div>
    );
  }

  // 2. TRẠNG THÁI LỖI
  if (errorMessage && !insightData) {
    return (
      <div className="bg-white rounded-2xl border border-red-200 p-6 shadow-sm mb-8 text-center">
        <div className="w-12 h-12 rounded-2xl bg-red-50 text-red-500 mx-auto flex items-center justify-center mb-3">
          <AlertCircle size={24} />
        </div>
        <h3 className="text-base font-bold text-red-800 mb-1">
          Chưa thể tải nhận xét AI
        </h3>
        <p className="text-sm text-red-600 mb-4">{errorMessage}</p>
        <button
          onClick={fetchInsight}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#8C4905] text-white text-xs font-bold rounded-xl hover:bg-[#723B04] transition-colors"
        >
          <RefreshCw size={14} /> Thử lại
        </button>
      </div>
    );
  }

  const insight = insightData?.insight;
  const masteryConfig = getMasteryBadgeConfig(insight?.mastery_assessment);

  // Format ngày tạo
  const formattedCreatedAt = insightData?.created_at
    ? (() => {
        try {
          return format(parseISO(insightData.created_at), "dd/MM/yyyy HH:mm", {
            locale: vi,
          });
        } catch {
          return null;
        }
      })()
    : null;

  return (
    <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm hover:shadow-md transition-shadow duration-300 mb-8 relative overflow-hidden">
      {/* Nền ánh sáng trang trí */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-br from-[#F7ECE1]/50 to-transparent rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />

      {/* HEADER: Tiêu đề + Huy hiệu đánh giá + Nút Làm mới */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6 pb-5 border-b border-[#F7ECE1] relative z-10">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#8C4905] to-[#C1762A] text-white flex items-center justify-center shadow-md shadow-[#C1762A]/20">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black text-[#8C4905] tracking-tight">
                Nhận Xét Sư Phạm AI
              </h2>
              <span className="text-[11px] font-bold uppercase tracking-wider bg-[#F7ECE1] text-[#8C4905] px-2 py-0.5 rounded-full border border-[#F1CCA6]">
                Gemini Socratic
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#C1762A] font-medium mt-1">
              <Calendar size={13} className="text-[#C1762A]" />
              <span>Khoảng thời gian: {insightData?.period_description || "Gần đây"}</span>
            </div>
          </div>
        </div>

        {/* Cụm Huy hiệu & Nút Phân tích lại */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Huy hiệu đánh giá tự lập */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-bold shadow-sm ${masteryConfig.badgeClass}`}
            title={masteryConfig.subtitle}
          >
            {masteryConfig.icon}
            <div>
              <span className="block leading-none">{masteryConfig.label}</span>
              <span className="text-[10px] font-medium opacity-80 leading-none block mt-0.5">
                {masteryConfig.subtitle}
              </span>
            </div>
          </div>

          {/* Nút Phân tích lại */}
          <button
            onClick={handleRegenerate}
            disabled={isGenerating}
            title="Quét lại các bài toán con vừa làm và sinh nhận xét mới"
            className="flex items-center gap-1.5 px-3 py-2 bg-[#FFFBF7] hover:bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6] rounded-xl text-xs font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs hover:shadow-sm"
          >
            <RefreshCw
              size={13}
              className={isGenerating ? "animate-spin text-[#C1762A]" : "text-[#8C4905]"}
            />
            <span>{isGenerating ? "Đang phân tích..." : "Cập nhật nhận xét"}</span>
          </button>
        </div>
      </div>

      {/* KHỐI TÓM TẮT SƯ PHẠM TỔNG THỂ */}
      <div className="bg-gradient-to-r from-[#FFFBF7] via-[#FFF9F3] to-[#F7ECE1]/60 border border-[#F1CCA6]/70 rounded-2xl p-4 md:p-5 mb-6 relative">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-xl bg-[#8C4905]/10 text-[#8C4905] flex items-center justify-center shrink-0 mt-0.5">
            <Brain size={18} />
          </div>
          <div className="space-y-1">
            <h3 className="text-xs font-extrabold text-[#8C4905] uppercase tracking-wider">
              Đánh giá tổng quan từ Cố vấn AI
            </h3>
            <p className="text-sm text-[#5C3203] leading-relaxed font-medium">
              {insight?.summary ||
                "Học sinh đang có những bước tiến tích cực trong thói quen tư duy độc lập và giải toán kiên trì."}
            </p>
          </div>
        </div>
      </div>

      {/* 3 CỘT PHÂN TÍCH TRỰC QUAN */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-5 mb-5">
        {/* 1. ĐIỂM MẠNH & SỰ KIÊN TRÌ */}
        <div className="bg-emerald-50/50 border border-emerald-200/80 rounded-2xl p-4 md:p-5 flex flex-col justify-between hover:border-emerald-300 transition-colors">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                <CheckCircle2 size={16} className="stroke-[2.5]" />
              </div>
              <div>
                <h4 className="text-sm font-extrabold text-emerald-900 leading-tight">
                  Điểm mạnh & Kiên trì
                </h4>
                <p className="text-[11px] text-emerald-700 font-medium">
                  Chủ đề con tự tin làm chủ
                </p>
              </div>
            </div>

            {insight?.strengths && insight.strengths.length > 0 ? (
              <ul className="space-y-2 mt-2">
                {insight.strengths.map((item, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-xs text-emerald-950 font-medium leading-relaxed bg-white/70 p-2.5 rounded-xl border border-emerald-100/60 shadow-2xs"
                  >
                    <span className="text-emerald-500 font-bold mt-0.5">✔</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-emerald-700/80 italic mt-2">
                Chưa có dữ liệu bài tập đạt điểm tự lập cao.
              </p>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-emerald-200/60 text-[11px] text-emerald-700 font-semibold flex items-center gap-1.5">
            <span>Hãy khen ngợi để con duy trì sự hứng thú học tập.</span>
          </div>
        </div>

        {/* 2. DẠNG BÀI CÒN LÚNG TÚNG */}
        <div className="bg-amber-50/50 border border-amber-200/80 rounded-2xl p-4 md:p-5 flex flex-col justify-between hover:border-amber-300 transition-colors">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                <AlertCircle size={16} className="stroke-[2.5]" />
              </div>
              <div>
                <h4 className="text-sm font-extrabold text-amber-900 leading-tight">
                  Điểm cần lưu ý
                </h4>
                <p className="text-[11px] text-amber-700 font-medium">
                  Dạng bài con còn xin gợi ý
                </p>
              </div>
            </div>

            {insight?.weak_points && insight.weak_points.length > 0 ? (
              <ul className="space-y-2 mt-2">
                {insight.weak_points.map((item, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-xs text-amber-950 font-medium leading-relaxed bg-white/70 p-2.5 rounded-xl border border-amber-100/60 shadow-2xs"
                  >
                    <span className="text-amber-500 font-bold mt-0.5">●</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-amber-700/80 italic mt-2">
                Con không gặp vướng mắc đáng kể ở các bài đã làm.
              </p>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-amber-200/60 text-[11px] text-amber-700 font-semibold flex items-center gap-1.5">
            <span>Khó khăn là cơ hội để con rèn luyện tư duy độc lập.</span>
          </div>
        </div>

        {/* 3. LỜI KHUYÊN SƯ PHẠM CHO CHA MẸ */}
        <div className="bg-[#FFFBF7] border border-[#F1CCA6] rounded-2xl p-4 md:p-5 flex flex-col justify-between hover:border-[#C1762A] transition-colors">
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center">
                <Lightbulb size={16} className="stroke-[2.5]" />
              </div>
              <div>
                <h4 className="text-sm font-extrabold text-[#8C4905] leading-tight">
                  Lời khuyên cho Cha Mẹ
                </h4>
                <p className="text-[11px] text-[#C1762A] font-medium">
                  Hành động thực tế hỗ trợ tại nhà
                </p>
              </div>
            </div>

            {insight?.recommendations && insight.recommendations.length > 0 ? (
              <ul className="space-y-2 mt-2">
                {insight.recommendations.map((item, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-xs text-[#5C3203] font-medium leading-relaxed bg-white p-2.5 rounded-xl border border-[#F1CCA6]/60 shadow-2xs"
                  >
                    <Compass size={14} className="text-[#C1762A] shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-[#C1762A] italic mt-2">
                Khuyến khích con tiếp tục đặt câu hỏi khi gặp bài khó.
              </p>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-[#F1CCA6]/60 text-[11px] text-[#8C4905] font-semibold flex items-center gap-1.5">
            <span>Phương pháp Socratic: Hỏi gợi mở, không làm thay.</span>
          </div>
        </div>
      </div>

      {/* FOOTER & METADATA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-3 text-[11px] text-[#C1762A]/80 border-t border-[#F7ECE1]">
        <div className="flex items-center gap-1.5">
          <Info size={13} />
          {insight?.is_fallback ? (
            <span>
              Báo cáo khởi tạo sơ bộ. Nhận xét sẽ càng chuẩn xác hơn khi con giải thêm bài.
            </span>
          ) : (
            <span>
              Báo cáo được tổng hợp tự động dựa trên số bài tập thực tế và điểm tự lực.
            </span>
          )}
        </div>
        {formattedCreatedAt && (
          <div className="font-medium text-[#8C4905]/70">
            Cập nhật lần cuối: {formattedCreatedAt}
          </div>
        )}
      </div>
    </section>
  );
}
