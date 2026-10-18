"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { Message } from "@/types/chat";
import { Sparkles, ArrowDown, WifiOff, RefreshCw } from "lucide-react";
import { AssistantOwl, OwlEmotion } from "./AssistantOwl";
// T6.15 – US 6.3: Hook phát hiện học sinh không tương tác 10 phút
import { useIdleTimer } from "@/hooks/useIdleTimer";
// T6.16 – US 6.3: Modal thông báo "Bạn vẫn đang học chứ?"
import { IdleModal } from "./IdleModal";

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  isOnline?: boolean;
  /**
   * Callback chính khi học sinh gửi tin nhắn.
   * @param content       - Nội dung text
   * @param isExplanation - True khi gọi từ nút "Chưa hiểu" (UnderstandingButtons)
   * @param image         - [T6.20] File ảnh đính kèm (từ ChatInput)
   */
  onSendMessage: (content: string, isExplanation?: boolean, image?: File) => void;
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
  /** T6.16: Session ID của cuộc hội thoại để gửi kèm restart timestamp */
  sessionId?: string;
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
  sessionId,
}: ChatWindowProps) {
  // Container cuộn của danh sách tin nhắn
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  // Ref dùng để xác định vị trí phần tử cuối cùng trong danh sách tin nhắn (phục vụ auto-scroll)
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  // T6.16 – US 6.3: Trạng thái hiển thị modal nhắc nhở khi học sinh idle
  const [isIdleModalOpen, setIsIdleModalOpen] = useState(false);

  // T6.15 – US 6.3: Idle Timer 10 phút
  // Hook tự khởi động khi component mount; gọi reset() mỗi khi học sinh gửi tin.
  // Khi timeout 10 phút → kích hoạt onIdle mở IdleModal.
  const { reset: resetIdleTimer } = useIdleTimer({
    timeout: 10 * 60 * 1000, // 10 phút theo đặc tả US 6.3
    onIdle: () => setIsIdleModalOpen(true),
    enabled: true,
  });

  /**
   * T6.16 – Khi học sinh bấm "Đang học" trong modal:
   * 1. Reset timer về 0 để tiếp tục đếm 10 phút mới.
   * 2. Đóng modal.
   */
  const handleContinueLearning = useCallback(() => {
    resetIdleTimer();
    setIsIdleModalOpen(false);
  }, [resetIdleTimer]);

  /**
   * T6.15/T6.20 – Wrapper tổng hợp của onSendMessage:
   * - Reset idle timer và đóng modal mỗi khi học sinh gửi tin nhắn.
   * - Truyền image (từ ChatInput) và isExplanation (từ UnderstandingButtons) lên ChatPage.
   */
  const handleSendMessage = useCallback(
    (content: string, isExplanationOrImage?: boolean | File, image?: File) => {
      setIsIdleModalOpen(false);
      resetIdleTimer();
      // Phân biệt 2 luồng gọi:
      // 1. Từ ChatInput: handleSendMessage(text, imageFile)
      // 2. Từ UnderstandingButtons: handleSendMessage(text, true)
      if (typeof isExplanationOrImage === "boolean") {
        onSendMessage(content, isExplanationOrImage, image);
      } else {
        // isExplanationOrImage là File hoặc undefined → luồng ChatInput
        onSendMessage(content, false, isExplanationOrImage);
      }
    },
    [resetIdleTimer, onSendMessage],
  );

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

  // Hàm tự động cuộn xuống dưới cùng của danh sách
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior,
      });
    } else {
      endOfMessagesRef.current?.scrollIntoView({ behavior });
    }
    // Khi đã gọi hàm cuộn xuống đáy -> chủ động ẩn nút và tắt cờ báo
    setShowScrollBottom(false);
    setHasNewMessage(false);
    setIsAutoScrollEnabled(true);
  }, []);

  // Xử lý sự kiện scroll để phát hiện vị trí người dùng
  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Khoảng cách từ vị trí cuộn hiện tại đến đáy
    const scrollBottomOffset =
      container.scrollHeight - container.scrollTop - container.clientHeight;

    // Ngưỡng phát hiện cuộn lên: chỉ khi người dùng cuộn lên cách đáy > 100px mới hiện nút
    const isScrolledUp = scrollBottomOffset > 100;
    setShowScrollBottom(isScrolledUp);
    setIsAutoScrollEnabled(!isScrolledUp);

    // Khi người dùng đã cuộn lại gần đáy (cách đáy <= 100px) thì tự động ẩn nút và xóa huy hiệu tin nhắn mới
    if (!isScrolledUp) {
      setHasNewMessage(false);
      setShowScrollBottom(false);
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

    const lastMsg = messages[messages.length - 1];
    const isUserJustSent = isNewMessageAdded && lastMsg?.role === "user";

    if (isUserJustSent) {
      // 1. Học sinh vừa gửi tin nhắn mới -> Luôn bật auto-scroll và cuộn ngay xuống đáy
      setIsAutoScrollEnabled(true);
      setShowScrollBottom(false);
      setHasNewMessage(false);
      scrollToBottom("smooth");
    } else if (isAutoScrollEnabled) {
      // 2. AI đang stream từng từ -> Cuộn trực tiếp (auto) để bám đáy 100%, không bị hủy animation giữa chừng
      scrollToBottom(isTyping ? "auto" : "smooth");
    } else if (isNewMessageAdded) {
      // 3. Người dùng đang chủ động cuộn lên xem lịch sử -> hiện huy hiệu có tin nhắn mới
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
        className="flex-1 overflow-y-auto p-4 md:p-6 relative"
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
                      onSendExplanation: (text: string) => handleSendMessage(text, true),
                      isAiLoading: isTyping,
                      notUnderstoodCount,
                    })}
                  />
                );
              })}

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

      {/* Footer Strip: cú + ô nhập liệu nằm cùng 1 hàng, cú không bao giờ đè tin nhắn */}
      <div className="flex flex-row items-end">
        <AssistantOwl emotion={currentEmotion} />
        <div className="flex-1 min-w-0">
          {/* [T6.20/T6.21] ChatInput: nhận text + ảnh đính kèm từ người dùng */}
          <ChatInput
            onSendMessage={(message, image) => handleSendMessage(message, image)}
            isLoading={isTyping}
            isOffline={!isOnline}
          />
        </div>
      </div>

      {/* T6.16 – US 6.3: Modal thông báo "Bạn vẫn đang học chứ? 🦉" */}
      <IdleModal
        isOpen={isIdleModalOpen}
        onContinue={handleContinueLearning}
        sessionId={sessionId}
      />
    </div>
  );
}

