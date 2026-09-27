"use client";

import { useRouter } from "next/navigation";
import { LogOut, Settings, X, Plus, Trash2 } from "lucide-react";
import { useSession, signOut } from "next-auth/react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { Conversation } from "@/types/chat";

interface ChatSidebarProps {
  className?: string;
  isMobileOpen: boolean;
  setIsMobileOpen: (open: boolean) => void;
  conversations: Conversation[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat?: (id: string) => void;
}

export function ChatSidebar({
  className,
  isMobileOpen,
  setIsMobileOpen,
  conversations,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
}: ChatSidebarProps) {
  const router = useRouter();
  const { data: session } = useSession();
  const [showSettings, setShowSettings] = useState(false);

  // Nhóm lịch sử chat theo ngày
  const groupedHistory = conversations.reduce((acc, chat) => {
    const key = chat.date || "Today";
    if (!acc[key]) acc[key] = [];
    acc[key].push(chat);
    return acc;
  }, {} as Record<string, Conversation[]>);

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          "fixed md:static inset-y-0 left-0 z-50 w-64 bg-[#F1CCA6] flex flex-col h-full transform transition-transform duration-300 ease-in-out border-r border-[#C1762A]/20 flex-shrink-0",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          className
        )}
      >
        {/* Mobile close button */}
        <div className="md:hidden flex justify-end p-4 pb-0">
          <button onClick={() => setIsMobileOpen(false)} className="text-[#8C4905]">
            <X size={24} />
          </button>
        </div>

        {/* Top Area (Logo & New Chat) */}
        <div className="p-4 flex flex-col gap-4">
          <div
            className="flex items-center gap-3 mb-2 cursor-pointer"
            onClick={() => router.push("/dashboard")}
          >
            <div className="w-10 h-10 bg-[#D9D9D9] rounded-xl flex items-center justify-center text-[#8C4905] font-bold text-sm shadow-inner">
              SK
            </div>
            <h2 className="font-extrabold italic text-xl text-[#8C4905] tracking-tight">
              SocraticKid
            </h2>
          </div>

          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 py-3 bg-white text-[#8C4905] rounded-2xl font-bold shadow-sm hover:shadow transition-all border border-[#F1CCA6]"
          >
            <Plus size={18} />
            new chat
          </button>
        </div>

        {/* Chat History List */}
        <div className="flex-1 overflow-y-auto px-4 py-2 space-y-6">
          {Object.entries(groupedHistory).map(([date, chats]) => (
            <div key={date}>
              <h3 className="text-xs font-semibold text-[#C1762A] mb-2">{date}</h3>
              <div className="space-y-1">
                {chats.map((chat) => (
                  <div
                    key={chat.id}
                    onClick={() => onSelectChat(chat.id)}
                    className={cn(
                      "group flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer transition-all",
                      activeChatId === chat.id
                        ? "bg-white text-[#8C4905] shadow-sm font-semibold"
                        : "text-[#8C4905] hover:bg-[#F7AD62]/20 hover:text-[#CB6600]"
                    )}
                  >
                    <span className="truncate flex-1 text-sm">{chat.title}</span>
                    {onDeleteChat && activeChatId === chat.id && (
                      <div className="flex gap-2 text-[#C1762A]">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteChat(chat.id);
                          }}
                          className="hover:text-[#8C4905] p-1"
                          title="Xóa đoạn chat"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Settings Dropdown (Floating) */}
        {showSettings && (
          <div className="absolute bottom-20 left-4 right-4 bg-white rounded-xl shadow-lg border border-[#F1CCA6] p-2 z-50 animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => signOut({ callbackUrl: "/" })}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[#8C4905] hover:bg-[#F7ECE1] rounded-lg transition-colors font-medium"
            >
              <LogOut size={16} />
              Đăng xuất
            </button>
          </div>
        )}

        {/* Mini Profile Area */}
        <div className="p-4 border-t border-[#C1762A]/20 bg-[#F1CCA6] flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {session?.user?.image ? (
              <img
                src={session.user.image}
                alt="Avatar"
                className="w-8 h-8 rounded-full border border-[#C1762A]"
              />
            ) : (
              <div className="w-8 h-8 bg-white rounded-full flex items-center justify-center text-[#8C4905] font-bold border border-[#C1762A]">
                {session?.user?.name?.charAt(0) || "U"}
              </div>
            )}
            <p className="text-sm font-bold text-[#8C4905] truncate flex-1">
              {session?.user?.name || "Người dùng"}
            </p>
          </div>
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-[#8C4905] hover:bg-[#F7AD62]/30 rounded-lg transition-colors"
          >
            <Settings size={20} />
          </button>
        </div>
      </aside>
    </>
  );
}
