"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { ArrowRight, Compass, CheckCircle2, Sparkles, MessageCircle } from "lucide-react";

export default function HeroSection() {
  const { data: session } = useSession();
  const router = useRouter();

  const handlePrimaryClick = () => {
    if (session) {
      const userRole = (session.user as any)?.role;
      if (
        session.is_new_user ||
        (session.user as any)?.is_new_user ||
        userRole === "PENDING"
      ) {
        router.push("/onboarding");
        return;
      }
      if (userRole === "ADMIN") {
        router.push("/admin");
      } else if (userRole === "MONITOR") {
        router.push("/dashboard/monitor");
      } else {
        router.push("/dashboard/chat");
      }
    } else {
      router.push("/try");
    }
  };

  const getPrimaryButtonText = () => {
    if (!session) return "Trải nghiệm học thử ngay";
    const userRole = (session.user as any)?.role;
    if (
      session.is_new_user ||
      (session.user as any)?.is_new_user ||
      userRole === "PENDING"
    ) {
      return "Hoàn tất thiết lập ngay";
    }
    if (userRole === "ADMIN") return "Vào Dashboard Quản Trị";
    if (userRole === "MONITOR") return "Vào Dashboard Giám Sát";
    return "Vào phòng học ngay";
  };

  const handleScrollToExplore = (e: React.MouseEvent) => {
    e.preventDefault();
    const section = document.getElementById("about");
    if (section) {
      section.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative w-full pt-10 sm:pt-14 pb-16 sm:pb-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
        
        {/* Cột trái: Thông điệp cốt lõi & Hành động */}
        <div className="lg:col-span-7 flex flex-col items-start text-left">
          
          {/* Tagline tinh tế, không phô trương */}
          <div className="inline-flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 rounded-full bg-[#F1CCA6]/40 border border-[#C1762A]/25 text-[#8C4905] text-[11px] sm:text-sm font-semibold mb-6 max-w-full">
            <span className="w-2 h-2 rounded-full bg-[#C1762A] shrink-0" />
            <span className="truncate">AI Sư Phạm Toán Học • Dành Riêng Cho Lớp 4 – 9</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-[#1C1917] tracking-tight leading-[1.18] sm:leading-[1.12] mb-6 text-balance">
            Học hiểu bản chất,{" "}
            <span className="text-[#C1762A] underline decoration-[#F1CCA6] decoration-wavy decoration-2 underline-offset-6 sm:underline-offset-8">
              không học vẹt
            </span>{" "}
            đáp án.
          </h1>

          <p className="text-base sm:text-lg text-[#552B04] leading-relaxed max-w-xl mb-8 font-normal">
            Khác với các công cụ làm bài hộ, <strong>SocraticKid</strong> áp dụng phương pháp gợi mở của triết gia Socrates — kiên nhẫn đặt từng câu hỏi gợi ý để học sinh <em>tự mình suy luận</em> và làm chủ kiến thức toán học.
          </p>

          {/* Cụm nút CTA cảm ứng xúc giác (Emil Kowalski feedback rule) */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 w-full sm:w-auto mb-8">
            <button
              type="button"
              onClick={handlePrimaryClick}
              className="bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-sm sm:text-base py-3 sm:py-3.5 px-6 sm:px-8 rounded-xl active:scale-[0.98] transition-all duration-150 ease-out shadow-xs hover:shadow-sm flex items-center justify-center gap-2 cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A] w-full sm:w-auto"
            >
              <span>{getPrimaryButtonText()}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <a
              href="#about"
              onClick={handleScrollToExplore}
              className="bg-white/80 hover:bg-white text-[#8C4905] font-semibold text-sm sm:text-base py-3 sm:py-3.5 px-5 sm:px-6 rounded-xl border border-[#C1762A]/25 hover:border-[#C1762A]/50 active:scale-[0.98] transition-all duration-150 ease-out flex items-center justify-center gap-2 cursor-pointer text-center w-full sm:w-auto"
            >
              <Compass className="w-4 h-4 text-[#C1762A]" />
              <span>Tìm hiểu phương pháp ↓</span>
            </a>
          </div>

          {/* 3 Cam kết thực tế (Trust Badges) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-6 border-t border-[#F1CCA6]/60 w-full text-xs sm:text-sm text-[#7A3E04] font-medium">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#C1762A] shrink-0" />
              <span>Tuyệt đối không giải bài hộ</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#C1762A] shrink-0" />
              <span>Chuẩn SGK Toán 4 – 9</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#C1762A] shrink-0" />
              <span>Kiểm duyệt an toàn PII</span>
            </div>
          </div>
        </div>

        {/* Cột phải: Bằng chứng sản phẩm thực tế (Authentic Socratic Dialogue Preview) */}
        <div className="lg:col-span-5 relative">
          
          {/* Card mô phỏng phiên chat toán học thực tế */}
          <div className="relative bg-white rounded-2xl border border-[#C1762A]/20 shadow-md p-5 sm:p-6 text-left">
            
            {/* Header thanh mô phỏng */}
            <div className="flex items-center justify-between pb-3.5 mb-4 border-b border-[#F7ECE1]">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-[#F7ECE1] p-0.5 border border-[#C1762A]/30 flex items-center justify-center overflow-hidden">
                  <img src="/logo.png" alt="Socratic Owl" className="w-full h-full object-cover" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-[#8C4905]">Gia sư Cú Socratic</h4>
                  <p className="text-[11px] text-[#7A3E04]/70">Toán lớp 5 • Dạng toán Tổng - Hiệu</p>
                </div>
              </div>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                Đang đối thoại
              </span>
            </div>

            {/* Các lượt hội thoại chân thực */}
            <div className="space-y-3.5 text-xs sm:text-sm leading-relaxed">
              
              {/* Lượt 1: Học sinh hỏi bài */}
              <div className="flex items-start gap-2.5 justify-end">
                <div className="bg-[#F1CCA6]/40 text-[#1C1917] p-3 rounded-2xl rounded-tr-xs border border-[#F1CCA6] max-w-[85%]">
                  <p className="font-medium text-[#7A3E04] text-[11px] mb-0.5">Em học sinh</p>
                  <p>Một thửa ruộng hình chữ nhật có chu vi 120m, chiều dài hơn chiều rộng 20m. Tính diện tích ạ?</p>
                </div>
              </div>

              {/* Lượt 2: AI không đưa đáp án mà gợi mở bước 1 */}
              <div className="flex items-start gap-2.5">
                <div className="w-6 h-6 rounded-full overflow-hidden shrink-0 mt-1 border border-[#C1762A]/30">
                  <img src="/logo.png" alt="Owl" className="w-full h-full object-cover" />
                </div>
                <div className="bg-[#F7ECE1] text-[#1C1917] p-3 rounded-2xl rounded-tl-xs border border-[#C1762A]/20 max-w-[88%]">
                  <p className="font-bold text-[#C1762A] text-[11px] mb-0.5">SocraticKid</p>
                  <p>
                    Chào em! Muốn tính diện tích ta cần biết chiều dài và chiều rộng. Đề bài đã cho chu vi là 120m, vậy em có tính được <strong>nửa chu vi</strong> (tổng của dài và rộng) không nào?
                  </p>
                </div>
              </div>

              {/* Lượt 3: Học sinh tự suy luận */}
              <div className="flex items-start gap-2.5 justify-end">
                <div className="bg-[#F1CCA6]/40 text-[#1C1917] p-3 rounded-2xl rounded-tr-xs border border-[#F1CCA6] max-w-[85%]">
                  <p className="font-medium text-[#7A3E04] text-[11px] mb-0.5">Em học sinh</p>
                  <p>Dạ nửa chu vi là 120 : 2 = 60m ạ!</p>
                </div>
              </div>

              {/* Lượt 4: AI khen và tiếp tục mở khóa bước 2 */}
              <div className="flex items-start gap-2.5">
                <div className="w-6 h-6 rounded-full overflow-hidden shrink-0 mt-1 border border-[#C1762A]/30">
                  <img src="/logo.png" alt="Owl" className="w-full h-full object-cover" />
                </div>
                <div className="bg-[#F7ECE1] text-[#1C1917] p-3 rounded-2xl rounded-tl-xs border border-[#C1762A]/20 max-w-[88%]">
                  <p className="font-bold text-[#C1762A] text-[11px] mb-0.5">SocraticKid</p>
                  <p>
                    Rất chuẩn! Bây giờ bài toán đã trở về dạng <em>Tìm hai số khi biết Tổng (60m) và Hiệu (20m)</em>. Em thử tính xem chiều dài bằng bao nhiêu nhé?
                  </p>
                </div>
              </div>

            </div>

            {/* Chú thích giá trị cốt lõi dưới card */}
            <div className="mt-4 pt-3 border-t border-[#F7ECE1] flex items-center justify-between text-[11px] text-[#7A3E04] font-medium">
              <span className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                <Sparkles className="w-3.5 h-3.5" />
                Học sinh tự giải quyết 100%
              </span>
              <span className="opacity-75">Tự hiểu bản chất bài toán</span>
            </div>

          </div>

          {/* Thẻ phụ tạo chiều sâu thị giác (Subtle depth, no heavy outer blur) */}
          <div className="hidden sm:flex items-center gap-3 bg-[#8C4905] text-[#F7ECE1] py-2 px-3.5 rounded-xl absolute -bottom-4 -left-4 shadow-md text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span>Phương pháp đối thoại gợi mở Socratic</span>
          </div>

        </div>

      </div>
    </section>
  );
}
