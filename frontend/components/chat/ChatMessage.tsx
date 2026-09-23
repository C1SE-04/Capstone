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
import { cn } from "@/lib/utils";

// Định nghĩa cấu trúc của một object Message
export interface MessageProps {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface ChatMessageProps {
  message: MessageProps;
}

export function ChatMessage({ message }: ChatMessageProps) {
  // Biến cờ kiểm tra xem tin nhắn có phải của user hay không
  const isUser = message.role === "user";

  return (
    // Wrap chính: flex để đẩy bong bóng sang phải (user) hoặc trái (assistant)
    <div className={cn("flex w-full mb-6", isUser ? "justify-end" : "justify-start")}>
      <div className={cn("flex max-w-[85%] md:max-w-[75%]", isUser ? "flex-row-reverse" : "flex-row")}>
        {/* Bong bóng chat */}
        <div
          className={cn(
            "px-5 py-4 rounded-2xl shadow-sm text-[15px] leading-relaxed",
            isUser
              ? "bg-[#C1762A] text-white rounded-tr-sm"
              : "bg-white border border-[#F1CCA6] text-[#000000] rounded-tl-sm"
          )}
        >
          {isUser ? (
            // Tin nhắn của user: giữ nguyên ngắt dòng tự nhiên bằng whitespace-pre-wrap
            <div className="whitespace-pre-wrap">{message.content}</div>
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
      </div>
    </div>
  );
}
