import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Liên hệ & Đóng góp ý kiến | SocraticKid",
  description:
    "Liên hệ và đóng góp ý kiến với đội ngũ SocraticKid để cùng hoàn thiện phương pháp học Toán Socratic. Tiếp nhận giải đáp thắc mắc, phản ánh sự cố kỹ thuật và đề xuất tính năng mới cho học sinh.",
  keywords: [
    "Liên hệ SocraticKid",
    "Góp ý SocraticKid",
    "Báo lỗi học toán",
    "Hỗ trợ sư phạm Socratic",
    "Trợ lý AI Toán học",
  ],
  openGraph: {
    title: "Liên hệ & Đóng góp ý kiến | SocraticKid",
    description:
      "Đồng hành cùng SocraticKid hoàn thiện nền tảng học Toán gợi mở tư duy cho học sinh từ lớp 4 đến lớp 9.",
    type: "website",
    locale: "vi_VN",
  },
};

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
