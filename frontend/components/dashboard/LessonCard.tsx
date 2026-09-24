/**
 * File: components/dashboard/LessonCard.tsx
 * Mô tả: Component thẻ giao diện hiển thị thông tin 1 khóa học.
 * - Sử dụng Next.js Image để tối ưu hình ảnh thumbnail.
 * - Hiển thị thanh tiến độ (Progress bar) tự động tính toán % độ rộng (width) thông qua CSS inline.
 * - Click vào thẻ sẽ dùng `useRouter` đẩy sang trang chi tiết bài học.
 */
"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { LessonProps } from "@/data/mockLessons";

interface LessonCardProps extends LessonProps {
  // Prop tùy chọn: Nếu được truyền vào, sẽ ghi đè hành vi điều hướng mặc định của thẻ
  onClick?: () => void;
}

export function LessonCard({ id, title, description, thumbnail, progress, onClick }: LessonCardProps) {
  const router = useRouter();

  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      // Khi click vào bài học Toán học, đặt active chat về bài Toán để mở đúng đoạn chat
      if (typeof window !== "undefined") {
        localStorage.setItem("socratic_active_chat_id", "c-math-1");
      }
      router.push(`/dashboard/chat`);
    }
  };

  return (
    <div 
      onClick={handleClick}
      className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 hover:scale-[1.02] cursor-pointer flex flex-col h-full border border-[#F1CCA6]/50 group"
    >
      {/* Thumbnail Area */}
      <div className="relative w-full h-48 overflow-hidden bg-[#D9D9D9]">
        <Image 
          src={thumbnail} 
          alt={title}
          fill
          className="object-cover transition-transform duration-500 group-hover:scale-110"
        />
        {progress === 100 && (
          <div className="absolute top-3 right-3 bg-[#C1762A] text-white text-xs font-bold px-3 py-1 rounded-full shadow-md">
            Hoàn thành
          </div>
        )}
      </div>

      {/* Content Area */}
      <div className="p-5 flex-1 flex flex-col">
        <h3 className="text-xl font-bold text-[#8C4905] mb-2 line-clamp-1 group-hover:text-[#CB6600] transition-colors">
          {title}
        </h3>
        <p className="text-[#000000]/70 text-sm mb-5 flex-1 line-clamp-2 leading-relaxed">
          {description}
        </p>

        {/* Progress Bar */}
        <div className="mt-auto">
          <div className="flex justify-between text-xs font-semibold mb-1">
            <span className="text-[#C1762A]">Tiến độ</span>
            <span className="text-[#8C4905]">{progress}%</span>
          </div>
          <div className="w-full bg-[#F7ECE1] rounded-full h-2.5 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-[#F7AD62] to-[#C1762A] h-2.5 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}
