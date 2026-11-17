"use client";

import React, { useState } from "react";
import Navbar from "@/components/homepage/Navbar";
import Footer from "@/components/homepage/Footer";
import AuthForm from "@/components/AuthForm";
import LegalModal, { LegalModalType } from "@/components/homepage/LegalModal";
import ContactHero from "@/components/contact/ContactHero";
import ContactInfoCards from "@/components/contact/ContactInfoCards";
import { MessageSquareText, ShieldAlert } from "lucide-react";

export default function ContactPage() {
  const [showAuthForm, setShowAuthForm] = useState(false);
  const [activeLegalModal, setActiveLegalModal] = useState<LegalModalType>(null);

  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col selection:bg-[#C1762A]/20 selection:text-[#8C4905] w-full overflow-x-hidden min-w-0">
      {/* ── 1. Header Điều hướng ── */}
      <Navbar onOpenAuth={() => setShowAuthForm(true)} />

      <main className="flex-grow flex flex-col w-full overflow-x-hidden min-w-0">
        {/* ── 2. Hero Section (Task T11.5.3) ── */}
        <ContactHero />

        {/* ── 3. Khối Thẻ Thông Tin Liên Hệ (Task T11.5.4) ── */}
        <ContactInfoCards />

        {/* ── 4. Neo Anchor Khung Form Liên Hệ (#contact-form) cho Task T11.5.5 kế tiếp ── */}
        <section
          id="contact-form"
          className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 mb-16 scroll-mt-24"
        >
          <div className="bg-white border border-[#F1CCA6] rounded-3xl p-6 sm:p-10 shadow-lg relative overflow-hidden">
            <div className="text-center max-w-2xl mx-auto mb-8">
              <span className="text-xs uppercase tracking-wider font-bold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
                Biểu Mẫu Góp Ý
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1C1917] tracking-tight mb-3">
                Gửi Thắc Mắc Hoặc Báo Lỗi Cho Chúng Mình
              </h2>
              <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed">
                Hãy cho chúng mình biết trải nghiệm học tập của bạn cùng SocraticKid. Form tiếp nhận chi tiết đang được đồng bộ cho Task T11.5.5.
              </p>
            </div>

            {/* Placeholder Container chuẩn bị cho ContactForm (T11.5.5) */}
            <div className="p-8 rounded-2xl bg-[#F7ECE1]/40 border border-dashed border-[#F1CCA6] flex flex-col items-center justify-center text-center">
              <div className="w-12 h-12 rounded-2xl bg-white border border-[#F1CCA6] flex items-center justify-center text-[#C1762A] mb-3 shadow-xs">
                <MessageSquareText className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-[#1C1917] mb-1">
                Khu Vực Biểu Mẫu Nhập Liệu (T11.5.5)
              </h4>
              <p className="text-xs text-[#7A3E04] max-w-md leading-relaxed">
                Nút bấm CTA từ Hero Section đã cuộn mượt chính xác tới vị trí này (`#contact-form`). Sẵn sàng nhúng `ContactForm.tsx` ở bước tiếp theo!
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* ── 5. Chân trang Footer ── */}
      <Footer onOpenLegal={(type) => setActiveLegalModal(type)} />

      {/* ── 6. Modals ── */}
      {showAuthForm && <AuthForm onClose={() => setShowAuthForm(false)} />}
      <LegalModal
        type={activeLegalModal}
        onClose={() => setActiveLegalModal(null)}
      />
    </div>
  );
}
