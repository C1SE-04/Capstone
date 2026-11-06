"use client";

import React, { useState } from 'react';
import { signIn, getSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { migrateLocalStorageBadgesToDB } from "@/lib/badgeStorage";

interface AuthFormProps {
  onClose?: () => void;
}

export default function AuthForm({ onClose }: AuthFormProps = {}) {
  const router = useRouter();
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [identifier, setIdentifier] = useState("");     // Đăng nhập: Tên tài khoản hoặc Email
  const [username, setUsername] = useState("");         // Đăng ký: Tên tài khoản
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState(""); // Đăng ký: Xác nhận mật khẩu
  const [isLoading, setIsLoading] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);  // Trạng thái chuyển cảnh mượt mà chống nháy

  const [errors, setErrors] = useState<{
    identifier?: string;
    username?: string;
    password?: string;
    confirmPassword?: string;
    form?: string;
  }>({});

  const toggleMode = () => {
    setIsLoginMode((prev) => !prev);
    setErrors({});
    setIdentifier("");
    setUsername("");
    setPassword("");
    setConfirmPassword("");
  };

  const validateForm = () => {
    let hasError = false;
    const newErrors: typeof errors = {};

    if (isLoginMode) {
      const trimmedIdentifier = identifier.trim();
      if (!trimmedIdentifier) {
        newErrors.identifier = "Tên tài khoản hoặc Email không được bỏ trống";
        hasError = true;
      }

      if (!password) {
        newErrors.password = "Mật khẩu không được bỏ trống";
        hasError = true;
      }
    } else {
      // Validate đăng ký: Tên tài khoản (3-20 ký tự chữ, số, gạch dưới) + Mật khẩu (>= 6 ký tự) + Xác nhận mật khẩu
      const trimmedUsername = username.trim();
      if (!trimmedUsername) {
        newErrors.username = "Tên tài khoản không được bỏ trống";
        hasError = true;
      } else if (!/^[a-zA-Z0-9_]{3,20}$/.test(trimmedUsername)) {
        newErrors.username = "Tên tài khoản phải từ 3-20 ký tự, chỉ gồm chữ, số và dấu gạch dưới";
        hasError = true;
      }

      if (!password) {
        newErrors.password = "Mật khẩu không được bỏ trống";
        hasError = true;
      } else if (password.length < 6) {
        newErrors.password = "Mật khẩu phải có ít nhất 6 ký tự";
        hasError = true;
      }

      if (!confirmPassword) {
        newErrors.confirmPassword = "Vui lòng xác nhận lại mật khẩu";
        hasError = true;
      } else if (password !== confirmPassword) {
        newErrors.confirmPassword = "Mật khẩu xác nhận không khớp";
        hasError = true;
      }
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
        // Dùng NextAuth Credentials để tạo session với username hoặc email
        const result = await signIn("credentials", {
          redirect: false,
          email: identifier.trim(),
          password,
        });

        if (result?.error) {
          throw new Error("Tên tài khoản/Email hoặc mật khẩu không chính xác");
        }

        // Bật trạng thái chuyển cảnh mượt mà ngay lập tức
        setIsRedirecting(true);

        // Lấy session ngay để điều hướng đúng trang đích
        const currentSession = await getSession();
        const userRole = (currentSession?.user as any)?.role;
        const isNewUser = (currentSession as any)?.is_new_user || (currentSession?.user as any)?.is_new_user;

        const loggedUserId = (currentSession?.user as any)?.id || (currentSession?.user as any)?.email;
        if (loggedUserId) {
          // US 9.2 (T9.8b): Migrate badge cũ trong localStorage lên DB sau khi đăng nhập
          migrateLocalStorageBadgesToDB(loggedUserId).catch((err) => {
            console.warn("[AuthForm] Lỗi migrate badge sau đăng nhập:", err);
          });
        }

        let targetUrl = "/dashboard/chat";
        if (userRole === "PENDING" || isNewUser) {
          targetUrl = "/onboarding";
        } else if (userRole === "ADMIN") {
          targetUrl = "/admin";
        } else if (userRole === "MONITOR") {
          targetUrl = "/dashboard/monitor";
        }

        // Chuyển hướng trực tiếp không đóng modal trước để tránh nhấp nháy lộ trang chủ
        router.replace(targetUrl);

        // Fallback tự đóng modal sau 2.5s phòng hờ route change hoàn tất
        setTimeout(() => {
          if (onClose) onClose();
        }, 2500);

      } else {
        // US 9.1 (T9.3): Đăng ký tài khoản mới bằng username + password (role='PENDING')
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${backendUrl}/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: username.trim(),
            password,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const detail = errorData.detail || "Đã có lỗi xảy ra khi đăng ký";

          // AC 9.1.2: Báo lỗi trùng Username màu đỏ
          if (typeof detail === "string" && (detail.toLowerCase().includes("tồn tại") || detail.toLowerCase().includes("sử dụng"))) {
            setErrors({
              username: "Tên tài khoản đã được sử dụng, vui lòng chọn tên khác",
            });
            setIsLoading(false);
            return;
          }
          throw new Error(detail);
        }

        // Tự động đăng nhập vào NextAuth phiên làm việc
        const signInResult = await signIn("credentials", {
          redirect: false,
          email: username.trim(),
          password,
        });

        if (signInResult?.error) {
          setIsLoginMode(true);
          setIdentifier(username.trim());
          setPassword("");
          setConfirmPassword("");
          setErrors({ form: "✅ Đăng ký thành công! Vui lòng đăng nhập để tiếp tục." });
          setIsLoading(false);
          return;
        }

        // Chuyển cảnh mượt mà sang trang onboarding
        setIsRedirecting(true);
        router.replace("/onboarding");

        setTimeout(() => {
          if (onClose) onClose();
        }, 2500);
      }
    } catch (err) {
      setErrors({ form: err instanceof Error ? err.message : "Đã xảy ra lỗi không xác định" });
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 transition-all">
      <div className="relative w-full max-w-md bg-[#F1CCA6] rounded-3xl overflow-hidden p-8 shadow-2xl transition-all">
        {/* Close Button (ẩn khi đang chuyển trang để tránh ngắt quãng) */}
        {onClose && !isRedirecting && (
          <button
            type="button"
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-[#8C4905] hover:text-[#8C4905] transition-colors cursor-pointer"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}

        {/* Màn hình chuyển cảnh mượt mà (Smooth Redirecting View - Chống nhấp nháy web) */}
        {isRedirecting ? (
          <div className="py-10 flex flex-col items-center justify-center text-center animate-fade-in">
            <div className="w-20 h-20 rounded-full overflow-hidden flex items-center justify-center bg-[#F7ECE1] shadow-md border-2 border-[#C1762A]/40 mb-6 animate-pulse">
              <img src="/logo.png" alt="SocraticKid Logo" className="w-full h-full object-cover" />
            </div>
            <div className="flex items-center gap-2.5 mb-2 text-[#8C4905]">
              <svg className="w-5 h-5 animate-spin text-[#C1762A]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <h3 className="text-xl font-bold tracking-tight">
                {isLoginMode ? "Đăng nhập thành công!" : "Đăng ký thành công!"}
              </h3>
            </div>
            <p className="text-sm font-medium text-[#8C4905]/80">
              Đang chuẩn bị không gian học tập cho bạn...
            </p>
          </div>
        ) : (
          <>
            {/* Logo SocraticKid */}
            <div className="flex justify-center mb-6">
              <div className="w-20 h-20 rounded-full overflow-hidden flex items-center justify-center bg-[#F7ECE1] shadow-md border-2 border-[#C1762A]/30">
                <img src="/logo.png" alt="SocraticKid Logo" className="w-full h-full object-cover" />
              </div>
            </div>

            {/* Title */}
            <h2 className="text-4xl font-bold text-center text-[#8C4905] mb-8 italic tracking-wide">
              {isLoginMode ? "Welcome!" : "Sign up"}
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              {/* Ô nhập thông tin định danh */}
              {isLoginMode ? (
                /* Đăng nhập: Tên tài khoản hoặc Email */
                <div>
                  <label className="block text-[#8C4905] text-sm font-bold mb-1">
                    Tên tài khoản hoặc Email
                  </label>
                  <input
                    type="text"
                    value={identifier}
                    onChange={(e) => {
                      setIdentifier(e.target.value);
                      if (errors.identifier) setErrors((prev) => ({ ...prev, identifier: undefined }));
                    }}
                    placeholder="Nhập tên tài khoản hoặc email..."
                    className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.identifier
                        ? 'border-2 border-[#EF4444] focus:ring-[#EF4444]'
                        : 'focus:ring-[#F7AD62] border-transparent'
                      }`}
                    disabled={isLoading}
                  />
                  {errors.identifier && (
                    <p className="mt-1 text-sm text-[#EF4444] font-bold">{errors.identifier}</p>
                  )}
                </div>
              ) : (
                /* Đăng ký: Tên tài khoản */
                <div>
                  <label className="block text-[#8C4905] text-sm font-bold mb-1">
                    Tên tài khoản
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      if (errors.username) setErrors((prev) => ({ ...prev, username: undefined }));
                    }}
                    placeholder="VD: socratic_kid (3-20 ký tự, chữ, số, _)"
                    className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.username
                        ? 'border-2 border-[#EF4444] focus:ring-[#EF4444]'
                        : 'focus:ring-[#F7AD62] border-transparent'
                      }`}
                    disabled={isLoading}
                  />
                  {errors.username && (
                    <p className="mt-1 text-sm text-[#EF4444] font-bold">{errors.username}</p>
                  )}
                </div>
              )}

              {/* Mật khẩu */}
              <div>
                <label className="block text-[#8C4905] text-sm font-bold mb-1">Mật khẩu</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }));
                  }}
                  placeholder="Nhập mật khẩu..."
                  className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.password
                      ? 'border-2 border-[#EF4444] focus:ring-[#EF4444]'
                      : 'focus:ring-[#F7AD62] border-transparent'
                    }`}
                  disabled={isLoading}
                />
                {errors.password && (
                  <p className="mt-1 text-sm text-[#EF4444] font-bold">{errors.password}</p>
                )}
              </div>

              {/* Xác nhận mật khẩu (Chỉ hiển thị khi Đăng ký) */}
              {!isLoginMode && (
                <div>
                  <label className="block text-[#8C4905] text-sm font-bold mb-1">
                    Xác nhận mật khẩu
                  </label>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: undefined }));
                    }}
                    placeholder="Nhập lại mật khẩu..."
                    className={`w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 focus:outline-none focus:ring-2 ${errors.confirmPassword
                        ? 'border-2 border-[#EF4444] focus:ring-[#EF4444]'
                        : 'focus:ring-[#F7AD62] border-transparent'
                      }`}
                    disabled={isLoading}
                  />
                  {errors.confirmPassword && (
                    <p className="mt-1 text-sm text-[#EF4444] font-bold">{errors.confirmPassword}</p>
                  )}
                </div>
              )}

              {/* Login Options (Chỉ khi đăng nhập) */}
              {isLoginMode && (
                <div className="flex items-center justify-between mt-2 px-1">
                  <label className="flex items-center text-xs font-bold text-[#8C4905] cursor-pointer">
                    <input type="checkbox" className="mr-2 rounded text-[#8C4905] focus:ring-[#F7AD62] cursor-pointer" disabled={isLoading} />
                    Nhớ tôi
                  </label>
                  <a href="#" className="text-xs font-bold text-[#8C4905] hover:text-[#8C4905] transition-colors cursor-pointer">
                    Quên mật khẩu?
                  </a>
                </div>
              )}

              {/* Lỗi chung Form */}
              {errors.form && (
                <div className="mt-2 text-center">
                  <p className={`text-sm font-bold ${errors.form.startsWith('✅') ? 'text-[#8C4905]' : 'text-[#EF4444]'
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
                  className="text-[#C1762A] hover:text-[#8C4905] hover:underline focus:outline-none disabled:opacity-70 disabled:cursor-not-allowed ml-1 cursor-pointer"
                >
                  {isLoginMode ? "Đăng ký" : "Đăng nhập"}
                </button>
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
