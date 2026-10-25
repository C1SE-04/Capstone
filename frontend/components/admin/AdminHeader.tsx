"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, Search, Bell, Plus, Sparkles, CheckCircle2 } from "lucide-react";
import Breadcrumbs from "./Breadcrumbs";

interface AdminHeaderProps {
  onOpenMobileSidebar?: () => void;
}

export default function AdminHeader({ onOpenMobileSidebar }: AdminHeaderProps) {
  const [searchValue, setSearchValue] = useState("");
  const [showNotificationToast, setShowNotificationToast] = useState(false);

  const handleNotificationClick = () => {
    setShowNotificationToast(true);
    setTimeout(() => setShowNotificationToast(false), 3500);
  };

  return (
    <header className="h-16 bg-white border-b border-[#F1CCA6] px-4 md:px-8 flex items-center justify-between shrink-0 relative z-10 shadow-xs">
      {/* ── Bên trái: Mobile Hamburger & Breadcrumbs ── */}
      <div className="flex items-center gap-3">
        {onOpenMobileSidebar && (
          <button
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
            className="w-48 lg:w-60 pl-9 pr-3 py-1.5 text-xs lg:text-sm bg-[#F7ECE1]/60 hover:bg-white focus:bg-white border border-[#F1CCA6] focus:border-[#C1762A] rounded-xl text-[#2A1C0E] placeholder:text-[#C1762A]/60 focus:outline-hidden transition-all"
          />
        </div>

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={handleNotificationClick}
            title="Xem cảnh báo an toàn & thông báo"
            className="relative p-2 rounded-xl border border-[#F1CCA6] text-[#8C4905] hover:bg-[#F7ECE1] transition-all cursor-pointer"
            aria-label="Thông báo"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#D93829] ring-2 ring-white" />
          </button>

          {/* Toast thông báo popup nhanh */}
          {showNotificationToast && (
            <div className="absolute right-0 top-12 w-72 bg-white rounded-xl shadow-lg border border-[#F1CCA6] p-3 z-50 text-xs animate-in fade-in slide-in-from-top-2 duration-200">
              <div className="flex items-start gap-2.5">
                <div className="p-1 rounded-full bg-[#FDF0ED] text-[#D93829] shrink-0">
                  <Bell className="w-3.5 h-3.5" />
                </div>
                <div>
                  <div className="font-bold text-[#2A1C0E]">3 Cảnh báo Safety chưa duyệt</div>
                  <div className="text-[#7E6B5A] mt-0.5">
                    Hệ thống phát hiện câu hỏi cần kiểm tra tại mục Giám sát Safety AI.
                  </div>
                  <Link
                    href="/admin/safety"
                    className="inline-block mt-1.5 text-[#C1762A] hover:underline font-semibold"
                  >
                    Đi tới Safety AI →
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Nút Hành động nhanh: + Thêm Học Liệu */}
        <Link
          href="/admin/content"
          className="inline-flex items-center gap-1.5 px-3 md:px-3.5 py-1.5 md:py-2 rounded-xl bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 active:scale-95 text-white text-xs md:text-sm font-bold shadow-sm transition-all shrink-0 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Thêm Học Liệu</span>
          <span className="sm:hidden">Thêm</span>
        </Link>
      </div>
    </header>
  );
}
