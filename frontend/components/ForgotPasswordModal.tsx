"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  X,
  KeyRound,
  Mail,
  User,
  Users,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  Lock,
} from "lucide-react";

export type ForgotPasswordRole = "parent" | "student";

interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialRole?: ForgotPasswordRole;
  onSwitchToLogin?: () => void;
}

export default function ForgotPasswordModal({
  isOpen,
  onClose,
  initialRole = "parent",
  onSwitchToLogin,
}: ForgotPasswordModalProps) {
  const [activeTab, setActiveTab] = useState<ForgotPasswordRole>(initialRole);
  const modalRef = useRef<HTMLDivElement>(null);

  // Đồng bộ role khi mở lại modal
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialRole);
    }
  }, [isOpen, initialRole]);

  // Xử lý đóng modal bằng phím ESC và khóa scroll body
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* 1. Backdrop mờ nền & Click outside để đóng (AC-PW-01) */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/55 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
        aria-hidden="true"
      />

      {/* 2. Modal Dialog Container tông màu ấm SocraticKid (#F1CCA6, #8C4905, #F7ECE1) */}
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="forgot-password-title"
        className="relative w-full max-w-lg bg-[#FFFDF9] rounded-3xl shadow-2xl border-2 border-[#F1CCA6] p-6 sm:p-8 animate-in zoom-in-95 duration-200 overflow-hidden z-10 space-y-6"
      >
        {/* Nút đóng góc phải (X) */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 text-[#C1762A] hover:text-[#8C4905] hover:bg-[#F7ECE1] rounded-full transition-colors cursor-pointer"
          aria-label="Đóng hộp thoại"
        >
          <X className="w-5 h-5" />
        </button>

        {/* ── Header Modal ── */}
        <div className="text-center space-y-2 pt-1">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#F1CCA6] to-[#F7ECE1] text-[#8C4905] shadow-inner mb-1">
            <KeyRound className="w-7 h-7 text-[#C1762A]" />
          </div>
          <h2
            id="forgot-password-title"
            className="text-2xl font-black text-[#8C4905] tracking-tight"
          >
            Khôi Phục Mật Khẩu
          </h2>
          <p className="text-xs text-[#78716C] max-w-xs mx-auto leading-relaxed">
            Đừng lo lắng! Hãy chọn đúng vai trò của bạn để nhận hướng dẫn lấy lại mật khẩu nhanh nhất.
          </p>
        </div>

        {/* ── 2 Tab Phân Vai Trò Rõ Ràng (T11.1.6 & AC-PW-01) ── */}
        <div className="grid grid-cols-2 gap-2 p-1.5 bg-[#F7ECE1]/70 rounded-2xl border border-[#F1CCA6]/60">
          <button
            type="button"
            onClick={() => setActiveTab("parent")}
            className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === "parent"
                ? "bg-[#C1762A] text-white shadow-md shadow-[#C1762A]/20 scale-[1.01]"
                : "text-[#8C4905] hover:bg-[#F7ECE1] hover:text-[#8C4905]"
            }`}
          >
            <Users className="w-4 h-4 shrink-0" />
            <span>👨‍👩‍👧 Phụ huynh</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("student")}
            className={`flex items-center justify-center gap-2 py-3 px-3 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
              activeTab === "student"
                ? "bg-[#C1762A] text-white shadow-md shadow-[#C1762A]/20 scale-[1.01]"
                : "text-[#8C4905] hover:bg-[#F7ECE1] hover:text-[#8C4905]"
            }`}
          >
            <User className="w-4 h-4 shrink-0" />
            <span>👦 Học sinh</span>
          </button>
        </div>

        {/* ── Khung Nội Dung Theo Vai Trò (Shell UI) ── */}
        <div className="space-y-4 min-h-[220px]">
          {activeTab === "parent" ? (
            /* Luồng Phụ huynh (Chuẩn bị cho T11.1.7) */
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/70 text-xs text-amber-900 flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-[#C1762A] shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  Phụ huynh xác thực bằng <strong>Email đã đăng ký</strong>. Hệ thống sẽ gửi mã OTP gồm 6 chữ số qua hòm thư để cấp lại mật khẩu mới.
                </p>
              </div>

              {/* Form placeholder mô phỏng (sẽ kết nối sâu ở T11.1.7) */}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-[#8C4905] mb-1.5">
                    Địa chỉ Email Phụ huynh:
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-[#C1762A] absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="email"
                      placeholder="vidu@gmail.com"
                      className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#F1CCA6] rounded-xl text-xs text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
                      readOnly
                    />
                  </div>
                </div>

                <button
                  type="button"
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer"
                >
                  <span>Gửi mã xác nhận OTP</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            /* Luồng Học sinh (Chuẩn bị cho T11.1.8) */
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/70 text-xs text-blue-900 flex items-start gap-2.5">
                <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  Vì học sinh tiểu học & THCS chỉ sử dụng <strong>Tên tài khoản (Username)</strong> để học, hệ thống sẽ giúp em tra cứu và gửi lời nhắn nhờ Bố/Mẹ hỗ trợ đổi mật khẩu.
                </p>
              </div>

              {/* Form placeholder mô phỏng (sẽ kết nối sâu ở T11.1.8) */}
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-bold text-[#8C4905] mb-1.5">
                    Tên tài khoản (Username) của em:
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-[#C1762A] absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Nhập tên đăng nhập của em (VD: nguyenvanan)"
                      className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#F1CCA6] rounded-xl text-xs text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
                      readOnly
                    />
                  </div>
                </div>

                <button
                  type="button"
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer"
                >
                  <span>Tra cứu tài khoản bảo trợ</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer Modal ── */}
        <div className="pt-3 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs text-[#78716C]">
          <button
            type="button"
            onClick={() => {
              onClose();
              if (onSwitchToLogin) onSwitchToLogin();
            }}
            className="flex items-center gap-1 font-bold text-[#8C4905] hover:text-[#C1762A] transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Quay lại đăng nhập</span>
          </button>

          <span className="text-[11px] text-[#A8A29E]">
            Hỗ trợ: support@socratickid.edu.vn
          </span>
        </div>
      </div>
    </div>
  );
}

