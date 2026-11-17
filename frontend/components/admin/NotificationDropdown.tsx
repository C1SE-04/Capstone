"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  MessageSquareWarning,
  CheckCheck,
  Bell,
  ArrowRight,
  ShieldCheck,
  X,
} from "lucide-react";

export type NotificationSeverity = "CRASH_500" | "AI_TIMEOUT" | "USER_REPORT";

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  severity: NotificationSeverity;
  createdAt: string;
  isRead: boolean;
  errorId?: string;
}

interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  notifications?: NotificationItem[];
  onMarkAllAsRead?: () => void;
  onNotificationClick?: (notification: NotificationItem) => void;
}

// Mock data ban đầu phong phú hỗ trợ hiển thị visual ngay khi chưa kết nối API
const DEFAULT_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "noti-1",
    errorId: "ERR-500-981",
    title: "Lỗi hệ thống 500: Database Connection Timeout",
    message: "Quá tải kết nối cơ sở dữ liệu PostgreSQL tại cụm máy chủ khu vực Đông Nam Á.",
    severity: "CRASH_500",
    createdAt: "3 phút trước",
    isRead: false,
  },
  {
    id: "noti-2",
    errorId: "ERR-408-204",
    title: "AI Response Timeout (Gemini 1.5 Pro)",
    message: "Học sinh khối 7 không nhận được phản hồi gợi mở sau 30 giây tại phiên trò chuyện #4829.",
    severity: "AI_TIMEOUT",
    createdAt: "18 phút trước",
    isRead: false,
  },
  {
    id: "noti-3",
    errorId: "ERR-USR-112",
    title: "Phản ánh từ học sinh: Gợi ý chưa khớp bài học",
    message: "Học sinh Minh Anh (Lớp 5B) báo cáo AI giải thích sai bài toán tính diện tích hình thang.",
    severity: "USER_REPORT",
    createdAt: "45 phút trước",
    isRead: false,
  },
  {
    id: "noti-4",
    errorId: "ERR-500-975",
    title: "Lỗi sập vi dịch vụ: Speech-to-Text API",
    message: "Dịch vụ nhận diện giọng nói học sinh tạm thời không phản hồi, đã tự động chuyển sang văn bản.",
    severity: "CRASH_500",
    createdAt: "2 giờ trước",
    isRead: true,
  },
  {
    id: "noti-5",
    errorId: "ERR-USR-108",
    title: "Phản ánh từ Phụ huynh: Đổi mật khẩu",
    message: "Phụ huynh bé Hoàng Quân yêu cầu hỗ trợ liên kết tài khoản giám sát tiến độ học tập.",
    severity: "USER_REPORT",
    createdAt: "5 giờ trước",
    isRead: true,
  },
];

