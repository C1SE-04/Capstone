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

  return (
    <>
      <div className="group relative bg-white rounded-2xl border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between overflow-hidden">
        {/* Header thẻ Flashcard */}
        <div className="p-4 bg-gradient-to-r from-[#F7ECE1]/60 to-white border-b border-[#F1CCA6]/40 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-7 h-7 rounded-lg bg-[#C1762A]/10 text-[#C1762A] flex items-center justify-center shrink-0">
              <BookOpen size={15} />
            </span>
            <h3 className="font-bold text-sm text-[#8C4905] truncate">
              {bookmark.session_title || "Bài toán Sổ tay"}
            </h3>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {bookmark.independence_score !== null &&
              bookmark.independence_score !== undefined && (
                <span
                  className={cn(
                    "text-[11px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1",
                    isPerfectScore
                      ? "bg-amber-100 text-amber-800 border border-amber-300"
                      : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  )}
                >
                  <Award size={12} />
                  {bookmark.independence_score}đ
                </span>
              )}
          </div>
        </div>

        {/* Thân thẻ Flashcard */}
        <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
          <div className="space-y-3">
            {/* Đề bài snapshot */}
            {bookmark.problem_snapshot && (
              <div>
                <p className="text-xs font-semibold text-[#8C4905]/70 uppercase tracking-wider mb-1 flex items-center gap-1">
                  Đề bài
                </p>
                <div className="p-2.5 rounded-xl bg-[#F7ECE1]/40 border border-[#F1CCA6]/40 text-xs text-stone-800 leading-relaxed font-medium line-clamp-4">
                  {bookmark.problem_snapshot}
                </div>
              </div>
            )}

            {/* Ảnh bài tập nếu có */}
            {bookmark.attachment_url && (
              <div>
                <div
                  onClick={() => setIsZoomOpen(true)}
                  className="relative group/img rounded-xl overflow-hidden max-h-36 bg-stone-100 border border-[#F1CCA6]/50 cursor-pointer shadow-inner"
                  title="Bấm để phóng to ảnh đề bài"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={bookmark.attachment_url}
                    alt="Ảnh đề bài"
                    className="w-full h-36 object-contain rounded-xl group-hover/img:scale-105 transition-transform duration-200"
                  />
                  <div className="absolute inset-0 bg-black/30 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="bg-white/90 backdrop-blur-sm text-[#8C4905] text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 shadow">
                      <Maximize2 size={12} /> Phóng to
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Bí kíp / Tóm tắt tư duy cốt lõi */}
            {bookmark.chat_summary && (
              <div className="p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/60">
                <p className="text-[11px] font-bold text-[#8C4905] flex items-center gap-1 mb-1">
                  <Sparkles size={12} className="text-[#C1762A]" />
                  Bí kíp cốt lõi
                </p>
                <p className="text-xs text-stone-700 leading-relaxed line-clamp-3">
                  {bookmark.chat_summary}
                </p>
              </div>
            )}
          </div>

          {/* Ngày lưu */}
          {formattedDate && (
            <div className="flex items-center gap-1 text-[11px] text-[#C1762A]/80 pt-1">
              <Calendar size={12} />
              <span>Đã lưu ngày {formattedDate}</span>
            </div>
          )}
        </div>

        {/* Footer thao tác */}
        <div className="p-3 bg-[#F7ECE1]/30 border-t border-[#F1CCA6]/40 flex items-center justify-between gap-2">
          <button
            onClick={() => onOpenChat(bookmark)}
            className="flex-1 inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 active:scale-[0.98] transition-all shadow-sm cursor-pointer"
          >
            <MessageSquare size={13} />
            <span>Xem lại đoạn chat</span>
          </button>

          <button
            onClick={handleDeleteClick}
            disabled={isDeleting}
            className="p-2 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors cursor-pointer"
            title="Xóa khỏi Sổ tay"
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
          imageTitle={bookmark.session_title || "Ảnh bài toán Sổ tay"}
          onClose={() => setIsZoomOpen(false)}
        />
      )}
    </>
  );
}
