"use client";

import React from "react";
import { ShieldCheck, BookOpen, Flame, Award, Lock, Sparkles, CheckCircle2 } from "lucide-react";

export default function FeaturesSection() {
  return (
    <section id="features" className="w-full py-16 sm:py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto scroll-mt-24">
      {/* Tiêu đề Section */}
      <div className="max-w-3xl mb-12 sm:mb-16">
        <span className="text-xs uppercase tracking-wider font-bold text-[#C1762A] bg-[#F1CCA6]/40 py-1.5 px-3.5 rounded-full border border-[#C1762A]/20 mb-3 inline-block">
          Tính Năng Vượt Trội
        </span>
        <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#1C1917] tracking-tight mb-4">
          Xây dựng cho học sinh, <span className="text-[#C1762A]">tin cậy</span> cho phụ huynh.
        </h2>
        <p className="text-base sm:text-lg text-[#552B04] leading-relaxed">
          Mỗi tính năng của SocraticKid đều được nghiên cứu kỹ lưỡng để kích thích niềm vui học toán tự lập và bảo vệ học sinh an toàn trong môi trường số.
        </p>
      </div>

      {/* Bento Grid bất đối xứng (Asymmetric Bento Grid) */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">

        {/* Card 1 (Lớn - 7 Cột): Hệ thống Giám Thị An Toàn Kép */}
        <div className="md:col-span-7 bg-white p-7 sm:p-8 rounded-2xl border border-[#C1762A]/20 shadow-xs flex flex-col justify-between relative overflow-hidden">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="w-12 h-12 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
              Tự Động Kiểm Duyệt 100%
            </span>
          </div>

          <div>
            <h3 className="text-xl sm:text-2xl font-bold text-[#8C4905] mb-2.5">
              Hệ Thống Giám Thị Sư Phạm (Reviewer Agent)
            </h3>
            <p className="text-sm sm:text-base text-[#552B04] leading-relaxed mb-6 font-normal">
              Mọi câu trả lời của AI đều phải đi qua một tầng kiểm duyệt chuyên biệt trước khi gửi đến mắt học sinh: loại bỏ hoàn toàn ngôn từ độc hại và tự động che giấu thông tin cá nhân (PII Protection).
            </p>
          </div>

          {/* Minh họa trực quan cơ chế bảo mật PII */}
          <div className="bg-[#F7ECE1]/60 p-4 rounded-xl border border-[#F1CCA6] text-xs space-y-2">
            <div className="flex items-center justify-between text-[#8C4905] font-semibold">
              <span className="flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-[#C1762A]" />
                Lọc dữ liệu cá nhân nhạy cảm
              </span>
              <span className="text-emerald-700 font-bold">Đã kích hoạt</span>
            </div>
            <p className="text-[#552B04] leading-relaxed">
              Ví dụ: Khi học sinh gõ <em>&ldquo;Em tên là Nguyễn Văn A ở phố Huế...&rdquo;</em>, hệ thống tự động ẩn danh hóa thành <em>&ldquo;Em tên là [HỌC SINH] ở [ĐỊA CHỈ]...&rdquo;</em> trước khi đưa vào mô hình học tập.
            </p>
          </div>
        </div>

        {/* Card 2 (5 Cột): Chuẩn SGK Việt Nam */}
        <div className="md:col-span-5 bg-white p-7 sm:p-8 rounded-2xl border border-[#C1762A]/20 shadow-xs flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6] mb-6">
              <BookOpen className="w-6 h-6" />
            </div>

            <h3 className="text-xl font-bold text-[#8C4905] mb-2.5">
              Tối Ưu Sách Giáo Khoa Lớp 4 – 9
            </h3>
            <p className="text-sm text-[#552B04] leading-relaxed mb-6 font-normal">
              Cơ sở tri thức được hiệu chỉnh bám sát theo các bộ SGK hiện hành (Kết nối tri thức, Cánh diều, Chân trời sáng tạo). AI hiểu chuẩn xác các thuật ngữ toán học và phương pháp vẽ sơ đồ đoạn thẳng của Việt Nam.
            </p>
          </div>

          {/* Badges các khối lớp */}
          <div className="flex flex-wrap gap-2 pt-4 border-t border-[#F7ECE1]">
            <span className="px-2.5 py-1 rounded-lg bg-[#F7ECE1] text-[#8C4905] text-xs font-semibold">
              Toán Lớp 4
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-[#F7ECE1] text-[#8C4905] text-xs font-semibold">
              Toán Lớp 5
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-[#F7ECE1] text-[#8C4905] text-xs font-semibold">
              Toán Lớp 6 – 9
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-[#F1CCA6]/40 text-[#C1762A] text-xs font-semibold">
              Đại số & Hình học
            </span>
          </div>
        </div>

        {/* Card 3 (6 Cột): Chỉ số Tự Lập cho Phụ Huynh */}
        <div className="md:col-span-6 bg-white p-7 sm:p-8 rounded-2xl border border-[#C1762A]/20 shadow-xs flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6] mb-6">
              <Award className="w-6 h-6" />
            </div>

            <h3 className="text-xl font-bold text-[#8C4905] mb-2.5">
              Báo Cáo Mức Độ Độc Lập Tư Duy
            </h3>
            <p className="text-sm text-[#552B04] leading-relaxed mb-5 font-normal">
              Bảng theo dõi dành riêng cho cha mẹ giúp đo lường chính xác con tự giải được bao nhiêu % bài toán mà không cần trợ giúp, chủ đề con cần ôn thêm và thời gian học tập mỗi ngày.
            </p>
          </div>

          <div className="bg-[#F7ECE1]/60 p-3.5 rounded-xl border border-[#F1CCA6] flex items-center justify-between text-xs text-[#8C4905]">
            <span className="font-semibold">Chỉ số độc lập trung bình:</span>
            <span className="font-bold text-sm text-[#C1762A] bg-white px-2.5 py-1 rounded-lg border border-[#F1CCA6]">
              84.5% Tự Lập
            </span>
          </div>
        </div>

        {/* Card 4 (6 Cột): Chuỗi Chuyên Cần Streak */}
        <div className="md:col-span-6 bg-white p-7 sm:p-8 rounded-2xl border border-[#C1762A]/20 shadow-xs flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6] mb-6">
              <Flame className="w-6 h-6 text-orange-500" />
            </div>

            <h3 className="text-xl font-bold text-[#8C4905] mb-2.5">
              Chuỗi Học Tập (Streak) & Huy Hiệu Sư Phạm
            </h3>
            <p className="text-sm text-[#552B04] leading-relaxed mb-5 font-normal">
              Tạo động lực học toán tự giác mỗi ngày. Học sinh nhận điểm chuyên cần và mở khóa các huy hiệu sư phạm danh giá khi kiên trì vượt qua những bài toán khó.
            </p>
          </div>

          <div className="bg-[#F7ECE1]/60 p-3.5 rounded-xl border border-[#F1CCA6] flex items-center justify-between text-xs text-[#8C4905]">
            <span className="font-semibold">Mục tiêu ngày:</span>
            <span className="flex items-center gap-1.5 font-bold text-orange-700 bg-white px-2.5 py-1 rounded-lg border border-[#F1CCA6]">
              <Flame className="w-4 h-4 fill-orange-500 text-orange-500" />
              Chuỗi 7 ngày liên tiếp
            </span>
          </div>
        </div>

      </div>
    </section>
  );
}
