"use client";

/**
 * File: frontend/components/monitor/ResetStudentPasswordModal.tsx
 * Mô tả: Modal dành riêng cho Phụ huynh (MONITOR) cấp lại mật khẩu cho con trực tiếp từ Dashboard.
 * Đáp ứng AC-PW-06 & AC-PW-07 thuộc User Story 11.1 (Task #372 / T11.1.9):
 * - Phụ huynh nhập mật khẩu mới cho học sinh đã liên kết.
 * - Gọi API POST /family/students/{student_id}/reset-password (hoặc /parent/students/...).
 * - Kiểm tra quyền giám hộ chặt chẽ, cập nhật mật khẩu ngay lập tức và tăng session_version.
 */

import React, { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import {
  X,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Lock,
} from "lucide-react";

export interface StudentToReset {
  student_id: string;
  email: string;
  nickname?: string | null;
}

interface ResetStudentPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  student: StudentToReset | null;
  onSuccess?: (studentName: string) => void;
}

export default function ResetStudentPasswordModal({
  isOpen,
  onClose,
  student,
  onSuccess,
}: ResetStudentPasswordModalProps) {
  const { data: session } = useSession();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  // Reset form khi modal mở ra
  useEffect(() => {
    if (isOpen) {
      setNewPassword("");
      setConfirmPassword("");
      setShowPassword(false);
      setShowConfirmPassword(false);
      setIsLoading(false);
      setErrorMsg(null);
      setIsSuccess(false);
      setSuccessMessage("");
    }
  }, [isOpen, student?.student_id]);

  // Đóng modal bằng phím Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isLoading, onClose]);

  if (!isOpen || !student) return null;

  const displayName = student.nickname || student.email.split("@")[0];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    const cleanPass = newPassword.trim();
    const cleanConfirm = confirmPassword.trim();

    if (!cleanPass) {
      setErrorMsg("Vui lòng nhập mật khẩu mới cho con.");
      return;
    }

    if (cleanPass.length < 6) {
      setErrorMsg("Mật khẩu mới phải có ít nhất 6 ký tự.");
      return;
    }

    if (cleanPass !== cleanConfirm) {
      setErrorMsg("Mật khẩu xác nhận không khớp. Vui lòng nhập lại.");
      return;
    }

    setIsLoading(true);

    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      const res = await fetch(
        `${backendUrl}/family/students/${student.student_id}/reset-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session?.access_token}`,
          },
          body: JSON.stringify({
            new_password: cleanPass,
          }),
        }
      );

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.success) {
        setIsSuccess(true);
        setSuccessMessage(
          data.message ||
            `Đã cấp lại mật khẩu cho ${displayName} thành công! Con có thể đăng nhập bằng mật khẩu mới ngay bây giờ.`
        );
        if (onSuccess) {
          onSuccess(displayName);
        }
      } else {
        setErrorMsg(
          data.detail ||
            "Không thể cập nhật mật khẩu. Vui lòng kiểm tra quyền giám hộ hoặc thử lại sau."
        );
      }
    } catch {
      setErrorMsg("Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isLoading) {
          onClose();
        }
      }}
    >
      <div className="relative w-full max-w-md bg-white rounded-3xl p-6 sm:p-7 border border-[#F1CCA6] shadow-2xl animate-in zoom-in-95 duration-200 text-stone-900">
        {/* Nút đóng */}
        <button
          type="button"
          onClick={onClose}
          disabled={isLoading}
          aria-label="Đóng"
          className="absolute top-4 right-4 p-2 text-[#78716C] hover:text-[#8C4905] hover:bg-[#F7ECE1] rounded-full transition-colors cursor-pointer disabled:opacity-50"
        >
          <X className="w-5 h-5" />
        </button>

        {isSuccess ? (
          /* Màn hình thành công (AC-PW-06) */
          <div className="text-center py-4 space-y-4 animate-in zoom-in-95 duration-300">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 shadow-sm">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-black text-emerald-950">
                Cấp Lại Mật Khẩu Thành Công! 🎉
              </h3>
              <p className="text-xs text-zinc-600 leading-relaxed max-w-xs mx-auto">
                {successMessage}
              </p>
              <div className="p-3 bg-[#F7ECE1]/60 rounded-xl border border-[#F1CCA6] text-[11px] text-[#8C4905] leading-relaxed">
                💡 <em>Lưu ý an toàn:</em> Tất cả các phiên đăng nhập cũ trên thiết bị của con đã được tự động đăng xuất để đảm bảo an toàn.
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="w-full py-3 px-4 bg-[#C1762A] hover:bg-[#8C4905] text-white font-extrabold text-xs rounded-xl shadow-md transition-all cursor-pointer active:scale-98"
            >
              Hoàn tất & Đóng
            </button>
          </div>
        ) : (
          /* Form cấp lại mật khẩu */
          <>
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-2xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-2xs">
                <KeyRound className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-[#8C4905] tracking-tight">
                  Cấp Lại Mật Khẩu Cho Con
                </h3>
                <p className="text-[11px] text-[#C1762A] font-medium">
                  Cập nhật mật khẩu mới nhanh chóng và an toàn
                </p>
              </div>
            </div>

            {/* Thẻ học sinh được chọn */}
            <div className="mb-5 p-3 rounded-2xl bg-[#F7ECE1]/70 border border-[#F1CCA6] flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#C1762A] text-white flex items-center justify-center font-black text-sm shadow-xs shrink-0">
                {displayName.charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-extrabold text-xs text-[#8C4905] truncate">
                  {displayName}
                </p>
                <p className="text-[11px] text-[#78716C] truncate font-mono">
                  {student.email}
                </p>
              </div>
            </div>

            {/* Error Banner */}
            {errorMsg && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 flex items-start gap-2.5 text-red-700 text-xs animate-in fade-in duration-200">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="font-medium leading-relaxed">{errorMsg}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Mật khẩu mới */}
              <div>
                <label className="block text-xs font-bold text-[#8C4905] mb-1.5">
                  Mật khẩu mới cho con
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-zinc-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => {
                      setNewPassword(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="Nhập ít nhất 6 ký tự..."
                    disabled={isLoading}
                    autoComplete="new-password"
                    className="w-full pl-9 pr-10 py-2.5 bg-[#F7ECE1]/50 border border-[#F1CCA6] rounded-xl text-xs font-medium text-stone-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#C1762A] transition-all disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-400 hover:text-[#8C4905] cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Xác nhận mật khẩu mới */}
              <div>
                <label className="block text-xs font-bold text-[#8C4905] mb-1.5">
                  Xác nhận lại mật khẩu mới
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-zinc-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errorMsg) setErrorMsg(null);
                    }}
                    placeholder="Nhập lại mật khẩu..."
                    disabled={isLoading}
                    autoComplete="new-password"
                    className="w-full pl-9 pr-10 py-2.5 bg-[#F7ECE1]/50 border border-[#F1CCA6] rounded-xl text-xs font-medium text-stone-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-[#C1762A] transition-all disabled:opacity-50"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-400 hover:text-[#8C4905] cursor-pointer"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Buttons */}
              <div className="pt-2 flex items-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className="flex-1 py-2.5 px-4 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 font-bold text-xs rounded-xl transition-all cursor-pointer disabled:opacity-50"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="flex-1 py-2.5 px-4 bg-[#C1762A] hover:bg-[#8C4905] text-white font-extrabold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2 active:scale-98"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang cập nhật...</span>
                    </>
                  ) : (
                    <span>Xác nhận cấp lại</span>
                  )}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

