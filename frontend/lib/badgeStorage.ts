/**
 * File: frontend/lib/badgeStorage.ts
 * Quản lý lưu trữ thành tựu & huy hiệu học sinh theo US 7.2 (Game hóa) & US 9.2 (Đồng bộ qua DB).
 *
 * Nhiệm vụ:
 * - [Task T9.8]: Tải danh sách badge từ backend DB khi khởi tạo session, chặn triệt để
 *   việc bắn lại popup ăn mừng cho các cúp đã đạt khi đổi máy / mở tab ẩn danh.
 * - [Task T9.8b]: Migrate tự động đọc badge cũ trong localStorage và đồng bộ lên
 *   endpoint POST /api/user/badges/unlock sau khi đăng nhập.
 */

import { BadgeItem, DEFAULT_BADGES } from "@/components/chat/BadgeModal";
import { authFetch } from "@/lib/authFetch";

export const BADGE_STORAGE_PREFIX = "socratic_unlocked_badges_";
export const BADGE_MIGRATED_PREFIX = "socratic_badges_migrated_";
export const BADGE_SYNC_EVENT = "SOCRATIC_BADGES_SYNCED";

export interface StoredBadgeInfo {
  unlockedAt: string;
  celebrated: boolean; // Đã từng hiển thị modal chúc mừng hay chưa (nếu true: KHÔNG bung lại modal)
  syncedToDb?: boolean; // Đã được đồng bộ thành công lên backend DB hay chưa
}

export interface BackendBadgeRecord {
  id?: number | string;
  user_id?: string;
  badge_id: string;
  unlocked_at?: string;
}

export interface BackendBadgeListResponse {
  success?: boolean;
  badge_ids?: string[];
  badges?: BackendBadgeRecord[];
  error?: string;
}

export interface BackendBadgeUnlockResponse {
  success?: boolean;
  message?: string;
  unlocked_badge_ids?: string[];
  newly_unlocked_ids?: string[];
  is_first_time?: boolean;
  error?: string;
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
 * Ghi đè danh sách huy hiệu vào LocalStorage và phát sự kiện đồng bộ
 */
export function setStoredBadges(
  badges: Record<string, StoredBadgeInfo>,
  userId?: string | null
): void {
  if (typeof window === "undefined") return;
  const safeId = userId || "student_guest";
  const key = `${BADGE_STORAGE_PREFIX}${safeId}`;
  try {
    localStorage.setItem(key, JSON.stringify(badges));
    window.dispatchEvent(
      new CustomEvent(BADGE_SYNC_EVENT, {
        detail: { userId: safeId, badges },
      })
    );
  } catch (e) {
    console.error("[badgeStorage] Lỗi ghi localStorage:", e);
  }
}

/**
 * Gửi yêu cầu mở khóa 1 huy hiệu lên backend DB
 */
export async function unlockBadgeOnBackend(
  badgeId: string,
  userId?: string | null
): Promise<BackendBadgeUnlockResponse | null> {
  if (typeof window === "undefined") return null;
  const safeId = userId || "student_guest";
  if (safeId === "student_guest") return null;

  try {
    // Ưu tiên gọi Next.js BFF proxy /api/user/badges/unlock
    const res = await authFetch("/api/user/badges/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ badge_id: badgeId }),
    });

    if (res.ok) {
      const data: BackendBadgeUnlockResponse = await res.json();
      return data;
    }

    // Fallback gọi trực tiếp backend nếu Next.js BFF không phản hồi
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
    const directRes = await authFetch(`${backendUrl}/api/user/badges/unlock`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ badge_id: badgeId }),
    });

    if (directRes.ok) {
      const directData: BackendBadgeUnlockResponse = await directRes.json();
      return directData;
    }
  } catch (err) {
    console.warn("[badgeStorage] Lỗi khi lưu badge lên DB:", err);
  }

  return null;
}

/**
 * [Task T9.8] Tải danh sách huy hiệu từ Backend DB về và lưu vào LocalStorage.
 * Đánh dấu toàn bộ các huy hiệu từ DB là `celebrated: true`
 * -> Chặn triệt để việc bắn lại popup ăn mừng cho các cúp đã đạt khi đổi máy hay mở tab ẩn danh.
 */
