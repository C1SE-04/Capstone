"use client";

import React from "react";
import { XCircle, CheckCircle2, Quote, Sparkles, BookOpen, Brain, Shield } from "lucide-react";

export default function AboutSection() {
  return (
    <section
      id="about"
      className="w-full py-16 sm:py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto scroll-mt-24"
    >
      {/* Tiêu đề & Thông điệp mở đầu */}
      <div className="max-w-3xl mb-12 sm:mb-16">
        <span className="text-xs uppercase tracking-wider font-bold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
          Về Chúng Tôi & Triết Lý Socratic
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1C1917] tracking-tight mb-4">
          Tại sao SocraticKid <span className="text-[#C1762A]">tuyệt đối không</span> giải bài hộ?
        </h2>
        <p className="text-base sm:text-lg text-[#552B04] leading-relaxed">
          Chúng tôi tin rằng việc đưa ra đáp án sẵn chỉ giúp học sinh chép xong bài tập về nhà, nhưng lại tước đi cơ hội quý giá nhất: <strong>khả năng tự suy nghĩ và giải quyết vấn đề</strong>.
        </p>
      </div>

      {/* Bảng so sánh 2 trường phái học tập (Split Comparison Framework) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 mb-14">
        
        {/* Khối 1: Cách học giải hộ thông thường */}
        <div className="bg-white/60 p-6 sm:p-8 rounded-2xl border border-[#F1CCA6]/60 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-[#F1CCA6]/50">
              <div className="w-8 h-8 rounded-lg bg-red-50 text-red-600 flex items-center justify-center shrink-0 border border-red-200/60">
                <XCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#1C1917]">
                  Công Cụ AI & Giải Bài Hộ Thông Thường
                </h3>
                <p className="text-xs text-[#7A3E04]">Ăn xổi • Học vẹt • Ỷ lại</p>
              </div>
            </div>

            <ul className="space-y-4 text-sm text-[#552B04] leading-relaxed">
              <li className="flex items-start gap-3">
                <span className="text-red-500 font-bold shrink-0 mt-0.5">✕</span>
                <span>
                  <strong>Đưa ra lời giải hoàn chỉnh ngay lập tức:</strong> Học sinh chỉ cần chụp đề và chép đáp án vào vở bài tập để đối phó.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-red-500 font-bold shrink-0 mt-0.5">✕</span>
                <span>
                  <strong>Não bộ rơi vào trạng thái thụ động:</strong> Bỏ qua toàn bộ quá trình phân tích dữ kiện, suy luận và thử sai.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-red-500 font-bold shrink-0 mt-0.5">✕</span>
                <span>
                  <strong>Hệ quả khi đi thi:</strong> Chỉ cần đề bài đổi số hoặc thay đổi ngữ cảnh một chút là học sinh lúng túng, không biết bắt đầu từ đâu.
                </span>
              </li>
            </ul>
          </div>

          <div className="mt-6 pt-4 border-t border-[#F1CCA6]/50 text-xs text-[#7A3E04] italic">
            Kết quả: Làm xong bài nhanh nhưng kiến thức trôi đi ngay sau vài ngày.
          </div>
        </div>

        {/* Khối 2: Phương pháp SocraticKid */}
        <div className="bg-white p-6 sm:p-8 rounded-2xl border-2 border-[#C1762A]/40 shadow-sm flex flex-col justify-between relative overflow-hidden">
          <div className="absolute top-0 right-0 bg-[#C1762A] text-white text-[11px] font-bold py-1 px-3.5 rounded-bl-xl">
            Phương Pháp Chuẩn Sư Phạm
          </div>

          <div>
            <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-[#F7ECE1]">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#8C4905]">
                  Phương Pháp Gợi Mở Cùng SocraticKid
                </h3>
                <p className="text-xs text-[#C1762A] font-semibold">Tự suy luận • Hiểu sâu • Tự tin</p>
              </div>
            </div>

            <ul className="space-y-4 text-sm text-[#1C1917] leading-relaxed">
              <li className="flex items-start gap-3">
                <span className="text-[#C1762A] font-bold shrink-0 mt-0.5">✓</span>
                <span>
                  <strong>Đặt câu hỏi gợi ý chia nhỏ bài toán:</strong> Dẫn dắt từng bước từ những công thức nền tảng các em đã biết.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-[#C1762A] font-bold shrink-0 mt-0.5">✓</span>
                <span>
                  <strong>Kích hoạt tư duy phản biện:</strong> Khuyến khích học sinh tự đặt bút nháp, tự nhận diện điểm nghẽn và tự tìm ra cách giải.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-[#C1762A] font-bold shrink-0 mt-0.5">✓</span>
                <span>
                  <strong>Khắc sâu kiến thức dài hạn:</strong> Cảm giác sung sướng khi &ldquo;Eureka! Em tự giải được rồi!&rdquo; giúp các em nhớ mãi và yêu thích môn Toán hơn.
                </span>
              </li>
            </ul>
          </div>

          <div className="mt-6 pt-4 border-t border-[#F7ECE1] text-xs font-semibold text-[#8C4905]">
            Kết quả: Nắm chắc bản chất toán học, hình thành năng lực tự học trọn đời.
          </div>
        </div>

      </div>

      {/* Trích dẫn Socrates và Cam kết đồng hành */}
      <div className="bg-[#8C4905] text-[#F7ECE1] p-6 sm:p-8 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-sm">
        <div className="flex items-start gap-4">
          <Quote className="w-8 h-8 text-[#F1CCA6] shrink-0 opacity-80 mt-1" />
          <div>
            <p className="text-base sm:text-lg font-medium italic leading-relaxed text-white">
              &ldquo;Tôi không thể dạy ai bất cứ điều gì; tôi chỉ có thể khiến họ suy nghĩ.&rdquo;
            </p>
            <p className="text-xs sm:text-sm font-semibold text-[#F7AD62] mt-1">
              — Socrates (470 TCN – 399 TCN)
            </p>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-3 border-t md:border-t-0 md:border-l border-white/20 pt-4 md:pt-0 md:pl-6 text-xs text-[#F7ECE1]/90">
          <Shield className="w-6 h-6 text-[#F1CCA6] shrink-0" />
          <div>
            <p className="font-bold text-white">Được thiết kế cho học sinh Việt Nam</p>
            <p className="opacity-75">Tương thích SGK Lớp 4 – 9</p>
          </div>
        </div>
      </div>
    </section>
  );
}
