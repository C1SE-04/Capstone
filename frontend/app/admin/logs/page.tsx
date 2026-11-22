"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { RefreshCw } from "lucide-react";

/**
 * US 9.5 (Task T9.22): Thay thế trang Logs cũ sang Trung Tâm Quản Trị Báo Lỗi & Sự Cố (/admin/errors).
 * Tự động chuyển hướng toàn bộ người dùng và query parameters sang /admin/errors?search=...
 */
function AdminLogsRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const term =
      searchParams.get("search") ||
      searchParams.get("email") ||
      searchParams.get("user_id") ||
      "";

    const targetUrl = term
      ? `/admin/errors?search=${encodeURIComponent(term)}`
      : "/admin/errors";

    router.replace(targetUrl);
  }, [router, searchParams]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3 text-[#78716C]">
      <RefreshCw className="w-8 h-8 text-[#C1762A] animate-spin" />
      <p className="text-sm font-semibold">
        Đang chuyển hướng sang Trung Tâm Quản Trị Báo Lỗi & Sự Cố (/admin/errors)...
      </p>
    </div>
  );
}

export default function AdminLogsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[50vh]">
          <RefreshCw className="w-8 h-8 text-[#C1762A] animate-spin" />
        </div>
      }
    >
      <AdminLogsRedirect />
    </Suspense>
  );
}
