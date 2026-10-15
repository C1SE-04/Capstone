/**
 * Task T6.13 - authFetch wrapper: Xử lý cờ SESSION_STALE tự động.
 *
 * Khi Backend trả về 401 kèm { error: "SESSION_STALE" }:
 *   1. Lấy refresh_token từ NextAuth session hiện tại.
 *   2. Gọi /refresh endpoint của Backend Python để lấy access_token mới (mang session_version và grade mới).
 *   3. Gọi update() của NextAuth để đồng bộ cookie session mà KHÔNG logout người dùng.
 *   4. Tự động retry lại request ban đầu với token mới và grade_level mới (nếu có trong body).
 *
 * Race condition safety:
 *   - Dùng singleton promise (pendingRefresh) để đảm bảo nếu nhiều request cùng gặp
 *     SESSION_STALE tại một thời điểm, chỉ có duy nhất 1 request /refresh được gửi đi.
 */

export interface RefreshResult {
  token: string;
  grade?: number;
}

let pendingRefresh: Promise<RefreshResult | null> | null = null;

async function doRefresh(): Promise<RefreshResult | null> {
  try {
    const nextAuth = await import("next-auth/react");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const update = (nextAuth as any).update;
    const getSession = nextAuth.getSession;

    // 1. Lấy refresh_token từ NextAuth session hiện tại
    const currentSession = await getSession();
    const refreshToken = (
      currentSession as { refresh_token?: string } | null
    )?.refresh_token;

    if (!refreshToken) {
      console.warn(
        "[authFetch] Không tìm thấy refresh_token trong session hiện tại."
      );
      return null;
    }

    const BACKEND_URL =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

    // 2. Gửi request refresh lên Backend
    const refreshRes = await fetch(`${BACKEND_URL}/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!refreshRes.ok) {
      // Trường hợp tab khác đã refresh trước khiến token này bị thu hồi:
      // Thử đọc lại session từ cookie NextAuth
      console.warn(
        `[authFetch] /refresh trả về ${refreshRes.status}. Kiểm tra lại session cookie...`
      );
      const freshSession = await getSession();
      const fallbackToken = (
        freshSession as { access_token?: string } | null
      )?.access_token;
      const fallbackGrade = (
        freshSession as { user?: { grade_level?: number } } | null
      )?.user?.grade_level;
      if (fallbackToken) {
        return {
          token: fallbackToken,
          grade: fallbackGrade ? Number(fallbackGrade) : undefined,
        };
      }
      return null;
    }

    const refreshData = await refreshRes.json();
    const newAccessToken: string = refreshData.access_token;
    const newRefreshToken: string = refreshData.refresh_token;
    const newGrade = refreshData.grade;

    if (!newAccessToken) {
      return null;
    }

    // 3. Đồng bộ lại JWT session của NextAuth
    if (typeof update === "function") {
      await update({
        access_token: newAccessToken,
        refresh_token: newRefreshToken,
        grade_level: newGrade,
      });
    }

    console.info("[authFetch] Tự động refresh token thành công ✓ (Lớp mới:", newGrade, ")");
    return {
      token: newAccessToken,
      grade: newGrade !== undefined ? Number(newGrade) : undefined,
    };
  } catch (err) {
    console.error("[authFetch] Lỗi khi thực hiện refresh session:", err);
    return null;
  }
}

/**
 * Hàm fetch wrapper tự động bắt lỗi SESSION_STALE và refresh token.
 */
export async function authFetch(
  url: RequestInfo | URL,
  options: RequestInit = {}
): Promise<Response> {
  // Lần gọi đầu tiên
  const response = await fetch(url, options);

  // Chỉ can thiệp khi gặp 401
  if (response.status !== 401) {
    return response;
  }

  // Kiểm tra cờ SESSION_STALE trong body
  let isStale = false;
  try {
    const body = await response.clone().json();
    isStale =
      body?.error === "SESSION_STALE" || body?.detail === "SESSION_STALE";
  } catch {
    // Body không phải JSON -> không phải SESSION_STALE
  }

  if (!isStale) {
    return response;
  }

  console.warn(
    "[authFetch] Phát hiện SESSION_STALE từ Backend — Đang tự động refresh..."
  );

  // Singleton lock tránh refresh trùng lặp
  if (!pendingRefresh) {
    pendingRefresh = doRefresh().finally(() => {
      pendingRefresh = null;
    });
  }

  const refreshResult = await pendingRefresh;

  if (!refreshResult || !refreshResult.token) {
    // Không refresh được token mới -> trả về 401 ban đầu
    return response;
  }

  // Chuẩn bị options cho lượt retry với token mới
  const newHeaders = new Headers(options.headers || {});
  newHeaders.set("Authorization", `Bearer ${refreshResult.token}`);

  // Cập nhật lại body nếu có chứa grade_level cũ
  let retryBody = options.body;
  if (typeof retryBody === "string" && retryBody.includes("grade_level")) {
    try {
      const parsed = JSON.parse(retryBody);
      if (refreshResult.grade !== undefined) {
        parsed.grade_level = Number(refreshResult.grade);
        retryBody = JSON.stringify(parsed);
      }
    } catch {
      // Không parse được body JSON -> giữ nguyên
    }
  }

  const retryOptions: RequestInit = {
    ...options,
    headers: newHeaders,
    body: retryBody,
  };

  return fetch(url, retryOptions);
}
