/**
 * File: components/chat/ChatInput.tsx
 * Mô tả: Component nhập liệu cho khung chat học sinh (SocraticKid) tích hợp MathLive chuẩn Google Math Solver (Cách 3).
 * Tính năng chính:
 * - Can thiệp sâu vào Shadow DOM & cấu hình MathLive để giữ 100% Font chuẩn Sans-serif (Geist Sans) đứng thẳng.
 * - Triệt tiêu lỗi font chữ có chân (serif), in nghiêng, và hiện tượng ngắt từ của ký tự tiếng Việt (.ML__error).
 * - Hỗ trợ các công thức toán học lồng nhau không giới hạn cấp độ (phân số trong căn, phân số lồng phân số).
 * - Tự động hiển thị các ô vuông nét đứt nhỏ gọn (#?) và focus ngay vào tử số khi bấm phân số.
 * - Thanh công cụ MathSymbolToolbar hỗ trợ kéo rê chuột (drag-to-scroll) trên desktop.
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
  let text = (latex || "").trim();
  if (!text) return "";

  // 1. Gỡ bỏ dấu $ bao quanh toàn bộ nếu có từ trước
  if (text.startsWith("$") && text.endsWith("$") && text.length > 2) {
    text = text.substring(1, text.length - 1).trim();
  }

  // 2. Chuyển các ký tự thoát dấu khoảng trắng & dấu câu của MathLive về văn bản tự nhiên
  text = text
    .replace(/\\ /g, " ")
    .replace(/\\,/g, ",")
    .replace(/\\;/g, ";")
    .replace(/\\:/g, ":")
    .replace(/\\!/g, "")
    .trim();

  // 3. Regex bóc tách riêng từng công thức toán để bọc trong $...$
  // Ví dụ: 'giải \frac23' -> 'giải $\frac23$'
  // 'chào thầy hãy giúp em \frac{1}{2} + \sqrt{4}' -> 'chào thầy hãy giúp em $\frac{1}{2} + \sqrt{4}$'
  const mathBlockRegex =
    /(\\(?:frac(?:\{[^{}]*\}\{[^{}]*\}|[0-9a-zA-Z]{2})|sqrt(?:\{[^{}]*\}|[0-9a-zA-Z])|left\|[\s\S]*?\\right\||log(?:_\{[^{}]*\})?(?:\([^{}]*\))?|sin(?:\([^{}]*\))?|cos(?:\([^{}]*\))?|tan(?:\([^{}]*\))?|cot(?:\([^{}]*\))?|le|ge|ne|pm|pi|times|div|Delta)(?:[\s\+\-\=\*\/0-9a-zA-Z\(\)\{\}\^\_]|\\(?:frac|sqrt|left|right|log|sin|cos|tan|cot|le|ge|ne|pm|pi|times|div|Delta|[a-zA-Z]+))*)/g;

  if (mathBlockRegex.test(text)) {
    const formatted = text.replace(mathBlockRegex, (match) => {
      const trimmed = match.trim();
      if (!trimmed) return match;
      return ` $${trimmed}$ `;
    });
    return formatted.replace(/\s+/g, " ").trim();
  }

  // 4. Nếu là công thức thuần toán không có câu nói tự nhiên
  const hasVietnameseWords =
    /[a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]{2,}/i.test(
      text
    );
  if (!hasVietnameseWords && /[\\^_{}√±×÷≤≥≠π]/.test(text)) {
    return `$${text}$`;
  }

  return text;
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

  // ── [Cách 3] Khởi tạo MathLive & Can thiệp sâu vào Shadow DOM & Bộ gõ ──
  useEffect(() => {
    setIsMounted(true);
    import("mathlive").then(() => {
      const mf = mathfieldRef.current as any;
      if (!mf) return;

      // 1. Cấu hình các thuộc tính triệt tiêu lỗi font và phím tắt ngầm
      mf.mathVirtualKeyboardPolicy = "manual";
      mf.menuItems = [];
      mf.letterShapeStyle = "upright"; // Chữ cái đứng thẳng, không in nghiêng
      mf.mathModeSpace = "\\ "; // Nhấn Space chèn dấu cách thật
      mf.inlineShortcuts = {}; // Tắt phím tắt ngầm để không bị nhảy chữ tiếng Việt

      // 2. Can thiệp trực tiếp vào Shadow DOM để ép font Geist Sans và xóa bỏ lỗi hiển thị ký tự tiếng Việt
      if (mf.shadowRoot) {
        let injectedStyle = mf.shadowRoot.getElementById("socratic-math-style");
        if (!injectedStyle) {
          injectedStyle = document.createElement("style");
          injectedStyle.id = "socratic-math-style";
          injectedStyle.textContent = `
            /* Ép toàn bộ ký tự bên trong Shadow DOM về font Geist Sans chuẩn của website */
            *, .ML__mathit, .ML__cmr, .ML__text, .ML__base, .ML__fieldcontainer, .ML__content, .ML__latex {
              font-family: var(--font-geist-sans), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
              font-style: normal !important;
              letter-spacing: normal !important;
            }

            /* Triệt tiêu khoảng cách biến số toán học để các chữ cái đứng liền nhau tự nhiên */
            .ML__mathit, .ML__cmr {
              font-style: normal !important;
              margin: 0 !important;
              padding: 0 !important;
              letter-spacing: normal !important;
            }

            /* Xóa bỏ giao diện báo lỗi (nền hồng/chấm đỏ) khi gõ ký tự tiếng Việt có dấu */
            .ML__error {
              background: transparent !important;
              background-image: none !important;
              border: none !important;
              padding: 0 !important;
              display: inline !important;
              color: inherit !important;
            }

            /* Ẩn hoàn toàn nút bàn phím ảo và nút menu mặc định */
            ::part(virtual-keyboard-toggle),
            ::part(menu-toggle),
            .ML__virtual-keyboard-toggle,
            .ML__menu-toggle {
              display: none !important;
            }

            /* Triệt tiêu hoàn toàn hiệu ứng bôi đen / highlight nền đen của MathLive */
            .ML__selection,
            .ML__selected,
            .ML__contains-highlight,
            .ML__focused .ML__contains-highlight,
            .ML__focused .ML__selection,
            :host(:focus) .ML__selection,
            :host(:focus) .ML__selected {
              background: transparent !important;
              background-color: transparent !important;
              color: inherit !important;
            }

            /* Căn chỉnh ô phân số nét đứt gọn gàng, tự co dãn chuẩn Google Math Solver */
            .ML__placeholder {
              border: 1.5px dashed #8C4905 !important;
              background: transparent !important;
              border-radius: 4px !important;
              min-width: 20px !important;
              min-height: 20px !important;
              margin: 0 2px !important;
              opacity: 0.75 !important;
            }

            /* Đường kẻ phân số màu ấm áp đồng bộ hệ thống */
            .ML__frac-line {
              background-color: #8C4905 !important;
              height: 1.5px !important;
            }
          `;
          mf.shadowRoot.appendChild(injectedStyle);
        }
      }

      // 3. Lắng nghe sự kiện gõ phím & Enter để gửi
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

      // Sử dụng lệnh insert với placeholder (#?) chuẩn MathLive Engine
      switch (symbolId) {
        case "fraction":
          mf.executeCommand(["insert", "\\frac{#?}{#?}"]);
          break;
        case "sqrt":
          mf.executeCommand(["insert", "\\sqrt{#?}"]);
          break;
        case "pow":
          mf.executeCommand(["insert", "#@^{#?}"]);
          break;
        case "abs":
          mf.executeCommand(["insert", "\\left|#?\\right|"]);
          break;
        case "log":
          mf.executeCommand(["insert", "\\log_{#?}(#?)"]);
          break;
        case "degree":
          mf.executeCommand(["insert", "^{\\circ}"]);
          break;
        case "percent":
          mf.executeCommand(["insert", "\\%"]);
          break;
        case "le":
          mf.executeCommand(["insert", "\\le"]);
          break;
        case "ge":
          mf.executeCommand(["insert", "\\ge"]);
          break;
        case "ne":
          mf.executeCommand(["insert", "\\ne"]);
          break;
        case "pm":
          mf.executeCommand(["insert", "\\pm"]);
          break;
        case "pi":
          mf.executeCommand(["insert", "\\pi"]);
          break;
        case "times":
          mf.executeCommand(["insert", "\\times"]);
          break;
        case "divide":
          mf.executeCommand(["insert", "\\div"]);
          break;
        case "delta":
          mf.executeCommand(["insert", "\\Delta"]);
          break;
        case "var_x":
          mf.executeCommand(["insert", "x"]);
          break;
        case "var_y":
          mf.executeCommand(["insert", "y"]);
          break;
        case "sin":
          mf.executeCommand(["insert", "\\sin(#?)"]);
          break;
        case "cos":
          mf.executeCommand(["insert", "\\cos(#?)"]);
          break;
        case "tan":
          mf.executeCommand(["insert", "\\tan(#?)"]);
          break;
        case "cot":
          mf.executeCommand(["insert", "\\cot(#?)"]);
          break;
        default:
          mf.executeCommand(["insert", template]);
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

      {/* Style ẩn nút bàn phím và nút menu mặc định của MathLive */}
      <style>{`
        math-field::part(virtual-keyboard-toggle),
        math-field::part(menu-toggle) {
          display: none !important;
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
                : "Hỏi SocraticKid (nhập toán: bấm phân số, căn, mũ trên thanh công cụ)..."}
            </div>
          )}

          {isMounted ? (
            React.createElement("math-field", {
              ref: mathfieldRef,
              "math-virtual-keyboard-policy": "manual",
              class: "w-full outline-none border-none bg-transparent text-[#1C1917] font-medium text-base py-1 leading-normal",
              style: {
                "--primary-color": "#C1762A",
                "--caret-color": "#8C4905",
                "--selection-background-color": "transparent",
                "--contains-highlight-background-color": "transparent",
                "--text-highlight-background-color": "transparent",
                "--placeholder-color": "#8C4905",
                "--placeholder-opacity": "0.75",
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
