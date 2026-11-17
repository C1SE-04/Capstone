"use client";

import React, { useState } from "react";
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

  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col selection:bg-[#C1762A]/20 selection:text-[#8C4905] w-full overflow-x-hidden min-w-0">
      {/* ── 1. Header Điều hướng ── */}
      <Navbar onOpenAuth={() => setShowAuthForm(true)} />

      <main className="flex-grow flex flex-col w-full overflow-x-hidden min-w-0">
        {/* ── 2. Hero Section (Task T11.5.3) ── */}
        <ContactHero />

        {/* ── 3. Khối Thẻ Thông Tin Liên Hệ (Task T11.5.4) ── */}
        <ContactInfoCards />

        {/* ── 4. Khung Biểu Mẫu Liên Hệ (Task T11.5.5) ── */}
        <section
          id="contact-form"
          className="w-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 mb-8 scroll-mt-24"
        >
          <div className="bg-white border border-[#F1CCA6] rounded-3xl p-6 sm:p-10 shadow-lg relative overflow-hidden">
            <div className="text-center max-w-2xl mx-auto mb-8">
              <span className="text-xs uppercase tracking-wider font-extrabold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
                Biểu Mẫu Góp Ý & Báo Lỗi
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1C1917] tracking-tight mb-3">
                Gửi Thắc Mắc Hoặc Báo Lỗi Cho Chúng Mình
              </h2>
              <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed">
                Hãy cho chúng mình biết trải nghiệm học tập của bạn cùng SocraticKid. Đội ngũ kỹ sư và sư phạm sẽ phản hồi qua email sớm nhất có thể.
              </p>
            </div>

            {/* Component Biểu mẫu Liên hệ T11.5.5 */}
            <ContactForm />
          </div>
        </section>

        {/* ── 5. Khối FAQ Accordion (Task T11.5.6) ── */}
        <ContactFaq />
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
