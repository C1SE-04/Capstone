"use client";

import { useSession, signOut } from "next-auth/react";
import { useEffect, useState } from "react";

// Kiểu dữ liệu trả về từ FastAPI
interface ApiResponse {
  message?: string;
  user?: string;
  error?: string;
  [key: string]: unknown;
}

type FetchStatus = "idle" | "loading" | "success" | "error";

/**
 * Trang Dashboard - được bảo vệ bởi middleware.ts
 * Gọi API /api/protected của FastAPI, truyền kèm token JWT để xác thực.
 */
export default function DashboardPage() {
  const { data: session } = useSession();
  const [apiResponse, setApiResponse] = useState<ApiResponse | null>(null);
  const [status, setStatus] = useState<FetchStatus>("idle");

  const callProtectedApi = async () => {
    setStatus("loading");
    setApiResponse(null);

    try {
      // Lấy token từ session (next-auth lưu accessToken vào session.accessToken)
      const token = (session as { accessToken?: string })?.accessToken;

      const response = await fetch("http://localhost:8000/api/protected", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          // Truyền token vào header Authorization để FastAPI xác thực
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      const data: ApiResponse = await response.json();

      if (!response.ok) {
        setApiResponse({ error: data?.message || `HTTP ${response.status}: ${response.statusText}` });
        setStatus("error");
      } else {
        setApiResponse(data);
        setStatus("success");
      }
    } catch (err) {
      setApiResponse({
        error: err instanceof Error ? err.message : "Không thể kết nối tới Backend. Hãy chắc chắn FastAPI đang chạy tại http://localhost:8000",
      });
      setStatus("error");
    }
  };

  // Tự động gọi API khi trang load xong và đã có session
  useEffect(() => {
    if (session) {
      callProtectedApi();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Dashboard</h1>
            <p className="text-gray-500 mt-1">Trang được bảo vệ bởi Middleware</p>
          </div>
          <button
            onClick={() => signOut({ callbackUrl: "/" })}
            className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all active:scale-95 text-sm"
          >
            Đăng xuất
          </button>
        </div>

        {/* Thông tin người dùng */}
        {session?.user && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 mb-6 flex items-center gap-4">
            {session.user.image && (
              <img
                src={session.user.image}
                alt="Avatar"
                className="w-14 h-14 rounded-full border-2 border-indigo-200"
              />
            )}
            <div>
              <p className="font-semibold text-gray-800 text-lg">{session.user.name}</p>
              <p className="text-gray-500 text-sm">{session.user.email}</p>
              <span className="inline-block mt-1 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                ✓ Đã xác thực
              </span>
            </div>
          </div>
        )}

        {/* CORS Test - Gọi FastAPI */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="font-semibold text-gray-800">🔗 Test kết nối Backend (CORS)</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                GET <code className="bg-gray-100 px-1 rounded">http://localhost:8000/api/protected</code>
              </p>
            </div>
            <button
              onClick={callProtectedApi}
              disabled={status === "loading"}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-all active:scale-95 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {status === "loading" ? "⏳ Đang gọi..." : "🚀 Gọi API"}
            </button>
          </div>

          {/* Trạng thái */}
          {status === "idle" && (
            <div className="text-center py-8 text-gray-400 text-sm">
              Nhấn &quot;Gọi API&quot; để kiểm tra kết nối với FastAPI Backend
            </div>
          )}

          {status === "loading" && (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-gray-500 text-sm mt-2">Đang gửi request...</p>
            </div>
          )}

          {/* Kết quả thành công */}
          {status === "success" && apiResponse && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                <span className="text-green-700 text-sm font-medium">Kết nối thành công! CORS hoạt động bình thường.</span>
              </div>
              <pre className="bg-gray-900 text-green-400 text-sm p-4 rounded-lg overflow-auto max-h-60 font-mono">
                {JSON.stringify(apiResponse, null, 2)}
              </pre>
            </div>
          )}

          {/* Kết quả lỗi */}
          {status === "error" && apiResponse && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                <span className="text-red-700 text-sm font-medium">Có lỗi xảy ra</span>
              </div>
              <pre className="bg-gray-900 text-red-400 text-sm p-4 rounded-lg overflow-auto max-h-60 font-mono">
                {JSON.stringify(apiResponse, null, 2)}
              </pre>
            </div>
          )}
        </div>

        {/* Ghi chú */}
        <p className="text-center text-xs text-gray-400 mt-6">
          Trang này chỉ hiển thị khi đã đăng nhập — được bảo vệ bởi <code>middleware.ts</code>
        </p>
      </div>
    </div>
  );
}
