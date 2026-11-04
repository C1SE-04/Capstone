/**
 * File: components/chat/MathSymbolToolbar.tsx
 * Mô tả: Thanh công cụ ký hiệu toán học phổ biến lớp 4-9 (US 9.4 - Tasks T9.13 & T9.13b).
 * - Cung cấp các ký hiệu căn bậc hai, số mũ, phân số, pi, delta, dấu so sánh và lượng giác.
 * - Nhấn nút không làm mất focus ô textarea (e.preventDefault() trên cả onMouseDown & onClick).
 * - Chèn ký tự chính xác tại con trỏ chuột và tự động đưa con trỏ vào giữa cặp ngoặc.
 * - Chuẩn màu SocraticKid (#F7ECE1, #F1CCA6, #8C4905), phản hồi xúc giác active:scale-95.
 * - Tối ưu Mobile: touch-pan-x, overflow-x-auto, scrollbar ẩn, nút bấm 38px chuẩn chạm ngón tay.
 */

"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface MathSymbolItem {
  id: string;
  label: React.ReactNode;
  ariaLabel: string;
  template: string;
  cursorOffset: number;
  title?: string;
}

export const MATH_SYMBOLS: MathSymbolItem[] = [
  {
    id: "sqrt",
    label: (
      <span className="flex items-center text-sm font-bold tracking-tight">
        √<span className="italic text-xs ml-0.5">x</span>
      </span>
    ),
    ariaLabel: "Căn bậc hai",
    template: "√()",
    cursorOffset: 2, // Con trỏ nằm giữa hai dấu ngoặc √(|)
    title: "Căn bậc hai: √(x)",
  },
  {
    id: "pow2",
    label: (
      <span className="flex items-center text-sm font-bold">
        <span className="italic text-xs mr-0.5">x</span>²
      </span>
    ),
    ariaLabel: "Bình phương",
    template: "^2",
    cursorOffset: 2,
    title: "Bình phương: x^2",
  },
  {
    id: "powY",
    label: (
      <span className="flex items-center text-sm font-bold">
        <span className="italic text-xs mr-0.5">x</span>ʸ
      </span>
    ),
    ariaLabel: "Số mũ",
    template: "^()",
    cursorOffset: 2, // Con trỏ nằm giữa ^(|)
    title: "Lũy thừa: x^(y)",
  },
  {
    id: "frac",
    label: (
      <span className="flex items-center text-xs font-bold leading-none tracking-tight">
        <span className="italic">a</span>/<span className="italic">b</span>
      </span>
    ),
    ariaLabel: "Phân số",
    template: "()/()",
    cursorOffset: 1, // Con trỏ nằm giữa tử số (|)/()
    title: "Phân số: (tử)/(mẫu)",
  },
  {
    id: "pm",
    label: "±",
    ariaLabel: "Cộng trừ",
    template: "±",
    cursorOffset: 1,
    title: "Cộng trừ: ±",
  },
  {
    id: "pi",
    label: "π",
    ariaLabel: "Số Pi",
    template: "π",
    cursorOffset: 1,
    title: "Số Pi: π (~3.14)",
  },
  {
    id: "delta",
    label: "Δ",
    ariaLabel: "Delta",
    template: "Δ",
    cursorOffset: 1,
    title: "Delta: Δ",
  },
  {
    id: "le",
    label: "≤",
    ariaLabel: "Nhỏ hơn hoặc bằng",
    template: "≤",
    cursorOffset: 1,
    title: "Nhỏ hơn hoặc bằng: ≤",
  },
  {
    id: "ge",
    label: "≥",
    ariaLabel: "Lớn hơn hoặc bằng",
    template: "≥",
    cursorOffset: 1,
    title: "Lớn hơn hoặc bằng: ≥",
  },
  {
    id: "ne",
    label: "≠",
    ariaLabel: "Khác",
    template: "≠",
    cursorOffset: 1,
    title: "Khác: ≠",
  },
  {
    id: "times",
    label: "×",
    ariaLabel: "Dấu nhân",
    template: "×",
    cursorOffset: 1,
    title: "Phép nhân: ×",
  },
  {
    id: "divide",
    label: "÷",
    ariaLabel: "Dấu chia",
    template: "÷",
    cursorOffset: 1,
    title: "Phép chia: ÷",
  },
  {
    id: "log",
    label: <span className="text-xs font-bold font-mono">log</span>,
    ariaLabel: "Logarit",
    template: "log()",
    cursorOffset: 4, // Con trỏ nằm giữa log(|)
    title: "Logarit: log(x)",
  },
  {
    id: "sin",
    label: <span className="text-xs font-bold font-mono">sin</span>,
    ariaLabel: "Hàm Sin",
    template: "sin()",
    cursorOffset: 4, // Con trỏ nằm giữa sin(|)
    title: "Lượng giác: sin(x)",
  },
  {
    id: "cos",
    label: <span className="text-xs font-bold font-mono">cos</span>,
    ariaLabel: "Hàm Cos",
    template: "cos()",
    cursorOffset: 4, // Con trỏ nằm giữa cos(|)
    title: "Lượng giác: cos(x)",
  },
  {
    id: "tan",
    label: <span className="text-xs font-bold font-mono">tan</span>,
    ariaLabel: "Hàm Tan",
    template: "tan()",
    cursorOffset: 4, // Con trỏ nằm giữa tan(|)
    title: "Lượng giác: tan(x)",
  },
];

interface MathSymbolToolbarProps {
  onInsertSymbol: (template: string, cursorOffset: number) => void;
  disabled?: boolean;
  className?: string;
}

export function MathSymbolToolbar({
  onInsertSymbol,
  disabled = false,
  className,
}: MathSymbolToolbarProps) {
  const handleButtonClick = (
    e: React.MouseEvent<HTMLButtonElement>,
    item: MathSymbolItem
  ) => {
    // Ngăn chặn sự kiện làm mất focus (blur) khỏi ô textarea
    e.preventDefault();
    if (disabled) return;
    onInsertSymbol(item.template, item.cursorOffset);
  };

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 overflow-x-auto touch-pan-x py-1 px-1 scrollbar-none select-none",
        "[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
        className
      )}
      role="toolbar"
      aria-label="Thanh công cụ ký hiệu toán học"
    >
      <div className="flex items-center gap-1.5 shrink-0">
        {MATH_SYMBOLS.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={disabled}
            aria-label={item.ariaLabel}
            title={item.title}
            onMouseDown={(e) => {
              // Ngăn ngừa trình duyệt chuyển focus khỏi textarea khi nhấn chuột
              e.preventDefault();
            }}
            onClick={(e) => handleButtonClick(e, item)}
            className={cn(
              "min-w-[38px] h-[38px] px-2.5 rounded-xl flex items-center justify-center shrink-0",
              "bg-[#F7ECE1] hover:bg-[#F1CCA6] text-[#8C4905] border border-[#F1CCA6]/70 shadow-2xs",
              "transition-all duration-150 active:scale-95 cursor-pointer font-medium",
              "focus:outline-none focus:ring-2 focus:ring-[#C1762A]/50",
              "disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100"
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
