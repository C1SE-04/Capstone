/**
 * File: app/dashboard/page.tsx
 * Mô tả: Trang chính (Overview) của Dashboard.
 * - Hiển thị tên người dùng lấy từ Session (NextAuth).
 * - Hiển thị danh sách các khóa học gợi ý thông qua component `LessonList`.
 */
"use client";

import { LessonList } from "@/components/dashboard/LessonList";
import { mockLessons } from "@/data/mockLessons";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

export default function DashboardPage() {
  const { data: session } = useSession();
  const router = useRouter();

  return (
    <div className="max-w-7xl mx-auto flex flex-col h-full animate-in fade-in duration-500">
      {/* Header Section */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-[#8C4905] mb-2 tracking-tight">
            Chào mừng trở lại, {session?.user?.name || "bạn"}! 👋
          </h1>
          <p className="text-[#C1762A] text-lg font-medium">
            Tiếp tục hành trình học tập của bạn hôm nay.
          </p>
        </div>
        
        <button
          onClick={() => router.push('/dashboard/chat')}
          className="bg-[#C1762A] text-white px-6 py-3 rounded-xl font-bold hover:bg-[#8C4905] transition-colors shadow-md hover:shadow-lg transform hover:-translate-y-0.5 self-start md:self-auto flex items-center gap-2"
        >
          <span className="text-xl leading-none">+</span> Vào chat ngay (nút tạm thời)
        </button>
      </div>

      {/* Lessons Section */}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-[#8C4905] flex items-center gap-2">
            <span className="bg-[#F1CCA6] w-2 h-8 rounded-full inline-block"></span>
            Bài học đề xuất
          </h2>
        </div>
        
        <LessonList lessons={mockLessons} />
      </div>
    </div>
  );
}
