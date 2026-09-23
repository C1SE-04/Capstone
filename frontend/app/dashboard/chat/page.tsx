"use client";

import { useState, useEffect } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { Conversation, Message } from "@/types/chat";
import { Menu } from "lucide-react";
import { useRouter } from "next/navigation";

// Dữ liệu ban đầu mặc định cho bài học Toán học: Đại số (theo đúng yêu cầu & hình ảnh)
const defaultMathConversation: Conversation = {
  id: "c-math-1",
  title: "Toán học: Đại số",
  date: "Today",
  messages: [
    {
      id: "m1",
      role: "assistant",
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
    },
  ],
};

const STORAGE_KEY_CONVERSATIONS = "socratic_conversations";
const STORAGE_KEY_ACTIVE_ID = "socratic_active_chat_id";

export default function ChatPage() {
  const router = useRouter();

  // Khởi tạo state với dữ liệu mặc định ban đầu
  const [conversations, setConversations] = useState<Conversation[]>([defaultMathConversation]);
  const [activeChatId, setActiveChatId] = useState<string | null>("c-math-1");
  const [isTyping, setIsTyping] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  const [isOnline, setIsOnline] = useState(true);

  // Theo dõi trạng thái kết nối mạng của người dùng
  useEffect(() => {
    if (typeof window === "undefined") return;
    setIsOnline(navigator.onLine);

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  // 1. Khôi phục trạng thái từ localStorage khi người dùng F5 hoặc truy cập lại
  useEffect(() => {
    try {
      const savedConvs = localStorage.getItem(STORAGE_KEY_CONVERSATIONS);
      const savedActiveId = localStorage.getItem(STORAGE_KEY_ACTIVE_ID);

      if (savedConvs) {
        const parsed = JSON.parse(savedConvs);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setConversations(parsed);
        }
      }

      if (savedActiveId !== null) {
        setActiveChatId(savedActiveId === "" ? null : savedActiveId);
      }
    } catch (e) {
      console.error("Lỗi đọc dữ liệu từ localStorage:", e);
    } finally {
      setIsHydrated(true);
    }
  }, []);

  // 2. Lưu vào localStorage mỗi khi conversations hoặc activeChatId thay đổi
  useEffect(() => {
    if (!isHydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY_CONVERSATIONS, JSON.stringify(conversations));
      localStorage.setItem(STORAGE_KEY_ACTIVE_ID, activeChatId || "");
    } catch (e) {
      console.error("Lỗi ghi dữ liệu vào localStorage:", e);
    }
  }, [conversations, activeChatId, isHydrated]);

  // Cuộc trò chuyện hiện tại đang được chọn
  const currentConversation = conversations.find((c) => c.id === activeChatId);
  const currentMessages = currentConversation ? currentConversation.messages : [];

  // Handler: Chọn phiên chat từ Sidebar
  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
    setIsMobileOpen(false);
  };

  // Handler: Bấm nút "+ new chat" -> chuyển sang khung chat trống
  const handleNewChat = () => {
    setActiveChatId(null);
    setIsMobileOpen(false);
  };

  // Handler: Xóa một đoạn chat khỏi lịch sử
  const handleDeleteChat = (id: string) => {
    const updated = conversations.filter((c) => c.id !== id);
    setConversations(updated);
    if (activeChatId === id) {
      if (updated.length > 0) {
        setActiveChatId(updated[0].id);
      } else {
        setActiveChatId(null);
      }
    }
  };

  // Handler: Thử kết nối lại
  const handleReconnect = () => {
    if (typeof window !== "undefined") {
      setIsOnline(navigator.onLine);
    }
  };

  // Hàm xử lý phản hồi từ AI (có xử lý lỗi mạng & trạng thái tin nhắn)
  const triggerBotResponse = (targetConversationId: string, userMessageId: string, userContent: string) => {
    // Nếu mất mạng: chuyển ngay trạng thái tin nhắn thành "error"
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === userMessageId ? { ...m, status: "error" } : m
                ),
              }
            : c
        )
      );
      setIsTyping(false);
      return;
    }

    setIsTyping(true);

    // Giả lập bot Socratic Kid phản hồi (hoặc gọi API)
    setTimeout(() => {
      // Khi gửi thành công, chuyển status user message thành "sent"
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === userMessageId ? { ...m, status: "sent" } : m
                ),
              }
            : c
        )
      );

      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Tuyệt vời! Về câu hỏi: "${userContent}", bạn hãy suy nghĩ xem bước đầu tiên chúng ta cần xác định các hệ số hoặc công thức liên quan là gì nhé? Hãy thử nêu suy nghĩ của bạn!`,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? { ...c, messages: [...c.messages, botResponse] }
            : c
        )
      );
      setIsTyping(false);
    }, 1200);
  };

  // Handler: Gửi prompt trong khung chat
  const handleSendMessage = (content: string) => {
    const messageId = Date.now().toString();
    const userMsg: Message = {
      id: messageId,
      role: "user",
      content,
      status: isOnline ? "sending" : "error",
    };

    let targetId = activeChatId;

    if (!targetId) {
      // Trường hợp New Chat: tạo phiên hội thoại mới và thêm vào Sidebar
      targetId = "c-" + Date.now();
      const title =
        content.trim().length > 25
          ? content.trim().slice(0, 25) + "..."
          : content.trim();

      const newConv: Conversation = {
        id: targetId,
        title,
        date: "Today",
        messages: [userMsg],
      };

      setConversations((prev) => [newConv, ...prev]);
      setActiveChatId(targetId);
    } else {
      // Đã có phiên hội thoại: thêm tin nhắn vào phiên hiện tại
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetId
            ? { ...c, messages: [...c.messages, userMsg] }
            : c
        )
      );
    }

    if (!isOnline) {
      return;
    }

    triggerBotResponse(targetId, messageId, content);
  };

  // Handler: Thử lại (Retry) khi gửi tin nhắn thất bại
  const handleRetryMessage = (messageId: string, content: string) => {
    if (!activeChatId) return;

    // Chuyển lại trạng thái thành "sending"
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeChatId
          ? {
              ...c,
              messages: c.messages.map((m) =>
                m.id === messageId ? { ...m, status: "sending" } : m
              ),
            }
          : c
      )
    );

    triggerBotResponse(activeChatId, messageId, content);
  };

  return (
    <div className="flex h-screen w-screen bg-[#F7ECE1] overflow-hidden font-sans">
      {/* Sidebar bên trái */}
      <div
        className={`${
          isSidebarCollapsed ? "hidden" : "flex"
        } transition-all duration-300 h-full`}
      >
        <ChatSidebar
          isMobileOpen={isMobileOpen}
          setIsMobileOpen={setIsMobileOpen}
          conversations={conversations}
          activeChatId={activeChatId}
          onSelectChat={handleSelectChat}
          onNewChat={handleNewChat}
          onDeleteChat={handleDeleteChat}
        />
      </div>

      {/* Khu vực nội dung Chat bên phải */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Header nhỏ phía trên */}
        <header className="bg-white border-b border-[#F1CCA6] p-3 flex items-center justify-between shadow-sm z-30">
          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                if (typeof window !== "undefined" && window.innerWidth < 768) {
                  setIsMobileOpen(true);
                } else {
                  setIsSidebarCollapsed(!isSidebarCollapsed);
                }
              }}
              className="p-2 text-[#8C4905] hover:bg-[#F1CCA6]/50 rounded-lg transition-colors"
              title="Đóng / mở thanh bên"
            >
              <Menu size={22} />
            </button>
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => router.push("/dashboard")}
            >
              <div className="w-8 h-8 bg-[#D9D9D9] rounded-lg flex items-center justify-center text-[#8C4905] font-bold text-xs shadow-inner">
                SK
              </div>
              <span className="font-bold italic text-[#C1762A] text-base">
                SocraticKid
              </span>
            </div>
          </div>
        </header>

        {/* Khung chat */}
        <main className="flex-1 overflow-hidden">
          <ChatWindow
            messages={currentMessages}
            isTyping={isTyping}
            isOnline={isOnline}
            onSendMessage={handleSendMessage}
            onRetryMessage={handleRetryMessage}
            onReconnect={handleReconnect}
          />
        </main>
      </div>
    </div>
  );
}
