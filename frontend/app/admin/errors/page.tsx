"use client";

import { useState, useMemo, useCallback, useEffect, useSyncExternalStore, Suspense } from "react";
import { useSession } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  AlertTriangle,
  Search,
  RefreshCw,
  Clock,
  User,
  CheckCircle2,
  X,
  ChevronLeft,
  ChevronRight,
  Code,
  AlertOctagon,
  Info,
  Sparkles,
  Eye,
  Activity,
  CheckCircle,
  WifiOff,
} from "lucide-react";

import {
  SystemErrorItem,
  SystemErrorsListResponse,
  SystemErrorSeverity,
  SystemErrorType,
  SystemErrorStatus,
} from "@/types/admin";
import ErrorDetailDrawer from "@/components/admin/ErrorDetailDrawer";

// ==============================================================================
// 1. DỮ LIỆU MẪU DỰ PHÒNG THỬ NGHIỆM KHI BACKEND CHƯA CHẠY (DEMO PREVIEW)
// ==============================================================================
const DEMO_PREVIEW_ERRORS: SystemErrorItem[] = [
  {
    id: "err_demo_001",
    error_code: "UR_8A1B2C3D",
    error_type: "USER_REPORT",
    severity: "INFO",
    message: "[Báo lỗi học sinh] AI giải sai kiến thức - Đề bài phép nhân đa thức tính sai dấu ở bước 2",
    stack_trace: null,
    endpoint: "/chat/message",
    request_payload: JSON.stringify(
      {
        reason: "AI giải sai kiến thức",
        detail: "Bước phân tích (x - 2)(x + 3) bị nhầm dấu thành x^2 - 5x + 6",
        message_id: "msg_chat_98231",
        session_id: "sess_math_8a",
        client_context: {
          device: "iPad Pro 11-inch",
          os: "iPadOS 17.5",
          browser: "Mobile Safari 17.5",
          screen: "2388 x 1668",
          ip: "192.168.1.45",
        },
        reported_at: "2026-11-04T08:15:20Z",
      },
      null,
      2
    ),
    user_id: "std_1004",
    user_email: "linh.vu@example.com",
    username: "vu_thuy_linh",
    status: "OPEN",
    resolved_at: null,
    resolved_by: null,
    resolved_note: null,
    created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
  {
    id: "err_demo_002",
    error_code: "ERR_500_A94F1C7E",
    error_type: "CRASH_500",
    severity: "CRITICAL",
    message: "ZeroDivisionError: float division by zero in independence_score evaluator",
    stack_trace: `Traceback (most recent call last):
  File "backend/middleware.py", line 142, in dispatch
    response = await call_next(request)
  File "backend/routers/chat.py", line 289, in send_chat_message
    score = calculate_independence_score(problem_id, hints_used, total_steps)
  File "backend/independence.py", line 78, in calculate_independence_score
    rate = correct_steps / (total_steps - invalid_turns)
ZeroDivisionError: float division by zero`,
    endpoint: "/chat/message",
    request_payload: JSON.stringify(
      {
        problem_id: "prob_geo_802",
        message: "Em đã hiểu định lý Thales rồi ạ",
        token: "***MASKED***",
        client_context: {
          device: "Máy tính xách tay (Laptop)",
          os: "Windows 11 Home 64-bit",
          browser: "Google Chrome 129.0",
          screen: "1920 x 1080 (FHD)",
          ip: "127.0.0.1",
        },
      },
      null,
      2
    ),
    user_id: "std_1009",
    user_email: "an.dinh@example.com",
    username: "hoai_an_math",
    status: "OPEN",
    resolved_at: null,
    resolved_by: null,
    resolved_note: null,
    created_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
  },
  {
    id: "err_demo_003",
    error_code: "ERR_TIMEOUT_3F8D2A10",
    error_type: "AI_TIMEOUT",
    severity: "WARNING",
    message: "Gemini API call timed out after 30.0s during Socratic prompt generation",
    stack_trace: `Traceback (most recent call last):
  File "backend/orchestrator.py", line 312, in generate_socratic_response
    res = await asyncio.wait_for(gemini_client.generate(), timeout=30.0)
  File "asyncio/tasks.py", line 452, in wait_for
    raise exceptions.TimeoutError()
TimeoutError: Request to Google Gemini API exceeded 30000ms threshold`,
    endpoint: "/chat/message",
    request_payload: JSON.stringify(
      {
        grade: 8,
        topic: "Phương trình bậc nhất một ẩn",
        student_query: "Giải thích lại cho em bước quy đồng mẫu số",
        client_context: {
          device: "Máy tính để bàn (Workstation)",
          os: "macOS Sonoma 14.6",
          browser: "Safari 17.4",
          screen: "2560 x 1440 (2K)",
          ip: "10.0.0.12",
        },
      },
      null,
      2
    ),
    user_id: "std_1012",
    user_email: "huy.doan@example.com",
    username: "giahuy_math",
    status: "OPEN",
    resolved_at: null,
    resolved_by: null,
    resolved_note: null,
    created_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
  },
];

// ==============================================================================
// 2. HELPER COMPONENTS & BADGES (AC 9.5.4 & AC 9.5.6)
// ==============================================================================

function SeverityBadge({ severity }: { severity: SystemErrorSeverity }) {
  const normalized = severity?.toUpperCase();

  if (normalized === "CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-red-100 text-red-800 border border-red-300 shadow-xs">
        <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
        CRITICAL
      </span>
    );
  }

  if (normalized === "WARNING") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300 shadow-xs">
        <span className="w-2 h-2 rounded-full bg-amber-500" />
        WARNING
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-blue-100 text-blue-800 border border-blue-300 shadow-xs">
      <span className="w-2 h-2 rounded-full bg-blue-500" />
      INFO
    </span>
  );
}

