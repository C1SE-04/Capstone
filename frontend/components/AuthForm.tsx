"use client";

import React, { useState } from 'react';
import { signIn, getSession } from "next-auth/react";
import { useRouter } from "next/navigation";

interface AuthFormProps {
  onClose?: () => void;
}

export default function AuthForm({ onClose }: AuthFormProps = {}) {
  const router = useRouter();
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");

  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    confirmPassword?: string;
    form?: string;
  }>({});

  const toggleMode = () => {
    setIsLoginMode((prev) => !prev);
    setErrors({});
    setEmail("");
    setPassword("");
    setConfirmPassword("");
  };

  const validateForm = () => {
    let hasError = false;
    const newErrors: typeof errors = {};

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      newErrors.email = "Email/SDT không được bỏ trống";
      hasError = true;
    } else if (!trimmedEmail.includes("@")) {
      newErrors.email = "Vui lòng nhập đúng định dạng email";
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/i.test(trimmedEmail)) {
      newErrors.email = "Vui lòng nhập đúng định dạng email";
      hasError = true;
    }

    if (!password) {
      newErrors.password = "Mật khẩu không được bỏ trống";
      hasError = true;
    }

    if (!isLoginMode && password !== confirmPassword) {
      newErrors.confirmPassword = "Mật khẩu xác nhận không khớp";
      hasError = true;
    }

    if (hasError) {
      setErrors(newErrors);
    }

    return !hasError;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      if (isLoginMode) {
        // Dùng NextAuth Credentials để tạo session
        const result = await signIn("credentials", {
          redirect: false,
          email,
          password,
        });

        if (result?.error) {
          throw new Error("Sai email hoặc mật khẩu");
        }

        setToastMessage("Đăng nhập thành công!");
        setShowSuccessToast(true);
        setTimeout(async () => {
          if (onClose) onClose();
          
          // Lấy session mới nhất để kiểm tra role
          const currentSession = await getSession();
          const userRole = (currentSession?.user as any)?.role;
          const isNewUser = (currentSession as any)?.is_new_user || (currentSession?.user as any)?.is_new_user;
          
          if (userRole === "PENDING" || isNewUser) {
            router.push("/onboarding");
          } else if (userRole === "ADMIN") {
            router.push("/admin");
          } else if (userRole === "MONITOR") {
            router.push("/dashboard/monitor");
          } else {
            router.push("/dashboard/chat");
          }
        }, 1200);
      } else {
        // Đăng ký mới đồng bộ với luồng Google OAuth:
        // 1. Gửi email & password sang backend POST /register (tạo user với role='PENDING')
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${backendUrl}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email.toLowerCase().trim(), password })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "Đã có lỗi xảy ra khi đăng ký");
        }

        setToastMessage("Đăng ký thành công! Đang chuyển đến bước thiết lập hồ sơ...");
        setShowSuccessToast(true);

        // 2. Tự động đăng nhập vào NextAuth phiên làm việc
        const signInResult = await signIn("credentials", {
          redirect: false,
          email: email.toLowerCase().trim(),
          password,
        });

        if (signInResult?.error) {
          // Fallback nếu vì lý do nào đó tự động đăng nhập lỗi: quay lại tab Đăng Nhập
          setIsLoginMode(true);
          setPassword("");
          setConfirmPassword("");
          setToastMessage("Đăng ký thành công! Vui lòng đăng nhập để tiếp tục.");
          setIsLoading(false);
          return;
        }

        // 3. Đóng modal và chuyển hướng sang trang Onboarding đồng bộ như Google Login
        setTimeout(() => {
          if (onClose) onClose();
          router.push("/onboarding");
        }, 1200);
      }
    } catch (err) {
      setErrors({ form: err instanceof Error ? err.message : "Đã xảy ra lỗi không xác định" });
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      {/* Success Toast */}
      {showSuccessToast && (
        <div className="fixed top-4 right-4 z-[60] bg-white border border-emerald-200/80 shadow-lg rounded-xl px-5 py-3.5 animate-fade-in-down flex items-center gap-3">
          <div className="bg-emerald-50 rounded-full p-1 text-emerald-600">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="text-stone-800 text-sm font-medium">{toastMessage}</p>
        </div>
      )}

      {/* Background form nhạt hơn F1CCA6 để lỗi dễ đọc hơn */}
      <div className="relative w-full max-w-md bg-[#F1CCA6] rounded-3xl overflow-hidden p-8 shadow-xl">

        {/* Close Button */}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-[#8C4905] hover:text-[#CB6600] transition-colors cursor-pointer"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Avatar Placeholder */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-[#D9D9D9] rounded-full flex items-center justify-center shadow-inner">
          </div>
        </div>

        {/* Title */}
        <h2 className="text-4xl font-bold text-center text-[#8C4905] mb-8 italic tracking-wide">
          {isLoginMode ? "Welcome!" : "Sign up"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* Email / Phone */}
          <div>
            <label className="block text-[#8C4905] text-sm font-bold mb-1">Email/SDT</label>
            <input
              type="text"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.email ? 'border-2 border-[#CB6600] focus:ring-[#CB6600]' : 'focus:ring-[#F7AD62] border-transparent'
                }`}
              disabled={isLoading}
            />
            {errors.email && (
              <p className="mt-1 text-sm text-[#CB6600] font-bold">{errors.email}</p>
            )}
          </div>

          {/* Password */}
          <div>
            <label className="block text-[#8C4905] text-sm font-bold mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.password ? 'border-2 border-[#CB6600] focus:ring-[#CB6600]' : 'focus:ring-[#F7AD62] border-transparent'
                }`}
              disabled={isLoading}
            />
            {errors.password && (
              <p className="mt-1 text-sm text-[#CB6600] font-bold">{errors.password}</p>
            )}
          </div>

          {/* Confirm Password (Only in Sign up) */}
          {!isLoginMode && (
            <div>
              <label className="block text-[#8C4905] text-sm font-bold mb-1">Xác Nhận Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.confirmPassword ? 'border-2 border-[#CB6600] focus:ring-[#CB6600]' : 'focus:ring-[#F7AD62] border-transparent'
                  }`}
                disabled={isLoading}
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-[#CB6600] font-bold">{errors.confirmPassword}</p>
              )}
            </div>
          )}



          {/* Login Options */}
          {isLoginMode && (
            <div className="flex items-center justify-between mt-2 px-1">
              <label className="flex items-center text-xs font-bold text-[#8C4905] cursor-pointer">
                <input type="checkbox" className="mr-2 rounded text-[#8C4905] focus:ring-[#F7AD62] cursor-pointer" disabled={isLoading} />
                Nhớ tôi
              </label>
              <a href="#" className="text-xs font-bold text-[#8C4905] hover:text-[#CB6600] transition-colors cursor-pointer">
                Quên mật khẩu?
              </a>
            </div>
          )}

          {/* Form Level Message (Error or Success) */}
          {errors.form && (
            <div className="mt-2 text-center">
              <p className={`text-sm font-bold ${errors.form.startsWith('✅') ? 'text-[#8C4905]' : 'text-[#CB6600]'
                }`}>
                {errors.form}
              </p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-4 bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white font-bold py-3.5 rounded-xl hover:brightness-105 active:scale-[0.98] transition-all flex items-center justify-center disabled:opacity-70 disabled:cursor-not-allowed shadow-md cursor-pointer"
          >
            {isLoading ? (
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : isLoginMode ? "Đăng Nhập" : "Đăng Ký"}
          </button>
        </form>

        {/* Social Login (Google OAuth US 8.3) */}
        <div className="relative my-4">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#8C4905]/20" />
          </div>
          <div className="relative flex justify-center text-xs">
            <span className="bg-[#F1CCA6] px-3 font-bold text-[#8C4905]">
              Hoặc tiếp tục với
            </span>
          </div>
        </div>

        <button
          type="button"
          disabled={isLoading}
          onClick={() => signIn("google", { callbackUrl: "/onboarding" })}
          className="w-full flex items-center justify-center gap-3 py-3 bg-white text-[#8C4905] rounded-xl font-bold text-sm shadow-xs hover:shadow transition-all border border-[#F1CCA6] cursor-pointer hover:bg-[#F7ECE1]/60 disabled:opacity-70 disabled:cursor-not-allowed"
        >
          <img src="/google-logo.svg" alt="Google Login" className="w-5 h-5 object-contain" />
          <span>Đăng nhập bằng Google</span>
        </button>

        <div className="mt-4 text-center">
          <p className="text-xs font-bold text-[#8C4905]">
            {isLoginMode ? "Không có tài khoản ? " : "Đã có tài khoản ? "}
            <button
              type="button"
              onClick={toggleMode}
              disabled={isLoading}
              className="text-[#CB6600] hover:underline focus:outline-none disabled:opacity-70 disabled:cursor-not-allowed ml-1 cursor-pointer"
            >
              {isLoginMode ? "Đăng ký" : "Đăng nhập"}
            </button>
          </p>
        </div>

      </div>
    </div>
  );
}
