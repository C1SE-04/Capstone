"use client";

/**
 * File: app/dashboard/monitor/settings/page.tsx
 * Mô tả: Trang Cài đặt dành cho Phụ huynh (role=MONITOR).
 * US 9.1 (T9.5):
 * - Hiển thị thông tin tài khoản (Tên tài khoản, Email, Trạng thái xác thực, Vai trò).
 * - Form đổi email nhận thông báo: kích hoạt popup Modal OTP xác nhận trước khi lưu email mới vào hệ thống.
 * - Nếu đăng nhập bằng Google OAuth -> email nhận thông báo = email Google, cố định không cho sửa.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowLeft, Mail, Lock, CheckCircle2, AlertCircle, Loader2, ShieldCheck, Clock } from "lucide-react";
import OtpModal from "@/components/OtpModal";

interface UserProfile {
  id?: number;
  username?: string | null;
  email: string | null;
  oauth_provider: string | null;
  notification_email?: string | null;
  email_verified?: boolean;
  role: string;
}

export default function MonitorSettingsPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);

  // Email nhận thông báo — field có thể chỉnh sửa
  const [notifEmail, setNotifEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Modal OTP state
  const [isOtpModalOpen, setIsOtpModalOpen] = useState(false);
  const [pendingEmail, setPendingEmail] = useState("");

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  // Fetch thông tin người dùng khi có session
  useEffect(() => {
    if (!session?.access_token) return;

    const fetchProfile = async () => {
      setIsLoadingProfile(true);
      try {
        const res = await fetch(`${backendUrl}/users/me`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (!res.ok) throw new Error("Không thể tải thông tin tài khoản");
        const data: UserProfile = await res.json();
        setProfile(data);
        // Điền vào input: email tài khoản chính (gộp chung với email thông báo)
        const initialEmail = data.email || data.notification_email || "";
        setNotifEmail(initialEmail);
      } catch (err) {
        console.error(err);
        setErrorMsg("Không thể tải thông tin tài khoản. Vui lòng thử lại.");
      } finally {
        setIsLoadingProfile(false);
      }
    };

    fetchProfile();
  }, [session?.access_token, backendUrl]);

  const isGoogleOAuth = profile?.oauth_provider === "google";
  const currentSavedEmail = profile?.email || profile?.notification_email || "";

  // Bước 1: Bấm nút Lưu -> Gọi API request OTP và mở Modal OTP
  const handleInitiateChangeEmail = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    const targetEmail = notifEmail.trim();
    if (!targetEmail) {
      setErrorMsg("Địa chỉ email không được để trống.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(targetEmail)) {
      setErrorMsg("Địa chỉ email không hợp lệ. Vui lòng kiểm tra lại.");
      return;
    }

    if (targetEmail.toLowerCase() === currentSavedEmail.toLowerCase() && profile?.email_verified) {
      setErrorMsg("Email này đã được lưu và xác thực trước đó.");
      return;
    }

    setIsSubmitting(true);

    try {
      const res = await fetch(`${backendUrl}/parent/settings/request-email-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ new_email: targetEmail }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Không thể gửi mã xác thực tới email này.");
      }

      // Lưu email đang chờ xác thực và bật Modal OTP
      setPendingEmail(targetEmail);
      setIsOtpModalOpen(true);
    } catch (err: any) {
      setErrorMsg(err.message || "Đã xảy ra lỗi hệ thống khi yêu cầu mã OTP.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Bước 2: Xác thực mã OTP trong Modal
  const handleVerifyOtp = async (otpCode: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(`${backendUrl}/parent/settings/verify-email-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({
          new_email: pendingEmail,
          otp_code: otpCode.trim(),
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const detail = errData.detail || "Mã xác thực không chính xác";
        if (typeof detail === "string" && (detail.includes("hết hạn") || detail.includes("không hợp lệ"))) {
          return { success: false, error: "Mã OTP đã hết hạn, vui lòng bấm Gửi lại mã" };
        }
        return { success: false, error: detail };
      }

      // Thành công: cập nhật profile state trên giao diện
      setProfile((prev) =>
        prev
          ? {
              ...prev,
              email: pendingEmail,
              notification_email: pendingEmail,
              email_verified: true,
            }
          : prev
      );
      setNotifEmail(pendingEmail);
      setSuccessMsg(`✓ Đổi email nhận thông báo thành ${pendingEmail} thành công! Email đã được xác thực qua OTP.`);
      setTimeout(() => setIsOtpModalOpen(false), 800);
      return { success: true };
    } catch (err: any) {
      return { success: false, error: err.message || "Mã xác thực không chính xác" };
    }
  };

  // Gửi lại mã OTP trong Modal
  const handleResendOtp = async (): Promise<{ success: boolean; error?: string; rateLimitSeconds?: number }> => {
    try {
      const res = await fetch(`${backendUrl}/parent/settings/request-email-otp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ new_email: pendingEmail }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        return { success: false, error: errData.detail || "Không thể gửi lại mã OTP." };
      }

      const data = await res.json().catch(() => ({}));
      return { success: true, rateLimitSeconds: data.rate_limit_seconds || 60 };
    } catch (err: any) {
      return { success: false, error: err.message || "Lỗi khi gửi lại mã OTP." };
    }
  };

  // Loading skeleton
  if (isLoadingProfile) {
    return (
      <div className="max-w-2xl mx-auto animate-in fade-in duration-500 pb-10">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-8 h-8 bg-[#F1CCA6] rounded-lg animate-pulse" />
          <div className="h-8 w-40 bg-[#F1CCA6] rounded-xl animate-pulse" />
        </div>
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 h-36 animate-pulse" />
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 h-48 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto animate-in fade-in duration-500 pb-10">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => router.back()}
          className="p-2 rounded-xl hover:bg-[#F7AD62]/20 text-[#8C4905] transition-colors cursor-pointer"
          title="Quay lại"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-3xl font-extrabold text-[#8C4905] tracking-tight">
          Cài đặt tài khoản Phụ huynh
        </h1>
      </div>

      {/* Thông tin tài khoản */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6 mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-4 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Thông tin tài khoản
        </h2>
        <div className="space-y-3 text-sm text-[#8C4905]">
          {profile?.username && (
            <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]/60">
              <span className="font-medium text-[#C1762A]">Tên tài khoản</span>
              <span className="font-bold text-[#8C4905]">{profile.username}</span>
            </div>
          )}
          <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]/60">
            <span className="font-medium text-[#C1762A]">Email tài khoản</span>
            <div className="flex items-center gap-2">
              <span className="font-bold">{profile?.email || "—"}</span>
              {profile?.email && (
                profile.email_verified ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                    <ShieldCheck size={12} /> Đã xác thực
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                    <Clock size={12} /> Chưa xác thực
                  </span>
                )
              )}
            </div>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]/60">
            <span className="font-medium text-[#C1762A]">Vai trò</span>
            <span className="inline-flex items-center px-3 py-0.5 rounded-full text-xs font-bold bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]">
              Phụ huynh
            </span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="font-medium text-[#C1762A]">Phương thức đăng nhập</span>
            <span className="font-bold">
              {isGoogleOAuth ? (
                <span className="inline-flex items-center gap-1.5">
                  <svg className="w-4 h-4" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  Google
                </span>
              ) : (
                "Tên tài khoản & Mật khẩu"
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Form Đổi Email nhận thông báo cảnh báo (US 9.1 - T9.5) */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-1 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Email nhận thông báo cảnh báo
        </h2>
        <p className="text-sm text-[#C1762A] mb-5 leading-relaxed">
          Hệ thống sẽ gửi <strong>cảnh báo học tập</strong> (điểm tự lập thấp, bài tập khó) và{" "}
          <strong>cảnh báo ngôn từ</strong> (phát hiện ngôn ngữ tiêu cực) đến địa chỉ email này.
        </p>

        {isGoogleOAuth ? (
          /* Google OAuth — không cho chỉnh sửa */
          <div className="flex items-start gap-3 p-4 bg-[#F7ECE1] rounded-xl border border-[#F1CCA6]">
            <Lock size={18} className="text-[#C1762A] mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-bold text-[#8C4905] mb-0.5">
                Tài khoản Google — Email nhận thông báo cố định
              </p>
              <p className="text-sm text-[#C1762A]">
                Email <span className="font-bold">{profile?.email}</span> đang được dùng để nhận thông báo.
                Vì bạn đăng nhập bằng Google, email này không thể thay đổi.
              </p>
            </div>
          </div>
        ) : (
          /* Cho phép thay đổi email với xác nhận OTP 2 bước (AC 9.1.6) */
          <form onSubmit={handleInitiateChangeEmail} className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-[#8C4905] mb-2">
                Địa chỉ email nhận thông báo mới
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#C1762A]" />
                <input
                  type="email"
                  value={notifEmail}
                  onChange={(e) => {
                    setNotifEmail(e.target.value);
                    setErrorMsg("");
                    setSuccessMsg("");
                  }}
                  placeholder="vidu: phuhuynh@gmail.com"
                  disabled={isSubmitting}
                  className="w-full pl-10 pr-4 py-3 rounded-xl bg-[#F7ECE1]/60 text-stone-900 border border-[#F1CCA6] focus:border-[#C1762A] focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 placeholder:text-[#C1762A]/50 disabled:opacity-60 transition-all font-medium"
                />
              </div>
              <p className="text-xs text-[#C1762A]/80 mt-2">
                ⚠️ <strong>Lưu ý bảo mật:</strong> Khi bấm lưu, hệ thống sẽ gửi một mã OTP gồm 6 chữ số đến email mới để bạn xác thực trước khi cập nhật.
              </p>
            </div>

            {/* Feedback messages */}
            {successMsg && (
              <div className="flex items-center gap-2 text-sm font-bold text-green-700 bg-green-50 border border-green-200 rounded-xl px-4 py-3 animate-in slide-in-from-top-1">
                <CheckCircle2 size={16} />
                {successMsg}
              </div>
            )}
            {errorMsg && (
              <div className="flex items-center gap-2 text-sm font-bold text-red-700 bg-red-50 border border-red-200 rounded-xl px-4 py-3 animate-in slide-in-from-top-1">
                <AlertCircle size={16} />
                {errorMsg}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || !notifEmail.trim()}
              className="w-full py-3.5 rounded-xl bg-[#C1762A] text-white font-bold hover:bg-[#8C4905] shadow-md transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Đang gửi mã OTP xác nhận...
                </>
              ) : (
                "Lưu email nhận thông báo (Gửi mã OTP)"
              )}
            </button>
          </form>
        )}
      </div>

      {/* Popup Modal OTP Xác nhận Đổi Email (AC 9.1.6) */}
      <OtpModal
        isOpen={isOtpModalOpen}
        email={pendingEmail}
        title="Xác nhận đổi email thông báo"
        description={
          <>
            Vui lòng nhập mã OTP 6 chữ số được gửi tới email mới:
            <br />
            <strong className="text-[#C1762A] break-all">{pendingEmail}</strong>
          </>
        }
        onClose={() => setIsOtpModalOpen(false)}
        onVerify={handleVerifyOtp}
        onResend={handleResendOtp}
        initialCountdown={60}
      />
    </div>
  );
}
