"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  Clock,
  RefreshCw,
  School,
  Lock,
  HelpCircle,
} from "lucide-react";

/**
 * File: frontend/components/contact/ContactFaq.tsx
 * Sprint 11 - Task T11.5.6: Khối FAQ Hỗ Trợ & Tiếp Nhận Liên Hệ
 * ==============================================================================
 * Khối FAQ chuyên biệt hóa cho Trang Liên Hệ (Tránh trùng lặp với FAQ Trang chủ):
 * - Tập trung vào: Thời gian phản hồi, Xử lý sự cố kỹ thuật, Hợp tác trường học, Bảo mật thông tin
 * - Thiết kế chuẩn đồng bộ với Homepage: Thẻ bo tròn 3xl, Squircle Icon, Phân loại Tag
 * - Animation: Chuyển động CSS Grid 60fps mượt mà, không giật layout
 * - Cơ chế Single-Open: Mở một câu thì câu khác tự đóng
 */

interface FaqItem {
  id: string;
  tag: string;
  icon: React.ComponentType<{ className?: string }>;
  question: string;
  answer: string;
}

const SUPPORT_FAQ_DATA: FaqItem[] = [
  {
    id: "faq-response-time",
    tag: "Thời Gian Phản Hồi",
    icon: Clock,
    question: "Đội ngũ SocraticKid sẽ phản hồi ý kiến hoặc báo lỗi của tôi trong bao lâu?",
    answer:
      "Chúng mình cam kết xem xét và phản hồi mọi thắc mắc, phản ánh lỗi của Quý phụ huynh, Thầy cô và Học sinh trong vòng 24 giờ làm việc qua địa chỉ email bạn đã cung cấp. Đối với các sự cố kỹ thuật gây gián đoạn phiên học, đội ngũ kỹ sư sẽ tiếp nhận và xử lý khẩn cấp ngay trong ca trực.",
  },
  {
    id: "faq-tech-issue",
    tag: "Xử Lý Sự Cố Kỹ Thuật",
    icon: RefreshCw,
    question: "Tôi nên làm gì khi gặp lỗi mạng, trang bị treo hoặc AI không phản hồi?",
    answer:
      "Trước tiên, bạn vui lòng nhấn F5 để tải lại trang hoặc kiểm tra kết nối Internet. Nếu AI vẫn không phản hồi sau 30 giây, bạn có thể chụp ảnh màn hình và gửi qua Biểu mẫu liên hệ bên trên (hệ thống cho phép đính kèm tối đa 2 ảnh ≤ 5MB) để đội ngũ kỹ thuật tra soát mã lỗi hệ thống và khắc phục ngay lập tức.",
  },
  {
    id: "faq-cooperation",
    tag: "Hợp Tác Giáo Dục",
    icon: School,
    question: "Nhà trường hoặc Giáo viên muốn liên hệ hợp tác thử nghiệm thì làm thế nào?",
    answer:
      "SocraticKid luôn chào đón Quý Thầy Cô và các đơn vị giáo dục cùng đồng hành ứng dụng phương pháp gợi mở Socratic trong lớp học. Bạn hãy chọn danh mục 'Hợp tác nhà trường & Nghiên cứu giáo dục' tại biểu mẫu góp ý bên trên, hoặc gửi thư trực tiếp đến email socratickidsupport@gmail.com kèm thông tin liên hệ của trường.",
  },
  {
    id: "faq-privacy",
    tag: "Bảo Mật Thông Tin",
    icon: Lock,
    question: "Thông tin cá nhân và ảnh chụp màn hình tôi gửi lên có được bảo mật không?",
    answer:
      "Toàn bộ dữ liệu bạn gửi (bao gồm Họ tên, Email, nội dung chia sẻ và ảnh chụp màn hình đính kèm) đều được mã hóa an toàn theo Tiêu chuẩn Bảo vệ Dữ liệu Trẻ em. Chúng mình cam kết tuyệt đối không chia sẻ cho bên thứ ba và chỉ phục vụ duy nhất mục đích cải tiến trải nghiệm sư phạm cho học sinh.",
  },
];

