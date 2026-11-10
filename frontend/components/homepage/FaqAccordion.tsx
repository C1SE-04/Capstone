"use client";

import React, { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";

interface FaqItem {
  id: string;
  question: string;
  answer: string;
}

const FAQ_LIST: FaqItem[] = [
  {
    id: "faq-1",
    question: "SocraticKid có đưa ra lời giải ngay lập tức không?",
    answer:
      "Không. Khác với các công cụ AI thông thường, SocraticKid kiên định với phương pháp sư phạm Socratic: không bao giờ làm bài hộ hay cung cấp đáp án sẵn để học sinh chép. Thay vào đó, AI đóng vai trò người gia sư kiên nhẫn, đặt từng câu hỏi nhỏ gợi mở, giúp các em tự suy luận và tự khám phá ra cách giải để hiểu sâu bản chất.",
  },
  {
    id: "faq-2",
    question: "Học sinh dùng thử có cần trả phí hoặc đăng ký tài khoản không?",
    answer:
      "Hoàn toàn miễn phí! Học sinh và phụ huynh có thể nhấn nút 'Dùng thử ngay' để trải nghiệm đối thoại giải toán cùng SocraticKid tức thì mà không cần đăng ký tài khoản hay cung cấp bất kỳ thông tin thanh toán nào.",
  },
  {
    id: "faq-3",
    question: "Phụ huynh có thể kiểm tra và theo dõi tiến độ của con không?",
    answer:
      "Có. Phụ huynh có thể tạo tài khoản Giám sát (Monitor) và liên kết với tài khoản học sinh của con. Bảng điều khiển phụ huynh cung cấp góc nhìn toàn diện: mức độ độc lập tư duy, thời lượng học tập mỗi ngày, chuỗi chuyên cần (streak) và các dạng bài toán con cần bồi dưỡng thêm.",
  },
  {
    id: "faq-4",
    question: "Nội dung của AI có an toàn cho trẻ em không?",
    answer:
      "Tuyệt đối an toàn. Mọi câu trả lời của AI đều được kiểm duyệt nghiêm ngặt qua hệ thống Giám thị (Reviewer Agent) nhằm đảm bảo chuẩn mực ngôn từ sư phạm, loại bỏ mọi nội dung độc hại và tự động che giấu thông tin cá nhân (PII) của học sinh.",
  },
  {
    id: "faq-5",
    question: "SocraticKid phù hợp với học sinh ở những khối lớp nào?",
    answer:
      "SocraticKid được thiết kế chuyên sâu cho học sinh từ Lớp 6 đến Lớp 12 theo khung chương trình Giáo dục Phổ thông hiện hành. AI tự động điều chỉnh độ khó, xưng hô thân thiện và phương pháp tư duy phù hợp chính xác theo khối lớp mà học sinh lựa chọn.",
  },
  {
    id: "faq-6",
    question: "Em có thể chụp ảnh bài tập trong sách hoặc chữ viết tay gửi cho AI không?",
    answer:
      "Hoàn toàn được! SocraticKid tích hợp công nghệ thị giác máy tính thông minh, có khả năng nhận diện đề bài từ hình chụp trang sách bài tập, đề kiểm tra hoặc chữ viết tay có chứa công thức toán học và sơ đồ hình học rõ ràng.",
  },
  {
    id: "faq-7",
    question: "Nếu học sinh thử nhiều lần vẫn không hiểu, AI sẽ làm gì?",
    answer:
      "SocraticKid luôn đồng hành và không bỏ cuộc. Khi nhận thấy học sinh gặp bế tắc (hoặc khi em bấm nút 'Chưa hiểu'), AI sẽ linh hoạt đổi hướng tiếp cận: đưa ra một bài toán ví dụ đơn giản hơn cùng dạng, nhắc lại định lý cơ bản, hoặc chia nhỏ gợi ý hơn nữa để học sinh gỡ rối từng bước.",
  },
  {
    id: "faq-8",
    question: "Điểm Tự Lực (Independence Score) được tính như thế nào?",
    answer:
      "Điểm Tự Lực (thang điểm 100) đánh giá mức độ chủ động suy nghĩ của học sinh trong từng bài toán. Học sinh tự tìm ra đáp án với càng ít gợi ý chi tiết thì điểm tự lực càng cao (mức Xuất sắc từ 80-100đ). Chỉ số này giúp phụ huynh nhận biết con đang tự học thực chất hay còn phụ thuộc nhiều vào chỉ dẫn.",
  },
  {
    id: "faq-9",
    question: "Tính năng Sổ tay bài học (Notebook) giúp ích gì cho việc ôn tập?",
    answer:
      "Sau khi tự mình giải xong một bài toán khó, học sinh có thể lưu lại vào Sổ tay ôn tập. Hệ thống sẽ tự động tóm tắt bài học thành một thẻ Flashcard với đề bài, bí kíp cốt lõi cần nhớ và liên kết xem lại toàn bộ đoạn đối thoại, giúp các em ôn thi học kỳ cực kỳ nhanh chóng và hiệu quả.",
  },
  {
    id: "faq-10",
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
    <div className="w-full space-y-3.5">
      {FAQ_LIST.map((item, idx) => {
        const isOpen = openId === item.id;
        const buttonId = `faq-btn-${item.id}`;
        const panelId = `faq-panel-${item.id}`;

        return (
          <div
            key={item.id}
            className={`rounded-2xl border transition-all duration-150 overflow-hidden ${
              isOpen
                ? "bg-white border-[#C1762A] shadow-xs"
                : "bg-white/70 border-[#C1762A]/20 hover:border-[#C1762A]/40 shadow-xs"
            }`}
          >
            <button
              id={buttonId}
              type="button"
              onClick={() => toggleItem(item.id)}
              aria-expanded={isOpen}
              aria-controls={panelId}
              className="w-full px-6 py-5 flex items-center justify-between text-left gap-4 cursor-pointer select-none focus-visible:outline-2 focus-visible:outline-[#C1762A] active:scale-[0.99] transition-all duration-150 ease-out"
            >
              <div className="flex items-center gap-3.5">
                <span className="w-8 h-8 rounded-full bg-[#F1CCA6]/50 text-[#C1762A] font-bold text-sm flex items-center justify-center shrink-0 tabular-nums">
                  {idx + 1}
                </span>
                <span className="text-[#8C4905] font-bold text-base sm:text-lg">
                  {item.question}
                </span>
              </div>
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-transform duration-200 ${
                  isOpen ? "rotate-180 bg-[#C1762A] text-white" : "bg-[#F1CCA6]/40 text-[#C1762A]"
                }`}
              >
                <ChevronDown className="w-5 h-5" />
              </div>
            </button>

            {isOpen && (
              <div
                id={panelId}
                role="region"
                aria-labelledby={buttonId}
                className="px-6 pb-5 pt-1 text-[#552B04] text-sm sm:text-base leading-relaxed border-t border-[#F1CCA6]/40 animate-subtle-fade"
              >
                <p className="pl-11">{item.answer}</p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

