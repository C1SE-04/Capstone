"use client";

import React, { useEffect } from "react";
import { X, FileText, ShieldCheck } from "lucide-react";

export type LegalModalType = "terms" | "privacy" | null;

interface LegalModalProps {
  type: LegalModalType;
  onClose: () => void;
}

export default function LegalModal({ type, onClose }: LegalModalProps) {
  useEffect(() => {
    if (!type) return;

    // Khóa cuộn trang nền khi modal mở
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Lắng nghe phím ESC để đóng modal
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [type, onClose]);

  if (!type) return null;

  const isTerms = type === "terms";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-xs animate-subtle-fade"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="legal-modal-title"
    >
      <div
        className="relative w-full max-w-2xl bg-[#F7ECE1] rounded-2xl shadow-xl border border-[#C1762A]/30 overflow-hidden flex flex-col max-h-[85vh] animate-modal-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Thanh trang trí đầu modal */}
        <div className="h-1 w-full bg-[#C1762A]" />

        {/* Header Modal */}
        <div className="px-6 py-5 border-b border-[#F1CCA6] flex items-center justify-between bg-white/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#F1CCA6]/60 text-[#C1762A] flex items-center justify-center">
              {isTerms ? <FileText className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            </div>
            <div>
              <h3 id="legal-modal-title" className="text-xl font-bold text-[#8C4905]">
                {isTerms ? "Điều Khoản Trải Nghiệm" : "Chính Sách Bảo Mật"}
              </h3>
              <p className="text-xs text-[#7A3E04] font-medium">
                {isTerms
                  ? "SocraticKid • Đồ Án Tốt Nghiệp Nghiên Cứu AI Sư Phạm Toán Học"
                  : "SocraticKid • Cam Kết Bảo Vệ & An Toàn Dữ Liệu Học Sinh"}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng cửa sổ"
            className="w-9 h-9 rounded-full bg-[#F1CCA6]/40 hover:bg-[#F1CCA6] active:scale-[0.95] text-[#8C4905] flex items-center justify-center transition-all duration-150 ease-out cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nội dung cuộn được bên trong */}
        <div className="px-6 py-6 overflow-y-auto text-[#1C1917] text-sm sm:text-base leading-relaxed space-y-5">
          {isTerms ? (
            <>
              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  1. Về Dự Án & Tinh Thần Trải Nghiệm
                </h4>
                <p className="text-[#552B04]">
                  Chào mừng bạn đến với <strong>SocraticKid</strong>! Đây là sản phẩm thuộc <em>Đồ án Tốt nghiệp (Capstone Project)</em> được phát triển bởi nhóm sinh viên với mong muốn nghiên cứu và ứng dụng phương pháp gợi mở Socratic vào việc hỗ trợ học sinh tự học toán. Nền tảng hoạt động hoàn toàn phi thương mại phục vụ mục đích học thuật và trải nghiệm giáo dục.
                </p>
              </div>

              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  2. Cùng Nhau Giữ Gìn Tinh Thần Tự Học
                </h4>
                <p className="text-[#552B04]">
                  Bạn Cú Socratic ở đây đóng vai trò người gia sư kiên nhẫn, luôn đặt các câu hỏi gợi ý nhỏ để các em học sinh tự mình tư duy và làm chủ kiến thức. Hệ thống <strong>tuyệt đối không làm bài hộ hay đưa ra đáp án sẵn để chép</strong>. Mong các bạn học sinh và phụ huynh cùng chung tay giữ gìn tinh thần học tập trung thực, không cố tình "bắt bẻ" hay ép AI giải hộ bài nhé!
                </p>
              </div>

              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  3. Tinh Thần Chia Sẻ Học Thuật & Bản Quyền
                </h4>
                <p className="text-[#552B04]">
                  Giao diện, hình ảnh chú Cú Socratic, kịch bản sư phạm và thuật toán gợi ý là thành quả tâm huyết từ những đêm thức trắng làm đồ án của nhóm sinh viên chúng mình. Bạn hoàn toàn có thể tự do trải nghiệm, tham khảo cho mục đích học tập phi thương mại; nếu có trích dẫn hoặc chia sẻ, nhóm chúng mình rất vui và cảm ơn bạn đã ghi nguồn ủng hộ dự án!
                </p>
              </div>

              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  4. Lời Nhắn Nhủ & Góc Nhỏ Thông Cảm
                </h4>
                <p className="text-[#552B04]">
                  Vì đây là sản phẩm đồ án tốt nghiệp đang trong giai đoạn thử nghiệm và hoàn thiện, bạn Cú AI đôi lúc có thể có những gợi mở chưa thực sự hoàn hảo. Rất mong quý thầy cô, phụ huynh và các bạn học sinh thông cảm và gửi góp ý để nhóm tiếp tục phát triển đề tài tốt hơn. Niềm vui hiểu bài và kết quả học tập vẫn luôn bắt nguồn từ chính sự kiên trì suy nghĩ của các bạn!
                </p>
              </div>
            </>
          ) : (
            <>
              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  1. Cam kết Bảo vệ Trẻ em & Tuân thủ Pháp luật
                </h4>
                <p className="text-[#552B04]">
                  SocraticKid đặt sự an toàn của học sinh lên hàng đầu, cam kết tuân thủ nghiêm ngặt <strong>Luật Trẻ em Việt Nam (2016)</strong> và các quy chuẩn quốc tế về bảo mật dữ liệu giáo dục cho trẻ vị thành niên.
                </p>
              </div>

              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  2. Tự động Che giấu Thông tin Cá nhân (PII Protection)
                </h4>
                <p className="text-[#552B04]">
                  Tầng kiểm duyệt an toàn (Reviewer Agent) tự động phát hiện và che giấu các thông tin nhạy cảm như họ tên đầy đủ, số điện thoại, địa chỉ nhà, trường lớp nếu học sinh vô tình nhập vào khung chat, ngăn ngừa rò rỉ dữ liệu cá nhân ra bên ngoài.
                </p>
              </div>

              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  3. Thu thập Dữ liệu Học tập & Tuyệt đối Không Bán Dữ liệu
                </h4>
                <p className="text-[#552B04]">
                  Hệ thống chỉ lưu trữ lịch sử đoạn hội thoại giải toán, chủ đề kiến thức và chỉ số chuỗi học tập (streak) nhằm phục vụ việc phân tích tiến độ cho phụ huynh và tối ưu hóa phương pháp giảng dạy. <strong>Chúng tôi tuyệt đối không bán, trao đổi hoặc chia sẻ dữ liệu học sinh cho bất kỳ bên thứ ba hay mạng quảng cáo nào.</strong>
                </p>
              </div>

              <div>
                <h4 className="font-bold text-[#8C4905] text-base mb-1.5">
                  4. Quyền Giám sát và Xóa Dữ liệu của Phụ huynh
                </h4>
                <p className="text-[#552B04]">
                  Phụ huynh có quyền truy cập bảng giám sát để kiểm tra lịch sử học tập của con, cũng như có quyền yêu cầu xóa vĩnh viễn toàn bộ dữ liệu hội thoại của con khỏi hệ thống bất cứ lúc nào thông qua tính năng quản lý tài khoản hoặc liên hệ ban quản trị.
                </p>
              </div>
            </>
          )}
        </div>

        {/* Footer Modal */}
        <div className="px-6 py-4 border-t border-[#F1CCA6] bg-white/70 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold py-2.5 px-6 rounded-xl active:scale-[0.98] transition-all duration-150 ease-out shadow-xs cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
          >
            {isTerms ? "Mình đã hiểu rồi!" : "Đã hiểu & Đóng"}
          </button>
        </div>
      </div>
    </div>
  );
}

