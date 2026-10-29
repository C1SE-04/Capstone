"use client";

import { useState, useEffect, useMemo, useCallback, useSyncExternalStore } from "react";
import { useSession } from "next-auth/react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatRightSidebar, ExerciseImage } from "@/components/chat/ChatRightSidebar";
import { ImageZoomModal } from "@/components/chat/ImageZoomModal";
import { FileTooLargeToast } from "@/components/chat/FileTooLargeToast";
// T7.18 (US 7.2): Streak Flame & Badge Modal
import { StreakBadge } from "@/components/chat/StreakBadge";
import { BadgeModal, BadgeItem, DEFAULT_BADGES } from "@/components/chat/BadgeModal";
import { getMergedBadges, saveStoredBadge, resetStoredBadge } from "@/lib/badgeStorage";
import { Conversation, Message } from "@/types/chat";
import { Menu, PanelRight, Trophy } from "lucide-react";
import { useRouter } from "next/navigation";
import { authFetch } from "@/lib/authFetch";
import { cn } from "@/lib/utils";

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
  const { data: session } = useSession();

  // Chặn tuyệt đối Quản trị viên (ADMIN) vào chat, đẩy thẳng về /admin
  useEffect(() => {
    if (session && (session.user as any)?.role === "ADMIN") {
      router.replace("/admin");
    }
  }, [session, router]);

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

  // Trạng thái mở/đóng thanh sidebar bên phải (Right Sidebar chứa ảnh bài tập giống Zalo)
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(false);
  // URL ảnh đang được phóng to trong ImageZoomModal
  const [selectedZoomImageUrl, setSelectedZoomImageUrl] = useState<string | null>(null);
  // Trạng thái thông báo nổi khi gửi ảnh quá 5MB
  const [fileTooLargeState, setFileTooLargeState] = useState<{
    isOpen: boolean;
    sizeMb: number;
    message?: string;
  }>({
    isOpen: false,
    sizeMb: 0,
  });

  // T7.18 (US 7.2): Quản lý huy hiệu & Modal chúc mừng (chỉ hiển thị 1 lần duy nhất)
  const userId = (session?.user as any)?.id || (session?.user as any)?.email || "student_guest";
  const [allBadges, setAllBadges] = useState<BadgeItem[]>(DEFAULT_BADGES);
  const [badgeQueue, setBadgeQueue] = useState<BadgeItem[]>([]);
  const [isBadgeModalOpen, setIsBadgeModalOpen] = useState(false);
  const [unlockedBadge, setUnlockedBadge] = useState<Partial<BadgeItem> | undefined>(undefined);

  // Đồng bộ trạng thái huy hiệu từ LocalStorage theo User
  useEffect(() => {
    if (typeof window !== "undefined") {
      setAllBadges(getMergedBadges(userId));

      // Hỗ trợ kiểm thử: cho phép Dev/QA reset huy hiệu qua Console
      (window as any).resetSocraticBadges = (badgeId?: string) => {
        resetStoredBadge(badgeId, userId);
        setAllBadges(getMergedBadges(userId));
        console.log(`[Badge] Đã reset huy hiệu ${badgeId || "tất cả"} cho user ${userId}`);
      };
    }
  }, [userId]);

  // Hàm mở khóa huy hiệu: đảm bảo CHỈ HIỆN 1 LẦN DUY NHẤT
  const triggerUnlockBadge = useCallback(
    (badgeId: string) => {
      // saveStoredBadge trả về true nếu là lần đầu tiên mở khóa
      const isFirstTime = saveStoredBadge(badgeId, userId);
      if (!isFirstTime) return;

      // Cập nhật lại allBadges trong state
      const updatedList = getMergedBadges(userId);
      setAllBadges(updatedList);

      const targetBadge =
        updatedList.find((b) => b.id === badgeId) ||
        DEFAULT_BADGES.find((b) => b.id === badgeId);

      if (targetBadge) {
        const itemToCelebrate: BadgeItem = {
          ...targetBadge,
          unlocked: true,
          earnedAt: "Hôm nay",
        };
        setBadgeQueue((prev) => [...prev, itemToCelebrate]);
      }
    },
    [userId]
  );

  // Xử lý hàng đợi hiển thị modal ăn mừng huy hiệu
  useEffect(() => {
    if (badgeQueue.length > 0 && !isBadgeModalOpen) {
      const nextBadge = badgeQueue[0];
      setUnlockedBadge(nextBadge);
      setIsBadgeModalOpen(true);
      setBadgeQueue((prev) => prev.slice(1));
    }
  }, [badgeQueue, isBadgeModalOpen]);

  // Khi tải xong số ngày streak: kiểm tra theo kỷ lục cao nhất (nếu >= 3 ngày -> mở khóa, nếu < 3 ngày -> khóa lại)
  const handleStreakLoaded = useCallback(
    (streakCount: number, maxStreakCount?: number) => {
      const highestStreak = maxStreakCount !== undefined ? Math.max(streakCount, maxStreakCount) : streakCount;
      if (highestStreak >= 3) {
        triggerUnlockBadge("streak_3");
      } else {
        // Tự động thu hồi/khóa lại nếu trước đó bị mở do test thử số ngày
        resetStoredBadge("streak_3", userId);
        setAllBadges(getMergedBadges(userId));
      }
    },
    [triggerUnlockBadge, userId]
  );

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
          // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
          const res = await authFetch(`${BACKEND_URL}/sessions`, {
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
                    attachment_url: m.attachment_url || undefined,
                    created_at: m.created_at,
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

  // Danh sách tất cả ảnh bài tập được gửi trong cuộc hội thoại hiện tại
  const currentImages: ExerciseImage[] = useMemo(() => {
    if (!currentConversation) return [];
    return currentConversation.messages
      .filter((m) => Boolean(m.attachment_url))
      .map((m) => ({
        id: m.id,
        url: m.attachment_url!,
        role: m.role,
      }));
  }, [currentConversation]);

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

    // 2. Gọi API để xóa trên Database (bỏ qua nếu là session tạm client chưa lưu DB)
    if (id.startsWith("c-")) {
      return;
    }

    try {
      const { getSession } = await import("next-auth/react");
      const nextAuthSession = await getSession();
      const token = (nextAuthSession as { access_token?: string } | null)
        ?.access_token;

      if (token) {
        const BACKEND_URL =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
        const res = await authFetch(`${BACKEND_URL}/sessions/${id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok && res.status !== 404) {
          console.warn(`[handleDeleteChat] Server trả về status ${res.status}`);
        }
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

  // US4.1 & US6.1 & US8.1 - Handler: Hoc sinh nhan "Da hieu"
  // 1. An ngay lap tuc 2 nut "Da hieu / Chua hieu"
  // 2. Hien thi bubble "SocraticKid dang nghi" (isTyping = true) trong khi Backend goi Gemini phan loai va sinh ten
  // 3. Sau khi Backend phan loai xong:
  //    - Neu la bai trung lap (EXACT_DUPLICATE / is_duplicate): Hien loi nhac bai da giai roi, khong tang so bai hoan thanh
  //    - Neu la bai moi: Hien tin nhan chuc mung, doi cam xuc Cu "correct", nhay so bai + 1 bai va mo khoa huy hieu
  const handleUnderstood = async () => {
    const prevNotUnderstoodCount = notUnderstoodCount;
    setNotUnderstoodCount(0);
    console.log("[US4.1, US6.1, US8.1] Hoc sinh nhan Da hieu -> An nut, hien Socratic dang nghi...");

    if (!activeChatId) return;

    const feedbackMsgId = `feedback-${Date.now()}`;

    // 1. Cập nhật state ngay lập tức: Ẩn 2 nút & Chèn bong bóng SocraticKid đang nghĩ (content: "")
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeChatId
          ? {
            ...c,
            messages: [
              ...c.messages.map((m) => ({
                ...m,
                isAnswerRevealed: false, // Ẩn tức thì nút Đã hiểu/Chưa hiểu ở tin nhắn trước
              })),
              {
                id: feedbackMsgId,
                role: "assistant" as const,
                content: "", // Rỗng -> Kích hoạt hiển thị "SocraticKid đang nghĩ" kèm 3 chấm động trong ChatMessage!
                emotion: "thinking",
                isAnswerRevealed: false,
                isCongrats: false,
                created_at: new Date().toISOString(),
              },
            ],
          }
          : c
      )
    );

    setIsTyping(true);

    // 2. Gửi request POST /chat/comprehension lên Backend để phân loại & sinh tên (Gemini chạy gộp 1 lần duy nhất)
    try {
      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
      const res = await authFetch(`${BACKEND_URL}/chat/comprehension`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeChatId,
          understood: true,
        }),
      });

      if (res.ok) {
        const resData = await res.json();
        const isDuplicate = Boolean(
          resData?.deduplication?.is_duplicate ||
          resData?.independence?.is_duplicate ||
          resData?.deduplication?.category === "EXACT_DUPLICATE"
        );

        if (isDuplicate) {
          // --- TRƯỜNG HỢP 1: BÀI TRÙNG LẶP Y HỆT ĐÃ LÀM TRƯỚC ĐÓ (AC 8.1.1) ---
          const reminderMsg = resData.deduplication?.gentle_reminder
            ? `**${resData.deduplication.gentle_reminder}**

*(Thầy ghi nhận em đã ôn tập lại bài này. Vì bài đã được hoàn thành trước đó nên hệ thống sẽ không cộng dồn thêm vào tổng số bài nhé!)*`
            : "Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?";

          setConversations((prev) =>
            prev.map((c) =>
              c.id === activeChatId
                ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === feedbackMsgId
                      ? {
                        ...m,
                        content: reminderMsg,
                        emotion: "idle",
                        isAnswerRevealed: false,
                        isCongrats: false, // Không hiện nhãn chúc mừng / lưu sổ tay cho bài trùng
                        created_at: resData?.independence?.created_at || new Date().toISOString(),
                      }
                      : m
                  ),
                }
                : c
            )
          );

          // Phát sự kiện cập nhật điểm nhưng kèm cờ is_duplicate: true để Sidebar KHÔNG nhảy số bài (+1 bài)
          if (resData.independence) {
            window.dispatchEvent(
              new CustomEvent("INDEPENDENCE_SCORE_UPDATED", {
                detail: {
                  ...resData.independence,
                  is_duplicate: true,
                  category: "EXACT_DUPLICATE",
                },
              })
            );
          }
        } else {
          // --- TRƯỜNG HỢP 2: BÀI MỚI (NEW_TOPIC HOẶC ISOMORPHIC_PRACTICE) ---
          const congratsMessages = [
            "**Tuyệt vời!** Em đã hiểu rồi! Thầy rất vui vì em nắm được vấn đề. Hãy tiếp tục phát huy nhé!",
            "**Xuất sắc!** Em đã hiểu bài rồi! Học toán mà hiểu được như vậy là rất giỏi đó. Tiếp tục nhé!",
            "**Giỏi lắm!** Em đã nắm được kiến thức này rồi! Mỗi câu hỏi hiểu được là một bước tiến lớn. Cứ tiếp tục học nhé!",
          ];
          const randomMsg = congratsMessages[Math.floor(Math.random() * congratsMessages.length)];

          setConversations((prev) =>
            prev.map((c) =>
              c.id === activeChatId
                ? {
                  ...c,
                  messages: c.messages.map((m) =>
                    m.id === feedbackMsgId
                      ? {
                        ...m,
                        content: randomMsg,
                        emotion: "correct",
                        isAnswerRevealed: false,
                        isCongrats: true, // Hiện nút Lưu vào Sổ tay
                        created_at: resData?.independence?.created_at || new Date().toISOString(),
                      }
                      : m
                  ),
                }
                : c
            )
          );

          // Phát sự kiện toàn cục để thanh tiến trình Mastery trên Sidebar cập nhật real-time & NHẢY SỐ BÀI (+1 bài)
          if (resData.independence) {
            window.dispatchEvent(
              new CustomEvent("INDEPENDENCE_SCORE_UPDATED", {
                detail: {
                  ...resData.independence,
                  is_duplicate: false,
                },
              })
            );

            // T7.18 (US 7.2): Nếu đạt 100 điểm tự lập -> Mở khóa huy hiệu "Tự lập nhí" (hiện 1 lần duy nhất)
            if (resData.independence.score === 100 || prevNotUnderstoodCount === 0) {
              triggerUnlockBadge("independence_100");
            }

            // T7.18 (US 7.2): Nếu bài toán có kèm ảnh bài tập -> Mở khóa huy hiệu "Thám Tử Hình Ảnh" (hiện 1 lần duy nhất)
            const currentConv = conversations.find((c) => c.id === activeChatId);
            const hasImageInSession = Boolean(
              currentImages.length > 0 ||
              currentConv?.messages.some((m) => Boolean(m.attachment_url))
            );
            if (hasImageInSession) {
              triggerUnlockBadge("photo_solver");
            }
          }
        }
      }
    } catch (e) {
      console.warn("[US6.1 & US8.1] Lỗi gửi comprehension feedback lên backend:", e);
      // Fallback khi lỗi mạng: hiện thông báo chúc mừng mặc định
      setConversations((prev) =>
        prev.map((c) =>
          c.id === activeChatId
            ? {
              ...c,
              messages: c.messages.map((m) =>
                m.id === feedbackMsgId
                  ? {
                    ...m,
                    content: "**Tuyệt vời!** Em đã hiểu rồi! Thầy rất vui vì em nắm được vấn đề. Hãy tiếp tục phát huy nhé!",
                    emotion: "correct",
                    isAnswerRevealed: false,
                    isCongrats: true,
                  }
                  : m
              ),
            }
            : c
        )
      );
    } finally {
      setIsTyping(false);
    }
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
      // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
      const response = await authFetch(`${BACKEND_URL}/chat/orchestrator`, {
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

    if (activeChatId) {
      // US6.1: Ghi nhận phản hồi "Chưa hiểu" lên backend để trừ điểm tự lực theo barem (-15đ)
      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
      authFetch(`${BACKEND_URL}/chat/comprehension`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeChatId,
          understood: false,
        }),
      }).catch((err) => {
        console.warn("[US6.1] Lỗi gửi feedback Chưa hiểu:", err);
      });
    }

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
    attachmentUrl?: string,
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

      // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
      const response = await authFetch(`${BACKEND_URL}/chat/orchestrator`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify({
          session_id: targetConversationId,
          prompt: userContent.trim() || (attachmentUrl ? "Em gửi ảnh bài toán, nhờ thầy hướng dẫn giúp em với ạ." : ""),
          problem_context: null,
          grade_level: gradeLevel ? Number(gradeLevel) : undefined,
          attachment_url: attachmentUrl || undefined,
        }),
      });

      if (!response.ok) {
        let errMsg = `Lỗi từ máy chủ (${response.status})`;
        try {
          const errData = await response.json();
          if (errData?.detail) errMsg = errData.detail;
        } catch {
          // ignore
        }
        throw new Error(errMsg);
      }

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
    } catch (error: any) {
      console.error("Lỗi khi kết nối backend:", error);
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: error?.message || "Xin lỗi, đã có lỗi kết nối tới máy chủ.",
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
  // imageFile?: File - File ảnh đính kèm từ ChatInput (US 6.4: Tích hợp upload Cloudinary)
  const handleSendMessage = async (content: string, isExplanation = false, imageFile?: File) => {
    // US4.1: Chi reset dem "Chua hieu" khi hoc sinh tu go tin nhan moi hoan toan,
    // khong reset khi gui giai thich tu UnderstandingButtons
    if (!isExplanation) {
      setNotUnderstoodCount(0);
    }

    // Kiểm tra dung lượng ảnh: gửi thông báo khi ảnh quá 5MB
    if (imageFile) {
      if (imageFile.size > 5 * 1024 * 1024) {
        const sizeMb = imageFile.size / (1024 * 1024);
        setFileTooLargeState({
          isOpen: true,
          sizeMb,
          message: `Ảnh bạn gửi có dung lượng ${sizeMb.toFixed(1)}MB, vượt quá giới hạn 5MB của hệ thống. Vui lòng chọn ảnh nhỏ hơn 5MB!`,
        });
        return;
      }

      // Sau khi học sinh gửi ảnh bài tập -> luôn hiện/mở thanh sidebar bên phải (giống Zalo)
      setIsRightSidebarOpen(true);
    }

    const messageId = Date.now().toString();
    const localPreviewUrl = imageFile ? URL.createObjectURL(imageFile) : undefined;

    const userMsg: Message = {
      id: messageId,
      role: "user",
      content,
      attachment_url: localPreviewUrl,
      status: isOnline ? "sending" : "error",
    };

    let targetId = activeChatId;

    if (!targetId) {
      // Trường hợp New Chat: cần tạo Session trên DB trước, rồi mới chat
      const title =
        content.trim().length > 25
          ? content.trim().slice(0, 25) + "..."
          : content.trim() || (imageFile ? "Bài toán từ ảnh" : "Phòng chat mới");

      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      let realSessionId: string | null = null;

      try {
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)
          ?.access_token;

        if (token) {
          // T6.13: dùng authFetch để tự refresh khi SESSION_STALE
          const res = await authFetch(`${BACKEND_URL}/sessions`, {
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

    // US 6.4 (Task #173): Upload ảnh lên Cloudinary nếu người dùng có đính kèm file
    let uploadedAttachmentUrl: string | undefined = undefined;
    if (imageFile) {
      try {
        const BACKEND_URL =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
        const { getSession } = await import("next-auth/react");
        const nextAuthSession = await getSession();
        const token = (nextAuthSession as { access_token?: string } | null)
          ?.access_token;

        const uploadHeaders: Record<string, string> = {};
        if (token) {
          uploadHeaders["Authorization"] = `Bearer ${token}`;
        }

        const formData = new FormData();
        formData.append("file", imageFile);

        const uploadRes = await authFetch(`${BACKEND_URL}/upload/image`, {
          method: "POST",
          headers: uploadHeaders,
          body: formData,
        });

        if (uploadRes.ok) {
          const uploadData = await uploadRes.json();
          uploadedAttachmentUrl = uploadData.secure_url || uploadData.url;

          // Cập nhật lại URL Cloudinary chính thức vào message trong state
          if (uploadedAttachmentUrl) {
            setConversations((prev) =>
              prev.map((c) =>
                c.id === targetId
                  ? {
                    ...c,
                    messages: c.messages.map((m) =>
                      m.id === messageId
                        ? { ...m, attachment_url: uploadedAttachmentUrl }
                        : m,
                    ),
                  }
                  : c,
              ),
            );
          }
        } else {
          console.error("Lỗi upload ảnh lên Cloudinary:", await uploadRes.text());
        }
      } catch (uploadErr) {
        console.error("Lỗi kết nối khi upload ảnh:", uploadErr);
      }
    }

    triggerBotResponse(targetId, messageId, content, uploadedAttachmentUrl);
  };

  // Handler: Thử lại (Retry) khi gửi tin nhắn thất bại
  const handleRetryMessage = (messageId: string, content: string) => {
    if (!activeChatId) return;

    let targetAttachmentUrl: string | undefined = undefined;
    const currentConv = conversations.find((c) => c.id === activeChatId);
    if (currentConv) {
      const msg = currentConv.messages.find((m) => m.id === messageId);
      if (msg?.attachment_url && !msg.attachment_url.startsWith("blob:")) {
        targetAttachmentUrl = msg.attachment_url;
      }
    }

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

    triggerBotResponse(activeChatId, messageId, content, targetAttachmentUrl);
  };

  if (!isHydrated) {
    return (
      <div className="flex h-[100dvh] w-screen bg-[#F7ECE1] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-[#8C4905] border-t-transparent rounded-full animate-spin"></div>
          <p className="text-[#8C4905] font-medium">Đang tải dữ liệu...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] w-screen bg-[#F7ECE1] overflow-hidden font-sans">
      {/* Sidebar bên trái */}
      <ChatSidebar
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
        isCollapsed={isSidebarCollapsed}
        conversations={conversations}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
      />

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
              className="p-2 text-[#8C4905] hover:bg-[#F1CCA6]/50 rounded-lg transition-colors cursor-pointer"
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

          {/* Khu vực Streak ngọn lửa, Bảng xếp hạng (Cúp) & Nút bật/tắt thanh ảnh bài tập bên phải */}
          <div className="flex items-center gap-2">
            {/* T7.18: Biểu tượng ngọn lửa hoạt hình Streak 🔥 */}
            <StreakBadge
              onStreakLoaded={handleStreakLoaded}
              onClick={() => {
                setUnlockedBadge(undefined); // Mở xem bộ sưu tập huy hiệu
                setIsBadgeModalOpen(true);
              }}
            />

            {/* Nút Bảng xếp hạng (Icon cái cúp 🏆) */}
            <button
              onClick={() => router.push("/dashboard/leaderboard")}
              className="flex items-center justify-center h-[34px] w-[34px] rounded-xl bg-white text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F1CCA6]/40 hover:text-[#C1762A] transition-all shadow-2xs cursor-pointer group active:scale-95"
              title="Xem Bảng xếp hạng (Streak Leaderboard)"
              aria-label="Xem Bảng xếp hạng"
            >
              <Trophy size={17} className="text-[#C1762A] group-hover:scale-110 transition-transform" />
            </button>

            <button
              onClick={() => setIsRightSidebarOpen((prev) => !prev)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition-all border cursor-pointer",
                isRightSidebarOpen
                  ? "bg-[#C1762A] text-white border-[#C1762A] shadow-sm"
                  : "bg-white text-[#8C4905] border-[#F1CCA6] hover:bg-[#F1CCA6]/40"
              )}
              title="Đóng / mở thanh ảnh bài tập bên phải"
            >
              <PanelRight size={17} />
              <span className="hidden sm:inline">Ảnh bài tập</span>
              {currentImages.length > 0 && (
                <span
                  className={cn(
                    "px-1.5 py-0.5 rounded-full text-[11px] font-bold leading-none",
                    isRightSidebarOpen
                      ? "bg-white/25 text-white"
                      : "bg-[#F1CCA6] text-[#8C4905]"
                  )}
                >
                  {currentImages.length}
                </span>
              )}
            </button>
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
            sessionId={activeChatId || undefined}
          />
        </main>
      </div>

      {/* Thanh sidebar bên phải hiển thị ảnh bài tập (giống Zalo) */}
      <ChatRightSidebar
        isOpen={isRightSidebarOpen}
        onClose={() => setIsRightSidebarOpen(false)}
        images={currentImages}
        onZoomImage={(url) => setSelectedZoomImageUrl(url)}
        onUploadClick={() => {
          const btn = document.getElementById("chat-attach-btn");
          btn?.click();
        }}
      />

      {/* Modal phóng to ảnh bài tập */}
      <ImageZoomModal
        isOpen={Boolean(selectedZoomImageUrl)}
        imageUrl={selectedZoomImageUrl}
        imageTitle="Ảnh bài tập đã chọn"
        onClose={() => setSelectedZoomImageUrl(null)}
      />

      {/* Thông báo nổi khi dung lượng ảnh vượt quá 5MB */}
      <FileTooLargeToast
        isOpen={fileTooLargeState.isOpen}
        fileSizeMb={fileTooLargeState.sizeMb}
        message={fileTooLargeState.message}
        onClose={() => setFileTooLargeState((prev) => ({ ...prev, isOpen: false }))}
      />

      {/* T7.18: Modal chúc mừng mở khóa Huy hiệu với hiệu ứng pháo hoa */}
      <BadgeModal
        isOpen={isBadgeModalOpen}
        onClose={() => setIsBadgeModalOpen(false)}
        activeBadge={unlockedBadge}
        allBadges={allBadges}
      />
    </div>
  );
}
