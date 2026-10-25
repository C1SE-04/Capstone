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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type UpdateSessionFn = (data?: any) => Promise<any>;

let pendingRefresh: Promise<RefreshResult | null> | null = null;
let lastRefreshTime = 0;

/**
 * Hàm chủ động làm mới session (gọi khi tab được focus hoặc khi cần đồng bộ giữa tab thường và tab ẩn danh).
 */
export async function refreshSession(
  updateFn?: UpdateSessionFn,
  force = false
): Promise<RefreshResult | null> {
  const now = Date.now();
  // Giới hạn tần suất: tối thiểu 2 giây giữa các lần refresh để tránh spam request
  if (!force && now - lastRefreshTime < 2000) {
    return pendingRefresh || null;
  }

  if (!pendingRefresh) {
    lastRefreshTime = now;
    pendingRefresh = doRefresh(updateFn, force).finally(() => {
      pendingRefresh = null;
    });
  } else if (updateFn && force) {
    pendingRefresh.then(async (res) => {
      if (res && res.grade !== undefined) {
        try {
          await updateFn({
            access_token: res.token,
            grade_level: res.grade,
          });
        } catch {
          // Bỏ qua lỗi update
        }
      }
    });
  }
  return pendingRefresh;
}

async function doRefresh(
  updateFn?: UpdateSessionFn,
  force = false
): Promise<RefreshResult | null> {
  try {
    const nextAuth = await import("next-auth/react");
    const getSession = nextAuth.getSession;

    // 1. Lấy thông tin session hiện tại
    const currentSession = await getSession();
    const refreshToken = (
      currentSession as { refresh_token?: string } | null
    )?.refresh_token;
    const currentAccessToken = (
      currentSession as { access_token?: string } | null
    )?.access_token;
    const currentRole = (
      currentSession as { user?: { role?: string } } | null
    )?.user?.role;
    const currentGrade = (
      currentSession as { user?: { grade_level?: number } } | null
    )?.user?.grade_level;

    // Khi refresh on focus thông thường (không phải force do SESSION_STALE):
    // MONITOR và ADMIN không cần làm mới session trên focus vì không đổi khối lớp
    if (!force && currentRole && currentRole !== "STUDENT") {
      return null;
    }

    const BACKEND_URL =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

    // 2. Gửi request refresh lên Backend nếu có refresh_token
    if (refreshToken) {
      const refreshRes = await fetch(`${BACKEND_URL}/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        const newAccessToken: string = refreshData.access_token;
        const newRefreshToken: string = refreshData.refresh_token;
        const newGrade = refreshData.grade;

        if (newAccessToken) {
          const gradeChanged =
            newGrade !== undefined &&
            (currentGrade === undefined || Number(newGrade) !== Number(currentGrade));

          // 3. Chỉ đồng bộ lại JWT session của NextAuth nếu bị SESSION_STALE (force) hoặc khối lớp thực sự thay đổi
          if (typeof updateFn === "function" && (force || gradeChanged)) {
            try {
              await updateFn({
                access_token: newAccessToken,
                refresh_token: newRefreshToken,
                grade_level: newGrade,
              });
            } catch (err) {
              console.warn("[authFetch] Lỗi khi gọi updateFn:", err);
            }
          }

          if (gradeChanged) {
            console.info(
              "[authFetch] Tự động cập nhật khối lớp mới thành công ✓ (Lớp mới:",
              newGrade,
              ")"
            );
          }
          return {
            token: newAccessToken,
            grade: newGrade !== undefined ? Number(newGrade) : undefined,
          };
        }
      }
    }

    // 4. Fallback: Tra cứu trực tiếp /users/me từ DB bằng access_token hiện tại
    if (currentAccessToken) {
      try {
        const userRes = await fetch(`${BACKEND_URL}/users/me`, {
          headers: { Authorization: `Bearer ${currentAccessToken}` },
        });
        if (userRes.ok) {
          const userData = await userRes.json();
          if (userData?.grade !== undefined) {
            const gradeChanged =
              currentGrade === undefined ||
              Number(userData.grade) !== Number(currentGrade);

            if (typeof updateFn === "function" && (force || gradeChanged)) {
              await updateFn({ grade_level: Number(userData.grade) });
            }
            return {
              token: currentAccessToken,
              grade: Number(userData.grade),
            };
          }
        }
      } catch {
        // Bỏ qua lỗi fallback
      }
    }

    return null;
  } catch (err) {
    console.error("[authFetch] Lỗi khi thực hiện refresh session:", err);
    return null;
  }
}

/**
 * Hàm fetch wrapper tự động gắn Bearer token từ session hiện tại nếu thiếu,
 * và tự động bắt lỗi SESSION_STALE để refresh token.
 */
export async function authFetch(
  url: RequestInfo | URL,
  options: RequestInit = {}
): Promise<Response> {
  const reqHeaders = new Headers(options.headers || {});

  // Tự động đính kèm Authorization Bearer token nếu caller chưa truyền
  if (!reqHeaders.has("Authorization")) {
    try {
      const nextAuth = await import("next-auth/react");
      const currentSession = await nextAuth.getSession();
      const token = (currentSession as { access_token?: string } | null)?.access_token;
      if (token) {
        reqHeaders.set("Authorization", `Bearer ${token}`);
      }
    } catch {
      // Bỏ qua nếu môi trường không gọi được getSession
    }
  }

  const initialOptions: RequestInit = {
    ...options,
    headers: reqHeaders,
  };

  // Lần gọi đầu tiên
  const response = await fetch(url, initialOptions);

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
    pendingRefresh = doRefresh(undefined, true).finally(() => {
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
