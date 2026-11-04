/**
 * File: components/chat/ChatInput.tsx
 * Mô tả: Component nhập liệu cho khung chat.
 * Tính năng chính:
 * - Textarea tự động co giãn dựa vào lượng text.
 * - Hỗ trợ phân số 2 ô xếp tầng (Tử số / Mẫu số) chèn trực tiếp trên khung input chat chuẩn Google Calculator.
 * - Tự động serialize phân số thành \frac{a}{b} khi gửi để AI hiểu chuẩn toán học.
 * - Tự động chuyển đổi ký tự khi gõ: >= thành ≥, <= thành ≤, != thành ≠, +- thành ±.
 * - Hỗ trợ đính kèm ảnh, dán ảnh từ clipboard, Bottom Sheet trên mobile.
 */
"use client";

import {
  useRef,
  useEffect,
  useState,
  KeyboardEvent,
  ClipboardEvent,
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

interface FractionData {
  id: string;
  numerator: string;
  denominator: string;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024;

// ─── Component ───────────────────────────────────────────────────────────────

export function ChatInput({
  onSendMessage,
  isLoading,
  isOffline = false,
}: ChatInputProps) {
  // ── State ──
  const [contentBefore, setContentBefore] = useState("");
  const [contentAfter, setContentAfter] = useState("");
  const [activeFraction, setActiveFraction] = useState<FractionData | null>(null);

  const [attachment, setAttachment] = useState<ImageAttachment | null>(null);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [fileTooLargeInfo, setFileTooLargeInfo] = useState<{
    isOpen: boolean;
    sizeMb: number;
    message?: string;
  }>({
    isOpen: false,
    sizeMb: 0,
  });

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Lắng nghe phím Escape và khóa cuộn trang khi đang xem trước ảnh
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

  // ── Refs ──
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const afterInputRef = useRef<HTMLInputElement>(null);
  const numInputRef = useRef<HTMLInputElement>(null);
  const denInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const libraryInputRef = useRef<HTMLInputElement>(null);
  const sheetContainerRef = useRef<HTMLDivElement>(null);

  // ── Auto-resize textarea ──

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [contentBefore]);

  // ── Tự động chuyển đổi ký tự khi gõ (>= thành ≥, <= thành ≤, != thành ≠, +- thành ±) ──

  const applyMathSymbolReplacements = (rawVal: string, cursor: number | null) => {
    const replacements: [string, string][] = [
      [">=", "≥"],
      ["<=", "≤"],
      ["!=", "≠"],
      ["+-", "±"],
    ];

    let updatedVal = rawVal;
    let offsetChange = 0;

    for (const [asciiSym, unicodeSym] of replacements) {
      if (updatedVal.includes(asciiSym)) {
        const index = updatedVal.indexOf(asciiSym);
        updatedVal = updatedVal.replaceAll(asciiSym, unicodeSym);
        if (cursor !== null && cursor > index) {
          offsetChange += asciiSym.length - unicodeSym.length;
        }
      }
    }

    const newCursor =
      offsetChange > 0 && cursor !== null
        ? Math.max(0, cursor - offsetChange)
        : cursor;

    return { updatedVal, newCursor };
  };

  const handleBeforeChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const rawVal = e.target.value;
    const cursor = e.target.selectionStart;
    const { updatedVal, newCursor } = applyMathSymbolReplacements(rawVal, cursor);

    setContentBefore(updatedVal);

    if (newCursor !== null && newCursor !== cursor) {
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.setSelectionRange(newCursor, newCursor);
        }
      });
    }
  };

  const handleAfterChange = (e: ChangeEvent<HTMLInputElement>) => {
    const rawVal = e.target.value;
    const cursor = e.target.selectionStart;
    const { updatedVal, newCursor } = applyMathSymbolReplacements(rawVal, cursor);

    setContentAfter(updatedVal);

    if (newCursor !== null && newCursor !== cursor) {
      requestAnimationFrame(() => {
        if (afterInputRef.current) {
          afterInputRef.current.setSelectionRange(newCursor, newCursor);
        }
      });
    }
  };

  // ── [US 9.4] Chèn phân số trực tiếp vào khung input chat (không mở popup) ──

  const handleInsertFraction = useCallback(() => {
    // Nếu đang có textarea, cắt văn bản tại vị trí con trỏ
    const textarea = textareaRef.current;
    let before = contentBefore;
    let after = contentAfter;

    if (textarea && !activeFraction) {
      const start = textarea.selectionStart ?? contentBefore.length;
      before = contentBefore.substring(0, start);
      after = contentBefore.substring(start);
    }

    setContentBefore(before);
    setContentAfter(after);
    setActiveFraction({
      id: "frac_" + Date.now(),
      numerator: "",
      denominator: "",
    });

    // Tự động focus vào ô tử số vừa chèn
    setTimeout(() => {
      numInputRef.current?.focus();
    }, 50);
  }, [contentBefore, contentAfter, activeFraction]);

  // ── Chèn ký hiệu toán học thông thường tại con trỏ ──

  const handleInsertMathSymbol = useCallback(
    (template: string, cursorOffset: number) => {
      // Nếu đang trong chế độ có phân số và đang focus ô after
      if (activeFraction && document.activeElement === afterInputRef.current) {
        const input = afterInputRef.current;
        if (!input) return;
        const start = input.selectionStart ?? contentAfter.length;
        const end = input.selectionEnd ?? contentAfter.length;
        const newAfter =
          contentAfter.substring(0, start) + template + contentAfter.substring(end);
        setContentAfter(newAfter);
        const targetPos = start + cursorOffset;
        requestAnimationFrame(() => {
          input.focus();
          input.setSelectionRange(targetPos, targetPos);
        });
        return;
      }

      // Mặc định chèn vào ô before (hoặc textarea chính)
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart ?? contentBefore.length;
      const end = textarea.selectionEnd ?? contentBefore.length;

      const newContent =
        contentBefore.substring(0, start) + template + contentBefore.substring(end);
      setContentBefore(newContent);

      const targetCursorPos = start + cursorOffset;

      requestAnimationFrame(() => {
        textarea.focus();
        textarea.setSelectionRange(targetCursorPos, targetCursorPos);
      });
    },
    [contentBefore, contentAfter, activeFraction]
  );

  // ── Image Attachment Helpers ──

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

  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData?.items ?? []);
    const imageItem = items.find((item) => item.type.startsWith("image/"));
    if (!imageItem) return;
    const file = imageItem.getAsFile();
    if (!file) return;
    e.preventDefault();
    attachImage(file);
  };

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

  // ── Xử lý phím Enter để gửi ──

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Ghép toàn bộ nội dung thành chuỗi gửi cho AI (serialize phân số thành \frac{a}{b})
  const getCompiledMessage = () => {
    let msg = contentBefore;
    if (activeFraction) {
      const num = activeFraction.numerator.trim() || "1";
      const den = activeFraction.denominator.trim() || "2";
      msg += `\\frac{${num}}{${den}}`;
      if (contentAfter) {
        msg += contentAfter;
      }
    }
    return msg.trim();
  };

  const compiledMessage = getCompiledMessage();

  const canSend =
    (compiledMessage.length > 0 || attachment !== null) &&
    !isLoading &&
    !isOffline;

  const handleSend = () => {
    if (!canSend) return;
    onSendMessage(compiledMessage, attachment?.file);
    setContentBefore("");
    setContentAfter("");
    setActiveFraction(null);
    removeAttachment();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
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

      {/* ── Thanh công cụ ký hiệu toán học chuẩn Google Math Calculator ── */}
      <div className="mb-2 px-0.5">
        <MathSymbolToolbar
          onInsertSymbol={handleInsertMathSymbol}
          onInsertFraction={handleInsertFraction}
          disabled={isLoading || isOffline}
        />
      </div>

      {/* ── Vùng background bo góc chứa ô nhập liệu và phân số inline ── */}
      <div
        className={cn(
          "relative flex items-center gap-2 bg-[#F1CCA6]/40 p-2 pl-3 pr-2 rounded-3xl border border-[#C1762A]/20 shadow-sm focus-within:border-[#C1762A] focus-within:bg-white transition-all flex-wrap sm:flex-nowrap",
          isOffline && "opacity-75 bg-[#F7ECE1] border-[#F1CCA6]",
        )}
      >
        {/* Nút + đính kèm */}
        <div
          className="relative self-center shrink-0"
          ref={sheetContainerRef}
        >
          <button
            id="chat-attach-btn"
            onClick={handlePlusClick}
            disabled={isOffline}
            aria-label="Đính kèm ảnh"
            aria-expanded={isSheetOpen}
            className={cn(
              "p-2.5 text-[#8C4905] hover:bg-[#F1CCA6] rounded-full transition-all duration-150 cursor-pointer",
              "disabled:opacity-40 disabled:cursor-not-allowed",
              isSheetOpen && "bg-[#F1CCA6] rotate-45",
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
                  "animate-in slide-in-from-bottom duration-250 ease-out",
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

        {/* ── Vùng nhập text & phân số inline trực tiếp trên khung input chat ── */}
        <div className="flex-1 flex items-center gap-1 min-w-0 flex-wrap sm:flex-nowrap">
          {/* Ô text trước phân số (hoặc ô textarea đầy đủ khi không có phân số) */}
          <textarea
            ref={textareaRef}
            value={contentBefore}
            onChange={handleBeforeChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={
              activeFraction
                ? "Nội dung trước..."
                : isOffline
                ? "Mất kết nối..."
                : "Hỏi SocraticKid (nhập toán: >=, <=, hoặc chọn thanh công cụ trên)..."
            }
            className={cn(
              "py-2 bg-transparent text-stone-900 placeholder:text-[#8C4905]/60 outline-none resize-none overflow-y-auto font-medium disabled:cursor-not-allowed",
              activeFraction
                ? "w-auto max-w-[180px] min-w-[70px] h-[38px] text-sm"
                : "flex-1 max-h-[150px] min-h-[44px]"
            )}
            rows={1}
            disabled={isLoading || isOffline}
          />

          {/* ── KHỐI PHÂN SỐ 2 Ô XẾP TẦNG TRỰC TIẾP TRÊN KHUNG CHAT (Chuẩn Google Calculator) ── */}
          {activeFraction && (
            <div className="inline-flex items-center gap-1 my-0.5 px-1.5 py-1 bg-white/90 rounded-2xl border-2 border-[#C1762A] shadow-xs shrink-0 animate-in zoom-in-95 duration-150">
              <div className="flex flex-col items-center justify-center gap-1">
                {/* Ô Tử số nét đứt */}
                <input
                  ref={numInputRef}
                  type="text"
                  value={activeFraction.numerator}
                  onChange={(e) => {
                    const val = e.target.value;
                    setActiveFraction((prev) =>
                      prev ? { ...prev, numerator: val } : null
                    );
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === "ArrowDown") {
                      e.preventDefault();
                      denInputRef.current?.focus();
                    } else if (e.key === "Backspace" && !activeFraction.numerator) {
                      e.preventDefault();
                      textareaRef.current?.focus();
                    }
                  }}
                  placeholder="tử"
                  className="w-12 h-6 text-center font-bold text-xs bg-[#F7ECE1]/60 text-[#8C4905] border-[1.8px] border-dashed border-[#8C4905] rounded-md focus:outline-none focus:bg-white focus:border-solid transition-all placeholder:text-[#8C4905]/40"
                />

                {/* Vạch kẻ ngang phân số */}
                <div className="w-14 h-[2px] bg-[#8C4905] rounded-full" />

                {/* Ô Mẫu số nét đứt */}
                <input
                  ref={denInputRef}
                  type="text"
                  value={activeFraction.denominator}
                  onChange={(e) => {
                    const val = e.target.value;
                    setActiveFraction((prev) =>
                      prev ? { ...prev, denominator: val } : null
                    );
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowUp") {
                      e.preventDefault();
                      numInputRef.current?.focus();
                    } else if (e.key === "ArrowRight" || e.key === "Tab") {
                      e.preventDefault();
                      afterInputRef.current?.focus();
                    } else if (e.key === "Enter") {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="mẫu"
                  className="w-12 h-6 text-center font-bold text-xs bg-[#F7ECE1]/60 text-[#8C4905] border-[1.8px] border-dashed border-[#8C4905] rounded-md focus:outline-none focus:bg-white focus:border-solid transition-all placeholder:text-[#8C4905]/40"
                />
              </div>

              {/* Nút X xóa phân số */}
              <button
                type="button"
                onClick={() => {
                  setActiveFraction(null);
                  setContentBefore((prev) => prev + (contentAfter ? " " + contentAfter : ""));
                  setContentAfter("");
                  textareaRef.current?.focus();
                }}
                className="text-stone-400 hover:text-red-500 p-0.5 rounded-full transition-colors cursor-pointer self-start"
                title="Xóa phân số"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {/* Ô text tiếp theo sau phân số (nếu có) */}
          {activeFraction && (
            <input
              ref={afterInputRef}
              type="text"
              value={contentAfter}
              onChange={handleAfterChange}
              onKeyDown={handleKeyDown}
              placeholder="tiếp tục gõ..."
              className="flex-1 min-w-[80px] py-2 bg-transparent text-stone-900 placeholder:text-[#8C4905]/60 outline-none text-sm font-medium"
              disabled={isLoading || isOffline}
            />
          )}
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
              : "bg-[#F1CCA6]/40 text-[#8C4905]/40 cursor-not-allowed",
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
