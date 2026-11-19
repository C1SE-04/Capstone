"use client";

import React, { useState } from "react";
import Script from "next/script";
import Navbar from "@/components/homepage/Navbar";
import Footer from "@/components/homepage/Footer";
import AuthForm from "@/components/AuthForm";
import LegalModal, { LegalModalType } from "@/components/homepage/LegalModal";
import ContactHero from "@/components/contact/ContactHero";
import ContactInfoCards from "@/components/contact/ContactInfoCards";
import ContactForm from "@/components/contact/ContactForm";
import ContactFaq from "@/components/contact/ContactFaq";

export default function ContactPage() {
  const [showAuthForm, setShowAuthForm] = useState(false);
  const [activeLegalModal, setActiveLegalModal] = useState<LegalModalType>(null);

  const recaptchaSiteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY;

  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col selection:bg-[#C1762A]/20 selection:text-[#8C4905] w-full overflow-x-hidden min-w-0">
      {/* ── Tích hợp Google reCAPTCHA v3 ngầm (Invisible) qua next/script ── */}
      {recaptchaSiteKey && (
        <Script
          src={`https://www.google.com/recaptcha/api.js?render=${recaptchaSiteKey}`}
          strategy="lazyOnload"
        />
      )}

      {/* ── 1. Navbar dùng chung của dự án ── */}
      <Navbar onOpenAuth={() => setShowAuthForm(true)} />

      {/* ── 2. Khung nội dung chính max-w-7xl w-full mx-auto ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pb-16 md:pb-24 space-y-12 md:space-y-16">
        {/* Contact Hero */}
        <ContactHero />

        {/* Contact Info Cards */}
        <ContactInfoCards />

        {/* Section bọc ContactForm (bắt buộc gắn id="contact-form" và scroll-mt-24, tối ưu max-w-3xl) */}
        <section
          id="contact-form"
          className="w-full max-w-3xl mx-auto scroll-mt-24"
        >
          <div className="bg-white border border-[#F1CCA6] rounded-2xl md:rounded-3xl p-6 sm:p-10 shadow-sm md:shadow-md relative overflow-hidden">
            <div className="text-center max-w-2xl mx-auto mb-8">
              <span className="text-xs uppercase tracking-wider font-extrabold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
                Biểu Mẫu Góp Ý & Báo Lỗi
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1C1917] tracking-tight mb-3">
                Gửi Thắc Mắc Hoặc Báo Cáo Sự Cố
              </h2>
              <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed">
                Hãy chia sẻ trải nghiệm học tập của bạn cùng SocraticKid. Đội ngũ kỹ sư và sư phạm sẽ phản hồi qua email trong thời gian sớm nhất.
              </p>
            </div>

            {/* Component Biểu mẫu Liên hệ T11.5.5 */}
            <ContactForm />
          </div>
        </section>

        {/* Contact FAQ (tối ưu max-w-3xl trên màn 1440px để độ rộng dòng đọc thoải mái) */}
        <ContactFaq />
      </main>

      {/* ── 3. Footer dùng chung của dự án ── */}
      <Footer onOpenLegal={(type) => setActiveLegalModal(type)} />

      {/* ── 4. Modals ── */}
      {showAuthForm && <AuthForm onClose={() => setShowAuthForm(false)} />}
      <LegalModal
        type={activeLegalModal}
        onClose={() => setActiveLegalModal(null)}
      />
    </div>
  );
}