export default function ContactFaq() {
  // Cơ chế Single-Open: Mở sẵn câu đầu tiên về thời gian phản hồi
  const [activeId, setActiveId] = useState<string | null>("faq-response-time");

  const toggleAccordion = (id: string) => {
    setActiveId((prev) => (prev === id ? null : id));
  };

  return (
    <section
      id="faq"
      className="w-full max-w-3xl mx-auto scroll-mt-24"
    >
      {/* ── Tiêu đề Section FAQ Hỗ Trợ ── */}
      <div className="text-center max-w-2xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white border border-[#F1CCA6] shadow-xs mb-3">
          <HelpCircle className="w-3.5 h-3.5 text-[#C1762A]" />
          <span className="text-xs uppercase font-extrabold text-[#8C4905] tracking-wider">
            Hỗ Trợ & Giải Đáp
          </span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-[#1C1917] tracking-tight mb-3">
          Câu Hỏi Về Tiếp Nhận & Hỗ Trợ
        </h2>
        <p className="text-xs sm:text-sm text-[#7A3E04] leading-relaxed">
          Những điều cần biết về thời gian xử lý phản hồi, xử lý sự cố kỹ thuật và quy trình hợp tác cùng SocraticKid.
        </p>
      </div>

      {/* ── Danh sách FAQ Accordions ── */}
      <div className="space-y-4">
        {SUPPORT_FAQ_DATA.map((item) => {
          const isOpen = activeId === item.id;
          const IconComponent = item.icon;
          const headerId = `faq-header-${item.id}`;
          const panelId = `faq-panel-${item.id}`;

          return (
            <div
              key={item.id}
              className={`rounded-3xl border transition-all duration-200 overflow-hidden ${
                isOpen
                  ? "bg-white border-[#C1762A]/60 shadow-md ring-2 ring-[#C1762A]/10"
                  : "bg-white/80 border-[#F1CCA6] shadow-xs hover:border-[#C1762A]/50 hover:bg-white"
              }`}
            >
              {/* ── Thanh Header Bấm Được Toàn Phần (Hitbox UX) ── */}
              <button
                type="button"
                id={headerId}
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => toggleAccordion(item.id)}
                className="w-full p-5 sm:p-6 text-left flex items-center justify-between gap-4 transition-colors cursor-pointer group focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#C1762A]"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  {/* Icon đại diện khối (Squircle Box) */}
                  <div
                    className={`w-10 h-10 sm:w-11 sm:h-11 rounded-2xl flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105 ${
                      isOpen
                        ? "bg-[#C1762A] text-white shadow-sm"
                        : "bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]/60"
                    }`}
                  >
                    <IconComponent className="w-5 h-5" />
                  </div>

                  <div className="min-w-0">
                    <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-[#C1762A] block mb-1">
                      {item.tag}
                    </span>
                    <h3
                      className={`text-sm sm:text-base font-extrabold tracking-tight transition-colors ${
                        isOpen
                          ? "text-[#8C4905]"
                          : "text-[#1C1917] group-hover:text-[#C1762A]"
                      }`}
                    >
                      {item.question}
                    </h3>
                  </div>
                </div>

                {/* Icon ChevronDown với hiệu ứng xoay 180 độ mượt mà */}
                <div
                  className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border transition-transform duration-300 ease-out ${
                    isOpen
                      ? "rotate-180 bg-[#F7ECE1] text-[#8C4905] border-[#F1CCA6]"
                      : "text-[#7A3E04]/70 border-transparent group-hover:bg-[#F7ECE1]/60"
                  }`}
                >
                  <ChevronDown className="w-4 h-4" />
                </div>
              </button>

              {/* ── Nội dung Trượt Mở Mượt Mà (Grid Transition 60fps) ── */}
              <div
                id={panelId}
                role="region"
                aria-labelledby={headerId}
                className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                  isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
                }`}
              >
                <div className="overflow-hidden">
                  <div className="px-5 pb-5 sm:px-6 sm:pb-6 pt-0 text-xs sm:text-sm text-[#552B04] leading-relaxed border-t border-[#F1CCA6]/40 mt-1 pt-4">
                    <p className="sm:pl-[58px]">{item.answer}</p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Banner chuyển tiếp về FAQ tổng quan Trang chủ ── */}
      <div className="mt-8 p-4 rounded-2xl bg-white/70 border border-[#F1CCA6] flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left shadow-2xs">
        <p className="text-xs sm:text-sm text-[#7A3E04]">
          Bạn muốn tìm hiểu thêm về phương pháp gợi mở Socratic và các tính năng học tập cốt lõi?
        </p>
        <a
          href="/#faq"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#F7ECE1] hover:bg-[#C1762A] text-[#8C4905] hover:text-white font-bold text-xs transition-all duration-200 border border-[#F1CCA6] shrink-0"
        >
          <span>Xem FAQ Trang chủ</span>
          <span>→</span>
        </a>
      </div>
    </section>
  );
}
