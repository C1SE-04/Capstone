"use client";

import { ShieldAlert, AlertCircle } from "lucide-react";

export default function AdminSafetyPage() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-extrabold text-[#2A1C0E]">
            Giám Sát An Toàn & Chất Lượng AI
          </h1>
          <p className="text-xs md:text-sm text-[#7E6B5A] mt-1">
            Nhật ký các câu hỏi bị chặn bởi Safety Agent và thống kê tỷ lệ phản hồi sư phạm
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold px-3 py-1.5 rounded-xl bg-[#FDF0ED] text-[#D93829] border border-[#F5BCB4]">
            Task T7.28 (Thiên sắp triển khai)
          </span>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#E8D5C4] p-8 text-center shadow-xs">
        <div className="w-14 h-14 rounded-2xl bg-[#FDF0ED] text-[#D93829] flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-bold text-[#2A1C0E]">
          Màn hình Giám sát Safety AI (Task T7.28)
        </h3>
        <p className="text-sm text-[#7E6B5A] max-w-md mx-auto mt-2">
          Khung layout và Breadcrumbs đã sẵn sàng. Bảng nhật ký câu hỏi toxic/jailbreak và biểu đồ tỷ lệ học sinh bấm Chưa hiểu sẽ được bạn triển khai ở task tiếp theo.
        </p>
      </div>
    </div>
  );
}
