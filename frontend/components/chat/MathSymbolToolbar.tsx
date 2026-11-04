/**
 * File: components/chat/MathSymbolToolbar.tsx
 * Mô tả: Thanh công cụ ký hiệu toán học chuẩn Google Math Calculator (US 9.4 - Tasks T9.13 & T9.13b).
 * - Biểu tượng trực quan nét đứt giống máy tính Google (phân số, căn, số mũ, trị tuyệt đối, log).
 * - Bấm nút phân số sẽ chèn ()/() với con trỏ nằm ngay giữa cặp ngoặc đầu tiên (|)/().
 * - Nút bấm lớn 44px công thái học, dễ chạm và phản hồi xúc giác mượt mà trên mobile.
 * - Nhấn nút không làm mất focus ô nhập liệu.
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
  // Danh sách các ký hiệu phong cách máy tính toán học Google
  const MATH_SYMBOLS: MathSymbolItem[] = [
    {
      id: "fraction",
      ariaLabel: "Phân số",
      title: "Phân số: ()/()",
      template: "()/()",
      cursorOffset: 1, // Con trỏ nằm giữa cặp ngoặc đầu tiên: (|)/()
      // Icon 2 ô nét đứt xếp chồng có vạch ngang y hệt Google Calculator
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
      title: "Căn bậc hai: √(x)",
      template: "√()",
      cursorOffset: 2, // Con trỏ nằm giữa √(|)
      // Icon căn bậc hai với ô nét đứt bên trong
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
      title: "Lũy thừa: x^(y)",
      template: "^()",
      cursorOffset: 2, // Con trỏ nằm giữa ^(|)
      // Icon cơ số với ô số mũ nhỏ nét đứt phía trên bên phải
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
      title: "Giá trị tuyệt đối: |x|",
      template: "|()|",
      cursorOffset: 2, // Con trỏ nằm giữa |(|)|
      // Icon trị tuyệt đối hai vạch thẳng bọc ô nét đứt
      label: (
        <div className="flex items-center gap-[3px] text-[#8C4905] font-black">
          <span className="text-base leading-none">|</span>
          <div className="w-[12px] h-[14px] rounded-[3px] border-[1.8px] border-dashed border-[#8C4905]" />
          <span className="text-base leading-none">|</span>
        </div>
      ),
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
      title: "Số Pi: π",
    },
    {
      id: "pm",
      label: <span className="text-lg font-bold">±</span>,
      ariaLabel: "Cộng trừ",
      template: "±",
      cursorOffset: 1,
      title: "Cộng trừ: ± (hoặc gõ +-)",
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
      title: "Delta: Δ",
    },
    {
      id: "var_x",
      label: <span className="text-base font-bold italic font-serif">x</span>,
      ariaLabel: "Biến x",
      template: "x",
      cursorOffset: 1,
      title: "Biến số: x",
    },
    {
      id: "var_y",
      label: <span className="text-base font-bold italic font-serif">y</span>,
      ariaLabel: "Biến y",
      template: "y",
      cursorOffset: 1,
      title: "Biến số: y",
    },
    {
      id: "log",
      label: <span className="text-xs font-black font-mono tracking-tight">log</span>,
      ariaLabel: "Logarit",
      template: "log()",
      cursorOffset: 4, // Con trỏ nằm giữa log(|)
      title: "Logarit: log(x)",
    },
    {
      id: "sin",
      label: <span className="text-xs font-black font-mono tracking-tight">sin</span>,
      ariaLabel: "Hàm Sin",
      template: "sin()",
      cursorOffset: 4,
      title: "Lượng giác: sin(x)",
    },
    {
      id: "cos",
      label: <span className="text-xs font-black font-mono tracking-tight">cos</span>,
      ariaLabel: "Hàm Cos",
      template: "cos()",
      cursorOffset: 4,
      title: "Lượng giác: cos(x)",
    },
    {
      id: "tan",
      label: <span className="text-xs font-black font-mono tracking-tight">tan</span>,
      ariaLabel: "Hàm Tan",
      template: "tan()",
      cursorOffset: 4,
      title: "Lượng giác: tan(x)",
    },
  ];

  const handleButtonClick = (
    e: React.MouseEvent<HTMLButtonElement>,
    item: MathSymbolItem
  ) => {
    e.preventDefault();
    if (disabled) return;
    onInsertSymbol(item.template, item.cursorOffset);
  };

  return (
    <div className={cn("relative w-full", className)}>
      {/* ── Dải thanh công cụ cuộn ngang trên mobile ── */}
      <div
        className={cn(
          "flex items-center gap-2 overflow-x-auto touch-pan-x py-1 px-0.5 scrollbar-none select-none",
          "[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
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
                // Ngăn mất focus ô chat
                e.preventDefault();
              }}
              onClick={(e) => handleButtonClick(e, item)}
              className={cn(
                "min-w-[44px] h-[44px] px-2 rounded-2xl flex items-center justify-center shrink-0",
                "bg-[#F7ECE1]/90 hover:bg-[#F1CCA6] text-[#8C4905] border border-[#F1CCA6] shadow-2xs",
                "transition-all duration-150 active:scale-95 cursor-pointer font-semibold",
                "hover:shadow-xs hover:border-[#C1762A]/50",
                "disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100"
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
