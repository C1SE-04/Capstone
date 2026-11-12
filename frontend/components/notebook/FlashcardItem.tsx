"use client";

import { useState } from "react";
import {
  MessageSquare,
  Sparkles,
  Trash2,
  Maximize2,
  Calendar,
  Award,
  BookOpen,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BookmarkItem } from "@/types/bookmark";
import { ImageZoomModal } from "@/components/chat/ImageZoomModal";
import { cleanLatexForDisplay } from "@/lib/latex";

interface FlashcardItemProps {
  bookmark: BookmarkItem;
  onOpenChat: (bookmark: BookmarkItem) => void;
  onDelete: (bookmarkId: string) => void;
}

export function FlashcardItem({
  bookmark,
  onOpenChat,
  onDelete,
}: FlashcardItemProps) {
  const [isZoomOpen, setIsZoomOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const formattedDate = bookmark.created_at
    ? new Date(bookmark.created_at).toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    : "";

  const isPerfectScore = bookmark.independence_score === 100;

  const handleDeleteClick = async () => {
    if (isDeleting) return;
    const confirmed = window.confirm("Em có chắc chắn muốn xóa bài toán này khỏi Sổ tay không?");
    if (!confirmed) return;

    try {
      setIsDeleting(true);
      await onDelete(bookmark.id);
    } finally {
      setIsDeleting(false);
    }
  };

  const rawTitle =
    bookmark.title ||
    bookmark.problem_snapshot ||
    bookmark.session_title ||
    "Bài toán Sổ tay";
  const displayTitle = cleanLatexForDisplay(rawTitle);

  return (
    <>
      <div className="group relative bg-white rounded-2xl border border-[#F1CCA6] shadow-xs hover:shadow-md hover:border-[#C1762A]/50 transition-all duration-200 flex flex-col justify-between overflow-hidden">
        {/* Header thẻ Flashcard */}
        <div className="p-4 bg-[#F7ECE1]/40 border-b border-[#F1CCA6]/60 flex items-center justify-between gap-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="w-8 h-8 rounded-lg bg-amber-50 text-[#C1762A] border border-[#F1CCA6] flex items-center justify-center shrink-0">
              <BookOpen size={15} />
            </span>
            <h3
              className="font-bold text-sm text-[#1C1917] truncate"
              title={displayTitle}
            >
              {displayTitle}
            </h3>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {bookmark.independence_score !== null &&
              bookmark.independence_score !== undefined && (
                <span
                  className={cn(
                    "text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1 tabular-nums",
                    isPerfectScore
                      ? "bg-amber-100 text-amber-900 border border-amber-300/80"
                      : "bg-[#ECFDF5] text-emerald-800 border border-emerald-200"
                  )}
                >
                  <Award size={12} />
                  {bookmark.independence_score}đ
                </span>
              )}
          </div>
        </div>

        {/* Thân thẻ Flashcard với khoảng đệm thoáng đãng */}
        <div className="p-5 space-y-3.5 flex-1 flex flex-col justify-between">
          <div className="space-y-3">
            {/* Đề bài snapshot */}
            {bookmark.problem_snapshot && (
              <div>
                <p className="text-[11px] font-bold text-[#7A3E04] uppercase tracking-wider mb-1.5">
                  Đề bài
                </p>
                <div className="p-3 rounded-xl bg-[#F7ECE1]/30 border border-[#F1CCA6]/60 text-xs text-[#1C1917] leading-relaxed font-normal line-clamp-3">
                  {cleanLatexForDisplay(bookmark.problem_snapshot)}
                </div>
              </div>
            )}

            {/* Thumbnail ảnh bài tập thu nhỏ gọn gàng (không chiếm quá nhiều diện tích dọc) */}
            {bookmark.attachment_url && (
              <div>
                <p className="text-[11px] font-bold text-[#7A3E04] uppercase tracking-wider mb-1.5">
                  Ảnh bài tập
                </p>
                <div
                  onClick={() => setIsZoomOpen(true)}
                  className="relative group/img rounded-xl overflow-hidden h-24 bg-[#F7ECE1]/20 border border-[#F1CCA6] cursor-pointer flex items-center justify-center"
                  title="Bấm để xem ảnh kích thước lớn"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={bookmark.attachment_url}
                    alt="Ảnh đề bài"
                    className="max-h-full max-w-full object-contain group-hover/img:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-stone-900/25 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="bg-white/95 text-stone-800 text-[11px] font-bold px-2 py-1 rounded-md flex items-center gap-1 shadow-sm">
                      <Maximize2 size={11} /> Phóng to
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Bí kíp / Tóm tắt tư duy cốt lõi (Nổi bật, dễ đọc) */}
            {bookmark.chat_summary && (
              <div className="p-3.5 rounded-xl bg-[#F1CCA6]/30 border border-[#C1762A]/30 shadow-xs">
                <p className="text-[11px] font-bold text-[#8C4905] flex items-center gap-1.5 mb-1">
                  <Sparkles size={13} className="text-[#C1762A] fill-amber-300" />
                  Bí kíp cốt lõi
                </p>
                <p className="text-xs text-[#1C1917] leading-relaxed font-medium line-clamp-3">
                  {cleanLatexForDisplay(bookmark.chat_summary)}
                </p>
              </div>
            )}
          </div>

          {/* Ngày lưu */}
          {formattedDate && (
            <div className="flex items-center gap-1.5 text-[11px] text-[#7A3E04] pt-1 tabular-nums">
              <Calendar size={12} />
              <span>Lưu ngày {formattedDate}</span>
            </div>
          )}
        </div>

        {/* Footer thao tác */}
        <div className="p-3.5 bg-[#F7ECE1]/30 border-t border-[#F1CCA6]/60 flex items-center justify-between gap-2">
          <button
            onClick={() => onOpenChat(bookmark)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold text-white bg-[#C1762A] hover:bg-[#8C4905] active:scale-[0.98] transition-all duration-150 ease-out shadow-xs cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
          >
            <MessageSquare size={13} />
            <span>Xem lại đoạn chat</span>
          </button>

          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="p-2 text-[#7A3E04] hover:text-red-600 hover:bg-red-50 rounded-xl active:scale-[0.95] transition-all duration-150 ease-out cursor-pointer disabled:opacity-50"
            title="Xóa bài toán này"
            aria-label="Xóa khỏi sổ tay"
          >
            {isDeleting ? (
              <Loader2 size={15} className="animate-spin text-red-500" />
            ) : (
              <Trash2 size={15} />
            )}
          </button>
        </div>
      </div>

      {/* Modal phóng to ảnh đề bài */}
      {bookmark.attachment_url && (
        <ImageZoomModal
          isOpen={isZoomOpen}
          imageUrl={bookmark.attachment_url}
          imageTitle={displayTitle}
          onClose={() => setIsZoomOpen(false)}
        />
      )}
    </>
  );
}

export default FlashcardItem;
