/**
 * File: components/chat/ChatInput.tsx
 * Mô tả: Component nhập liệu cho khung chat chuẩn Trình giải toán Google (Google Math Solver) (US 9.4).
 * Tính năng chính:
 * - Tích hợp MathLive Engine: Hỗ trợ tạo và lồng ghép biểu thức toán học không giới hạn
 *   (phân số trong phân số, căn trong phân số, số mũ của số mũ, logarit, trị tuyệt đối...).
 * - Hiển thị các ô vuông nét đứt (\placeholder{}) nhỏ gọn, tự động co giãn theo số nhập vào.
 * - Khi bấm nút Phân số: tự động tạo 2 ô tử & mẫu và con trỏ chuột focus ngay lập tức vào ô tử số.
 * - Hỗ trợ chèn căn bậc hai, số mũ, phân số lồng sâu vào bất kỳ ô nào đã nhập.
 * - Phím tắt điều hướng thông minh (Mũi tên lên/xuống/trái/phải, Tab, Backspace).
 * - Đính kèm ảnh (Camera/Library), xem trước, phóng to, giới hạn 5MB.
 * - Gửi tin nhắn bằng phím Enter (Shift+Enter để xuống dòng).
 */
"use client";

import React, {
  useRef,
  useEffect,
  useState,
  useCallback,
  ChangeEvent,
} from "react";
import {
  Send,
  Plus,
  X,
  Camera,
  ImageIcon,
  AlertCircle,
  Maximize2,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FileTooLargeToast } from "./FileTooLargeToast";
import { ImageZoomModal } from "./ImageZoomModal";
import { MathSymbolToolbar } from "./MathSymbolToolbar";

// ─── Types ───────────────────────────────────────────────────────────────────

interface ImageAttachment {
  previewUrl: string;
  file: File;
}

export interface ChatInputProps {
  onSendMessage: (message: string, image?: File) => void;
  isLoading?: boolean;
  isOffline?: boolean;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024;

// ─── Helper: Format LaTeX cho Chat & KaTeX ─────────────────────────────────────

function formatLatexForChat(latex: string): string {
  const trimmed = latex.trim();
  if (!trimmed) return "";

  // 1. Kiểm tra xem có chứa biểu thức toán học đặc biệt không (sau khi đã tách các thẻ \text)
  const withoutText = trimmed
    .replace(/\\text\{[^{}]*\}/g, "")
    .replace(/\\ /g, " ")
    .trim();
  const hasMath = /[\\^_{}√±×÷≤≥≠π]/.test(withoutText);

  // Nếu hoàn toàn không có công thức toán (văn bản thuần túy)
  if (!hasMath) {
    return trimmed
      .replace(/\\text\{([^}]*)\}/g, "$1")
      .replace(/\\ /g, " ")
      .trim();
  }

  // 2. Nếu là công thức thuần toán (không có thẻ \text{} nào)
  if (!trimmed.includes("\\text{")) {
    if (!trimmed.startsWith("$") && !trimmed.endsWith("$")) {
      return `$${trimmed}$`;
    }
    return trimmed;
  }

  // 3. Nếu là hỗn hợp giữa văn bản thường và công thức toán:
  // Ví dụ: \text{Chào thầy, tính giúp em }\frac{1}{2}\text{ với ạ}
  // Tách text thường giữ nguyên, công thức toán bọc trong $...$
  let result = "";
  let lastIndex = 0;
  const textRegex = /\\text\{([^{}]*)\}/g;
  let match: RegExpExecArray | null;

  while ((match = textRegex.exec(trimmed)) !== null) {
    const mathPart = trimmed.substring(lastIndex, match.index).trim();
    if (mathPart) {
      if (!mathPart.startsWith("$") && !mathPart.endsWith("$")) {
        result += ` $${mathPart}$ `;
      } else {
        result += ` ${mathPart} `;
      }
    }
    const textPart = match[1];
    result += textPart;
    lastIndex = textRegex.lastIndex;
  }

  const remainingMath = trimmed.substring(lastIndex).trim();
  if (remainingMath) {
    if (!remainingMath.startsWith("$") && !remainingMath.endsWith("$")) {
      result += ` $${remainingMath}$`;
    } else {
      result += ` ${remainingMath}`;
    }
  }

