/**
 * File: components/chat/MathSymbolToolbar.tsx
 * Mô tả: Thanh công cụ ký hiệu toán học chuẩn Google Math Calculator (US 9.4 - Tasks T9.13 & T9.13b).
 * - Biểu tượng trực quan nét đứt giống máy tính Google (phân số, căn, số mũ, trị tuyệt đối, log).
 * - Popup 2 ô nhập phân số trực quan (Tử số / Mẫu số) chèn chuẩn \frac{a}{b}.
 * - Nút bấm lớn 44px công thái học, dễ chạm và phản hồi xúc giác mượt mà trên mobile.
 * - Nhấn nút không làm mất focus ô textarea.
 */

"use client";

import React, { useState, useRef, useEffect } from "react";
import { X, Check, CornerDownLeft } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MathSymbolItem {
  id: string;
  label: React.ReactNode;
  ariaLabel: string;
  template: string;
  cursorOffset: number;
  title?: string;
  isCustomAction?: boolean;
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
  // State điều khiển popover 2 ô nhập phân số phong cách Google Math Calculator
  const [isFractionOpen, setIsFractionOpen] = useState(false);
  const [numerator, setNumerator] = useState("");
  const [denominator, setDenominator] = useState("");
  const numInputRef = useRef<HTMLInputElement>(null);
  const denInputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Tự động focus vào ô tử số khi mở popover
  useEffect(() => {
    if (isFractionOpen) {
      setTimeout(() => {
        numInputRef.current?.focus();
      }, 50);
    } else {
      setNumerator("");
      setDenominator("");
    }
  }, [isFractionOpen]);

  // Đóng popover khi click ra ngoài
  useEffect(() => {
    if (!isFractionOpen) return;
    const handleOutsideClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsFractionOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isFractionOpen]);

  // Xử lý xác nhận chèn phân số
  const handleConfirmFraction = () => {
    const num = numerator.trim() || "1";
    const den = denominator.trim() || "2";
    // Định dạng \frac{a}{b} chuẩn xác cho máy tính và AI
    const fractionCode = `\\frac{${num}}{${den}}`;
    onInsertSymbol(fractionCode, fractionCode.length);
    setIsFractionOpen(false);
  };

  // Danh sách các ký hiệu phong cách máy tính toán học Google
  const MATH_SYMBOLS: MathSymbolItem[] = [
    {
      id: "fraction",
      ariaLabel: "Phân số",
      title: "Phân số: 2 ô nhập tử số và mẫu số",
      isCustomAction: true,
      template: "()/()",
      cursorOffset: 1,
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
      cursorOffset: 2,
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
      cursorOffset: 2,
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
      cursorOffset: 2,
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
      cursorOffset: 4,
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

    if (item.isCustomAction && item.id === "fraction") {
      setIsFractionOpen((prev) => !prev);
      return;
    }

    onInsertSymbol(item.template, item.cursorOffset);
  };

  return (
    <div className={cn("relative w-full", className)}>
      {/* ── Popover 2 ô nhập phân số phong cách Google Math Calculator ── */}
      {isFractionOpen && (
        <div
          ref={popoverRef}
          className="absolute bottom-full left-0 mb-3 z-30 bg-white/95 backdrop-blur-md rounded-2xl p-3 border-2 border-[#C1762A] shadow-xl animate-in zoom-in-95 duration-150 flex flex-col gap-2 min-w-[210px]"
        >
          <div className="flex items-center justify-between border-b border-[#F1CCA6] pb-1.5">
            <span className="text-xs font-extrabold text-[#8C4905] flex items-center gap-1.5">
              <span>Nhập phân số</span>
              <span className="text-[10px] font-semibold text-[#C1762A] bg-[#F7ECE1] px-1.5 py-0.2 rounded font-mono">
                a/b
              </span>
            </span>
            <button
              onClick={() => setIsFractionOpen(false)}
              className="text-stone-400 hover:text-stone-700 p-0.5 rounded-lg transition-colors cursor-pointer"
            >
              <X size={14} />
            </button>
          </div>

          {/* Khung 2 ô nhập mô phỏng trực quan phân số */}
          <div className="flex items-center justify-center gap-3 py-1.5">
            <div className="flex flex-col items-center gap-1.5">
              {/* Ô Tử Số */}
              <input
                ref={numInputRef}
                type="text"
                value={numerator}
                onChange={(e) => setNumerator(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === "ArrowDown") {
                    e.preventDefault();
                    denInputRef.current?.focus();
                  }
                }}
                placeholder="Tử số"
                className="w-20 h-9 text-center font-bold text-sm bg-[#F7ECE1]/60 text-[#8C4905] border-2 border-dashed border-[#C1762A] rounded-xl focus:outline-none focus:bg-white focus:border-solid transition-all placeholder:text-[#8C4905]/40"
              />

              {/* Đường kẻ ngang phân số */}
              <div className="w-24 h-[2.5px] bg-[#8C4905] rounded-full" />

              {/* Ô Mẫu Số */}
              <input
                ref={denInputRef}
                type="text"
                value={denominator}
                onChange={(e) => setDenominator(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleConfirmFraction();
                  } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    numInputRef.current?.focus();
                  }
                }}
                placeholder="Mẫu số"
                className="w-20 h-9 text-center font-bold text-sm bg-[#F7ECE1]/60 text-[#8C4905] border-2 border-dashed border-[#C1762A] rounded-xl focus:outline-none focus:bg-white focus:border-solid transition-all placeholder:text-[#8C4905]/40"
              />
            </div>

            {/* Nút Chèn nhanh */}
            <button
              onClick={handleConfirmFraction}
              className="h-20 px-3 rounded-xl bg-gradient-to-b from-[#C1762A] to-[#8C4905] text-white flex flex-col items-center justify-center gap-1 font-bold text-xs shadow-md hover:brightness-105 active:scale-95 transition-all cursor-pointer"
              title="Chèn phân số vào ô chat (Enter)"
            >
              <Check size={18} strokeWidth={3} />
              <span>Chèn</span>
            </button>
          </div>
          <p className="text-[10px] text-stone-500 text-center">
            Mẹo: Nhấn <strong>Enter</strong> để chuyển giữa tử và mẫu số
          </p>
        </div>
      )}

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
                "disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100",
                item.id === "fraction" && isFractionOpen && "bg-[#F1CCA6] border-[#C1762A] ring-2 ring-[#C1762A]/30"
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
