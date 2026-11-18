"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import {
  CheckCheck,
  ArrowRight,
  ShieldCheck,
  X,
  Bell,
} from "lucide-react";

import NotificationItem, {
  NotificationItemData,
  NotificationSeverity,
} from "./NotificationItem";
import { useOnClickOutside } from "@/hooks/useOnClickOutside";
import {
  getStoredReadErrorIds,
  markErrorAsRead,
  markAllErrorsAsRead,
  ADMIN_NOTIFICATIONS_UPDATED_EVENT,
} from "@/lib/adminNotificationStorage";
import { SystemErrorItem, SystemErrorsListResponse } from "@/types/admin";

export type { NotificationSeverity, NotificationItemData };
export type NotificationItem = NotificationItemData;

interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  notifications?: NotificationItemData[];
  onMarkAllAsRead?: () => void;
  onNotificationClick?: (notification: NotificationItemData) => void;
  onUnreadCountChange?: (count: number) => void;
}

// ── Mock data ban đầu hỗ trợ hiển thị đẹp mắt ngay cả khi Backend offline ──
const DEFAULT_FALLBACK_NOTIFICATIONS: NotificationItemData[] = [
  {
    id: "noti-1",
    errorId: "ERR-500-981",
    title: "Lỗi hệ thống 500: Database Connection Timeout",
    message: "Quá tải kết nối cơ sở dữ liệu PostgreSQL tại cụm máy chủ khu vực Đông Nam Á.",
    severity: "CRASH_500",
    createdAt: new Date(Date.now() - 3 * 60 * 1000).toISOString(),
    isRead: false,
  },
  {
    id: "noti-2",
    errorId: "ERR-408-204",
    title: "AI Response Timeout (Gemini 1.5 Pro)",
    message: "Học sinh khối 7 không nhận được phản hồi gợi mở sau 30 giây tại phiên trò chuyện #4829.",
    severity: "AI_TIMEOUT",
    createdAt: new Date(Date.now() - 18 * 60 * 1000).toISOString(),
    isRead: false,
  },
  {
    id: "noti-3",
    errorId: "ERR-USR-112",
    title: "Phản ánh từ học sinh: Gợi ý chưa khớp bài học",
    message: "Học sinh Minh Anh (Lớp 5B) báo cáo AI giải thích sai bài toán tính diện tích hình thang.",
    severity: "USER_REPORT",
    createdAt: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    isRead: false,
  },
  {
    id: "noti-4",
    errorId: "ERR-500-975",
    title: "Lỗi sập vi dịch vụ: Speech-to-Text API",
    message: "Dịch vụ nhận diện giọng nói học sinh tạm thời không phản hồi, đã tự động chuyển sang văn bản.",
    severity: "CRASH_500",
    createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isRead: true,
  },
  {
    id: "noti-5",
    errorId: "ERR-USR-108",
    title: "Phản ánh từ Phụ huynh: Hỗ trợ giám sát học tập",
    message: "Phụ huynh bé Hoàng Quân yêu cầu hỗ trợ liên kết tài khoản giám sát tiến độ học tập.",
    severity: "USER_REPORT",
    createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    isRead: true,
  },
];

/**
 * Chuyển đổi dữ liệu lỗi từ Backend sang dạng NotificationItemData
 */
function mapSystemErrorToNotification(
  error: SystemErrorItem,
  readIdsSet: Set<string>
): NotificationItemData {
  let mappedSeverity: NotificationSeverity = "USER_REPORT";
  const errType = (error.error_type || "").toUpperCase();

  if (errType === "CRASH_500" || error.severity === "CRITICAL") {
    mappedSeverity = "CRASH_500";
  } else if (errType === "AI_TIMEOUT" || error.severity === "WARNING") {
    mappedSeverity = "AI_TIMEOUT";
  } else {
    mappedSeverity = "USER_REPORT";
  }

  const isRead = readIdsSet.has(error.id) || error.status?.toUpperCase() === "RESOLVED";

  return {
    id: error.id,
    errorId: error.error_code || error.id,
    title: `${error.error_code ? `[${error.error_code}] ` : ""}${error.message?.slice(0, 50) || "Thông báo sự cố"}`,
    message: error.message || "Không có chi tiết mô tả sự cố.",
    severity: mappedSeverity,
    createdAt: error.created_at,
    isRead,
  };
}

