"use client";

import React, { useState } from 'react';
import { signIn } from "next-auth/react";
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
  const [role, setRole] = useState<'student' | 'monitor'>('student');
  const [isLoading, setIsLoading] = useState(false);

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

    if (!email.trim()) {
      newErrors.email = "Email/SDT không được bỏ trống";
      hasError = true;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && email.includes("@")) {
      newErrors.email = "Vui lòng nhập đúng định dạng email";
      hasError = true;
    } else if (!email.includes("@")) {
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

        if (onClose) onClose();
        router.push("/dashboard");
        // Không gọi setIsLoading(false) để giữ vòng xoay loading mượt mà khi redirect
      } else {
        // Tích hợp API Đăng ký
        const endpoint = role === 'student' ? '/register/student' : '/register/monitor';
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${backendUrl}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Đã có lỗi xảy ra khi đăng ký");
        }

        // Đăng ký xong → chuyển sang tab đăng nhập
        setIsLoginMode(true);
        setEmail("");
        setPassword("");
        setConfirmPassword("");
        setErrors({ form: "✅ Đăng ký thành công! Vui lòng đăng nhập." });
        setIsLoading(false);
      }
    } catch (err: any) {
      setErrors({ form: err.message });
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      {/* Background form nhạt hơn F1CCA6 để lỗi dễ đọc hơn */}
      <div className="relative w-full max-w-md bg-[#F1CCA6] rounded-3xl overflow-hidden p-8 shadow-xl">

        {/* Close Button */}
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-[#8C4905] hover:text-[#CB6600] transition-colors"
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
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-[#000000] focus:outline-none focus:ring-2 ${errors.email ? 'border-2 border-[#CB6600] focus:ring-[#CB6600]' : 'focus:ring-[#F7AD62] border-transparent'
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
              className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-[#000000] focus:outline-none focus:ring-2 ${errors.password ? 'border-2 border-[#CB6600] focus:ring-[#CB6600]' : 'focus:ring-[#F7AD62] border-transparent'
                }`}
              disabled={isLoading}
            />
            {errors.password && (
              <p className="mt-1 text-sm text-[#CB6600] font-bold">{errors.password}</p>
            )}

            {/* Form Level Message (Error or Success) */}
            {errors.form && isLoginMode && (
              <p className={`mt-2 text-sm font-bold text-center ${errors.form.startsWith('✅') ? 'text-[#8C4905]' : 'text-[#CB6600]'
                }`}>{errors.form}</p>
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
                className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-[#000000] focus:outline-none focus:ring-2 ${errors.confirmPassword ? 'border-2 border-[#CB6600] focus:ring-[#CB6600]' : 'focus:ring-[#F7AD62] border-transparent'
                  }`}
                disabled={isLoading}
              />
              {errors.confirmPassword && (
                <p className="mt-1 text-sm text-[#CB6600] font-bold">{errors.confirmPassword}</p>
              )}

              {/* Form Level Error (e.g., Email exists) */}
              {errors.form && !isLoginMode && (
                <p className="mt-2 text-sm text-[#CB6600] font-bold text-center">{errors.form}</p>
              )}
            </div>
          )}

          {/* Role Selection (Only in Sign up) */}
          {!isLoginMode && (
            <div className="flex gap-4 pt-2">
              <button
                type="button"
                onClick={() => setRole('student')}
                className={`flex-1 py-2 rounded-xl font-bold transition-all ${role === 'student'
                    ? 'bg-[#8C4905] text-[#F7ECE1] shadow-md'
                    : 'bg-[#F7ECE1] text-[#8C4905] opacity-80 hover:opacity-100'
                  }`}
                disabled={isLoading}
              >
                Học sinh
              </button>
              <button
                type="button"
                onClick={() => setRole('monitor')}
                className={`flex-1 py-2 rounded-xl font-bold transition-all ${role === 'monitor'
                    ? 'bg-[#8C4905] text-[#F7ECE1] shadow-md'
                    : 'bg-[#F7ECE1] text-[#8C4905] opacity-80 hover:opacity-100'
                  }`}
                disabled={isLoading}
              >
                Người giám sát
              </button>
            </div>
          )}

          {/* Login Options */}
          {isLoginMode && (
            <div className="flex items-center justify-between mt-2 px-1">
              <label className="flex items-center text-xs font-bold text-[#8C4905] cursor-pointer">
                <input type="checkbox" className="mr-2 rounded text-[#8C4905] focus:ring-[#F7AD62]" disabled={isLoading} />
                Nhớ tôi
              </label>
              <a href="#" className="text-xs font-bold text-[#8C4905] hover:text-[#CB6600] transition-colors">
                Quên mật khẩu?
              </a>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-4 bg-[#000000] text-[#F7ECE1] font-bold py-3 rounded-xl hover:bg-gray-800 transition-colors flex items-center justify-center disabled:opacity-70 disabled:cursor-not-allowed shadow-md"
          >
            {isLoading ? (
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : isLoginMode ? "Đăng Nhập" : "Đăng Ký"}
          </button>
        </form>

        {/* Social Login & Toggle Mode */}
        {isLoginMode && (
          <div className="mt-6 text-center">
            <div className="flex justify-center mb-4">
              <button
                type="button"
                disabled={isLoading}
                onClick={() => signIn("google")}
                className="w-12 h-12 bg-[#F7ECE1] rounded-full flex items-center justify-center hover:bg-white transition-colors shadow-md disabled:opacity-70 disabled:cursor-not-allowed p-2"
              >
                <img src="/google-logo.svg" alt="Google Login" className="w-full h-full object-contain" />
              </button>
            </div>
          </div>
        )}

        <div className="mt-4 text-center">
          <p className="text-xs font-bold text-[#8C4905]">
            {isLoginMode ? "Không có tài khoản ? " : "Đã có tài khoản ? "}
            <button
              type="button"
              onClick={toggleMode}
              disabled={isLoading}
              className="text-[#CB6600] hover:underline focus:outline-none disabled:opacity-70 disabled:cursor-not-allowed ml-1"
            >
              {isLoginMode ? "Đăng ký" : "Đăng nhập"}
            </button>
          </p>
        </div>

      </div>
    </div>
  );
}
