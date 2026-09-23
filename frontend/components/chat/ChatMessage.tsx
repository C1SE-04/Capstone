/**
 * File: components/chat/ChatMessage.tsx
 * Mô tả: Component chịu trách nhiệm render từng dòng tin nhắn (bong bóng chat).
 * Hỗ trợ render Markdown và các công thức toán học (KaTeX) đối với tin nhắn từ AI (Assistant).
 * Tin nhắn của người dùng sẽ hiển thị dạng văn bản thô, lệch về bên phải.
 */
"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm"; // Hỗ trợ cú pháp GitHub Flavored Markdown (như table, strikethrough)
import remarkMath from "remark-math"; // Hỗ trợ cú pháp toán học (dấu $ hoặc $$)
import rehypeKatex from "rehype-katex"; // Biến đổi cú pháp toán học thành HTML chuẩn KaTeX
import { AlertCircle, RotateCcw, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Message } from "@/types/chat";

export interface MessageProps extends Message {}

interface ChatMessageProps {
  message: Message;
  onRetry?: (messageId: string, content: string) => void;
}

export function ChatMessage({ message, onRetry }: ChatMessageProps) {
  // Biến cờ kiểm tra xem tin nhắn có phải của user hay không
  const isUser = message.role === "user";
  const isError = message.status === "error";
  const isSending = message.status === "sending";

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
              : "bg-white border border-[#F1CCA6] text-[#000000] rounded-tl-sm",
            isSending && "opacity-80"
          )}
        >
          {isUser ? (
            // Tin nhắn của user: giữ nguyên ngắt dòng tự nhiên bằng whitespace-pre-wrap
            <div className="whitespace-pre-wrap flex items-start gap-2">
              <span className="flex-1">{message.content}</span>
              {isSending && (
                <Loader2 size={16} className="animate-spin text-white/80 shrink-0 mt-1" />
              )}
            </div>
          ) : (
            // Tin nhắn của assistant: Cần render thành Markdown và Toán học.
            // Sử dụng các class `prose-*` của Tailwind (hoặc tùy chỉnh thủ công) để định dạng các thẻ HTML (h1, p, pre, code, table) bên trong Markdown.
            <div className="markdown-prose prose-sm max-w-none text-[#000000] 
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
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

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
