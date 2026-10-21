"use client";

import { Users, Search, Filter, ShieldCheck, UserCheck } from "lucide-react";

export default function AdminUsersPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold text-[#2A1C0E]">
            Quản Lý Người Dùng
          </h1>
          <p className="text-xs md:text-sm text-[#7E6B5A] mt-1">
            Danh sách toàn bộ tài khoản Học sinh và Phụ huynh trong hệ thống SocraticKid
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-[#FDF6EE] text-[#C1762A] border border-[#F1CCA6]">
            Task T7.26 (Bảo đang phát triển)
          </span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#E8D5C4] p-8 text-center shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-[#FDF6EE] text-[#C1762A] flex items-center justify-center mx-auto mb-4">
          <Users className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-bold text-[#2A1C0E]">
          Màn hình Quản lý Users (Task T7.26)
        </h3>
        <p className="text-sm text-[#7E6B5A] max-width-lg mx-auto mt-2 max-w-md">
          Khung layout và điều hướng Breadcrumbs đã hoạt động hoàn hảo. Bảng danh sách người dùng, bộ lọc Role và modal Khóa/Mở tài khoản đang được hoàn thiện.
        </p>
      </div>
    </div>
  );
}
