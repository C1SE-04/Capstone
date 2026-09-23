/**
 * File: app/try/page.tsx
 * Mô tả: Trang "Dùng thử" - Khung chat demo dành cho khách chưa đăng nhập.
 * Không yêu cầu xác thực.
 */
"use client";

import { useState } from "react";
import { Send } from "lucide-react";
import { useRouter } from "next/navigation";

const SUGGESTION = "Giải thích cho mình về phân số nhé?";

export default function TryPage() {
  const [inputValue, setInputValue] = useState("");
  const router = useRouter();

  const handleSend = () => {
    if (inputValue.trim()) {
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <div className="min-h-screen bg-[#F7ECE1] font-sans flex flex-col">
      {/* Minimal Header */}
      <header className="w-full px-6 py-4 flex items-center justify-between">
        <div
          className="w-10 h-10 bg-[#D9D9D9] rounded-xl flex items-center justify-center text-[#8C4905] font-bold text-sm cursor-pointer hover:bg-[#F1CCA6] transition-colors shadow-inner"
          onClick={() => router.push("/")}
        >
          SK
        </div>
        <button
          onClick={() => router.push("/")}
          className="text-sm font-semibold text-[#C1762A] hover:text-[#8C4905] transition-colors"
        >
          Đăng nhập →
        </button>
      </header>

      {/* Center Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4">
        {/* Welcome */}
        <h1 className="text-4xl md:text-5xl font-extrabold italic text-[#C1762A] mb-12 tracking-tight">
          Welcome!
        </h1>

        {/* Input Bar */}
        <div className="w-full max-w-2xl">
          <div className="flex items-center bg-[#F1CCA6]/50 border border-[#C1762A]/20 rounded-full px-5 py-3 shadow-sm focus-within:border-[#C1762A] focus-within:bg-white transition-all gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Hỏi SocraticKid bất cứ điều gì..."
              className="flex-1 bg-transparent text-[#000000] placeholder:text-[#8C4905]/50 outline-none font-medium"
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim()}
              className={`p-2 rounded-full transition-all ${
                inputValue.trim()
                  ? "bg-[#C1762A] text-white hover:bg-[#8C4905] hover:scale-105"
                  : "text-[#C1762A]/40 cursor-not-allowed"
              }`}
            >
              <Send size={18} />
            </button>
          </div>

          {/* Single Prompt Suggestion */}
          <div className="mt-4 flex justify-center">
            <button
              onClick={() => setInputValue(SUGGESTION)}
              className="px-5 py-2 bg-[#F1CCA6] text-[#8C4905] rounded-full text-sm font-semibold hover:bg-[#F7AD62] hover:text-white transition-all"
            >
              {SUGGESTION}
            </button>
          </div>
        </div>

        {/* Disclaimer */}
        <p className="mt-10 text-xs text-[#8C4905]/50 text-center">
          Đây là phiên bản dùng thử.{" "}
          <button onClick={() => router.push("/")} className="underline hover:text-[#C1762A] transition-colors">
            Đăng nhập
          </button>{" "}
          để sử dụng đầy đủ tính năng.
        </p>
      </div>
    </div>
  );
}
