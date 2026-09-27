/**
 * File: components/chat/ChatInput.tsx
 * Mô tả: Component nhập liệu cho khung chat.
 * Tính năng chính:
 * - Textarea tự động co giãn (auto-expand) dựa vào lượng text người dùng nhập.
 * - Hỗ trợ nhấn Enter để gửi, Shift+Enter để xuống dòng.
 * - Khóa nút gửi khi textarea trống hoặc khi AI đang bận phản hồi (isLoading).
 */
"use client";

import { useRef, useEffect, useState, KeyboardEvent } from "react";
import { Send, Paperclip } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading?: boolean; // Cờ kiểm tra AI đang xử lý
  isOffline?: boolean; // Cờ kiểm tra trạng thái mất mạng
}

export function ChatInput({ onSendMessage, isLoading, isOffline = false }: ChatInputProps) {
  // State lưu nội dung nhập
  const [content, setContent] = useState("");
  // Tham chiếu trực tiếp tới element <textarea> để thao tác thay đổi chiều cao DOM
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Hàm tự động điều chỉnh chiều cao của thẻ textarea
  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      // 1. Reset height về auto để lấy kích thước chính xác dựa trên scrollHeight
      textarea.style.height = "auto";
      // 2. Set chiều cao mới (giới hạn tối đa 150px)
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  };

  // Lắng nghe sự thay đổi của biến content để điều chỉnh chiều cao tương ứng
  useEffect(() => {
    adjustHeight();
  }, [content]);

  // Hàm xử lý bắt phím
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Nếu nhấn phím Enter VÀ không đè phím Shift
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // Tránh bị xuống dòng mặc định của textarea
      handleSend(); // Gọi hàm gửi tin nhắn
    }
  };

  // Hàm xử lý gửi tin nhắn
  const handleSend = () => {
    // Chỉ gửi khi nội dung không rỗng, AI không đang trả lời và mạng đang kết nối
    if (content.trim() && !isLoading && !isOffline) {
      onSendMessage(content.trim());
      setContent(""); // Xóa trắng textarea
      
      // Sau khi gửi, cần set cứng height về auto để khung nhập thu nhỏ lại ngay lập tức
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  return (
    // Wrapper cố định phần tử ở cuối (mt-auto)
    <div className="p-4 bg-transparent mt-auto relative z-10 w-full max-w-4xl mx-auto">
      {/* Vùng background bo góc chứa các nút và ô nhập liệu */}
      <div className={cn(
        "relative flex items-end gap-2 bg-[#F1CCA6]/40 p-2 pl-4 pr-2 rounded-3xl border border-[#C1762A]/20 shadow-sm focus-within:border-[#C1762A] focus-within:bg-white transition-all",
        isOffline && "opacity-75 bg-gray-100 border-gray-300"
      )}>
        
        {/* Nút đính kèm file */}
        <button
          disabled={isOffline}
          className="p-2.5 text-[#8C4905] hover:bg-[#F1CCA6] rounded-full transition-colors self-end mb-0.5 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Paperclip size={20} />
        </button>

        {/* Ô nhập liệu Textarea */}
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isOffline ? "Mất kết nối mạng. Đang chờ kết nối lại..." : "Hỏi SocraticKid bất cứ điều gì..."}
          className="flex-1 max-h-[150px] min-h-[44px] py-3 bg-transparent text-[#000000] placeholder:text-[#8C4905]/60 outline-none resize-none overflow-y-auto font-medium disabled:cursor-not-allowed"
          rows={1}
          disabled={isLoading || isOffline}
        />

        {/* Nút Gửi */}
        <button
          onClick={handleSend}
          disabled={!content.trim() || isLoading || isOffline}
          className={cn(
            "p-2.5 rounded-full flex items-center justify-center transition-all self-end mb-0.5 shadow-sm",
            content.trim() && !isLoading && !isOffline
              ? "bg-[#C1762A] text-white hover:bg-[#8C4905] hover:scale-105"
              : "bg-[#D9D9D9] text-gray-400 cursor-not-allowed"
          )}
          title={isOffline ? "Không thể gửi khi mất kết nối" : "Gửi tin nhắn"}
        >
          <Send size={20} className={cn(content.trim() && !isOffline && "ml-0.5")} />
        </button>
      </div>
      
      {/* Cảnh báo nhẹ dưới ô nhập liệu (UI/UX) */}
      <div className="text-center mt-2">
        <p className="text-xs text-[#8C4905]/60">AI có thể mắc lỗi. Vui lòng kiểm tra lại thông tin quan trọng.</p>
      </div>
    </div>
  );
}
