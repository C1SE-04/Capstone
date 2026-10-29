"use client";

/**
 * File: app/dashboard/monitor/settings/page.tsx
 * Mô tả: Trang Cài đặt dành cho Phụ huynh (role=MONITOR).
 * - Hiển thị thông tin tài khoản (email đăng nhập, vai trò).
 * - Cho phép chỉnh sửa email nhận thông báo cảnh báo học tập & ngôn từ.
 * - Nếu đăng nhập bằng Google OAuth → email nhận thông báo = email Google, KHÔNG cho phép chỉnh sửa.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowLeft, Mail, Lock, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

interface UserProfile {
  email: string;
  oauth_provider: string | null;
  notification_email: string | null;
  role: string;
}

export default function MonitorSettingsPage() {
  const router = useRouter();
  const { data: session } = useSession();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);

  // Email nhận thông báo — field có thể chỉnh sửa
  const [notifEmail, setNotifEmail] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

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
        // Điền vào input: notification_email nếu đã lưu, ngược lại dùng email chính
        setNotifEmail(data.notification_email || data.email || "");
      } catch (err) {
        console.error(err);
        setErrorMsg("Không thể tải thông tin tài khoản. Vui lòng thử lại.");
      } finally {
        setIsLoadingProfile(false);
      }
    };

    fetchProfile();
  }, [session?.access_token]);

  const isGoogleOAuth = profile?.oauth_provider === "google";

  const handleSave = async () => {
    if (!notifEmail.trim()) {
      setErrorMsg("Email không được để trống.");
      return;
    }
    // Validate email format cơ bản
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(notifEmail.trim())) {
      setErrorMsg("Địa chỉ email không hợp lệ.");
      return;
    }

    setIsSaving(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const res = await fetch(`${backendUrl}/users/me/notification-email`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ notification_email: notifEmail.trim() }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể cập nhật email thông báo");
      }

      // Cập nhật lại profile local
      setProfile((prev) => prev ? { ...prev, notification_email: notifEmail.trim() } : prev);
      setSuccessMsg("✓ Đã lưu email nhận thông báo thành công!");
      setTimeout(() => setSuccessMsg(""), 4000);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Đã xảy ra lỗi hệ thống");
    } finally {
      setIsSaving(false);
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
          Cài đặt tài khoản
        </h1>
      </div>

      {/* Thông tin tài khoản */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6 mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-4 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Thông tin tài khoản
        </h2>
        <div className="space-y-3 text-sm text-[#8C4905]">
          <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]">
            <span className="font-medium text-[#C1762A]">Email đăng nhập</span>
            <span className="font-bold">{profile?.email || "—"}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]">
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
                "Email & Mật khẩu"
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Email nhận thông báo cảnh báo */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-1 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Email nhận thông báo cảnh báo
        </h2>
        <p className="text-sm text-[#C1762A] mb-5 leading-relaxed">
          Hệ thống sẽ gửi <strong>cảnh báo học tập</strong> (điểm tự lập thấp, tỷ lệ "Chưa hiểu" tăng đột biến) và{" "}
          <strong>cảnh báo ngôn từ</strong> (phát hiện ngôn ngữ không phù hợp) đến địa chỉ email này.
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
          /* Email & Password — cho phép chỉnh sửa */
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-[#8C4905] mb-2">
                Địa chỉ email nhận thông báo
              </label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#C1762A]" />
                <input
                  type="email"
                  value={notifEmail}
                  onChange={(e) => {
                    setNotifEmail(e.target.value);
                    setErrorMsg("");
                    setSuccessMsg("");
                  }}
                  placeholder="vidu@gmail.com"
                  disabled={isSaving}
                  className="w-full pl-9 pr-4 py-3 rounded-xl bg-[#F7ECE1] text-stone-900 border border-transparent focus:outline-none focus:ring-2 focus:ring-[#F7AD62] placeholder:text-[#C1762A]/50 disabled:opacity-60 transition-shadow"
                />
              </div>
              <p className="text-xs text-[#C1762A]/70 mt-1.5">
                Nếu để trống hoặc chưa đặt, hệ thống sẽ gửi về email đăng nhập: <strong>{profile?.email}</strong>
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
              onClick={handleSave}
              disabled={isSaving || notifEmail === (profile?.notification_email || profile?.email || "")}
              className="w-full py-3 rounded-xl bg-[#C1762A] text-white font-bold hover:bg-[#8C4905] shadow-md transition-all transform hover:-translate-y-0.5 disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2"
            >
              {isSaving ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Đang lưu...
                </>
              ) : (
                "Lưu email thông báo"
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

