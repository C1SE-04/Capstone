"use client";

/**
 * File: components/monitor/ChildProblemHistory.tsx
 * Mô tả: Sổ theo dõi bài tập của con (Child Problem & Session History) - Task T7.9.
 * - Danh sách timeline bài toán con đã hoàn thành theo ngày/tuần.
 * - Hiển thị: Tên bài, ngày giờ, điểm tự lập (0-100), số gợi ý, số lần bấm Chưa hiểu.
 * - Modal phóng to ảnh đề bài Cloudinary (Lightbox).
 * - Popup xem đoạn đối thoại và quá trình tư duy của con.
 * - Dữ liệu thật từ API GET /parent/child-problems.
 */

import React, { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import {
  BookOpen,
  Clock,
  Sparkles,
  HelpCircle,
  ZoomIn,
  X,
  ExternalLink,
  MessageSquare,
  Brain,
  Lightbulb,
  ChevronLeft,
  ChevronRight,
  Image as ImageIcon,
  AlertCircle,
  Bot,
  User,
  CheckCircle2,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { vi } from "date-fns/locale";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { preprocessLaTeX } from "@/lib/latex";

// Schema tin nhắn đối thoại từng bước giữa Con và AI
export interface ProblemDialogueMessage {
  sender_type: "USER" | "AGENT_TUTOR" | string;
  content: string;
  attachment_url?: string | null;
  created_at?: string | null;
}

// Schema tương thích hoàn toàn với backend ChildProblemItem
export interface ChildProblemItem {
  id?: string;
  session_id: string;
  session_title: string | null;
  completed_at: string;
  score: number;
  hints_used: number;
  not_understood_count: number;
  evaluation: string | null;
  attachment_url: string | null;
  chat_summary: string | null;
  dialogue_messages?: ProblemDialogueMessage[];
}

interface ChildProblemsResponse {
  student_id: string;
  total: number;
  page: number;
  page_size: number;
  items: ChildProblemItem[];
}

interface ChildProblemHistoryProps {
  studentId?: string;
}

type FilterType = "ALL" | "WITH_IMAGE" | "EXCELLENT" | "NEEDS_SUPPORT";

export function ChildProblemHistory({ studentId }: ChildProblemHistoryProps) {
  const { data: session } = useSession();

  // State quản lý danh sách & phân trang
  const [problems, setProblems] = useState<ChildProblemItem[]>([]);
  const [totalProblems, setTotalProblems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;
  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // State bộ lọc nhanh
  const [filter, setFilter] = useState<FilterType>("ALL");

  // State Modal phóng to ảnh Cloudinary
  const [activeImage, setActiveImage] = useState<{
    url: string;
    title: string;
  } | null>(null);

  // State Popup xem đối thoại tư duy
  const [activeDialogue, setActiveDialogue] = useState<ChildProblemItem | null>(
    null
  );

  // Chuyển tab bộ lọc: reset trang về 1 để luôn hiển thị từ trang đầu của bộ lọc đó
  const handleFilterChange = (newFilter: FilterType) => {
    if (newFilter === filter) return;
    setFilter(newFilter);
    setCurrentPage(1);
  };

  // Fetch dữ liệu thật từ API /parent/child-problems
  useEffect(() => {
    let isMounted = true;
    if (!studentId || !session?.access_token) return;

    const loadData = async () => {
      setIsLoading(true);
      setFetchError(null);
      try {
        const backendUrl =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        const res = await fetch(
          `${backendUrl}/parent/child-problems?student_id=${studentId}&page=${currentPage}&page_size=${pageSize}&filter_type=${filter}`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

        if (!res.ok) {
          throw new Error(`Lỗi tải lịch sử bài tập: HTTP ${res.status}`);
        }

        const json: ChildProblemsResponse = await res.json();
        if (isMounted) {
          setProblems(json.items || []);
          setTotalProblems(json.total || 0);
        }
      } catch (err: unknown) {
        console.error("Lỗi fetch child-problems:", err);
        if (isMounted) {
          const msg =
            err instanceof Error
              ? err.message
              : "Không thể tải dữ liệu lịch sử bài tập";
          setFetchError(msg);
          setProblems([]);
          setTotalProblems(0);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, [studentId, session, currentPage, pageSize, filter, refreshKey]);

  // Phân loại badge tự lập
  const getIndependenceBadge = (score: number, evaluation?: string | null) => {
    if (score >= 80) {
      return {
        label: evaluation || "Xuất sắc",
        bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
        dotColor: "bg-emerald-500",
      };
    }
    if (score >= 65) {
      return {
        label: evaluation || "Khá tự lập",
        bg: "bg-amber-50 text-amber-700 border-amber-200",
        dotColor: "bg-amber-500",
      };
    }
    return {
      label: evaluation || "Cần hỗ trợ",
      bg: "bg-orange-50 text-orange-700 border-orange-200",
      dotColor: "bg-orange-500",
    };
  };

  // Danh sách bài tập hiển thị (Backend API /parent/child-problems đã thực hiện lọc và phân trang chuẩn theo filter_type)
  const filteredProblems = problems;

  // Format ngày an toàn
  const formatProblemDate = (dateStr: string) => {
    try {
      const d = parseISO(dateStr);
      return format(d, "HH:mm - EEEE, dd/MM/yyyy", { locale: vi });
    } catch {
      return dateStr;
    }
  };

  // Xử lý đóng modal bằng phím ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveImage(null);
        setActiveDialogue(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const totalPages = Math.max(1, Math.ceil(totalProblems / pageSize));

  return (
    <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm mt-8">
      {/* ─── HEADER KHỐI SỔ THEO DÕI ────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-[#F7ECE1]">
        <div>
          <h2 className="text-lg font-bold text-[#8C4905] flex items-center gap-2">
            <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
            <BookOpen size={20} className="text-[#C1762A]" />
            Sổ Theo Dõi Bài Tập Của Con
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]">
              {filter === "ALL" ? `${totalProblems} bài đã giải` : `${totalProblems} bài phù hợp`}
            </span>
          </h2>
          <p className="text-xs text-[#C1762A] mt-1 ml-3.5">
            Lịch sử từng bài toán con đã giải, ảnh đề bài chụp và diễn biến đối
            thoại tư duy
          </p>
        </div>

        {/* BỘ LỌC NHANH */}
        <div className="flex items-center gap-1.5 bg-[#FFFBF7] p-1 rounded-xl border border-[#F1CCA6] text-xs font-medium">
          <button
            onClick={() => handleFilterChange("ALL")}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              filter === "ALL"
                ? "bg-[#C1762A] text-white font-bold shadow-xs"
                : "text-[#8C4905] hover:bg-[#F7ECE1]"
            }`}
          >
            Tất cả
          </button>
          <button
            onClick={() => handleFilterChange("WITH_IMAGE")}
            className={`px-3 py-1.5 rounded-lg flex items-center gap-1 transition-colors ${
              filter === "WITH_IMAGE"
                ? "bg-[#C1762A] text-white font-bold shadow-xs"
                : "text-[#8C4905] hover:bg-[#F7ECE1]"
            }`}
          >
            <ImageIcon size={13} /> Có ảnh
          </button>
          <button
            onClick={() => handleFilterChange("EXCELLENT")}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              filter === "EXCELLENT"
                ? "bg-[#C1762A] text-white font-bold shadow-xs"
                : "text-[#8C4905] hover:bg-[#F7ECE1]"
            }`}
          >
            Xuất sắc (≥80đ)
          </button>
          <button
            onClick={() => handleFilterChange("NEEDS_SUPPORT")}
            className={`px-3 py-1.5 rounded-lg transition-colors ${
              filter === "NEEDS_SUPPORT"
                ? "bg-[#C1762A] text-white font-bold shadow-xs"
                : "text-[#8C4905] hover:bg-[#F7ECE1]"
            }`}
          >
            Cần hỗ trợ (&lt;65đ)
          </button>
        </div>
      </div>

      {/* ─── NỘI DUNG CHÍNH (LOADING / ERROR / EMPTY / TIMELINE) ─────────────── */}
      <div className="pt-6">
        {isLoading ? (
          /* SKELETON LOADING */
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="animate-pulse bg-[#FFFBF7] border border-[#F1CCA6]/60 rounded-2xl p-5 flex flex-col md:flex-row gap-4 justify-between"
              >
                <div className="space-y-3 flex-1">
                  <div className="h-4 bg-[#F1CCA6]/50 rounded-md w-1/3" />
                  <div className="h-5 bg-[#F1CCA6]/70 rounded-md w-2/3" />
                  <div className="h-3 bg-[#F1CCA6]/40 rounded-md w-1/2" />
                </div>
                <div className="w-24 h-24 bg-[#F1CCA6]/40 rounded-xl" />
              </div>
            ))}
          </div>
        ) : fetchError ? (
          /* BÁO LỖI */
          <div className="text-center py-10 bg-red-50 rounded-2xl border border-red-200 p-6">
            <AlertCircle size={36} className="text-red-500 mx-auto mb-2" />
            <p className="text-sm font-bold text-red-800">{fetchError}</p>
            <button
              onClick={() => setRefreshKey((k) => k + 1)}
              className="mt-3 text-xs font-semibold px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition"
            >
              Thử lại
            </button>
          </div>
        ) : filteredProblems.length === 0 ? (
          /* EMPTY STATE */
          <div className="text-center py-12 px-4 bg-[#FFFBF7] rounded-2xl border border-dashed border-[#F1CCA6]">
            <div className="w-16 h-16 bg-[#F7ECE1] rounded-2xl flex items-center justify-center mx-auto mb-3 text-[#C1762A] shadow-inner">
              <BookOpen size={28} />
            </div>
            <h3 className="text-base font-bold text-[#8C4905]">
              {filter === "ALL"
                ? "Con chưa hoàn thành bài toán nào"
                : "Không tìm thấy bài tập phù hợp với bộ lọc"}
            </h3>
            <p className="text-xs text-[#C1762A] mt-1 max-w-sm mx-auto">
              Khi con giải xong bài toán và bấm &quot;Đã hiểu&quot;, bài toán sẽ
              tự động xuất hiện tại đây kèm ảnh đề bài và tiến trình tư duy.
            </p>
          </div>
        ) : (
          /* DANH SÁCH TIMELINE BÀI TẬP */
          <div className="relative pl-4 md:pl-6 space-y-6 before:absolute before:left-[19px] md:before:left-[27px] before:top-3 before:bottom-3 before:w-[2px] before:bg-[#F1CCA6]">
            {filteredProblems.map((item, index) => {
              const badge = getIndependenceBadge(item.score, item.evaluation);
              const title = item.session_title || "Bài toán chưa đặt tên";
              const uniqueKey =
                item.id || `${item.session_id}_${item.completed_at}_${index}`;

              return (
                <div key={uniqueKey} className="relative flex items-start gap-4">
                  {/* Timeline Node Dot */}
                  <div
                    className={`relative z-10 w-4 h-4 rounded-full mt-5 ring-4 ring-white ${badge.dotColor} shadow-xs shrink-0`}
                  />

                  {/* Problem Card */}
                  <div className="flex-1 bg-[#FFFBF7] hover:bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs hover:shadow-md transition-all duration-200">
                    <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                      {/* Cột thông tin bài */}
                      <div className="space-y-2 flex-1">
                        {/* Thời gian & Badge tự lập */}
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[11px] font-medium text-[#C1762A] flex items-center gap-1">
                            <Clock size={12} />
                            {formatProblemDate(item.completed_at)}
                          </span>
                          <span
                            className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${badge.bg}`}
                          >
                            {badge.label} • {item.score}/100đ
                          </span>
                        </div>

                        {/* Tiêu đề bài toán */}
                        <h3 className="text-base font-extrabold text-[#8C4905] leading-snug">
                          {title}
                        </h3>

                        {/* Thống kê gợi ý & chưa hiểu */}
                        <div className="flex flex-wrap items-center gap-3 pt-1">
                          <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#F7ECE1] text-[#8C4905] flex items-center gap-1.5 border border-[#F1CCA6]/60">
                            <Lightbulb size={13} className="text-[#C1762A]" />
                            {item.hints_used} gợi ý đã dùng
                          </span>
                          <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-orange-50 text-orange-700 flex items-center gap-1.5 border border-orange-200/60">
                            <HelpCircle size={13} className="text-orange-500" />
                            {item.not_understood_count} lần Chưa hiểu
                          </span>
                        </div>

                        {/* Đoạn trích chat tóm tắt nếu có */}
                        {item.chat_summary && (
                          <div className="mt-3 p-3 rounded-xl bg-white border border-[#F1CCA6]/70 text-xs text-[#8C4905] line-clamp-2 italic leading-relaxed">
                            <span className="font-bold text-[#C1762A] not-italic mr-1.5">
                              Con hỏi:
                            </span>
                            &ldquo;{item.chat_summary.split(" | ")[0]}&rdquo;
                          </div>
                        )}
                      </div>

                      {/* Cột ảnh Cloudinary (Thumbnail) */}
                      {item.attachment_url && (
                        <div className="shrink-0 flex flex-col items-center">
                          <div
                            onClick={() =>
                              setActiveImage({
                                url: item.attachment_url!,
                                title: title,
                              })
                            }
                            className="relative group w-24 h-24 rounded-xl overflow-hidden border-2 border-[#F1CCA6] cursor-pointer shadow-xs hover:border-[#C1762A] transition"
                            title="Click để phóng to đề bài"
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={item.attachment_url}
                              alt="Ảnh đề bài của con"
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                              loading="lazy"
                            />
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center text-white text-[10px] font-bold gap-1">
                              <ZoomIn size={16} />
                              <span>Phóng to</span>
                            </div>
                          </div>
                          <span className="text-[10px] font-medium text-[#C1762A] mt-1">
                            Ảnh chụp đề
                          </span>
                        </div>
                      )}
                    </div>

                      {/* Card Footer: Các nút thao tác */}
                    <div className="mt-4 pt-3 border-t border-[#F1CCA6]/50 flex items-center justify-end">
                      <button
                        onClick={() => setActiveDialogue(item)}
                        className="px-3.5 py-1.5 text-xs font-bold text-white bg-[#C1762A] hover:bg-[#8C4905] rounded-xl transition shadow-xs flex items-center gap-1.5"
                      >
                        <Brain size={13} />
                        Xem đối thoại tư duy
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ─── THANH ĐIỀU HƯỚNG PHÂN TRANG ─────────────────────────────────── */}
        {!isLoading && totalPages > 1 && (
          <div className="mt-8 pt-4 border-t border-[#F7ECE1] flex items-center justify-between">
            <span className="text-xs text-[#C1762A] font-medium">
              Hiển thị {filteredProblems.length} / {totalProblems} bài (Trang {currentPage}/{totalPages})
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className={`p-2 rounded-xl border border-[#F1CCA6] text-xs font-bold transition flex items-center gap-1 ${
                  currentPage <= 1
                    ? "opacity-40 cursor-not-allowed bg-gray-50 text-gray-400"
                    : "bg-white text-[#8C4905] hover:bg-[#F7ECE1]"
                }`}
              >
                <ChevronLeft size={14} /> Trước
              </button>
              <button
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className={`p-2 rounded-xl border border-[#F1CCA6] text-xs font-bold transition flex items-center gap-1 ${
                  currentPage >= totalPages
                    ? "opacity-40 cursor-not-allowed bg-gray-50 text-gray-400"
                    : "bg-white text-[#8C4905] hover:bg-[#F7ECE1]"
                }`}
              >
                Sau <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ─── MODAL PHÓNG TO ẢNH CLOUDINARY (LIGHTBOX) ────────────────────────── */}
      {activeImage && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setActiveImage(null)}
        >
          <div
            className="relative max-w-4xl w-full bg-[#1e1b18] rounded-2xl overflow-hidden shadow-2xl border border-white/10 flex flex-col max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/40 text-white">
              <div className="flex items-center gap-2">
                <ImageIcon size={18} className="text-[#F1CCA6]" />
                <h4 className="text-sm font-bold truncate max-w-md">
                  {activeImage.title}
                </h4>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={activeImage.url}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white text-xs flex items-center gap-1 transition"
                  title="Mở ảnh gốc trong tab mới"
                >
                  <ExternalLink size={14} />
                  <span className="hidden sm:inline">Mở ảnh gốc</span>
                </a>
                <button
                  onClick={() => setActiveImage(null)}
                  className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white transition"
                  title="Đóng (Esc)"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Modal Body: Hiển thị ảnh chất lượng cao */}
            <div className="p-4 flex items-center justify-center bg-black/60 overflow-auto">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={activeImage.url}
                alt={activeImage.title}
                className="max-h-[75vh] w-auto max-w-full object-contain rounded-lg shadow-lg"
              />
            </div>
          </div>
        </div>
      )}

      {/* ─── POPUP XEM ĐỐI THOẠI TƯ DUY CỦA CON ──────────────────────────────── */}
      {activeDialogue && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setActiveDialogue(null)}
        >
          <div
            className="bg-white rounded-3xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-[#F1CCA6] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Popup Header */}
            <div className="p-5 border-b border-[#F7ECE1] bg-gradient-to-r from-[#FFFBF7] to-[#F7ECE1] flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#8C4905] text-[#F7ECE1] flex items-center justify-center shadow-xs">
                  <Brain size={20} />
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-[#8C4905]">
                    Hành Trình Tư Duy Của Con
                  </h3>
                  <p className="text-xs text-[#C1762A] line-clamp-1">
                    {activeDialogue.session_title || "Bài toán giải cùng AI Socratic"}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveDialogue(null)}
                className="p-1.5 rounded-xl text-[#8C4905] hover:bg-[#F1CCA6]/40 transition"
                title="Đóng"
              >
                <X size={18} />
              </button>
            </div>

            {/* Popup Body: Diễn biến từng câu đối thoại */}
            <div className="p-6 overflow-y-auto space-y-4">
              {/* Thẻ tóm tắt chỉ số nhanh */}
              <div className="grid grid-cols-3 gap-2 p-3 rounded-2xl bg-[#FFFBF7] border border-[#F1CCA6] text-center text-xs">
                <div>
                  <p className="text-[10px] text-[#C1762A] font-semibold uppercase">Điểm tự lực</p>
                  <p className="text-base font-black text-[#8C4905]">{activeDialogue.score}/100</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#C1762A] font-semibold uppercase">Số gợi ý</p>
                  <p className="text-base font-black text-[#8C4905]">{activeDialogue.hints_used}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#C1762A] font-semibold uppercase">Chưa hiểu</p>
                  <p className="text-base font-black text-[#8C4905]">{activeDialogue.not_understood_count}</p>
                </div>
              </div>

              {/* Luồng đối thoại tư duy từng bước */}
              <div className="space-y-4 pt-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-bold text-[#8C4905] uppercase tracking-wider flex items-center gap-1.5">
                    <MessageSquare size={14} className="text-[#C1762A]" />
                    Diễn biến giải bài & đối thoại giữa Con và Gia sư AI:
                  </p>
                  {activeDialogue.dialogue_messages && activeDialogue.dialogue_messages.length > 0 && (
                    <span className="text-[11px] font-semibold text-[#C1762A] bg-[#F7ECE1] px-2 py-0.5 rounded-full border border-[#F1CCA6]">
                      {activeDialogue.dialogue_messages.length} lượt đối thoại
                    </span>
                  )}
                </div>

                {activeDialogue.dialogue_messages && activeDialogue.dialogue_messages.length > 0 ? (
                  <div className="relative pl-6 space-y-4 before:absolute before:left-3 before:top-3 before:bottom-3 before:w-0.5 before:bg-gradient-to-b before:from-[#C1762A] before:via-[#F1CCA6] before:to-emerald-400">
                    {activeDialogue.dialogue_messages.map((msg, index) => {
                      const isUser = msg.sender_type === "USER";
                      const isFirstUserMsg =
                        isUser &&
                        !activeDialogue.dialogue_messages!
                          .slice(0, index)
                          .some((m) => m.sender_type === "USER");

                      return (
                        <div key={index} className="relative group">
                          {/* Điểm mốc trên timeline */}
                          <div
                            className={`absolute -left-[18px] top-3 w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white shadow-xs border-2 border-white ${
                              isUser ? "bg-[#C1762A]" : "bg-[#8C4905]"
                            }`}
                            title={`Bước ${index + 1}`}
                          >
                            {index + 1}
                          </div>

                          {/* Bong bóng tin nhắn */}
                          <div
                            className={`p-3.5 rounded-2xl border transition-all ${
                              isUser
                                ? "bg-[#FFFBF7] border-[#F1CCA6] shadow-2xs ml-1"
                                : "bg-[#FAF8F5] border-[#E2D9CF] shadow-2xs ml-1"
                            }`}
                          >
                            {/* Header tin nhắn */}
                            <div className="flex items-center justify-between mb-1.5 gap-2">
                              <span
                                className={`text-[11px] font-bold flex items-center gap-1.5 ${
                                  isUser ? "text-[#C1762A]" : "text-[#8C4905]"
                                }`}
                              >
                                {isUser ? (
                                  <>
                                    <User size={13} />
                                    {isFirstUserMsg
                                      ? "Đề bài / Câu hỏi ban đầu của con:"
                                      : "Con suy luận & trả lời:"}
                                  </>
                                ) : (
                                  <>
                                    <Bot size={13} />
                                    Gia sư AI SocraticKid gợi mở:
                                  </>
                                )}
                              </span>

                              {msg.created_at && (
                                <span className="text-[10px] text-gray-400">
                                  {format(parseISO(msg.created_at), "HH:mm")}
                                </span>
                              )}
                            </div>

                            {/* Ảnh đính kèm (nếu là ảnh đề bài con gửi) */}
                            {msg.attachment_url && (
                              <div className="mb-2">
                                <div
                                  onClick={() =>
                                    setActiveImage({
                                      url: msg.attachment_url!,
                                      title: activeDialogue.session_title || "Ảnh bài toán của con",
                                    })
                                  }
                                  className="relative group/img inline-block rounded-xl overflow-hidden border-2 border-[#F1CCA6] cursor-pointer hover:border-[#C1762A] transition"
                                >
                                  {/* eslint-disable-next-line @next/next/no-img-element */}
                                  <img
                                    src={msg.attachment_url}
                                    alt="Đề bài của con"
                                    className="max-h-36 max-w-xs object-cover rounded-lg group-hover/img:scale-105 transition-transform"
                                    loading="lazy"
                                  />
                                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center text-white text-[11px] font-bold gap-1">
                                    <ZoomIn size={14} /> Phóng to đề bài
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Nội dung đối thoại (Hỗ trợ render KaTeX & Markdown chuẩn cho AI) */}
                            {isUser ? (
                              <p className="text-xs leading-relaxed whitespace-pre-line font-medium text-[#8C4905]">
                                {msg.content}
                              </p>
                            ) : (
                              <div className="markdown-prose prose-sm max-w-none text-xs leading-relaxed font-medium text-[#5A3818] min-w-0 break-words overflow-hidden">
                                <ReactMarkdown
                                  remarkPlugins={[remarkMath, remarkGfm]}
                                  rehypePlugins={[rehypeKatex]}
                                >
                                  {preprocessLaTeX(msg.content)}
                                </ReactMarkdown>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {/* Mốc hoàn thành bài */}
                    <div className="relative pt-1">
                      <div className="absolute -left-[18px] top-2 w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center shadow-xs border-2 border-white">
                        <CheckCircle2 size={14} />
                      </div>
                      <div className="ml-1 p-2.5 rounded-xl bg-emerald-50/80 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2">
                        <span>🎉 Con đã hiểu bài & hoàn thành bài giải thành công!</span>
                        <span className="ml-auto px-2 py-0.5 rounded-full bg-emerald-200/80 text-emerald-900 text-[10px] font-bold">
                          {activeDialogue.score}/100 điểm tự lập
                        </span>
                      </div>
                    </div>
                  </div>
                ) : activeDialogue.chat_summary ? (
                  /* Fallback dữ liệu cũ chưa có dialogue_messages */
                  activeDialogue.chat_summary.split(" | ").map((sentence, index) => (
                    <div
                      key={index}
                      className="p-3.5 rounded-2xl bg-[#FFFBF7] border border-[#F1CCA6] flex items-start gap-3 shadow-2xs"
                    >
                      <div className="w-6 h-6 rounded-full bg-[#C1762A] text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <span className="text-[11px] font-bold text-[#C1762A] block mb-0.5">
                          {index === 0
                            ? "Con nêu bài toán / câu hỏi ban đầu:"
                            : `Con phản hồi bước ${index + 1}:`}
                        </span>
                        <p className="text-xs text-[#8C4905] leading-relaxed font-medium">
                          &ldquo;{sentence}&rdquo;
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-xl bg-gray-50 text-center text-xs text-gray-500">
                    Chưa có trích đoạn văn bản cho phiên giải này.
                  </div>
                )}
              </div>

              {/* Lời khuyên sư phạm cho phụ huynh */}
              <div className="mt-4 p-4 rounded-2xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900 flex items-start gap-3">
                <Sparkles size={18} className="text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-bold block text-amber-800">
                    Góc nhìn sư phạm:
                  </span>
                  <p className="leading-relaxed">
                    {activeDialogue.score >= 80
                      ? "Con nắm rất chắc phương pháp, chỉ cần gợi mở nhẹ nhàng là tự suy luận ra đáp án. Phụ huynh nên khích lệ sự tự tin của con."
                      : activeDialogue.score >= 65
                      ? "Con có tư duy tốt nhưng còn hơi lúng túng ở các bước tính toán trung gian. Cần thêm 1-2 bài luyện tập cùng dạng để thuần thục."
                      : "Dạng bài này con còn chưa nắm vững công thức nền tảng. Ba mẹ có thể cùng con xem lại phần lý thuyết hoặc cho con giải lại bài này."}
                  </p>
                </div>
              </div>
            </div>

            {/* Popup Footer */}
            <div className="p-4 border-t border-[#F7ECE1] bg-[#FFFBF7] flex justify-end">
              <button
                onClick={() => setActiveDialogue(null)}
                className="px-5 py-2 text-xs font-bold text-white bg-[#8C4905] hover:bg-[#C1762A] rounded-xl transition shadow-xs"
              >
                Đóng cửa sổ
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

