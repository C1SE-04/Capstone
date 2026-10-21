"use client";

/**
 * File: components/chat/IdleModal.tsx
 * Task: T6.16 – US 6.3: UI Modal thông báo "Bạn vẫn đang học chứ? 🦉"
 *
 * Mô tả:
 *   - Hiển thị khi học sinh không gửi tin nhắn trong 10 phút (lắng nghe event IDLE_DETECTED hoặc qua props).
 *   - Overlay làm mờ nền (backdrop-blur).
 *   - Nút "Đang học" để học sinh xác nhận tiếp tục.
 *   - Khi bấm nút:
 *       1. Gửi timestamp restart lên BE (/api/metrics/restart) để BE ghi nhận khoảng active mới (T6.18).
 *       2. Gọi onContinue() để reset idle timer (T6.15) và đóng modal.
 */

import { useState, useEffect, useCallback } from "react";
import { Sparkles, Loader2, Clock } from "lucide-react";
import { AssistantOwl } from "./AssistantOwl";
import { IDLE_DETECTED_EVENT } from "@/hooks/useIdleTimer";

export interface IdleModalProps {
  /** Trạng thái mở/đóng modal (controlled mode) */
  isOpen?: boolean;
  /** Callback được gọi khi học sinh bấm "Đang học" */
  onContinue: () => void;
  /** Callback được gọi khi học sinh bấm "Không học" */
  onStopLearning?: () => void;
  /** ID của phiên học hiện tại (nếu có) để gửi kèm timestamp restart lên BE */
  sessionId?: string;
  /** Cho phép tự lắng nghe event IDLE_DETECTED trên window (uncontrolled mode, mặc định: true) */
  listenToIdleEvent?: boolean;
}

export function IdleModal({
  isOpen: controlledIsOpen,
  onContinue,
  onStopLearning,
  sessionId,
  listenToIdleEvent = true,
}: IdleModalProps) {
  // Trạng thái mở nội bộ (dùng khi component tự lắng nghe event)
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Xác định modal có đang mở hay không (ưu tiên prop từ bên ngoài nếu có truyền)
  const isOpen =
    controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;

  // Lắng nghe CustomEvent("IDLE_DETECTED") từ useIdleTimer (T6.15)
  useEffect(() => {
    if (!listenToIdleEvent) return;

    const handleIdleDetected = () => {
      setInternalIsOpen(true);
    };

    window.addEventListener(IDLE_DETECTED_EVENT, handleIdleDetected);
    return () => {
      window.removeEventListener(IDLE_DETECTED_EVENT, handleIdleDetected);
    };
  }, [listenToIdleEvent]);

  // Gửi timestamp restart lên BE và reset timer
  const handleContinueLearning = useCallback(async () => {
    setIsSubmitting(true);
    const now = Date.now();

    try {
      // T6.18: Gửi timestamp restart lên BFF / API Backend
      await fetch("/api/metrics/restart", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          timestamp: Math.floor(now / 1000), // Epoch seconds
          timestamp_ms: now,
          restart_time: new Date(now).toISOString(),
          session_id: sessionId || null,
        }),
      });
    } catch (error) {
      // Nếu backend chưa chạy hoặc lỗi mạng, log cảnh báo để không block trải nghiệm học sinh
      console.warn("[IdleModal] Gửi restart timestamp lên BE thất bại:", error);
    } finally {
      setIsSubmitting(false);
      setInternalIsOpen(false);
      onContinue();
    }
  }, [sessionId, onContinue]);

  // Xử lý khi học sinh chọn "Không học"
  const handleStopLearning = useCallback(() => {
    setInternalIsOpen(false);
    onStopLearning?.();
  }, [onStopLearning]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="idle-modal-title"
      aria-describedby="idle-modal-desc"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="relative bg-white rounded-3xl shadow-2xl p-6 sm:p-8 w-full max-w-sm sm:max-w-md border-2 border-[#F1CCA6] text-center overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Họa tiết trang trí nền ấm áp */}
        <div className="absolute -top-12 -right-12 w-32 h-32 bg-[#FFF6EB] rounded-full blur-2xl pointer-events-none" />
        <div className="absolute -bottom-12 -left-12 w-32 h-32 bg-[#FEEED8] rounded-full blur-2xl pointer-events-none" />

        {/* Avatar Cú Socratic thân thiện */}
        <div className="relative mx-auto mb-4 flex items-center justify-center">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-[#FFF6EB] to-[#FEEED8] border-2 border-[#F1CCA6] flex items-center justify-center shadow-inner overflow-hidden">
            <AssistantOwl emotion="idle" />
          </div>
          <div className="absolute -bottom-1 right-1/2 translate-x-8 bg-[#8C4905] text-[#FFE8D6] p-1.5 rounded-full shadow-md border-2 border-white">
            <Clock className="w-4 h-4 animate-pulse" />
          </div>
        </div>

        {/* Tiêu đề & Nội dung theo đặc tả US 6.3 */}
        <h3
          id="idle-modal-title"
          className="text-xl font-bold text-stone-900 mb-2 tracking-tight"
        >
          Bạn vẫn đang học chứ?
        </h3>

        <p
          id="idle-modal-desc"
          className="text-sm text-stone-600 mb-6 leading-relaxed"
        >
          Hệ thống nhận thấy bạn đã không tương tác trong một khoảng thời gian.
          Hãy bấm nút bên dưới để tiếp tục nhé!
        </p>

        {/* Cụm 2 nút: "Không học" & "Đang học" */}
        <div className="flex items-center gap-3 w-full">
          {/* Nút "Không học" */}
          <button
            type="button"
            onClick={handleStopLearning}
            disabled={isSubmitting}
            className="flex-1 py-3 px-4 rounded-2xl bg-[#F7ECE1] hover:bg-[#F1CCA6]/70 text-[#8C4905] font-bold text-sm border border-[#F1CCA6] transition-all active:scale-[0.98] cursor-pointer disabled:opacity-60"
          >
            Không học
          </button>

          {/* Nút "Đang học" để tiếp tục tính giờ học */}
          <button
            type="button"
            onClick={handleContinueLearning}
            disabled={isSubmitting}
            className="flex-1 py-3 px-4 rounded-2xl bg-gradient-to-r from-[#E07A5F] to-[#D96B43] hover:from-[#d56d52] hover:to-[#c85e37] text-white font-bold text-sm shadow-md shadow-[#E07A5F]/20 hover:shadow-lg hover:shadow-[#E07A5F]/30 active:scale-[0.98] transition-all flex items-center justify-center gap-1.5 disabled:opacity-75 disabled:cursor-not-allowed cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang kết nối...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-amber-200" />
                <span>Đang học</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
