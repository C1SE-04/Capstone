"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { Menu, Search, Bell, Plus } from "lucide-react";
import Breadcrumbs from "./Breadcrumbs";
import NotificationDropdown, {
  NotificationItem,
  NotificationSeverity,
} from "./NotificationDropdown";
import { useAdminNotifications } from "@/hooks/useAdminNotifications";
import { SystemErrorItem } from "@/types/admin";

interface AdminHeaderProps {
  onOpenMobileSidebar?: () => void;
}

// Dữ liệu mẫu ban đầu dự phòng khi Backend chưa khởi động
const DEMO_NOTIFICATIONS_BASE = [
  {
    id: "noti-1",
    errorId: "ERR-500-981",
    title: "Lỗi hệ thống 500: Database Connection Timeout",
    message:
      "Quá tải kết nối cơ sở dữ liệu PostgreSQL tại cụm máy chủ khu vực Đông Nam Á.",
    severity: "CRASH_500" as NotificationSeverity,
    createdAt: "3 phút trước",
  },
  {
    id: "noti-2",
    errorId: "ERR-408-204",
    title: "AI Response Timeout (Gemini)",
    message:
      "Học sinh khối 7 không nhận được phản hồi gợi mở sau 30 giây tại phiên trò chuyện #4829.",
    severity: "AI_TIMEOUT" as NotificationSeverity,
    createdAt: "18 phút trước",
  },
  {
    id: "noti-3",
    errorId: "UR_B7C1F309",
    title: "[Báo lỗi học sinh] Đơ lag / Lỗi mạng - AI phản hồi lag",
    message:
      "Học sinh phản ánh phản hồi bài giải toán bị chậm trên thiết bị iPad.",
    severity: "USER_REPORT" as NotificationSeverity,
    createdAt: "45 phút trước",
  },
  {
    id: "noti-4",
    errorId: "ERR-500-975",
    title: "Lỗi sập vi dịch vụ: Speech-to-Text API",
    message:
      "Dịch vụ nhận diện giọng nói học sinh tạm thời không phản hồi, đã tự động chuyển sang văn bản.",
    severity: "CRASH_500" as NotificationSeverity,
    createdAt: "2 giờ trước",
  },
  {
    id: "noti-5",
    errorId: "ERR-USR-108",
    title: "Phản ánh từ Phụ huynh: Đổi mật khẩu",
    message:
      "Phụ huynh bé Hoàng Quân yêu cầu hỗ trợ liên kết tài khoản giám sát tiến độ học tập.",
    severity: "USER_REPORT" as NotificationSeverity,
    createdAt: "5 giờ trước",
  },
];

function formatRelativeTime(isoString?: string | null): string {
  if (!isoString) return "Vừa xong";
  try {
    const diffMs = Date.now() - new Date(isoString).getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return "Vừa xong";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} phút trước`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour} giờ trước`;
    const diffDay = Math.floor(diffHour / 24);
    return `${diffDay} ngày trước`;
  } catch {
    return "Vừa xong";
  }
}

