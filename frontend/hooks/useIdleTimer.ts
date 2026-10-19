/**
 * File: hooks/useIdleTimer.ts
 * Task: T6.15 – US 6.3 (Thông Báo Idle & Dừng Tính Giờ Học)
 *
 * Mô tả:
 *   Hook theo dõi trạng thái idle của học sinh trong phiên chat.
 *   - Khởi tạo setTimeout countdown từ lần gửi tin nhắn cuối cùng.
 *   - Mỗi khi `reset()` được gọi (khi onSendMessage được trigger),
 *     timer cũ bị clear và tạo lại từ đầu.
 *   - Khi hết timeout → dispatch CustomEvent("IDLE_DETECTED") để:
 *       • T6.16 (IdleModal) hiển thị modal "Bạn vẫn đang học chứ? 🦉"
 *       • T6.17 (BE API) dừng tính active_seconds
 *
 * Cách dùng:
 *   const { reset: resetIdleTimer } = useIdleTimer({ timeout: 10 * 60 * 1000 });
 *   // Gọi resetIdleTimer() bên trong onSendMessage của ChatWindow.
 */

import { useEffect, useRef, useCallback } from "react";

/** Tên event phát ra khi học sinh không tương tác quá timeout */
export const IDLE_DETECTED_EVENT = "IDLE_DETECTED";

interface UseIdleTimerOptions {
  /**
   * Thời gian chờ tính bằng milliseconds trước khi phát IDLE_DETECTED.
   * Mặc định: 10 phút (600_000 ms) theo đặc tả US 6.3.
   */
  timeout?: number;
  /**
   * Callback tuỳ chọn – được gọi đồng thời khi idle xảy ra,
   * ngoài việc dispatch CustomEvent.
   * Hữu ích khi component muốn tự xử lý mà không cần lắng nghe event.
   */
  onIdle?: () => void;
  /**
   * Khi false, hook không khởi chạy timer (ví dụ: khi chưa có session).
   * Mặc định: true.
   */
  enabled?: boolean;
}

interface UseIdleTimerReturn {
  /**
   * Gọi hàm này mỗi khi học sinh gửi tin nhắn (onSendMessage).
   * Reset timer về 0 và bắt đầu đếm lại từ đầu.
   */
  reset: () => void;
}

const DEFAULT_TIMEOUT = 10 * 60 * 1000; // 10 phút theo đặc tả US 6.3

export function useIdleTimer({
  timeout = DEFAULT_TIMEOUT,
  onIdle,
  enabled = true,
}: UseIdleTimerOptions = {}): UseIdleTimerReturn {
  // Giữ ref tới timeoutId để có thể clear từ bất kỳ closure nào
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /**
   * Hàm nội bộ: clear timer cũ và khởi tạo timer mới.
   * Khi timer hết hạn:
   *   1. Dispatch CustomEvent("IDLE_DETECTED") lên window
   *      → IdleModal (T6.16) lắng nghe và hiện modal.
   *   2. Gọi onIdle() nếu caller truyền vào.
   */
  const startTimer = useCallback(() => {
    // Huỷ timer cũ trước (tránh leak)
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
    }

    timerRef.current = setTimeout(() => {
      // 1. Phát sự kiện toàn cục để các component khác lắng nghe
      window.dispatchEvent(new CustomEvent(IDLE_DETECTED_EVENT));

      // 2. Gọi callback cục bộ nếu có
      onIdle?.();
    }, timeout);
  }, [timeout, onIdle]);

  // Khởi động timer ngay khi hook mount (nếu enabled)
  useEffect(() => {
    if (!enabled) return;

    startTimer();

    // Cleanup khi component unmount: tránh dispatch sau khi đã rời trang
    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
      }
    };
  }, [enabled, startTimer]);

  /**
   * reset() – Public API của hook.
   * Gọi mỗi khi onSendMessage được trigger trong ChatWindow/ChatPage.
   * Clear timer hiện tại và bắt đầu đếm lại từ đầu (10 phút).
   */
  const reset = useCallback(() => {
    if (!enabled) return;
    startTimer();
  }, [enabled, startTimer]);

  return { reset };
}
