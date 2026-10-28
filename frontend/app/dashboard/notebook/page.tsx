"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  BookMarked,
  Search,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Image as ImageIcon,
  Award,
  Layers,
  Folder,
  Star,
  Plus,
  PanelLeft,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BookmarkItem, PlaylistOption } from "@/types/bookmark";
import { FlashcardItem } from "@/components/notebook/FlashcardItem";
import { BookmarkChatDrawer } from "@/components/notebook/BookmarkChatDrawer";
import { PlaylistSidebar } from "@/components/notebook/PlaylistSidebar";
import { NotebookPagination } from "@/components/notebook/NotebookPagination";
import { CreatePlaylistModal } from "@/components/notebook/CreatePlaylistModal";
import { authFetch } from "@/lib/authFetch";

const PAGE_SIZE = 10; // Tiêu chí Sprint 8 [AC 8.2.5]: Phân trang Sổ tay 10 bài/trang

export default function NotebookPage() {
  const router = useRouter();

  // Dữ liệu bài toán & Playlist
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [playlists, setPlaylists] = useState<PlaylistOption[]>([]);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState<string | null>(null);

  // Trạng thái Sidebar collapsible
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);

  // Phân trang
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [totalAllCount, setTotalAllCount] = useState<number>(0);

  // Trạng thái tải & lỗi
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState<boolean>(true);
  const [apiError, setApiError] = useState<string | null>(null);

  // Bộ lọc tìm kiếm
  const [searchQuery, setSearchQuery] = useState("");
  const [scoreFilter, setScoreFilter] = useState<"all" | "perfect" | "passed">("all");
  const [hasAttachmentOnly, setHasAttachmentOnly] = useState(false);

  // Drawer xem lại đoạn chat
  const [selectedBookmark, setSelectedBookmark] = useState<BookmarkItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  // 1. Fetch danh sách Playlists từ backend
  const fetchPlaylists = useCallback(async () => {
    setIsLoadingPlaylists(true);
    try {
      const res = await authFetch(`${BACKEND_URL}/bookmarks/playlists`);
      if (res.ok) {
        const data: PlaylistOption[] = await res.json();
        setPlaylists(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.warn("Lỗi tải danh sách playlist:", e);
    } finally {
      setIsLoadingPlaylists(false);
    }
  }, [BACKEND_URL]);

  // 2. Fetch danh sách bookmarks theo playlist và phân trang (10 bài/trang)
  const fetchBookmarks = useCallback(async (page: number = 1, playlistId: string | null = selectedPlaylistId) => {
    setIsLoading(true);
    setApiError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(PAGE_SIZE));

      if (playlistId) {
        params.set("playlist_id", playlistId);
      }
      if (searchQuery.trim()) {
        params.set("search", searchQuery.trim());
      }
      if (scoreFilter !== "all") {
        params.set("score_filter", scoreFilter);
      }
      if (hasAttachmentOnly) {
        params.set("has_attachment", "true");
      }

      const res = await authFetch(`${BACKEND_URL}/bookmarks?${params.toString()}`);

      if (res.ok) {
        const data = await res.json();
        const items: BookmarkItem[] = Array.isArray(data) ? data : [];
        setBookmarks(items);

        // Đọc header X-Total-Count từ server nếu có
        const serverTotalHeader = res.headers.get("x-total-count");
        if (serverTotalHeader) {
          const parsed = parseInt(serverTotalHeader, 10);
          if (!isNaN(parsed)) {
            setTotalCount(parsed);
            if (!playlistId && !searchQuery.trim() && scoreFilter === "all" && !hasAttachmentOnly) {
              setTotalAllCount(parsed);
            }
          }
        } else {
          setTotalCount(items.length);
        }
      } else if (res.status === 404 || res.status === 501) {
        setApiError("API Sổ tay (/bookmarks) đang trong quá trình đồng bộ từ máy chủ.");
        setBookmarks([]);
        setTotalCount(0);
      } else {
        setApiError("Chưa thể tải dữ liệu Sổ tay từ máy chủ. Vui lòng thử lại!");
        setBookmarks([]);
        setTotalCount(0);
      }
    } catch {
      setApiError("Lỗi kết nối mạng tới máy chủ Sổ tay.");
      setBookmarks([]);
      setTotalCount(0);
    } finally {
      setIsLoading(false);
    }
  }, [BACKEND_URL, selectedPlaylistId, searchQuery, scoreFilter, hasAttachmentOnly]);

  // Tải dữ liệu ban đầu
  useEffect(() => {
    let ignore = false;
    const loadPlaylists = async () => {
      try {
        const res = await authFetch(`${BACKEND_URL}/bookmarks/playlists`);
        if (res.ok && !ignore) {
          const data: PlaylistOption[] = await res.json();
          setPlaylists(Array.isArray(data) ? data : []);
        }
      } catch (e) {
        console.warn("Lỗi tải danh sách playlist:", e);
      } finally {
        if (!ignore) setIsLoadingPlaylists(false);
      }
    };
    loadPlaylists();
    return () => {
      ignore = true;
    };
  }, [BACKEND_URL]);

  useEffect(() => {
    let ignore = false;
    const loadBookmarks = async () => {
      queueMicrotask(() => {
        if (!ignore) {
          setIsLoading(true);
          setApiError(null);
        }
      });
      try {
        const params = new URLSearchParams();
        params.set("page", String(currentPage));
        params.set("page_size", String(PAGE_SIZE));

        if (selectedPlaylistId) {
          params.set("playlist_id", selectedPlaylistId);
        }
        if (searchQuery.trim()) {
          params.set("search", searchQuery.trim());
        }
        if (scoreFilter !== "all") {
          params.set("score_filter", scoreFilter);
        }
        if (hasAttachmentOnly) {
          params.set("has_attachment", "true");
        }

        const res = await authFetch(`${BACKEND_URL}/bookmarks?${params.toString()}`);
        if (ignore) return;

        if (res.ok) {
          const data = await res.json();
          const items: BookmarkItem[] = Array.isArray(data) ? data : [];
          setBookmarks(items);

          const serverTotalHeader = res.headers.get("x-total-count");
          if (serverTotalHeader) {
            const parsed = parseInt(serverTotalHeader, 10);
            if (!isNaN(parsed)) {
              setTotalCount(parsed);
              if (!selectedPlaylistId && !searchQuery.trim() && scoreFilter === "all" && !hasAttachmentOnly) {
                setTotalAllCount(parsed);
              }
            }
          } else {
            setTotalCount(items.length);
          }
        } else if (res.status === 404 || res.status === 501) {
          setApiError("API Sổ tay (/bookmarks) đang trong quá trình đồng bộ từ máy chủ.");
          setBookmarks([]);
          setTotalCount(0);
        } else {
          setApiError("Chưa thể tải dữ liệu Sổ tay từ máy chủ. Vui lòng thử lại!");
          setBookmarks([]);
          setTotalCount(0);
        }
      } catch {
        if (!ignore) {
          setApiError("Lỗi kết nối mạng tới máy chủ Sổ tay.");
          setBookmarks([]);
          setTotalCount(0);
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    };

    loadBookmarks();
    return () => {
      ignore = true;
    };
  }, [BACKEND_URL, currentPage, selectedPlaylistId, searchQuery, scoreFilter, hasAttachmentOnly]);

  // Handler tạo playlist mới
  const handleCreatePlaylist = async (name: string): Promise<boolean> => {
    try {
      const res = await authFetch(`${BACKEND_URL}/bookmarks/playlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });

      if (res.ok) {
        const created: PlaylistOption = await res.json();
        setPlaylists((prev) => [...prev, created]);
        setSelectedPlaylistId(created.id);
        setCurrentPage(1);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  // Handler xóa playlist
  const handleDeletePlaylist = async (playlistId: string): Promise<void> => {
    try {
      const res = await authFetch(`${BACKEND_URL}/bookmarks/playlists/${playlistId}`, {
        method: "DELETE",
      });

      if (res.ok || res.status === 204) {
        setPlaylists((prev) => prev.filter((p) => p.id !== playlistId));
        if (selectedPlaylistId === playlistId) {
          setSelectedPlaylistId(null);
          setCurrentPage(1);
        }
      }
    } catch (err) {
      console.warn("Lỗi xóa playlist:", err);
    }
  };

  // Handler xóa bookmark
  const handleDeleteBookmark = async (bookmarkId: string) => {
    try {
      const res = await authFetch(`${BACKEND_URL}/bookmarks/${bookmarkId}`, {
        method: "DELETE",
      });

      if (res.ok || res.status === 204) {
        setBookmarks((prev) => prev.filter((b) => b.id !== bookmarkId));
        setTotalCount((prev) => Math.max(0, prev - 1));
        setTotalAllCount((prev) => Math.max(0, prev - 1));
        fetchPlaylists(); // Cập nhật lại số lượng item_count trên danh sách
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

  // Chuyển playlist
  const handleSelectPlaylist = (playlistId: string | null) => {
    setSelectedPlaylistId(playlistId);
    setCurrentPage(1);
  };

  // Chuyển trang mượt mà
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Tính số trang
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  // Tên playlist hiện tại đang xem
  const currentPlaylist = useMemo(() => {
    if (!selectedPlaylistId) return null;
    return playlists.find((p) => p.id === selectedPlaylistId) || null;
  }, [selectedPlaylistId, playlists]);

  return (
    <div className="flex-1 flex flex-col h-full bg-[#FAFAF9] overflow-y-auto">
      {/* 1. Header trang Sổ tay: Typography cân bằng, màu sắc tinh tế, nền trắng sạch sẽ */}
      <header className="bg-white border-b border-stone-200/80 px-4 sm:px-6 py-4 sticky top-0 z-20 shadow-2xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          {/* Tiêu đề trang hài hòa */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-[#C1762A] border border-amber-200/60 flex items-center justify-center shrink-0">
              <BookMarked size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-bold text-stone-900 tracking-tight">
                  Sổ Tay Bài Toán Yêu Thích
                </h1>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-stone-100 text-stone-600">
                  {totalAllCount > 0 ? totalAllCount : totalCount} bài
                </span>
              </div>
              <p className="text-xs text-stone-500 mt-0.5">
                Ôn tập các bài toán trọng tâm và bí kíp Socratic đã học
              </p>
            </div>
          </div>

          {/* Các nút hành động trên Header */}
          <div className="flex items-center gap-2 self-start sm:self-auto">
            {/* Nút Ẩn/Hiện Sidebar Danh sách phát */}
            <button
              onClick={() => setIsSidebarOpen((prev) => !prev)}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer border",
                isSidebarOpen
                  ? "bg-amber-50 text-[#8C4905] border-amber-200"
                  : "bg-white text-stone-700 hover:bg-stone-50 border-stone-200"
              )}
              title={isSidebarOpen ? "Đóng danh sách phát" : "Mở danh sách phát"}
              aria-label="Danh sách phát"
            >
              <PanelLeft size={14} />
              <span>{isSidebarOpen ? "Thu gọn danh sách" : "Danh sách phát"}</span>
            </button>

            {/* Nút Đồng bộ */}
            <button
              onClick={() => {
                fetchPlaylists();
                fetchBookmarks(currentPage, selectedPlaylistId);
              }}
              disabled={isLoading || isLoadingPlaylists}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-stone-700 bg-white hover:bg-stone-50 border border-stone-200 transition-all cursor-pointer active:scale-95 shadow-2xs"
            >
              <RefreshCw size={12} className={cn((isLoading || isLoadingPlaylists) && "animate-spin")} />
              <span>Đồng bộ</span>
            </button>
          </div>
        </div>

        {/* 2. Thanh tìm kiếm gọn gàng & Bộ lọc Chips & Dropdown danh sách */}
        <div className="max-w-7xl mx-auto mt-3.5 pt-3 border-t border-stone-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-0">
            {/* Ô tìm kiếm rút gọn */}
            <div className="relative w-64 sm:w-72">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Tìm bài toán, đề bài, bí kíp..."
                className="w-full pl-9 pr-3 py-1.5 bg-white border border-stone-200 rounded-xl text-xs text-stone-800 placeholder:text-stone-400 focus:outline-none focus:border-[#C1762A] focus:ring-1 focus:ring-[#C1762A]/20 transition-all shadow-2xs"
              />
            </div>

            {/* Dropdown chọn nhanh Playlist tích hợp ngay cạnh ô tìm kiếm */}
            <div className="relative">
              <select
                value={selectedPlaylistId ?? ""}
                onChange={(e) => {
                  const val = e.target.value;
                  handleSelectPlaylist(val === "" ? null : val);
                }}
                className="appearance-none pl-3 pr-8 py-1.5 bg-white border border-stone-200 rounded-xl text-xs font-semibold text-stone-700 hover:border-stone-300 focus:outline-none focus:border-[#C1762A] cursor-pointer shadow-2xs transition-all"
              >
                <option value="">⭐ Tất cả bài toán ({totalAllCount > 0 ? totalAllCount : totalCount})</option>
                {playlists.map((pl) => (
                  <option key={`opt-${pl.id}`} value={pl.id}>
                    {pl.name} ({pl.item_count} bài)
                  </option>
                ))}
              </select>
              <ChevronDown
                size={13}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
              />
            </div>
          </div>

          {/* Bộ lọc Chips (viên thuốc nhỏ gọn gàng) */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
            <button
              onClick={() => {
                setScoreFilter("all");
                setCurrentPage(1);
              }}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-semibold transition-all shrink-0 cursor-pointer touch-manipulation",
                scoreFilter === "all"
                  ? "bg-[#C1762A] text-white shadow-2xs"
                  : "bg-white text-stone-600 border border-stone-200 hover:bg-stone-50"
              )}
            >
              Tất cả
            </button>
            <button
              onClick={() => {
                setScoreFilter("perfect");
                setCurrentPage(1);
              }}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1 transition-all shrink-0 cursor-pointer touch-manipulation",
                scoreFilter === "perfect"
                  ? "bg-[#C1762A] text-white shadow-2xs"
                  : "bg-white text-stone-600 border border-stone-200 hover:bg-stone-50"
              )}
            >
              <Award size={12} />
              Tự lập 100đ
            </button>
            <button
              onClick={() => {
                setHasAttachmentOnly(!hasAttachmentOnly);
                setCurrentPage(1);
              }}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1 transition-all shrink-0 cursor-pointer touch-manipulation",
                hasAttachmentOnly
                  ? "bg-[#C1762A] text-white shadow-2xs"
                  : "bg-white text-stone-600 border border-stone-200 hover:bg-stone-50"
              )}
            >
              <ImageIcon size={12} />
              Có ảnh đề bài
            </button>
          </div>
        </div>

        {/* 3. Horizontal Menu / Tabs (Menu ngang danh sách phát) giải phóng không gian bên trái */}
        <div className="max-w-7xl mx-auto mt-3 flex items-center gap-1.5 overflow-x-auto pb-1 pt-0.5">
          <button
            onClick={() => handleSelectPlaylist(null)}
            className={cn(
              "px-3 py-1 rounded-lg text-xs font-semibold shrink-0 transition-all cursor-pointer touch-manipulation flex items-center gap-1.5",
              selectedPlaylistId === null
                ? "bg-amber-100/70 text-[#8C4905] border border-amber-300/80 font-bold"
                : "bg-white text-stone-600 border border-stone-200 hover:bg-stone-50"
            )}
          >
            <Star size={12} className={selectedPlaylistId === null ? "fill-current" : ""} />
            <span>Tất cả bài</span>
            <span className="text-[11px] opacity-75">({totalAllCount > 0 ? totalAllCount : totalCount})</span>
          </button>

          {playlists.map((pl) => (
            <button
              key={`tab-${pl.id}`}
              onClick={() => handleSelectPlaylist(pl.id)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-semibold shrink-0 transition-all cursor-pointer touch-manipulation flex items-center gap-1.5",
                selectedPlaylistId === pl.id
                  ? "bg-amber-100/70 text-[#8C4905] border border-amber-300/80 font-bold"
                  : "bg-white text-stone-600 border border-stone-200 hover:bg-stone-50"
              )}
            >
              <Folder size={12} />
              <span>{pl.name}</span>
              <span className="text-[11px] opacity-75">({pl.item_count})</span>
            </button>
          ))}

          {/* Nút thêm playlist nhanh trên thanh tab */}
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-2.5 py-1 rounded-lg text-xs font-semibold text-[#C1762A] hover:bg-amber-50 border border-dashed border-amber-300/80 shrink-0 transition-all flex items-center gap-1 cursor-pointer"
            title="Tạo danh sách mới"
          >
            <Plus size={13} />
            <span>Thêm playlist</span>
          </button>
        </div>
      </header>

      {/* 4. Thân trang: Thoáng đãng với padding rộng và khoảng cách hợp lý */}
      <div className="flex-1 p-5 sm:p-8 max-w-7xl mx-auto w-full flex items-start gap-6">
        {/* Collapsible Sidebar: Chỉ trượt ra khi học sinh mở, không chiếm chỗ cố định */}
        {isSidebarOpen && (
          <div className="sticky top-32 z-10 shrink-0">
            <PlaylistSidebar
              playlists={playlists}
              selectedPlaylistId={selectedPlaylistId}
              totalBookmarksCount={totalAllCount > 0 ? totalAllCount : totalCount}
              isLoading={isLoadingPlaylists}
              onSelectPlaylist={handleSelectPlaylist}
              onCreatePlaylist={handleCreatePlaylist}
              onDeletePlaylist={handleDeletePlaylist}
              onClose={() => setIsSidebarOpen(false)}
            />
          </div>
        )}

        {/* Lưới bài toán chính: Chiếm trọn không gian thoáng đãng */}
        <main className="flex-1 w-full min-w-0">
          {/* Header danh mục bài toán đang xem */}
          <div className="mb-5 flex items-center justify-between pb-3 border-b border-stone-200/80">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-md bg-amber-50 text-[#C1762A] flex items-center justify-center">
                {currentPlaylist ? <Folder size={13} /> : <Star size={13} />}
              </span>
              <h2 className="text-sm font-bold text-stone-800">
                {currentPlaylist ? currentPlaylist.name : "Tất cả bài toán đã lưu"}
              </h2>
              <span className="text-xs text-stone-400 font-medium">
                ({totalCount} bài)
              </span>
            </div>

            <span className="text-xs text-stone-400 font-medium">
              Trang {currentPage} / {totalPages}
            </span>
          </div>

          {/* Trạng thái Loading Skeleton */}
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl p-5 border border-stone-200/80 shadow-2xs animate-pulse space-y-4"
                >
                  <div className="h-5 bg-stone-100 rounded-lg w-2/3"></div>
                  <div className="h-20 bg-stone-50 rounded-lg"></div>
                  <div className="h-10 bg-stone-50 rounded-lg"></div>
                </div>
              ))}
            </div>
          ) : apiError ? (
            /* Thông báo lỗi */
            <div className="bg-white border border-stone-200 rounded-xl p-8 text-center max-w-md mx-auto shadow-2xs my-10 space-y-3">
              <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
                <Layers size={24} />
              </div>
              <h3 className="text-sm font-bold text-stone-900">
                Dịch vụ Sổ tay đang kết nối
              </h3>
              <p className="text-xs text-stone-500 leading-relaxed">
                {apiError}
              </p>
              <button
                onClick={() => fetchBookmarks(currentPage, selectedPlaylistId)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-[#C1762A] text-white rounded-lg text-xs font-semibold hover:bg-[#8C4905] transition-colors cursor-pointer"
              >
                <RefreshCw size={12} />
                <span>Thử kết nối lại</span>
              </button>
            </div>
          ) : bookmarks.length === 0 ? (
            /* Empty States */
            selectedPlaylistId ? (
              // Empty state khi playlist được chọn chưa có bài
              <div className="bg-white border border-stone-200 rounded-xl p-10 text-center max-w-sm mx-auto shadow-2xs my-8 space-y-3">
                <div className="w-12 h-12 rounded-xl bg-stone-100 text-stone-500 flex items-center justify-center mx-auto">
                  <Folder size={24} />
                </div>
                <h3 className="text-sm font-bold text-stone-900">
                  Danh sách này đang trống
                </h3>
                <p className="text-xs text-stone-500 leading-relaxed">
                  Chưa có bài toán nào trong danh sách &quot;{currentPlaylist?.name}&quot;. Hãy chọn thêm bài vào danh sách này khi lưu bài nhé!
                </p>
                <button
                  type="button"
                  onClick={() => handleSelectPlaylist(null)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-stone-800 hover:bg-stone-900 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  <Star size={12} />
                  <span>Xem tất cả bài toán</span>
                </button>
              </div>
            ) : searchQuery.trim() || scoreFilter !== "all" || hasAttachmentOnly ? (
              // Empty state khi lọc không khớp
              <div className="bg-white border border-stone-200 rounded-xl p-8 text-center max-w-sm mx-auto shadow-2xs my-8 space-y-2.5">
                <p className="text-xs font-semibold text-stone-700">
                  Không tìm thấy bài toán nào phù hợp với bộ lọc.
                </p>
                <button
                  onClick={() => {
                    setSearchQuery("");
                    setScoreFilter("all");
                    setHasAttachmentOnly(false);
                    setCurrentPage(1);
                  }}
                  className="text-xs font-bold text-[#C1762A] hover:underline cursor-pointer"
                >
                  Đặt lại bộ lọc
                </button>
              </div>
            ) : (
              // Empty state sổ tay hoàn toàn trống
              <div className="bg-white border border-stone-200 rounded-xl p-12 text-center max-w-md mx-auto shadow-2xs my-10 space-y-3.5">
                <div className="w-14 h-14 rounded-xl bg-amber-50 text-[#C1762A] border border-amber-200/50 flex items-center justify-center mx-auto">
                  <Sparkles size={26} />
                </div>
                <h3 className="text-base font-bold text-stone-900">
                  Sổ tay của bạn đang trống
                </h3>
                <p className="text-xs text-stone-500 leading-relaxed">
                  Khi giải xong một bài toán trong khung Chat và bấm &quot;Đã hiểu&quot;, hãy bấm
                  <span className="font-semibold text-stone-800"> ⭐ &quot;Lưu vào Sổ tay&quot;</span> để tạo playlist và lưu lại bí kíp tư duy nhé!
                </p>
                <button
                  onClick={() => router.push("/dashboard/chat")}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#C1762A] hover:bg-[#8C4905] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer mt-1"
                >
                  <span>Đến khung Chat học bài ngay</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            )
          ) : (
            /* Lưới thẻ Flashcard thoáng đãng với gap-6 và phân trang 10 bài/trang */
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-150">
                {bookmarks.map((bm) => (
                  <FlashcardItem
                    key={bm.id}
                    bookmark={bm}
                    onOpenChat={handleOpenChat}
                    onDelete={handleDeleteBookmark}
                  />
                ))}
              </div>

              {/* Bộ phân trang 10 bài/trang */}
              <NotebookPagination
                currentPage={currentPage}
                totalPages={totalPages}
                totalItems={totalCount}
                pageSize={PAGE_SIZE}
                onPageChange={handlePageChange}
              />
            </div>
          )}
        </main>
      </div>

      {/* 5. Floating Action Button (FAB) cho "Tạo playlist" góc dưới bên phải */}
      <div className="fixed bottom-6 right-6 z-30">
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-3 bg-[#C1762A] hover:bg-[#8C4905] text-white text-xs font-bold rounded-full shadow-lg hover:shadow-xl active:scale-95 transition-all cursor-pointer touch-manipulation group"
          title="Tạo danh sách phát mới"
          aria-label="Tạo playlist"
        >
          <Plus size={16} strokeWidth={2.4} className="group-hover:rotate-90 transition-transform duration-200" />
          <span className="hidden sm:inline">Tạo playlist</span>
        </button>
      </div>

      {/* 6. Modal Tạo Playlist Mới */}
      <CreatePlaylistModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreatePlaylist}
      />

      {/* 7. Drawer xem lại đối thoại tư duy của bài toán */}
      <BookmarkChatDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        sessionId={selectedBookmark?.session_id || null}
        problemTitle={selectedBookmark?.title || selectedBookmark?.problem_snapshot || selectedBookmark?.session_title}
        independenceScore={selectedBookmark?.independence_score}
        createdAt={selectedBookmark?.created_at}
        dialogueMessages={selectedBookmark?.dialogue_messages}
      />
    </div>
  );
}