  return result.replace(/\s+/g, " ").trim();
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function ChatInput({
  onSendMessage,
  isLoading,
  isOffline = false,
}: ChatInputProps) {
  // ── State ──
  const [hasContent, setHasContent] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [attachment, setAttachment] = useState<ImageAttachment | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [fileTooLargeInfo, setFileTooLargeInfo] = useState<{
    isOpen: boolean;
    sizeMb: number;
    message?: string;
  }>({
    isOpen: false,
    sizeMb: 0,
  });

  // ── Refs ──
  const mathfieldRef = useRef<HTMLElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const libraryInputRef = useRef<HTMLInputElement>(null);
  const sheetContainerRef = useRef<HTMLDivElement>(null);

  // Khởi tạo MathLive trên Client
  useEffect(() => {
    setIsMounted(true);
    import("mathlive").then(() => {
      const mf = mathfieldRef.current as any;
      if (mf) {
        mf.mathVirtualKeyboardPolicy = "manual";
        mf.menuItems = [];
        mf.defaultMode = "text"; // Bật Text Mode làm mặc định để gõ chữ tiếng Việt tự nhiên và giữ đúng font của web

        const handleInput = () => {
          const val = mf.value || "";
          setHasContent(Boolean(val.trim().length > 0));
        };

        const handleKeyDown = (e: KeyboardEvent) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        };

        mf.addEventListener("input", handleInput);
        mf.addEventListener("keydown", handleKeyDown);

        return () => {
          mf.removeEventListener("input", handleInput);
          mf.removeEventListener("keydown", handleKeyDown);
        };
      }
    });
  }, []);

  // Lắng nghe phím Escape để đóng preview ảnh
  useEffect(() => {
    if (!isPreviewOpen) return;
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsPreviewOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isPreviewOpen]);

  // Image Attachment Helpers
  const attachImage = useCallback((file: File) => {
    setErrorMessage(null);
    if (!file.type.startsWith("image/")) {
      setErrorMessage("Vui lòng chỉ chọn định dạng file hình ảnh (PNG, JPG, WEBP...)");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      const sizeMb = file.size / (1024 * 1024);
      setFileTooLargeInfo({
        isOpen: true,
        sizeMb,
        message: `Ảnh bạn chọn có dung lượng ${sizeMb.toFixed(1)}MB, vượt quá giới hạn 5MB của hệ thống. Vui lòng chọn hoặc nén ảnh dưới 5MB nhé!`,
      });
      setErrorMessage(`Dung lượng ảnh (${sizeMb.toFixed(1)}MB) vượt quá giới hạn 5MB`);
      return;
    }
    setAttachment((prev) => {
      if (prev) URL.revokeObjectURL(prev.previewUrl);
      return { file, previewUrl: URL.createObjectURL(file) };
    });
  }, []);

  const removeAttachment = useCallback(() => {
    setErrorMessage(null);
    setIsPreviewOpen(false);
    setAttachment((prev) => {
      if (prev) URL.revokeObjectURL(prev.previewUrl);
      return null;
    });
  }, []);

  useEffect(() => {
    if (!errorMessage) return;
    const timer = setTimeout(() => setErrorMessage(null), 4000);
    return () => clearTimeout(timer);
  }, [errorMessage]);

  useEffect(() => {
    return () => {
      setAttachment((prev) => {
        if (prev) URL.revokeObjectURL(prev.previewUrl);
        return null;
      });
    };
  }, []);

