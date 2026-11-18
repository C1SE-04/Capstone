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
  Eye,
  EyeOff,
  Loader2,
  RefreshCw,
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

  // ── State Luồng Phụ huynh (Task #370 / T11.1.7) ──
  // parentStep: 1 = Nhập Email, 2 = Nhập 6 OTP, 3 = Nhập Mật khẩu mới, 4 = Thành công (AC-PW-04)
  const [parentStep, setParentStep] = useState<1 | 2 | 3 | 4>(1);
  const [parentEmail, setParentEmail] = useState<string>("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [newPassword, setNewPassword] = useState<string>("");
  const [confirmPassword, setConfirmPassword] = useState<string>("");
  const [showNewPassword, setShowNewPassword] = useState<boolean>(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isGoogleAccount, setIsGoogleAccount] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<number>(0);

  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Reset state mỗi khi mở modal
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialRole);
      setParentStep(1);
      setParentEmail("");
      setOtpDigits(["", "", "", "", "", ""]);
      setNewPassword("");
      setConfirmPassword("");
      setShowNewPassword(false);
      setShowConfirmPassword(false);
      setIsLoading(false);
      setErrorMessage(null);
      setIsGoogleAccount(false);
      setCountdown(0);
    }
  }, [isOpen, initialRole]);

  // Bộ đếm ngược 60s cho nút gửi lại mã OTP
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

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

  // Lấy URL Backend từ biến môi trường
  const getBackendUrl = () => {
    return (
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://127.0.0.1:8000"
    );
  };

  // ==============================================================================
  // LUỒNG PHỤ HUYNH: BƯỚC 1 - GỬI MÃ OTP QUA EMAIL (AC-PW-02 & AC-PW-03)
  // ==============================================================================
  const handleRequestOtp = async (isResend: boolean = false) => {
    const emailToUse = parentEmail.trim().toLowerCase();
    if (!emailToUse) {
      setErrorMessage("Vui lòng nhập địa chỉ Email phụ huynh của bạn.");
      return;
    }

    // Validate email đơn giản
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailToUse)) {
      setErrorMessage("Địa chỉ Email không đúng định dạng. Vui lòng kiểm tra lại.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setIsGoogleAccount(false);

    try {
      const res = await fetch(`${getBackendUrl()}/auth/forgot-password/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailToUse }),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok) {
        // AC-PW-02: Gửi OTP thành công -> Chuyển sang Bước 2 và bật đếm ngược 60s
        setParentStep(2);
        setCountdown(data.rate_limit_seconds || 60);
        // Focus vào ô OTP đầu tiên sau khi chuyển bước
        setTimeout(() => {
          otpInputRefs.current[0]?.focus();
        }, 150);
      } else {
        const detailMsg = data.detail || "Không thể gửi mã OTP. Vui lòng thử lại.";

        // AC-PW-03: Nhắc nhở tài khoản Google Auth
        if (
          typeof detailMsg === "string" &&
          (detailMsg.toLowerCase().includes("google") || detailMsg.toLowerCase().includes("oauth"))
        ) {
          setIsGoogleAccount(true);
          setErrorMessage(
            "Tài khoản này dùng đăng nhập Google, vui lòng bấm nút 'Đăng nhập bằng Google' ngoài màn hình chính."
          );
        } else {
          setErrorMessage(detailMsg);
        }
      }
    } catch {
      setErrorMessage("Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.");
    } finally {
      setIsLoading(false);
    }
  };

  // ==============================================================================
  // LUỒNG PHỤ HUYNH: BƯỚC 2 - NHẬP 6 Ô OTP TỰ NHẢY CON TRỎ
  // ==============================================================================
  const handleOtpDigitChange = (index: number, value: string) => {
    // Chỉ nhận ký tự số
    const cleaned = value.replace(/\D/g, "");

    // Hỗ trợ paste chuỗi nhiều số
    if (cleaned.length > 1) {
      const pasteDigits = cleaned.slice(0, 6).split("");
      const nextDigits = [...otpDigits];
      pasteDigits.forEach((digit, i) => {
        if (index + i < 6) {
          nextDigits[index + i] = digit;
        }
      });
      setOtpDigits(nextDigits);
      setErrorMessage(null);

      const nextFocusIndex = Math.min(index + pasteDigits.length, 5);
      otpInputRefs.current[nextFocusIndex]?.focus();
      return;
    }

    const nextDigits = [...otpDigits];
    nextDigits[index] = cleaned;
    setOtpDigits(nextDigits);
    setErrorMessage(null);

    // Tự động nhảy sang ô tiếp theo khi nhập
    if (cleaned && index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    // Phím Backspace: Nếu ô hiện tại rỗng -> lùi về ô trước
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
  };

  const handleGoToPasswordStep = () => {
    const fullOtp = otpDigits.join("");
    if (fullOtp.length !== 6 || fullOtp.includes("")) {
      setErrorMessage("Vui lòng nhập đủ 6 chữ số mã OTP xác nhận.");
      return;
    }
    setErrorMessage(null);
    setParentStep(3);
  };

  // ==============================================================================
  // LUỒNG PHỤ HUYNH: BƯỚC 3 - XÁC THỰC OTP & ĐẶT LẠI MẬT KHẨU MỚI (AC-PW-04)
  // ==============================================================================
  const handleVerifyAndResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();

    const fullOtp = otpDigits.join("");
    if (fullOtp.length !== 6) {
      setErrorMessage("Mã OTP chưa đủ 6 chữ số. Vui lòng kiểm tra lại.");
      setParentStep(2);
      return;
    }

    if (newPassword.length < 6) {
      setErrorMessage("Mật khẩu mới phải có tối thiểu 6 ký tự.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("Mật khẩu xác nhận không khớp với mật khẩu mới.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await fetch(`${getBackendUrl()}/auth/forgot-password/verify-and-reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: parentEmail.trim().toLowerCase(),
          otp_code: fullOtp,
          new_password: newPassword,
        }),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.success) {
        // AC-PW-04: Đặt lại mật khẩu thành công -> Chuyển sang màn hình chúc mừng
        setParentStep(4);
      } else {
        const detailMsg = data.detail || "Không thể đặt lại mật khẩu. Vui lòng kiểm tra lại mã OTP.";
        setErrorMessage(detailMsg);

        // Nếu lỗi do OTP sai -> quay lại bước 2 để phụ huynh gõ lại mã
        if (
          typeof detailMsg === "string" &&
          (detailMsg.toLowerCase().includes("otp") || detailMsg.toLowerCase().includes("hết hiệu lực"))
        ) {
          setParentStep(2);
        }
      }
    } catch {
      setErrorMessage("Không thể kết nối đến máy chủ. Vui lòng thử lại sau ít phút.");
    } finally {
      setIsLoading(false);
    }
  };

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
        {parentStep !== 4 && (
          <div className="grid grid-cols-2 gap-2 p-1.5 bg-[#F7ECE1]/70 rounded-2xl border border-[#F1CCA6]/60">
            <button
              type="button"
              onClick={() => {
                setActiveTab("parent");
                setErrorMessage(null);
                setIsGoogleAccount(false);
              }}
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
              onClick={() => {
                setActiveTab("student");
                setErrorMessage(null);
                setIsGoogleAccount(false);
              }}
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
        )}

        {/* ── Khung Nội Dung Theo Vai Trò (Task #370 & Task #371) ── */}
        <div className="space-y-4 min-h-[220px]">
          {activeTab === "parent" ? (
            /* ==============================================================================
               LUỒNG PHỤ HUYNH: 4 BƯỚC (Task #370 / T11.1.7)
            ============================================================================== */
            <div className="space-y-4">
              {/* Thanh hiển thị tiến trình (Step Indicator) cho Phụ huynh */}
              {parentStep !== 4 && (
                <div className="flex items-center justify-between px-2 pt-1">
                  <div className="flex items-center gap-1.5 text-xs font-bold">
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                        parentStep === 1
                          ? "bg-[#C1762A] text-white"
                          : "bg-emerald-600 text-white"
                      }`}
                    >
                      {parentStep > 1 ? "✓" : "1"}
                    </span>
                    <span className={parentStep === 1 ? "text-[#8C4905]" : "text-[#78716C]"}>
                      Nhập Email
                    </span>
                  </div>

                  <div className="w-8 h-0.5 bg-[#F1CCA6]" />

                  <div className="flex items-center gap-1.5 text-xs font-bold">
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                        parentStep === 2
                          ? "bg-[#C1762A] text-white"
                          : parentStep > 2
                          ? "bg-emerald-600 text-white"
                          : "bg-[#E7E5E4] text-[#78716C]"
                      }`}
                    >
                      {parentStep > 2 ? "✓" : "2"}
                    </span>
                    <span className={parentStep === 2 ? "text-[#8C4905]" : "text-[#78716C]"}>
                      Xác thực OTP
                    </span>
                  </div>

                  <div className="w-8 h-0.5 bg-[#F1CCA6]" />

                  <div className="flex items-center gap-1.5 text-xs font-bold">
                    <span
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                        parentStep === 3
                          ? "bg-[#C1762A] text-white"
                          : "bg-[#E7E5E4] text-[#78716C]"
                      }`}
                    >
                      3
                    </span>
                    <span className={parentStep === 3 ? "text-[#8C4905]" : "text-[#78716C]"}>
                      Mật khẩu mới
                    </span>
                  </div>
                </div>
              )}

              {/* Thông báo lỗi / cảnh báo */}
              {errorMessage && (
                <div
                  className={`p-3.5 rounded-2xl border text-xs flex items-start gap-2.5 animate-in fade-in duration-200 ${
                    isGoogleAccount
                      ? "bg-amber-50 border-amber-300 text-amber-900"
                      : "bg-rose-50 border-rose-200 text-rose-800"
                  }`}
                >
                  <AlertCircle
                    className={`w-4 h-4 shrink-0 mt-0.5 ${
                      isGoogleAccount ? "text-amber-600" : "text-rose-600"
                    }`}
                  />
                  <div className="flex-1 space-y-1">
                    <p className="font-semibold leading-relaxed">{errorMessage}</p>
                    {isGoogleAccount && (
                      <p className="text-[11px] text-amber-800 font-medium">
                        👉 Vui lòng đóng hộp thoại này và chọn <strong>"Đăng nhập bằng Google"</strong>.
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* ── BƯỚC 1: Nhập Email Phụ Huynh (AC-PW-02) ── */}
              {parentStep === 1 && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/70 text-xs text-amber-900 flex items-start gap-2.5">
                    <ShieldCheck className="w-4 h-4 text-[#C1762A] shrink-0 mt-0.5" />
                    <p className="leading-relaxed">
                      Nhập địa chỉ Email bạn đã đăng ký tài khoản Phụ huynh. Hệ thống sẽ gửi mã OTP xác nhận gồm 6 chữ số qua hòm thư Brevo SMTP.
                    </p>
                  </div>

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
                          value={parentEmail}
                          onChange={(e) => {
                            setParentEmail(e.target.value);
                            if (errorMessage) setErrorMessage(null);
                            if (isGoogleAccount) setIsGoogleAccount(false);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleRequestOtp(false);
                            }
                          }}
                          className="w-full pl-10 pr-4 py-2.5 bg-white border border-[#F1CCA6] rounded-xl text-xs text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
                          disabled={isLoading}
                          autoFocus
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleRequestOtp(false)}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50 active:scale-98"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>Đang kiểm tra & gửi mã...</span>
                        </>
                      ) : (
                        <>
                          <span>Gửi mã xác nhận OTP</span>
                          <ArrowRight className="w-4 h-4" />
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* ── BƯỚC 2: Nhập 6 ô mã OTP tự động nhảy con trỏ ── */}
              {parentStep === 2 && (
                <div className="space-y-4 animate-in fade-in duration-200">
                  <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200/70 text-xs text-emerald-950 flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2">
                      <Mail className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                      <p className="leading-relaxed">
                        Mã OTP 6 số đã được gửi đến: <strong className="font-mono">{parentEmail}</strong>. Mã có hiệu lực trong 5 phút.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setParentStep(1);
                        setErrorMessage(null);
                      }}
                      className="text-[11px] font-bold text-[#8C4905] hover:underline shrink-0 cursor-pointer"
                    >
                      Đổi email
                    </button>
                  </div>

                  {/* 6 ô mã OTP */}
                  <div>
                    <label className="block text-xs font-bold text-[#8C4905] mb-2 text-center">
                      Nhập mã xác nhận 6 chữ số:
                    </label>
                    <div className="flex justify-center items-center gap-2 sm:gap-2.5">
                      {otpDigits.map((digit, index) => (
                        <input
                          key={index}
                          ref={(el) => {
                            otpInputRefs.current[index] = el;
                          }}
                          type="text"
                          inputMode="numeric"
                          maxLength={1}
                          value={digit}
                          onChange={(e) => handleOtpDigitChange(index, e.target.value)}
                          onKeyDown={(e) => handleOtpKeyDown(index, e)}
                          className="w-10 h-12 sm:w-11 sm:h-13 text-center text-lg font-black font-mono bg-white border-2 border-[#F1CCA6] rounded-xl text-[#8C4905] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-all shadow-xs"
                        />
                      ))}
                    </div>
                  </div>

                  {/* Nút đếm ngược gửi lại OTP */}
                  <div className="flex items-center justify-between text-xs pt-1 px-1">
                    <span className="text-[#78716C]">Không nhận được mã?</span>
                    {countdown > 0 ? (
                      <span className="font-semibold text-[#8C4905] flex items-center gap-1">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#C1762A]" />
                        Gửi lại mã sau ({countdown}s)
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleRequestOtp(true)}
                        disabled={isLoading}
                        className="font-bold text-[#C1762A] hover:text-[#8C4905] hover:underline cursor-pointer flex items-center gap-1"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Gửi lại mã OTP</span>
                      </button>
                    )}
                  </div>

                  {/* Nút tiếp tục sang Bước 3 */}
                  <button
                    type="button"
                    onClick={handleGoToPasswordStep}
                    disabled={otpDigits.join("").length !== 6}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50 active:scale-98"
                  >
                    <span>Tiếp tục đặt mật khẩu mới</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* ── BƯỚC 3: Nhập Mật khẩu mới & Xác nhận (AC-PW-04) ── */}
              {parentStep === 3 && (
                <form onSubmit={handleVerifyAndResetPassword} className="space-y-3 animate-in fade-in duration-200">
                  <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200/70 text-xs text-amber-900 flex items-center justify-between">
                    <span>
                      Mã xác nhận: <strong className="font-mono text-amber-950 font-bold">{otpDigits.join("")}</strong>
                    </span>
                    <button
                      type="button"
                      onClick={() => setParentStep(2)}
                      className="text-[11px] font-bold text-[#8C4905] hover:underline cursor-pointer"
                    >
                      Nhập lại OTP
                    </button>
                  </div>

                  {/* Ô nhập mật khẩu mới */}
                  <div>
                    <label className="block text-xs font-bold text-[#8C4905] mb-1">
                      Mật khẩu mới (tối thiểu 6 ký tự):
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-[#C1762A] absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type={showNewPassword ? "text" : "password"}
                        placeholder="Nhập mật khẩu mới an toàn"
                        value={newPassword}
                        onChange={(e) => {
                          setNewPassword(e.target.value);
                          if (errorMessage) setErrorMessage(null);
                        }}
                        className="w-full pl-10 pr-10 py-2.5 bg-white border border-[#F1CCA6] rounded-xl text-xs text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
                        disabled={isLoading}
                        autoFocus
                      />
                      <button
                        type="button"
                        onClick={() => setShowNewPassword((prev) => !prev)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[#78716C] hover:text-[#1C1917] cursor-pointer"
                        tabIndex={-1}
                      >
                        {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Ô xác nhận mật khẩu mới */}
                  <div>
                    <label className="block text-xs font-bold text-[#8C4905] mb-1">
                      Xác nhận lại mật khẩu mới:
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-[#C1762A] absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type={showConfirmPassword ? "text" : "password"}
                        placeholder="Nhập lại chính xác mật khẩu mới"
                        value={confirmPassword}
                        onChange={(e) => {
                          setConfirmPassword(e.target.value);
                          if (errorMessage) setErrorMessage(null);
                        }}
                        className="w-full pl-10 pr-10 py-2.5 bg-white border border-[#F1CCA6] rounded-xl text-xs text-[#1C1917] focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-[#78716C] hover:text-[#1C1917] cursor-pointer"
                        tabIndex={-1}
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Nút xác nhận đổi mật khẩu */}
                  <button
                    type="submit"
                    disabled={isLoading || !newPassword || !confirmPassword}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-50 active:scale-98 mt-2"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Đang cập nhật mật khẩu mới...</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Xác nhận đổi mật khẩu</span>
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* ── BƯỚC 4: THÀNH CÔNG (AC-PW-04) ── */}
              {parentStep === 4 && (
                <div className="text-center space-y-4 py-4 animate-in zoom-in-95 duration-300">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 shadow-sm">
                    <CheckCircle2 className="w-10 h-10" />
                  </div>
                  <div className="space-y-1.5">
                    <h3 className="text-lg font-black text-emerald-900">
                      Đặt Lại Mật Khẩu Thành Công!
                    </h3>
                    <p className="text-xs text-zinc-600 max-w-sm mx-auto leading-relaxed">
                      Mật khẩu tài khoản Phụ huynh của bạn đã được cập nhật thành công. Toàn bộ phiên đăng nhập trên các thiết bị cũ đã tự động đăng xuất để đảm bảo an toàn tuyệt đối.
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      if (onSwitchToLogin) onSwitchToLogin();
                    }}
                    className="inline-flex items-center justify-center gap-2 py-2.5 px-6 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-xs rounded-xl shadow-md transition-all cursor-pointer active:scale-98"
                  >
                    <span>Đăng nhập ngay bằng mật khẩu mới</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* ==============================================================================
               LUỒNG HỌC SINH (Chuẩn bị sẵn cho Task #371 / T11.1.8)
            ============================================================================== */
            <div className="space-y-4 animate-in fade-in duration-200">
              <div className="p-3.5 rounded-2xl bg-blue-50/70 border border-blue-200/70 text-xs text-blue-900 flex items-start gap-2.5">
                <HelpCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  Vì học sinh tiểu học & THCS chỉ sử dụng <strong>Tên tài khoản (Username)</strong> để học, hệ thống sẽ giúp em tra cứu và gửi lời nhắn nhờ Bố/Mẹ hỗ trợ đổi mật khẩu.
                </p>
              </div>

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
