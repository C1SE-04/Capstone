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
  Minimize2,
  ChevronDown,
  ChevronUp,
  CornerDownLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FileTooLargeToast } from "./FileTooLargeToast";
import { ImageZoomModal } from "./ImageZoomModal";
import { MathSymbolToolbar } from "./MathSymbolToolbar";
import { formatLatexForChat } from "@/lib/latex";

// ─── Types ───────────────────────────────────────────────────────────────────

interface ImageAttachment {
  previewUrl: string;
  file: File;
}

export interface ChatInputProps {
  onSendMessage: (message: string, image?: File) => void;
  isLoading?: boolean;
  isOffline?: boolean;
  cooldownSeconds?: number;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024;

/** Kiểm tra nội dung MathLive có thực sự rỗng (kể cả khi còn khung \displaylines{\\ } sau Ctrl+A xóa hết) */
function isMathFieldEffectivelyEmpty(latex: string): boolean {
  if (!latex) return true;
  const cleaned = latex
    .replace(/\\displaylines\s*\{/g, "")
    .replace(/\\text\s*\{\s*\}/g, "")
    .replace(/\\\\/g, "")
    .replace(/[{}]/g, "")
    .replace(/\\ /g, "")
    .trim();
  return cleaned.length === 0;
}

// ─── Main Component ──────────────────────────────────────────────────────────

export function ChatInput({
  onSendMessage,
  isLoading,
  isOffline = false,
  cooldownSeconds = 0,
}: ChatInputProps) {
  // ── State ──
  const [hasContent, setHasContent] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [canExpand, setCanExpand] = useState(false);
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
  const handleSendRef = useRef<() => void>(() => {});
  const handleInsertNewLineRef = useRef<() => void>(() => {});
  const attachImageRef = useRef<(file: File) => void>(() => {});
  const isLoadingRef = useRef(isLoading);
  const preserveEmptyNewLineRef = useRef(false);

  // Đồng bộ hasContent và tự động dọn bảng \displaylines trống khi người dùng Ctrl+A / tô xóa hết
  const syncContentState = useCallback((node: any, allowEmptyMultiline = false) => {
    if (!node) return;
    const val = node.value || "";
    const empty = isMathFieldEffectivelyEmpty(val);

    if (empty && val.length > 0 && !allowEmptyMultiline) {
      node.value = "";
      node.scrollTop = 0;
      setHasContent(false);
      setIsExpanded(false);
      setCanExpand(false);
      return;
    }

    if (empty) {
      setIsExpanded(false);
      setCanExpand(false);
    }

    setHasContent(!empty);
  }, []);

  // Đảm bảo trên điện thoại (iOS/Android), phần tử ẩn .ML__keyboard-sink của MathLive
  // mở bàn phím hệ thống thay vì bị chặn bởi inputmode="none".
  const syncMobileKeyboardInput = useCallback((node: HTMLElement | null) => {
    const sink = node?.shadowRoot?.querySelector(".ML__keyboard-sink") as HTMLElement | null;
    if (sink) {
      if (sink.getAttribute("inputmode") !== "text") {
        sink.setAttribute("inputmode", "text");
      }
      if (sink.getAttribute("aria-multiline") !== "true") {
        sink.setAttribute("aria-multiline", "true");
      }
    }
  }, []);

  // Cập nhật trạng thái disabled / readOnly cho MathLive khi isLoading hoặc isOffline thay đổi
  useEffect(() => {
    isLoadingRef.current = isLoading;
    const mf = mathfieldRef.current as any;
    if (mf) {
      mf.disabled = Boolean(isLoading || isOffline);
      mf.readOnly = Boolean(isLoading || isOffline);
      // Khi AI phản hồi xong, tự động focus lại ô nhập để học sinh tiếp tục gõ
      if (!isLoading && !isOffline) {
        setTimeout(() => {
          try {
            mf.focus();
          } catch {
            // bỏ qua nếu node chưa sẵn sàng
          }
        }, 80);
      }
    }
  }, [isLoading, isOffline]);

  // ── [Cách 3] Khởi tạo MathLive & Can thiệp sâu vào Shadow DOM & Bộ gõ ──
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const onMathFieldRef = useCallback((node: any) => {
    mathfieldRef.current = node;
    if (!node) return;

    // Đồng bộ trạng thái khóa ngay khi node được gắn
    node.disabled = Boolean(isLoadingRef.current || isOffline);
    node.readOnly = Boolean(isLoadingRef.current || isOffline);

    // Tránh đăng ký nhiều lần event listeners nếu node được gắn lại
    if (node._socraticInitialized) return;
    node._socraticInitialized = true;

    // 1. Lắng nghe sự kiện gõ phím & cập nhật hasContent ĐỒNG BỘ ngay lập tức
    const updateContent = () => {
      const keepEmpty = preserveEmptyNewLineRef.current;
      preserveEmptyNewLineRef.current = false;
      syncContentState(node, keepEmpty);
    };

    updateContent();
    node.addEventListener("input", updateContent);
    node.addEventListener("change", updateContent);
    // Chỉ kiểm tra lại khi nhả phím xóa (tránh serialize toàn bộ AST MathLive ở mọi phím như Ctrl+A / mũi tên)
    node.addEventListener("keyup", (e: KeyboardEvent) => {
      if (e.key === "Backspace" || e.key === "Delete") {
        updateContent();
      }
    });
    node.addEventListener("cut", () => setTimeout(updateContent, 0));

    // Theo dõi chiều cao nội dung để hiện nút phóng to khi nhập từ ~3 dòng trở lên
    if (typeof ResizeObserver !== "undefined" && !node._socraticResizeObserver) {
      const ro = new ResizeObserver(() => {
        const expandable = node.scrollHeight > 68;
        setCanExpand(expandable);
      });
      ro.observe(node);
      node._socraticResizeObserver = ro;
    }

    node.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        // Chặn Enter khi đang trong quá trình gõ bộ gõ IME tiếng Việt
        if (e.isComposing || (e as any).keyCode === 229) return;
        e.preventDefault();
        // Chặn gửi tin nhắn nếu đang đợi AI phản hồi
        if (isLoadingRef.current) return;
        handleSendRef.current?.();
      } else if (e.key === "Enter" && e.shiftKey) {
        if (e.isComposing || (e as any).keyCode === 229) return;
        e.preventDefault();
        e.stopPropagation();
        if (isLoadingRef.current) return;
        handleInsertNewLineRef.current?.();
      }
    });

    // Fix lỗi paste:
    // 1. Nếu paste file ảnh (chụp màn hình Snipping Tool, copy ảnh web) -> đính kèm ảnh
    // 2. Nếu paste text: MathLive mặc định ở math mode làm mất dấu cách. Chuyển sang text mode để giữ nguyên khoảng trắng & xuống dòng.
    node.addEventListener("paste", (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (items) {
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.startsWith("image/")) {
            const file = items[i].getAsFile();
            if (file) {
              e.preventDefault();
              attachImageRef.current?.(file);
              return;
            }
          }
        }
      }

      const text = e.clipboardData?.getData("text/plain");
      if (!text) return;
      e.preventDefault();
      // Chuẩn hóa Unicode ký tự toán học (như 𝑥, 𝑦, 𝐴, 𝟐 copy từ web/Word) về ký tự chuẩn
      const cleanText = text.normalize("NFKC").replace(/\r\n?/g, "\n");
      const pastedLines = cleanText.split("\n");
      pastedLines.forEach((line, idx) => {
        if (line) {
          // Dùng insert() API của MathLive với mode text để giữ space
          if (typeof node.insert === "function") {
            node.insert(line, { mode: "text" });
          } else {
            node.executeCommand(["insert", line]);
          }
        }
        if (idx < pastedLines.length - 1) {
          node.executeCommand("addRowAfter");
        }
      });
      updateContent();
    });

    // Hàm cấu hình loại trừ triệt để phím tắt ngầm và lỗi xung đột bộ gõ tiếng Việt Telex
    const applyMathLiveConfigs = () => {
      try {
        syncMobileKeyboardInput(node);
        // Cấu hình an toàn thông qua setOptions (hoạt động tốt cả trước và sau khi _mathfield mount)
        if (typeof node.setOptions === "function") {
          node.setOptions({
            mathVirtualKeyboardPolicy: "manual",
            letterShapeStyle: "upright",
            mathModeSpace: "\\text{ }",
            inlineShortcuts: {}, // Tắt toàn bộ inline shortcuts ("th" -> \operatorname{th}, "ch", "tg", ...)
            inlineShortcutTimeout: 0,
            isImplicitFunction: () => false, // Vô hiệu hóa nhận diện "th", "ch" làm hàm toán ngầm
          });
        }

        try {
          node.mathVirtualKeyboardPolicy = "manual";
          node.letterShapeStyle = "upright";
          node.mathModeSpace = "\\text{ }";
        } catch {}

        // Chỉ can thiệp menuItems và keybindings khi _mathfield đã mount để tránh ném lỗi "Mathfield not mounted"
        if (node._mathfield) {
          try {
            node.menuItems = [];
          } catch {}

          try {
            if (Array.isArray(node.keybindings)) {
              node.keybindings = node.keybindings.filter((kb: any) => {
                const k = (kb?.key || "").toLowerCase();
                return (
                  !k.includes("alt+o") &&
                  !k.includes("alt+d") &&
                  !k.includes("alt+p") &&
                  !k.includes("alt+v")
                );
              });
            }
          } catch {}
        }
      } catch (err) {
        console.warn("Could not apply MathLive configs:", err);
      }
    };

    applyMathLiveConfigs();
    node.addEventListener("focus", () => syncMobileKeyboardInput(node));
    setTimeout(applyMathLiveConfigs, 50);
    setTimeout(applyMathLiveConfigs, 200);

    // @ts-ignore
    import("mathlive").then(() => {
      if (typeof window !== "undefined" && window.customElements) {
        window.customElements.whenDefined("math-field").then(() => {
          applyMathLiveConfigs();
          setTimeout(applyMathLiveConfigs, 50);
        });
      }
      // 2. Cấu hình lại một lần nữa sau khi module MathLive nạp hoàn tất
      applyMathLiveConfigs();

      // 3. Can thiệp trực tiếp vào Shadow DOM để ép font Geist Sans và xóa bỏ lỗi hiển thị ký tự tiếng Việt
      if (node.shadowRoot) {
        let injectedStyle = node.shadowRoot.getElementById("socratic-math-style");
        if (!injectedStyle) {
          injectedStyle = document.createElement("style");
          injectedStyle.id = "socratic-math-style";
          injectedStyle.textContent = `
            /* Cho phép khung nhập tự dãn chiều cao theo nội dung (6 hàng mặc định, 16 hàng khi phóng to) và cuộn dọc khi vượt quá */
            :host {
              display: block !important;
              width: 100% !important;
              min-height: 36px !important;
              max-height: var(--socratic-mf-max-height, 156px) !important;
              overflow-y: auto !important;
              overflow-x: hidden !important;
              box-sizing: border-box !important;
              scrollbar-width: thin;
              scrollbar-color: rgba(140, 73, 5, 0.3) transparent;
            }

            :host::-webkit-scrollbar {
              width: 5px;
            }

            :host::-webkit-scrollbar-track {
              background: transparent;
            }

            :host::-webkit-scrollbar-thumb {
              background-color: rgba(140, 73, 5, 0.28);
              border-radius: 9999px;
            }

            :host::-webkit-scrollbar-thumb:hover {
              background-color: rgba(140, 73, 5, 0.48);
            }

            .ML__container {
              min-height: 36px !important;
              align-items: flex-start !important;
              touch-action: pan-y !important;
            }

            .ML__content {
              display: block !important;
              overflow: visible !important;
              width: 100% !important;
              box-sizing: border-box !important;
            }

            .ML__latex {
              display: block !important;
              width: 100% !important;
              white-space: normal !important;
              line-height: 1.5 !important;
              overflow-wrap: break-word !important;
            }

            /* Chỉ bật inline-wrap ở cấp gốc để không phá vỡ layout phân số/căn thức lồng nhau */
            .ML__latex > .ML__base {
              display: inline !important;
              width: auto !important;
              white-space: normal !important;
            }

            .ML__text {
              white-space: pre-wrap !important;
              overflow-wrap: break-word !important;
            }

            .ML__focused .ML__text {
              background: transparent !important;
              background-color: transparent !important;
            }

            /* Hỗ trợ xuống dòng thật (Shift+Enter / nút Xuống dòng -> \displaylines) mà vẫn tự wrap không đè dòng */
            /* Lưu ý: Dùng child combinator (>) để khớp chính xác cấp bảng gốc (.ML__latex > .ML__mtable hoặc > .ML__base > .ML__mtable) và không làm vỡ .ML__vlist của phân số bên trong */
            .ML__latex:has(> .ML__mtable) > .ML__strut,
            .ML__latex:has(> .ML__mtable) > .ML__strut--bottom,
            .ML__latex:has(> .ML__base > .ML__mtable) > .ML__strut,
            .ML__latex:has(> .ML__base > .ML__mtable) > .ML__strut--bottom {
              display: none !important;
            }

            .ML__latex:has(> .ML__mtable),
            .ML__latex:has(> .ML__base > .ML__mtable),
            .ML__latex > .ML__mtable,
            .ML__latex > .ML__base > .ML__mtable,
            .ML__latex > .ML__mtable > .col-align-l,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l,
            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t,
            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r {
              display: block !important;
              width: 100% !important;
            }

            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist {
              display: flex !important;
              flex-direction: column !important;
              gap: 4px !important;
              width: 100% !important;
              height: auto !important;
            }

            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist > span,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist > span {
              position: static !important;
              top: auto !important;
              height: auto !important;
              min-height: 1.5em !important;
              display: block !important;
              width: 100% !important;
            }

            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist > span > span:not(.ML__pstrut),
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist > span > span:not(.ML__pstrut) {
              display: block !important;
              width: 100% !important;
              height: auto !important;
              white-space: normal !important;
            }

            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist > span > .ML__pstrut,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist > span > .ML__pstrut,
            .ML__latex > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist-s,
            .ML__latex > .ML__base > .ML__mtable > .col-align-l > .ML__vlist-t > .ML__vlist-r > .ML__vlist-s {
              display: none !important;
            }

            /* Ép toàn bộ ký tự bên trong Shadow DOM về font Geist Sans chuẩn của website */
            :host, .ML__mathit, .ML__cmr, .ML__text, .ML__base, .ML__fieldcontainer, .ML__content, .ML__latex, .ML__op {
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

            /* Màu nền highlight bán trong suốt màu cam ấm cho cấu trúc phân số/căn thức khi đang nhập */
            .ML__contains-highlight,
            .ML__focused .ML__contains-highlight,
            .ML__focused .ML__selected,
            :host(:focus) .ML__selected {
              background: rgba(193, 118, 42, 0.12) !important;
              background-color: rgba(193, 118, 42, 0.12) !important;
              border-radius: 6px !important;
              color: inherit !important;
            }

            /* Khi người dùng chủ động bôi đen (selection) - không bo góc từng ký tự để tránh lag khi Ctrl+A đoạn dài */
            .ML__selection,
            .ML__focused .ML__selection,
            :host(:focus) .ML__selection {
              background: rgba(193, 118, 42, 0.25) !important;
              background-color: rgba(193, 118, 42, 0.25) !important;
              border-radius: 0 !important;
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
          node.shadowRoot.appendChild(injectedStyle);
        }
      }
    });
  }, [syncMobileKeyboardInput, syncContentState]);

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
  attachImageRef.current = attachImage;

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

      syncContentState(mf);
    },
    [syncContentState]
  );

  const handleInsertNewLine = useCallback(() => {
    if (isLoadingRef.current || isOffline) return;
    const mf = mathfieldRef.current as any;
    if (!mf) return;

    syncMobileKeyboardInput(mf);
    mf.focus();
    const sink = mf.shadowRoot?.querySelector(".ML__keyboard-sink") as HTMLElement | null;
    if (sink) {
      try {
        sink.focus({ preventScroll: true });
      } catch {}
    }

    preserveEmptyNewLineRef.current = true;
    let inserted = mf.executeCommand("addRowAfter");
    if (!inserted) {
      mf.executeCommand("moveToMathfieldEnd");
      inserted = mf.executeCommand("addRowAfter");
    }

    syncContentState(mf, true);
    setTimeout(() => {
      try {
        mf.executeCommand("scrollIntoView");
      } catch {}
    }, 20);
  }, [isOffline, syncMobileKeyboardInput, syncContentState]);
  handleInsertNewLineRef.current = handleInsertNewLine;

  // ── Gửi tin nhắn ──

  const canSend =
    (hasContent || attachment !== null) &&
    !isLoading &&
    !isOffline &&
    (!cooldownSeconds || cooldownSeconds <= 0);

  const handleSend = () => {
    // Chặn tuyệt đối nếu hệ thống đang phản hồi, mất kết nối hoặc đang trong thời gian chờ cooldown
    if (isLoading || isOffline || (cooldownSeconds && cooldownSeconds > 0)) return;

    const mf = mathfieldRef.current as any;
    let rawVal = mf?.value || "";
    // Xóa toán tử ngầm nếu lỡ phát sinh trong MathLive
    rawVal = rawVal.replace(/\\operatorname\{(th|ch|sh|tg|cotg|cth)\}/gi, "$1");
    const formatted = formatLatexForChat(rawVal);
    if (!formatted && !attachment) return;

    onSendMessage(formatted, attachment?.file);
    if (mf) {
      mf.value = "";
      mf.scrollTop = 0;
    }
    setHasContent(false);
    setIsExpanded(false);
    setCanExpand(false);
    removeAttachment();
  };
  handleSendRef.current = handleSend;

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
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (isLoading || isOffline) return;
          const files = e.dataTransfer?.files;
          if (files && files.length > 0) {
            attachImage(files[0]);
          }
        }}
        className={cn(
          "relative flex items-end gap-2 bg-[#F1CCA6]/40 p-2 pl-3 pr-2 rounded-3xl border border-[#C1762A]/20 shadow-sm focus-within:border-[#C1762A] focus-within:bg-white transition-colors duration-150",
          isOffline && "opacity-75 bg-[#F7ECE1] border-[#F1CCA6]",
          isLoading && "bg-[#F7ECE1]/80 border-[#C1762A]/30 cursor-not-allowed opacity-80"
        )}
      >
        {/* Nút Phóng to / Thu nhỏ khung nhập (tối đa 6 dòng mặc định -> 16 dòng khi phóng to) */}
        {(canExpand || isExpanded) && (
          <button
            id="chat-expand-btn"
            type="button"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              setIsExpanded((prev) => !prev);
              const mf = mathfieldRef.current as any;
              if (mf) {
                syncMobileKeyboardInput(mf);
                mf.focus();
              }
            }}
            aria-label={isExpanded ? "Thu gọn khung nhập" : "Phóng to khung nhập"}
            title={isExpanded ? "Thu gọn khung nhập (tối đa 6 dòng)" : "Phóng to khung nhập (tối đa 16 dòng)"}
            className="absolute top-2.5 right-3 z-10 p-1.5 rounded-full text-[#8C4905]/65 hover:text-[#8C4905] hover:bg-[#F1CCA6]/60 transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
          >
            {isExpanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        )}

        {/* Nút + và Mobile Bottom Sheet */}
        <div className="relative shrink-0 self-end" ref={sheetContainerRef}>
          <button
            id="chat-attach-btn"
            onClick={handlePlusClick}
            disabled={isOffline || isLoading}
            aria-label="Đính kèm ảnh"
            aria-expanded={isSheetOpen}
            className={cn(
              "p-2.5 text-[#8C4905] rounded-full transition-all duration-150",
              isOffline || isLoading
                ? "opacity-40 cursor-not-allowed"
                : "hover:bg-[#F1CCA6] cursor-pointer",
              isSheetOpen && "bg-[#F1CCA6] rotate-45"
            )}
            title={isLoading ? "Vui lòng đợi hệ thống phản hồi xong" : "Đính kèm ảnh"}
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
                    className="flex-1 flex flex-col items-center gap-2.5 py-5 px-4 rounded-2xl border border-[#F1CCA6] hover:border-[#C1762A] hover:bg-[#F7ECE1]/60 transition-all duration-150 ease-out active:scale-[0.98] cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
                  >
                    <div className="w-12 h-12 rounded-full bg-[#F1CCA6] flex items-center justify-center">
                      <Camera size={22} className="text-[#8C4905]" />
                    </div>
                    <span className="text-sm font-semibold text-[#8C4905]">
                      Camera
                    </span>
                  </button>

                  <button
                    id="chat-attach-library-btn"
                    onClick={() => libraryInputRef.current?.click()}
                    className="flex-1 flex flex-col items-center gap-2.5 py-5 px-4 rounded-2xl border border-[#F1CCA6] hover:border-[#C1762A] hover:bg-[#F7ECE1]/60 transition-all duration-150 ease-out active:scale-[0.98] cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
                  >
                    <div className="w-12 h-12 rounded-full bg-[#F1CCA6] flex items-center justify-center">
                      <ImageIcon size={22} className="text-[#8C4905]" />
                    </div>
                    <span className="text-sm font-semibold text-[#8C4905]">
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
        <div
          onClick={() => {
            if (!isLoading && !isOffline) {
              const mf = mathfieldRef.current as any;
              if (!mf) return;
              syncMobileKeyboardInput(mf);
              mf.focus();
              // Gọi đồng bộ trên keyboard-sink trong sự kiện click/tap để iOS Safari & Android mở bàn phím hệ thống
              const sink = mf.shadowRoot?.querySelector(".ML__keyboard-sink") as HTMLElement | null;
              if (sink) {
                try {
                  sink.focus({ preventScroll: true });
                } catch {}
              }
            }
          }}
          className={cn(
            "relative flex-1 min-w-0 flex items-center min-h-[40px] px-1",
            isLoading || isOffline ? "cursor-not-allowed select-none opacity-60" : "cursor-text"
          )}
        >
          {/* Placeholder tự nhiên khi khung nhập rỗng */}
          {!hasContent && (
            <div
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#8C4905]/50 pointer-events-none text-xs sm:text-sm font-medium truncate select-none"
            >
              {cooldownSeconds && cooldownSeconds > 0 ? (
                <span className="text-[#C1762A] font-semibold flex items-center gap-1">
                  <span>Vui lòng đợi {cooldownSeconds}s trước khi gửi tiếp... ⏳</span>
                </span>
              ) : isOffline ? (
                "Mất kết nối. Đang chờ kết nối lại..."
              ) : isLoading ? (
                <span className="flex items-center gap-1.5 text-[#C1762A] animate-pulse">
                  <span>SocraticKid đang trả lời, vui lòng đợi... 🦉</span>
                </span>
              ) : (
                "Hỏi SocraticKid..."
              )}
            </div>
          )}

          {isMounted ? (
            React.createElement("math-field", {
              ref: onMathFieldRef,
              "math-virtual-keyboard-policy": "manual",
              disabled: isLoading || isOffline ? "true" : undefined,
              "read-only": isLoading || isOffline ? "true" : undefined,
              class: cn(
                "w-full outline-none border-none bg-transparent font-medium text-base leading-normal",
                isLoading || isOffline
                  ? "text-[#1C1917]/40 cursor-not-allowed pointer-events-none"
                  : "text-[#1C1917] cursor-text"
              ),
              style: {
                "--primary-color": "#C1762A",
                "--caret-color": "#8C4905",
                "--selection-background-color": "rgba(193, 118, 42, 0.25)",
                "--contains-highlight-background-color": "rgba(193, 118, 42, 0.12)",
                "--text-highlight-background-color": "transparent",
                "--placeholder-color": "#8C4905",
                "--placeholder-opacity": "0.75",
                "--socratic-mf-max-height": isExpanded
                  ? "min(396px, calc(100dvh - 240px))"
                  : "156px",
                display: "block",
                width: "100%",
                minHeight: "36px",
                maxHeight: isExpanded ? "min(396px, calc(100dvh - 240px))" : "156px",
                overflowY: "auto",
                overflowX: "hidden",
                boxSizing: "border-box",
              } as React.CSSProperties,
            })
          ) : (
            <div className="w-full min-h-[36px]" />
          )}
        </div>

        {/* ── Cặp Chevron chuẩn Google Math Solver (ở góc phải khung nhập) ── */}
        <div className="hidden sm:flex flex-col items-center justify-center text-[#8C4905]/40 select-none shrink-0 self-end mb-2.5 px-1">
          <ChevronUp className="w-3.5 h-3.5 -mb-1 stroke-[2.5]" />
          <ChevronDown className="w-3.5 h-3.5 stroke-[2.5]" />
        </div>

        {/* Nút Xuống dòng (bên trái nút Gửi) */}
        <button
          id="chat-newline-btn"
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleInsertNewLine}
          disabled={isLoading || isOffline}
          aria-label="Xuống dòng"
          title="Xuống dòng (Shift + Enter)"
          className={cn(
            "p-2.5 rounded-full flex items-center justify-center transition-colors duration-150 self-end shrink-0 focus-visible:outline-2 focus-visible:outline-[#C1762A]",
            !isLoading && !isOffline
              ? "bg-[#F1CCA6]/70 text-[#8C4905] hover:bg-[#F1CCA6] active:scale-[0.95] cursor-pointer"
              : "bg-[#F1CCA6]/40 text-[#8C4905]/40 cursor-not-allowed opacity-60"
          )}
        >
          <CornerDownLeft size={20} />
        </button>

        {/* Nút Gửi */}
        <button
          id="chat-send-btn"
          onClick={handleSend}
          disabled={!canSend || isLoading || isOffline}
          className={cn(
            "p-2.5 rounded-full flex items-center justify-center transition-colors duration-150 self-end shadow-xs shrink-0 focus-visible:outline-2 focus-visible:outline-[#C1762A]",
            canSend && !isLoading && !isOffline
              ? "bg-[#C1762A] text-white hover:bg-[#8C4905] active:scale-[0.95] cursor-pointer"
              : "bg-[#F1CCA6]/40 text-[#8C4905]/40 cursor-not-allowed opacity-60"
          )}
          title={
            cooldownSeconds && cooldownSeconds > 0
              ? `Vui lòng đợi ${cooldownSeconds}s trước khi gửi tiếp`
              : isOffline
              ? "Không thể gửi khi mất kết nối"
              : isLoading
              ? "SocraticKid đang phản hồi, vui lòng đợi..."
              : "Gửi tin nhắn"
          }
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-[#8C4905]/30 border-t-[#C1762A] rounded-full animate-spin" />
          ) : cooldownSeconds && cooldownSeconds > 0 ? (
            <span className="text-xs font-bold text-[#8C4905] min-w-[20px] text-center">
              {cooldownSeconds}s
            </span>
          ) : (
            <Send size={20} className={cn(canSend && !isOffline && "ml-0.5")} />
          )}
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
