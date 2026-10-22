"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import AdminSidebar from "@/components/admin/AdminSidebar";
import AdminHeader from "@/components/admin/AdminHeader";

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

  // Màn hình Loading đồng bộ với Dashboard Phụ Huynh / Monitor
  if (status === "loading" || status === "unauthenticated" || !isRealAdmin) {
    return (
      <div className="flex h-[100dvh] items-center justify-center bg-[#F7ECE1]">
        <svg
          className="animate-spin h-10 w-10 text-[#C1762A]"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v8H4z"
          />
        </svg>
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
