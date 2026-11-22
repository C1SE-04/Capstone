"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

const STEPS = [
  {
    num: "01",
    title: "Gửi đề bài toán khó",
    context: "Khởi đầu dễ dàng trong 5 giây",
    description:
      "Gặp bài toán hình học hay đại số khó? Em chỉ cần gõ nội dung hoặc chụp ảnh trang sách bài tập gửi cho Cú Socratic.",
  },
  {
    num: "02",
    title: "AI gợi mở từng nấc thang",
    context: "Không bao giờ đưa đáp án sẵn",
    description:
      "SocraticKid chia nhỏ bài toán thành các câu hỏi gợi ý đơn giản, giúp em nhớ lại định nghĩa, nhận ra điểm then chốt và tự vẽ đường đi.",
  },
  {
    num: "03",
    title: "Tự mình tìm ra đáp án",
    context: "Hiểu sâu & Nhớ mãi bản chất",
    description:
      "Em tự tay tính ra kết quả đúng, cảm nhận niềm vui chiến thắng bài khó, tích điểm chuyên cần và lưu công thức vào Sổ tay ôn thi.",
  },
];

export default function HowItWorksSection() {
  return (
    <section
      id="how-it-works"
      className="w-full py-16 sm:py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto scroll-mt-24"
    >
      {/* Tiêu đề Section */}
      <div className="max-w-3xl mb-12 sm:mb-16">
        <span className="text-xs uppercase tracking-wider font-bold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
          Hướng Dẫn Học Tập
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1C1917] tracking-tight mb-4">
          Lộ trình 3 bước bẻ khóa mọi bài toán.
        </h2>
        <p className="text-base sm:text-lg text-[#552B04] leading-relaxed">
          Đơn giản, trực quan và không gây áp lực. Biến những giờ tự học ở nhà thành trải nghiệm khám phá đầy hào hứng.
        </p>
      </div>

      {/* Quy trình kết nối (Connected Steps Timeline) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative mb-12">
        {STEPS.map((s, idx) => (
          <div
            key={idx}
            className="bg-white p-7 sm:p-8 rounded-2xl border border-[#C1762A]/20 shadow-xs flex flex-col justify-between relative group hover:border-[#C1762A]/50 transition-colors"
          >
            <div>
              {/* Header bước: Tối giản, không icon rườm rà */}
              <div className="mb-5 pb-3 border-b border-[#F7ECE1]">
                <span className="text-xs font-bold text-[#C1762A] tracking-wider tabular-nums">
                  BƯỚC {s.num}
                </span>
              </div>

              <p className="text-xs font-semibold text-[#7A3E04] uppercase tracking-wider mb-1">
                {s.context}
              </p>
              <h3 className="text-xl font-bold text-[#8C4905] mb-3 leading-snug">
                {s.title}
              </h3>
              <p className="text-sm text-[#552B04] leading-relaxed font-normal">
                {s.description}
              </p>
            </div>

            {/* Mũi tên định hướng kết nối giữa các bước: Căn giữa khoảng trống giữa 2 thẻ, ngang hàng với dòng tiêu đề Bước */}
            {idx < 2 && (
              <div
                aria-hidden="true"
                className="hidden md:flex absolute left-[calc(100%+0.75rem)] -translate-x-1/2 top-7 z-10 text-[#C1762A]/70 items-center justify-center pointer-events-none"
              >
                <ArrowRight className="w-5 h-5 stroke-[2.5]" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Box hành động trải nghiệm thử */}
      <div className="bg-[#F1CCA6]/30 border border-[#C1762A]/20 rounded-2xl p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6 text-left">
        <div>
          <h4 className="text-lg font-bold text-[#8C4905] mb-1">
            Muốn trải nghiệm cảm giác tự giải một bài toán?
          </h4>
          <p className="text-sm text-[#552B04]">
            Học sinh có thể trải nghiệm ngay 5 lượt tương tác gợi mở mà không cần đăng ký tài khoản.
          </p>
        </div>

        <Link
          href="/try"
          className="shrink-0 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-sm sm:text-base py-3 px-6 rounded-xl active:scale-[0.98] transition-all duration-150 ease-out shadow-sm flex items-center gap-2 cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
        >
          <span>Trải nghiệm thử một câu hỏi</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </section>
  );
}
