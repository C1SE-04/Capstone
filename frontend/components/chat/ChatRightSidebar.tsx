"use client";

import { useState } from "react";
import {
  X,
  Maximize2,
  ImageIcon,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface ExerciseImage {
  id: string;
  url: string;
  time?: string;
  role?: string;
}

interface ChatRightSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  images: ExerciseImage[];
  onZoomImage: (url: string) => void;
  onUploadClick?: () => void;
  className?: string;
}

export function ChatRightSidebar({
  isOpen,
  onClose,
  images,
  onZoomImage,
  onUploadClick,
  className,
}: ChatRightSidebarProps) {
  // Ảnh đang được chọn hiển thị ở ô preview cuối sidebar
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);

  // Mặc định chọn ảnh mới nhất (ảnh cuối cùng trong mảng images)
  const activeImage =
    images.find((img) => img.id === selectedImageId) ||
    (images.length > 0 ? images[images.length - 1] : null);

  return (
    <>
      {/* Mobile backdrop overlay khi mở sidebar trên màn hình nhỏ */}
      <div
        className={cn(
          "fixed inset-0 bg-black/40 z-40 md:hidden transition-opacity duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      {/* Right Sidebar Container với transition trượt thu gọn / mở rộng mượt mà */}
      <aside
        className={cn(
          "fixed md:static inset-y-0 right-0 z-50 bg-[#FDF8F3] border-l border-[#C1762A]/20 flex flex-col h-full flex-shrink-0 shadow-lg md:shadow-none overflow-hidden",
          "transition-[width,transform,opacity] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
          isOpen
            ? "w-80 md:w-84 translate-x-0 opacity-100"
            : "w-0 md:w-0 translate-x-full md:translate-x-0 opacity-0 pointer-events-none border-l-0",
          className
        )}
      >
        {/* ── Top Header (Giống Zalo Thông tin hội thoại) ── */}
        <div className="p-4 border-b border-[#C1762A]/15 bg-white flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#F1CCA6]/60 flex items-center justify-center text-[#8C4905]">
              <ImageIcon size={18} />
            </div>
            <div>
              <h3 className="font-bold text-[#8C4905] text-sm">
                Ảnh bài tập & Đề bài
              </h3>
              <p className="text-[11px] text-[#C1762A] font-medium">
                {images.length > 0 ? `${images.length} ảnh trong buổi học` : "Chưa có ảnh đề bài"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-[#8C4905] hover:bg-[#F1CCA6]/40 rounded-lg transition-colors cursor-pointer"
            title="Đóng thanh bên phải"
            aria-label="Đóng thanh bên phải"
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Vùng cuộn ở giữa: Danh sách ảnh / Lời khuyên ── */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {images.length === 0 ? (
            /* Trạng thái chưa có ảnh nào */
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <div className="w-16 h-16 rounded-2xl bg-[#F1CCA6]/40 flex items-center justify-center text-[#C1762A] mb-3 shadow-inner">
                <ImageIcon size={28} />
              </div>
              <h4 className="font-bold text-[#8C4905] text-sm mb-1">
                Chưa có ảnh bài tập
              </h4>
              <p className="text-xs text-[#C1762A] leading-relaxed mb-4">
                Khi học sinh gửi ảnh đề bài toán, hình ảnh sẽ luôn xuất hiện ở đây để tiện vừa xem đề vừa học với AI.
              </p>
              {onUploadClick && (
                <button
                  onClick={onUploadClick}
                  className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#C1762A] hover:bg-[#8C4905] text-white text-xs font-semibold shadow-sm transition-all active:scale-95 cursor-pointer"
                >
                  <Plus size={15} />
                  Gửi ảnh đề bài ngay
                </button>
              )}
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-bold text-[#8C4905] uppercase tracking-wider">
                  Kho ảnh bài tập ({images.length})
                </h4>
                <span className="text-[11px] text-[#C1762A]">
                  Bấm để chọn
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {images.map((img, index) => {
                  const isSelected = activeImage?.id === img.id;
                  return (
                    <div
                      key={img.id}
                      onClick={() => setSelectedImageId(img.id)}
                      className={cn(
                        "relative aspect-square rounded-xl overflow-hidden cursor-pointer border-2 transition-all group",
                        isSelected
                          ? "border-[#8C4905] shadow-md ring-2 ring-[#C1762A]/40 scale-[1.02]"
                          : "border-transparent hover:border-[#C1762A]/60 opacity-80 hover:opacity-100"
                      )}
                      title={`Bài tập #${index + 1}`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={img.url}
                        alt={`Bài tập ${index + 1}`}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      />
                      <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/60 text-[9px] font-bold text-white">
                        #{index + 1}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── [YÊU CẦU ĐẶC BIỆT]: VỊ TRÍ CUỐI CÙNG SIDEBAR ẤY (GIỐNG ZALO) ── */}
        {/* Ảnh bài tập luôn hiện ở vị trí cuối cùng của thanh sidebar bên phải, kèm nút phóng to */}
        {activeImage && (
          <div className="p-4 border-t border-[#C1762A]/20 bg-white/80 backdrop-blur-sm">
            <div className="flex items-center justify-end mb-2">
              <button
                onClick={() => onZoomImage(activeImage.url)}
                className="text-xs font-semibold text-[#C1762A] hover:text-[#8C4905] flex items-center gap-1 transition-colors cursor-pointer"
                title="Phóng to ảnh xem toàn màn hình"
              >
                <Maximize2 size={13} />
                <span>Phóng to</span>
              </button>
            </div>

            {/* Container Ảnh bài tập ở vị trí cuối sidebar */}
            <div
              onClick={() => onZoomImage(activeImage.url)}
              className="relative group cursor-pointer overflow-hidden rounded-2xl border-2 border-[#C1762A]/40 shadow-md bg-black/5 hover:border-[#8C4905] transition-all"
              title="Bấm vào để phóng to hình ảnh bài tập"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={activeImage.url}
                alt="Đề bài tập đang giải"
                className="w-full h-44 object-contain bg-white/70 group-hover:scale-[1.02] transition-transform duration-200"
              />

              {/* Lớp phủ hover với nút phóng to */}
              <div className="absolute inset-0 bg-black/35 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 text-white">
                <div className="w-10 h-10 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center shadow-lg transform group-hover:scale-110 transition-transform">
                  <Maximize2 size={20} className="text-white" />
                </div>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-black/60 backdrop-blur-sm">
                  Bấm để phóng to
                </span>
              </div>
            </div>
          </div>
        )}
      </aside>
    </>
  );
}
