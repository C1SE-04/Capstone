/**
 * File: components/chat/MathSymbolToolbar.tsx
 * Mô tả: Thanh công cụ ký hiệu toán học chuẩn Google Math Calculator (US 9.4 - Tasks T9.13 & T9.13b).
 * - Được tinh chỉnh phù hợp 100% với chương trình Toán học Lớp 4 - 9 (GDPT 2018):
 *   + Phân số ()/(), Căn bậc hai √(), Lũy thừa ^(), Giá trị tuyệt đối |()|
 *   + Dấu so sánh (≤, ≥, ≠), Ký hiệu hình học (độ °, delta Δ)
 *   + Bộ 4 tỉ số lượng giác lớp 9 (sin, cos, tan, cot)
 *   + Hằng số & Phép tính phổ biến (π, %, ±, ×, ÷, biến số x, y)
 *   + Giữ log() ở cuối để phục vụ kịch bản nghiệm thu Sprint [AC 9.4.2].
 */

"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MathSymbolItem {
  id: string;
  label: React.ReactNode;
  ariaLabel: string;
  template: string;
  cursorOffset: number;
  title?: string;
}

interface MathSymbolToolbarProps {
  onInsertSymbol: (template: string, cursorOffset: number, symbolId: string) => void;
  disabled?: boolean;
  className?: string;
}

