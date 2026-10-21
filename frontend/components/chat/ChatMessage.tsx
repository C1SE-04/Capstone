/**
 * File: components/chat/ChatMessage.tsx
 * Mô tả: Component chịu trách nhiệm render từng dòng tin nhắn (bong bóng chat).
 * Hỗ trợ render Markdown và các công thức toán học (KaTeX) đối với tin nhắn từ AI (Assistant).
 * Tin nhắn của người dùng sẽ hiển thị dạng văn bản thô, lệch về bên phải.
 * US4.1: Hiển thị 2 nút "Đã hiểu" / "Chưa hiểu" sau tin nhắn cuối cùng của AI.
 */
"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm"; // Hỗ trợ cú pháp GitHub Flavored Markdown (như table, strikethrough)
import remarkMath from "remark-math"; // Hỗ trợ cú pháp toán học (dấu $ hoặc $$)
import rehypeKatex from "rehype-katex"; // Biến đổi cú pháp toán học thành HTML chuẩn KaTeX
import { AlertCircle, RotateCcw, Loader2, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Message } from "@/types/chat";
import { UnderstandingButtons } from "./UnderstandingButtons";
import { ImageZoomModal } from "./ImageZoomModal";
import { SaveBookmarkButton } from "./SaveBookmarkButton";

export type MessageProps = Message;

interface ChatMessageProps {
  message: Message;
  onRetry?: (messageId: string, content: string) => void;
  /** US4.1: Cac callback chi truyen vao tin nhan AI cuoi cung de hien nut Da hieu/Chua hieu */
  onUnderstood?: () => void;
  onNotUnderstood?: () => void;
  onSendExplanation?: (text: string) => void;
  /** Truyen xuong de disable nut khi AI dang xu ly */
  isAiLoading?: boolean;
  /** US4.1: So lan nhan Chua hieu (tu ChatPage, khong bi reset khi remount) */
  notUnderstoodCount?: number;
  /** T7.17: Session ID hien tai de luu vao So tay */
  sessionId?: string | null;
}

