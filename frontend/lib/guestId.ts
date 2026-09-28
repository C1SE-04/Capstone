/**
 * File: lib/guestId.ts
 * Mô tả: Utility quản lý Guest ID cho chế độ dùng thử (US 4.3 - Task 89).
 *
 * Cách hoạt động:
 *  - Lần đầu tiên người dùng (khách) truy cập trang /try, một UUID ngẫu nhiên
 *    sẽ được tạo ra và lưu vào localStorage với key "sk_guest_id".
 *  - Mỗi lần sau đó (F5, tắt mở lại tab, đóng browser...), cùng một ID sẽ được
 *    đọc ra và kẹp vào header "X-Guest-ID" của mỗi request gửi lên backend.
 *  - Backend dùng ID này để đếm số câu đã hỏi trong 24h và chặn lúc quá 10 câu.
 *
 * Sprint 4 - US 4.3 - AC1, AC2 (chống F5 ăn gian & tắt máy mở lại vẫn bị đếm tiếp)
 */

const GUEST_ID_KEY = "sk_guest_id";

/**
 * Lấy hoặc tạo mới Guest ID từ localStorage.
 * Chỉ chạy được phía client (browser). Trả về null ở SSR.
 */
export function getOrCreateGuestId(): string | null {
  if (typeof window === "undefined") return null;

  let guestId = localStorage.getItem(GUEST_ID_KEY);

  if (!guestId) {
    // Tạo UUID ngẫu nhiên — dùng crypto.randomUUID() nếu trình duyệt hỗ trợ,
    // fallback về Math.random() cho môi trường cũ hơn.
    guestId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `guest-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

    localStorage.setItem(GUEST_ID_KEY, guestId);
  }

  return guestId;
}

/**
 * Trả về object header chứa X-Guest-ID để kẹp vào fetch().
 * Nếu không lấy được ID (SSR), trả về object rỗng.
 *
 * Ví dụ dùng:
 *   const response = await fetch(url, {
 *     method: "POST",
 *     headers: { "Content-Type": "application/json", ...getGuestHeaders() },
 *     body: JSON.stringify(payload),
 *   });
 */
export function getGuestHeaders(): Record<string, string> {
  const id = getOrCreateGuestId();
  if (!id) return {};
  return { "X-Guest-ID": id };
}
