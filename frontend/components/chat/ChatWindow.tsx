/**
 * File: components/chat/ChatWindow.tsx
 * Mô tả: Component chính hiển thị cửa sổ chat, bao gồm Header, Danh sách tin nhắn (Messages Area) và Ô nhập liệu (Input Area).
 * Chức năng: 
 * - Quản lý state danh sách tin nhắn (messages).
 * - Hiển thị trạng thái AI đang gõ chữ (isTyping).
 * - Tự động cuộn xuống cuối (auto-scroll) khi có tin nhắn mới.
 */
"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage, MessageProps } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { LessonCard } from "@/components/dashboard/LessonCard";
import { mockLessons } from "@/data/mockLessons";
import { useRouter } from "next/navigation";

// Dữ liệu mock ban đầu cho cuộc trò chuyện
const initialMockMessages: MessageProps[] = [
  {
    id: "m1",
    role: "assistant",
    content: "Chào bạn! Mình là SocraticKid. Mình có thể giúp gì cho bạn hôm nay?",
  },
  {
    id: "m2",
    role: "user",
    content: "Bạn có thể giải thích lại cho mình về phương trình bậc 2 được không?",
  },
  {
    id: "m3",
    role: "assistant",
    // Nội dung mock chứa Markdown và Math (KaTeX) để test khả năng render
    content: `Tất nhiên rồi! Dưới đây là phương trình bậc 2 dạng tổng quát:

$$ax^2 + bx + c = 0$$ (với $a \\neq 0$)

Để giải phương trình này, chúng ta tính biệt thức Delta ($\\Delta$):
$$\\Delta = b^2 - 4ac$$

Dựa vào $\\Delta$, ta có các trường hợp sau:
1. Nếu $\\Delta < 0$: Phương trình vô nghiệm.
2. Nếu $\\Delta = 0$: Phương trình có nghiệm kép $x = -\\frac{b}{2a}$.
3. Nếu $\\Delta > 0$: Phương trình có 2 nghiệm phân biệt:
$$x_{1,2} = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}$$

**Bảng tóm tắt:**
| $\\Delta$ | Số nghiệm |
| :--- | :--- |
| $< 0$ | 0 |
| $= 0$ | 1 (nghiệm kép) |
| $> 0$ | 2 (phân biệt) |

Bạn có muốn làm thử một bài tập ví dụ không?`,
  }
];

export function ChatWindow() {
  // State lưu trữ danh sách tin nhắn
  const [messages, setMessages] = useState<MessageProps[]>(initialMockMessages);
  
  // State hiển thị hiệu ứng "AI đang gõ chữ"
  const [isTyping, setIsTyping] = useState(false);
  
  const router = useRouter();
  
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

  // Hàm xử lý khi người dùng gửi tin nhắn mới
  const handleSendMessage = (content: string) => {
    // 1. Tạo tin nhắn mới của người dùng
    const newUserMsg: MessageProps = {
      id: Date.now().toString(),
      role: "user",
      content,
    };
    
    // 2. Thêm tin nhắn vào state và bật hiệu ứng typing
    setMessages((prev) => [...prev, newUserMsg]);
    setIsTyping(true);

    // 3. Giả lập thời gian chờ (delay) phản hồi từ AI (1.5s)
    setTimeout(() => {
      const aiResponse: MessageProps = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Đây là phản hồi mẫu từ AI. Mình nhận được câu hỏi của bạn: \n\n> " + content + "\n\nHiện tại mình đang trong quá trình thử nghiệm giao diện. Bạn có thắc mắc gì thêm không?",
      };
      // Thêm phản hồi của AI vào state và tắt hiệu ứng typing
      setMessages((prev) => [...prev, aiResponse]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    // Container chính: h-full để lấp đầy khu vực main content từ layout
    <div className="flex flex-col h-full bg-[#F7ECE1] overflow-hidden">

      {/* Vùng hiển thị tin nhắn (Messages Area) */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 scroll-smooth">
        <div className="max-w-4xl mx-auto flex flex-col min-h-full">

          {/* Hiển thị LessonCard gợi ý khi chưa có tin nhắn */}
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center gap-6 py-12">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-[#8C4905] mb-2">Xin chào! Bạn muốn học gì hôm nay?</h2>
                <p className="text-[#C1762A]">Đặt câu hỏi, hoặc chọn bài học bên dưới để bắt đầu.</p>
              </div>
              <div className="w-full max-w-sm">
                <LessonCard {...mockLessons[0]} onClick={() => router.push('/dashboard/chat')} />
              </div>
            </div>
          )}

          {/* Render danh sách tin nhắn */}
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
        </div>
      </div>

      {/* Vùng nhập liệu (Input Area) ở dưới cùng */}
      <ChatInput onSendMessage={handleSendMessage} isLoading={isTyping} />
    </div>
  );
}
