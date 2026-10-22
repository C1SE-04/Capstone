"use client";

import Link from "next/link";
import {
  Users,
  BookOpen,
  ShieldAlert,
  Settings,
  ArrowRight,
  BarChart3,
  TrendingUp,
  Cpu,
  GraduationCap,
} from "lucide-react";

export default function AdminPage() {
  const quickCards = [
    {
      title: "Quản lý Người dùng",
      description: "Xem danh sách 12,480 tài khoản học sinh, phụ huynh, phân quyền và khóa tài khoản vi phạm.",
      icon: Users,
      href: "/admin/users",
      stats: "12,480 Users",
      color: "#C1762A",
      bgLight: "#FDF6EE",
    },
    {
      title: "Học liệu Toán 4-9",
      description: "Quản lý 64 chủ đề toán học theo chương trình mới, cấu hình cho phép AI giải đáp bài tập.",
      icon: BookOpen,
      href: "/admin/content",
      stats: "64 Chủ đề",
      color: "#2B78C5",
      bgLight: "#EEF6FC",
    },
    {
      title: "Giám sát An toàn AI",
      description: "Nhật ký cảnh báo Safety Agent chặn ngôn từ không phù hợp, theo dõi chỉ số học sinh chưa hiểu.",
      icon: ShieldAlert,
      href: "/admin/safety",
      stats: "3 Cảnh báo mới",
      color: "#D93829",
      bgLight: "#FDF0ED",
    },
    {
      title: "Cài đặt Tham số Hệ thống",
      description: "Cấu hình model Gemini 1.5 Flash/Pro, giới hạn token, nhiệt độ sáng tạo và thông tin phiên bản.",
      icon: Settings,
      href: "/admin/settings",
      stats: "v1.4.0 Live",
      color: "#8C4905",
      bgLight: "#F7ECE1",
    },
  ];

  return (
    <div className="space-y-6">
      {/* ── 4 KPI Stats Quick Overview (Preview cho T7.25) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-5 border border-[#E8D5C4] shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#7E6B5A]">Tổng Người Dùng</span>
            <div className="p-2 rounded-lg bg-[#FDF6EE] text-[#C1762A]">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#2A1C0E] mt-2">12,480</div>
          <div className="text-xs font-semibold text-[#2A8C4A] mt-1 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5" />
            +14.2% so với tháng trước
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-[#E8D5C4] shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#7E6B5A]">Học Sinh Active (DAU)</span>
            <div className="p-2 rounded-lg bg-[#EEF6FC] text-[#2B78C5]">
              <GraduationCap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#2A1C0E] mt-2">3,842</div>
          <div className="text-xs font-semibold text-[#2A8C4A] mt-1 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5" />
            +8.6% hôm nay
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-[#E8D5C4] shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#7E6B5A]">Phiên Đối Thoại AI</span>
            <div className="p-2 rounded-lg bg-[#EAF7EE] text-[#2A8C4A]">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#2A1C0E] mt-2">48,920</div>
          <div className="text-xs font-semibold text-[#7E6B5A] mt-1">
            Tỷ lệ tự hiểu: <span className="font-bold text-[#C1762A]">82.4%</span>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 border border-[#E8D5C4] shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#7E6B5A]">Token AI Tiêu Thụ</span>
            <div className="p-2 rounded-lg bg-[#FDF0ED] text-[#D93829]">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-[#2A1C0E] mt-2">14.8M</div>
          <div className="text-xs font-semibold text-[#7E6B5A] mt-1">
            Chi phí ước tính: <span className="font-bold text-[#2A1C0E]">$18.42</span>
          </div>
        </div>
      </div>

      {/* ── Điều Hướng Nhanh Tới 4 Trang Chức Năng ── */}
      <div>
        <h2 className="text-base font-bold text-[#2A1C0E] mb-3">
          Danh mục Quản trị & Điều hướng Nhanh
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickCards.map((c) => {
            const Icon = c.icon;
            return (
              <Link
                key={c.href}
                href={c.href}
                className="group bg-white rounded-2xl p-5 border border-[#E8D5C4] hover:border-[#C1762A] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105"
                      style={{ backgroundColor: c.bgLight, color: c.color }}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-[#F7ECE1] text-[#8C4905]">
                      {c.stats}
                    </span>
                  </div>
                  <h3 className="font-bold text-[#2A1C0E] text-base group-hover:text-[#C1762A] transition-colors">
                    {c.title}
                  </h3>
                  <p className="text-xs md:text-sm text-[#7E6B5A] mt-1.5 leading-relaxed">
                    {c.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs font-semibold text-[#C1762A] group-hover:text-[#8C4905]">
                  <span>Vào trang quản trị</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
