/**
 * File: frontend/lib/adminNotificationStorage.ts
 * Sprint 11 - US 11.3 (Task #387 - T11.3.5)
 * ==============================================================================
 * Quản lý lưu trữ trạng thái đọc/chưa đọc của các thông báo sự cố Admin.
 *
 * Nhiệm vụ:
 * 1. Lưu trữ danh sách error_id đã đọc vào LocalStorage (`socratic_admin_read_error_ids`).
 * 2. Đảm bảo an toàn môi trường SSR của Next.js (không văng lỗi `window is undefined`).
 * 3. Hỗ trợ phát CustomEvent `SOCRATIC_ADMIN_NOTIFICATIONS_UPDATED` để đồng bộ
 *    tức thời số đếm giữa Icon Chuông (Header) và Dropdown Thông Báo.
 * 4. Cung cấp tiện ích đánh dấu 1 lỗi đã xem, đánh dấu tất cả đã xem, và tính unread count.
 */

export const ADMIN_READ_ERRORS_STORAGE_KEY = "socratic_admin_read_error_ids";
export const ADMIN_NOTIFICATIONS_UPDATED_EVENT = "SOCRATIC_ADMIN_NOTIFICATIONS_UPDATED";

/**
 * Đọc danh sách các ID lỗi đã đọc từ LocalStorage an toàn
 */
export function getStoredReadErrorIds(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(ADMIN_READ_ERRORS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (err) {
    console.error("[adminNotificationStorage] Lỗi khi đọc LocalStorage:", err);
    return [];
  }
}

/**
 * Phát Custom Event để thông báo cho toàn bộ các component (Header, Dropdown, Drawer)
 * cập nhật lại số đếm và trạng thái đọc mà không cần reload trang.
 */
function emitNotificationsUpdated() {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(new CustomEvent(ADMIN_NOTIFICATIONS_UPDATED_EVENT));
  } catch (err) {
    console.error("[adminNotificationStorage] Lỗi khi phát event cập nhật:", err);
  }
}

/**
 * Đánh dấu 1 sự cố là "Đã đọc"
 * - Thêm errorId vào mảng đã đọc trong LocalStorage (loại bỏ trùng lặp bằng Set)
 * - Phát sự kiện đồng bộ để giảm số đếm trên Icon Chuông ngay lập tức
 */
export function markErrorAsRead(errorId: string): void {
  if (typeof window === "undefined" || !errorId) return;

  try {
    const currentList = getStoredReadErrorIds();
    const idSet = new Set(currentList);

    if (!idSet.has(errorId)) {
      idSet.add(errorId);
      // Giới hạn tối đa 500 ID gần nhất để tránh phình to LocalStorage theo thời gian
      const updatedList = Array.from(idSet).slice(-500);
      localStorage.setItem(ADMIN_READ_ERRORS_STORAGE_KEY, JSON.stringify(updatedList));
      emitNotificationsUpdated();
    }
  } catch (err) {
    console.error("[adminNotificationStorage] Lỗi khi ghi markErrorAsRead:", err);
  }
}

/**
 * Đánh dấu toàn bộ danh sách sự cố truyền vào là "Đã đọc" (Nút '✓✓ Đánh dấu tất cả đã đọc')
 */
export function markAllErrorsAsRead(allErrorIds: string[]): void {
  if (typeof window === "undefined" || !allErrorIds || allErrorIds.length === 0) return;

  try {
    const currentList = getStoredReadErrorIds();
    const idSet = new Set(currentList);

    let hasChange = false;
    for (const id of allErrorIds) {
      if (id && !idSet.has(id)) {
        idSet.add(id);
        hasChange = true;
      }
    }

    if (hasChange) {
      const updatedList = Array.from(idSet).slice(-500);
      localStorage.setItem(ADMIN_READ_ERRORS_STORAGE_KEY, JSON.stringify(updatedList));
      emitNotificationsUpdated();
    }
  } catch (err) {
    console.error("[adminNotificationStorage] Lỗi khi ghi markAllErrorsAsRead:", err);
  }
}

/**
 * Kiểm tra xem 1 sự cố cụ thể đã được đánh dấu là "Đã đọc" hay chưa
 */
export function isErrorRead(errorId: string, readIds?: string[]): boolean {
  if (!errorId) return false;
  const list = readIds || getStoredReadErrorIds();
  return list.includes(errorId);
}

/**
 * Tính toán số lượng thông báo sự cố CHƯA ĐỌC
 * - Chỉ đếm các sự cố có status là "OPEN" (hoặc chưa resolved)
 * - Loại bỏ các sự cố có ID đã nằm trong danh sách đã đọc
 */
export function calculateUnreadCount(
  openErrors: Array<{ id: string; status?: string }>,
  readIds?: string[]
): number {
  if (!openErrors || !Array.isArray(openErrors)) return 0;
  const list = readIds || getStoredReadErrorIds();
  const readSet = new Set(list);

  return openErrors.filter((err) => {
    // Chỉ tính các lỗi đang mở (OPEN) và chưa nằm trong danh sách đã đọc
    const isOpen = !err.status || err.status.toUpperCase() === "OPEN";
    return isOpen && !readSet.has(err.id);
  }).length;
}

/**
 * Xóa toàn bộ danh sách đã đọc (Hỗ trợ Debug / Reset thử nghiệm)
 */
export function clearStoredReadErrors(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(ADMIN_READ_ERRORS_STORAGE_KEY);
    emitNotificationsUpdated();
  } catch (err) {
    console.error("[adminNotificationStorage] Lỗi khi xóa storage:", err);
  }
}

