/**
 * File: components/dashboard/Sidebar.tsx
 * Mô tả: Component thanh điều hướng nằm bên trái (Sidebar).
 * - Render Logo, danh sách các link điều hướng (Trang chủ, Lịch sử, Cài đặt).
 * - Hiển thị thông tin hồ sơ rút gọn (Mini Profile) và Nút Đăng xuất ở dưới cùng.
 * - Hỗ trợ hiệu ứng hiển thị lớp phủ (overlay) trên Mobile thông qua props `isMobileOpen`.
 */
"use client";

import { usePathname, useRouter } from "next/navigation";
import { History, Settings, LogOut, X } from "lucide-react";
import { useSession, signOut } from "next-auth/react";
import { cn } from "@/lib/utils";
import { useState } from "react";

interface SidebarProps {
  className?: string;
  isMobileOpen: boolean;
  setIsMobileOpen: (open: boolean) => void;
}

export function Sidebar({ className, isMobileOpen, setIsMobileOpen }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const [showSettings, setShowSettings] = useState(false);

  const navLinks = [
    { name: "Lịch sử", href: "/dashboard/history", icon: History },
  ];

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          "fixed md:static inset-y-0 left-0 z-50 w-64 bg-[#F1CCA6] flex flex-col h-full transform transition-transform duration-300 ease-in-out border-r border-[#C1762A]/20",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          className
        )}
      >
        {/* Mobile close button */}
        <div className="md:hidden flex justify-end p-4">
          <button onClick={() => setIsMobileOpen(false)} className="text-[#8C4905]">
            <X size={24} />
          </button>
        </div>

        {/* Logo Area — clicking navigates to Dashboard */}
        <div className="p-6 pt-8 md:pt-6 flex flex-col items-center border-b border-[#C1762A]/20">
          <div
            className="w-16 h-16 bg-[#D9D9D9] rounded-2xl flex items-center justify-center text-[#8C4905] font-bold text-xl shadow-inner cursor-pointer hover:bg-[#F7AD62]/40 transition-colors"
            onClick={() => router.push("/dashboard")}
          >
            SK
          </div>
          <h2 className="mt-4 text-[#8C4905] font-extrabold italic text-2xl tracking-tight">
            SocraticKid
          </h2>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 py-6 px-4 space-y-2 overflow-y-auto">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href;

            return (
              <button
                key={link.name}
                onClick={() => {
                  router.push(link.href);
                  setIsMobileOpen(false);
                }}
                className={cn(
                  "w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-200 font-semibold group",
                  isActive
                    ? "bg-[#C1762A] text-white shadow-md"
                    : "text-[#8C4905] hover:bg-[#F7AD62]/20 hover:text-[#CB6600]"
                )}
              >
                <Icon size={20} className={cn(isActive ? "text-white" : "text-[#C1762A] group-hover:text-[#CB6600]", "transition-colors")} />
                <span>{link.name}</span>
              </button>
            );
          })}
        </nav>

        {/* Settings Dropdown */}
        {showSettings && (
          <div className="absolute bottom-20 left-4 right-4 bg-white rounded-xl shadow-lg border border-[#F1CCA6] p-2 z-50 animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[#8C4905] hover:bg-[#F7ECE1] rounded-lg transition-colors font-medium"
            >
              <LogOut size={16} />
              Đăng xuất
            </button>
          </div>
        )}

        {/* Mini Profile Area */}
        <div className="p-4 border-t border-[#C1762A]/20 bg-[#F1CCA6] flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {session?.user?.image ? (
              <img
                src={session.user.image}
                alt="Avatar"
                className="w-8 h-8 rounded-full border border-[#C1762A]"
              />
            ) : (
              <div className="w-8 h-8 bg-[#C1762A] rounded-full flex items-center justify-center text-white font-bold text-sm">
                {session?.user?.name?.charAt(0) || "U"}
              </div>
            )}
            <p className="text-sm font-bold text-[#8C4905] truncate flex-1">
              {session?.user?.name || "Người dùng"}
            </p>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-[#8C4905] hover:bg-[#F7AD62]/30 rounded-lg transition-colors"
          >
            <Settings size={20} />
          </button>
        </div>
      </aside>
    </>
  );
}
