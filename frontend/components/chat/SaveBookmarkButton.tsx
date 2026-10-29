"use client";

import { useState } from "react";
import { Star, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { SavePlaylistModal } from "./SavePlaylistModal";

interface SaveBookmarkButtonProps {
  sessionId?: string | null;
  messageCreatedAt?: string | Date;
  className?: string;
  onSaved?: (bookmarkId: string) => void;
}

export function SaveBookmarkButton({
  sessionId,
  messageCreatedAt,
  className,
  onSaved,
}: SaveBookmarkButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [savedBookmarkId, setSavedBookmarkId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "saved">("idle");

  const effectiveSessionId = sessionId || "current_session";

  return (
    <div className={cn("inline-flex flex-col items-start gap-1", className)}>
      <button
        type="button"
        onClick={() => setIsModalOpen(true)}
        className={cn(
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all duration-200 border cursor-pointer select-none",
          status === "saved"
            ? "bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100 shadow-xs"
            : "bg-white text-[#8C4905] border-[#F1CCA6] hover:bg-[#F1CCA6]/40 shadow-xs active:scale-95"
        )}
        title={
          status === "saved"
            ? "Bấm để đổi tên bài hoặc đổi ngăn lưu trữ Sổ tay"
            : "Lưu bài toán vào Sổ tay (Ngăn lưu trữ)"
        }
      >
        {status === "saved" ? (
          <>
            <Check size={15} className="text-emerald-700 stroke-[2.5]" />
            <span className="hidden sm:inline">Đã lưu Sổ tay</span>
          </>
        ) : (
          <>
            <Star size={15} className="fill-[#C1762A] text-[#C1762A]" />
            <span className="hidden sm:inline">Lưu Sổ tay</span>
          </>
        )}
      </button>

      {/* Task T8.12: Popup Lưu vào Sổ tay dạng Playlist (YouTube-style) */}
      <SavePlaylistModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        sessionId={effectiveSessionId}
        messageCreatedAt={messageCreatedAt}
        initialBookmarkId={savedBookmarkId || undefined}
        onSaved={(id) => {
          setStatus("saved");
          setSavedBookmarkId(id);
          onSaved?.(id);
        }}
      />
    </div>
  );
}

export default SaveBookmarkButton;