export function MathSymbolToolbar({
  onInsertSymbol,
  disabled = false,
  className,
}: MathSymbolToolbarProps) {
  // Danh sách các ký hiệu toán học chuẩn hóa cho học sinh Lớp 4 - 9
  const MATH_SYMBOLS: MathSymbolItem[] = [
    {
      id: "fraction",
      ariaLabel: "Phân số",
      title: "Phân số: ()/() (Lớp 4 - 9)",
      template: "()/()",
      cursorOffset: 1, // Con trỏ nằm giữa cặp ngoặc đầu tiên: (|)/()
      label: (
        <div className="flex flex-col items-center justify-center gap-[3px] py-0.5">
          <div className="w-[14px] h-[10px] rounded-[3px] border-[1.8px] border-dashed border-[#8C4905]" />
          <div className="w-[18px] h-[2px] bg-[#8C4905] rounded-full" />
          <div className="w-[14px] h-[10px] rounded-[3px] border-[1.8px] border-dashed border-[#8C4905]" />
        </div>
      ),
    },
    {
      id: "sqrt",
      ariaLabel: "Căn bậc hai",
      title: "Căn bậc hai: √(x) (Lớp 7, 9)",
      template: "√()",
      cursorOffset: 2, // Con trỏ nằm giữa √(|)
      label: (
        <div className="flex items-center text-[#8C4905]">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M3 14 L6 14 L9 20 L13 5 L22 5" strokeLinecap="round" strokeLinejoin="round" />
            <rect x="13.5" y="8" width="8" height="8" rx="1.5" strokeDasharray="2 2" strokeWidth="1.8" />
          </svg>
        </div>
      ),
    },
    {
      id: "pow",
      ariaLabel: "Lũy thừa / Số mũ",
      title: "Lũy thừa: x^(y) (Lớp 6 - 9)",
      template: "^()",
      cursorOffset: 2, // Con trỏ nằm giữa ^(|)
      label: (
        <div className="flex items-start text-[#8C4905]">
          <div className="w-[15px] h-[15px] rounded-[3px] border-[1.8px] border-dashed border-[#8C4905] mt-1.5" />
          <div className="w-[9px] h-[9px] rounded-[2px] border-[1.5px] border-dashed border-[#8C4905] -ml-0.5" />
        </div>
      ),
    },
    {
      id: "abs",
      ariaLabel: "Giá trị tuyệt đối",
      title: "Giá trị tuyệt đối: |x| (Lớp 7 - 9)",
      template: "|()|",
      cursorOffset: 2, // Con trỏ nằm giữa |(|)|
      label: (
        <div className="flex items-center gap-[3px] text-[#8C4905] font-black">
          <span className="text-base leading-none">|</span>
          <div className="w-[12px] h-[14px] rounded-[3px] border-[1.8px] border-dashed border-[#8C4905]" />
          <span className="text-base leading-none">|</span>
        </div>
      ),
    },
    {
      id: "degree",
      label: <span className="text-lg font-bold">°</span>,
      ariaLabel: "Độ góc",
      template: "°",
      cursorOffset: 1,
      title: "Độ góc: ° (Ví dụ 30°, 60° - Lớp 6 - 9)",
    },
    {
      id: "percent",
      label: <span className="text-base font-bold">%</span>,
      ariaLabel: "Phần trăm",
      template: "%",
      cursorOffset: 1,
      title: "Tỉ số phần trăm: % (Lớp 5 - 9)",
    },
    {
      id: "le",
      label: <span className="text-lg font-bold">≤</span>,
      ariaLabel: "Nhỏ hơn hoặc bằng",
      template: "≤",
      cursorOffset: 1,
      title: "Nhỏ hơn hoặc bằng: ≤ (hoặc gõ <=)",
    },
    {
      id: "ge",
      label: <span className="text-lg font-bold">≥</span>,
      ariaLabel: "Lớn hơn hoặc bằng",
      template: "≥",
      cursorOffset: 1,
      title: "Lớn hơn hoặc bằng: ≥ (hoặc gõ >=)",
    },
    {
      id: "ne",
      label: <span className="text-lg font-bold">≠</span>,
      ariaLabel: "Khác",
      template: "≠",
      cursorOffset: 1,
      title: "Dấu khác: ≠ (hoặc gõ !=)",
    },
    {
      id: "pi",
      label: <span className="text-base font-bold font-serif">π</span>,
      ariaLabel: "Số Pi",
      template: "π",
      cursorOffset: 1,
      title: "Số Pi: π (Hình tròn Lớp 5, Lớp 9)",
    },
    {
      id: "pm",
      label: <span className="text-lg font-bold">±</span>,
      ariaLabel: "Cộng trừ",
      template: "±",
      cursorOffset: 1,
      title: "Cộng trừ: ± (Nghiệm x = ±3 - Lớp 7, 9)",
    },
    {
      id: "times",
      label: <span className="text-lg font-bold">×</span>,
      ariaLabel: "Dấu nhân",
      template: "×",
      cursorOffset: 1,
      title: "Phép nhân: ×",
    },
    {
      id: "divide",
      label: <span className="text-lg font-bold">÷</span>,
      ariaLabel: "Dấu chia",
      template: "÷",
      cursorOffset: 1,
      title: "Phép chia: ÷",
    },
    {
      id: "delta",
      label: <span className="text-base font-bold font-serif">Δ</span>,
      ariaLabel: "Delta",
      template: "Δ",
      cursorOffset: 1,
      title: "Delta / Tam giác: Δ (Lớp 8, 9)",
    },
    {
      id: "var_x",
      label: <span className="text-base font-bold italic font-serif">x</span>,
      ariaLabel: "Biến x",
      template: "x",
      cursorOffset: 1,
      title: "Biến số: x (Tìm x)",
    },
    {
      id: "var_y",
      label: <span className="text-base font-bold italic font-serif">y</span>,
      ariaLabel: "Biến y",
      template: "y",
      cursorOffset: 1,
      title: "Biến số: y (Hệ phương trình Lớp 9)",
    },
    {
      id: "sin",
      label: <span className="text-xs font-black font-mono tracking-tight">sin</span>,
      ariaLabel: "Hàm Sin",
      template: "sin()",
      cursorOffset: 4,
      title: "Lượng giác: sin(x) (Toán 9)",
    },
    {
      id: "cos",
      label: <span className="text-xs font-black font-mono tracking-tight">cos</span>,
      ariaLabel: "Hàm Cos",
      template: "cos()",
      cursorOffset: 4,
      title: "Lượng giác: cos(x) (Toán 9)",
    },
    {
      id: "tan",
      label: <span className="text-xs font-black font-mono tracking-tight">tan</span>,
      ariaLabel: "Hàm Tan",
      template: "tan()",
      cursorOffset: 4,
      title: "Lượng giác: tan(x) (Toán 9)",
    },
    {
      id: "cot",
      label: <span className="text-xs font-black font-mono tracking-tight">cot</span>,
      ariaLabel: "Hàm Cotang",
      template: "cot()",
      cursorOffset: 4,
      title: "Lượng giác: cot(x) (Toán 9)",
    },
    {
      id: "log",
      label: <span className="text-xs font-black font-mono tracking-tight">log</span>,
      ariaLabel: "Logarit",
      template: "log()",
      cursorOffset: 4, // Con trỏ nằm giữa log(|)
      title: "Logarit: log(x) (Phục vụ AC 9.4.2)",
    },
  ];

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Refs quản lý kéo chuột (Click & Drag to Scroll)
  const isMouseDownRef = useRef(false);
  const startXRef = useRef(0);
  const scrollLeftStartRef = useRef(0);
  const hasDraggedRef = useRef(false);

  const checkScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const { scrollLeft, scrollWidth, clientWidth } = el;
    setCanScrollLeft(scrollLeft > 6);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 6);
  }, []);

  useEffect(() => {
    checkScroll();
    const el = scrollContainerRef.current;
    if (!el) return;

    el.addEventListener("scroll", checkScroll, { passive: true });
    window.addEventListener("resize", checkScroll);
    return () => {
      el.removeEventListener("scroll", checkScroll);
      window.removeEventListener("resize", checkScroll);
    };
  }, [checkScroll]);

  const handleScroll = (direction: "left" | "right") => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const amount = direction === "left" ? -260 : 260;
    el.scrollBy({ left: amount, behavior: "smooth" });
  };

  // Hỗ trợ lăn chuột dọc thành cuộn ngang trên máy tính
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    const el = scrollContainerRef.current;
    if (!el) return;
    if (e.deltaY !== 0) {
      el.scrollLeft += e.deltaY * 0.9;
      checkScroll();
    }
  };

  // ── Xử lý nhấn giữ và kéo chuột để di chuyển trên máy tính (Drag to Scroll) ──

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = scrollContainerRef.current;
    if (!el) return;
    isMouseDownRef.current = true;
    hasDraggedRef.current = false;
    startXRef.current = e.pageX - el.offsetLeft;
    scrollLeftStartRef.current = el.scrollLeft;
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isMouseDownRef.current) return;
    const el = scrollContainerRef.current;
    if (!el) return;

    const x = e.pageX - el.offsetLeft;
    const walk = x - startXRef.current;

    if (Math.abs(walk) > 4) {
      hasDraggedRef.current = true;
      if (!isDragging) setIsDragging(true);
      el.scrollLeft = scrollLeftStartRef.current - walk;
      checkScroll();
    }
  };

  const handleMouseUpOrLeave = () => {
    isMouseDownRef.current = false;
    setIsDragging(false);
    // Giữ cờ hasDragged thêm 60ms để ngăn chặn sự kiện click nhầm vào nút vừa kéo
    setTimeout(() => {
      hasDraggedRef.current = false;
    }, 60);
  };

  const handleButtonClick = (
    e: React.MouseEvent<HTMLButtonElement>,
    item: MathSymbolItem
  ) => {
    e.preventDefault();
    // Nếu người dùng đang nhấn giữ kéo di chuyển thì KHÔNG bấm nút
    if (hasDraggedRef.current) return;
    if (disabled) return;
    onInsertSymbol(item.template, item.cursorOffset, item.id);
  };

  return (
    <div className={cn("relative w-full flex items-center group", className)}>
      {/* ── Nút cuộn sang trái (hiển thị khi có phần tử bị khuất bên trái) ── */}
      {canScrollLeft && (
        <button
          type="button"
          onClick={() => handleScroll("left")}
          aria-label="Cuộn sang trái"
          className={cn(
            "absolute -left-1 z-20 w-8 h-8 rounded-full bg-white/95 text-[#8C4905] border border-[#F1CCA6]",
            "shadow-md flex items-center justify-center transition-all duration-150 cursor-pointer",
            "hover:bg-[#F7ECE1] hover:scale-110 active:scale-95 animate-in fade-in duration-200"
          )}
        >
          <ChevronLeft className="w-5 h-5 stroke-[2.5]" />
        </button>
      )}

      {/* ── Dải thanh công cụ cuộn ngang (hỗ trợ nhấn giữ kéo chuột, lăn chuột, vuốt cảm ứng) ── */}
      <div
        ref={scrollContainerRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUpOrLeave}
        onMouseLeave={handleMouseUpOrLeave}
        className={cn(
          "flex items-center gap-2 overflow-x-auto touch-pan-x py-1 px-1 select-none w-full",
          "[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
          isDragging ? "cursor-grabbing scroll-auto" : "cursor-grab scroll-smooth"
        )}
        role="toolbar"
        aria-label="Thanh công cụ ký hiệu toán học"
      >
        <div className="flex items-center gap-2 shrink-0">
          {MATH_SYMBOLS.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              aria-label={item.ariaLabel}
              title={item.title}
              onMouseDown={(e) => {
                // Ngăn mất focus ô chat nhưng cho phép mousemove nổi bọt lên container
                e.preventDefault();
              }}
              onClick={(e) => handleButtonClick(e, item)}
              className={cn(
                "min-w-[44px] h-[44px] px-2 rounded-2xl flex items-center justify-center shrink-0",
                "bg-[#F7ECE1]/90 hover:bg-[#F1CCA6] text-[#8C4905] border border-[#F1CCA6] shadow-2xs",
                "transition-all duration-150 active:scale-95 font-semibold",
                "hover:shadow-xs hover:border-[#C1762A]/50",
                "disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100",
                isDragging ? "cursor-grabbing" : "cursor-pointer"
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Nút cuộn sang phải (hiển thị khi có phần tử bị khuất bên phải) ── */}
      {canScrollRight && (
        <button
          type="button"
          onClick={() => handleScroll("right")}
          aria-label="Cuộn sang phải"
          className={cn(
            "absolute -right-1 z-20 w-8 h-8 rounded-full bg-white/95 text-[#8C4905] border border-[#F1CCA6]",
            "shadow-md flex items-center justify-center transition-all duration-150 cursor-pointer",
            "hover:bg-[#F7ECE1] hover:scale-110 active:scale-95 animate-in fade-in duration-200"
          )}
        >
          <ChevronRight className="w-5 h-5 stroke-[2.5]" />
        </button>
      )}
    </div>
  );
}
