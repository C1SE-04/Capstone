"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { Conversation, Message } from "@/types/chat";
import { Menu } from "lucide-react";
import { useRouter } from "next/navigation";

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

  // Khởi tạo state trống để đợi load từ DB
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  // US4.1: Luu so lan nhan "Chua hieu" o cap page de state khong bi mat khi AI tra loi moi
  const [notUnderstoodCount, setNotUnderstoodCount] = useState(0);
  // Key tăng mỗi khi người dùng chọn chat cũ từ Sidebar
  // ChatWindow lắng nghe key này để trigger scroll-to-bottom ngay lập tức
  const [selectedChatKey, setSelectedChatKey] = useState(0);
  const isOnline = useSyncExternalStore(
    subscribeOnline,
    getOnlineSnapshot,
    getOnlineServerSnapshot,
  );

  // 1. Khôi phục danh sách conversations từ DB khi người dùng truy cập
  //    KHÔNG khôi phục activeChatId → luôn bắt đầu bằng New Chat trống hoàn toàn
  useEffect(() => {
    let isMounted = true;
    const fetchSessions = async () => {
      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)
          ?.access_token;

        if (token) {
          const BACKEND_URL =
            process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
          const res = await fetch(`${BACKEND_URL}/sessions`, {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (res.status === 401 && isMounted) {
            const { signOut } = await import("next-auth/react");
            signOut({ callbackUrl: "/" });
            return;
          }

          if (res.ok && isMounted) {
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0) {
              // Danh sach cac prompt ngam can loc bo khi hien thi lai lich su
              const HIDDEN_PROMPTS = [
                "Hoc sinh chua hieu cach giai thich tren. Hay giai thich lai theo cach khac, don gian va de hieu hon.",
                "Hoc sinh van chua hieu sau nhieu lan giai thich. Hay dua ra dap an chinh xac va giai thich tung buoc that ro rang.",
              ];
              const loadedConvs = data.map((sess: any) => ({
                id: sess.id,
                title: sess.title || "Phòng chat",
                date: new Date(sess.updated_at).toLocaleDateString("vi-VN"),
                messages: (sess.messages || [])
                  .map((m: any) => ({
                    id: m.id,
                    role: m.sender_type === "USER" ? "user" : "assistant",
                    content: m.content,
                  }))
                  // Loc bo cac prompt ngam de khong bi lo khi reload trang
                  .filter((m: any) => !(
                    m.role === "user" && HIDDEN_PROMPTS.includes(m.content.trim())
                  )),
              }));
              setConversations(loadedConvs);
            } else {
              setConversations([]);
            }
            // Luôn bắt đầu với New Chat trống (không restore activeChatId)
            setActiveChatId(null);
          }
        }
      } catch (e) {
        console.error("Lỗi đọc dữ liệu từ Server:", e);
      } finally {
        if (isMounted) setIsHydrated(true);
      }
    };
    fetchSessions();

    return () => {
      isMounted = false;
    };
  }, []);

  // Cuộc trò chuyện hiện tại đang được chọn
  const currentConversation = conversations.find((c) => c.id === activeChatId);
  const currentMessages = currentConversation
    ? currentConversation.messages
    : [];

  // Handler: Chọn phiên chat từ Sidebar
  // Tăng selectedChatKey để ChatWindow nhận biết và scroll xuống tin nhắn mới nhất
  const handleSelectChat = (id: string) => {
    setActiveChatId(id);
    setSelectedChatKey((prev) => prev + 1);
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
      // Sau khi xóa → quay về New Chat trống thay vì load chat khác
      setActiveChatId(null);
    }

    // 2. Gọi API để xóa trên Database
    try {
      const { getSession } = await import("next-auth/react");
      const nextAuthSession = await getSession();
      const token = (nextAuthSession as { access_token?: string } | null)
        ?.access_token;

      if (token) {
        const BACKEND_URL =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        await fetch(`${BACKEND_URL}/sessions/${id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
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

  // US4.1 - Handler: Hoc sinh nhan "Da hieu" -> them tin nhan chuc mung + doi dieu bo cu
  const handleUnderstood = () => {
    setNotUnderstoodCount(0);
    console.log("[US4.1] Hoc sinh da hieu bai.");

    // Chỉ thêm message chúc mừng khi đang có cuộc trò chuyện
    if (!activeChatId) return;

    const congratsMessages = [
      "**Tuyệt vời!** Em đã hiểu rồi! Thầy rất vui vì em nắm được vấn đề. Hãy tiếp tục phát huy nhé!",
      "**Xuất sắc!** Em đã hiểu bài rồi! Học toán mà hiểu được như vậy là rất giỏi đó. Tiếp tục nhé!",
      "**Giỏi lắm!** Em đã nắm được kiến thức này rồi! Mỗi câu hỏi hiểu được là một bước tiến lớn. Cứ tiếp tục học nhé!",
    ];
    const randomMsg = congratsMessages[Math.floor(Math.random() * congratsMessages.length)];
    const congratsId = `congrats-${Date.now()}`;

    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeChatId
          ? {
              ...c,
              messages: [
                ...c.messages,
                {
                  id: congratsId,
                  role: "assistant" as const,
                  content: randomMsg,
                  emotion: "correct",
                  isAnswerRevealed: false, // Không hiện lại nút Đã hiểu/Chưa hiểu
                },
              ],
            }
          : c
      )
    );

    // Con cú giữ nguyên trạng thái correct — không reset về idle
  };

  // US4.1 - Trigger AI giai thich lai (AN, khong them tin nhan user vao UI)
  // Nhan tham so prompt de tai su dung cho ca lan 1 (giai thich lai) va lan 5+ (dua dap an)
  const triggerSilentReexplain = async (conversationId: string, prompt: string) => {
    if (!conversationId) return;
    setIsTyping(true);
    const botMessageId = (Date.now() + 1).toString();
    const initialBotMsg: Message = {
      id: botMessageId,
      role: "assistant",
      content: "",
    };
    setConversations((prev) =>
      prev.map((c) =>
        c.id === conversationId
          ? { ...c, messages: [...c.messages, initialBotMsg] }
          : c,
      ),
    );
    try {
      let authHeader: Record<string, string> = {};
      let gradeLevel: number | undefined = undefined;
      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)
          ?.access_token;
        if (token) authHeader = { Authorization: `Bearer ${token}` };
        gradeLevel = (nextAuthSession as any)?.user?.grade_level;
      } catch {
        /* khong co session */
      }

      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${BACKEND_URL}/chat/orchestrator`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify({
          session_id: conversationId,
          prompt,
          problem_context: null,
          grade_level: gradeLevel ? Number(gradeLevel) : undefined,
        }),
      });
      if (!response.body) throw new Error("No stream");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";
      let lastEmotion: string | undefined = undefined;
      let isAnswerRevealedFlag = false;
      let isDone = false;
      while (!isDone) {
        const { value, done } = await reader.read();
        isDone = done;
        if (value) {
          const chunkStr = decoder.decode(value, { stream: true });
          for (const line of chunkStr.split("\n")) {
            if (line.startsWith("event: ask_comprehension")) {
              isAnswerRevealedFlag = true;
            }
            if (line.startsWith("data: ")) {
              const dataStr = line.slice(6).trim();
              if (!dataStr || dataStr === "{}") continue;
              try {
                const dataObj = JSON.parse(dataStr);
                if (dataObj.text) {
                  aiText += dataObj.text;
                }
                if (dataObj.emotion) {
                  lastEmotion = dataObj.emotion;
                }
                if (dataObj.text || dataObj.emotion || isAnswerRevealedFlag) {
                  setConversations((prev) =>
                    prev.map((c) =>
                      c.id === conversationId
                        ? {
                            ...c,
                            messages: c.messages.map((m) =>
                              m.id === botMessageId
                                ? {
                                    ...m,
                                    content: aiText,
                                    emotion: lastEmotion,
                                    isAnswerRevealed: isAnswerRevealedFlag,
                                  }
                                : m,
                            ),
                          }
                        : c,
                    ),
                  );
                }
              } catch {
                /* ignore parse error */
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("[US4.1] Loi goi lai AI:", error);
      const errMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: "Xin loi, khong the ket noi lai may chu.",
      };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId
            ? { ...c, messages: [...c.messages, errMsg] }
            : c,
        ),
      );
    } finally {
      setIsTyping(false);
    }
  };

  // US4.1 - Handler: Hoc sinh nhan "Chua hieu"
  // - Lan 1: AI giai thich lai theo cach khac (prompt ngam)
  // - Lan 2-4: Hien o nhap de hoc sinh tu giai thich phan chua hieu
  // - Lan 5+: AI dua ra dap an truc tiep va giai thich tung buoc (prompt ngam)
  const MAX_NOT_UNDERSTOOD = 5;
  const handleNotUnderstood = () => {
    const newCount = notUnderstoodCount + 1;
    setNotUnderstoodCount(newCount);
    if (newCount === 1 && activeChatId) {
      // Lan 1: Yeu cau AI giai thich lai theo cach khac
      triggerSilentReexplain(
        activeChatId,
        "Hoc sinh chua hieu cach giai thich tren. Hay giai thich lai theo cach khac, don gian va de hieu hon."
      );
    } else if (newCount >= MAX_NOT_UNDERSTOOD && activeChatId) {
      // Lan 5+: Hoc sinh van chua hieu -> dua ra dap an chinh xac
      triggerSilentReexplain(
        activeChatId,
        "Hoc sinh van chua hieu sau nhieu lan giai thich. Hay dua ra dap an chinh xac va giai thich tung buoc that ro rang."
      );
    }
    // Lan 2-4: Chi hien o nhap (xu ly o UnderstandingButtons, khong can goi AI)
  };

  // Hàm xử lý phản hồi từ AI (có xử lý lỗi mạng & trạng thái tin nhắn)
  const triggerBotResponse = async (
    targetConversationId: string,
    userMessageId: string,
    userContent: string,
  ) => {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === userMessageId ? { ...m, status: "error" } : m,
                ),
              }
            : c,
        ),
      );
      setIsTyping(false);
      return;
    }

    setIsTyping(true);

    try {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === targetConversationId
            ? {
                ...c,
                messages: c.messages.map((m) =>
                  m.id === userMessageId ? { ...m, status: "sent" } : m,
                ),
              }
            : c,
        ),
      );

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
            : c,
        ),
      );

      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      let authHeader: Record<string, string> = {};
      let gradeLevel: number | undefined = undefined;
      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)
          ?.access_token;
        if (token) {
          authHeader = { Authorization: `Bearer ${token}` };
        }
        gradeLevel = (nextAuthSession as any)?.user?.grade_level;
      } catch {
        // Không có session -> chat như khách
      }

      // Dummy problem_context (thực tế lấy từ state/context của ứng dụng)
      const problem_context = {
        correctSolution: "4",
      };

      let answer_status: string | null = null;
      // Trích xuất con số đầu tiên tìm thấy trong message
      const numberMatch = userContent.match(/\d+/);
      if (numberMatch) {
        if (numberMatch[0] === problem_context.correctSolution) {
          answer_status = "correct";
        } else {
          answer_status = "wrong";
        }
      }

      const response = await fetch(`${BACKEND_URL}/chat/orchestrator`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify({
          session_id: targetConversationId,
          prompt: userContent,
          problem_context: null,
          answer_status,
          grade_level: gradeLevel ? Number(gradeLevel) : undefined,
        }),
      });

      if (!response.body) throw new Error("Không có phản hồi từ server");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let aiText = "";
      let lastEmotion: string | undefined = undefined;
      let isAnswerRevealedFlag = false;
      let isDone = false;

      while (!isDone) {
        const { value, done } = await reader.read();
        isDone = done;
        if (value) {
          const chunkStr = decoder.decode(value, { stream: true });
          const lines = chunkStr.split("\n");
          for (const line of lines) {
            if (line.startsWith("event: ask_comprehension")) {
              isAnswerRevealedFlag = true;
            }
            if (line.startsWith("data: ")) {
              const dataStr = line.slice(6).trim();
              if (dataStr === "" || dataStr === "{}") continue;
              try {
                const dataObj = JSON.parse(dataStr);
                if (dataObj.text) {
                  aiText += dataObj.text;
                }
                // Parse emotion nếu server trả về
                if (dataObj.emotion) {
                  lastEmotion = dataObj.emotion;
                }
                // Cập nhật message với cả text, emotion, và cờ isAnswerRevealed mới nhất
                if (dataObj.text || dataObj.emotion || isAnswerRevealedFlag) {
                  setConversations((prev) =>
                    prev.map((c) =>
                      c.id === targetConversationId
                        ? {
                            ...c,
                            messages: c.messages.map((m) =>
                              m.id === botMessageId
                                ? {
                                    ...m,
                                    content: aiText,
                                    emotion: lastEmotion,
                                    isAnswerRevealed: isAnswerRevealedFlag,
                                  }
                                : m,
                            ),
                          }
                        : c,
                    ),
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
            : c,
        ),
      );
    } finally {
      setIsTyping(false);
    }
  };

  // Handler: Gửi prompt trong khung chat
  // isExplanation = true khi gui tu o UnderstandingButtons (onSendExplanation)
  // -> Khong reset notUnderstoodCount vi day la phan cua flow "Chua hieu"
  const handleSendMessage = async (content: string, isExplanation = false) => {
    // US4.1: Chi reset dem "Chua hieu" khi hoc sinh tu go tin nhan moi hoan toan,
    // khong reset khi gui giai thich tu UnderstandingButtons
    if (!isExplanation) {
      setNotUnderstoodCount(0);
    }

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

      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      let realSessionId: string | null = null;

      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)
          ?.access_token;

        if (token) {
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

      targetId = realSessionId || "c-" + Date.now();

      const nowStr = new Date().toLocaleDateString("vi-VN");
      const newConv: Conversation = {
        id: targetId,
        title,
        date: nowStr,
        messages: [userMsg],
      };

      setConversations((prev) => [newConv, ...prev]);
      setActiveChatId(targetId);
    } else {
      // Đã có phiên hội thoại: thêm tin nhắn + cập nhật timestamp sidebar
      const nowStr = new Date().toLocaleDateString("vi-VN");
      setConversations((prev) => {
        const updated = prev.map((c) =>
          c.id === targetId
            ? { ...c, messages: [...c.messages, userMsg], date: nowStr }
            : c,
        );
        // Đưa conversation đang chat lên đầu danh sách
        const idx = updated.findIndex((c) => c.id === targetId);
        if (idx > 0) {
          const [item] = updated.splice(idx, 1);
          updated.unshift(item);
        }
        return [...updated];
      });
    }

    if (!isOnline) {
      return;
    }

    triggerBotResponse(targetId, messageId, content);
  };

  // Handler: Thử lại (Retry) khi gửi tin nhắn thất bại
  const handleRetryMessage = (messageId: string, content: string) => {
    if (!activeChatId) return;

    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeChatId
          ? {
              ...c,
              messages: c.messages.map((m) =>
                m.id === messageId ? { ...m, status: "sending" } : m,
              ),
            }
          : c,
      ),
    );

    triggerBotResponse(activeChatId, messageId, content);
  };

  if (!isHydrated) {
    return (
      <div className="flex h-screen w-screen bg-[#F7ECE1] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[#8C4905] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-[#8C4905] font-medium">Đang tải dữ liệu...</p>
        </div>
      </div>
    );
  }

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
              onClick={() => router.push("/")}
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
            onUnderstood={handleUnderstood}
            onNotUnderstood={handleNotUnderstood}
            notUnderstoodCount={notUnderstoodCount}
            selectedChatKey={selectedChatKey}
          />
        </main>
      </div>
    </div>
  );
}
