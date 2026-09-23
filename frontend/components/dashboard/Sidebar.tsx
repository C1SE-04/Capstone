/**
 * File: components/dashboard/Sidebar.tsx
 * Mô tả: Component thanh điều hướng nằm bên trái (Sidebar).
 * - Render Logo, danh sách các link điều hướng (Trang chủ, Lịch sử, Cài đặt).
 * - Hiển thị thông tin hồ sơ rút gọn (Mini Profile) và Nút Đăng xuất ở dưới cùng.
 * - Hỗ trợ hiệu ứng hiển thị lớp phủ (overlay) trên Mobile thông qua props `isMobileOpen`.
 */
"use client";

import { usePathname, useRouter } from "next/navigation";
import { Home, History, Settings, LogOut, Menu, X } from "lucide-react";
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

  const navLinks = [
    { name: "Trang chủ", href: "/dashboard", icon: Home },
    { name: "Lịch sử", href: "/dashboard/history", icon: History },
    { name: "Cài đặt", href: "/dashboard/settings", icon: Settings },
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

        {/* Logo Area */}
        <div className="p-6 pt-8 md:pt-6 flex flex-col items-center border-b border-[#C1762A]/20">
          <div className="w-16 h-16 bg-[#D9D9D9] rounded-2xl flex items-center justify-center text-[#8C4905] font-bold text-xl shadow-inner cursor-pointer" onClick={() => router.push("/")}>
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

        {/* Mini Profile Area */}
        <div className="p-4 border-t border-[#C1762A]/20 bg-[#F1CCA6]">
          <div className="flex items-center gap-3 mb-4 p-2">
            {session?.user?.image ? (
              <img
                src={session.user.image}
                alt="Avatar"
                className="w-10 h-10 rounded-full border-2 border-[#C1762A]"
              />
            ) : (
              <div className="w-10 h-10 bg-[#C1762A] rounded-full flex items-center justify-center text-white font-bold">
                {session?.user?.name?.charAt(0) || "U"}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-[#8C4905] truncate">
                {session?.user?.name || "Người dùng"}
              </p>
            </div>
          </div>
          
          <button
            onClick={() => signOut({ callbackUrl: "/" })}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-transparent text-[#8C4905] border border-[#C1762A] rounded-lg hover:bg-[#C1762A] hover:text-white transition-colors font-semibold"
          >
            <LogOut size={18} />
            <span>Đăng xuất</span>
          </button>
        </div>
      </aside>
    </>
  );
}
