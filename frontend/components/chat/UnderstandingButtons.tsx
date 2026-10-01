/**
 * File: components/chat/UnderstandingButtons.tsx
 * Mô tả: Component hiển thị 2 nút "Đã hiểu" / "Chưa hiểu" sau mỗi câu trả lời của AI.
 *
 * Logic chính:
 * - notUnderstoodCount được quản lý ở ChatPage (không phải nội bộ) để tránh bị reset
 *   khi AI trả lời mới và component unmount/remount.
 * - Lần 1 nhấn "Chưa hiểu": AI sẽ giải thích lại theo cách khác (gọi callback onNotUnderstood).
 * - Lần 2 nhấn "Chưa hiểu": Chèn sẵn "Chưa hiểu: " vào ô nhập và focus con trỏ.
 * - Nút "Gửi" validate: nếu học sinh chưa gõ thêm gì thì chặn gửi.
 * - Nhấn "Đã hiểu" reset toàn bộ trạng thái và gọi callback onUnderstood.
 */
"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { CheckCircle2, HelpCircle, Send, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface UnderstandingButtonsProps {
  /** So lan nhan "Chua hieu" - quan ly o ChatPage de tranh bi reset khi remount */
  notUnderstoodCount: number;
  /** Goi khi hoc sinh nhan "Da hieu" */
  onUnderstood: () => void;
  /** Goi khi hoc sinh nhan "Chua hieu" (moi lan nhan) */
  onNotUnderstood: () => void;
  /** Goi khi hoc sinh giai thich ro phan chua hieu va nhan Gui */
  onSendExplanation: (text: string) => void;
  /** Disable cac nut khi AI dang xu ly */
  isLoading?: boolean;
}

