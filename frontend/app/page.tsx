"use client";
import { useState } from "react";
import { signOut, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";

export default function Home() {
  const { data: session } = useSession();
  const router = useRouter();
  const [showAuthForm, setShowAuthForm] = useState(false);
  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col">
      {/* Navigation Bar / Header */}
      <header className="w-full py-4 px-8 flex justify-between items-center relative z-10">
        {/* Logo Placeholder */}
        <div className="w-12 h-12 bg-[#D9D9D9] rounded-lg"></div>

        {/* Navigation Links */}
        <nav className="hidden md:flex absolute left-1/2 -translate-x-1/2 gap-12 text-[#C1762A] font-bold text-lg">
          <a href="#features" className="hover:text-[#8C4905] transition-colors">
            Tính năng
          </a>
          <a href="#about" className="hover:text-[#8C4905] transition-colors">
            Về Chúng tôi
          </a>
          <a href="#contact" className="hover:text-[#8C4905] transition-colors">
            Liên Hệ
          </a>
        </nav>

        {/* Login Button */}
        <div>
          {!session ? (
            <button
              onClick={() => setShowAuthForm(true)}
              className="bg-[#F1CCA6] text-[#C1762A] font-bold py-2 px-6 rounded-lg hover:bg-[#F7AD62] hover:text-white transition-colors italic cursor-pointer"
            >
              Đăng nhập
            </button>
          ) : (
            <div className="flex items-center gap-4">
              <span className="text-[#C1762A] font-medium hidden sm:inline-block">
                Xin chào, {session.user?.name}
              </span>
              <img
                src={session.user?.image || ""}
                alt="Avatar"
                className="w-10 h-10 rounded-full border-2 border-[#C1762A]"
              />
              <button
                onClick={() => signOut()}
                className="bg-[#C1762A] text-white font-bold py-2 px-4 rounded-lg hover:bg-[#8C4905] transition-colors text-sm cursor-pointer"
              >
                Đăng xuất
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-grow flex flex-col items-center pt-16 pb-20 px-4 text-center">
        <h1 className="text-5xl md:text-7xl font-extrabold italic text-[#C1762A] mb-6 tracking-tight">
          SocraticKid
        </h1>
        <p className="max-w-xl text-[#C1762A] font-medium text-lg md:text-xl mb-6 leading-relaxed">
          Trợ lý AI được thiết kế dành riêng cho học sinh Việt Nam — giải đáp thắc mắc và hỗ trợ ôn thi mọi lúc mọi nơi.
        </p>
        <div className="max-w-3xl text-[#8C4905] bg-[#F1CCA6]/40 p-6 rounded-2xl mb-10 shadow-sm border border-[#F1CCA6]">
          <p className="font-medium text-base md:text-lg italic leading-relaxed">
            &ldquo;Khác với các công cụ AI thông thường, SocraticKid không bao giờ làm bài hộ hay đưa ra đáp án trực tiếp. Chúng tôi áp dụng phương pháp Socratic – đặt câu hỏi gợi mở, dẫn dắt từng bước để các em học sinh tự mình khám phá ra câu trả lời, từ đó hiểu sâu và nhớ lâu hơn.&rdquo;
          </p>
        </div>
        <button 
          onClick={() => session ? router.push("/dashboard") : router.push("/try")}
          className="bg-[#F1CCA6] text-[#8C4905] font-bold text-lg py-3 px-10 rounded-xl hover:bg-[#F7AD62] hover:text-white transition-all shadow-md transform hover:scale-105 cursor-pointer">
          Dùng thử
        </button>
      </main>

      {/* Features Section */}
      <section id="features" className="w-full pb-20">
        <div className="bg-[#C1762A] w-full py-4 mb-16 shadow-inner">
          <h2 className="text-center text-2xl md:text-3xl font-black italic text-[#000000]">
            Các Tính Năng Nổi Bật
          </h2>
        </div>

        {/* Features Grid */}
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1 */}
          <div className="bg-[#F1CCA6] p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col text-center items-center">
            <img src="/star.svg" alt="Star Icon" className="w-12 h-12 mb-4" />
            <h3 className="text-xl font-bold text-[#8C4905] mb-4">Học Hiểu Sâu - Nhớ Lâu Dài</h3>
            <p className="text-[#C1762A] font-medium leading-relaxed">
              AI được huấn luyện đặc biệt để đóng vai trò người dẫn dắt. Thay vì cung cấp ngay đáp án, SocraticKid sẽ đặt các câu hỏi gợi ý, chia nhỏ bài toán phức tạp giúp các em tự suy luận và tìm ra cách giải.
            </p>
          </div>
          {/* Card 2 */}
          <div className="bg-[#F1CCA6] p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col text-center items-center">
            <img src="/shield.svg" alt="Shield Icon" className="w-12 h-12 mb-4" />
            <h3 className="text-xl font-bold text-[#8C4905] mb-4">An Toàn & Chuẩn Xác Tuyệt Đối</h3>
            <p className="text-[#C1762A] font-medium leading-relaxed">
              Mọi câu trả lời của AI đều được đi qua một hệ thống &ldquo;Giám thị&rdquo; (Reviewer Agent) nhằm đảm bảo nội dung phù hợp với học sinh, loại bỏ các từ ngữ độc hại và kiểm tra độ chính xác trước khi hiển thị.
            </p>
          </div>
          {/* Card 3 */}
          <div className="bg-[#F1CCA6] p-8 rounded-2xl shadow-sm hover:shadow-md transition-shadow flex flex-col text-center items-center">
            <img src="/target.svg" alt="Target Icon" className="w-12 h-12 mb-4" />
            <h3 className="text-xl font-bold text-[#8C4905] mb-4">Tối Ưu Cho Học Sinh Lớp 4 – 9</h3>
            <p className="text-[#C1762A] font-medium leading-relaxed">
              Hệ thống được thiết kế riêng biệt để tương thích với tư duy, ngôn ngữ và chương trình sách giáo khoa của học sinh Việt Nam, giúp các em ôn tập và làm bài tập bám sát kiến thức trên lớp.
            </p>
          </div>
        </div>
      </section>

      {/* Bottom Footer Area */}
      <footer id="contact" className="w-full bg-[#C1762A] text-[#F7ECE1] py-12 px-8 mt-auto">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Cột 1: Thương hiệu & Thông điệp */}
          <div className="flex flex-col gap-4">
            <div className="w-12 h-12 bg-[#D9D9D9] rounded-lg"></div> {/* Logo Placeholder */}
            <p className="font-medium text-sm md:text-base">
              &ldquo;Hệ thống AI Gia sư Socratic – Đồng hành cùng học sinh Việt Nam.&rdquo;
            </p>
            <p className="text-sm mt-4 opacity-80">
              © 2026 SocraticKid. All rights reserved.
            </p>
          </div>

          {/* Cột 2: Điều hướng nhanh */}
          <div className="flex flex-col gap-3">
            <h4 className="font-bold text-lg mb-2 text-white">Điều hướng nhanh</h4>
            <a href="#about" className="hover:text-white transition-colors">Về chúng tôi (About Us)</a>
            <a href="#features" className="hover:text-white transition-colors">Tính năng nổi bật (Features)</a>
            <a href="#how-it-works" className="hover:text-white transition-colors">Hướng dẫn sử dụng (How it works)</a>
          </div>

          {/* Cột 3: Hỗ trợ & Chính sách */}
          <div className="flex flex-col gap-3">
            <h4 className="font-bold text-lg mb-2 text-white">Hỗ trợ & Chính sách</h4>
            <a href="#faq" className="hover:text-white transition-colors">Câu hỏi thường gặp (FAQ)</a>
            <a href="#terms" className="hover:text-white transition-colors">Điều khoản sử dụng (Terms of Service)</a>
            <a href="#privacy" className="hover:text-white transition-colors">Chính sách bảo mật (Privacy Policy)</a>
            <a href="#contact" className="hover:text-white transition-colors">Liên hệ hỗ trợ (Contact)</a>
          </div>

          {/* Cột 4: Kết nối với chúng tôi */}
          <div className="flex flex-col gap-3">
            <h4 className="font-bold text-lg mb-2 text-white">Kết nối với chúng tôi</h4>
            <p>Email: <a href="mailto:support@socratickid.vn" className="hover:text-white transition-colors">support@socratickid.vn</a></p>
            <p>Hotline: <a href="tel:1900xxxx" className="hover:text-white transition-colors">1900 xxxx</a></p>
            
            <div className="flex gap-4 mt-2">
              {/* Facebook Icon */}
              <a href="#" className="hover:opacity-80 transition-opacity" aria-label="Facebook">
                <img src="/facebook.svg" alt="Facebook" className="w-8 h-8" />
              </a>
              {/* TikTok Icon */}
              <a href="#" className="hover:opacity-80 transition-opacity" aria-label="TikTok">
                <img src="/tiktok.svg" alt="TikTok" className="w-8 h-8" />
              </a>
              {/* YouTube Icon */}
              <a href="#" className="hover:opacity-80 transition-opacity" aria-label="YouTube">
                <img src="/youtube.svg" alt="YouTube" className="w-8 h-8" />
              </a>
            </div>
          </div>
        </div>
      </footer>

      {/* Auth Modal */}
      {showAuthForm && <AuthForm onClose={() => setShowAuthForm(false)} />}
    </div>
  );
}
