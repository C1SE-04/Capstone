/**
 * File: app/dashboard/layout.tsx
 * Mô tả: Layout dùng chung cho phần Dashboard. Cung cấp cấu trúc flexbox 
 * chia đôi màn hình: Sidebar cố định bên trái, Main Content bên phải.
 * - Quản lý bảo mật (Bảo vệ Route): Kiểm tra `useSession()`, nếu chưa đăng nhập thì tự động đẩy về trang chủ (router.push('/')).
 * - Responsive: Render Mobile Header & Hamburger Menu khi ở màn hình nhỏ.
 */
"use client";

import { useState } from "react";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { Menu } from "lucide-react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F7ECE1]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#C1762A]"></div>
      </div>
    );
  }

  if (!session) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="flex h-screen bg-[#F7ECE1] overflow-hidden font-sans">
      <Sidebar isMobileOpen={isMobileOpen} setIsMobileOpen={setIsMobileOpen} />
      
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Mobile Header */}
        <header className="md:hidden bg-white border-b border-[#F1CCA6] p-4 flex items-center justify-between shadow-sm z-30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#D9D9D9] rounded-xl flex items-center justify-center text-[#8C4905] font-bold shadow-inner text-sm">
              SK
            </div>
            <h1 className="text-xl font-bold italic text-[#C1762A]">SocraticKid</h1>
          </div>
          <button
            onClick={() => setIsMobileOpen(true)}
            className="p-2 text-[#8C4905] hover:bg-[#F1CCA6]/50 rounded-lg transition-colors"
          >
            <Menu size={24} />
          </button>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8 bg-[#F7ECE1]">
          {children}
        </main>
      </div>
    </div>
  );
}
