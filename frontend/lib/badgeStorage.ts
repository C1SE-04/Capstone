/**
 * File: frontend/lib/badgeStorage.ts
 * Quản lý lưu trữ thành tựu & huy hiệu học sinh theo US 7.2 (Game hóa).
 * Đảm bảo mỗi huy hiệu khi đạt điều kiện chỉ hiển thị ăn mừng (popup) đúng 1 lần duy nhất.
 */

import { BadgeItem, DEFAULT_BADGES } from "@/components/chat/BadgeModal";

const BADGE_STORAGE_PREFIX = "socratic_unlocked_badges_";

export interface StoredBadgeInfo {
  unlockedAt: string;
  celebrated: boolean; // Đã từng hiển thị modal chúc mừng hay chưa
}

/**
 * Lấy danh sách các huy hiệu đã mở khóa từ LocalStorage theo User ID
 */
export function getStoredBadges(userId?: string | null): Record<string, StoredBadgeInfo> {
  if (typeof window === "undefined") return {};
  const safeId = userId || "student_guest";
  const key = `${BADGE_STORAGE_PREFIX}${safeId}`;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    console.error("[badgeStorage] Lỗi đọc localStorage:", e);
    return {};
  }
}

/**
 * Mở khóa và đánh dấu đã chúc mừng cho 1 huy hiệu.
 * Trả về:
 * - `true`: Nếu đây là lần ĐẦU TIÊN mở khóa (được phép bung popup ăn mừng).
 * - `false`: Nếu huy hiệu đã từng được mở khóa và chúc mừng trước đó (KHÔNG hiển thị lại).
 */
export function saveStoredBadge(badgeId: string, userId?: string | null): boolean {
  if (typeof window === "undefined") return false;
  const safeId = userId || "student_guest";
  const key = `${BADGE_STORAGE_PREFIX}${safeId}`;

  try {
    const current = getStoredBadges(userId);
    // Nếu đã tồn tại và đã từng được ăn mừng -> không hiển thị lại (chỉ 1 lần duy nhất)
    if (current[badgeId]?.celebrated) {
      return false;
    }

    current[badgeId] = {
      unlockedAt: new Date().toISOString(),
      celebrated: true,
    };

    localStorage.setItem(key, JSON.stringify(current));
    return true; // Lần đầu tiên đạt được!
  } catch (e) {
    console.error("[badgeStorage] Lỗi ghi localStorage:", e);
    return false;
  }
}

/**
 * Đặt lại trạng thái mở khóa của huy hiệu (phục vụ test lại)
 */
export function resetStoredBadge(badgeId?: string, userId?: string | null): void {
  if (typeof window === "undefined") return;
  const safeId = userId || "student_guest";
  const key = `${BADGE_STORAGE_PREFIX}${safeId}`;
  try {
    if (!badgeId) {
      localStorage.removeItem(key);
    } else {
      const current = getStoredBadges(userId);
      delete current[badgeId];
      localStorage.setItem(key, JSON.stringify(current));
    }
  } catch (e) {
    console.error("[badgeStorage] Lỗi xóa localStorage:", e);
  }
}

/**
 * Kết hợp danh mục huy hiệu mẫu với trạng thái mở khóa thực tế từ LocalStorage
 */
export function getMergedBadges(userId?: string | null): BadgeItem[] {
  const stored = getStoredBadges(userId);
  return DEFAULT_BADGES.map((b) => {
    const info = stored[b.id];
    if (info) {
      return {
        ...b,
        unlocked: true,
        earnedAt: new Date(info.unlockedAt).toLocaleDateString("vi-VN"),
      };
    }
    return {
      ...b,
      unlocked: false,
    };
  });
}
