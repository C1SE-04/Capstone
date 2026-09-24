/**
 * File: app/try/page.tsx
 * Mô tả: Trang "Dùng thử" - Chat demo dành cho khách chưa đăng nhập.
 * Không yêu cầu xác thực. Không lưu lịch sử.
 */
"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import { useRouter } from "next/navigation";

const GUEST_SESSION_ID = "guest-try-session";

const SUGGESTIONS = [
  "Phân số là gì?",
  "Giải thích cho mình về tích phân nhé?",
  "Làm thế nào để giải phương trình bậc 2?",
];

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

let idCounter = 0;
function createMessageId(prefix: string = "msg") {
  idCounter += 1;
  return `${prefix}-${Date.now()}-${idCounter}`;
}

export default function TryPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Xin chào! Mình là **SocraticKid** 🦉\n\nBạn có thể hỏi mình bất cứ điều gì về Toán học. Mình sẽ **không cho đáp án luôn** — mình sẽ đặt câu hỏi dẫn dắt để bạn tự khám phá ra nhé! 💪\n\n*Đây là chế độ dùng thử — lịch sử sẽ không được lưu lại.*",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isTyping) return;

    const userMsg: Message = {
      id: createMessageId("user"),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsTyping(true);

    // Tạo tin nhắn AI rỗng để stream vào
    const botId = createMessageId("bot");
    const botMsg: Message = { id: botId, role: "assistant", content: "" };
    setMessages((prev) => [...prev, botMsg]);

    const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
    try {
      const response = await fetch(`${BACKEND_URL}/chat/orchestrator`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: GUEST_SESSION_ID,
          prompt: trimmed,
          problem_context: null, // Chế độ dùng thử: không có bài toán cụ thể
        }),
      });

      if (!response.body) throw new Error("Không có phản hồi từ server");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let isDone = false;

      while (!isDone) {
        const { value, done } = await reader.read();
        isDone = done;
        if (value) {
          const chunkStr = decoder.decode(value, { stream: true });
          for (const line of chunkStr.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const dataStr = line.slice(6).trim();
            if (!dataStr || dataStr === "{}") continue;
            try {
              const obj = JSON.parse(dataStr);
              if (obj.text) {
                const chunk = obj.text;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === botId ? { ...m, content: m.content + chunk } : m
                  )
                );
              }
            } catch {
              // bỏ qua chunk lỗi parse
            }
          }
        }
      }
    } catch (err) {
      console.error("Lỗi kết nối backend:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botId
            ? { ...m, content: "Xin lỗi, không thể kết nối tới máy chủ. Vui lòng thử lại sau." }
            : m
        )
      );
    } finally {
      setIsTyping(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputValue);
    }
  };

  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col">
      {/* Header */}
      <header className="w-full px-6 py-4 flex items-center justify-between border-b border-[#C1762A]/10 bg-[#F7ECE1]/80 backdrop-blur-sm sticky top-0 z-10">
        <div
          className="w-10 h-10 bg-[#D9D9D9] rounded-xl flex items-center justify-center text-[#8C4905] font-bold text-sm cursor-pointer hover:bg-[#F1CCA6] transition-colors shadow-inner"
          onClick={() => router.push("/")}
        >
          SK
        </div>
        <span className="text-xs text-[#8C4905]/60 font-medium">
          Chế độ dùng thử · Không lưu lịch sử
        </span>
        <button
          onClick={() => router.push("/")}
          className="text-sm font-semibold text-[#C1762A] hover:text-[#8C4905] transition-colors"
        >
          Đăng nhập →
        </button>
      </header>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-2xl w-full mx-auto flex flex-col gap-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 items-start ${msg.role === "user" ? "flex-row-reverse" : ""}`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-white text-xs font-bold ${
                msg.role === "user" ? "bg-[#C1762A]" : "bg-[#8C4905]"
              }`}
            >
              {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap shadow-sm ${
                msg.role === "user"
                  ? "bg-[#C1762A] text-white rounded-tr-sm"
                  : "bg-white text-[#1a1a1a] rounded-tl-sm border border-[#C1762A]/10"
              } ${msg.content === "" ? "animate-pulse bg-gray-100 text-gray-400 italic" : ""}`}
            >
              {msg.content === "" ? "Đang soạn..." : msg.content}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && messages[messages.length - 1]?.content !== "" && (
          <div className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-full bg-[#8C4905] flex items-center justify-center">
              <Bot size={14} className="text-white" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-white border border-[#C1762A]/10 shadow-sm">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-[#C1762A]/40 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-[#C1762A]/40 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-[#C1762A]/40 rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions (chỉ hiện khi mới vào) */}
      {messages.length <= 1 && (
        <div className="flex flex-wrap justify-center gap-2 px-4 pb-2 max-w-2xl mx-auto w-full">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="px-4 py-2 bg-[#F1CCA6] text-[#8C4905] rounded-full text-xs font-semibold hover:bg-[#F7AD62] hover:text-white transition-all"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <div className="w-full max-w-2xl mx-auto px-4 pb-6 pt-2">
        <div className="flex items-center bg-white border border-[#C1762A]/20 rounded-full px-5 py-3 shadow-sm focus-within:border-[#C1762A] focus-within:shadow-md transition-all gap-3">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi SocraticKid bất cứ điều gì..."
            className="flex-1 bg-transparent text-[#000000] placeholder:text-[#8C4905]/40 outline-none font-medium text-sm"
            disabled={isTyping}
          />
          <button
            onClick={() => sendMessage(inputValue)}
            disabled={!inputValue.trim() || isTyping}
            className={`p-2 rounded-full transition-all ${
              inputValue.trim() && !isTyping
                ? "bg-[#C1762A] text-white hover:bg-[#8C4905] hover:scale-105"
                : "text-[#C1762A]/30 cursor-not-allowed"
            }`}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
