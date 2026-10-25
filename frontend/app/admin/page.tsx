"use client";

import Link from "next/link";
import {
  Users,
  BookOpen,
  ShieldAlert,
  Settings,
  ArrowRight,
  TrendingUp,
  Brain,
  Flame,
  CheckCircle2,
  GraduationCap,
  MessageSquare,
  Cpu,
} from "lucide-react";

export default function AdminPage() {
  const quickCards = [
    {
      title: "Quản Lý Người Dùng",
      description: "Xem danh sách 48 tài khoản học sinh, phụ huynh, liên kết gia đình và kiểm soát trạng thái khóa/mở.",
      icon: Users,
      href: "/admin/users",
      stats: "48 Users",
      color: "#C1762A",
      bgLight: "#F7ECE1",
    },
    {
      title: "Học Liệu Toán 4 - 9",
      description: "Quản lý 64 chủ đề toán học theo chương trình mới, 3 cấp độ gợi ý Socratic và bài học mẫu cho AI.",
      icon: BookOpen,
      href: "/admin/content",
      stats: "64 Chủ đề",
      color: "#8C4905",
      bgLight: "#F7ECE1",
    },
    {
      title: "Giám Sát An Toàn AI",
      description: "Nhật ký cảnh báo Safety Agent chặn câu hỏi toxic, jailbreak prompt và theo dõi tỷ lệ học sinh chưa hiểu.",
      icon: ShieldAlert,
      href: "/admin/safety",
      stats: "3 Cảnh báo mới",
      color: "#D93829",
      bgLight: "#FDF0ED",
    },
    {
      title: "Cài Đặt Hệ Thống",
      description: "Cấu hình tham số model Gemini 1.5 Flash/Pro, nhiệt độ sáng tạo temperature, max tokens và phiên bản.",
      icon: Settings,
      href: "/admin/settings",
      stats: "v1.7.0 Live",
      color: "#8C4905",
      bgLight: "#F7ECE1",
    },
  ];

  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-500 space-y-8 pb-10">
      {/* ── 1. Header (Đồng bộ chuẩn Parent Dashboard) ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-[#C1762A] rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-md">
            AD
          </div>
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-[#8C4905] tracking-tight leading-none">
              Tổng Quan Quản Trị Hệ Thống
            </h1>
            <p className="text-sm text-[#C1762A] mt-1 font-medium">
              Giám sát người dùng, học liệu toán và hiệu năng AI SocraticKid
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-white text-[#8C4905] border border-[#F1CCA6] shadow-xs">
            Hệ thống: <strong className="text-[#2A8C4A]">Hoạt động ổn định</strong>
          </span>
        </div>
      </div>

      {/* ── 2. 4 KPI Summary Cards (Cùng ngôn ngữ với SummaryCards của Phụ Huynh) ── */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Thẻ 1: Tổng người dùng */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
              <Users size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-100">
              <TrendingUp size={12} /> +14.2%
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
              Tổng người dùng
            </p>
            <p className="text-2xl font-black text-[#8C4905] leading-none">
              48
            </p>
            <p className="text-xs text-[#C1762A]/70 mt-1.5 font-medium">36 Học sinh • 12 Phụ huynh</p>
          </div>
        </div>

        {/* Thẻ 2: Core Metric: Học sinh DAU (Nổi bật với viền cam đậm giống thẻ Tự Lực của phụ huynh) */}
        <div className="bg-gradient-to-br from-[#FFFBF7] to-[#F7ECE1] rounded-2xl p-5 border-2 border-[#C1762A]/40 shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-[#C1762A]/5 rounded-full blur-xl pointer-events-none" />
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#8C4905] flex items-center justify-center text-[#F7ECE1] shadow-md">
              <GraduationCap size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200">
              Tích cực
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#8C4905] uppercase tracking-wider mb-1 flex items-center gap-1.5">
              Học Sinh Active (DAU)
            </p>
            <div className="flex items-baseline gap-1.5">
              <span className="text-3xl font-black text-[#8C4905] leading-none">
                18
              </span>
              <span className="text-xs font-bold text-[#2A8C4A]">+8.6% hôm nay</span>
            </div>
            <p className="text-xs text-[#8C4905]/80 font-medium mt-1.5">
              MAU: 32 học sinh gắn kết
            </p>
          </div>
        </div>

        {/* Thẻ 3: Phiên Chat Socratic */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
              <MessageSquare size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-semibold text-[#8C4905] bg-[#F7ECE1] px-2 py-0.5 rounded-full border border-[#F1CCA6]">
              Tự hiểu: 82.4%
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
              Phiên Đối Thoại AI
            </p>
            <p className="text-2xl font-black text-[#8C4905] leading-none">
              46
            </p>
            <p className="text-xs text-[#C1762A]/70 mt-1.5 font-medium">Trung bình 18.5 phút / bài toán</p>
          </div>
        </div>

        {/* Thẻ 4: Điểm Tự Lập Toàn Hệ Thống */}
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200 flex flex-col justify-between">
          <div className="flex items-start justify-between">
            <div className="w-11 h-11 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A] shadow-inner">
              <Brain size={22} className="stroke-[2.2]" />
            </div>
            <span className="text-[11px] font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              Mục tiêu &gt; 80đ
            </span>
          </div>
          <div className="mt-4">
            <p className="text-xs font-bold text-[#C1762A] uppercase tracking-wider mb-1">
              Điểm Tự Lập Trung Bình
            </p>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-[#8C4905] leading-none">
                84.6
              </span>
              <span className="text-xs font-bold text-[#C1762A]">/100</span>
            </div>
            <p className="text-xs text-[#C1762A]/70 mt-1.5 font-medium">+4.2đ sau tinh chỉnh Socratic</p>
          </div>
        </div>
      </section>

      {/* ── 3. Danh mục Quản trị & Điều hướng nhanh ── */}
      <section className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-sm">
        <h2 className="text-lg font-bold text-[#8C4905] mb-5 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Danh Mục Quản Trị & Điều Hướng Nhanh
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickCards.map((c) => {
            const Icon = c.icon;
            return (
              <Link
                key={c.href}
                href={c.href}
                className="group bg-[#FFFDFB] rounded-2xl p-5 border border-[#F1CCA6] hover:border-[#C1762A] shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div
                      className="w-11 h-11 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105 shadow-inner"
                      style={{ backgroundColor: c.bgLight, color: c.color }}
                    >
                      <Icon className="w-5 h-5 stroke-[2.2]" />
                    </div>
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6]">
                      {c.stats}
                    </span>
                  </div>

                  <h3 className="font-extrabold text-[#8C4905] text-base group-hover:text-[#C1762A] transition-colors">
                    {c.title}
                  </h3>
                  <p className="text-xs md:text-sm text-[#7E6B5A] mt-1.5 leading-relaxed">
                    {c.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-[#F1CCA6]/40 flex items-center justify-between text-xs font-bold text-[#C1762A] group-hover:text-[#8C4905]">
                  <span>Vào trang quản trị</span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
