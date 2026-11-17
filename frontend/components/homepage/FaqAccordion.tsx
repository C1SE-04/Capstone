"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  Brain,
  Gift,
  Users,
  ShieldCheck,
  GraduationCap,
  Camera,
  Lightbulb,
  Award,
  BookOpen,
  Link2,
} from "lucide-react";

/**
 * File: frontend/components/homepage/FaqAccordion.tsx
 * ==============================================================================
 * Khối FAQ Accordion tại Trang chủ (Homepage) đồng bộ 100% với Trang Contact:
 * - Ngoại hình: Thẻ bo tròn rounded-3xl, squircle icon theo chủ đề, tag phân loại uppercase
 * - Trạng thái: Active ring-2 ring-[#C1762A]/10, viền nổi bật, hover effect mượt mà
 * - Animation: Chuyển động CSS Grid 60fps (grid-rows-[0fr] -> grid-rows-[1fr]),
 *   hoàn toàn không giật layout, đóng mở êm ái
 * - Cơ chế Single-Open: Mở một câu thì câu khác tự động khép lại
 * - ChevronDown xoay mượt 180 độ
 */

interface FaqItem {
  id: string;
  tag: string;
  icon: React.ComponentType<{ className?: string }>;
  question: string;
  answer: string;
}

const FAQ_LIST: FaqItem[] = [
  {
    id: "faq-1",
    tag: "Phương Pháp Socratic",
    icon: Brain,
    question: "SocraticKid có đưa ra lời giải ngay lập tức không?",
    answer:
      "Không. Khác với các công cụ AI thông thường, SocraticKid kiên định với phương pháp sư phạm Socratic: không bao giờ làm bài hộ hay cung cấp đáp án sẵn để học sinh chép. Thay vào đó, AI đóng vai trò người gia sư kiên nhẫn, đặt từng câu hỏi nhỏ gợi mở, giúp các em tự suy luận và tự khám phá ra cách giải để hiểu sâu bản chất.",
  },
  {
    id: "faq-2",
    tag: "Chính Sách Sử Dụng",
    icon: Gift,
    question: "Học sinh dùng thử có cần trả phí hoặc đăng ký tài khoản không?",
    answer:
      "Hoàn toàn miễn phí! Học sinh và phụ huynh có thể nhấn nút 'Dùng thử ngay' để trải nghiệm đối thoại giải toán cùng SocraticKid tức thì mà không cần đăng ký tài khoản hay cung cấp bất kỳ thông tin thanh toán nào.",
  },
  {
    id: "faq-3",
    tag: "Bảng Điều Khiển Phụ Huynh",
    icon: Users,
    question: "Phụ huynh có thể kiểm tra và theo dõi tiến độ của con không?",
    answer:
      "Có. Phụ huynh có thể tạo tài khoản Giám sát (Monitor) và liên kết với tài khoản học sinh của con. Bảng điều khiển phụ huynh cung cấp góc nhìn toàn diện: mức độ độc lập tư duy, thời lượng học tập mỗi ngày, chuỗi chuyên cần (streak) và các dạng bài toán con cần bồi dưỡng thêm.",
  },
  {
    id: "faq-4",
    tag: "An Toàn Trẻ Em",
    icon: ShieldCheck,
    question: "Nội dung của AI có an toàn cho trẻ em không?",
    answer:
      "Tuyệt đối an toàn. Mọi câu trả lời của AI đều được kiểm duyệt nghiêm ngặt qua hệ thống Giám thị (Safety Guardrails) nhằm đảm bảo chuẩn mực ngôn từ sư phạm, loại bỏ mọi nội dung độc hại và tự động che giấu thông tin cá nhân (PII) của học sinh.",
  },
  {
    id: "faq-5",
    tag: "Khung Chương Trình",
    icon: GraduationCap,
    question: "SocraticKid phù hợp với học sinh ở những khối lớp nào?",
    answer:
      "SocraticKid được thiết kế chuyên biệt cho học sinh từ Lớp 4 đến Lớp 9 theo Khung Chương trình Giáo dục Phổ thông 2018 (tương thích Cánh Diều, Kết nối tri thức, Chân trời sáng tạo). AI tự động điều chỉnh độ khó, xưng hô thân thiện và phương pháp tư duy phù hợp chính xác theo khối lớp mà học sinh lựa chọn.",
  },
  {
    id: "faq-6",
    tag: "Nhận Diện Hình Ảnh (OCR)",
    icon: Camera,
    question: "Em có thể chụp ảnh bài tập trong sách hoặc chữ viết tay gửi cho AI không?",
    answer:
      "Hoàn toàn được! SocraticKid tích hợp công nghệ thị giác máy tính thông minh, có khả năng nhận diện đề bài từ hình chụp trang sách bài tập, đề kiểm tra hoặc chữ viết tay có chứa công thức toán học và sơ đồ hình học rõ ràng.",
  },
  {
    id: "faq-7",
    tag: "Sư Phạm Linh Hoạt",
    icon: Lightbulb,
    question: "Nếu học sinh thử nhiều lần vẫn không hiểu, AI sẽ làm gì?",
    answer:
      "SocraticKid luôn đồng hành và không bỏ cuộc. Khi nhận thấy học sinh gặp bế tắc (hoặc khi em bấm nút 'Chưa hiểu'), AI sẽ linh hoạt đổi hướng tiếp cận: đưa ra một bài toán ví dụ đơn giản hơn cùng dạng, nhắc lại định lý cơ bản, hoặc chia nhỏ gợi ý hơn nữa để học sinh gỡ rối từng bước.",
  },
  {
    id: "faq-8",
    tag: "Điểm Tự Lực & Đánh Giá",
    icon: Award,
    question: "Điểm Tự Lực (Independence Score) được tính như thế nào?",
    answer:
      "Điểm Tự Lực (thang điểm 100) đánh giá mức độ chủ động suy nghĩ của học sinh trong từng bài toán. Học sinh tự tìm ra đáp án với càng ít gợi ý chi tiết thì điểm tự lực càng cao (mức Xuất sắc từ 80-100đ). Chỉ số này giúp phụ huynh nhận biết con đang tự học thực chất hay còn phụ thuộc nhiều vào chỉ dẫn.",
  },
  {
    id: "faq-9",
    tag: "Sổ Tay Ôn Tập (Notebook)",
    icon: BookOpen,
    question: "Tính năng Sổ tay bài học (Notebook) giúp ích gì cho việc ôn tập?",
    answer:
      "Sau khi tự mình giải xong một bài toán khó, học sinh có thể lưu lại vào Sổ tay ôn tập. Hệ thống sẽ tự động tóm tắt bài học thành một thẻ Flashcard với đề bài, bí kíp cốt lõi cần nhớ và liên kết xem lại toàn bộ đoạn đối thoại, giúp các em ôn thi học kỳ cực kỳ nhanh chóng và hiệu quả.",
  },
  {
    id: "faq-10",
    tag: "Kết Nối Tài Khoản",
    icon: Link2,
    question: "Làm thế nào để phụ huynh liên kết tài khoản theo dõi con?",
    answer:
      "Rất đơn giản và bảo mật. Học sinh vào mục Cài đặt tài khoản và chọn 'Lấy mã liên kết' để tạo một mã ghép nối 6 ký tự. Phụ huynh chỉ cần nhập mã này vào trang Bảng điều khiển Phụ huynh là có thể bắt đầu theo dõi tiến độ học tập hàng ngày của con ngay lập tức.",
  },
];