export function ChatMessage({
  message,
  onRetry,
  onUnderstood,
  onNotUnderstood,
  onSendExplanation,
  isAiLoading,
  notUnderstoodCount = 0,
  sessionId,
}: ChatMessageProps) {
  // Biến cờ kiểm tra xem tin nhắn có phải của user hay không
  const isUser = message.role === "user";
  const isError = message.status === "error";
  const isSending = message.status === "sending";

  // State quản lý xem ảnh phóng to ở giữa màn hình
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Lắng nghe phím Escape và khóa cuộn trang khi đang mở ảnh
  useEffect(() => {
    if (!isPreviewOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
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

  return (
    // Wrap chính: flex để đẩy bong bóng sang phải (user) hoặc trái (assistant)
    <div className={cn("flex w-full mb-6", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("flex flex-col max-w-[85%] md:max-w-[75%]", isUser ? "items-end" : "items-start")}>
        {/* Bong bóng chat */}
        <div
          className={cn(
            "px-5 py-4 rounded-2xl shadow-sm text-[15px] leading-relaxed transition-all",
            isUser
              ? isError
                ? "bg-red-50 text-red-900 border border-red-300 rounded-tr-sm"
                : "bg-[#C1762A] text-white rounded-tr-sm"
              : message.emotion === "correct"
              ? "bg-gradient-to-br from-emerald-50 to-green-50 border-2 border-emerald-300 text-stone-900 rounded-tl-sm animate-in fade-in zoom-in-95 duration-500"
              : "bg-white border border-[#F1CCA6] text-stone-900 rounded-tl-sm",
            isSending && "opacity-80"
          )}
        >
          {isUser ? (
            // Tin nhắn của user: hỗ trợ hiển thị ảnh đính kèm và giữ nguyên ngắt dòng tự nhiên
            <div className="flex flex-col gap-2">
              {message.attachment_url && (
                <>
                  <div
                    onClick={() => setIsPreviewOpen(true)}
                    className="group relative rounded-xl overflow-hidden max-w-[260px] max-h-[260px] bg-black/10 border border-white/20 shadow-sm cursor-pointer"
                    title="Bấm để xem ảnh đề bài phóng to"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={message.attachment_url}
                      alt="Ảnh đính kèm bài toán"
                      className="w-full h-auto max-h-[240px] object-contain rounded-xl transition-all duration-200 group-hover:scale-[1.02] group-hover:brightness-95"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/25 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <span className="bg-black/70 backdrop-blur-sm text-white text-xs font-medium px-2.5 py-1.5 rounded-lg flex items-center gap-1.5 shadow-md">
                        <Maximize2 size={13} />
                        Xem đề bài
                      </span>
                    </div>
                  </div>

                  {/* Modal phóng to ảnh chuyên dụng đầy đủ tính năng */}
                  <ImageZoomModal
                    isOpen={isPreviewOpen}
                    imageUrl={message.attachment_url || null}
                    imageTitle="Ảnh bài toán đề bài"
                    onClose={() => setIsPreviewOpen(false)}
                  />
                </>
              )}
              {message.content && (
                <div className="whitespace-pre-wrap flex items-start gap-2">
                  <span className="flex-1">{message.content}</span>
                  {isSending && (
                    <Loader2 size={16} className="animate-spin text-white/80 shrink-0 mt-1" />
                  )}
                </div>
              )}
              {!message.content && isSending && (
                <div className="flex items-center gap-2 text-white/80 text-xs">
                  <Loader2 size={14} className="animate-spin" />
                  <span>Đang gửi ảnh bài toán...</span>
                </div>
              )}
            </div>
          ) : message.content === "" ? (
            // Tin nhắn của assistant đang trống (đang suy nghĩ)
            <div className="flex items-center gap-1.5 h-6">
              <span className="text-xs text-[#8C4905] mr-1 font-medium">SocraticKid đang nghĩ</span>
              <div className="w-2 h-2 bg-[#C1762A] rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-2 h-2 bg-[#C1762A] rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-2 h-2 bg-[#C1762A] rounded-full animate-bounce"></div>
            </div>
          ) : (
            // Tin nhắn của assistant: Cần render thành Markdown và Toán học.
            // Sử dụng các class `prose-*` của Tailwind (hoặc tùy chỉnh thủ công) để định dạng các thẻ HTML (h1, p, pre, code, table) bên trong Markdown.
            <div className="markdown-prose prose-sm max-w-none text-stone-900 
              prose-p:leading-relaxed prose-p:mb-3 
              prose-pre:bg-[#D9D9D9]/30 prose-pre:text-[#8C4905] prose-pre:p-3 prose-pre:rounded-lg
              prose-code:text-[#CB6600] prose-code:bg-[#F1CCA6]/40 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded
              prose-ul:list-disc prose-ul:ml-4 prose-ul:mb-3
              prose-ol:list-decimal prose-ol:ml-4 prose-ol:mb-3
              prose-table:w-full prose-table:border-collapse prose-table:mb-3
              prose-th:border prose-th:border-[#C1762A]/30 prose-th:p-2 prose-th:bg-[#F1CCA6]/30 prose-th:text-left
              prose-td:border prose-td:border-[#C1762A]/20 prose-td:p-2
              prose-a:text-[#C1762A] hover:prose-a:text-[#8C4905] prose-a:underline
              prose-strong:text-[#8C4905]"
            >
              {/* Component ReactMarkdown thực hiện chức năng phân tích cú pháp chuỗi thành HTML */}
              <ReactMarkdown
                remarkPlugins={[remarkMath, remarkGfm]}
                rehypePlugins={[rehypeKatex]}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* T7.17: Nút ⭐ "Lưu vào Sổ tay" xuất hiện ngay dưới bong bóng chúc mừng khi học sinh đã hiểu */}
        {!isUser && message.emotion === "correct" && (
          <SaveBookmarkButton sessionId={sessionId} />
        )}

        {/* US4.1: Nut Da hieu / Chua hieu - chi hien duoi tin nhan cuoi cung cua AI */}
        {!isUser && onUnderstood && onNotUnderstood && onSendExplanation && (
          <UnderstandingButtons
            onUnderstood={onUnderstood}
            onNotUnderstood={onNotUnderstood}
            onSendExplanation={onSendExplanation}
            isLoading={isAiLoading}
            notUnderstoodCount={notUnderstoodCount}
          />
        )}

        {/* Thông báo lỗi & nút Thử lại khi tin nhắn gửi thất bại do mạng lag / offline */}
        {isUser && isError && (
          <div className="flex items-center gap-2 mt-1.5 mr-1 text-xs text-red-600 animate-in fade-in duration-200">
            <AlertCircle size={13} className="shrink-0" />
            <span>Gửi thất bại (lỗi mạng hoặc timeout)</span>
            {onRetry && (
              <button
                onClick={() => onRetry(message.id, message.content)}
                className="inline-flex items-center gap-1 font-semibold text-[#8C4905] bg-[#F1CCA6]/60 hover:bg-[#F1CCA6] px-2 py-0.5 rounded-full transition-colors ml-1"
                title="Gửi lại tin nhắn này"
              >
                <RotateCcw size={11} />
                Thử lại
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
