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
  BellOff,
  Sparkles,
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

      const res = await fetch(`${backendUrl}/admin/errors?status=OPEN&limit=30`, {
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
    <>
      {/* Backdrop mờ nhẹ trên Mobile (< 640px) chống bấm nhầm */}
      <div
        className="fixed inset-0 bg-black/20 backdrop-blur-[2px] z-40 sm:hidden animate-in fade-in duration-200"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={dropdownRef}
        role="dialog"
        aria-label="Thông báo sự cố"
        className="fixed inset-x-3 top-16 w-auto max-w-[calc(100vw-24px)] sm:absolute sm:inset-x-auto sm:right-0 sm:top-12 sm:mt-2 sm:w-[380px] sm:max-w-none bg-white rounded-2xl sm:rounded-3xl shadow-2xl border border-[#F1CCA6] z-50 overflow-hidden flex flex-col max-h-[calc(100dvh-5rem)] sm:max-h-[520px] animate-in fade-in zoom-in-95 duration-200"
      >
        {/* ── 1. HEADER DROPDOWN ── */}
        <div className="p-4 border-b border-[#F1CCA6]/60 bg-gradient-to-b from-[#F7ECE1]/60 to-white shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-orange-100/80 border border-[#F1CCA6] flex items-center justify-center text-[#C1762A] shadow-xs shrink-0">
                <Bell className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="font-extrabold text-[#1C1917] text-sm sm:text-base leading-tight truncate">
                  Thông báo sự cố
                </h3>
                <p className="text-[11px] text-[#7A3E04] font-medium truncate">
                  Cập nhật tức thời qua Incident Hub
                </p>
              </div>

              {/* Badge số đếm chưa đọc kèm Pulse Animation */}
              {unreadCount > 0 && (
                <span
                  className="px-2 py-0.5 text-xs font-black rounded-full bg-red-500 text-white leading-none shadow-xs animate-pulse ring-2 ring-red-100 shrink-0"
                  title={`${unreadCount} thông báo chưa đọc`}
                >
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  className="inline-flex items-center justify-center gap-1 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 text-xs font-bold text-[#8C4905] hover:text-[#C1762A] hover:bg-[#F7ECE1]/60 px-2.5 py-1.5 rounded-xl border border-transparent hover:border-[#F1CCA6]/60 transition-all cursor-pointer active:scale-95"
                  title="Đánh dấu tất cả thông báo là đã đọc"
                  aria-label="Đánh dấu tất cả đã đọc"
                >
                  <CheckCheck className="w-3.5 h-3.5 text-[#10B981] shrink-0" />
                  <span className="hidden sm:inline">Đọc tất cả</span>
                </button>
              )}

              <button
                type="button"
                onClick={onClose}
                className="min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 p-2 text-[#7A3E04] hover:text-[#1C1917] hover:bg-[#F7ECE1] rounded-xl transition-colors cursor-pointer flex items-center justify-center"
                aria-label="Đóng bảng thông báo"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* ── Tab Switcher Segmented Control (T11.3.4) ── */}
          <div className="flex items-center gap-1.5 p-1 bg-[#F7ECE1]/60 rounded-2xl border border-[#F1CCA6]/60">
            <button
              type="button"
              onClick={() => setActiveTab("all")}
              className={`flex-1 min-h-[44px] sm:min-h-0 sm:py-1.5 px-3 text-xs font-bold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1.5 active:scale-[0.98] ${
                activeTab === "all"
                  ? "bg-[#F7ECE1] text-[#8C4905] shadow-xs border border-[#F1CCA6]"
                  : "text-[#7A3E04]/70 hover:text-[#1C1917] hover:bg-[#F7ECE1]/40 border border-transparent"
              }`}
            >
              <span>Tất cả</span>
              <span
                className={`text-[11px] px-1.5 py-0.5 rounded-full font-bold leading-none ${
                  activeTab === "all"
                    ? "bg-[#C1762A]/15 text-[#8C4905]"
                    : "bg-black/5 text-[#7A3E04]/80"
                }`}
              >
                {items.length}
              </span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("unread")}
              className={`flex-1 min-h-[44px] sm:min-h-0 sm:py-1.5 px-3 text-xs font-bold rounded-xl transition-all cursor-pointer flex items-center justify-center gap-1.5 active:scale-[0.98] ${
                activeTab === "unread"
                  ? "bg-[#F7ECE1] text-[#8C4905] shadow-xs border border-[#F1CCA6]"
                  : "text-[#7A3E04]/70 hover:text-[#1C1917] hover:bg-[#F7ECE1]/40 border border-transparent"
              }`}
            >
              <span>Chưa đọc</span>
              <span
                className={`text-[11px] px-1.5 py-0.5 rounded-full font-bold leading-none ${
                  unreadCount > 0
                    ? "bg-red-500 text-white"
                    : activeTab === "unread"
                      ? "bg-[#C1762A]/15 text-[#8C4905]"
                      : "bg-black/5 text-[#7A3E04]/80"
                }`}
              >
                {unreadCount}
              </span>
            </button>
          </div>
        </div>

        {/* ── 2. SCROLLABLE BODY VỚI NOTIFICATION ITEMS (Task T11.3.2 & T11.3.4) ── */}
        <div className="flex-1 overflow-y-auto divide-y divide-[#F1CCA6]/30">
          {filteredItems.length === 0 ? (
            // Empty State thân thiện & ấm áp (Task T11.3.4)
            <div className="py-12 px-6 text-center flex flex-col items-center justify-center animate-in fade-in zoom-in-95 duration-200">
              <div className="relative mb-3.5">
                <div
                  className={`w-16 h-16 rounded-full flex items-center justify-center shadow-xs border ${
                    activeTab === "all"
                      ? "bg-[#ECFDF5] border-[#10B981]/25 text-[#10B981]"
                      : "bg-[#F7ECE1] border-[#F1CCA6] text-[#C1762A]"
                  }`}
                >
                  {activeTab === "all" ? (
                    <ShieldCheck className="w-8 h-8 stroke-[1.8]" />
                  ) : (
                    <BellOff className="w-8 h-8 stroke-[1.8]" />
                  )}
                </div>
                <Sparkles
                  className={`w-4 h-4 absolute -top-1 -right-1 animate-pulse ${
                    activeTab === "all" ? "text-[#10B981]" : "text-[#C1762A]"
                  }`}
                />
              </div>

              <h4 className="text-sm sm:text-base font-extrabold text-[#1C1917] mb-1.5">
                {activeTab === "all"
                  ? "Hệ thống đang an toàn!"
                  : "Bạn đã xem hết thông báo!"}
              </h4>
              <p className="text-xs sm:text-sm text-[#7A3E04] max-w-[270px] mx-auto leading-relaxed">
                {activeTab === "all"
                  ? "Chưa có sự cố hay phản ánh nào từ học sinh cần xử lý."
                  : "Tuyệt vời, không còn sự cố nào bị bỏ sót."}
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
        <div className="p-3 bg-[#F7ECE1]/50 border-t border-[#F1CCA6]/60 text-center shrink-0">
          <Link
            href="/admin/errors"
            onClick={onClose}
            className="inline-flex items-center justify-center gap-2 w-full min-h-[44px] sm:min-h-0 py-2.5 sm:py-2 px-3 text-xs font-bold text-[#8C4905] hover:text-[#C1762A] hover:bg-white rounded-xl transition-all border border-transparent hover:border-[#F1CCA6]/60 shadow-2xs group cursor-pointer"
          >
            <span>Xem chi tiết tại Quản trị Báo Lỗi</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </div>
    </>
  );
}
