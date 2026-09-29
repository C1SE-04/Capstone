/**
 * File: app/try/page.tsx
 * Mô tả: Trang "Dùng thử" - Chat demo dành cho khách chưa đăng nhập.
 * Không yêu cầu xác thực. Không lưu lịch sử.
 * Sprint 4 - US 4.3:
 *   - Task 89:  Tạo Guest ID lưu vào localStorage, kẹp X-Guest-ID vào mỗi API call.
 *   - Task 113: Hiển thị bảng thông báo hết lượt dùng thử (TrialExpiredModal).
 *   - Task 113: Nút "Đăng nhập" mở AuthForm modal giống trang chủ.
 */
"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import { getOrCreateGuestId, getGuestHeaders } from "@/lib/guestId";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

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

/* ──────────────────────────────────────────────
   Modal: Thông báo hết lượt dùng thử (US 4.3)
────────────────────────────────────────────── */
function TrialExpiredModal({ onLogin }: { onLogin: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{
        backgroundColor: "rgba(0,0,0,0.55)",
        backdropFilter: "blur(4px)",
        animation: "trialFadeIn 0.2s ease both",
      }}
    >
      <style>{`
        @keyframes trialFadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes trialSlideUp {
          from { opacity: 0; transform: translateY(24px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        .trial-card { animation: trialSlideUp 0.3s ease both; }
      `}</style>

      {/* Card */}
      <div
        className="trial-card relative bg-[#F7ECE1] rounded-3xl shadow-2xl overflow-hidden max-w-sm w-full border border-[#C1762A]/20"
      >
        {/* Top decorative strip */}
        <div
          style={{
            height: "4px",
            background: "linear-gradient(90deg, #C1762A, #F7AD62, #C1762A)",
          }}
        />

        <div className="px-8 py-8 flex flex-col items-center text-center gap-5">
          {/* Owl icon */}
          <div
            className="w-20 h-20 rounded-full bg-[#F1CCA6] flex items-center justify-center shadow-inner"
            style={{ fontSize: "2.5rem" }}
            aria-hidden="true"
          >
            🦉
          </div>

          {/* Heading */}
          <div>
            <h2 className="text-2xl font-extrabold text-[#8C4905] italic tracking-tight mb-2">
              Hết lượt hôm nay rồi!
            </h2>
            <p className="text-sm text-[#C1762A] font-medium leading-relaxed max-w-xs">
              Bạn đã dùng hết{" "}
              <strong className="text-[#8C4905]">10 câu hỏi</strong> miễn phí
              hôm nay. Quay lại sau{" "}
              <strong className="text-[#8C4905]">24 tiếng</strong> để được cấp
              thêm lượt mới — hoặc{" "}
              <span className="text-[#8C4905] font-bold">đăng nhập</span> để
              học tẹt ga không giới hạn! 🚀
            </p>
          </div>

          {/* Countdown hint */}
          <div className="w-full bg-[#F1CCA6]/60 rounded-2xl px-5 py-3 border border-[#C1762A]/20">
            <p className="text-xs text-[#8C4905]/70 font-medium">
              ⏰ Lượt dùng thử sẽ được reset sau 24 giờ kể từ lần hỏi đầu tiên
            </p>
          </div>

          {/* CTA */}
          <div className="w-full flex flex-col gap-3 pt-1">
            <button
              id="trial-expired-login-btn"
              onClick={onLogin}
              className="w-full bg-[#C1762A] text-white font-bold py-3 rounded-xl
                         hover:bg-[#8C4905] transition-all shadow-md
                         flex items-center justify-center gap-2 cursor-pointer"
              style={{ transform: "scale(1)" }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.transform = "scale(1.02)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.transform = "scale(1)")
              }
            >
              {/* Arrow icon */}
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17 8l4 4m0 0l-4 4m4-4H3"
                />
              </svg>
              Đăng nhập / Đăng ký ngay
            </button>

            <p className="text-xs text-[#8C4905]/50 font-medium">
              Hoặc đợi đến ngày mai để tiếp tục dùng thử miễn phí
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────
   Main Page
────────────────────────────────────────────── */
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

  // Modal states (Task 113)
  const [showTrialExpired, setShowTrialExpired] = useState(false);
  const [showAuthForm, setShowAuthForm] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [sessionId, setSessionId] = useState("");

  // Task 89 - US 4.3: Lấy hoặc tạo Guest ID từ localStorage
  // (persistent — tắt browser mở lại vẫn giữ nguyên ID để backend đếm tiếp)
  useEffect(() => {
    const guestId = getOrCreateGuestId();
    if (guestId) setSessionId(guestId);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  /** Mở AuthForm modal — dùng chung cho header và TrialExpiredModal */
  const handleOpenAuth = () => {
    setShowTrialExpired(false);
    setShowAuthForm(true);
  };

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
      // Task 89: Kẹp X-Guest-ID vào header để backend nhận diện và đếm số câu
      const response = await fetch(`${BACKEND_URL}/chat/orchestrator`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getGuestHeaders(), // { "X-Guest-ID": "<uuid từ localStorage>" }
        },
        body: JSON.stringify({
          session_id: sessionId,
          prompt: trimmed,
          problem_context: null, // Chế độ dùng thử: không có bài toán cụ thể
        }),
      });

      // ── Hết lượt dùng thử → hiện bảng thông báo (US 4.3 - AC1, AC2, AC3) ──
      if (response.status === 403) {
        setMessages((prev) => prev.filter((m) => m.id !== botId));
        setShowTrialExpired(true);
        return;
      }

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
      {/* ── Header ── */}
      <header className="w-full px-6 py-4 flex items-center justify-between border-b border-[#C1762A]/10 bg-[#F7ECE1]/80 backdrop-blur-sm sticky top-0 z-10">
        {/* Logo */}
        <div
          className="w-10 h-10 bg-[#D9D9D9] rounded-xl flex items-center justify-center text-[#8C4905] font-bold text-sm cursor-pointer hover:bg-[#F1CCA6] transition-colors shadow-inner"
          onClick={() => router.push("/")}
        >
          SK
        </div>

        {/* Status label */}
        <span className="text-xs text-[#8C4905]/60 font-medium">
          Chế độ dùng thử · Không lưu lịch sử
        </span>

        {/* Nút Đăng nhập — bấm mở AuthForm modal (Task 113) */}
        <button
          id="try-page-login-btn"
          onClick={handleOpenAuth}
          className="text-sm font-semibold text-[#C1762A] hover:text-[#8C4905] transition-colors cursor-pointer
                     bg-[#F1CCA6]/60 hover:bg-[#F1CCA6] px-4 py-1.5 rounded-lg border border-[#C1762A]/20"
        >
          Đăng nhập →
        </button>
      </header>

      {/* ── Chat area ── */}
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
              className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.role === "user"
                  ? "bg-[#C1762A] text-white rounded-tr-sm whitespace-pre-wrap"
                  : "bg-white text-[#1a1a1a] rounded-tl-sm border border-[#C1762A]/10"
              } ${msg.content === "" ? "animate-pulse bg-gray-100 text-gray-400 italic" : ""}`}
            >
              {msg.content === "" ? (
                "Đang soạn..."
              ) : msg.role === "user" ? (
                msg.content
              ) : (
                <div className="markdown-prose prose-sm max-w-none
                  prose-p:leading-relaxed prose-p:mb-2
                  prose-pre:bg-gray-100 prose-pre:p-3 prose-pre:rounded-lg
                  prose-code:text-[#CB6600] prose-code:bg-[#F1CCA6]/40 prose-code:px-1 prose-code:rounded
                  prose-ul:list-disc prose-ul:ml-4 prose-ul:mb-2
                  prose-ol:list-decimal prose-ol:ml-4 prose-ol:mb-2
                  prose-strong:text-[#8C4905]"
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkMath, remarkGfm]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}
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

      {/* ── Input bar ── */}
      <div className="w-full max-w-2xl mx-auto px-4 pb-6 pt-2">
        <div className="flex items-center bg-white border border-[#C1762A]/20 rounded-full px-5 py-3 shadow-sm focus-within:border-[#C1762A] focus-within:shadow-md transition-all gap-3">
          <input
            ref={inputRef}
            id="try-page-input"
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

      {/* ── Modal: Hết lượt dùng thử (US 4.3 - Task 113) ── */}
      {showTrialExpired && (
        <TrialExpiredModal onLogin={handleOpenAuth} />
      )}

      {/* ── Modal: AuthForm giống trang chủ (Task 113) ── */}
      {showAuthForm && <AuthForm onClose={() => setShowAuthForm(false)} />}
    </div>
  );
}