export default function AdminHeader({ onOpenMobileSidebar }: AdminHeaderProps) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const [searchValue, setSearchValue] = useState("");
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [systemErrors, setSystemErrors] = useState<SystemErrorItem[]>([]);

  // Task #387: Hook quản lý trạng thái thông báo và đồng bộ LocalStorage
  const { checkIsRead, markAsRead, markAllAsRead, isMounted } =
    useAdminNotifications(systemErrors);

  const isContentTab = pathname?.startsWith("/admin/content");

  // Fetch danh sách lỗi OPEN từ Backend định kỳ (30s polling)
  const fetchActiveErrors = useCallback(async () => {
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const token = (session as { access_token?: string })?.access_token || "";
      const res = await fetch(`${backendUrl}/admin/errors?status=OPEN&limit=10`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.items) && data.items.length > 0) {
          setSystemErrors(data.items);
          return;
        }
      }
    } catch {
      // Fallback an toàn nếu backend chưa kết nối
    }
  }, [session]);

  useEffect(() => {
    fetchActiveErrors();
    const interval = setInterval(fetchActiveErrors, 30000);
    return () => clearInterval(interval);
  }, [fetchActiveErrors]);

  // Ánh xạ danh sách lỗi sang NotificationItem chuẩn để hiển thị Dropdown
  const notificationItems: NotificationItem[] = useMemo(() => {
    if (systemErrors.length > 0) {
      return systemErrors.map((err) => {
        const sev: NotificationSeverity =
          err.error_type === "CRASH_500"
            ? "CRASH_500"
            : err.error_type === "AI_TIMEOUT"
            ? "AI_TIMEOUT"
            : "USER_REPORT";

        const errKey = err.id;
        const isRead = checkIsRead(errKey) || checkIsRead(err.error_code);

        return {
          id: err.id,
          errorId: err.error_code || err.id,
          title: `[${sev}] ${err.error_code}`,
          message: err.message,
          severity: sev,
          createdAt: formatRelativeTime(err.created_at),
          isRead,
        };
      });
    }

    // Nếu chưa có dữ liệu từ backend, dùng DEMO_NOTIFICATIONS_BASE
    return DEMO_NOTIFICATIONS_BASE.map((demo) => ({
      ...demo,
      isRead: checkIsRead(demo.errorId || demo.id),
    }));
  }, [systemErrors, checkIsRead]);

  // Tính số lượng lỗi chưa đọc (chỉ tính sau khi đã mounted trên client)
  const unreadCount = useMemo(() => {
    if (!isMounted) return 0;
    return notificationItems.filter((item) => !item.isRead).length;
  }, [notificationItems, isMounted]);

  // Kiểm tra nếu có lỗi CRITICAL chưa đọc thì thêm hiệu ứng pulse gây chú ý
  const hasCriticalUnread = useMemo(() => {
    return notificationItems.some(
      (item) => !item.isRead && item.severity === "CRASH_500"
    );
  }, [notificationItems]);

  const handleNotificationClick = () => {
    setIsNotificationOpen((prev) => !prev);
  };

  return (
    <header className="h-16 bg-white border-b border-[#F1CCA6] px-4 md:px-8 flex items-center justify-between shrink-0 relative z-10 shadow-xs">
      {/* ── Bên trái: Mobile Hamburger & Breadcrumbs ── */}
      <div className="flex items-center gap-3">
        {onOpenMobileSidebar && (
          <button
            type="button"
            onClick={onOpenMobileSidebar}
            className="lg:hidden p-2 -ml-1 rounded-xl text-[#8C4905] hover:bg-[#F7ECE1] transition-colors"
            aria-label="Mở thanh điều hướng"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <Breadcrumbs />
      </div>

      {/* ── Bên phải: Công cụ quản trị, Tìm kiếm, Thông báo ── */}
      <div className="flex items-center gap-2 md:gap-3.5">
        {/* Search Input */}
        <div className="relative hidden md:block">
          <Search className="w-4 h-4 text-[#C1762A] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Tìm học sinh, chủ đề..."
            className="w-48 lg:w-60 pl-9 pr-3 py-1.5 text-xs lg:text-sm bg-[#F7ECE1]/60 hover:bg-white focus:bg-white border border-[#F1CCA6] focus:border-[#C1762A] rounded-xl text-[#1C1917] placeholder:text-[#C1762A]/60 focus:outline-hidden transition-all"
          />
        </div>

        {/* Task #389: Notification Bell & Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={handleNotificationClick}
            title="Xem cảnh báo an toàn & thông báo sự cố"
            aria-label="Thông báo sự cố"
            aria-expanded={isNotificationOpen}
            className="relative p-2 rounded-xl border border-[#F1CCA6] text-[#8C4905] hover:bg-[#F7ECE1] transition-all cursor-pointer focus:outline-hidden"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span
                className={`absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-[#EF4444] text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white ${
                  hasCriticalUnread ? "animate-pulse" : ""
                }`}
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Dropdown Menu thông báo */}
          <NotificationDropdown
            isOpen={isNotificationOpen}
            onClose={() => setIsNotificationOpen(false)}
            notifications={notificationItems}
            onMarkAllAsRead={() => {
              const allIds = notificationItems.map((n) => n.errorId || n.id);
              markAllAsRead(allIds);
            }}
            onNotificationClick={(item) => {
              markAsRead(item.errorId || item.id);
              setIsNotificationOpen(false);
            }}
          />
        </div>

        {/* Nút Hành động nhanh: + Thêm Học Liệu (Chỉ hiện trong tab Học liệu) */}
        {isContentTab && (
          <Link
            href="/admin/content"
            className="inline-flex items-center gap-1.5 px-3 md:px-3.5 py-1.5 md:py-2 rounded-xl bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 active:scale-95 text-white text-xs md:text-sm font-bold shadow-sm transition-all shrink-0 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">Thêm Học Liệu</span>
            <span className="sm:hidden">Thêm</span>
          </Link>
        )}
      </div>
    </header>
  );
}