export default function FaqAccordion() {
  // Mặc định mở câu hỏi đầu tiên để người dùng thấy ngay câu trả lời mẫu
  const [openId, setOpenId] = useState<string | null>("faq-1");

  const toggleItem = (id: string) => {
    setOpenId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="w-full space-y-4">
      {FAQ_LIST.map((item) => {
        const isOpen = openId === item.id;
        const IconComponent = item.icon;
        const buttonId = `faq-btn-${item.id}`;
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
              id={buttonId}
              type="button"
              onClick={() => toggleItem(item.id)}
              aria-expanded={isOpen}
              aria-controls={panelId}
              className="w-full p-5 sm:p-6 text-left flex items-center justify-between gap-4 transition-colors cursor-pointer group focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[#C1762A]"
            >
              <div className="flex items-center gap-3.5 sm:gap-4 min-w-0">
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
              aria-labelledby={buttonId}
              className={`grid transition-[grid-template-rows] duration-300 ease-out ${
                isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden">
                <div className="px-5 pb-5 sm:px-6 sm:pb-6 pt-0 text-xs sm:text-sm md:text-base text-[#552B04] leading-relaxed border-t border-[#F1CCA6]/40 mt-1 pt-4">
                  <p className="sm:pl-[58px]">{item.answer}</p>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
