"use client";

import { useEffect, RefObject } from "react";

/**
 * File: frontend/hooks/useOnClickOutside.ts
 * Sprint 11 - Task T11.3.3
 * ==============================================================================
 * Hook xử lý bắt sự kiện click ra ngoài vùng phần tử (hoặc bấm phím Escape)
 * để đóng dropdown, menu hoặc modal một cách mượt mà và tự nhiên.
 *
 * UX Note:
 * - Khi người dùng click, tương tác hay cuộn chuột BÊN TRONG ref, menu KHÔNG bị đóng.
 * - Chỉ khi nhấn chuột hoặc chạm ngón tay bên NGOÀI ref thì handler mới được kích hoạt.
 * - Hỗ trợ bắt phím Escape theo chuẩn Accessible UI (WAI-ARIA).
 */
export function useOnClickOutside<T extends HTMLElement = HTMLElement>(
  ref: RefObject<T | null>,
  handler: (event: MouseEvent | TouchEvent | KeyboardEvent) => void,
  options: { enabled?: boolean; listenEscape?: boolean } = { enabled: true, listenEscape: true }
) {
  const { enabled = true, listenEscape = true } = options;

  useEffect(() => {
    if (!enabled) return;

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      const el = ref.current;
      // Không làm gì nếu ref chưa gắn hoặc click xảy ra bên trong ref
      if (!el || el.contains(event.target as Node)) {
        return;
      }
      handler(event);
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (listenEscape && event.key === "Escape") {
        handler(event);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    if (listenEscape) {
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      if (listenEscape) {
        document.removeEventListener("keydown", handleKeyDown);
      }
    };
  }, [ref, handler, enabled, listenEscape]);
}
