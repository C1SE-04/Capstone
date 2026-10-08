"use client";

/**
 * File: app/dashboard/monitor/layout.tsx
 * Mô tả: Layout riêng cho Dashboard Phụ huynh.
 * - Dùng layout 2 cột: MonitorSidebar (trái) + Main content (phải).
 * - Bảo vệ route: chỉ role MONITOR mới được truy cập; STUDENT bị redirect về /dashboard.
 */

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import MonitorSidebar, {
  LinkedStudent,
} from "@/components/monitor/MonitorSidebar";
import { Menu, X } from "lucide-react";

// Context để chia sẻ học sinh đang được chọn xuống các page con
import { createContext, useContext } from "react";

interface MonitorContextValue {
  selectedStudent: LinkedStudent | null;
  setSelectedStudent: (s: LinkedStudent | null) => void;
}

export const MonitorContext = createContext<MonitorContextValue>({
  selectedStudent: null,
  setSelectedStudent: () => {},
});

export function useMonitorContext() {
  return useContext(MonitorContext);
}

export default function MonitorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [selectedStudent, setSelectedStudent] = useState<LinkedStudent | null>(
    null
  );
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(false);

  // Tách mount/unmount khỏi animation: show sau 1 tick để transition chạy
  const openSidebar = () => {
    setIsMobileSidebarOpen(true);
    requestAnimationFrame(() => setSidebarVisible(true));
  };
  const closeSidebar = () => {
    setSidebarVisible(false);
    setTimeout(() => setIsMobileSidebarOpen(false), 300); // match duration-300
  };

  // Bảo vệ route: chỉ MONITOR mới được vào
  useEffect(() => {
    if (status === "loading") return;
    const role = (session?.user as any)?.role;
    if (!session || role !== "MONITOR") {
      router.replace("/dashboard");
    }
  }, [session, status, router]);

  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-[#F7ECE1]">
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
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </div>
    );
  }

  return (
    <MonitorContext.Provider value={{ selectedStudent, setSelectedStudent }}>
      <div className="flex h-screen bg-[#F7ECE1] overflow-hidden font-sans">
        {/* Sidebar — Desktop */}
        <div className="hidden md:flex h-full">
          <MonitorSidebar
            selectedStudentId={selectedStudent?.student_id ?? null}
            onSelectStudent={(s) => setSelectedStudent(s)}
          />
        </div>

        {/* Mobile: overlay sidebar with smooth transition */}
        {isMobileSidebarOpen && (
          <div className="fixed inset-0 z-50 flex md:hidden">
            {/* Overlay mờ dần */}
            <div
              className="absolute inset-0 bg-black/50 transition-opacity duration-300"
              style={{ opacity: sidebarVisible ? 1 : 0 }}
              onClick={closeSidebar}
            />
            {/* Sidebar trượt từ trái */}
            <div
              className="relative z-10 h-full transition-transform duration-300 ease-in-out"
              style={{ transform: sidebarVisible ? "translateX(0)" : "translateX(-100%)" }}
            >
              <MonitorSidebar
                selectedStudentId={selectedStudent?.student_id ?? null}
                onSelectStudent={(s) => {
                  setSelectedStudent(s);
                  closeSidebar();
                }}
              />
            </div>
            <button
              onClick={closeSidebar}
              className="absolute top-4 right-4 z-20 text-white transition-opacity duration-300"
              style={{ opacity: sidebarVisible ? 1 : 0 }}
            >
              <X size={24} />
            </button>
          </div>
        )}

        {/* Main content */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Mobile header */}
          <header className="bg-white border-b border-[#F1CCA6] p-3 flex md:hidden items-center gap-3 shadow-sm">
            <button
              onClick={openSidebar}
              className="p-2 text-[#8C4905] hover:bg-[#F1CCA6]/50 rounded-lg transition-colors"
            >
              <Menu size={22} />
            </button>
            <span className="font-bold italic text-[#C1762A] text-base">
              SocraticKid — Phụ huynh
            </span>
          </header>

          <main className="flex-1 overflow-y-auto p-4 md:p-8">{children}</main>
        </div>
      </div>
    </MonitorContext.Provider>
  );
}