export default function NotificationDropdown({
  isOpen,
  onClose,
  notifications: initialNotifications,
  onMarkAllAsRead,
  onNotificationClick,
}: NotificationDropdownProps) {
  const [items, setItems] = useState<NotificationItem[]>(
    initialNotifications && initialNotifications.length > 0
      ? initialNotifications
      : DEFAULT_NOTIFICATIONS
  );
  const [prevInitial, setPrevInitial] = useState(initialNotifications);
  if (initialNotifications !== prevInitial) {
    setPrevInitial(initialNotifications);
    if (initialNotifications && initialNotifications.length > 0) {
      setItems(initialNotifications);
    }
  }
  const [activeTab, setActiveTab] = useState<"all" | "unread">("all");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Xử lý Click Outside để tự động đóng dropdown
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const unreadCount = items.filter((item) => !item.isRead).length;
  const filteredItems =
    activeTab === "unread" ? items.filter((item) => !item.isRead) : items;

  const handleMarkAllRead = () => {
    setItems((prev) => prev.map((item) => ({ ...item, isRead: true })));
    if (onMarkAllAsRead) {
      onMarkAllAsRead();
    }
  };

  const handleItemClick = (notification: NotificationItem) => {
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

  // Helper render Icon & Màu sắc tương ứng theo Severity
  const renderSeverityIcon = (severity: NotificationSeverity) => {
    switch (severity) {
      case "CRASH_500":
        return (
          <div className="w-8 h-8 rounded-xl bg-red-100 flex items-center justify-center text-red-600 shrink-0">
            <AlertCircle className="w-4 h-4" />
          </div>
        );
      case "AI_TIMEOUT":
        return (
          <div className="w-8 h-8 rounded-xl bg-amber-100 flex items-center justify-center text-amber-600 shrink-0">
            <AlertTriangle className="w-4 h-4" />
          </div>
        );
      case "USER_REPORT":
        return (
          <div className="w-8 h-8 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
            <MessageSquareWarning className="w-4 h-4" />
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 rounded-xl bg-orange-100 flex items-center justify-center text-[#C1762A] shrink-0">
            <Bell className="w-4 h-4" />
          </div>
        );
    }
  };

  return (
    <div
      ref={dropdownRef}
      role="dialog"
      aria-label="Thông báo sự cố"
      className="absolute right-0 top-12 w-[360px] sm:w-[380px] bg-white rounded-2xl shadow-xl border border-[#F1CCA6] z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-200"
    >
      {/* ── 1. HEADER ── */}
      <div className="p-3.5 border-b border-[#F1CCA6]/60 bg-gradient-to-b from-[#F7ECE1]/40 to-white">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#1C1917] text-sm md:text-base">
              Thông báo sự cố
            </span>
            {unreadCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-red-500 text-white leading-none">
                {unreadCount}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="inline-flex items-center gap-1 text-xs font-medium text-[#C1762A] hover:text-[#8C4905] hover:underline p-1 rounded-md transition-colors cursor-pointer"
                title="Đánh dấu tất cả đã đọc"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Đọc tất cả</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="p-1 text-[#7A3E04] hover:text-[#1C1917] hover:bg-[#F7ECE1] rounded-lg transition-colors cursor-pointer"
              aria-label="Đóng bảng thông báo"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Tab Switcher: Tất cả / Chưa đọc */}
        <div className="flex items-center gap-1 p-0.5 bg-[#F7ECE1]/60 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`flex-1 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              activeTab === "all"
                ? "bg-white text-[#8C4905] shadow-xs"
                : "text-[#7A3E04] hover:text-[#1C1917]"
            }`}
          >
            Tất cả ({items.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("unread")}
            className={`flex-1 py-1 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              activeTab === "unread"
                ? "bg-white text-[#8C4905] shadow-xs"
                : "text-[#7A3E04] hover:text-[#1C1917]"
            }`}
          >
            Chưa đọc ({unreadCount})
          </button>
        </div>
      </div>

      {/* ── 2. SCROLLABLE BODY ── */}
      <div className="max-h-[380px] overflow-y-auto divide-y divide-[#F1CCA6]/40">
        {filteredItems.length === 0 ? (
          // Empty State thân thiện
          <div className="py-10 px-4 text-center flex flex-col items-center justify-center">
            <div className="w-14 h-14 rounded-2xl bg-[#ECFDF5] border border-[#10B981]/20 flex items-center justify-center text-[#10B981] mb-3 shadow-xs">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <h4 className="text-sm font-bold text-[#1C1917] mb-1">
              Hệ thống an toàn tuyệt đối!
            </h4>
            <p className="text-xs text-[#7A3E04] max-w-[240px] leading-relaxed">
              {activeTab === "unread"
                ? "Bạn đã đọc hết tất cả thông báo sự cố trong danh sách."
                : "Không có sự cố nào được ghi nhận gần đây."}
            </p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <Link
              key={item.id}
              href={`/admin/errors?error_id=${item.errorId || item.id}`}
              onClick={() => handleItemClick(item)}
              className={`block p-3.5 transition-colors cursor-pointer group hover:bg-[#F7ECE1]/40 ${
                !item.isRead ? "bg-[#F7ECE1]/20" : "bg-white"
              }`}
            >
              <div className="flex items-start gap-3">
                {renderSeverityIcon(item.severity)}

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1 mb-0.5">
                    <span className="text-xs font-bold text-[#1C1917] truncate group-hover:text-[#C1762A] transition-colors">
                      {item.title}
                    </span>
                    {!item.isRead && (
                      <span className="w-2 h-2 rounded-full bg-[#C1762A] shrink-0" />
                    )}
                  </div>

                  <p className="text-xs text-[#552B04] line-clamp-2 leading-relaxed mb-1.5">
                    {item.message}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-[#7A3E04]">
                    <span>{item.createdAt}</span>
                    {item.errorId && (
                      <span className="font-mono text-[10px] bg-[#F7ECE1] px-1.5 py-0.5 rounded text-[#8C4905]">
                        {item.errorId}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </Link>
          ))
        )}
      </div>

      {/* ── 3. FOOTER ── */}
      <div className="p-2.5 bg-[#F7ECE1]/40 border-t border-[#F1CCA6]/60 text-center">
        <Link
          href="/admin/errors"
          onClick={onClose}
          className="inline-flex items-center justify-center gap-1.5 w-full py-1.5 text-xs font-bold text-[#8C4905] hover:text-[#C1762A] hover:bg-white rounded-xl transition-all"
        >
          <span>Xem tất cả sự cố tại Quản trị sự cố</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