  // Đóng Bottom Sheet khi click ra ngoài
  useEffect(() => {
    if (!isSheetOpen) return;
    const handleOutside = (e: MouseEvent) => {
      if (
        sheetContainerRef.current &&
        !sheetContainerRef.current.contains(e.target as Node)
      ) {
        setIsSheetOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, [isSheetOpen]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) attachImage(file);
    e.target.value = "";
    setIsSheetOpen(false);
  };

  const handlePlusClick = () => {
    const isMobile =
      typeof window !== "undefined" &&
      window.matchMedia("(max-width: 767px)").matches;
    if (isMobile) {
      setIsSheetOpen((prev) => !prev);
    } else {
      libraryInputRef.current?.click();
    }
  };

  // ── Xử lý chèn biểu thức toán học từ Toolbar (Hỗ trợ lồng ghép phân số, căn, mũ không giới hạn) ──

  const handleInsertMathSymbol = useCallback(
    (template: string, cursorOffset: number, symbolId: string) => {
      const mf = mathfieldRef.current as any;
      if (!mf) return;

      mf.focus();

      // Sử dụng lệnh insert với mode: "math" để chèn khối toán học vào văn bản
      const insertMath = (latex: string) => {
        if (typeof mf.insert === "function") {
          mf.insert(latex, { mode: "math", selectionMode: "placeholder" });
        } else if (typeof mf.executeCommand === "function") {
          mf.executeCommand(["insert", latex, { mode: "math", selectionMode: "placeholder" }]);
        }
      };

      switch (symbolId) {
        case "fraction":
          insertMath("\\frac{#?}{#?}");
          break;
        case "sqrt":
          insertMath("\\sqrt{#?}");
          break;
        case "pow":
          insertMath("#@^{#?}");
          break;
        case "abs":
          insertMath("\\left|#?\\right|");
          break;
        case "log":
          insertMath("\\log_{#?}(#?)");
          break;
        case "degree":
          insertMath("^{\\circ}");
          break;
        case "percent":
          insertMath("\\%");
          break;
        case "le":
          insertMath("\\le");
          break;
        case "ge":
          insertMath("\\ge");
          break;
        case "ne":
          insertMath("\\ne");
          break;
        case "pm":
          insertMath("\\pm");
          break;
        case "pi":
          insertMath("\\pi");
          break;
        case "times":
          insertMath("\\times");
          break;
        case "divide":
          insertMath("\\div");
          break;
        case "delta":
          insertMath("\\Delta");
          break;
        case "var_x":
          insertMath("x");
          break;
        case "var_y":
          insertMath("y");
          break;
        case "sin":
          insertMath("\\sin(#?)");
          break;
        case "cos":
          insertMath("\\cos(#?)");
          break;
        case "tan":
          insertMath("\\tan(#?)");
          break;
        case "cot":
          insertMath("\\cot(#?)");
          break;
        default:
          insertMath(template);
          break;
      }

      setHasContent(Boolean(mf.value && mf.value.trim().length > 0));
    },
    []
  );

  // ── Gửi tin nhắn ──

  const canSend =
    (hasContent || attachment !== null) &&
    !isLoading &&
    !isOffline;

  const handleSend = () => {
    const mf = mathfieldRef.current as any;
    const rawVal = mf?.value || "";
    const formatted = formatLatexForChat(rawVal);
    if (!formatted && !attachment) return;

    onSendMessage(formatted, attachment?.file);
    if (mf) {
      mf.value = "";
    }
    setHasContent(false);
    removeAttachment();
  };

  return (
    <div className="p-2 sm:p-4 bg-transparent mt-auto relative z-10 w-full">
      {/* Cảnh báo lỗi tải ảnh */}
      {errorMessage && (
        <div className="mb-2 ml-1 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-200">
          <AlertCircle size={14} className="shrink-0 text-red-500" />
          <span className="font-medium">{errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            className="ml-1 text-red-400 hover:text-red-700 transition-colors cursor-pointer"
            aria-label="Đóng thông báo lỗi"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* Thumbnail Preview khi có ảnh đính kèm */}
      {attachment && (
        <div className="mb-2 ml-1 flex items-start gap-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="relative group inline-block">
            <div
              onClick={() => setIsPreviewOpen(true)}
              className="relative cursor-pointer overflow-hidden rounded-xl group/thumb"
              title="Bấm để xem ảnh phóng to"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={attachment.previewUrl}
                alt="Ảnh đính kèm"
                className="h-20 w-20 object-cover rounded-xl border-2 border-[#C1762A]/30 shadow-md group-hover/thumb:brightness-95 transition-all"
              />
              <div className="absolute inset-0 bg-black/0 group-hover/thumb:bg-black/25 rounded-xl transition-all flex items-center justify-center opacity-0 group-hover/thumb:opacity-100">
                <Maximize2 size={16} className="text-white drop-shadow" />
              </div>
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                removeAttachment();
              }}
              aria-label="Xóa ảnh đính kèm"
              className={[
                "absolute -top-2 -right-2 w-5 h-5 z-10",
                "bg-[#8C4905] text-white rounded-full",
                "flex items-center justify-center shadow-md",
                "opacity-0 group-hover:opacity-100 focus:opacity-100",
                "transition-opacity duration-150 hover:bg-red-600 cursor-pointer",
              ].join(" ")}
            >
              <X size={11} strokeWidth={3} />
            </button>
          </div>
          <div className="flex flex-col mt-1 min-w-0">
            <span className="text-xs text-[#8C4905] font-medium truncate max-w-[180px]">
              {attachment.file.name}
            </span>
            <span className="text-[11px] text-[#8C4905]/60">
              {attachment.file.size < 1024 * 1024
                ? `${(attachment.file.size / 1024).toFixed(1)} KB`
                : `${(attachment.file.size / (1024 * 1024)).toFixed(2)} MB`}
            </span>
          </div>
        </div>
      )}

      {/* Thông báo nổi khi dung lượng ảnh vượt quá 5MB */}
      <FileTooLargeToast
        isOpen={fileTooLargeInfo.isOpen}
        fileSizeMb={fileTooLargeInfo.sizeMb}
        message={fileTooLargeInfo.message}
        onClose={() => setFileTooLargeInfo((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* Modal xem ảnh phóng to */}
      <ImageZoomModal
        isOpen={isPreviewOpen}
        imageUrl={attachment?.previewUrl || null}
        imageTitle={`Ảnh đính kèm: ${attachment?.file.name || "Bài tập"}`}
        onClose={() => setIsPreviewOpen(false)}
      />

      {/* Style ẩn nút bàn phím và nút menu mặc định của MathLive & set font chuẩn cho text thường */}
      <style>{`
        math-field::part(virtual-keyboard-toggle),
        math-field::part(menu-toggle) {
          display: none !important;
        }
        math-field {
          --text-font-family: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
          font-family: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        math-field::part(content) {
          font-family: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
      `}</style>

      {/* ── [US 9.4] MathSymbolToolbar: Chuẩn Google Math Calculator ── */}
      <div className="mb-2 px-0.5">
        <MathSymbolToolbar
          onInsertSymbol={handleInsertMathSymbol}
          disabled={isLoading || isOffline}
        />
      </div>

      {/* ── Vùng background bo góc chứa các nút và ô nhập liệu Trình giải toán Google (MathLive) ── */}
      <div
        className={cn(
          "relative flex items-center gap-2 bg-[#F1CCA6]/40 p-2 pl-3 pr-2 rounded-3xl border border-[#C1762A]/20 shadow-sm focus-within:border-[#C1762A] focus-within:bg-white transition-all",
          isOffline && "opacity-75 bg-[#F7ECE1] border-[#F1CCA6]"
        )}
      >
        {/* Nút + và Mobile Bottom Sheet */}
        <div className="relative shrink-0 self-center" ref={sheetContainerRef}>
          <button
            id="chat-attach-btn"
            onClick={handlePlusClick}
            disabled={isOffline}
            aria-label="Đính kèm ảnh"
            aria-expanded={isSheetOpen}
            className={cn(
              "p-2.5 text-[#8C4905] hover:bg-[#F1CCA6] rounded-full transition-all duration-150 cursor-pointer",
              "disabled:opacity-40 disabled:cursor-not-allowed",
              isSheetOpen && "bg-[#F1CCA6] rotate-45"
            )}
          >
            <Plus size={20} />
          </button>

          {/* Mobile Bottom Sheet */}
          {isSheetOpen && (
            <>
              <div
                className="fixed inset-0 bg-black/20 z-30 md:hidden"
                onClick={() => setIsSheetOpen(false)}
                aria-hidden="true"
              />

              <div
                role="dialog"
                aria-label="Chọn nguồn ảnh"
                className={cn(
                  "fixed bottom-0 left-0 right-0 z-40 md:hidden",
                  "bg-white rounded-t-2xl shadow-2xl border-t border-[#C1762A]/10",
                  "animate-in slide-in-from-bottom duration-250 ease-out"
                )}
              >
                <div className="flex justify-center pt-3 pb-1">
                  <div className="w-10 h-1 bg-[#F1CCA6] rounded-full" />
                </div>
                <p className="text-center text-sm font-semibold text-[#8C4905] pb-3">
                  Thêm ảnh
                </p>
                <div className="flex gap-3 px-6 pb-8 pt-1">
                  <button
                    id="chat-attach-camera-btn"
                    onClick={() => cameraInputRef.current?.click()}
                    className="flex-1 flex flex-col items-center gap-2.5 py-5 px-4 rounded-2xl border-2 border-[#C1762A]/20 hover:border-[#C1762A]/60 hover:bg-[#F1CCA6]/30 transition-all active:scale-95 cursor-pointer"
                  >
                    <div className="w-12 h-12 rounded-full bg-[#F1CCA6] flex items-center justify-center">
                      <Camera size={22} className="text-[#8C4905]" />
                    </div>
                    <span className="text-sm font-medium text-[#8C4905]">
                      Camera
                    </span>
                  </button>

                  <button
                    id="chat-attach-library-btn"
                    onClick={() => libraryInputRef.current?.click()}
                    className="flex-1 flex flex-col items-center gap-2.5 py-5 px-4 rounded-2xl border-2 border-[#C1762A]/20 hover:border-[#C1762A]/60 hover:bg-[#F1CCA6]/30 transition-all active:scale-95 cursor-pointer"
                  >
                    <div className="w-12 h-12 rounded-full bg-[#F1CCA6] flex items-center justify-center">
                      <ImageIcon size={22} className="text-[#8C4905]" />
                    </div>
                    <span className="text-sm font-medium text-[#8C4905]">
                      Thư viện
                    </span>
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Hidden File Inputs */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleFileChange}
          aria-hidden="true"
          tabIndex={-1}
        />
        <input
          ref={libraryInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
          aria-hidden="true"
          tabIndex={-1}
        />

        {/* ── MathLive MathField Container ── */}
        <div className="relative flex-1 flex items-center min-h-[44px] max-h-[160px] overflow-y-auto px-1 py-1">
          {/* Placeholder tự nhiên khi khung nhập rỗng */}
          {!hasContent && (
            <div
              onClick={() => (mathfieldRef.current as any)?.focus()}
              className="absolute left-1 top-1/2 -translate-y-1/2 text-[#8C4905]/50 pointer-events-none text-xs sm:text-sm font-medium truncate select-none"
            >
              {isOffline
                ? "Mất kết nối. Đang chờ kết nối lại..."
                : "Hỏi SocraticKid (gõ văn bản thường, bấm phân số, căn trên thanh công cụ)..."}
            </div>
          )}

          {isMounted ? (
            React.createElement("math-field", {
              ref: mathfieldRef,
              "math-virtual-keyboard-policy": "manual",
              "default-mode": "text",
              class: "w-full outline-none border-none bg-transparent text-[#1C1917] font-normal text-base py-1 leading-normal",
              style: {
                "--primary-color": "#C1762A",
                "--caret-color": "#8C4905",
                "--selection-background-color": "#F1CCA6",
                "--placeholder-color": "#8C4905",
                "--placeholder-opacity": "0.75",
                "--text-font-family": "var(--font-geist-sans), -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                fontFamily: "var(--font-geist-sans), -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                display: "block",
                minHeight: "36px",
              } as React.CSSProperties,
            })
          ) : (
            <div className="w-full min-h-[36px]" />
          )}
        </div>

        {/* ── Cặp Chevron chuẩn Google Math Solver (ở góc phải khung nhập) ── */}
        <div className="hidden sm:flex flex-col items-center justify-center text-[#8C4905]/40 select-none shrink-0 self-center px-1">
          <ChevronUp className="w-3.5 h-3.5 -mb-1 stroke-[2.5]" />
          <ChevronDown className="w-3.5 h-3.5 stroke-[2.5]" />
        </div>

        {/* Nút Gửi */}
        <button
          id="chat-send-btn"
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            "p-2.5 rounded-full flex items-center justify-center transition-all self-center shadow-sm shrink-0",
            canSend
              ? "bg-[#C1762A] text-white hover:bg-[#8C4905] hover:scale-105 active:scale-95 cursor-pointer"
              : "bg-[#F1CCA6]/40 text-[#8C4905]/40 cursor-not-allowed"
          )}
          title={isOffline ? "Không thể gửi khi mất kết nối" : "Gửi tin nhắn"}
        >
          <Send size={20} className={cn(canSend && !isOffline && "ml-0.5")} />
        </button>
      </div>

      {/* Cảnh báo nhẹ dưới ô nhập liệu */}
      <div className="text-center mt-2">
        <p className="text-xs text-[#8C4905]/60">
          AI có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.
        </p>
      </div>
    </div>
  );
}
