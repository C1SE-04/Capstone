"use client";

import { useRef, useEffect } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { Message } from "@/types/chat";
import { Sparkles } from "lucide-react";

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  onSendMessage: (content: string) => void;
}

export function ChatWindow({ messages, isTyping, onSendMessage }: ChatWindowProps) {
  // Ref dùng để xác định vị trí phần tử cuối cùng trong danh sách tin nhắn (phục vụ auto-scroll)
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  // Hàm tự động cuộn xuống dưới cùng của danh sách
  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Kích hoạt cuộn mỗi khi messages hoặc isTyping thay đổi
  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  return (
    // Container chính: lấp đầy khu vực main content
    <div className="flex flex-col h-full bg-[#F7ECE1] overflow-hidden">
      {/* Vùng hiển thị tin nhắn (Messages Area) */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth">
        <div className="max-w-4xl mx-auto flex flex-col min-h-full">
          {/* Hiển thị màn hình khởi tạo khi chưa có tin nhắn (New Chat) */}
          {messages.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-4 py-16 text-center animate-in fade-in duration-300">
              <div className="w-16 h-16 bg-[#F1CCA6] rounded-2xl flex items-center justify-center text-[#8C4905] shadow-inner">
                <Sparkles size={32} />
              </div>
              <h2 className="text-2xl font-bold text-[#8C4905]">
                Bắt đầu phiên học mới với SocraticKid
              </h2>
              <p className="text-[#C1762A] max-w-md text-sm leading-relaxed">
                Hãy đặt câu hỏi về Toán học (Đại số, Hình học, Phương trình...) hoặc bất kỳ bài toán nào bạn đang thắc mắc nhé!
              </p>
            </div>
          ) : (
            /* Render danh sách tin nhắn */
            <div className="flex flex-col justify-end flex-1">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}

              {/* Hiệu ứng bong bóng 3 dấu chấm (Typing indicator) */}
              {isTyping && (
                <div className="flex justify-start mb-6 w-full animate-in fade-in duration-300">
                  <div className="bg-white border border-[#F1CCA6] px-5 py-5 rounded-2xl rounded-tl-sm flex items-center gap-1 shadow-sm h-[52px]">
                    <div className="w-2 h-2 bg-[#C1762A] rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                    <div className="w-2 h-2 bg-[#C1762A] rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                    <div className="w-2 h-2 bg-[#C1762A] rounded-full animate-bounce"></div>
                  </div>
                </div>
              )}

              {/* Thẻ div rỗng nằm ở cuối để làm mốc cho hàm cuộn (scrollIntoView) */}
              <div ref={endOfMessagesRef} className="h-4" />
            </div>
          )}
        </div>
      </div>

      {/* Vùng nhập liệu (Input Area) ở dưới cùng */}
      <ChatInput onSendMessage={onSendMessage} isLoading={isTyping} />
    </div>
  );
}
