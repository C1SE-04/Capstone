"use client";

import { BookOpen, Plus } from "lucide-react";

export default function AdminContentPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold text-[#2A1C0E]">
            Quản Lý Học Liệu Toán Lớp 4 - 9
          </h1>
          <p className="text-xs md:text-sm text-[#7E6B5A] mt-1">
            Danh mục các chủ đề toán học và bài học mẫu cho AI sư phạm
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-[#EEF6FC] text-[#2B78C5] border border-[#BADEF7]">
            Task T7.27 (Bảo đang phát triển)
          </span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#E8D5C4] p-8 text-center shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-[#EEF6FC] text-[#2B78C5] flex items-center justify-center mx-auto mb-4">
          <BookOpen className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-bold text-[#2A1C0E]">
          Màn hình Quản lý Học liệu (Task T7.27)
        </h3>
        <p className="text-sm text-[#7E6B5A] max-w-md mx-auto mt-2">
          Khung layout và Breadcrumbs đã sẵn sàng. Danh sách chủ đề toán lớp 4-9, nút Thêm chủ đề mới và Drawer chỉnh sửa đang được hoàn thiện.
        </p>
      </div>
    </div>
  );
}
