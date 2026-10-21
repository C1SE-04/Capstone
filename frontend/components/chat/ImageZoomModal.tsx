"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  X,
  ZoomIn,
  ZoomOut,
  RotateCw,
  RefreshCw,
  Maximize2,
  Download,
} from "lucide-react";

interface ImageZoomModalProps {
  isOpen: boolean;
  imageUrl: string | null;
  imageTitle?: string;
  onClose: () => void;
}

export function ImageZoomModal({
  isOpen,
  imageUrl,
  imageTitle = "Ảnh bài tập đã chọn",
  onClose,
}: ImageZoomModalProps) {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Reset transform khi mở ảnh mới hoặc đổi ảnh
  useEffect(() => {
    if (isOpen) {
      setScale(1);
      setRotation(0);
      setPosition({ x: 0, y: 0 });
    }
  }, [isOpen, imageUrl]);

  // Điều khiển phóng to / thu nhỏ
  const handleZoomIn = useCallback(() => {
    setScale((prev) => Math.min(prev + 0.25, 4));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale((prev) => {
      const next = Math.max(prev - 0.25, 0.5);
      if (next <= 1) setPosition({ x: 0, y: 0 });
      return next;
    });
  }, []);

  const handleReset = useCallback(() => {
    setScale(1);
    setRotation(0);
    setPosition({ x: 0, y: 0 });
  }, []);

  const handleRotate = useCallback(() => {
    setRotation((prev) => (prev + 90) % 360);
  }, []);

  // Lắng nghe phím tắt và ngăn cuộn trang
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "+" || e.key === "=") {
        handleZoomIn();
      } else if (e.key === "-") {
        handleZoomOut();
      } else if (e.key === "0") {
        handleReset();
      } else if (e.key.toLowerCase() === "r") {
        handleRotate();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, onClose, handleZoomIn, handleZoomOut, handleReset, handleRotate]);

  // Xử lý kéo thả ảnh khi đã zoom > 1
  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale <= 1) return;
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || scale <= 1) return;
    setPosition({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Hỗ trợ cuộn chuột để zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.stopPropagation();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  };

  if (!isOpen || !imageUrl || !isMounted) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[99999] flex flex-col items-center justify-between bg-black/90 backdrop-blur-md select-none animate-in fade-in duration-200"
      onClick={onClose}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      role="dialog"
      aria-modal="true"
      aria-label="Xem ảnh bài tập phóng to"
    >
      {/* Thanh điều khiển trên cùng (Header toolbar) */}
      <div
        className="w-full flex items-center justify-between px-4 md:px-6 py-3.5 bg-gradient-to-b from-black/80 to-transparent text-white z-20"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Tiêu đề & tỷ lệ zoom */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center text-[#F1CCA6]">
            <Maximize2 size={16} />
          </div>
          <div>
            <h3 className="text-sm md:text-base font-semibold text-white/95 truncate max-w-[200px] sm:max-w-md">
              {imageTitle}
            </h3>
            <p className="text-xs text-white/60">
              Tỷ lệ: {Math.round(scale * 100)}% {rotation !== 0 ? `• Xoay ${rotation}°` : ""}
            </p>
          </div>
        </div>

        {/* Cụm công cụ Zoom & Xoay */}
        <div className="flex items-center gap-1 sm:gap-2">
          {/* Nút Thu nhỏ */}
          <button
            onClick={handleZoomOut}
            disabled={scale <= 0.5}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-white cursor-pointer"
            title="Thu nhỏ (-)"
            aria-label="Thu nhỏ"
          >
            <ZoomOut size={18} />
          </button>

          {/* Reset tỉ lệ */}
          <button
            onClick={handleReset}
            className="px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 transition-all text-xs font-semibold text-white cursor-pointer"
            title="Đặt lại (Phím 0)"
            aria-label="Đặt lại kích thước"
          >
            100%
          </button>

          {/* Nút Phóng to */}
          <button
            onClick={handleZoomIn}
            disabled={scale >= 4}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-white cursor-pointer"
            title="Phóng to (+)"
            aria-label="Phóng to"
          >
            <ZoomIn size={18} />
          </button>

          {/* Nút Xoay ảnh */}
          <button
            onClick={handleRotate}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition-all text-white cursor-pointer ml-1"
            title="Xoay 90° (Phím R)"
            aria-label="Xoay ảnh"
          >
            <RotateCw size={18} />
          </button>

          {/* Nút Mở tab mới / tải ảnh */}
          <a
            href={imageUrl}
            target="_blank"
            rel="noopener noreferrer"
            download="bai-tap-socratickid.jpg"
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition-all text-white cursor-pointer"
            title="Mở ảnh gốc trong tab mới"
            aria-label="Mở ảnh gốc"
          >
            <Download size={18} />
          </a>

          {/* Nút Đóng */}
          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-red-500/80 hover:bg-red-600 transition-all text-white cursor-pointer ml-2 shadow-lg"
            title="Đóng (Esc)"
            aria-label="Đóng xem ảnh"
          >
            <X size={19} />
          </button>
        </div>
      </div>

      {/* Vùng hiển thị ảnh chính */}
      <div
        className="flex-1 w-full flex items-center justify-center overflow-hidden p-4 relative"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        style={{
          cursor: scale > 1 ? (isDragging ? "grabbing" : "grab") : "default",
        }}
      >
        <div
          className="relative transition-transform duration-100 ease-out flex items-center justify-center max-w-[95vw] max-h-[85vh]"
          style={{
            transform: `translate(${position.x}px, ${position.y}px) scale(${scale}) rotate(${rotation}deg)`,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt="Ảnh bài tập phóng to"
            draggable={false}
            className="max-h-[80vh] max-w-[90vw] object-contain rounded-xl shadow-2xl border border-white/20 select-none pointer-events-auto"
          />
        </div>
      </div>

      {/* Chú thích gợi ý dưới đáy */}
      <div
        className="w-full py-2.5 px-4 text-center text-xs text-white/50 bg-gradient-to-t from-black/80 to-transparent z-20 flex items-center justify-center gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <span>Cuộn chuột hoặc bấm +/- để phóng to/thu nhỏ</span>
        <span>•</span>
        <span>Kéo chuột để di chuyển ảnh</span>
        <span>•</span>
        <span>Nhấn Esc để đóng</span>
      </div>
    </div>,
    document.body
  );
}
