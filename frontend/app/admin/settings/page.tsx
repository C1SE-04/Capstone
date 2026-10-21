"use client";

import { Settings, Cpu } from "lucide-react";

export default function AdminSettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold text-[#2A1C0E]">
            Cài Đặt Hệ Thống & Tham Số AI
          </h1>
          <p className="text-xs md:text-sm text-[#7E6B5A] mt-1">
            Cấu hình mô hình ngôn ngữ lớn, ngưỡng nhiệt độ và giới hạn token cho phiên học
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-[#F7ECE1] text-[#8C4905] border border-[#E8D5C4]">
            Task T7.29 (Thiên sắp triển khai)
          </span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#E8D5C4] p-8 text-center shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center mx-auto mb-4">
          <Settings className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-bold text-[#2A1C0E]">
          Màn hình Cài đặt Hệ thống (Task T7.29)
        </h3>
        <p className="text-sm text-[#7E6B5A] max-w-md mx-auto mt-2">
          Khung layout và Breadcrumbs đã sẵn sàng. Form cấu hình model Gemini, temperature, max tokens và thông tin version sẽ được bạn triển khai ở task tiếp theo.
        </p>
      </div>
    </div>
  );
}
