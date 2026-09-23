/**
 * File: app/dashboard/chat/page.tsx
 * Mô tả: Đây là trang route chính cho giao diện Chat (App Router: /dashboard/chat).
 * Trang này đóng vai trò như một wrapper, bọc component ChatWindow bên trong.
 */
"use client";

import { ChatWindow } from "@/components/chat/ChatWindow";

export default function ChatPage() {
  return <ChatWindow />;
}
