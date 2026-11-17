"use client";

import React from "react";
import { Mail, MessageCircle, Clock, ArrowUpRight, ShieldCheck } from "lucide-react";

export default function ContactInfoCards() {
  return (
    <section className="w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 mb-12">
      {/* ── Grid 2 Cột Thẻ Thông Tin Cân Đối ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
        
        {/* ── Thẻ 1: Email Dự án ── */}
        <div className="group relative bg-white border border-[#F1CCA6] rounded-2xl p-6 sm:p-7 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-2xl bg-[#F7ECE1] border border-[#F1CCA6]/60 flex items-center justify-center text-[#C1762A] mb-4 group-hover:scale-105 transition-transform">
              <Mail className="w-6 h-6" />
            </div>
            <span className="text-xs uppercase font-bold tracking-wider text-[#C1762A] block mb-1">
              Hòm Thư Dự Án
            </span>
            <h3 className="text-xl font-bold text-[#1C1917] mb-2">
              Email Trực Tiếp
            </h3>
            <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed mb-6">
              Tiếp nhận các phản ánh sự cố kỹ thuật, báo cáo bảo mật và đề xuất hợp tác nghiên cứu giáo dục.
            </p>
          </div>

          <div className="pt-4 border-t border-[#F1CCA6]/40">
            <a
              href="mailto:hello@socratickid.edu.vn"
              className="inline-flex items-center gap-1.5 text-sm font-bold text-[#8C4905] hover:text-[#C1762A] group/link transition-colors"
            >
              <span>hello@socratickid.edu.vn</span>
              <ArrowUpRight className="w-4 h-4 transition-transform group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5" />
            </a>
          </div>
        </div>

        {/* ── Thẻ 2: Zalo Group Phụ huynh Beta ── */}
        <div className="group relative bg-white border border-[#F1CCA6] rounded-2xl p-6 sm:p-7 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-200 flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-2xl bg-[#ECFDF5] border border-[#10B981]/20 flex items-center justify-center text-[#10B981] mb-4 group-hover:scale-105 transition-transform">
              <MessageCircle className="w-6 h-6" />
            </div>
            <span className="text-xs uppercase font-bold tracking-wider text-[#10B981] block mb-1">
              Cộng Đồng Thử Nghiệm
            </span>
            <h3 className="text-xl font-bold text-[#1C1917] mb-2">
              Zalo Group Phụ Huynh Beta
            </h3>
            <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed mb-6">
              Không gian trao đổi trực tiếp cùng đội ngũ phát triển, chia sẻ bí quyết học cùng con và cập nhật tính năng mới.
            </p>
          </div>

          <div className="pt-4 border-t border-[#F1CCA6]/40">
            <a
              href="https://zalo.me/g/socratickid-beta"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-bold text-[#10B981] hover:text-[#059669] group/link transition-colors"
            >
              <span>Tham gia Zalo Group</span>
              <ArrowUpRight className="w-4 h-4 transition-transform group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5" />
            </a>
          </div>
        </div>
      </div>

      {/* ── Khối Ghi Chú Cam Kết SLA Phản Hồi (12-24 giờ) ── */}
      <div className="mt-6 max-w-4xl mx-auto p-4 rounded-2xl bg-white/70 border border-[#F1CCA6] shadow-xs flex flex-col sm:flex-row items-center sm:items-start md:items-center gap-3 text-center sm:text-left">
        <div className="w-9 h-9 rounded-xl bg-[#FFFBEB] border border-[#F59E0B]/30 flex items-center justify-center text-[#F59E0B] shrink-0">
          <Clock className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed">
            <strong className="text-[#1C1917] not-italic">
              Cam kết dịch vụ (SLA):
            </strong>{" "}
            <span className="italic">
              Đội ngũ SocraticKid cam kết phản hồi tất cả thư liên hệ, báo lỗi
              và góp ý tính năng của Quý người dùng trong vòng{" "}
              <strong className="text-[#8C4905]">12 đến 24 giờ</strong> làm việc.
            </span>
          </p>
        </div>
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#ECFDF5] border border-[#10B981]/20 text-[#10B981] text-xs font-bold shrink-0">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Hỗ trợ 24/7 với lỗi bảo mật</span>
        </div>
      </div>
    </section>
  );
}
