"use client";

import React, { useState, useEffect, useRef } from "react";
import { Mail, KeyRound, Loader2, RefreshCw, X, AlertCircle, CheckCircle2 } from "lucide-react";

interface OtpModalProps {
  isOpen: boolean;
  email: string;
  title?: string;
  description?: React.ReactNode;
  onClose: () => void;
  onVerify: (otpCode: string) => Promise<{ success: boolean; error?: string }>;
  onResend: () => Promise<{ success: boolean; error?: string; rateLimitSeconds?: number }>;
  initialCountdown?: number;
}

export default function OtpModal({
  isOpen,
  email,
  title = "Xác thực mã OTP Phụ huynh",
  description,
  onClose,
  onVerify,
  onResend,
  initialCountdown = 60,
}: OtpModalProps) {
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [countdown, setCountdown] = useState<number>(initialCountdown);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isShaking, setIsShaking] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Reset state mỗi khi modal mở
  useEffect(() => {
    if (isOpen) {
      setDigits(["", "", "", "", "", ""]);
      setCountdown(initialCountdown);
      setErrorMessage(null);
      setIsShaking(false);
      setIsSuccess(false);

      // Focus ô đầu tiên
      const timer = setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen, initialCountdown]);

  // Bộ đếm ngược 60s
  useEffect(() => {
    if (!isOpen || countdown <= 0) return;

    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [isOpen, countdown]);

  if (!isOpen) return null;

  const triggerShake = () => {
    setIsShaking(true);
    setTimeout(() => setIsShaking(false), 500);
  };

  const handleDigitChange = (index: number, value: string) => {
    // Chỉ nhận ký tự số
    const cleaned = value.replace(/\D/g, "");
    if (!cleaned) {
      const nextDigits = [...digits];
      nextDigits[index] = "";
      setDigits(nextDigits);
      return;
    }

    const lastChar = cleaned.slice(-1);
    const nextDigits = [...digits];
    nextDigits[index] = lastChar;
    setDigits(nextDigits);
    setErrorMessage(null);

    // Tự động focus ô tiếp theo
    if (index < 5 && lastChar) {
      inputRefs.current[index + 1]?.focus();
    }

    // Nếu đã đủ 6 số, tự động trigger xác thực
    const fullOtp = nextDigits.join("");
    if (fullOtp.length === 6 && !nextDigits.includes("")) {
      handleAutoSubmit(fullOtp);
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (!digits[index] && index > 0) {
        // Nếu ô hiện tại trống, xóa và lùi về ô trước
        const nextDigits = [...digits];
        nextDigits[index - 1] = "";
        setDigits(nextDigits);
        inputRefs.current[index - 1]?.focus();
      } else {
        const nextDigits = [...digits];
        nextDigits[index] = "";
        setDigits(nextDigits);
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData("text").trim();
    const digitsOnly = pasteData.replace(/\D/g, "").slice(0, 6);
    if (!digitsOnly) return;

    const nextDigits = [...digits];
    for (let i = 0; i < 6; i++) {
      nextDigits[i] = digitsOnly[i] || "";
    }
    setDigits(nextDigits);
    setErrorMessage(null);

    if (digitsOnly.length === 6) {
      inputRefs.current[5]?.focus();
      handleAutoSubmit(digitsOnly);
    } else {
      const focusIndex = Math.min(digitsOnly.length, 5);
      inputRefs.current[focusIndex]?.focus();
    }
  };

  const handleAutoSubmit = async (code: string) => {
    if (code.length !== 6 || isVerifying) return;
    setIsVerifying(true);
    setErrorMessage(null);

    try {
      const result = await onVerify(code);
      if (result.success) {
        setIsSuccess(true);
      } else {
        triggerShake();
        setErrorMessage(result.error || "Mã xác thực không chính xác");
      }
    } catch (err: any) {
      triggerShake();
      setErrorMessage(err.message || "Mã xác thực không chính xác");
    } finally {
      setIsVerifying(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = digits.join("");
    if (code.length < 6) {
      triggerShake();
      setErrorMessage("Vui lòng nhập đủ 6 chữ số mã OTP");
      return;
    }
    await handleAutoSubmit(code);
  };

  const handleResend = async () => {
    if (countdown > 0 || isResending) return;
    setIsResending(true);
    setErrorMessage(null);

    try {
      const res = await onResend();
      if (res.success) {
        setCountdown(res.rateLimitSeconds || 60);
        setDigits(["", "", "", "", "", ""]);
        inputRefs.current[0]?.focus();
      } else {
        setErrorMessage(res.error || "Không thể gửi lại mã OTP. Vui lòng thử lại sau.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Lỗi khi gửi lại mã OTP.");
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in">
      <div
        className={`relative w-full max-w-md bg-white rounded-3xl border border-[#F1CCA6] p-6 sm:p-8 shadow-2xl transition-all ${
          isShaking ? "animate-shake" : "animate-modal-in"
        }`}
      >
        {/* Nút đóng */}
        <button
          type="button"
          onClick={onClose}
          disabled={isVerifying}
          className="absolute top-4 right-4 p-2 text-[#8C4905]/70 hover:text-[#8C4905] rounded-full hover:bg-[#F7ECE1] transition-colors cursor-pointer disabled:opacity-50"
          title="Đóng"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Icon & Tiêu đề */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-[#F7ECE1] border border-[#F1CCA6] flex items-center justify-center text-[#C1762A] shadow-xs mb-3">
            <KeyRound className="w-7 h-7" />
          </div>
          <h3 className="text-xl sm:text-2xl font-extrabold text-[#8C4905] tracking-tight">
            {title}
          </h3>
          <p className="text-xs sm:text-sm text-[#8C4905]/80 mt-1.5 leading-relaxed">
            {description || (
              <>
                Mã xác thực gồm 6 chữ số đã được gửi tới email
                <br />
                <strong className="text-[#C1762A] break-all">{email}</strong>
              </>
            )}
          </p>
        </div>

        {/* Thông báo thành công */}
        {isSuccess && (
          <div className="mb-5 p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-bold flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span>Xác thực thành công! Đang xử lý...</span>
          </div>
        )}

        {/* Thông báo lỗi */}
        {errorMessage && (
          <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-[#EF4444] text-xs font-bold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-[#EF4444]" />
            <span className="leading-snug">{errorMessage}</span>
          </div>
        )}

        {/* Form 6 ô rời (Digit Input UX) */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="flex justify-center items-center gap-2 sm:gap-3">
            {digits.map((digit, index) => (
              <input
                key={index}
                ref={(el) => {
                  inputRefs.current[index] = el;
                }}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                value={digit}
                onChange={(e) => handleDigitChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={handlePaste}
                disabled={isVerifying || isSuccess}
                className={`w-11 h-14 sm:w-12 sm:h-16 text-center text-2xl font-extrabold font-mono rounded-xl bg-[#F7ECE1]/60 border-2 transition-all outline-none ${
                  errorMessage
                    ? "border-[#EF4444] text-[#EF4444] focus:ring-2 focus:ring-[#EF4444]/30"
                    : digit
                    ? "border-[#C1762A] text-[#8C4905] bg-[#F7ECE1]"
                    : "border-[#F1CCA6] text-[#1C1917] focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20"
                }`}
              />
            ))}
          </div>

          {/* Đếm ngược & Nút Gửi lại mã */}
          <div className="flex items-center justify-between text-xs font-semibold pt-1">
            <span className="text-[#8C4905]/70">Không nhận được mã?</span>
            <button
              type="button"
              onClick={handleResend}
              disabled={countdown > 0 || isResending || isVerifying || isSuccess}
              className={`flex items-center gap-1.5 transition-colors ${
                countdown > 0
                  ? "text-[#8C4905]/50 cursor-not-allowed"
                  : "text-[#C1762A] hover:text-[#8C4905] hover:underline cursor-pointer font-bold"
              }`}
            >
              {isResending ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang gửi lại...</span>
                </>
              ) : countdown > 0 ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 opacity-50" />
                  <span>Gửi lại sau ({countdown}s)</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Gửi lại mã</span>
                </>
              )}
            </button>
          </div>

          {/* Nút Xác nhận */}
          <button
            type="submit"
            disabled={isVerifying || isSuccess || digits.join("").length < 6}
            className="w-full py-3.5 rounded-xl bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white font-bold text-sm sm:text-base shadow-md hover:brightness-105 active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isVerifying ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang kiểm tra mã...</span>
              </>
            ) : (
              <span>Xác nhận & Hoàn tất</span>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
