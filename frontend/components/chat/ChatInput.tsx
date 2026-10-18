/**
 * File: components/chat/ChatInput.tsx
 * Mô tả: Component nhập liệu cho khung chat.
 * Tính năng chính:
 * - Textarea tự động co giãn (auto-expand) dựa vào lượng text người dùng nhập.
 * - Hỗ trợ nhấn Enter để gửi, Shift+Enter để xuống dòng.
 * - Khóa nút gửi khi textarea trống hoặc khi AI đang bận phản hồi (isLoading).
 * - [T6.20] Hỗ trợ paste ảnh từ clipboard (onPaste handler).
 * - [T6.20] Đính kèm ảnh qua nút +, hiển thị thumbnail preview + nút X xóa ảnh.
 * - [T6.21] Mobile Bottom Sheet khi bấm +: Chọn Camera hoặc Thư viện ảnh.
 */
"use client";

import {
  useRef,
  useEffect,
  useState,
  KeyboardEvent,
  ClipboardEvent,
  useCallback,
} from "react";
import { createPortal } from "react-dom";
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

// ─── Types ───────────────────────────────────────────────────────────────────

/** Đại diện cho một ảnh đính kèm đang chờ gửi */
interface ImageAttachment {
  /** URL tạm để render thumbnail (từ URL.createObjectURL) */
  previewUrl: string;
  /** File gốc để gửi lên server */
  file: File;
}

export interface ChatInputProps {
  /**
   * Callback khi gửi tin nhắn.
   * @param message - Nội dung text (có thể rỗng nếu chỉ gửi ảnh)
   * @param image   - [T6.20] File ảnh đính kèm (tùy chọn)
   */
  onSendMessage: (message: string, image?: File) => void;
  isLoading?: boolean; // Cờ kiểm tra AI đang xử lý
  isOffline?: boolean; // Cờ kiểm tra trạng thái mất mạng
}

// ─── Constants ───────────────────────────────────────────────────────────────

/** [T6.20/AC5] Kích thước file ảnh tối đa cho phép: 5MB */
const MAX_FILE_SIZE = 5 * 1024 * 1024;

// ─── Component ───────────────────────────────────────────────────────────────

