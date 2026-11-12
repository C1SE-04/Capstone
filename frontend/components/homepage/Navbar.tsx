"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { Menu, X, LogOut, ArrowRight, User } from "lucide-react";

interface NavbarProps {
  onOpenAuth: () => void;
}

const NAV_LINKS = [
  { label: "Về chúng tôi", href: "#about" },
  { label: "Tính năng", href: "#features" },
  { label: "Hướng dẫn", href: "#how-it-works" },
  { label: "Hỏi đáp", href: "#faq" },
  { label: "Liên hệ", href: "#contact" },
];

export default function Navbar({ onOpenAuth }: NavbarProps) {
  const { data: session } = useSession();
  const router = useRouter();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Điều hướng người dùng theo vai trò khi bấm vào Avatar hoặc Tên
  const handleRoleNavigate = () => {
    if (!session) return;
    const role = (session.user as any)?.role;
    const isNewUser =
      session.is_new_user || (session.user as any)?.is_new_user || role === "PENDING";

    if (isNewUser) {
      router.push("/onboarding");
    } else if (role === "ADMIN") {
      router.push("/admin");
    } else if (role === "MONITOR") {
      router.push("/dashboard/monitor");
    } else {
      router.push("/dashboard/chat");
    }
    setMobileMenuOpen(false);
  };

  const handleLogout = async () => {
    try {
      const token = session?.access_token;
      if (token) {
        const backendUrl =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        await fetch(`${backendUrl}/auth/cancel-onboarding`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });
      }
    } catch {
      // Bỏ qua lỗi hủy onboarding
    }
    await signOut({ callbackUrl: "/" });
  };

  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
    window.history.replaceState(null, "", window.location.pathname);
    setMobileMenuOpen(false);
  };

  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    const targetId = href.replace(/^#/, "");
    const targetElement = document.getElementById(targetId);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: "smooth" });
    }
    window.history.replaceState(null, "", href);
    setMobileMenuOpen(false);
  };

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case "ADMIN":
        return "Quản trị viên";
      case "MONITOR":
        return "Phụ huynh";
      case "STUDENT":
        return "Học sinh";
      default:
        return "";
    }
  };

  const userRole = (session?.user as any)?.role;

  return (
    <header className="sticky top-0 z-40 w-full bg-[#F7ECE1]/95 backdrop-blur-md border-b border-[#F1CCA6]/50 shadow-2xs">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-16 sm:h-20 flex items-center justify-between">
        {/* 1. Logo SocraticKid có thể click cuộn mượt về đầu trang */}
        <Link
          href="/"
          onClick={handleLogoClick}
          className="flex items-center gap-2 sm:gap-2.5 lg:gap-3 group cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A] rounded-xl shrink-0"
          aria-label="Về đầu trang SocraticKid"
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 lg:w-11 lg:h-11 rounded-full overflow-hidden flex items-center justify-center bg-white border-2 border-[#C1762A]/40 group-hover:border-[#C1762A] group-hover:scale-105 transition-all shadow-xs shrink-0">
            <img
              src="/logo.png"
              alt="SocraticKid Logo"
              className="w-full h-full object-cover"
            />
          </div>
          <span className="text-lg sm:text-xl lg:text-2xl font-extrabold text-[#C1762A] tracking-tight group-hover:text-[#8C4905] transition-colors whitespace-nowrap">
            SocraticKid
          </span>
        </Link>

        {/* 2. Menu Desktop/Tablet - Co giãn tỷ lệ chuẩn theo từng kích thước màn hình */}
        <nav
          className="hidden md:flex items-center gap-2.5 lg:gap-6 xl:gap-8 text-[#C1762A] font-bold text-xs md:text-[13px] lg:text-[15px] xl:text-base shrink min-w-0"
          aria-label="Thanh điều hướng chính"
        >
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={(e) => handleNavClick(e, link.href)}
              className="hover:text-[#8C4905] transition-colors relative py-1 px-1 lg:px-2 focus-visible:outline-2 focus-visible:outline-[#C1762A] rounded-md whitespace-nowrap after:content-[''] after:absolute after:bottom-0 after:left-0 after:w-0 after:h-0.5 after:bg-[#8C4905] hover:after:w-full after:transition-all"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* 3. Khu vực Auth trên Desktop/Tablet */}
        <div className="hidden md:flex items-center gap-2 lg:gap-3 shrink-0">
          {!session ? (
            <button
              type="button"
              onClick={onOpenAuth}
              className="bg-[#F1CCA6] text-[#8C4905] font-bold py-2 lg:py-2.5 px-3.5 lg:px-6 text-xs lg:text-sm rounded-xl hover:bg-[#F7AD62] hover:text-white transition-all duration-150 ease-out shadow-xs hover:shadow-sm cursor-pointer active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-[#C1762A] whitespace-nowrap"
            >
              Đăng nhập
            </button>
          ) : (
            <div className="flex items-center gap-2 lg:gap-3 bg-white/70 py-1 lg:py-1.5 px-2.5 lg:px-3 rounded-2xl border border-[#F1CCA6] shadow-xs">
              {/* Cụm Avatar + Tên có thể bấm để điều hướng theo Role */}
              <button
                type="button"
                onClick={handleRoleNavigate}
                title="Bấm để vào không gian học tập"
                className="flex items-center gap-2 text-left group cursor-pointer hover:opacity-90 active:scale-[0.98] transition-all duration-150 ease-out focus-visible:outline-2 focus-visible:outline-[#C1762A] rounded-xl"
              >
                {session.user?.image ? (
                  <img
                    src={session.user.image}
                    alt="Avatar"
                    className="w-8 h-8 lg:w-9 lg:h-9 rounded-full border-2 border-[#C1762A] object-cover group-hover:ring-2 group-hover:ring-[#C1762A]/40 transition-all shrink-0"
                  />
                ) : (
                  <div className="w-8 h-8 lg:w-9 lg:h-9 rounded-full border-2 border-[#C1762A] bg-[#F7ECE1] overflow-hidden flex items-center justify-center shrink-0">
                    <img
                      src="/logo.png"
                      alt="Avatar"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <div className="flex flex-col">
                  <span className="text-[#8C4905] font-bold text-xs lg:text-sm leading-tight group-hover:text-[#C1762A] transition-colors max-w-[90px] lg:max-w-[120px] truncate">
                    {session.user?.name || "Người dùng"}
                  </span>
                  {userRole && (
                    <span className="text-[10px] lg:text-[11px] font-semibold text-[#C1762A] leading-tight">
                      {getRoleBadge(userRole)}
                    </span>
                  )}
                </div>
              </button>

              <button
                type="button"
                onClick={handleLogout}
                title="Đăng xuất"
                aria-label="Đăng xuất"
                className="p-1.5 lg:p-2 rounded-xl text-[#8C4905] hover:bg-[#F1CCA6]/60 hover:text-red-600 active:scale-[0.95] transition-all duration-150 ease-out cursor-pointer focus-visible:outline-2 focus-visible:outline-red-500"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* 4. Cụm điều khiển trên Mobile (Nút Đăng nhập luôn hiển thị cùng logo và menu, co giãn linh hoạt theo màn hình) */}
        <div className="flex md:hidden items-center gap-1.5 sm:gap-2">
          {!session ? (
            <button
              type="button"
              onClick={onOpenAuth}
              className="bg-[#F1CCA6] text-[#8C4905] font-bold text-xs py-1.5 px-3 rounded-lg sm:rounded-xl hover:bg-[#C1762A] hover:text-white border border-[#C1762A]/20 transition-all duration-150 ease-out shadow-xs cursor-pointer active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-[#C1762A] whitespace-nowrap"
            >
              Đăng nhập
            </button>
          ) : (
            <button
              type="button"
              onClick={handleRoleNavigate}
              title="Vào không gian học tập"
              aria-label="Vào không gian học tập"
              className="flex items-center gap-1.5 bg-white/80 p-1 pr-2 rounded-lg sm:rounded-xl border border-[#F1CCA6] text-[#8C4905] text-xs font-bold active:scale-[0.98] transition-all duration-150 ease-out shadow-xs cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
            >
              <img
                src={session.user?.image || "/logo.png"}
                alt="Avatar"
                className="w-6 h-6 rounded-full border border-[#C1762A] object-cover shrink-0"
              />
              <span className="max-w-[60px] truncate">
                {session.user?.name?.split(" ").pop() || "Vào học"}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-expanded={mobileMenuOpen}
            aria-label={mobileMenuOpen ? "Đóng menu điều hướng" : "Mở menu điều hướng"}
            className="p-1.5 sm:p-2.5 rounded-lg sm:rounded-xl bg-white/80 border border-[#F1CCA6] text-[#8C4905] hover:bg-[#F1CCA6] active:scale-[0.95] transition-all duration-150 ease-out cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A] shrink-0"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* 5. Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#F7ECE1] border-b-2 border-[#C1762A]/30 px-6 pt-3 pb-6 space-y-4 shadow-xl animate-drawer-in">
          <nav className="flex flex-col gap-3 font-bold text-lg text-[#C1762A]">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={(e) => handleNavClick(e, link.href)}
                className="py-2 px-3 rounded-lg hover:bg-white/80 hover:text-[#8C4905] transition-colors"
              >
                {link.label}
              </a>
            ))}
          </nav>

          {/* Khi đã đăng nhập: Hiển thị khối hồ sơ và nút Đăng xuất trong menu */}
          {session && (
            <div className="pt-3 border-t border-[#F1CCA6]">
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={handleRoleNavigate}
                  className="w-full flex items-center justify-between bg-white/80 p-3 rounded-xl border border-[#F1CCA6] cursor-pointer hover:bg-white transition-colors"
                >
                  <div className="flex items-center gap-3 text-left">
                    <img
                      src={session.user?.image || "/logo.png"}
                      alt="Avatar"
                      className="w-10 h-10 rounded-full border-2 border-[#C1762A] object-cover"
                    />
                    <div>
                      <p className="font-bold text-[#8C4905] text-sm">
                        {session.user?.name || "Người dùng"}
                      </p>
                      <p className="text-xs text-[#C1762A] font-semibold">
                        {getRoleBadge(userRole) || "Không gian cá nhân"}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-[#C1762A] flex items-center gap-1">
                    Vào học <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </button>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full py-2.5 px-4 rounded-xl border border-red-300 text-red-700 bg-red-50/50 hover:bg-red-100 font-bold text-sm flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <LogOut className="w-4 h-4" /> Đăng xuất
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </header>
  );
}