export function UnderstandingButtons({
  notUnderstoodCount,
  onUnderstood,
  onNotUnderstood,
  onSendExplanation,
  isLoading = false,
}: UnderstandingButtonsProps) {
  // Noi dung o nhap (chi local state)
  const [inputValue, setInputValue] = useState("");
  // Thong bao loi validate
  const [validationError, setValidationError] = useState("");
  // Ref toi textarea de focus + auto-height
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Khi notUnderstoodCount chuyen sang 2, chen prefix va focus
  useEffect(() => {
    if (notUnderstoodCount === 2) {
      setInputValue("Chưa hiểu: ");
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.focus();
          const len = "Chưa hiểu: ".length;
          inputRef.current.setSelectionRange(len, len);
        }
      }, 0);
    } else if (notUnderstoodCount > 2) {
      // Lan 3+: chi focus lai o nhap
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    }
  }, [notUnderstoodCount]);

  // Tu dong dieu chinh chieu cao textarea theo noi dung
  useEffect(() => {
    const el = inputRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  // ----- Handler: Da hieu -----
  const handleUnderstood = () => {
    if (isLoading) return;
    setInputValue("");
    setValidationError("");
    onUnderstood();
  };

  // ----- Handler: Chua hieu -----
  const handleNotUnderstood = () => {
    if (isLoading) return;
    setValidationError("");
    onNotUnderstood(); // ChatPage se tang dem va xu ly logic
  };

  // ----- Handler: Gui giai thich -----
  const handleSend = () => {
    if (isLoading) return;
    const trimmed = inputValue.trim();

    // Validate khi dang o trang thai bat buoc giai thich (lan 2+)
    if (notUnderstoodCount >= 2) {
      if (trimmed === "Chưa hiểu:" || trimmed === "") {
        setValidationError("Vui lòng giải thích rõ hơn bạn chưa hiểu ở phần nào nhé!");
        inputRef.current?.focus();
        return;
      }
    } else if (!trimmed) {
      return;
    }

    setValidationError("");
    onSendExplanation(trimmed);
    setInputValue("");
  };

  // Nhan Enter de gui (Shift+Enter xuong dong)
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Hien o nhap khi da nhan Chua hieu >= 2 lan va chua den lan 5 (lan 5 AI tu xu ly)
  const showInput = notUnderstoodCount >= 2 && notUnderstoodCount < 5;
  const disableButtons = isLoading;

  return (
    <div className="flex flex-col gap-3 mt-1 animate-in fade-in duration-300">
      {/* ---- Khu vuc 2 nut chinh ---- */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Nut Da hieu */}
        <button
          id="btn-understood"
          onClick={handleUnderstood}
          disabled={disableButtons}
          className={cn(
            "inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border transition-all duration-200 shadow-sm",
            "border-emerald-500/40 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 hover:border-emerald-500 hover:scale-105 active:scale-95",
            disableButtons && "opacity-50 cursor-not-allowed hover:scale-100"
          )}
          title="Tôi đã hiểu bài"
        >
          <CheckCircle2 size={16} className="shrink-0" />
          Đã hiểu
        </button>

        {/* Nut Chua hieu */}
        <button
          id="btn-not-understood"
          onClick={handleNotUnderstood}
          disabled={disableButtons}
          className={cn(
            "inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold border transition-all duration-200 shadow-sm",
            notUnderstoodCount === 0
              ? "border-[#C1762A]/40 text-[#8C4905] bg-[#F1CCA6]/40 hover:bg-[#F1CCA6]/80 hover:border-[#C1762A] hover:scale-105 active:scale-95"
              : "border-amber-500/40 text-amber-700 bg-amber-50 hover:bg-amber-100 hover:border-amber-500 hover:scale-105 active:scale-95",
            disableButtons && "opacity-50 cursor-not-allowed hover:scale-100"
          )}
          title={
            notUnderstoodCount === 0
              ? "Tôi chưa hiểu, giải thích lại giúp mình"
              : `Đã nhấn ${notUnderstoodCount} lần – nhấn thêm để gõ câu hỏi`
          }
        >
          <HelpCircle size={16} className="shrink-0" />
          Chưa hiểu
          {/* Badge dem so lan nhan */}
          {notUnderstoodCount > 0 && (
            <span className="ml-0.5 bg-amber-500/20 text-amber-700 rounded-full px-1.5 py-0.5 text-[10px] font-bold leading-none">
              {notUnderstoodCount}
            </span>
          )}
        </button>

        {/* Nhan trang thai nho */}
        {notUnderstoodCount === 1 && !isLoading && (
          <span className="text-xs text-[#8C4905]/70 italic animate-in fade-in duration-200">
            AI đang giải thích lại theo cách khác…
          </span>
        )}
        {notUnderstoodCount >= 2 && notUnderstoodCount < 5 && (
          <span className="text-xs text-amber-700/80 italic animate-in fade-in duration-200">
            Hãy gõ phần bạn chưa hiểu bên dưới ↓
          </span>
        )}
        {notUnderstoodCount >= 5 && !isLoading && (
          <span className="text-xs text-red-700/80 italic animate-in fade-in duration-200">
            AI đang đưa ra đáp án chính xác…
          </span>
        )}
      </div>

      {/* ---- O nhap lieu (chi hien khi nhan Chua hieu >= 2 lan) ---- */}
      {showInput && (
        <div className="animate-in slide-in-from-top-2 fade-in duration-300 flex flex-col gap-1.5">
          <div
            className={cn(
              "relative flex items-end gap-2 bg-[#F1CCA6]/30 p-2 pl-4 pr-2 rounded-2xl border transition-all",
              validationError
                ? "border-red-400 bg-red-50/40 focus-within:border-red-500"
                : "border-[#C1762A]/30 focus-within:border-[#C1762A] focus-within:bg-white"
            )}
          >
            <textarea
              ref={inputRef}
              id="input-not-understood-explanation"
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                if (validationError) setValidationError("");
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ví dụ: Chưa hiểu: tại sao phải chuyển vế ở bước 2..."
              rows={1}
              className="flex-1 max-h-[120px] min-h-[40px] py-2.5 bg-transparent text-[#000000] placeholder:text-[#8C4905]/50 outline-none resize-none overflow-y-auto text-sm font-medium"
              disabled={isLoading}
            />
            {/* Nut Gui */}
            <button
              id="btn-send-explanation"
              onClick={handleSend}
              disabled={isLoading || !inputValue.trim()}
              title="Gửi câu hỏi của bạn"
              className={cn(
                "p-2 rounded-full flex items-center justify-center transition-all self-end mb-0.5 shadow-sm shrink-0",
                inputValue.trim() && !isLoading
                  ? "bg-[#C1762A] text-white hover:bg-[#8C4905] hover:scale-105 active:scale-95"
                  : "bg-[#D9D9D9] text-gray-400 cursor-not-allowed"
              )}
            >
              <Send size={16} className={cn(inputValue.trim() && "ml-0.5")} />
            </button>
          </div>

          {/* Thong bao loi validate */}
          {validationError && (
            <div className="flex items-center gap-1.5 px-1 animate-in fade-in slide-in-from-top-1 duration-200">
              <AlertTriangle size={13} className="text-red-500 shrink-0" />
              <span className="text-xs text-red-600 font-medium">{validationError}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