export async function syncBadgesFromDB(
  userId?: string | null
): Promise<Record<string, StoredBadgeInfo>> {
  if (typeof window === "undefined") return {};
  const safeId = userId || "student_guest";
  const current = getStoredBadges(safeId);

  // Học sinh dùng thử hoặc khách chưa đăng nhập: chỉ đọc local
  if (safeId === "student_guest") {
    return current;
  }

  try {
    let res = await authFetch("/api/user/badges", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      res = await authFetch(`${backendUrl}/api/user/badges`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
    }

    if (res.ok) {
      const data: BackendBadgeListResponse = await res.json();
      const badgeIds =
        data.badge_ids ||
        (Array.isArray(data.badges) ? data.badges.map((b) => b.badge_id) : []);

      let hasChanges = false;
      const updated: Record<string, StoredBadgeInfo> = { ...current };

      badgeIds.forEach((id) => {
        const backendRecord = data.badges?.find((b) => b.badge_id === id);
        const unlockedAt =
          backendRecord?.unlocked_at ||
          updated[id]?.unlockedAt ||
          new Date().toISOString();

        // Cúp đã có trong DB: BẮT BUỘC celebrated: true để chặn popup bắn lại
        if (!updated[id] || !updated[id].celebrated || !updated[id].syncedToDb) {
          updated[id] = {
            unlockedAt,
            celebrated: true,
            syncedToDb: true,
          };
          hasChanges = true;
        }
      });

      if (hasChanges) {
        setStoredBadges(updated, safeId);
      }

      return updated;
    }
  } catch (err) {
    console.warn("[badgeStorage] Lỗi đồng bộ danh sách badge từ DB:", err);
  }

  return current;
}

/**
 * [Task T9.8b] Hàm migrate tự động đọc badge cũ trong localStorage
 * và đồng bộ lên endpoint POST /api/user/badges/unlock sau khi đăng nhập.
 *
 * @param userId ID của người dùng vừa đăng nhập
 * @returns kết quả migrate { success, migrated: string[], count: number }
 */
export async function migrateLocalStorageBadgesToDB(
  userId?: string | null
): Promise<{ success: boolean; migrated: string[]; count: number }> {
  if (typeof window === "undefined") {
    return { success: false, migrated: [], count: 0 };
  }

  const safeId = userId || "student_guest";
  if (safeId === "student_guest") {
    return { success: false, migrated: [], count: 0 };
  }

  try {
    // 1. Gom các badge ID từ localStorage của user hiện tại
    const userBadges = getStoredBadges(safeId);

    // Đồng thời kiểm tra xem có badge của phiên guest trước khi đăng nhập không
    const guestBadges = getStoredBadges("student_guest");

    const badgeIdsSet = new Set<string>();

    Object.keys(userBadges).forEach((bid) => {
      if (userBadges[bid]?.unlockedAt) {
        badgeIdsSet.add(bid);
      }
    });

    Object.keys(guestBadges).forEach((bid) => {
      if (guestBadges[bid]?.unlockedAt) {
        badgeIdsSet.add(bid);
      }
    });

    const badgeIdsToMigrate = Array.from(badgeIdsSet);

    // Không có badge nào cần migrate
    if (badgeIdsToMigrate.length === 0) {
      localStorage.setItem(`${BADGE_MIGRATED_PREFIX}${safeId}`, "true");
      return { success: true, migrated: [], count: 0 };
    }

    // 2. Gửi request đồng bộ hàng loạt lên backend endpoint POST /api/user/badges/unlock
    const payload = { badge_ids: badgeIdsToMigrate };

    let res = await authFetch("/api/user/badges/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      res = await authFetch(`${backendUrl}/api/user/badges/unlock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    }

    if (res.ok) {
      const data: BackendBadgeUnlockResponse = await res.json();

      // Cập nhật lại localStorage với trạng thái đã đồng bộ và celebrated = true
      const mergedBadges: Record<string, StoredBadgeInfo> = { ...userBadges };
      badgeIdsToMigrate.forEach((bid) => {
        mergedBadges[bid] = {
          unlockedAt:
            userBadges[bid]?.unlockedAt ||
            guestBadges[bid]?.unlockedAt ||
            new Date().toISOString(),
          celebrated: true, // Huy hiệu migrate từ trước -> không bắn popup
          syncedToDb: true,
        };
      });

      setStoredBadges(mergedBadges, safeId);

      // Đánh dấu đã hoàn thành migrate cho user này
      localStorage.setItem(`${BADGE_MIGRATED_PREFIX}${safeId}`, "true");

      // Nếu có guest badges, dọn dẹp để tránh lẫn lộn session sau
      try {
        localStorage.removeItem(`${BADGE_STORAGE_PREFIX}student_guest`);
      } catch {
        // ignore
      }

      console.log(
        `[badgeStorage] Đã migrate thành công ${badgeIdsToMigrate.length} huy hiệu lên backend DB cho user ${safeId}`,
        data
      );

      return {
        success: true,
        migrated: badgeIdsToMigrate,
        count: badgeIdsToMigrate.length,
      };
    }
  } catch (err) {
    console.error("[badgeStorage] Lỗi trong quá trình migrate badge lên DB:", err);
  }

  return { success: false, migrated: [], count: 0 };
}

/**
 * [Task T9.8] Hàm tổng hợp khởi tạo session:
 * 1. Tự động chạy migrate badge cũ (nếu có)
 * 2. Tải danh sách badge từ backend DB về
 * 3. Đánh dấu celebrated = true cho các cúp đã đạt -> Chặn tuyệt đối bắn lại popup
 * 4. Trả về danh sách huy hiệu chuẩn để hiển thị giao diện
 */
export async function initBadgeSession(
  userId?: string | null
): Promise<BadgeItem[]> {
  const safeId = userId || "student_guest";

  if (typeof window === "undefined") {
    return getMergedBadges(safeId);
  }

  if (safeId !== "student_guest") {
    // 1. Chạy migration các badge cũ từ localStorage
    await migrateLocalStorageBadgesToDB(safeId);

    // 2. Tải danh sách từ DB và cập nhật local cache (celebrated: true)
    await syncBadgesFromDB(safeId);
  }

  return getMergedBadges(safeId);
}

/**
 * Mở khóa và đánh dấu đã chúc mừng cho 1 huy hiệu.
 * Trả về:
 * - `true`: Nếu đây là lần ĐẦU TIÊN mở khóa (được phép bung popup ăn mừng).
 * - `false`: Nếu huy hiệu đã từng được mở khóa và chúc mừng trước đó (KHÔNG hiển thị lại).
 */
export function saveStoredBadge(
  badgeId: string,
  userId?: string | null
): boolean {
  if (typeof window === "undefined") return false;
  const safeId = userId || "student_guest";
  const key = `${BADGE_STORAGE_PREFIX}${safeId}`;

  try {
    const current = getStoredBadges(safeId);
    // Nếu đã tồn tại và đã từng được ăn mừng -> không hiển thị lại (chỉ 1 lần duy nhất)
    if (current[badgeId]?.celebrated) {
      return false;
    }

    current[badgeId] = {
      unlockedAt: new Date().toISOString(),
      celebrated: true,
      syncedToDb: false,
    };

    localStorage.setItem(key, JSON.stringify(current));

    // Phát sự kiện cập nhật giao diện
    window.dispatchEvent(
      new CustomEvent(BADGE_SYNC_EVENT, {
        detail: { userId: safeId, badges: current },
      })
    );

    // Bất đồng bộ lưu lên Backend DB
    if (safeId !== "student_guest") {
      unlockBadgeOnBackend(badgeId, safeId).then((res) => {
        if (res?.success) {
          const fresh = getStoredBadges(safeId);
          if (fresh[badgeId]) {
            fresh[badgeId].syncedToDb = true;
            localStorage.setItem(key, JSON.stringify(fresh));
          }
        }
      });
    }

    return true; // Lần đầu tiên đạt được!
  } catch (e) {
    console.error("[badgeStorage] Lỗi ghi localStorage:", e);
    return false;
  }
}

/**
 * Phiên bản async của mở khóa huy hiệu, trực tiếp hỏi backend DB xem có phải lần đầu không
 */
export async function unlockBadgeAsync(
  badgeId: string,
  userId?: string | null
): Promise<{ isFirstTime: boolean; badge?: BadgeItem }> {
  const safeId = userId || "student_guest";

  // Kiểm tra trước trong local cache
  const current = getStoredBadges(safeId);
  if (current[badgeId]?.celebrated) {
    return { isFirstTime: false };
  }

  // Nếu là guest: lưu local bình thường
  if (safeId === "student_guest") {
    const isFirst = saveStoredBadge(badgeId, safeId);
    const badges = getMergedBadges(safeId);
    return {
      isFirstTime: isFirst,
      badge: badges.find((b) => b.id === badgeId),
    };
  }

  // Gọi endpoint backend
  try {
    const dbRes = await unlockBadgeOnBackend(badgeId, safeId);
    if (dbRes && typeof dbRes.is_first_time === "boolean") {
      // Backend phản hồi chính xác trạng thái
      const isFirst = dbRes.is_first_time;
      const updated = getStoredBadges(safeId);
      updated[badgeId] = {
        unlockedAt: updated[badgeId]?.unlockedAt || new Date().toISOString(),
        celebrated: true,
        syncedToDb: true,
      };
      setStoredBadges(updated, safeId);

      const badges = getMergedBadges(safeId);
      return {
        isFirstTime: isFirst,
        badge: badges.find((b) => b.id === badgeId),
      };
    }
  } catch (err) {
    console.warn("[badgeStorage] Lỗi unlockBadgeAsync, fallback sang saveStoredBadge:", err);
  }

  // Fallback nếu mất kết nối backend
  const isFirst = saveStoredBadge(badgeId, safeId);
  const badges = getMergedBadges(safeId);
  return {
    isFirstTime: isFirst,
    badge: badges.find((b) => b.id === badgeId),
  };
}

/**
 * Đặt lại trạng thái mở khóa của huy hiệu (phục vụ test lại)
 */
export function resetStoredBadge(
  badgeId?: string,
  userId?: string | null
): void {
  if (typeof window === "undefined") return;
  const safeId = userId || "student_guest";
  const key = `${BADGE_STORAGE_PREFIX}${safeId}`;
  try {
    if (!badgeId) {
      localStorage.removeItem(key);
      localStorage.removeItem(`${BADGE_MIGRATED_PREFIX}${safeId}`);
    } else {
      const current = getStoredBadges(safeId);
      delete current[badgeId];
      localStorage.setItem(key, JSON.stringify(current));
    }
    window.dispatchEvent(
      new CustomEvent(BADGE_SYNC_EVENT, {
        detail: { userId: safeId, badgeId },
      })
    );
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
