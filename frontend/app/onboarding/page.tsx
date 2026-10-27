"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { GraduationCap, Users, CheckCircle2, ArrowRight, Loader2, Sparkles, BookOpen } from "lucide-react";

export default function OnboardingPage() {
  const { data: session, status, update } = useSession();
  const router = useRouter();

  const [role, setRole] = useState<"STUDENT" | "MONITOR">("STUDENT");
  const [selectedGrade, setSelectedGrade] = useState<number>(6);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Điều hướng nếu chưa đăng nhập hoặc đã hoàn tất onboarding
  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/");
    } else if (status === "authenticated" && session) {
      const isNew = session.is_new_user ?? (session.user as any)?.is_new_user;
      const userRole = (session.user as any)?.role;
      const grade = (session.user as any)?.grade_level;

      // Nếu không phải user mới và đã có khối lớp (với STUDENT) hoặc là MONITOR
      if (isNew === false && (userRole === "MONITOR" || (userRole === "STUDENT" && grade))) {
        if (userRole === "MONITOR") {
          router.replace("/dashboard/monitor");
        } else {
          router.replace("/dashboard/chat");
        }
      }
    }
  }, [status, session, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (role === "STUDENT" && (!selectedGrade || selectedGrade < 4 || selectedGrade > 9)) {
      setErrorMessage("Vui lòng chọn khối lớp từ lớp 4 đến lớp 9.");
      return;
    }

    const token = session?.access_token;
    if (!token) {
      setErrorMessage("Không tìm thấy phiên đăng nhập. Vui lòng thử đăng nhập lại.");
      return;
    }

    setIsSubmitting(true);

    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      const res = await fetch(`${backendUrl}/auth/onboarding`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          role: role,
          grade: role === "STUDENT" ? selectedGrade : null,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Không thể lưu thông tin. Vui lòng thử lại.");
      }

      const data = await res.json();

      // Đồng bộ thông tin mới vào session của NextAuth
      await update({
        role: data.role,
        grade_level: data.grade,
        is_new_user: false,
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });

      // Điều hướng người dùng tới Dashboard tương ứng
      if (data.role === "MONITOR") {
        router.replace("/dashboard/monitor");
      } else {
        router.replace("/dashboard/chat");
      }
    } catch (err: any) {
      console.error("[Onboarding] Lỗi hoàn tất thiết lập:", err);
      setErrorMessage(err.message || "Đã xảy ra lỗi khi hoàn tất thiết lập.");
      setIsSubmitting(false);
    }
  };

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-[#F7ECE1] flex flex-col items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4">
          <div className="w-14 h-14 rounded-full border-4 border-[#F1CCA6] border-t-[#C1762A] animate-spin" />
          <p className="text-[#8C4905] font-semibold text-base animate-pulse">
            Đang tải thông tin của bạn...
          </p>
        </div>
      </div>
    );
  }

  const grades = [
    { grade: 4, label: "Lớp 4", level: "Tiểu học" },
    { grade: 5, label: "Lớp 5", level: "Tiểu học" },
    { grade: 6, label: "Lớp 6", level: "THCS" },
    { grade: 7, label: "Lớp 7", level: "THCS" },
    { grade: 8, label: "Lớp 8", level: "THCS" },
    { grade: 9, label: "Lớp 9", level: "THCS" },
  ];

  return (
    <div className="min-h-screen bg-[#F7ECE1] text-[#8C4905] font-sans flex flex-col justify-between p-4 sm:p-8">
      {/* Top Brand Header */}
      <header className="max-w-4xl mx-auto w-full flex items-center justify-between pb-6 border-b border-[#F1CCA6]/60">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full overflow-hidden flex items-center justify-center bg-white shadow-xs">
            <img src="/logo.png" alt="SocraticKid" className="w-full h-full object-cover" />
          </div>
          <div>
            <span className="font-extrabold italic text-2xl text-[#C1762A] tracking-tight">
              SocraticKid
            </span>
            <span className="ml-2 px-2 py-0.5 text-xs font-bold rounded-full bg-[#F1CCA6] text-[#8C4905]">
              Thiết lập ban đầu
            </span>
          </div>
        </div>

        {session?.user && (
          <div className="flex items-center gap-2.5 bg-white/70 backdrop-blur-xs py-1.5 px-3 rounded-full border border-[#F1CCA6] shadow-xs">
            {session.user.image ? (
              <img
                src={session.user.image}
                alt="Avatar"
                className="w-7 h-7 rounded-full border border-[#C1762A]"
              />
            ) : (
              <div className="w-7 h-7 rounded-full bg-[#C1762A] text-white flex items-center justify-center font-bold text-xs">
                {session.user.name?.[0] || "U"}
              </div>
            )}
            <span className="text-xs font-semibold text-[#8C4905] hidden sm:inline max-w-[150px] truncate">
              {session.user.name || session.user.email}
            </span>
          </div>
        )}
      </header>

      {/* Main Container */}
      <main className="max-w-2xl mx-auto w-full my-8 bg-white/80 backdrop-blur-sm rounded-3xl p-6 sm:p-10 border border-[#F1CCA6] shadow-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#F7ECE1] text-[#C1762A] text-xs font-bold mb-3 border border-[#F1CCA6]">
            <Sparkles className="w-4 h-4 text-[#C1762A]" />
            Khởi đầu cùng Trợ lý AI
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#C1762A] tracking-tight mb-2">
            Chào mừng bạn đến với SocraticKid! 🎉
          </h1>
          <p className="text-sm sm:text-base text-[#8C4905]/80 font-medium max-w-lg mx-auto">
            Hãy chọn vai trò và khối lớp để AI chuẩn hóa phương pháp gợi mở và đồng hành phù hợp nhất với bạn.
          </p>
        </div>

        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm font-semibold flex items-center gap-3">
            <span className="text-lg">⚠️</span>
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Section 1: Chọn Vai trò */}
          <div>
            <label className="block text-sm font-bold text-[#8C4905] mb-3">
              1. Bạn tham gia SocraticKid với vai trò gì?
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Card Học sinh */}
              <button
                type="button"
                onClick={() => setRole("STUDENT")}
                className={`relative p-5 rounded-2xl border-2 text-left transition-all cursor-pointer flex flex-col justify-between ${
                  role === "STUDENT"
                    ? "border-[#C1762A] bg-[#F7ECE1]/60 shadow-sm ring-2 ring-[#C1762A]/20"
                    : "border-stone-200 bg-white hover:border-[#F1CCA6] hover:bg-stone-50/50"
                }`}
              >
                {role === "STUDENT" && (
                  <div className="absolute top-4 right-4 text-[#C1762A]">
                    <CheckCircle2 className="w-5 h-5 fill-[#C1762A] text-white" />
                  </div>
                )}
                <div>
                  <div className="w-12 h-12 rounded-xl bg-[#F1CCA6]/50 flex items-center justify-center text-[#C1762A] mb-3">
                    <GraduationCap className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-base text-[#8C4905] mb-1">
                    Em là Học sinh
                  </h3>
                  <p className="text-xs text-[#8C4905]/75 font-medium leading-relaxed">
                    Tự học Toán qua gợi mở từng bước của AI Socratic, tích lũy điểm ngọn lửa Streak.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#F1CCA6]/40 flex items-center gap-1.5 text-xs font-bold text-[#C1762A]">
                  <BookOpen className="w-3.5 h-3.5" />
                  Lớp 4 đến Lớp 9
                </div>
              </button>

              {/* Card Phụ huynh */}
              <button
                type="button"
                onClick={() => setRole("MONITOR")}
                className={`relative p-5 rounded-2xl border-2 text-left transition-all cursor-pointer flex flex-col justify-between ${
                  role === "MONITOR"
                    ? "border-[#C1762A] bg-[#F7ECE1]/60 shadow-sm ring-2 ring-[#C1762A]/20"
                    : "border-stone-200 bg-white hover:border-[#F1CCA6] hover:bg-stone-50/50"
                }`}
              >
                {role === "MONITOR" && (
                  <div className="absolute top-4 right-4 text-[#C1762A]">
                    <CheckCircle2 className="w-5 h-5 fill-[#C1762A] text-white" />
                  </div>
                )}
                <div>
                  <div className="w-12 h-12 rounded-xl bg-[#F1CCA6]/50 flex items-center justify-center text-[#C1762A] mb-3">
                    <Users className="w-6 h-6" />
                  </div>
                  <h3 className="font-bold text-base text-[#8C4905] mb-1">
                    Tôi là Phụ huynh
                  </h3>
                  <p className="text-xs text-[#8C4905]/75 font-medium leading-relaxed">
                    Theo dõi tiến độ tự lập, nhận cảnh báo học tập định kỳ và quản lý bài giải của con.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#F1CCA6]/40 flex items-center gap-1.5 text-xs font-bold text-[#C1762A]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Báo cáo & Giám sát
                </div>
              </button>
            </div>
          </div>

          {/* Section 2: Khối lớp (Chỉ hiện khi là Học sinh) */}
          {role === "STUDENT" ? (
            <div>
              <label className="block text-sm font-bold text-[#8C4905] mb-1.5">
                2. Em đang học lớp mấy?
              </label>
              <p className="text-xs text-[#8C4905]/70 font-medium mb-3.5">
                Chương trình học và câu hỏi gợi mở sẽ được tùy biến sát theo sách giáo khoa khối lớp của em.
              </p>
              <div className="grid grid-cols-3 sm:grid-cols-6 gap-2.5">
                {grades.map((item) => {
                  const isSelected = selectedGrade === item.grade;
                  return (
                    <button
                      key={item.grade}
                      type="button"
                      onClick={() => setSelectedGrade(item.grade)}
                      className={`p-3 rounded-xl border-2 flex flex-col items-center justify-center gap-1 transition-all cursor-pointer ${
                        isSelected
                          ? "border-[#C1762A] bg-[#C1762A] text-white shadow-sm scale-102"
                          : "border-stone-200 bg-white text-[#8C4905] hover:border-[#F1CCA6] hover:bg-stone-50"
                      }`}
                    >
                      <span className="font-extrabold text-base">
                        {item.label}
                      </span>
                      <span
                        className={`text-[10px] font-semibold ${
                          isSelected ? "text-[#F7ECE1]" : "text-[#8C4905]/60"
                        }`}
                      >
                        {item.level}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Thông báo cho Phụ huynh */
            <div className="p-4 rounded-2xl bg-[#F7ECE1]/60 border border-[#F1CCA6] flex items-start gap-3">
              <span className="text-xl">💡</span>
              <p className="text-xs sm:text-sm text-[#8C4905] font-medium leading-relaxed">
                Sau khi hoàn tất, bạn có thể nhập <strong>Mã liên kết (Pairing Code)</strong> từ tài khoản của con trong mục <em>Báo cáo & Giám sát</em> để theo dõi kết quả học tập mọi lúc mọi nơi.
              </p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3.5 px-6 rounded-xl bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white font-bold text-base shadow-md hover:brightness-105 active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Đang thiết lập thông tin...</span>
              </>
            ) : (
              <>
                <span>
                  {role === "STUDENT"
                    ? "Bắt đầu học ngay với SocraticKid"
                    : "Truy cập Bảng điều khiển Phụ huynh"}
                </span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
      </main>

      {/* Footer */}
      <footer className="text-center text-xs text-[#8C4905]/60 font-medium py-3">
        © 2026 SocraticKid — Trợ lý AI giáo dục Socratic cho học sinh Việt Nam
      </footer>
    </div>
  );
}
