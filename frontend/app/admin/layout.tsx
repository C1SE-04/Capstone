"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import AdminSidebar from "@/components/admin/AdminSidebar";
import AdminHeader from "@/components/admin/AdminHeader";
import { AlertTriangle } from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  // Route Guard: chỉ cho phép tài khoản có role ADMIN truy cập
  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/");
    } else if (status === "authenticated") {
      const role = (session?.user as any)?.role;
      if (role !== "ADMIN") {
        router.replace(role === "MONITOR" ? "/dashboard/monitor" : "/dashboard/chat");
      }
    }
  }, [status, session, router]);

  const userRole = (session?.user as any)?.role;
  const isRealAdmin = userRole === "ADMIN";

  // Màn hình Loading hoặc Chặn quyền truy cập nếu không phải ADMIN
  if (status === "loading" || status === "unauthenticated" || !isRealAdmin) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#F7ECE1] select-none">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#C1762A] to-[#8C4905] text-white flex items-center justify-center font-extrabold text-2xl shadow-lg animate-bounce">
          S
        </div>
        <div className="mt-4 text-base font-extrabold text-[#2A1C0E]">
          SocraticKid Admin Portal
        </div>
        <div className="mt-1 text-xs font-semibold text-[#7E6B5A] flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#C1762A] animate-ping" />
          {status === "loading"
            ? "Đang xác thực quyền Quản trị viên..."
            : !isRealAdmin && status === "authenticated"
            ? "Bạn không có quyền truy cập. Đang chuyển hướng..."
            : "Chuyển hướng đăng nhập..."}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen max-h-screen overflow-hidden bg-[#F7ECE1] text-[#2A1C0E]">
      {/* ── 1. Desktop Sidebar (Cố định màn hình lớn) ── */}
      <div className="hidden lg:block h-full flex-shrink-0">
        <AdminSidebar />
      </div>

      {/* ── 2. Mobile Sidebar Drawer ── */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            onClick={() => setIsMobileOpen(false)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
          />

          {/* Drawer Panel */}
          <div className="fixed inset-y-0 left-0 w-64 shadow-2xl transition-transform animate-in slide-in-from-left duration-200">
            <AdminSidebar onCloseMobile={() => setIsMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* ── 3. Main Content Shell ── */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        {/* Header trên cùng */}
        <AdminHeader onOpenMobileSidebar={() => setIsMobileOpen(true)} />

        {/* Nội dung trang con cuộn độc lập */}
        <main className="flex-1 overflow-y-auto bg-[#F7ECE1] p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto w-full">{children}</div>
        </main>
      </div>
    </div>
  );
}
