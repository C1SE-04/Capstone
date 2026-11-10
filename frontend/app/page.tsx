"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import Navbar from "@/components/homepage/Navbar";
import HeroSection from "@/components/homepage/HeroSection";
import AboutSection from "@/components/homepage/AboutSection";
import FeaturesSection from "@/components/homepage/FeaturesSection";
import HowItWorksSection from "@/components/homepage/HowItWorksSection";
import FaqAccordion from "@/components/homepage/FaqAccordion";
import Footer from "@/components/homepage/Footer";
import LegalModal, { LegalModalType } from "@/components/homepage/LegalModal";

export default function Home() {
  const { data: session } = useSession();
  const router = useRouter();
  const [showAuthForm, setShowAuthForm] = useState(false);
  const [activeLegalModal, setActiveLegalModal] = useState<LegalModalType>(null);

  // Nếu là ADMIN, tự động chuyển hướng sang /admin
  useEffect(() => {
    if (session) {
      const role = (session.user as any)?.role;
      if (role === "ADMIN") {
        router.replace("/admin");
      }
    }
  }, [session, router]);

  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col selection:bg-[#C1762A]/20 selection:text-[#8C4905] w-full overflow-x-hidden min-w-0">
      {/* 1. Header cố định */}
      <Navbar onOpenAuth={() => setShowAuthForm(true)} />

      {/* 2. Hero Section */}
      <main className="flex-grow flex flex-col w-full overflow-x-hidden min-w-0">
        <HeroSection />

        {/* 3. Section Về chúng tôi (#about) */}
        <AboutSection />

        {/* 4. Section Tính năng nổi bật (#features) */}
        <FeaturesSection />

        {/* 5. Section Hướng dẫn sử dụng (#how-it-works) */}
        <HowItWorksSection />

        {/* 6. Section Câu hỏi thường gặp (#faq) */}
        <section
          id="faq"
          className="w-full py-16 sm:py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto scroll-mt-24"
        >
          <div className="max-w-3xl mb-12 sm:mb-16">
            <span className="text-xs uppercase tracking-wider font-bold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
              Giải Đáp Thắc Mắc
            </span>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1C1917] tracking-tight mb-4">
              Câu Hỏi Thường Gặp (FAQ)
            </h2>
            <p className="text-base sm:text-lg text-[#552B04] leading-relaxed">
              Những điều phụ huynh và học sinh quan tâm nhất về phương pháp học tập gợi mở cùng SocraticKid.
            </p>
          </div>
          <FaqAccordion />
        </section>
      </main>

      {/* 7. Footer chân trang (#contact) */}
      <Footer onOpenLegal={(type) => setActiveLegalModal(type)} />

      {/* 8. Modals (Auth & Legal) */}
      {showAuthForm && <AuthForm onClose={() => setShowAuthForm(false)} />}
      <LegalModal
        type={activeLegalModal}
        onClose={() => setActiveLegalModal(null)}
      />
    </div>
  );
}
