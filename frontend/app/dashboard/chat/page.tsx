"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
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

function subscribeOnline(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getOnlineSnapshot() {
  return typeof navigator !== "undefined" ? navigator.onLine : true;
}

function getOnlineServerSnapshot() {
  return true;
}

export default function ChatPage() {
  const router = useRouter();

  // Khởi tạo state với dữ liệu mặc định ban đầu
  const [conversations, setConversations] = useState<Conversation[]>([defaultMathConversation]);
  const [activeChatId, setActiveChatId] = useState<string | null>("c-math-1");
  const [isTyping, setIsTyping] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  const isOnline = useSyncExternalStore(subscribeOnline, getOnlineSnapshot, getOnlineServerSnapshot);

  // 1. Khôi phục trạng thái từ DB khi người dùng truy cập
  useEffect(() => {
    let isMounted = true;
    const fetchSessions = async () => {
      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)?.access_token;
        
        if (token) {
          const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
          const res = await fetch(`${BACKEND_URL}/sessions`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          
          if (res.ok && isMounted) {
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0) {
              // Convert backend data to frontend Conversation format
              const loadedConvs = data.map((sess: any) => ({
                id: sess.id,
                title: sess.title || "Phòng chat",
                date: new Date(sess.updated_at).toLocaleDateString(),
                messages: (sess.messages || []).map((m: any) => ({
                  id: m.id,
                  role: m.sender_type === "USER" ? "user" : "assistant",
                  content: m.content
                }))
              }));
              setConversations(loadedConvs);
              
              // Nếu activeChatId không nằm trong danh sách load về, set lại cái đầu tiên
              const activeIdExists = loadedConvs.some((c: any) => c.id === activeChatId);
              if (!activeIdExists && loadedConvs.length > 0) {
                setActiveChatId(loadedConvs[0].id);
              }
            } else {
              // Nếu user chưa có session nào ở DB, có thể tạo 1 session mặc định hoặc để trống
              // Nhưng API backend chưa tạo, tạm thời giữ nguyên hoặc khởi tạo trống
              setConversations([]);
              setActiveChatId(null);
            }
          }
        }
      } catch (e) {
        console.error("Lỗi đọc dữ liệu từ Server:", e);
      } finally {
        if (isMounted) setIsHydrated(true);
      }
    };
    fetchSessions();
    
    return () => { isMounted = false; };
  }, []);

  // 2. localStorage backup for active chat state (optional, can be removed)
  useEffect(() => {
    if (!isHydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY_ACTIVE_ID, activeChatId || "");
    } catch (e) {
      console.error("Lỗi ghi dữ liệu vào localStorage:", e);
    }
  }, [activeChatId, isHydrated]);

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
  const handleDeleteChat = async (id: string) => {
    // 1. Cập nhật state UI ngay lập tức
    const updated = conversations.filter((c) => c.id !== id);
    setConversations(updated);
    if (activeChatId === id) {
      if (updated.length > 0) {
        setActiveChatId(updated[0].id);
      } else {
        setActiveChatId(null);
      }
    }

    // 2. Gọi API để xóa trên Database (nếu đã đăng nhập)
    try {
      const { getSession } = await import("next-auth/react");
      const nextAuthSession = await getSession();
      const token = (nextAuthSession as { access_token?: string } | null)?.access_token;
      
      if (token) {
        const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        await fetch(`${BACKEND_URL}/sessions/${id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` }
        });
      }
    } catch (e) {
      console.error("Lỗi xóa session trên Server:", e);
    }
  };

  // Handler: Thử kết nối lại
  const handleReconnect = () => {
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event(navigator.onLine ? "online" : "offline"));
    }
  };

  // Hàm xử lý phản hồi từ AI (có xử lý lỗi mạng & trạng thái tin nhắn)
  const triggerBotResponse = async (targetConversationId: string, userMessageId: string, userContent: string) => {
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

    try {
      // Khi bắt đầu gửi thì đổi status của tin nhắn user thành "sent"
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

      // Tạo tin nhắn AI rỗng ban đầu để chuẩn bị stream
      const botMessageId = (Date.now() + 1).toString();
      const initialBotMsg: Message = {
        id: botMessageId,
        role: "assistant",
        content: "",
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? { ...c, messages: [...c.messages, initialBotMsg] }
            : c
        )
      );

      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      // Lấy access_token từ session NextAuth (nếu đang đăng nhập)
      let authHeader: Record<string, string> = {};
      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)?.access_token;
        if (token) {
          authHeader = { Authorization: `Bearer ${token}` };
        }
      } catch {
        // Không có session -> chat như khách
      }

      const response = await fetch(`${BACKEND_URL}/chat/orchestrator`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify({
          session_id: targetConversationId,
          prompt: userContent,
          problem_context: null,
        }),
      });

      if (!response.body) throw new Error("Không có phản hồi từ server");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";
      let isDone = false;

      while (!isDone) {
        const { value, done } = await reader.read();
        isDone = done;
        if (value) {
          const chunkStr = decoder.decode(value, { stream: true });
          const lines = chunkStr.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.slice(6).trim();
              if (dataStr === "" || dataStr === "{}") continue;
              try {
                const dataObj = JSON.parse(dataStr);
                if (dataObj.text) {
                  aiText += dataObj.text;
                  setConversations((prev) =>
                    prev.map((c) =>
                      c.id === targetConversationId
                        ? {
                            ...c,
                            messages: c.messages.map((m) =>
                              m.id === botMessageId ? { ...m, content: aiText } : m
                            ),
                          }
                        : c
                    )
                  );
                }
              } catch {
                // Ignore parse error on partial chunks
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("Lỗi khi kết nối backend:", error);
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: "Xin lỗi, đã có lỗi kết nối tới máy chủ.",
      };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? { ...c, messages: [...c.messages, errorMsg] }
            : c
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  // Handler: Gửi prompt trong khung chat
  const handleSendMessage = async (content: string) => {
    const messageId = Date.now().toString();
    const userMsg: Message = {
      id: messageId,
      role: "user",
      content,
      status: isOnline ? "sending" : "error",
    };

    let targetId = activeChatId;

    if (!targetId) {
      // Trường hợp New Chat: cần tạo Session trên DB trước, rồi mới chat
      const title =
        content.trim().length > 25
          ? content.trim().slice(0, 25) + "..."
          : content.trim();

      // Tạo session thật trên DB (gọi POST /sessions)
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      let realSessionId: string | null = null;

      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)?.access_token;

        if (token) {
          // Người dùng đã đăng nhập → tạo session trên DB
          const res = await fetch(`${BACKEND_URL}/sessions`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ title }),
          });
          if (res.ok) {
            const data = await res.json();
            realSessionId = data.id;
          }
        }
      } catch (e) {
        console.error("Không thể tạo session trên DB:", e);
      }

      // Nếu chưa đăng nhập hoặc tạo session thất bại → dùng ID local tạm thời
      targetId = realSessionId || ("c-" + Date.now());

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
