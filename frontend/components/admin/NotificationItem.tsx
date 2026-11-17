"use client";

import React from "react";
import Link from "next/link";
import {
  AlertCircle,
  AlertTriangle,
  MessageSquareWarning,
  Bell,
  Clock,
  Sparkles,
} from "lucide-react";
import { formatDistanceToNow, parseISO, isValid } from "date-fns";
import { vi } from "date-fns/locale";

/**
 * File: frontend/components/admin/NotificationItem.tsx
 * Sprint 11 - Task T11.3.2: Render Thẻ Thông Báo Sự Cố
 * ==============================================================================
 * Component hiển thị từng mục thông báo sự cố trong Dropdown Thông Báo của Admin.
 *
 * Tiêu chuẩn UX/UI:
 * - Phân cấp màu sắc biểu tượng rõ ràng theo Severity:
 *   + CRASH_500: Nền #FEF2F2, Icon #EF4444
 *   + AI_TIMEOUT: Nền #FFFBEB, Icon #F59E0B
 *   + USER_REPORT: Nền #EFF6FF, Icon #3B82F6
 * - Trạng thái Đọc/Chưa đọc:
 *   + Chưa đọc: Nền trắng ngà bg-white, chấm tròn xanh nước biển w-2.5 h-2.5 bg-blue-500, title font-bold
 *   + Đã đọc: Nền thẻ hơi chìm bg-gray-50/50, không có chấm xanh, text font-medium
 * - Định dạng thời gian tương đối bằng date-fns (locale tiếng Việt "x phút trước")
 * - Cắt ngắn nội dung với `line-clamp-2 text-sm text-gray-600` chống vỡ layout
 */

export type NotificationSeverity = "CRASH_500" | "AI_TIMEOUT" | "USER_REPORT" | string;

export interface NotificationItemData {
  id: string;
  title: string;
  message: string;
  severity: NotificationSeverity;
  createdAt: string;
  isRead: boolean;
  errorId?: string;
}

interface NotificationItemProps {
  notification: NotificationItemData;
  onClick?: (notification: NotificationItemData) => void;
  className?: string;
}

/**
 * Helper định dạng thời gian tương đối an toàn bằng date-fns
 */
function formatRelativeTime(dateString: string): string {
  if (!dateString) return "Vừa xong";

  // Nếu chuỗi đã là dạng tương đối do server hoặc mock trả về (ví dụ "3 phút trước", "Hôm nay")
  if (dateString.includes("trước") || dateString.includes("Hôm nay") || dateString.includes("Vừa xong")) {
    return dateString;
  }

  try {
    const parsedDate = parseISO(dateString);
    if (isValid(parsedDate)) {
      return formatDistanceToNow(parsedDate, {
        addSuffix: true,
        locale: vi,
      });
    }

    const nativeDate = new Date(dateString);
    if (isValid(nativeDate)) {
      return formatDistanceToNow(nativeDate, {
        addSuffix: true,
        locale: vi,
      });
    }
  } catch {
    // Fallback nếu chuỗi không parse được
  }

  return dateString;
}

export default function NotificationItem({
  notification,
  onClick,
  className = "",
}: NotificationItemProps) {
  const { id, title, message, severity, createdAt, isRead, errorId } = notification;

  // ── Phân cấp màu sắc & Icon theo Severity (Mục tiêu 1 của T11.3.2) ──
  const renderSeverityIcon = () => {
    const normalized = (severity || "").toUpperCase();

    switch (normalized) {
      case "CRASH_500":
        return (
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
            style={{ backgroundColor: "#FEF2F2", color: "#EF4444" }}
            title="Lỗi sập hệ thống nghiêm trọng (Crash 500)"
          >
            <AlertCircle className="w-4 h-4 stroke-[2.2]" />
          </div>
        );

      case "AI_TIMEOUT":
        return (
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
            style={{ backgroundColor: "#FFFBEB", color: "#F59E0B" }}
            title="Cảnh báo quá thời gian chờ phản hồi AI (Timeout)"
          >
            <AlertTriangle className="w-4 h-4 stroke-[2.2]" />
          </div>
        );

      case "USER_REPORT":
        return (
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-xs"
            style={{ backgroundColor: "#EFF6FF", color: "#3B82F6" }}
            title="Báo cáo phản ánh từ học sinh/phụ huynh"
          >
            <MessageSquareWarning className="w-4 h-4 stroke-[2.2]" />
          </div>
        );

      default:
        return (
          <div className="w-9 h-9 rounded-xl bg-orange-50 text-[#C1762A] flex items-center justify-center shrink-0 shadow-xs">
            <Bell className="w-4 h-4" />
          </div>
        );
    }
  };

  const relativeTime = formatRelativeTime(createdAt);
  const targetHref = `/admin/errors?error_id=${errorId || id}`;

  const handleClick = () => {
    if (onClick) {
      onClick(notification);
    }
  };

  return (
    <Link
      href={targetHref}
      onClick={handleClick}
      className={`block p-3.5 transition-all duration-150 cursor-pointer group border-b border-[#F1CCA6]/40 last:border-b-0 hover:bg-[#F7ECE1]/50 focus:outline-hidden focus:bg-[#F7ECE1]/60 ${
        !isRead ? "bg-white" : "bg-gray-50/50"
      } ${className}`}
    >
      <div className="flex items-start gap-3">
        {/* Biểu tượng phân cấp mức độ lỗi */}
        {renderSeverityIcon()}

        {/* Nội dung thông báo */}
        <div className="flex-1 min-w-0">
          {/* Hàng 1: Tiêu đề + Chấm tròn trạng thái chưa đọc */}
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4
              className={`text-xs sm:text-sm truncate transition-colors group-hover:text-[#C1762A] ${
                !isRead
                  ? "font-bold text-[#1C1917]"
                  : "font-medium text-gray-700"
              }`}
            >
              {title}
            </h4>

            {/* Chấm tròn trạng thái Chưa đọc (Unread Indicator) */}
            {!isRead && (
              <span
                className="w-2.5 h-2.5 bg-blue-500 rounded-full shrink-0 ring-2 ring-blue-100 shadow-xs mt-1 animate-pulse"
                title="Chưa đọc"
              />
            )}
          </div>

          {/* Hàng 2: Tóm tắt nội dung cắt dòng gọn gàng */}
          <p className="line-clamp-2 text-xs sm:text-sm text-gray-600 leading-relaxed mb-2 group-hover:text-gray-800 transition-colors">
            {message}
          </p>

          {/* Hàng 3: Metadata - Thời gian tương đối & Mã sự cố */}
          <div className="flex items-center justify-between text-[11px] text-[#7A3E04]/80">
            <span className="flex items-center gap-1 font-medium">
              <Clock className="w-3 h-3 text-[#C1762A]" />
              {relativeTime}
            </span>

            {errorId && (
              <span className="font-mono text-[10px] font-semibold bg-[#F7ECE1] px-1.5 py-0.5 rounded-md text-[#8C4905] border border-[#F1CCA6]/60">
                {errorId}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
