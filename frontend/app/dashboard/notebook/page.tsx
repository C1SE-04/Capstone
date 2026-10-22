"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  BookMarked,
  Search,
  Filter,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Image as ImageIcon,
  Award,
  Layers,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BookmarkItem } from "@/types/bookmark";
import { FlashcardItem } from "@/components/notebook/FlashcardItem";
import { BookmarkChatDrawer } from "@/components/notebook/BookmarkChatDrawer";
import { authFetch } from "@/lib/authFetch";

export default function NotebookPage() {
  const router = useRouter();
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [apiError, setApiError] = useState<string | null>(null);

  // Bộ lọc
  const [searchQuery, setSearchQuery] = useState("");
  const [scoreFilter, setScoreFilter] = useState<"all" | "perfect" | "passed">("all");
  const [hasAttachmentOnly, setHasAttachmentOnly] = useState(false);

  // Drawer xem lại đoạn chat
  const [selectedBookmark, setSelectedBookmark] = useState<BookmarkItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Fetch danh sách bookmarks từ backend
  const fetchBookmarks = useCallback(async () => {
    setIsLoading(true);
    setApiError(null);
    try {
      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      const res = await authFetch(`${BACKEND_URL}/bookmarks`);

      if (res.ok) {
        const data = await res.json();
        setBookmarks(Array.isArray(data) ? data : []);
      } else if (res.status === 404 || res.status === 501) {
        // Backend API T7.13 đang trong quá trình hoàn thiện
        setApiError("API Sổ tay (/bookmarks) đang trong quá trình đồng bộ từ máy chủ.");
        setBookmarks([]);
      } else {
        setApiError("Chưa thể tải dữ liệu Sổ tay từ máy chủ. Vui lòng thử lại!");
        setBookmarks([]);
      }
    } catch {
      setApiError("Lỗi kết nối mạng tới máy chủ Sổ tay.");
      setBookmarks([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  // Handler xóa bookmark
  const handleDeleteBookmark = async (bookmarkId: string) => {
    try {
      const BACKEND_URL =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

      const res = await authFetch(`${BACKEND_URL}/bookmarks/${bookmarkId}`, {
        method: "DELETE",
      });

      if (res.ok || res.status === 204) {
        setBookmarks((prev) => prev.filter((b) => b.id !== bookmarkId));
      } else {
        console.warn("Không thể xóa bookmark trên server:", res.status);
      }
    } catch (err) {
      console.warn("Lỗi xóa bookmark:", err);
    }
  };

  // Mở Drawer đối thoại chat
  const handleOpenChat = (bookmark: BookmarkItem) => {
    setSelectedBookmark(bookmark);
    setIsDrawerOpen(true);
  };

  // Lọc danh sách theo từ khóa & tiêu chí
  const filteredBookmarks = useMemo(() => {
    return bookmarks.filter((bm) => {
      // Tìm kiếm theo từ khóa
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const inTitle = bm.session_title?.toLowerCase().includes(q);
        const inSnapshot = bm.problem_snapshot?.toLowerCase().includes(q);
        const inSummary = bm.chat_summary?.toLowerCase().includes(q);
        if (!inTitle && !inSnapshot && !inSummary) return false;
      }

      // Lọc điểm tự lập
      if (scoreFilter === "perfect" && bm.independence_score !== 100) {
        return false;
      }
      if (scoreFilter === "passed" && (bm.independence_score ?? 0) < 80) {
        return false;
      }

      // Lọc có ảnh bài tập
      if (hasAttachmentOnly && !bm.attachment_url) {
        return false;
      }

      return true;
    });
  }, [bookmarks, searchQuery, scoreFilter, hasAttachmentOnly]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#F7ECE1] overflow-y-auto">
      {/* Header trang Sổ tay */}
      <div className="bg-white border-b border-[#F1CCA6] p-6 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#F1CCA6] to-[#F7ECE1] flex items-center justify-center text-[#8C4905] shadow-inner">
              <BookMarked size={26} />
            </div>
            <div>
              <h1 className="text-xl md:text-2xl font-extrabold text-[#8C4905] tracking-tight flex items-center gap-2">
                Sổ Tay Bài Toán Yêu Thích
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F1CCA6]/60 text-[#8C4905]">
                  {bookmarks.length} bài
                </span>
              </h1>
              <p className="text-xs md:text-sm text-[#C1762A] mt-0.5">
                Ôn tập các bí kíp toán học, xem lại ảnh đề bài và chuỗi đối thoại tư duy của bạn
              </p>
            </div>
          </div>

          <button
            onClick={fetchBookmarks}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-[#8C4905] bg-[#F7ECE1] hover:bg-[#F1CCA6]/60 border border-[#F1CCA6] transition-colors self-start md:self-auto cursor-pointer"
          >
            <RefreshCw size={13} className={cn(isLoading && "animate-spin")} />
            <span>Đồng bộ</span>
          </button>
        </div>

        {/* Thanh công cụ lọc & tìm kiếm */}
        <div className="max-w-7xl mx-auto mt-6 pt-5 border-t border-[#F1CCA6]/30 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Ô tìm kiếm */}
          <div className="relative flex-1 max-w-md">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#C1762A]"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm kiếm bài toán, đề bài, bí kíp..."
              className="w-full pl-10 pr-4 py-2 bg-[#F7ECE1]/40 border border-[#F1CCA6] rounded-xl text-xs md:text-sm text-stone-800 placeholder-[#C1762A]/60 focus:outline-none focus:ring-2 focus:ring-[#C1762A]/50 focus:bg-white transition-all"
            />
          </div>

          {/* Bộ nút lọc */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
            <button
              onClick={() => setScoreFilter("all")}
              className={cn(
                "px-3 py-1.5 rounded-xl text-xs font-semibold transition-all shrink-0 cursor-pointer",
                scoreFilter === "all"
                  ? "bg-[#C1762A] text-white shadow-sm"
                  : "bg-white text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F7ECE1]"
              )}
            >
              Tất cả
            </button>
            <button
              onClick={() => setScoreFilter("perfect")}
              className={cn(
                "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shrink-0 cursor-pointer",
                scoreFilter === "perfect"
                  ? "bg-[#C1762A] text-white shadow-sm"
                  : "bg-white text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F7ECE1]"
              )}
            >
              <Award size={13} />
              Tự lập 100đ
            </button>
            <button
              onClick={() => setHasAttachmentOnly(!hasAttachmentOnly)}
              className={cn(
                "px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all shrink-0 cursor-pointer",
                hasAttachmentOnly
                  ? "bg-[#C1762A] text-white shadow-sm"
                  : "bg-white text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F7ECE1]"
              )}
            >
              <ImageIcon size={13} />
              Có ảnh đề bài
            </button>
          </div>
        </div>
      </div>

      {/* Nội dung danh sách Flashcard */}
      <div className="flex-1 p-6 max-w-7xl mx-auto w-full">
        {isLoading ? (
          // Skeleton loader
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm animate-pulse space-y-4"
              >
                <div className="h-5 bg-stone-200 rounded-lg w-2/3"></div>
                <div className="h-20 bg-stone-100 rounded-xl"></div>
                <div className="h-10 bg-stone-100 rounded-xl"></div>
              </div>
            ))}
          </div>
        ) : apiError ? (
          // Thông báo API đang chờ hoàn tất (Không mock data giả)
          <div className="bg-white border border-[#F1CCA6] rounded-3xl p-10 text-center max-w-lg mx-auto shadow-sm my-10 space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
              <Layers size={28} />
            </div>
            <h3 className="text-base font-bold text-[#8C4905]">
              Dịch vụ Sổ tay đang kết nối
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              {apiError}
              <br />
              Trang sẽ tự động hiển thị đầy đủ thẻ Flashcard ngay khi API hoàn tất.
            </p>
            <button
              onClick={fetchBookmarks}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#C1762A] text-white rounded-xl text-xs font-semibold hover:bg-[#8C4905] transition-colors cursor-pointer"
            >
              <RefreshCw size={13} />
              <span>Thử kết nối lại</span>
            </button>
          </div>
        ) : bookmarks.length === 0 ? (
          // Empty State khi chưa có bài nào được lưu
          <div className="bg-white border border-[#F1CCA6] rounded-3xl p-12 text-center max-w-lg mx-auto shadow-sm my-10 space-y-4 animate-in fade-in duration-300">
            <div className="w-16 h-16 rounded-2xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center mx-auto shadow-inner">
              <Sparkles size={32} />
            </div>
            <h3 className="text-lg font-bold text-[#8C4905]">
              Sổ tay của bạn đang trống
            </h3>
            <p className="text-xs md:text-sm text-[#C1762A] leading-relaxed">
              Khi giải xong một bài toán trong khung Chat và bấm &quot;Đã hiểu&quot;, hãy bấm
              <span className="font-semibold text-[#8C4905]"> ⭐ &quot;Lưu vào Sổ tay&quot;</span> để lưu lại đề bài, ảnh bài tập và bí kíp tư duy tại đây nhé!
            </p>
            <button
              onClick={() => router.push("/dashboard/chat")}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white rounded-xl text-xs font-bold hover:brightness-105 active:scale-95 transition-all shadow cursor-pointer mt-2"
            >
              <span>Đến khung Chat học bài ngay</span>
              <ArrowRight size={14} />
            </button>
          </div>
        ) : filteredBookmarks.length === 0 ? (
          // Empty State khi tìm kiếm / lọc không ra kết quả
          <div className="text-center py-16 text-[#8C4905]">
            <p className="text-sm font-semibold">
              Không tìm thấy bài toán nào phù hợp với bộ lọc hiện tại.
            </p>
            <button
              onClick={() => {
                setSearchQuery("");
                setScoreFilter("all");
                setHasAttachmentOnly(false);
              }}
              className="mt-3 text-xs font-bold text-[#C1762A] underline hover:text-[#8C4905]"
            >
              Đặt lại tất cả bộ lọc
            </button>
          </div>
        ) : (
          // Lưới thẻ Flashcard
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 animate-in fade-in duration-200">
            {filteredBookmarks.map((bm) => (
              <FlashcardItem
                key={bm.id}
                bookmark={bm}
                onOpenChat={handleOpenChat}
                onDelete={handleDeleteBookmark}
              />
            ))}
          </div>
        )}
      </div>

      {/* Drawer xem lại đối thoại tư duy của bài toán (Task T7.20) */}
      <BookmarkChatDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        sessionId={selectedBookmark?.session_id || null}
        problemTitle={selectedBookmark?.session_title}
        independenceScore={selectedBookmark?.independence_score}
        createdAt={selectedBookmark?.created_at}
        dialogueMessages={selectedBookmark?.dialogue_messages}
      />
    </div>
  );
}
