"use client";

import { useState } from "react";
import {
  Folder,
  Star,
  Plus,
  Trash2,
  Loader2,
  Check,
  X,
  ListMusic,
  BookMarked,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { PlaylistOption } from "@/types/bookmark";

interface PlaylistSidebarProps {
  playlists: PlaylistOption[];
  selectedPlaylistId: string | null;
  totalBookmarksCount: number;
  isLoading: boolean;
  onSelectPlaylist: (playlistId: string | null) => void;
  onCreatePlaylist: (name: string) => Promise<boolean>;
  onDeletePlaylist: (playlistId: string) => Promise<void>;
  onClose?: () => void;
}

export function PlaylistSidebar({
  playlists,
  selectedPlaylistId,
  totalBookmarksCount,
  isLoading,
  onSelectPlaylist,
  onCreatePlaylist,
  onDeletePlaylist,
  onClose,
}: PlaylistSidebarProps) {
  const [showCreateBox, setShowCreateBox] = useState(false);
  const [newPlaylistName, setNewPlaylistName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleCreate = async () => {
    const clean = newPlaylistName.trim();
    if (!clean || isCreating) return;

    setIsCreating(true);
    const success = await onCreatePlaylist(clean);
    setIsCreating(false);

    if (success) {
      setNewPlaylistName("");
      setShowCreateBox(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, pl: PlaylistOption) => {
    e.stopPropagation();
    if (pl.is_default || deletingId) return;

    const confirmed = window.confirm(
      `Bạn có chắc chắn muốn xóa danh sách "${pl.name}"? Các bài toán bên trong vẫn được giữ an toàn trong Sổ tay.`
    );
    if (!confirmed) return;

    setDeletingId(pl.id);
    await onDeletePlaylist(pl.id);
    setDeletingId(null);
  };

  return (
    <aside className="w-72 shrink-0 bg-white rounded-xl border border-stone-200/90 p-4 shadow-xs flex flex-col justify-between gap-4 animate-in slide-in-from-left duration-200">
      <div className="space-y-3">
        {/* Header sidebar */}
        <div className="flex items-center justify-between pb-3 border-b border-stone-100 px-1">
          <div className="flex items-center gap-2 text-stone-800">
            <span className="w-7 h-7 rounded-lg bg-amber-50 text-[#C1762A] border border-amber-200/50 flex items-center justify-center shrink-0">
              <ListMusic size={15} />
            </span>
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-stone-800">
                Ngăn Lưu Trữ
              </h2>
              <p className="text-[11px] text-stone-400">
                {playlists.length} danh mục
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setShowCreateBox((prev) => !prev)}
              className="w-7 h-7 rounded-lg hover:bg-stone-100 text-stone-500 hover:text-stone-800 active:scale-95 flex items-center justify-center transition-all cursor-pointer"
              title="Tạo ngăn lưu trữ mới"
              aria-label="Tạo ngăn lưu trữ mới"
            >
              {showCreateBox ? <X size={14} /> : <Plus size={15} />}
            </button>

            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="w-7 h-7 rounded-lg hover:bg-stone-100 text-stone-400 hover:text-stone-700 active:scale-95 flex items-center justify-center transition-all cursor-pointer"
                title="Thu gọn sidebar"
                aria-label="Thu gọn"
              >
                <ChevronLeft size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Khung tạo nhanh ngăn lưu trữ mới */}
        {showCreateBox && (
          <div className="p-2.5 rounded-lg bg-stone-50 border border-stone-200 shadow-2xs space-y-2 animate-in fade-in duration-150">
            <label className="block text-[11px] font-semibold text-stone-700">
              Tên ngăn lưu trữ mới
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={newPlaylistName}
                onChange={(e) => setNewPlaylistName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    handleCreate();
                  } else if (e.key === "Escape") {
                    setShowCreateBox(false);
                  }
                }}
                autoFocus
                placeholder="VD: Ôn thi HK1..."
                className="flex-1 px-2.5 py-1.5 rounded-lg bg-white border border-stone-200 text-xs text-stone-800 placeholder:text-stone-400 focus:outline-none focus:border-[#C1762A] focus:ring-1 focus:ring-[#C1762A]/20 transition-all"
              />
              <button
                type="button"
                onClick={handleCreate}
                disabled={isCreating || !newPlaylistName.trim()}
                className="px-2.5 py-1.5 bg-[#C1762A] hover:bg-[#8C4905] active:scale-95 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all flex items-center justify-center shrink-0 cursor-pointer shadow-xs"
              >
                {isCreating ? <Loader2 size={12} className="animate-spin" /> : <Check size={13} />}
              </button>
            </div>
          </div>
        )}

        {/* Danh sách mục playlist */}
        <div className="space-y-1 max-h-[calc(100vh-380px)] overflow-y-auto pr-0.5">
          {/* Mục "Tất cả bài toán" */}
          <button
            type="button"
            onClick={() => onSelectPlaylist(null)}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 text-left group cursor-pointer",
              selectedPlaylistId === null
                ? "bg-amber-50 text-[#8C4905] font-bold border border-amber-200/80"
                : "text-stone-700 hover:bg-stone-50 hover:text-stone-900"
            )}
          >
            <div className="flex items-center gap-2 truncate">
              <span
                className={cn(
                  "w-6 h-6 rounded-md flex items-center justify-center shrink-0 transition-colors",
                  selectedPlaylistId === null
                    ? "bg-[#C1762A] text-white"
                    : "bg-stone-100 text-stone-500 group-hover:text-stone-700"
                )}
              >
                <BookMarked size={13} />
              </span>
              <span className="truncate">Tất cả bài toán</span>
            </div>

            <span
              className={cn(
                "text-[11px] font-bold px-2 py-0.5 rounded-full shrink-0 transition-colors",
                selectedPlaylistId === null
                  ? "bg-amber-200/60 text-[#8C4905]"
                  : "bg-stone-100 text-stone-500"
              )}
            >
              {totalBookmarksCount}
            </span>
          </button>

          {/* Các playlist của học sinh */}
          {isLoading && playlists.length === 0 ? (
            <div className="py-6 flex flex-col items-center justify-center gap-2 text-stone-400 text-xs">
              <Loader2 size={16} className="animate-spin text-[#C1762A]" />
              <span>Đang tải...</span>
            </div>
          ) : (
            playlists.map((pl) => {
              const isActive = selectedPlaylistId === pl.id;
              const isDeleting = deletingId === pl.id;

              return (
                <div
                  key={pl.id}
                  onClick={() => onSelectPlaylist(pl.id)}
                  className={cn(
                    "w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 text-left group cursor-pointer select-none",
                    isActive
                      ? "bg-amber-50 text-[#8C4905] font-bold border border-amber-200/80"
                      : "text-stone-700 hover:bg-stone-50 hover:text-stone-900"
                  )}
                >
                  <div className="flex items-center gap-2 truncate min-w-0">
                    <span
                      className={cn(
                        "w-6 h-6 rounded-md flex items-center justify-center shrink-0 transition-colors",
                        isActive
                          ? "bg-[#C1762A] text-white"
                          : "bg-stone-100 text-stone-500 group-hover:text-stone-700"
                      )}
                    >
                      {pl.is_default ? <Star size={12} className="fill-current" /> : <Folder size={12} />}
                    </span>
                    <span className="truncate" title={pl.name}>
                      {pl.name}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 shrink-0 ml-1.5">
                    <span
                      className={cn(
                        "text-[11px] font-bold px-2 py-0.5 rounded-full transition-colors",
                        isActive
                          ? "bg-amber-200/60 text-[#8C4905]"
                          : "bg-stone-100 text-stone-500"
                      )}
                    >
                      {pl.item_count}
                    </span>

                    {!pl.is_default && (
                      <button
                        type="button"
                        onClick={(e) => handleDelete(e, pl)}
                        disabled={isDeleting}
                        className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-1 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded transition-all"
                        title="Xóa ngăn lưu trữ này"
                        aria-label="Xóa ngăn lưu trữ"
                      >
                        {isDeleting ? (
                          <Loader2 size={12} className="animate-spin text-red-500" />
                        ) : (
                          <Trash2 size={12} />
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}

export default PlaylistSidebar;