export function ChatInput({
  onSendMessage,
  isLoading,
  isOffline = false,
}: ChatInputProps) {
  // ── State ──
  const [content, setContent] = useState("");
  /** [T6.20] Ảnh đính kèm hiện tại (tối đa 1 ảnh) */
  const [attachment, setAttachment] = useState<ImageAttachment | null>(null);
  /** [T6.21] Kiểm soát Bottom Sheet trên mobile */
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  /** [T6.20/AC5] Thông báo lỗi validation ảnh (VD: vượt quá 5MB hoặc sai định dạng) */
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  /** Trạng thái mở modal xem trước ảnh to ở giữa màn hình */
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

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
  /** [T6.21] Hidden input dành cho Camera (capture="environment") */
  const cameraInputRef = useRef<HTMLInputElement>(null);
  /** [T6.20] Hidden input dành cho Thư viện ảnh */
  const libraryInputRef = useRef<HTMLInputElement>(null);
  /** Container của nút + và bottom sheet để xử lý click outside */
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
  }, [content]);

  // ── [T6.20/AC5] Image Attachment Helpers ──

  /**
   * Gán ảnh từ File object vào state attachment.
   * [AC5] Kiểm tra định dạng ảnh và kích thước tối đa 5MB.
   * Revoke URL cũ trước khi tạo URL mới để tránh memory leak.
   */
  const attachImage = useCallback((file: File) => {
    setErrorMessage(null);
    if (!file.type.startsWith("image/") || file.size > MAX_FILE_SIZE) {
      setErrorMessage("Chỉ hỗ trợ ảnh dưới 5MB");
      return;
    }
    setAttachment((prev) => {
      if (prev) URL.revokeObjectURL(prev.previewUrl);
      return { file, previewUrl: URL.createObjectURL(file) };
    });
  }, []);

  /** Xóa ảnh đính kèm và revoke object URL để tránh memory leak */
  const removeAttachment = useCallback(() => {
    setErrorMessage(null);
    setIsPreviewOpen(false);
    setAttachment((prev) => {
      if (prev) URL.revokeObjectURL(prev.previewUrl);
      return null;
    });
  }, []);

  /** Tự động ẩn thông báo lỗi sau 4 giây */
  useEffect(() => {
    if (!errorMessage) return;
    const timer = setTimeout(() => setErrorMessage(null), 4000);
    return () => clearTimeout(timer);
  }, [errorMessage]);

  /** Cleanup object URL khi component unmount */
  useEffect(() => {
    return () => {
      setAttachment((prev) => {
        if (prev) URL.revokeObjectURL(prev.previewUrl);
        return null;
      });
    };
  }, []);

  // ── [T6.21] Đóng Bottom Sheet khi click bên ngoài ──

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

  // ── [T6.20] Paste Handler: nhận ảnh từ clipboard ──

  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData?.items ?? []);
    const imageItem = items.find((item) => item.type.startsWith("image/"));
    if (!imageItem) return;
    const file = imageItem.getAsFile();
    if (!file) return;
    // Ngăn paste text/html không mong muốn khi có ảnh trong clipboard
    e.preventDefault();
    attachImage(file);
  };

  // ── [T6.20/T6.21] Xử lý thay đổi file input ──

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) attachImage(file);
    // Reset value để người dùng có thể chọn lại cùng file
    e.target.value = "";
    setIsSheetOpen(false);
  };

  // ── [T6.21] Xử lý nhấn nút + ──

  const handlePlusClick = () => {
    const isMobile =
      typeof window !== "undefined" &&
      window.matchMedia("(max-width: 767px)").matches;
    if (isMobile) {
      // Mobile: bật/tắt bottom sheet để chọn Camera hoặc Thư viện
      setIsSheetOpen((prev) => !prev);
    } else {
      // Desktop: mở thư viện ảnh trực tiếp (không cần bottom sheet)
      libraryInputRef.current?.click();
    }
  };

  // ── Xử lý bắt phím ──

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Derived state ──

  /** Có thể gửi khi: có text HOẶC có ảnh, VÀ không loading, VÀ không offline */
  const canSend =
    (content.trim().length > 0 || attachment !== null) &&
    !isLoading &&
    !isOffline;

  // ── Xử lý gửi tin nhắn ──

  const handleSend = () => {
    if (!canSend) return;
    onSendMessage(content.trim(), attachment?.file);
    setContent("");
    removeAttachment();
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  // ── Render ──

  return (
    <div className="p-4 bg-transparent mt-auto relative z-10 w-full">
      {/* ── [T6.20/AC5] Cảnh báo lỗi tải ảnh (>5MB hoặc định dạng không hợp lệ) ── */}
      {errorMessage && (
        <div className="mb-2 ml-1 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs shadow-sm animate-in fade-in slide-in-from-bottom-2 duration-200">
          <AlertCircle size={14} className="shrink-0 text-red-500" />
          <span className="font-medium">{errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            className="ml-1 text-red-400 hover:text-red-700 transition-colors"
            aria-label="Đóng thông báo lỗi"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* ── [T6.20] Thumbnail Preview khi có ảnh đính kèm ── */}
      {attachment && (
        <div className="mb-2 ml-1 flex items-start gap-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <div className="relative group inline-block">
            {/* Thumbnail ảnh — có thể bấm vào để xem to ở giữa màn hình */}
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

            {/* Nút X xóa ảnh — hiện khi hover/focus */}
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
          {/* Tên file và dung lượng */}
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

      {/* ── Modal xem ảnh phóng to ở giữa màn hình khi đính kèm trong ô chat ── */}
      {isPreviewOpen &&
        isMounted &&
        attachment &&
        createPortal(
          <div
            className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
            onClick={() => setIsPreviewOpen(false)}
            role="dialog"
            aria-modal="true"
            aria-label="Xem trước ảnh bài toán"
          >
            <div
              className="relative flex flex-col items-center max-w-[95vw] max-h-[92vh] animate-in zoom-in-95 duration-200"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Thanh tiêu đề trên đầu */}
              <div className="w-full flex items-center justify-between pb-3 px-1 text-white">
                <span className="text-sm font-semibold tracking-wide text-white/90 drop-shadow">
                  Xem trước ảnh bài toán
                </span>
                <button
                  onClick={() => setIsPreviewOpen(false)}
                  className="p-1.5 rounded-full bg-white/15 hover:bg-red-500/80 text-white transition-colors cursor-pointer"
                  title="Đóng (hoặc nhấn Esc)"
                  aria-label="Đóng xem ảnh"
                >
                  <X size={19} />
                </button>
              </div>

              {/* Ảnh hiển thị lớn ở giữa màn hình */}
              <div className="relative overflow-hidden rounded-2xl border border-white/20 shadow-2xl bg-black/40 flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={attachment.previewUrl}
                  alt="Ảnh xem trước phóng to"
                  className="max-h-[82vh] w-auto max-w-[92vw] object-contain select-none"
                />
              </div>
            </div>
          </div>,
          document.body,
        )}

      {/* ── Vùng background bo góc chứa các nút và ô nhập liệu ── */}
      <div
        className={cn(
          "relative flex items-end gap-2 bg-[#F1CCA6]/40 p-2 pl-4 pr-2 rounded-3xl border border-[#C1762A]/20 shadow-sm focus-within:border-[#C1762A] focus-within:bg-white transition-all",
          isOffline && "opacity-75 bg-gray-100 border-gray-300",
        )}
      >
        {/* ── [T6.20/T6.21] Nút + và Bottom Sheet ── */}
        <div
          className="relative self-end mb-0.5 shrink-0"
          ref={sheetContainerRef}
        >
          {/* Nút + */}
          <button
            id="chat-attach-btn"
            onClick={handlePlusClick}
            disabled={isOffline}
            aria-label="Đính kèm ảnh"
            aria-expanded={isSheetOpen}
            className={cn(
              "p-2.5 text-[#8C4905] hover:bg-[#F1CCA6] rounded-full transition-all duration-150",
              "disabled:opacity-40 disabled:cursor-not-allowed",
              isSheetOpen && "bg-[#F1CCA6] rotate-45",
            )}
          >
            <Plus size={20} />
          </button>

          {/* ── [T6.21] Mobile Bottom Sheet ── */}
          {isSheetOpen && (
            <>
              {/* Backdrop — chỉ hiện trên mobile, đóng sheet khi tap bên ngoài */}
              <div
                className="fixed inset-0 bg-black/20 z-30 md:hidden"
                onClick={() => setIsSheetOpen(false)}
                aria-hidden="true"
              />

              {/* Sheet Panel — trượt lên từ dưới màn hình */}
              <div
                role="dialog"
                aria-label="Chọn nguồn ảnh"
                className={cn(
                  "fixed bottom-0 left-0 right-0 z-40 md:hidden",
                  "bg-white rounded-t-2xl shadow-2xl border-t border-[#C1762A]/10",
                  "animate-in slide-in-from-bottom duration-250 ease-out",
                )}
              >
                {/* Handle bar kéo */}
                <div className="flex justify-center pt-3 pb-1">
                  <div className="w-10 h-1 bg-gray-300 rounded-full" />
                </div>

                {/* Tiêu đề */}
                <p className="text-center text-sm font-semibold text-[#8C4905] pb-3">
                  Thêm ảnh
                </p>

                {/* Hai lựa chọn */}
                <div className="flex gap-3 px-6 pb-8 pt-1">
                  {/* [T6.21] Camera — capture="environment" mở camera sau trên mobile */}
                  <button
                    id="chat-attach-camera-btn"
                    onClick={() => cameraInputRef.current?.click()}
                    className={[
                      "flex-1 flex flex-col items-center gap-2.5 py-5 px-4 rounded-2xl",
                      "border-2 border-[#C1762A]/20 hover:border-[#C1762A]/60",
                      "hover:bg-[#F1CCA6]/30 transition-all active:scale-95",
                    ].join(" ")}
                  >
                    <div className="w-12 h-12 rounded-full bg-[#F1CCA6] flex items-center justify-center">
                      <Camera size={22} className="text-[#8C4905]" />
                    </div>
                    <span className="text-sm font-medium text-[#8C4905]">
                      Camera
                    </span>
                  </button>

                  {/* [T6.21] Thư viện — không có capture, mở thư viện ảnh hệ thống */}
                  <button
                    id="chat-attach-library-btn"
                    onClick={() => libraryInputRef.current?.click()}
                    className={[
                      "flex-1 flex flex-col items-center gap-2.5 py-5 px-4 rounded-2xl",
                      "border-2 border-[#C1762A]/20 hover:border-[#C1762A]/60",
                      "hover:bg-[#F1CCA6]/30 transition-all active:scale-95",
                    ].join(" ")}
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

        {/* ── [T6.20] Hidden File Inputs ── */}

        {/* Camera: capture="environment" → mở camera sau trên thiết bị di động */}
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

        {/* Thư viện: không có capture → mở file picker hoặc thư viện ảnh */}
        <input
          ref={libraryInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileChange}
          aria-hidden="true"
          tabIndex={-1}
        />

        {/* ── Ô nhập liệu Textarea ── */}
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={
            isOffline
              ? "Mất kết nối. Đang chờ kết nối lại..."
              : "Hỏi SocraticKid..."
          }
          className="flex-1 max-h-[150px] min-h-[44px] py-3 bg-transparent text-[#000000] placeholder:text-[#8C4905]/60 outline-none resize-none overflow-y-auto font-medium disabled:cursor-not-allowed"
          rows={1}
          disabled={isLoading || isOffline}
        />

        {/* ── Nút Gửi ── */}
        <button
          id="chat-send-btn"
          onClick={handleSend}
          disabled={!canSend}
          className={cn(
            "p-2.5 rounded-full flex items-center justify-center transition-all self-end mb-0.5 shadow-sm shrink-0",
            canSend
              ? "bg-[#C1762A] text-white hover:bg-[#8C4905] hover:scale-105"
              : "bg-[#D9D9D9] text-gray-400 cursor-not-allowed",
          )}
          title={isOffline ? "Không thể gửi khi mất kết nối" : "Gửi tin nhắn"}
        >
          <Send size={20} className={cn(canSend && !isOffline && "ml-0.5")} />
        </button>
      </div>

      {/* ── Cảnh báo nhẹ dưới ô nhập liệu ── */}
      <div className="text-center mt-2">
        <p className="text-xs text-[#8C4905]/60">
          AI có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.
        </p>
      </div>
    </div>
  );
}
