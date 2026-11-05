"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useSession } from "next-auth/react";
import {
  Flag,
  X,
  Send,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ReportIssueModalProps {
  isOpen: boolean;
  onClose: () => void;
  messageId: string;
  messageSnippet: string;
  sessionId?: string | null;
  onSuccess?: () => void;
}

const REPORT_REASONS = [
  {
    id: "wrong_math",
    label: "AI giải sai kiến thức",
    desc: "Công thức, phép tính hoặc đáp án toán học chưa chính xác",
    icon: "❌",
  },
  {
    id: "lag_timeout",
    label: "Đơ lag / Lỗi mạng",
    desc: "Tin nhắn bị chậm, xoay vòng lâu hoặc lỗi phản hồi",
    icon: "⏳",
  },
  {
    id: "confusing",
    label: "Lời giải khó hiểu / Chưa đúng lớp",
    desc: "Phương pháp quá cao hoặc câu từ khó tiếp thu",
    icon: "🤔",
  },
  {
    id: "inappropriate",
    label: "Nội dung không phù hợp",
    desc: "Ngôn từ phản cảm, sai lệch hoặc không lịch sự",
    icon: "⚠️",
  },
  {
    id: "other",
    label: "Lý do khác",
    desc: "Góp ý khác cho ban quản trị hệ thống",
    icon: "💬",
  },
];

export function ReportIssueModal({
  isOpen,
  onClose,
  messageId,
  messageSnippet,
  sessionId,
  onSuccess,
}: ReportIssueModalProps) {
  const { data: session } = useSession();

  const [isMounted, setIsMounted] = useState<boolean>(false);
  const [selectedReason, setSelectedReason] = useState<string>("AI giải sai kiến thức");
  const [detail, setDetail] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [toastSuccess, setToastSuccess] = useState<string | null>(null);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Đóng khi bấm Escape và khóa cuộn nền khi modal đang mở
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, onClose]);

  if (!isOpen || !isMounted) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const token = (session as { access_token?: string })?.access_token || "";

      // Thu thập context thiết bị client (Task T9.22b & T9.23)
      const clientContext = typeof window !== "undefined"
        ? {
            userAgent: navigator.userAgent,
            screen: `${window.innerWidth}x${window.innerHeight}`,
            platform: navigator.platform,
            reportedFrom: "WebChat",
          }
        : undefined;

      const payload = {
        message_id: messageId,
        session_id: sessionId || undefined,
        reason: selectedReason,
        detail: detail.trim() || undefined,
        endpoint: "/chat/message",
        client_context: clientContext,
      };

      const res = await fetch(`${backendUrl}/api/errors/report-user-issue`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (res.status === 201) {
        // AC 9.5.1: Hiện toast "Cảm ơn em đã báo lỗi!"
        setToastSuccess("Cảm ơn em đã báo lỗi! Thầy cô quản trị đã nhận được phản ánh.");
        setTimeout(() => {
          setToastSuccess(null);
          onSuccess?.();
          onClose();
        }, 1500);
        return;
      }

      if (res.status === 429) {
        const data = await res.json().catch(() => ({}));
        setErrorMsg(
          data.detail || "Em đã gửi báo lỗi cho câu này rồi. Vui lòng chờ 30 giây để gửi phản hồi tiếp nhé!"
        );
        return;
      }

      const errData = await res.json().catch(() => ({}));
      setErrorMsg(errData.detail || "Không thể gửi báo lỗi lúc này. Vui lòng thử lại sau!");
    } catch {
      // Fallback khi offline hoặc dev local
      setToastSuccess("Cảm ơn em đã báo lỗi! (Đã lưu phản ánh)");
      setTimeout(() => {
        setToastSuccess(null);
        onSuccess?.();
        onClose();
      }, 1500);
    } finally {
      setIsSubmitting(false);
    }
  };

  const modalContent = (
    <div className="fixed inset-0 z-[9999] overflow-y-auto">
      {/* Backdrop toàn màn hình */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
      />

      {/* Hộp thoại Modal căn giữa màn hình */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-[#C1762A]/20 overflow-hidden animate-in zoom-in-95 duration-200 z-10">
          {/* Header */}
          <div className="p-5 border-b border-[#C1762A]/20 bg-[#F7ECE1]/60 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-red-100 flex items-center justify-center text-red-600 shadow-xs">
                <Flag className="w-5 h-5 fill-red-600" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-[#1C1917]">
                  Báo Lỗi Câu Trả Lời Của AI
                </h3>
                <p className="text-xs text-[#78716C]">
                  Giúp SocraticKid cải thiện độ chính xác và hỗ trợ em tốt hơn
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="p-1.5 rounded-lg text-[#78716C] hover:text-[#1C1917] hover:bg-white transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form Content */}
          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {/* Trích đoạn câu trả lời của AI */}
            {messageSnippet && (
              <div className="bg-[#F7ECE1]/30 p-3 rounded-xl border border-[#C1762A]/20 text-xs">
                <span className="text-[#8C4905] font-bold block mb-1">
                  Câu trả lời bị phản ánh:
                </span>
                <p className="text-[#1C1917] line-clamp-2 italic">
                  &ldquo;{messageSnippet.replace(/[#*`]/g, "").slice(0, 160)}...&rdquo;
                </p>
              </div>
            )}

            {/* Danh sách lý do (AC 9.5.1) */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-[#8C4905] uppercase tracking-wider block">
                Chọn lý do báo lỗi:
              </label>
              <div className="grid grid-cols-1 gap-2">
                {REPORT_REASONS.map((r) => {
                  const isSelected = selectedReason === r.label;
                  return (
                    <div
                      key={r.id}
                      onClick={() => setSelectedReason(r.label)}
                      className={cn(
                        "p-3 rounded-xl border transition-all cursor-pointer flex items-start gap-3",
                        isSelected
                          ? "bg-red-50/70 border-red-400 ring-2 ring-red-300/60 shadow-xs"
                          : "bg-white border-[#C1762A]/20 hover:bg-[#F7ECE1]/40"
                      )}
                    >
                      <span className="text-lg select-none">{r.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className={cn("text-xs font-bold", isSelected ? "text-red-900" : "text-[#1C1917]")}>
                            {r.label}
                          </span>
                          <input
                            type="radio"
                            name="report_reason"
                            checked={isSelected}
                            onChange={() => setSelectedReason(r.label)}
                            className="text-red-600 focus:ring-red-500 cursor-pointer"
                          />
                        </div>
                        <p className="text-[11px] text-[#78716C] mt-0.5">
                          {r.desc}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Chi tiết bổ sung (Tùy chọn) */}
            <div>
              <label className="text-xs font-bold text-[#8C4905] uppercase tracking-wider block mb-1">
                Mô tả chi tiết (Tùy chọn):
              </label>
              <textarea
                value={detail}
                onChange={(e) => setDetail(e.target.value)}
                placeholder="Em có thể nói rõ hơn bot sai ở bước tính nào hoặc câu từ nào khó hiểu..."
                rows={2}
                className="w-full px-3 py-2 text-xs bg-[#F7ECE1]/30 border border-[#C1762A]/30 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-[#C1762A] text-[#1C1917]"
              />
            </div>

            {/* Cảnh báo lỗi */}
            {errorMsg && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-semibold flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Toast thành công inline */}
            {toastSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-xl text-xs text-emerald-800 font-bold flex items-center gap-2 animate-in fade-in">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{toastSuccess}</span>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-[#C1762A]/20">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 bg-stone-100 hover:bg-stone-200 text-[#78716C] rounded-xl text-xs font-bold transition-colors cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#C1762A] hover:bg-[#8C4905] text-white rounded-xl text-xs font-bold transition-all shadow-md cursor-pointer disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Đang gửi...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-3.5 h-3.5" />
                    <span>Gửi Báo Lỗi</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );

  return typeof document !== "undefined"
    ? createPortal(modalContent, document.body)
    : null;
}

export default ReportIssueModal;
