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

  // Route Guard: chỉ redirect khi BIẾT CHẮC chưa đăng nhập (status xác định rõ)
  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/");
    }
  }, [status, router]);

  // Màn hình Loading sang trọng chuẩn hệ màu SocraticKid
  if (status === "loading" || status === "unauthenticated") {
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
          {status === "loading" ? "Đang xác thực quyền Quản trị viên..." : "Chuyển hướng đăng nhập..."}
        </div>
      </div>
    );
  }

  const userRole = (session?.user as any)?.role || "STUDENT";
  const isRealAdmin = userRole === "ADMIN";

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

        {/* Banner hỗ trợ kiểm thử Sprint 7 (nếu user test chưa có role ADMIN trên DB) */}
        {!isRealAdmin && (
          <div className="bg-[#FDF3E7] border-b border-[#F1CCA6] px-4 py-2 flex items-center justify-between text-xs text-[#8C4905]">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-[#C1762A] flex-shrink-0" />
              <span>
                <strong>Chế độ Xem Thử Nghiệm Sprint 7:</strong> Bạn đang truy cập với vai trò{" "}
                <code className="bg-white/80 px-1.5 py-0.5 rounded text-[#C1762A] font-bold">
                  {userRole}
                </code>
                . Toàn bộ các trang và nút bấm quản trị đã được mở khóa để kiểm thử.
              </span>
            </div>
            <span className="hidden md:inline-block text-[11px] font-semibold text-[#A18E7F]">
              Cổng Quản Trị SocraticKid
            </span>
          </div>
        )}

        {/* Nội dung trang con cuộn độc lập */}
        <main className="flex-1 overflow-y-auto bg-[#F7ECE1] p-4 md:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto w-full">{children}</div>
        </main>
      </div>
    </div>
  );
}
