/**
 * File: components/dashboard/LessonList.tsx
 * Mô tả: Component danh sách nhận vào mảng `lessons` và render ra một CSS Grid.
 * Tự động thích ứng số lượng cột hiển thị tùy theo thiết bị (Mobile: 1 cột, Tablet: 2 cột, PC: 3-4 cột).
 */
"use client";

import { LessonCard } from "./LessonCard";
import { LessonProps } from "@/data/mockLessons";

interface LessonListProps {
  lessons: LessonProps[];
}

export function LessonList({ lessons }: LessonListProps) {
  if (!lessons || lessons.length === 0) {
    return (
      <div className="w-full py-12 flex flex-col items-center justify-center text-center bg-white/50 rounded-2xl border border-dashed border-[#C1762A]/30">
        <p className="text-[#8C4905] font-medium text-lg">Chưa có bài học nào được tìm thấy.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      {lessons.map((lesson) => (
        <LessonCard key={lesson.id} {...lesson} />
      ))}
    </div>
  );
}
