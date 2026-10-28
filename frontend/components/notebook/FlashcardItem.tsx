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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BookmarkItem } from "@/types/bookmark";
import { ImageZoomModal } from "@/components/chat/ImageZoomModal";

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
    setIsDeleting(true);
    await onDelete(bookmark.id);
    setIsDeleting(false);
  };

  const displayTitle =
    bookmark.title ||
    bookmark.problem_snapshot ||
    bookmark.session_title ||
    "Bài toán Sổ tay";

  return (
    <>
      <div className="group relative bg-white rounded-xl border border-stone-200/90 shadow-2xs hover:shadow-md hover:border-stone-300 transition-all duration-200 flex flex-col justify-between overflow-hidden">
        {/* Header thẻ Flashcard */}
        <div className="p-4 bg-stone-50/60 border-b border-stone-100 flex items-center justify-between gap-2.5">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="w-8 h-8 rounded-lg bg-amber-50 text-[#C1762A] border border-amber-200/50 flex items-center justify-center shrink-0">
              <BookOpen size={15} />
            </span>
            <h3
              className="font-bold text-sm text-stone-900 truncate"
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
                    "text-[11px] font-bold px-2.5 py-0.5 rounded-full flex items-center gap-1",
                    isPerfectScore
                      ? "bg-amber-100 text-amber-900 border border-amber-300/80"
                      : "bg-emerald-50 text-emerald-800 border border-emerald-200"
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
                <p className="text-[11px] font-bold text-stone-400 uppercase tracking-wider mb-1.5">
                  Đề bài
                </p>
                <div className="p-3 rounded-lg bg-stone-50 border border-stone-200/60 text-xs text-stone-800 leading-relaxed font-normal line-clamp-3">
                  {bookmark.problem_snapshot}
                </div>
              </div>
            )}

            {/* Thumbnail ảnh bài tập thu nhỏ gọn gàng (không chiếm quá nhiều diện tích dọc) */}
            {bookmark.attachment_url && (
              <div>
                <p className="text-[11px] font-bold text-stone-400 uppercase tracking-wider mb-1.5">
                  Ảnh bài tập
                </p>
                <div
                  onClick={() => setIsZoomOpen(true)}
                  className="relative group/img rounded-lg overflow-hidden h-24 bg-stone-50 border border-stone-200 cursor-pointer flex items-center justify-center"
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
              <div className="p-3.5 rounded-lg bg-amber-50/90 border border-amber-200/80 shadow-2xs">
                <p className="text-[11px] font-bold text-[#8C4905] flex items-center gap-1.5 mb-1">
                  <Sparkles size={13} className="text-[#C1762A] fill-amber-300" />
                  Bí kíp cốt lõi
                </p>
                <p className="text-xs text-stone-800 leading-relaxed font-medium line-clamp-3">
                  {bookmark.chat_summary}
                </p>
              </div>
            )}
          </div>

          {/* Ngày lưu */}
          {formattedDate && (
            <div className="flex items-center gap-1.5 text-[11px] text-stone-400 pt-1">
              <Calendar size={12} />
              <span>Lưu ngày {formattedDate}</span>
            </div>
          )}
        </div>

        {/* Footer thao tác */}
        <div className="p-3.5 bg-stone-50/50 border-t border-stone-100 flex items-center justify-between gap-2">
          <button
            onClick={() => onOpenChat(bookmark)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-bold text-white bg-[#C1762A] hover:bg-[#8C4905] active:scale-[0.98] transition-all shadow-xs cursor-pointer"
          >
            <MessageSquare size={13} />
            <span>Xem lại đoạn chat</span>
          </button>

          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="p-2 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
            title="Xóa bài toán này"
            aria-label="Xóa khỏi sổ tay"
          >
            <Trash2 size={15} />
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
