"use client";

/**
 * File: components/monitor/MonitorSidebar.tsx
 * Mô tả: Sidebar dành riêng cho Dashboard Phụ huynh (role=MONITOR).
 * - Hiển thị danh sách con đã liên kết, cho phép chuyển đổi xem.
 * - Tích hợp nút "Thêm con" mở LinkStudentModal.
 * - Hỗ trợ huỷ liên kết từng học sinh.
 * - Kết nối API thật: GET /family/students, DELETE /family/students/{id}
 */

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  UserPlus,
  LogOut,
  ChevronLeft,
  Users,
  Trash2,
  User,
  Home,
  Edit2,
  Settings,
  Settings2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import LinkStudentModal from "@/components/LinkStudentModal";

export interface LinkedStudent {
  student_id: string;
  email: string;
  nickname: string | null;
  created_at: string;
}

interface MonitorSidebarProps {
  selectedStudentId: string | null;
  onSelectStudent: (student: LinkedStudent) => void;
}

export default function MonitorSidebar({
  selectedStudentId,
  onSelectStudent,
}: MonitorSidebarProps) {
  const { data: session } = useSession();
  const router = useRouter();
  const [students, setStudents] = useState<LinkedStudent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Đóng dropdown khi click bên ngoài
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        settingsRef.current &&
        !settingsRef.current.contains(event.target as Node)
      ) {
        setShowSettings(false);
      }
    };
    if (showSettings) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showSettings]);

  // Fetch danh sách con từ API
  const fetchStudents = async () => {
    setIsLoading(true);
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/family/students`, {
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (res.ok) {
        const data: LinkedStudent[] = await res.json();
        setStudents(data);
        // Tự động chọn con đầu tiên nếu chưa chọn, hoặc reset nếu không có con
        if (data.length > 0) {
          if (!selectedStudentId) {
            onSelectStudent(data[0]);
          }
        } else {
          onSelectStudent(null as any);
        }
      }
    } catch (err) {
      console.error("Lỗi fetch danh sách học sinh:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (session?.access_token) {
      fetchStudents();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.access_token]);

  // Huỷ liên kết với 1 học sinh
  const handleRemoveStudent = async (studentId: string) => {
    if (!confirm("Bạn có chắc muốn huỷ liên kết với học sinh này?")) return;
    setRemovingId(studentId);
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/family/students/${studentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });
      if (res.ok) {
        const updated = students.filter((s) => s.student_id !== studentId);
        setStudents(updated);
        // Nếu đang xem con này → chuyển sang con khác hoặc clear
        if (selectedStudentId === studentId) {
          onSelectStudent(updated[0] ?? null!);
        }
      }
    } catch (err) {
      console.error("Lỗi huỷ liên kết:", err);
    } finally {
      setRemovingId(null);
    }
  };

  const handleEditNickname = async (student: LinkedStudent) => {
    const newName = window.prompt("Nhập biệt danh mới cho học sinh này:", student.nickname || "");
    if (newName === null || newName.trim() === student.nickname) return;
    
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/family/students/${student.student_id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ nickname: newName.trim() }),
      });
      if (res.ok) {
        const updatedStudent = await res.json();
        setStudents(prev => prev.map(s => s.student_id === student.student_id ? updatedStudent : s));
        if (selectedStudentId === student.student_id) {
          onSelectStudent(updatedStudent);
        }
      } else {
        alert("Có lỗi xảy ra khi cập nhật biệt danh!");
      }
    } catch (err) {
      console.error("Lỗi cập nhật biệt danh:", err);
      alert("Lỗi kết nối tới máy chủ.");
    }
  };

  // Sau khi thêm con thành công → fetch lại danh sách
  const handleLinkSuccess = (_name: string) => {
    fetchStudents();
  };

  const getDisplayName = (s: LinkedStudent) =>
    s.nickname || s.email.split("@")[0];

  const getInitial = (s: LinkedStudent) =>
    getDisplayName(s).charAt(0).toUpperCase();

  return (
    <>
      <aside className="w-72 bg-[#F1CCA6] flex flex-col h-full border-r border-[#C1762A]/20 shrink-0 relative">
        {/* Logo / Header */}
        <div className="p-6 border-b border-[#C1762A]/20">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => router.push("/")}
          >
            <div className="w-10 h-10 rounded-full overflow-hidden flex items-center justify-center hover:opacity-80 transition-opacity bg-[#F7ECE1]">
              <img src="/logo.png" alt="SocraticKid Logo" className="w-full h-full object-cover" />
            </div>
            <div>
              <h2 className="text-[#8C4905] font-extrabold italic text-lg tracking-tight leading-none">
                SocraticKid
              </h2>
              <p className="text-xs text-[#C1762A] font-medium mt-0.5">
                Bảng điều khiển
              </p>
            </div>
          </div>
        </div>

        {/* Tiêu đề danh sách con */}
        <div className="px-4 pt-5 pb-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={16} className="text-[#C1762A]" />
            <span className="text-sm font-bold text-[#8C4905]">
              Danh sách con ({students.length})
            </span>
          </div>
        </div>

        {/* Danh sách học sinh */}
        <nav className="flex-1 overflow-y-auto px-3 pb-3 space-y-1">
          {isLoading ? (
            // Skeleton loading
            <div className="space-y-2 px-1 pt-1">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="h-16 bg-[#F7AD62]/20 rounded-xl animate-pulse"
                />
              ))}
            </div>
          ) : students.length === 0 ? (
            // Empty state
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center gap-3">
              <div className="w-14 h-14 bg-[#F7ECE1] rounded-2xl flex items-center justify-center">
                <User size={28} className="text-[#C1762A]/50" />
              </div>
              <p className="text-sm text-[#8C4905]/70 font-medium leading-relaxed">
                Chưa có học sinh nào được liên kết.
                <br />
                Nhấn &quot;Thêm con&quot; để bắt đầu.
              </p>
            </div>
          ) : (
            students.map((student) => {
              const isActive = student.student_id === selectedStudentId;
              return (
                <div
                  key={student.student_id}
                  className={cn(
                    "group flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 cursor-pointer",
                    isActive
                      ? "bg-[#C1762A] text-white shadow-md"
                      : "text-[#8C4905] hover:bg-[#F7AD62]/20"
                  )}
                  onClick={() => onSelectStudent(student)}
                >
                  {/* Avatar */}
                  <div
                    className={cn(
                      "w-9 h-9 rounded-full flex items-center justify-center font-black text-sm shrink-0",
                      isActive
                        ? "bg-white/20 text-white"
                        : "bg-[#C1762A] text-white"
                    )}
                  >
                    {getInitial(student)}
                  </div>

                  {/* Tên và email */}
                  <div className="flex-1 min-w-0">
                    <p
                      className={cn(
                        "font-bold text-sm truncate",
                        isActive ? "text-white" : "text-[#8C4905]"
                      )}
                    >
                      {getDisplayName(student)}
                    </p>
                    <p
                      className={cn(
                        "text-xs truncate",
                        isActive ? "text-white/70" : "text-[#C1762A]"
                      )}
                    >
                      {student.email}
                    </p>
                  </div>

                  {/* Nút xoá và sửa — chỉ hiện khi hover */}
                  <div className="opacity-0 group-hover:opacity-100 transition-all duration-150 flex items-center gap-1 shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEditNickname(student);
                      }}
                      className={cn(
                        "p-1.5 rounded-lg transition-all duration-150",
                        isActive
                          ? "hover:bg-white/20 text-white"
                          : "hover:bg-[#F1CCA6] text-[#C1762A]"
                      )}
                      title="Đổi biệt danh"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveStudent(student.student_id);
                      }}
                      disabled={removingId === student.student_id}
                      className={cn(
                        "p-1.5 rounded-lg transition-all duration-150",
                        isActive
                          ? "hover:bg-white/20 text-white"
                          : "hover:bg-red-100 text-red-400"
                      )}
                      title="Huỷ liên kết"
                    >
                      {removingId === student.student_id ? (
                        <svg
                          className="animate-spin h-3.5 w-3.5"
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
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </nav>

        {/* Nút Thêm con */}
        <div className="px-4 pb-3">
          <button
            id="add-student-sidebar-btn"
            onClick={() => setShowLinkModal(true)}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#C1762A] text-white font-bold text-sm hover:bg-[#8C4905] shadow-md transition-all transform hover:-translate-y-0.5 cursor-pointer"
          >
            <UserPlus size={16} />
            Thêm con
          </button>
        </div>

        {/* Settings Dropdown (Floating) */}
        {showSettings && (
          <div
            ref={settingsRef}
            className="absolute bottom-20 left-4 right-4 bg-white rounded-xl shadow-lg border border-[#F1CCA6] p-2 z-50 animate-in fade-in zoom-in-95 duration-200 flex flex-col gap-1"
          >
            <button
              onClick={() => {
                setShowSettings(false);
                router.push("/dashboard/monitor/settings");
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[#8C4905] hover:bg-[#F7ECE1] rounded-lg transition-colors font-medium cursor-pointer"
            >
              <Settings2 size={16} />
              Cài đặt
            </button>
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[#8C4905] hover:bg-[#F7ECE1] rounded-lg transition-colors font-medium cursor-pointer"
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
                className="w-8 h-8 rounded-full border border-[#C1762A] shrink-0"
              />
            ) : (
              <div className="w-8 h-8 bg-[#C1762A] rounded-full flex items-center justify-center text-white font-bold text-sm shrink-0">
                {session?.user?.name?.charAt(0) || "P"}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-[#8C4905] truncate">
                {session?.user?.name || "Phụ huynh"}
              </p>
              <p className="text-xs text-[#C1762A]">Người giám sát</p>
            </div>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-[#8C4905] hover:bg-[#F7AD62]/30 rounded-lg transition-colors cursor-pointer"
            title="Cài đặt"
          >
            <Settings size={20} />
          </button>
        </div>
      </aside>

      {/* Modal thêm con */}
      <LinkStudentModal
        isOpen={showLinkModal}
        onClose={() => setShowLinkModal(false)}
        onSuccess={handleLinkSuccess}
      />
    </>
  );
}