export default function NotificationDropdown({
  isOpen,
  onClose,
  notifications: initialNotifications,
  onMarkAllAsRead,
  onNotificationClick,
  onUnreadCountChange,
}: NotificationDropdownProps) {
  const { data: session } = useSession();
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [items, setItems] = useState<NotificationItemData[]>(() => {
    if (initialNotifications && initialNotifications.length > 0) {
      return initialNotifications;
    }
    return DEFAULT_FALLBACK_NOTIFICATIONS;
  });

  const [activeTab, setActiveTab] = useState<"all" | "unread">("all");

  // ── 1. Đóng mượt mà khi Click-Outside hoặc bấm phím Escape (Task T11.3.3) ──
  useOnClickOutside(dropdownRef, onClose, {
    enabled: isOpen,
    listenEscape: true,
  });

  // ── 2. Polling Ngầm (Background Fetching) mỗi 30 giây (Zero UI Flash) ──
  const fetchOpenErrors = useCallback(async () => {
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const token = (session as { access_token?: string })?.access_token || "";

      const res = await fetch(`${backendUrl}/admin/errors?status=OPEN&limit=10`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        const data: SystemErrorsListResponse = await res.json();
        if (data && Array.isArray(data.items) && data.items.length > 0) {
          const storedReadIds = new Set(getStoredReadErrorIds());
          const mapped = data.items.map((item) =>
            mapSystemErrorToNotification(item, storedReadIds)
          );
          // Cập nhật ngầm êm dịu mà không làm nháy màn hình (Zero UI Flash)
          setItems(mapped);
          return;
        }
      }
    } catch {
      // Backend có thể offline hoặc chưa có token, giữ nguyên dữ liệu hiện tại (Zero UI Flash)
    }
  }, [session]);

  // Khởi động chu kỳ Polling ngầm mỗi 30s
  useEffect(() => {
    fetchOpenErrors();

    const intervalId = setInterval(() => {
      fetchOpenErrors();
    }, 30000); // 30 giây theo yêu cầu T11.3.3

    // Refresh nhẹ khi người dùng quay lại tab trình duyệt
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchOpenErrors();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [fetchOpenErrors]);

  // Đồng bộ trạng thái đã đọc từ LocalStorage khi có Custom Event
  useEffect(() => {
    const handleStorageUpdate = () => {
      const readSet = new Set(getStoredReadErrorIds());
      setItems((prev) =>
        prev.map((item) => ({
          ...item,
          isRead: readSet.has(item.id) || item.isRead,
        }))
      );
    };

    window.addEventListener(ADMIN_NOTIFICATIONS_UPDATED_EVENT, handleStorageUpdate);
    return () => {
      window.removeEventListener(ADMIN_NOTIFICATIONS_UPDATED_EVENT, handleStorageUpdate);
    };
  }, []);

  // Tính số lượng chưa đọc & thông báo ra ngoài cho Icon chuông Header
  const unreadCount = useMemo(() => {
    return items.filter((item) => !item.isRead).length;
  }, [items]);

  useEffect(() => {
    if (onUnreadCountChange) {
      onUnreadCountChange(unreadCount);
    }
  }, [unreadCount, onUnreadCountChange]);

  // Cập nhật khi prop initialNotifications thay đổi từ bên ngoài
  useEffect(() => {
    if (initialNotifications && initialNotifications.length > 0) {
      setItems(initialNotifications);
    }
  }, [initialNotifications]);

  if (!isOpen) return null;

  // Lọc theo tab hiển thị
  const filteredItems =
    activeTab === "unread" ? items.filter((item) => !item.isRead) : items;

  // ── Đánh dấu tất cả đã đọc ──
  const handleMarkAllRead = () => {
    const allIds = items.map((i) => i.id);
    markAllErrorsAsRead(allIds);

    setItems((prev) => prev.map((item) => ({ ...item, isRead: true })));

    if (onMarkAllAsRead) {
      onMarkAllAsRead();
    }
  };

  // ── Đánh dấu 1 item cụ thể đã đọc khi click ──
  const handleItemClick = (notification: NotificationItemData) => {
    markErrorAsRead(notification.id);

    setItems((prev) =>
      prev.map((item) =>
        item.id === notification.id ? { ...item, isRead: true } : item
      )
    );

    if (onNotificationClick) {
      onNotificationClick(notification);
    }
    onClose();
  };

  return (
    <div
      ref={dropdownRef}
      role="dialog"
      aria-label="Thông báo sự cố"
      className="absolute right-0 top-12 w-[360px] sm:w-[410px] bg-white rounded-3xl shadow-2xl border border-[#F1CCA6] z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
    >
      {/* ── 1. HEADER DROPDOWN ── */}
      <div className="p-4 border-b border-[#F1CCA6]/60 bg-gradient-to-b from-[#F7ECE1]/60 to-white">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-orange-100/80 border border-[#F1CCA6] flex items-center justify-center text-[#C1762A] shadow-xs">
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-extrabold text-[#1C1917] text-sm sm:text-base leading-tight">
                Thông báo sự cố
              </h3>
              <p className="text-[11px] text-[#7A3E04] font-medium">
                Cập nhật tức thời qua Incident Hub
              </p>
            </div>

            {/* Badge số đếm chưa đọc kèm Pulse Animation */}
            {unreadCount > 0 && (
              <span
                className="px-2 py-0.5 text-xs font-black rounded-full bg-red-500 text-white leading-none shadow-xs animate-pulse ring-2 ring-red-100"
                title={`${unreadCount} thông báo chưa đọc`}
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="inline-flex items-center gap-1 text-xs font-bold text-[#8C4905] hover:text-[#C1762A] hover:bg-white/80 px-2 py-1 rounded-lg border border-transparent hover:border-[#F1CCA6]/60 transition-all cursor-pointer active:scale-95"
                title="Đánh dấu tất cả thông báo là đã đọc"
              >
                <CheckCheck className="w-3.5 h-3.5 text-[#10B981]" />
                <span className="hidden sm:inline">Đọc tất cả</span>
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 text-[#7A3E04] hover:text-[#1C1917] hover:bg-[#F7ECE1] rounded-xl transition-colors cursor-pointer"
              aria-label="Đóng bảng thông báo"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tab Switcher: Tất cả / Chưa đọc */}
        <div className="flex items-center gap-1 p-1 bg-[#F7ECE1]/70 rounded-2xl border border-[#F1CCA6]/50">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`flex-1 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              activeTab === "all"
                ? "bg-white text-[#8C4905] shadow-sm border border-[#F1CCA6]/60"
                : "text-[#7A3E04] hover:text-[#1C1917]"
            }`}
          >
            Tất cả ({items.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("unread")}
            className={`flex-1 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              activeTab === "unread"
                ? "bg-white text-[#8C4905] shadow-sm border border-[#F1CCA6]/60"
                : "text-[#7A3E04] hover:text-[#1C1917]"
            }`}
          >
            Chưa đọc ({unreadCount})
          </button>
        </div>
      </div>

      {/* ── 2. SCROLLABLE BODY VỚI NOTIFICATION ITEMS (Task T11.3.2) ── */}
      <div className="max-h-[380px] overflow-y-auto divide-y divide-[#F1CCA6]/30">
        {filteredItems.length === 0 ? (
          // Empty State thân thiện
          <div className="py-12 px-6 text-center flex flex-col items-center justify-center">
            <div className="w-14 h-14 rounded-2xl bg-[#ECFDF5] border border-[#10B981]/30 flex items-center justify-center text-[#10B981] mb-3 shadow-xs">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <h4 className="text-sm font-bold text-[#1C1917] mb-1">
              Hệ thống hoạt động ổn định!
            </h4>
            <p className="text-xs text-[#7A3E04] max-w-[260px] leading-relaxed">
              {activeTab === "unread"
                ? "Tuyệt vời! Bạn đã đọc hết tất cả thông báo sự cố trong danh sách."
                : "Hiện không có sự cố nào được ghi nhận gần đây."}
            </p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <NotificationItem
              key={item.id}
              notification={item}
              onClick={handleItemClick}
            />
          ))
        )}
      </div>

      {/* ── 3. FOOTER ĐIỀU HƯỚNG QUẢN TRỊ ── */}
      <div className="p-3 bg-[#F7ECE1]/50 border-t border-[#F1CCA6]/60 text-center">
        <Link
          href="/admin/errors"
          onClick={onClose}
          className="inline-flex items-center justify-center gap-2 w-full py-2 px-3 text-xs font-bold text-[#8C4905] hover:text-[#C1762A] hover:bg-white rounded-xl transition-all border border-transparent hover:border-[#F1CCA6]/60 shadow-2xs group cursor-pointer"
        >
          <span>Xem chi tiết tại Trung tâm Sự cố (Incident Hub)</span>
          <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
        </Link>
      </div>
    </div>
  );
}
