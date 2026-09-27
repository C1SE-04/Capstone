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
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { Menu } from "lucide-react";
import { useSession } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  // useSession chỉ được dùng để lấy thông tin user hiển thị (avatar, tên).
  // Việc bảo vệ route (redirect nếu chưa đăng nhập) đã do middleware.ts xử lý.
  const { data: session } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  const isChatRoute = pathname === "/dashboard/chat";

  // Khi ở trang Chat, nhường layout cho ChatPage tự quản lý Sidebar và ChatWindow bằng State React thuần
  if (isChatRoute) {
    return <>{children}</>;
  }

  return (
    <div className="flex h-screen bg-[#F7ECE1] overflow-hidden font-sans">
      <Sidebar isMobileOpen={isMobileOpen} setIsMobileOpen={setIsMobileOpen} />

      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header trên Mobile */}
        <header className="bg-white border-b border-[#F1CCA6] p-3 flex md:hidden items-center justify-between shadow-sm z-30">
          <button
            onClick={() => setIsMobileOpen(true)}
            className="p-2 text-[#8C4905] hover:bg-[#F1CCA6]/50 rounded-lg transition-colors"
          >
            <Menu size={22} />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#D9D9D9] rounded-xl flex items-center justify-center text-[#8C4905] font-bold shadow-inner text-xs">SK</div>
            <span className="text-base font-bold italic text-[#C1762A]">SocraticKid</span>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto bg-[#F7ECE1] p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
