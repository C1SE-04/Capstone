"use client";

/**
 * File: frontend/hooks/useAdminNotifications.ts
 * Sprint 11 - US 11.3 (Task #387 - T11.3.5)
 * ==============================================================================
 * React Hook đồng bộ State thông báo lỗi Admin giữa các Component (Icon Chuông Header,
 * Dropdown Thông Báo, Drawer Chi Tiết Lỗi) và giữa nhiều Tab trình duyệt.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getStoredReadErrorIds,
  markErrorAsRead as storageMarkErrorAsRead,
  markAllErrorsAsRead as storageMarkAllErrorsAsRead,
  isErrorRead as storageIsErrorRead,
  calculateUnreadCount as storageCalculateUnreadCount,
  ADMIN_NOTIFICATIONS_UPDATED_EVENT,
  ADMIN_READ_ERRORS_STORAGE_KEY,
} from "@/lib/adminNotificationStorage";
import { SystemErrorItem } from "@/types/admin";

export function useAdminNotifications(errorsList: SystemErrorItem[] = []) {
  const [readIds, setReadIds] = useState<string[]>([]);
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // Khởi tạo đọc từ LocalStorage sau khi mounted trên client (tránh Next.js hydration mismatch)
  useEffect(() => {
    setIsMounted(true);
    setReadIds(getStoredReadErrorIds());

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === ADMIN_READ_ERRORS_STORAGE_KEY) {
        setReadIds(getStoredReadErrorIds());
      }
    };

    const handleCustomUpdate = () => {
      setReadIds(getStoredReadErrorIds());
    };

    window.addEventListener("storage", handleStorageChange);
    window.addEventListener(ADMIN_NOTIFICATIONS_UPDATED_EVENT, handleCustomUpdate);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      window.removeEventListener(ADMIN_NOTIFICATIONS_UPDATED_EVENT, handleCustomUpdate);
    };
  }, []);

  // Đánh dấu 1 sự cố là đã xem
  const markAsRead = useCallback((errorId: string) => {
    storageMarkErrorAsRead(errorId);
    setReadIds(getStoredReadErrorIds());
  }, []);

  // Đánh dấu tất cả sự cố là đã xem
  const markAllAsRead = useCallback((errorIds?: string[]) => {
    const targetIds = errorIds || errorsList.map((err) => err.id);
    storageMarkAllErrorsAsRead(targetIds);
    setReadIds(getStoredReadErrorIds());
  }, [errorsList]);

  // Kiểm tra 1 sự cố cụ thể đã đọc hay chưa
  const checkIsRead = useCallback(
    (errorId: string) => {
      if (!isMounted) return false;
      return storageIsErrorRead(errorId, readIds);
    },
    [isMounted, readIds]
  );

  // Tính số lượng lỗi chưa đọc
  const unreadCount = useMemo(() => {
    if (!isMounted || !errorsList.length) return 0;
    return storageCalculateUnreadCount(errorsList, readIds);
  }, [isMounted, errorsList, readIds]);

  // Danh sách các lỗi chưa đọc
  const unreadErrors = useMemo(() => {
    if (!isMounted) return errorsList;
    const readSet = new Set(readIds);
    return errorsList.filter((err) => {
      const isOpen = !err.status || err.status.toUpperCase() === "OPEN";
      return isOpen && !readSet.has(err.id);
    });
  }, [isMounted, errorsList, readIds]);

  return {
    isMounted,
    readIds,
    unreadCount,
    unreadErrors,
    markAsRead,
    markAllAsRead,
    checkIsRead,
  };
}