function ErrorTypeBadge({ type }: { type: SystemErrorType }) {
  const normalized = type?.toUpperCase();

  let label = normalized;
  let bgClasses = "bg-stone-100 text-stone-800 border-stone-300";

  if (normalized === "CRASH_500") {
    label = "Crash 500";
    bgClasses = "bg-rose-50 text-rose-700 border-rose-200";
  } else if (normalized === "AI_TIMEOUT") {
    label = "AI Timeout";
    bgClasses = "bg-orange-50 text-orange-700 border-orange-200";
  } else if (normalized === "USER_REPORT") {
    label = "Báo Lỗi Học Sinh";
    bgClasses = "bg-sky-50 text-sky-700 border-sky-200";
  } else if (normalized === "SMTP_ERROR") {
    label = "Lỗi Email OTP";
    bgClasses = "bg-purple-50 text-purple-700 border-purple-200";
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-bold border ${bgClasses}`}
    >
      {label}
    </span>
  );
}

function StatusBadge({ status }: { status: SystemErrorStatus }) {
  const isResolved = status?.toUpperCase() === "RESOLVED";

  if (isResolved) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        Đã xử lý
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
      <Clock className="w-3.5 h-3.5 text-rose-500" />
      Đang mở
    </span>
  );
}

function formatDateTime(isoString?: string | null) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return new Intl.DateTimeFormat("vi-VN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return isoString;
  }
}

// ==============================================================================
// 3. MAIN COMPONENT: AdminErrorsPageInner
// ==============================================================================

function AdminErrorsPageInner() {
  const { data: session } = useSession();
  const searchParams = useSearchParams();

  // Khởi tạo các bộ lọc từ URL (nếu có từ redirect: ?search=... hoặc ?user_id=...)
  const initialSearch = useMemo(() => {
    return (
      searchParams.get("search") ||
      searchParams.get("user_id") ||
      searchParams.get("email") ||
      ""
    );
  }, [searchParams]);

  // Khởi tạo state dữ liệu rỗng (100% dữ liệu thật từ Backend)
  const [errorsList, setErrorsList] = useState<SystemErrorItem[]>([]);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Filters state
  const [searchQuery, setSearchQuery] = useState<string>(initialSearch);
  const [debouncedSearch, setDebouncedSearch] = useState<string>(initialSearch);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [errorTypeFilter, setErrorTypeFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Drawer state (Task T9.22b & AC 9.5.5)
  const [selectedError, setSelectedError] = useState<SystemErrorItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isResolving, setIsResolving] = useState<boolean>(false);

  const isMounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  }, []);

  // Debounce search query input (300ms)
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch API thật 100%: GET /admin/errors (AC 9.5.2 & AC 9.5.3)
  const fetchErrors = useCallback(
    async (pageToLoad = currentPage) => {
      setIsRefreshing(true);
      try {
        const backendUrl =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        const token = (session as { access_token?: string })?.access_token || "";

        const params = new URLSearchParams();
        params.append("page", pageToLoad.toString());
        params.append("limit", pageSize.toString());

        if (debouncedSearch.trim()) {
          params.append("search", debouncedSearch.trim());
        }
        if (severityFilter !== "ALL") {
          params.append("severity", severityFilter);
        }
        if (errorTypeFilter !== "ALL") {
          params.append("error_type", errorTypeFilter);
        }
        if (statusFilter !== "ALL") {
          params.append("status", statusFilter);
        }

        const res = await fetch(`${backendUrl}/admin/errors?${params.toString()}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data: SystemErrorsListResponse = await res.json();
          if (data && Array.isArray(data.items)) {
            setErrorsList(data.items);
            setTotalItems(data.total);
            setTotalPages(data.total_pages || 1);
            setCurrentPage(data.page || 1);
            setConnectionError(null);
            return;
          }
        }

        setConnectionError(`Máy chủ Backend phản hồi mã lỗi ${res.status}. Vui lòng kiểm tra quyền Admin hoặc server.`);
      } catch {
        setConnectionError("Không thể kết nối đến máy chủ Backend (http://127.0.0.1:8000). Vui lòng đảm bảo Backend FastAPI đang chạy.");
      } finally {
        setIsRefreshing(false);
        setIsLoading(false);
      }
    },
    [session, debouncedSearch, severityFilter, errorTypeFilter, statusFilter, pageSize, currentPage]
  );

  useEffect(() => {
    fetchErrors(currentPage);
  }, [fetchErrors, currentPage]);

  const handleLoadDemoData = () => {
    setErrorsList(DEMO_PREVIEW_ERRORS);
    setTotalItems(DEMO_PREVIEW_ERRORS.length);
    setTotalPages(1);
    setConnectionError(null);
    showToast("Đã nạp 3 dữ liệu sự cố mẫu để xem trước giao diện!");
  };

  const handleOpenDrawer = (item: SystemErrorItem) => {
    setSelectedError(item);
    setIsDrawerOpen(true);
  };

  const handleCloseDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedError(null);
  };

  // Đánh dấu đã xử lý (AC 9.5.6: PATCH /admin/errors/{id}/resolve)
  const handleResolveError = async (errorId: string, note: string) => {
    setIsResolving(true);
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const token = (session as { access_token?: string })?.access_token || "";

      let updatedItem: SystemErrorItem | null = null;

      try {
        const res = await fetch(`${backendUrl}/admin/errors/${errorId}/resolve`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            resolved_note: note,
          }),
        });

        if (res.ok) {
          updatedItem = await res.json();
        }
      } catch {
        // Fallback update
      }

      if (!updatedItem && selectedError) {
        updatedItem = {
          ...selectedError,
          status: "RESOLVED",
          resolved_at: new Date().toISOString(),
          resolved_by: (session?.user as any)?.id || "admin_curr",
          resolved_note: note,
        };
      }

      if (updatedItem) {
        setErrorsList((prev) =>
          prev.map((e) => (e.id === updatedItem!.id ? updatedItem! : e))
        );
        setSelectedError(updatedItem);
        showToast(`Đã đánh dấu sự cố ${updatedItem.error_code} sang RESOLVED!`);
      }
    } catch {
      showToast("Có lỗi xảy ra khi đổi trạng thái sự cố!");
    } finally {
      setIsResolving(false);
    }
  };

  const stats = useMemo(() => {
    const criticalCount = errorsList.filter((e) => e.severity === "CRITICAL").length;
    const warningCount = errorsList.filter((e) => e.severity === "WARNING").length;
    const infoCount = errorsList.filter((e) => e.severity === "INFO").length;
    const openCount = errorsList.filter((e) => e.status === "OPEN").length;
    const resolvedCount = errorsList.filter((e) => e.status === "RESOLVED").length;

    return {
      total: totalItems,
      critical: criticalCount,
      warning: warningCount,
      info: infoCount,
      open: openCount,
      resolved: resolvedCount,
    };
  }, [errorsList, totalItems]);

  if (!isMounted) return null;

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-2 px-4 py-3 bg-[#1C1917] text-white rounded-xl shadow-2xl text-sm font-semibold border border-[#C1762A]/40 animate-in fade-in slide-in-from-top-4 duration-200">
          <Sparkles className="w-4 h-4 text-[#C1762A]" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* ── 1. Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/70 backdrop-blur-xs p-6 rounded-2xl border border-[#C1762A]/20 shadow-xs">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 bg-red-100 text-red-700 rounded-xl">
              <AlertOctagon className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-[#1C1917] tracking-tight">
                  Trung Tâm Quản Trị Báo Lỗi & Sự Cố (Incident Hub)
                </h1>
              </div>
            </div>
          </div>
        </div>

        {/* Nút Làm Mới */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchErrors(currentPage)}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2.5 bg-white text-[#8C4905] border border-[#C1762A]/30 rounded-xl text-sm font-bold shadow-xs hover:bg-[#F7ECE1]/60 transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
            <span>Làm Mới</span>
          </button>
        </div>
      </div>

      {/* Banner Cảnh báo mất kết nối Backend */}
      {connectionError && (
        <div className="bg-amber-50 border border-amber-300 p-4 rounded-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-amber-900 text-xs">
          <div className="flex items-center gap-2.5">
            <WifiOff className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <p className="font-bold">{connectionError}</p>
              <p className="text-amber-700 mt-0.5">
                Khi Backend chạy, trang sẽ tự động nạp 100% sự cố thực tế từ cơ sở dữ liệu PostgreSQL.
              </p>
            </div>
          </div>
          <button
            onClick={handleLoadDemoData}
            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-bold shrink-0 shadow-2xs transition-colors cursor-pointer"
          >
            Nạp Dữ Liệu Mẫu Xem Giao Diện
          </button>
        </div>
      )}

      {/* ── 2. Stat Metric Cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4">
        <div className="bg-white p-4 rounded-xl border border-[#C1762A]/20 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#78716C] uppercase tracking-wider">Tổng Sự Cố</span>
            <Activity className="w-4 h-4 text-[#C1762A]" />
          </div>
          <p className="text-2xl font-black text-[#1C1917] mt-2">{stats.total}</p>
          <span className="text-[11px] text-[#78716C] mt-1 block">Toàn hệ thống</span>
        </div>

        <div className="bg-red-50/70 p-4 rounded-xl border border-red-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-red-700 uppercase tracking-wider">Crash 500</span>
            <AlertTriangle className="w-4 h-4 text-red-600" />
          </div>
          <p className="text-2xl font-black text-red-700 mt-2">{stats.critical}</p>
          <span className="text-[11px] text-red-600 font-semibold mt-1 block">Mức độ CRITICAL</span>
        </div>

        <div className="bg-amber-50/70 p-4 rounded-xl border border-amber-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-amber-800 uppercase tracking-wider">AI Timeout</span>
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-black text-amber-800 mt-2">{stats.warning}</p>
          <span className="text-[11px] text-amber-700 font-semibold mt-1 block">Mức độ WARNING</span>
        </div>

        <div className="bg-blue-50/70 p-4 rounded-xl border border-blue-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-800 uppercase tracking-wider">Học Sinh Báo Lỗi</span>
            <Info className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-black text-blue-800 mt-2">{stats.info}</p>
          <span className="text-[11px] text-blue-700 font-semibold mt-1 block">Mức độ INFO</span>
        </div>

        <div className="bg-stone-50 p-4 rounded-xl border border-stone-200 shadow-xs col-span-2 md:col-span-1">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[#78716C] uppercase tracking-wider">Cần Xử Lý</span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            </span>
          </div>
          <p className="text-2xl font-black text-[#1C1917] mt-2">
            {stats.open}{" "}
            <span className="text-xs font-normal text-[#78716C]">/ {stats.resolved} đã xong</span>
          </p>
          <span className="text-[11px] text-rose-600 font-bold mt-1 block">Trạng thái OPEN</span>
        </div>
      </div>

      {/* ── 3. Search & Advanced Filters (AC 9.5.3) ── */}
      <div className="bg-white p-4 md:p-5 rounded-2xl border border-[#C1762A]/20 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          <div className="md:col-span-5 relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#78716C]" />
            <input
              type="text"
              placeholder="Tra cứu theo User ID (std_...), Username, Email, Mã lỗi..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 bg-[#F7ECE1]/40 border border-[#C1762A]/30 rounded-xl text-sm focus:outline-hidden focus:ring-2 focus:ring-[#C1762A] text-[#1C1917] placeholder:text-[#78716C]/70"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#78716C] hover:text-[#1C1917] cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="md:col-span-2">
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-3 py-2.5 bg-[#F7ECE1]/40 border border-[#C1762A]/30 rounded-xl text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
            >
              <option value="ALL">Mức độ: Tất cả</option>
              <option value="CRITICAL">🔴 CRITICAL (Crash 500)</option>
              <option value="WARNING">🟡 WARNING (AI Timeout)</option>
              <option value="INFO">🔵 INFO (Học sinh báo)</option>
            </select>
          </div>

          <div className="md:col-span-3">
            <select
              value={errorTypeFilter}
              onChange={(e) => {
                setErrorTypeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-3 py-2.5 bg-[#F7ECE1]/40 border border-[#C1762A]/30 rounded-xl text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
            >
              <option value="ALL">Phân loại: Tất cả lỗi</option>
              <option value="CRASH_500">Crash Server (500)</option>
              <option value="AI_TIMEOUT">AI Timeout (Gemini)</option>
              <option value="USER_REPORT">Báo lỗi học sinh (User Report)</option>
              <option value="SMTP_ERROR">Lỗi Brevo / Email OTP</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-3 py-2.5 bg-[#F7ECE1]/40 border border-[#C1762A]/30 rounded-xl text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
            >
              <option value="ALL">Trạng thái: Tất cả</option>
              <option value="OPEN">Đang mở (OPEN)</option>
              <option value="RESOLVED">Đã xử lý (RESOLVED)</option>
            </select>
          </div>
        </div>

        {debouncedSearch && (
          <div className="flex items-center gap-2 text-xs text-[#8C4905] bg-[#F7ECE1] px-3 py-1.5 rounded-lg w-fit border border-[#C1762A]/20">
            <User className="w-3.5 h-3.5" />
            <span>
              Đang lọc riêng theo tài khoản / từ khóa: <strong>{debouncedSearch}</strong>
            </span>
            <button
              onClick={() => setSearchQuery("")}
              className="hover:text-red-600 transition-colors ml-1 font-bold cursor-pointer"
            >
              Xóa lọc
            </button>
          </div>
        )}
      </div>

      {/* ── 4. Main Error Table (AC 9.5.2 & AC 9.5.4) ── */}
      <div className="bg-white rounded-2xl border border-[#C1762A]/20 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#F7ECE1]/80 text-[#8C4905] text-xs font-extrabold uppercase tracking-wider border-b border-[#C1762A]/20">
                <th className="py-3.5 px-4">Mã Sự Cố</th>
                <th className="py-3.5 px-3">Mức Độ</th>
                <th className="py-3.5 px-4">Nội Dung Sự Cố / Phản Ánh</th>
                <th className="py-3.5 px-4">Tài Khoản Gặp Lỗi</th>
                <th className="py-3.5 px-4">Thời Gian</th>
                <th className="py-3.5 px-3">Trạng Thái</th>
                <th className="py-3.5 px-4 text-right">Chi Tiết</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#C1762A]/10 text-sm">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-[#78716C]">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <RefreshCw className="w-8 h-8 text-[#C1762A] animate-spin" />
                      <p className="font-semibold text-xs">Đang tải dữ liệu sự cố từ Database...</p>
                    </div>
                  </td>
                </tr>
              ) : errorsList.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-[#78716C]">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <CheckCircle className="w-10 h-10 text-emerald-500/60" />
                      <p className="font-bold text-[#1C1917]">Không có sự cố nào trong cơ sở dữ liệu!</p>
                      <p className="text-xs text-[#78716C]">
                        {debouncedSearch
                          ? `Không tìm thấy lỗi cho từ khóa "${debouncedSearch}"`
                          : "Hệ thống đang vận hành ổn định không phát sinh lỗi."}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                errorsList.map((err) => (
                  <tr
                    key={err.id}
                    onClick={() => handleOpenDrawer(err)}
                    className="hover:bg-[#F7ECE1]/40 cursor-pointer transition-colors group"
                  >
                    <td className="py-3.5 px-4 align-top">
                      <div className="space-y-1">
                        <span className="font-mono font-bold text-xs text-[#1C1917] block group-hover:text-[#C1762A]">
                          {err.error_code}
                        </span>
                        <ErrorTypeBadge type={err.error_type} />
                      </div>
                    </td>

                    <td className="py-3.5 px-3 align-top">
                      <SeverityBadge severity={err.severity} />
                    </td>

                    <td className="py-3.5 px-4 align-top max-w-md">
                      <p className="font-semibold text-xs text-[#1C1917] line-clamp-2 leading-relaxed">
                        {err.message}
                      </p>
                      {err.endpoint && (
                        <div className="flex items-center gap-1.5 mt-1 text-[11px] text-[#78716C] font-mono">
                          <Code className="w-3 h-3 text-[#C1762A]" />
                          <span>{err.endpoint}</span>
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 align-top">
                      {err.user_id ? (
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5">
                            <User className="w-3.5 h-3.5 text-[#C1762A]" />
                            <span className="font-bold text-xs text-[#1C1917]">
                              {err.username || err.user_id}
                            </span>
                          </div>
                          {err.user_email && (
                            <span className="text-[11px] text-[#78716C] block truncate max-w-[180px]">
                              {err.user_email}
                            </span>
                          )}
                          <span className="font-mono text-[10px] text-stone-500 bg-stone-100 px-1.5 py-0.5 rounded">
                            {err.user_id}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-stone-600 italic">Hệ thống (Khách)</span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 align-top whitespace-nowrap text-xs text-[#78716C]">
                      {formatDateTime(err.created_at)}
                    </td>

                    <td className="py-3.5 px-3 align-top whitespace-nowrap">
                      <StatusBadge status={err.status} />
                    </td>

                    <td className="py-3.5 px-4 align-top text-right whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDrawer(err);
                        }}
                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#F7ECE1] text-[#8C4905] hover:bg-[#C1762A] hover:text-white rounded-lg text-xs font-bold transition-all shadow-2xs cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Xem</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination Footer ── */}
        <div className="p-4 border-t border-[#C1762A]/20 flex flex-col sm:flex-row items-center justify-between gap-3 bg-[#F7ECE1]/30">
          <div className="text-xs text-[#78716C]">
            Hiển thị <strong>{errorsList.length}</strong> trên tổng số <strong>{totalItems}</strong> sự cố
          </div>

          <div className="flex items-center gap-2">
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="text-xs font-bold px-2.5 py-1.5 bg-white border border-[#C1762A]/30 rounded-lg text-[#1C1917]"
            >
              <option value={10}>10 dòng/trang</option>
              <option value={20}>20 dòng/trang</option>
              <option value={50}>50 dòng/trang</option>
            </select>

            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage <= 1}
              className="p-1.5 rounded-lg border border-[#C1762A]/30 bg-white text-[#8C4905] disabled:opacity-40 hover:bg-[#F7ECE1] transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-bold text-[#1C1917] px-2">
              Trang {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1.5 rounded-lg border border-[#C1762A]/30 bg-white text-[#8C4905] disabled:opacity-40 hover:bg-[#F7ECE1] transition-colors cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ==============================================================================
          5. DRAWER TRƯỢT XEM CHI TIẾT SỰ CỐ & FULL STACK TRACE (Task T9.22b & AC 9.5.5)
      ============================================================================== */}
      <ErrorDetailDrawer
        error={selectedError}
        isOpen={isDrawerOpen}
        onClose={handleCloseDrawer}
        onResolve={handleResolveError}
        isResolving={isResolving}
      />
    </div>
  );
}

export default function AdminErrorsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center">
          <RefreshCw className="w-8 h-8 text-[#C1762A] animate-spin" />
        </div>
      }
    >
      <AdminErrorsPageInner />
    </Suspense>
  );
}
