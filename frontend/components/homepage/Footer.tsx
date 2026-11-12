"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Mail, Clock, Copy, Check, Sparkles } from "lucide-react";

interface FooterProps {
  onOpenLegal: (type: "terms" | "privacy") => void;
}

export default function Footer({ onOpenLegal }: FooterProps) {
  const [copied, setCopied] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Dọn dẹp timer khi unmount
  useEffect(() => {
    return () => {
      if (toastTimerRef.current) {
        clearTimeout(toastTimerRef.current);
      }
    };
  }, []);

  // Quản lý Toast mượt mà với clearTimeout chống spam click
  const showToast = (msg: string) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    setToastMessage(msg);
    toastTimerRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  };

  const handleCopyEmail = async () => {
    try {
      await navigator.clipboard.writeText("support@socratickid.vn");
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      showToast("Đã sao chép địa chỉ email hỗ trợ!");
    } catch {
      showToast("Không thể sao chép, vui lòng copy thủ công.");
    }
  };

  const handleSocialClick = (platform: string) => {
    showToast(`Kênh ${platform} chính thức của SocraticKid sẽ sớm ra mắt!`);
  };

  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
    window.history.replaceState(null, "", window.location.pathname);
  };

  const handleSectionClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    const targetId = href.replace(/^#/, "");
    const targetElement = document.getElementById(targetId);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: "smooth" });
    }
    window.history.replaceState(null, "", href);
  };

  return (
    <footer
      id="contact"
      className="w-full bg-[#C1762A] text-[#F7ECE1] py-14 px-6 sm:px-8 mt-auto scroll-mt-24 border-t-4 border-[#8C4905]/40"
    >
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-10">
        {/* Cột 1: Thương hiệu & Slogan */}
        <div className="flex flex-col gap-4">
          <Link
            href="/"
            onClick={handleLogoClick}
            className="flex items-center gap-3 group w-fit cursor-pointer"
            aria-label="Về đầu trang SocraticKid"
          >
            <div className="w-12 h-12 rounded-full overflow-hidden flex items-center justify-center bg-[#F7ECE1] border-2 border-white/50 group-hover:scale-105 transition-transform shadow-sm">
              <img
                src="/logo.png"
                alt="SocraticKid Logo"
                className="w-full h-full object-cover"
              />
            </div>
            <span className="text-2xl font-black italic text-white tracking-tight">
              SocraticKid
            </span>
          </Link>
          <p className="font-medium text-sm md:text-base leading-relaxed text-[#F7ECE1]/90">
            &ldquo;Hệ thống AI Gia sư Socratic – Đồng hành khơi mở tiềm năng toán học cho học sinh Việt Nam.&rdquo;
          </p>
          <p className="text-xs sm:text-sm mt-3 opacity-75">
            © 2026 SocraticKid • Đồ án Tốt nghiệp (Capstone Project).
          </p>
        </div>

        {/* Cột 2: Điều hướng nhanh */}
        <div className="flex flex-col gap-3.5">
          <h4 className="font-bold text-lg text-white border-b border-[#F7ECE1]/20 pb-2">
            Điều hướng nhanh
          </h4>
          <a
            href="#about"
            onClick={(e) => handleSectionClick(e, "#about")}
            className="hover:text-white hover:translate-x-1 transition-all text-sm sm:text-base text-[#F7ECE1]/85"
          >
            Về chúng tôi (About Us)
          </a>
          <a
            href="#features"
            onClick={(e) => handleSectionClick(e, "#features")}
            className="hover:text-white hover:translate-x-1 transition-all text-sm sm:text-base text-[#F7ECE1]/85"
          >
            Tính năng nổi bật (Features)
          </a>
          <a
            href="#how-it-works"
            onClick={(e) => handleSectionClick(e, "#how-it-works")}
            className="hover:text-white hover:translate-x-1 transition-all text-sm sm:text-base text-[#F7ECE1]/85"
          >
            Hướng dẫn sử dụng (How it works)
          </a>
        </div>

        {/* Cột 3: Hỗ trợ & Chính sách */}
        <div className="flex flex-col gap-3.5">
          <h4 className="font-bold text-lg text-white border-b border-[#F7ECE1]/20 pb-2">
            Hỗ trợ & Chính sách
          </h4>
          <a
            href="#faq"
            onClick={(e) => handleSectionClick(e, "#faq")}
            className="hover:text-white hover:translate-x-1 transition-all text-sm sm:text-base text-[#F7ECE1]/85 text-left"
          >
            Câu hỏi thường gặp (FAQ)
          </a>
          <button
            type="button"
            onClick={() => onOpenLegal("terms")}
            className="hover:text-white hover:translate-x-1 transition-all text-sm sm:text-base text-[#F7ECE1]/85 text-left cursor-pointer"
          >
            Điều khoản sử dụng (Terms of Service)
          </button>
          <button
            type="button"
            onClick={() => onOpenLegal("privacy")}
            className="hover:text-white hover:translate-x-1 transition-all text-sm sm:text-base text-[#F7ECE1]/85 text-left cursor-pointer"
          >
            Chính sách bảo mật (Privacy Policy)
          </button>
        </div>

        {/* Cột 4: Kết nối với chúng tôi */}
        <div className="flex flex-col gap-3.5">
          <h4 className="font-bold text-lg text-white border-b border-[#F7ECE1]/20 pb-2">
            Kết nối với chúng tôi
          </h4>
          
          {/* Email hỗ trợ kèm nút sao chép nhanh 1-chạm */}
          <div className="flex flex-col gap-1.5 text-sm sm:text-base">
            <span className="text-xs uppercase tracking-wider font-semibold opacity-80">
              Email hỗ trợ:
            </span>
            <div className="flex items-center gap-2 bg-[#8C4905]/40 py-2 px-3 rounded-xl border border-white/20">
              <Mail className="w-4 h-4 shrink-0 text-[#F7ECE1]" />
              <a
                href="mailto:support@socratickid.vn"
                className="hover:text-white hover:underline transition-colors truncate font-mono text-sm"
              >
                support@socratickid.vn
              </a>
              <button
                type="button"
                onClick={handleCopyEmail}
                title="Sao chép email hỗ trợ"
                aria-label="Sao chép địa chỉ email hỗ trợ"
                className="ml-auto p-1.5 rounded-lg bg-white/10 hover:bg-white/25 active:scale-[0.95] text-white transition-all duration-150 ease-out cursor-pointer shrink-0 focus-visible:outline-2 focus-visible:outline-white"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-300" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {/* Thời gian trực hỗ trợ (Thay thế hotline 1900 xxxx giả định) */}
          <div className="flex items-center gap-2 text-xs sm:text-sm text-[#F7ECE1]/90 pt-1">
            <Clock className="w-4 h-4 shrink-0 text-[#F1CCA6]" />
            <span>Hỗ trợ trực tuyến: 08:00 - 21:00 hàng ngày</span>
          </div>

          {/* 3 Icon MXH: Sử dụng button thay vì href="#" chống giật trang */}
          <div className="pt-2">
            <span className="text-xs font-semibold opacity-80 block mb-2">
              Kênh truyền thông:
            </span>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => handleSocialClick("Facebook")}
                className="w-10 h-10 rounded-xl bg-white/15 hover:bg-white/30 flex items-center justify-center transition-all duration-150 ease-out hover:scale-105 active:scale-[0.95] cursor-pointer focus-visible:outline-2 focus-visible:outline-white"
                aria-label="Kênh Facebook SocraticKid"
              >
                <img src="/facebook.svg" alt="Facebook" className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => handleSocialClick("TikTok")}
                className="w-10 h-10 rounded-xl bg-white/15 hover:bg-white/30 flex items-center justify-center transition-all duration-150 ease-out hover:scale-105 active:scale-[0.95] cursor-pointer focus-visible:outline-2 focus-visible:outline-white"
                aria-label="Kênh TikTok SocraticKid"
              >
                <img src="/tiktok.svg" alt="TikTok" className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => handleSocialClick("YouTube")}
                className="w-10 h-10 rounded-xl bg-white/15 hover:bg-white/30 flex items-center justify-center transition-all duration-150 ease-out hover:scale-105 active:scale-[0.95] cursor-pointer focus-visible:outline-2 focus-visible:outline-white"
                aria-label="Kênh YouTube SocraticKid"
              >
                <img src="/youtube.svg" alt="YouTube" className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Toast thông báo nổi khi sao chép hoặc click MXH */}
      {toastMessage && (
        <div
          role="status"
          aria-live="polite"
          className="fixed bottom-6 right-6 z-50 bg-[#1C1917] text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 text-sm font-medium border border-[#F1CCA6]/40 animate-message-pop"
        >
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shrink-0 animate-pulse" />
          <span>{toastMessage}</span>
        </div>
      )}
    </footer>
  );
}

