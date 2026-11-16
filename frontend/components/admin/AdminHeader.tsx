"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Search, Bell, Plus } from "lucide-react";
import Breadcrumbs from "./Breadcrumbs";
import NotificationDropdown from "./NotificationDropdown";

interface AdminHeaderProps {
  onOpenMobileSidebar?: () => void;
}

export default function AdminHeader({ onOpenMobileSidebar }: AdminHeaderProps) {
  const pathname = usePathname();
  const [searchValue, setSearchValue] = useState("");
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(3);

  const isContentTab = pathname?.startsWith("/admin/content");

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

        {/* Notification Bell & Dropdown */}
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
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-[#EF4444] text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white animate-pulse">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {/* Dropdown Menu thông báo */}
          <NotificationDropdown
            isOpen={isNotificationOpen}
            onClose={() => setIsNotificationOpen(false)}
            onMarkAllAsRead={() => setUnreadCount(0)}
            onNotificationClick={() =>
              setUnreadCount((prev) => Math.max(0, prev - 1))
            }
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
