"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Star, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { authFetch } from "@/lib/authFetch";

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
  const { data: session } = useSession();
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!sessionId) return null;

  const handleSave = async () => {
    if (!sessionId || status === "saving" || status === "saved") return;

    setStatus("saving");
    setErrorMessage(null);

    try {
      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      const token = (session as { access_token?: string } | null)?.access_token;

      let isoCreatedAt: string | undefined = undefined;
      if (messageCreatedAt) {
        try {
          const d = new Date(messageCreatedAt);
          if (!isNaN(d.getTime())) {
            isoCreatedAt = d.toISOString();
          }
        } catch {
          // ignore
        }
      }

      const res = await authFetch(`${BACKEND_URL}/bookmarks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: sessionId,
          message_created_at: isoCreatedAt,
        }),
      });

      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setStatus("saved");
        if (onSaved && data.id) {
          onSaved(data.id);
        }
      } else if (res.status === 401) {
        setStatus("error");
        setErrorMessage("Bạn chưa đăng nhập hoặc phiên học tập đã hết hạn. Vui lòng tải lại trang!");
      } else if (res.status === 404 || res.status === 405 || res.status === 501) {
        // Backend API T7.13 chưa được deploy/merge
        setStatus("error");
        setErrorMessage("Hệ thống Sổ tay đang kết nối với máy chủ, bạn thử lại sau ít phút nhé!");
      } else {
        const errData = await res.json().catch(() => ({}));
        setStatus("error");
        const msg =
          errData.detail === "Not authenticated"
            ? "Bạn chưa đăng nhập hoặc phiên học tập đã hết hạn."
            : errData.detail || "Không thể lưu vào Sổ tay, vui lòng thử lại!";
        setErrorMessage(msg);
      }
    } catch {
      setStatus("error");
      setErrorMessage("Không thể kết nối máy chủ để lưu Sổ tay.");
    }
  };

  return (
    <div className={cn("flex flex-col items-start gap-1 mt-2.5", className)}>
      <button
        onClick={handleSave}
        disabled={status === "saving" || status === "saved"}
        className={cn(
          "inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 shadow-sm cursor-pointer select-none",
          status === "saved"
            ? "bg-emerald-100 text-emerald-800 border border-emerald-300 cursor-default"
            : status === "saving"
            ? "bg-[#F1CCA6] text-[#8C4905] border border-[#C1762A]/40 cursor-wait"
            : "bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white hover:brightness-105 active:scale-95 border border-[#C1762A]/20"
        )}
        title={
          status === "saved"
            ? "Bài toán đã nằm trong Sổ tay của bạn"
            : "Lưu bài toán và lời giải này vào Sổ tay để xem lại"
        }
      >
        {status === "saving" ? (
          <>
            <Loader2 size={13} className="animate-spin text-[#8C4905]" />
            <span>Đang lưu vào Sổ tay...</span>
          </>
        ) : status === "saved" ? (
          <>
            <Check size={14} className="text-emerald-700 stroke-[2.5]" />
            <span>Đã lưu vào Sổ tay</span>
          </>
        ) : (
          <>
            <Star size={13} className="fill-amber-300 text-amber-100" />
            <span>Lưu vào Sổ tay</span>
          </>
        )}
      </button>

      {status === "error" && errorMessage && (
        <p className="text-[11px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 animate-in fade-in duration-200">
          {errorMessage}
        </p>
      )}
    </div>
  );
}
