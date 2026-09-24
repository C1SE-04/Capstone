"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { Message } from "@/types/chat";
import { Sparkles, ArrowDown, WifiOff, RefreshCw } from "lucide-react";

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  isOnline?: boolean;
  onSendMessage: (content: string) => void;
  onRetryMessage?: (messageId: string, content: string) => void;
  onReconnect?: () => void;
}

export function ChatWindow({
  messages,
  isTyping,
  isOnline = true,
  onSendMessage,
  onRetryMessage,
  onReconnect,
}: ChatWindowProps) {
  // Container cuộn của danh sách tin nhắn
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  // Ref dùng để xác định vị trí phần tử cuối cùng trong danh sách tin nhắn (phục vụ auto-scroll)
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  // Trạng thái hiển thị nút cuộn xuống dưới
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  // Cờ báo có tin nhắn mới khi người dùng đang cuộn lên xem lịch sử
  const [hasNewMessage, setHasNewMessage] = useState(false);
  // Lưu số lượng tin nhắn trước đó để phát hiện tin nhắn mới
  const prevMessagesCountRef = useRef(messages.length);

  // Hàm tự động cuộn xuống dưới cùng của danh sách với hiệu ứng mượt
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    endOfMessagesRef.current?.scrollIntoView({ behavior });
    setHasNewMessage(false);
  }, []);

  // Xử lý sự kiện scroll để phát hiện vị trí người dùng
  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Khoảng cách từ vị trí cuộn hiện tại đến đáy
    const scrollBottomOffset =
      container.scrollHeight - container.scrollTop - container.clientHeight;

    // Nếu cách đáy hơn 120px thì coi như người dùng đang cuộn lên để đọc
    const isScrolledUp = scrollBottomOffset > 120;
    setShowScrollBottom(isScrolledUp);

    // Khi người dùng đã cuộn lại gần đáy thì tự động xóa huy hiệu tin nhắn mới
    if (!isScrolledUp) {
      setHasNewMessage(false);
    }
  };

  // Lắng nghe thay đổi messages hoặc isTyping để kích hoạt auto-scroll thông minh
  useEffect(() => {
    const isNewMessageAdded = messages.length > prevMessagesCountRef.current;
    prevMessagesCountRef.current = messages.length;

    const container = scrollContainerRef.current;
    const isNearBottom =
      container
        ? container.scrollHeight - container.scrollTop - container.clientHeight <= 150
        : true;

    // Nếu người dùng đang ở gần đáy hoặc vừa bắt đầu gõ -> tự động cuộn xuống
    if (isNearBottom) {
      scrollToBottom("smooth");
    } else if (isNewMessageAdded) {
      // Nếu người dùng đang đọc ở trên -> không cưỡng bức cuộn, mà hiện thông báo tin nhắn mới
      setHasNewMessage(true);
    }
  }, [messages, isTyping, scrollToBottom]);

  return (
    // Container chính: lấp đầy khu vực main content
    <div className="flex flex-col h-full bg-[#F7ECE1] overflow-hidden relative">
      {/* Banner cảnh báo khi mất kết nối mạng hoặc lag */}
      {!isOnline && (
        <div className="bg-amber-500/90 text-white text-xs md:text-sm px-4 py-2 flex items-center justify-between shadow-sm z-20 animate-in slide-in-from-top duration-300">
          <div className="flex items-center gap-2">
            <WifiOff size={16} className="animate-pulse shrink-0" />
            <span className="font-medium">
              Mất kết nối Internet hoặc mạng không ổn định. Tin nhắn của bạn có thể bị chậm trễ.
            </span>
          </div>
          {onReconnect && (
            <button
              onClick={onReconnect}
              className="flex items-center gap-1 bg-white/20 hover:bg-white/30 px-2.5 py-1 rounded text-xs font-semibold transition-colors shrink-0 ml-2"
            >
              <RefreshCw size={12} />
              Thử kết nối lại
            </button>
          )}
        </div>
      )}

      {/* Vùng hiển thị tin nhắn (Messages Area) */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth relative"
      >
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
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  onRetry={onRetryMessage}
                />
              ))}

              {/* Hiệu ứng bong bóng 3 dấu chấm (Typing indicator) */}
              {isTyping && (
                <div className="flex justify-start mb-6 w-full animate-in fade-in duration-300">
                  <div className="bg-white border border-[#F1CCA6] px-5 py-5 rounded-2xl rounded-tl-sm flex items-center gap-1.5 shadow-sm h-[52px]">
                    <span className="text-xs text-[#8C4905] mr-1 font-medium">SocraticKid đang nghĩ</span>
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

      {/* Nút bấm nổi "Cuộn xuống đáy" (Floating Scroll-to-Bottom Button) */}
      {showScrollBottom && (
        <div className="absolute bottom-24 right-6 md:right-10 z-20 animate-in fade-in zoom-in-95 duration-200">
          <button
            onClick={() => scrollToBottom("smooth")}
            className="flex items-center gap-1.5 bg-[#C1762A] hover:bg-[#8C4905] text-white px-3.5 py-2 rounded-full shadow-lg transition-all transform hover:scale-105 active:scale-95 text-xs font-semibold"
            title="Cuộn xuống tin nhắn mới nhất"
          >
            <ArrowDown size={15} />
            {hasNewMessage ? (
              <span className="flex items-center gap-1">
                <span>Tin nhắn mới</span>
                <span className="w-2 h-2 bg-yellow-300 rounded-full animate-ping" />
              </span>
            ) : (
              <span>Xuống dưới</span>
            )}
          </button>
        </div>
      )}

      {/* Vùng nhập liệu (Input Area) ở dưới cùng */}
      <ChatInput
        onSendMessage={onSendMessage}
        isLoading={isTyping}
        isOffline={!isOnline}
      />
    </div>
  );
}

