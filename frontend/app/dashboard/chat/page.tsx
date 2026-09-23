/**
 * File: app/dashboard/chat/page.tsx
 * Mô tả: Đây là trang route chính cho giao diện Chat (App Router: /dashboard/chat).
 * Trang này đóng vai trò như một wrapper, bọc component ChatWindow bên trong.
 */
"use client";

import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  return (
    // Wrapper div có animation mờ dần (fade-in) khi tải trang
    <div className="h-full animate-in fade-in duration-500">
      <ChatWindow />
    </div>
  );
}
