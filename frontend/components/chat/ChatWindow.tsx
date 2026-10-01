"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { Message } from "@/types/chat";
import { Sparkles, ArrowDown, WifiOff, RefreshCw } from "lucide-react";
import { AssistantOwl, OwlEmotion } from "./AssistantOwl";

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  isOnline?: boolean;
  onSendMessage: (content: string, isExplanation?: boolean) => void;
  onRetryMessage?: (messageId: string, content: string) => void;
  onReconnect?: () => void;
  /** US4.1: Callbacks cho nut Da hieu / Chua hieu */
  onUnderstood?: () => void;
  onNotUnderstood?: () => void;
  /** US4.1: So lan nhan Chua hieu (quan ly o ChatPage de tranh bi reset khi remount) */
  notUnderstoodCount?: number;
  /**
   * Key tăng mỗi khi người dùng chọn một cuộc hội thoại cũ từ Sidebar.
   * Khi key thay đổi, ChatWindow sẽ scroll ngay xuống tin nhắn mới nhất.
   */
  selectedChatKey?: number;
}

export function ChatWindow({
  messages,
  isTyping,
  isOnline = true,
  onSendMessage,
  onRetryMessage,
  onReconnect,
  onUnderstood,
  onNotUnderstood,
  notUnderstoodCount = 0,
  selectedChatKey = 0,
}: ChatWindowProps) {
  // Container cuộn của danh sách tin nhắn
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  // Ref dùng để xác định vị trí phần tử cuối cùng trong danh sách tin nhắn (phục vụ auto-scroll)
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  // Xác định trạng thái cảm xúc của cú
  let currentEmotion: OwlEmotion = "idle";
  if (isTyping) {
    currentEmotion = "thinking";
  } else {
    const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
    if (lastAssistantMsg && lastAssistantMsg.emotion) {
      currentEmotion = lastAssistantMsg.emotion as OwlEmotion;
    }
  }

  // Trạng thái hiển thị nút cuộn xuống dưới
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  // Cờ báo có tin nhắn mới khi người dùng đang cuộn lên xem lịch sử
  const [hasNewMessage, setHasNewMessage] = useState(false);
  // Cờ điều khiển auto-scroll thông minh
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
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

    // Nếu cách đáy hơn 20px thì coi như người dùng đang cuộn lên để đọc
    const isScrolledUp = scrollBottomOffset > 20;
    setShowScrollBottom(isScrolledUp);
    // Bật tắt auto-scroll theo hành vi cuộn của người dùng
    setIsAutoScrollEnabled(!isScrolledUp);

    // Khi người dùng đã cuộn lại gần đáy thì tự động xóa huy hiệu tin nhắn mới
    if (!isScrolledUp) {
      setHasNewMessage(false);
    }
  };

  // Khi người dùng chọn một cuộc hội thoại cũ từ Sidebar (selectedChatKey thay đổi),
  // scroll ngay xuống dưới cùng bằng "instant" (không animation) để thấy tin nhắn mới nhất
  useEffect(() => {
    if (selectedChatKey === 0) return; // Bỏ qua lần mount đầu tiên
    setIsAutoScrollEnabled(true);
    // Dùng setTimeout nhỏ để đảm bảo DOM đã render xong danh sách tin nhắn
    const timer = setTimeout(() => {
      scrollToBottom("instant");
    }, 50);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedChatKey]);

  // Lắng nghe thay đổi messages hoặc isTyping để kích hoạt auto-scroll thông minh
  useEffect(() => {
    const isNewMessageAdded = messages.length > prevMessagesCountRef.current;
    prevMessagesCountRef.current = messages.length;

    // Nếu người dùng đang theo dõi phần mới nhất -> tự động cuộn
    if (isAutoScrollEnabled) {
      scrollToBottom("smooth");
    } else if (isNewMessageAdded) {
      // Nếu người dùng đang đọc ở trên -> không cưỡng bức cuộn, mà hiện thông báo tin nhắn mới
      setHasNewMessage(true);
    }
  }, [messages, isTyping, isAutoScrollEnabled, scrollToBottom]);

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
            <div className="flex flex-col justify-start flex-1 pt-2">
              {messages.map((msg, index) => {
                // US4.1: Chi truyen callbacks cho tin nhan AI cuoi cung (khong tinh khi AI dang typing)
                // - Chi hien khi AI dua ra dap an (msg.isAnswerRevealed = true)
                const isLastAssistantMsg =
                  !isTyping &&
                  msg.role === "assistant" &&
                  index === messages.length - 1 &&
                  msg.isAnswerRevealed === true;

                return (
                  <ChatMessage
                    key={msg.id}
                    message={msg}
                    onRetry={onRetryMessage}
                    {...(isLastAssistantMsg && {
                      onUnderstood,
                      onNotUnderstood,
                      onSendExplanation: (text: string) => onSendMessage(text, true),
                      isAiLoading: isTyping,
                      notUnderstoodCount,
                    })}
                  />
                );
              })}

              {/* Thẻ div rỗng nằm ở cuối để làm mốc cho hàm cuộn (scrollIntoView) và tạo padding bottom để không bị con cú che khuất */}
              <div ref={endOfMessagesRef} className="h-[150px] md:h-[260px]" />
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

      {/* Trợ lý ảo Cú */}
      <AssistantOwl emotion={currentEmotion} />
    </div>
  );
}

