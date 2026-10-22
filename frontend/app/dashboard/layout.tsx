/**
 * File: app/dashboard/layout.tsx
 * Mô tả: Layout dùng chung cho phần Dashboard. Cung cấp cấu trúc flexbox 
 * chia đôi màn hình: Sidebar cố định bên trái, Main Content bên phải.
 * - Quản lý bảo mật (Bảo vệ Route): Kiểm tra `useSession()`, nếu chưa đăng nhập thì tự động đẩy về trang chủ (router.push('/')).
 * - Responsive: Render Mobile Header & Hamburger Menu khi ở màn hình nhỏ.
 */
"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { Menu } from "lucide-react";
import { useSession } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";
import { refreshSession } from "@/lib/authFetch";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  // useSession chỉ được dùng để lấy thông tin user hiển thị (avatar, tên).
  // Việc bảo vệ route (redirect nếu chưa đăng nhập) đã do middleware.ts xử lý.
  const { data: session, update } = useSession();
  const pathname = usePathname();
  const router = useRouter();

  // Chặn Quản trị viên (ADMIN) vào các trang Dashboard của người dùng thường
  useEffect(() => {
    if (session && (session.user as any)?.role === "ADMIN") {
      router.replace("/admin");
    }
  }, [session, router]);

  const isChatRoute = pathname === "/dashboard/chat";
  const isMonitorRoute = pathname.startsWith("/dashboard/monitor");
  const isStudent = (session?.user as any)?.role === "STUDENT";

  // [Task T6.12] Lắng nghe sự kiện đổi lớp từ các tab khác qua BroadcastChannel để đồng bộ session toàn Dashboard
  // Chỉ áp dụng cho tài khoản Học sinh và ngoài màn hình Monitor
  useEffect(() => {
    if (isMonitorRoute || !isStudent) return;
    if (typeof window === "undefined" || !("BroadcastChannel" in window)) return;

    const channel = new BroadcastChannel("socratic_grade_sync");
    channel.onmessage = (event) => {
      if (event.data?.type === "GRADE_UPDATED" && event.data.grade) {
        update({ grade_level: Number(event.data.grade) });
      }
    };

    return () => {
      channel.close();
    };
  }, [update, isMonitorRoute, isStudent]);

  // Đồng bộ session & khối lớp khi focus lại tab (giúp tab ẩn danh tự cập nhật theo tab thường)
  // Chỉ áp dụng cho tài khoản Học sinh và ngoài màn hình Monitor
  useEffect(() => {
    if (isMonitorRoute || !isStudent) return;

    const handleFocus = async () => {
      try {
        await refreshSession(update);
      } catch (err) {
        console.warn("Lỗi đồng bộ session layout on focus:", err);
      }
    };

    window.addEventListener("focus", handleFocus);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        handleFocus();
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [update, isMonitorRoute, isStudent]);

  // Khi ở trang Chat hoặc Monitor, nhường layout cho trang con tự quản lý
  if (isChatRoute || isMonitorRoute) {
    return <>{children}</>;
  }


  return (
    <div className="flex h-[100dvh] bg-[#F7ECE1] overflow-hidden font-sans">
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
            <div className="w-8 h-8 rounded-full overflow-hidden flex items-center justify-center bg-[#F7ECE1]">
              <img src="/logo.png" alt="SocraticKid Logo" className="w-full h-full object-cover" />
            </div>
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
