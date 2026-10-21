"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { X, Sparkles, MessageSquare, Loader2 } from "lucide-react";
import { Message } from "@/types/chat";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { authFetch } from "@/lib/authFetch";

interface RawSessionMessage {
  id?: string;
  sender_type?: string;
  role?: string;
  content?: string;
  attachment_url?: string;
}

interface BookmarkChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string | null;
  problemTitle?: string | null;
  independenceScore?: number | null;
  createdAt?: string | null;
}

function subscribe() {
  return () => {};
}

export function BookmarkChatDrawer({
  isOpen,
  onClose,
  sessionId,
  problemTitle,
  independenceScore,
  createdAt,
}: BookmarkChatDrawerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isMounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false
  );

  // Lấy danh sách tin nhắn thật của session khi mở Drawer
  useEffect(() => {
    let ignore = false;

    if (!isOpen || !sessionId) {
      return;
    }

    const loadMessages = async () => {
      setIsLoading(true);
      setError(null);
      setMessages([]);
      try {
        const BACKEND_URL =
          process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

        const res = await authFetch(`${BACKEND_URL}/sessions/${sessionId}`);

        if (!res.ok) {
          throw new Error(`Không thể tải đoạn chat (Mã lỗi: ${res.status})`);
        }

        const data = await res.json();
        const rawMessages = Array.isArray(data.messages) ? data.messages : [];

        const HIDDEN_PROMPTS = [
          "Hoc sinh chua hieu cach giai thich tren. Hay giai thich lai theo cach khac, don gian va de hieu hon.",
          "Hoc sinh van chua hieu sau nhieu lan giai thich. Hay dua ra dap an chinh xac va giai thich tung buoc that ro rang.",
        ];

        const formatted: Message[] = (rawMessages as RawSessionMessage[])
          .map((m) => ({
            id: m.id || String(Math.random()),
            role: m.sender_type === "USER" || m.role === "user" ? ("user" as const) : ("assistant" as const),
            content: m.content || "",
            attachment_url: m.attachment_url || undefined,
          }))
          .filter((m: Message) => !(m.role === "user" && HIDDEN_PROMPTS.includes(m.content.trim())));

        if (!ignore) {
          setMessages(formatted);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const msg = err instanceof Error ? err.message : "Không thể nạp nội dung đối thoại bài học này.";
          setError(msg);
          setMessages([]);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    loadMessages();

    return () => {
      ignore = true;
    };
  }, [isOpen, sessionId]);

  // Đóng Drawer khi bấm phím Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, onClose]);

  if (!isMounted || !isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop mờ nền */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-[2px] transition-opacity duration-200"
        onClick={onClose}
      />

      {/* Drawer trượt từ bên phải */}
      <div
        className="relative w-full max-w-xl h-full bg-[#F7ECE1] shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-200 border-l border-[#F1CCA6]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="px-5 py-4 bg-white border-b border-[#F1CCA6] flex items-center justify-between shadow-sm shrink-0">
          <div className="flex items-center gap-2.5 min-w-0 pr-3">
            <div className="w-8 h-8 rounded-lg bg-[#F1CCA6]/60 text-[#8C4905] flex items-center justify-center shrink-0">
              <MessageSquare size={17} />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-bold text-[#8C4905] truncate">
                {problemTitle || "Xem lại đối thoại tư duy"}
              </h3>
              <div className="flex items-center gap-2 text-[11px] text-[#C1762A] mt-0.5">
                {independenceScore !== undefined && independenceScore !== null && (
                  <span className="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200">
                    {independenceScore}đ tự lập
                  </span>
                )}
                {createdAt && (
                  <span>
                    {new Date(createdAt).toLocaleDateString("vi-VN", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                    })}
                  </span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#8C4905] hover:bg-[#F1CCA6]/40 transition-colors shrink-0"
            title="Đóng ngăn kéo"
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Body - Danh sách tin nhắn */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="h-full flex flex-col items-center justify-center gap-3 text-center py-20 text-[#8C4905]">
              <Loader2 size={24} className="animate-spin text-[#C1762A]" />
              <p className="text-xs font-medium">Đang mở lại đoạn đối thoại của bài toán...</p>
            </div>
          ) : error ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-stone-600 gap-3">
              <p className="text-xs bg-red-50 text-red-700 p-3 rounded-xl border border-red-200 max-w-sm">
                {error}
              </p>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16 text-[#8C4905] gap-2">
              <Sparkles size={28} className="text-[#C1762A]" />
              <p className="text-xs font-medium">Chưa có tin nhắn nào trong phiên này.</p>
            </div>
          ) : (
            <div className="pt-2">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
