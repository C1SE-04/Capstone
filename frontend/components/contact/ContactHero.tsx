"use client";

import React from "react";
import { Send, Sparkles, MessageSquareHeart } from "lucide-react";

interface ContactHeroProps {
  onCtaClick?: () => void;
}

export default function ContactHero({ onCtaClick }: ContactHeroProps) {
  const handleScrollToForm = () => {
    if (onCtaClick) {
      onCtaClick();
      return;
    }

    const formElement = document.getElementById("contact-form");
    if (formElement) {
      formElement.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <section className="relative w-full pt-8 pb-6 md:pt-12 md:pb-10 text-center overflow-hidden">
      {/* Nền trang trí trừu tượng dạng gradient blur nhẹ */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-gradient-to-r from-[#F7AD62]/20 via-[#F1CCA6]/30 to-[#C1762A]/15 blur-3xl rounded-full pointer-events-none -z-10" />

      <div className="max-w-4xl mx-auto flex flex-col items-center">
        {/* Badge Phiên bản Beta */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/80 border border-[#F1CCA6] shadow-xs backdrop-blur-xs mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#C1762A] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#C1762A]" />
          </span>
          <span className="text-xs font-bold text-[#8C4905] tracking-wide uppercase">
            Phiên bản Thử nghiệm Beta
          </span>
          <Sparkles className="w-3.5 h-3.5 text-[#C1762A]" />
        </div>

        {/* Tiêu đề chính lớn H1 */}
        <h1 className="text-2xl sm:text-4xl md:text-5xl lg:text-6xl font-extrabold text-[#1C1917] tracking-tight leading-[1.2] mb-5 break-words">
          Đồng Hành & Lắng Nghe{" "}
          <span className="bg-gradient-to-r from-[#C1762A] to-[#8C4905] bg-clip-text text-transparent">
            Cùng SocraticKid
          </span>
        </h1>

        {/* Phụ đề (Subtitle) ấm áp */}
        <p className="text-base sm:text-lg md:text-xl text-[#7A3E04] max-w-2xl leading-relaxed mb-8">
          Mỗi ý kiến đóng góp, thắc mắc sư phạm hay phản ánh sự cố từ Quý phụ
          huynh, Thầy cô và các Em học sinh đều là động lực quý báu giúp chúng
          mình hoàn thiện nền tảng học tập khơi mở tư duy.
        </p>

        {/* Nút bấm CTA chính */}
        <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
          <button
            type="button"
            onClick={handleScrollToForm}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-7 py-3.5 rounded-2xl bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white font-bold text-sm md:text-base shadow-md hover:shadow-xl hover:brightness-105 active:scale-95 transition-all duration-200 cursor-pointer group"
          >
            <span>Gửi góp ý & phản hồi</span>
            <Send className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </button>

          <a
            href="#faq"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl bg-white/70 hover:bg-white text-[#8C4905] font-semibold text-sm md:text-base border border-[#F1CCA6] shadow-xs hover:shadow-md transition-all duration-200"
          >
            <MessageSquareHeart className="w-4 h-4 text-[#C1762A]" />
            <span>Câu hỏi thường gặp</span>
          </a>
        </div>
      </div>
    </section>
  );
}
