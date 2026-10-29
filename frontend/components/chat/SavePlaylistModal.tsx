"use client";

import React, { useState, useEffect } from "react";
import { Bookmark, X, Check, Plus, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { authFetch } from "@/lib/authFetch";

export interface PlaylistOption {
  id: string;
  name: string;
  item_count: number;
  is_default?: boolean;
}

interface SavePlaylistModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  messageCreatedAt?: string | Date;
  initialTitle?: string;
  initialBookmarkId?: string;
  onSaved?: (bookmarkId: string) => void;
}

export function SavePlaylistModal({
  isOpen,
  onClose,
  sessionId,
  messageCreatedAt,
  initialTitle = "",
  initialBookmarkId,
  onSaved,
}: SavePlaylistModalProps) {
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  // Tên bài toán
  const [problemTitle, setProblemTitle] = useState(initialTitle);
  const [isSuggestingTitle, setIsSuggestingTitle] = useState(false);

  // Danh sách playlist
  const [playlists, setPlaylists] = useState<PlaylistOption[]>([]);
  const [selectedPlaylistIds, setSelectedPlaylistIds] = useState<string[]>([]);
  const [isLoadingPlaylists, setIsLoadingPlaylists] = useState(false);

  // Tạo playlist mới
  const [showCreateBox, setShowCreateBox] = useState(true);
  const [newPlaylistName, setNewPlaylistName] = useState("");
  const [isCreatingPlaylist, setIsCreatingPlaylist] = useState(false);

  // Trạng thái lưu
  const [isSaving, setIsSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Tải danh sách playlist và gợi ý tên bài toán khi mở modal
  useEffect(() => {
    if (!isOpen || !sessionId) return;
    let isMounted = true;

    const loadData = async () => {
      try {
        const res = await authFetch(`${BACKEND_URL}/bookmarks/playlists`);
        if (res.ok && isMounted) {
          const data: PlaylistOption[] = await res.json();
          setPlaylists(data);
          const defaultPl = data.find((p) => p.is_default) || data[0];
          if (defaultPl) {
            setSelectedPlaylistIds((prev) => (prev.length === 0 ? [defaultPl.id] : prev));
          }
        }
      } catch (e) {
        console.error("[SavePlaylistModal] Lỗi tải playlists:", e);
      } finally {
        if (isMounted) setIsLoadingPlaylists(false);
      }

      if (!initialTitle) {
        setIsSuggestingTitle(true);
        try {
          const res = await authFetch(`${BACKEND_URL}/bookmarks/suggest-title`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId }),
          });
          if (res.ok && isMounted) {
            const data = await res.json();
            if (data.friendly_title) {
              setProblemTitle(data.friendly_title);
            }
          }
        } catch {
          // ignore
        } finally {
          if (isMounted) setIsSuggestingTitle(false);
        }
      }
    };

    loadData();

    // Hỗ trợ đóng modal bằng phím Escape chuẩn trải nghiệm desktop/web
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      isMounted = false;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, sessionId, initialTitle, BACKEND_URL, onClose]);

  if (!isOpen) return null;

  // Toggle chọn / bỏ chọn playlist
  const togglePlaylist = (id: string) => {
    setSelectedPlaylistIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  // 3. Tạo playlist mới và tự động chọn (hoặc lưu luôn) theo [AC 8.2.4]
  const handleCreateAndSavePlaylist = async () => {
    const cleanName = newPlaylistName.trim();
    if (!cleanName) return;

    setIsCreatingPlaylist(true);
    setErrorMsg(null);

    try {
      const res = await authFetch(`${BACKEND_URL}/bookmarks/playlists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: cleanName,
          initial_bookmark_id: initialBookmarkId || undefined,
        }),
      });

      if (res.ok) {
        const created: PlaylistOption = await res.json();
        setPlaylists((prev) => [...prev, created]);
        setSelectedPlaylistIds((prev) => [...prev, created.id]);
        setNewPlaylistName("");
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Không thể tạo danh sách mới, vui lòng thử lại!");
      }
    } catch {
      setErrorMsg("Lỗi kết nối khi tạo ngăn lưu trữ.");
    } finally {
      setIsCreatingPlaylist(false);
    }
  };

  // 4. Bấm "Lưu thay đổi"
  const handleSaveBookmark = async () => {
    if (isSaving) return;
    setIsSaving(true);
    setErrorMsg(null);

    try {
      let isoCreatedAt: string | undefined = undefined;
      if (messageCreatedAt) {
        try {
          const d = new Date(messageCreatedAt);
          if (!isNaN(d.getTime())) {
            isoCreatedAt = d.toISOString();
          }
        } catch {
          // ignore
        }
      }

      const res = await authFetch(`${BACKEND_URL}/bookmarks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message_created_at: isoCreatedAt,
          title: problemTitle.trim() || undefined,
          playlist_ids: selectedPlaylistIds,
        }),
      });

      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        onSaved?.(data.id || "saved");
        onClose();
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Không thể lưu vào Sổ tay, vui lòng thử lại!");
      }
    } catch {
      setErrorMsg("Không thể kết nối máy chủ để lưu bài toán.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Lớp mờ nền Apple-style: độ mờ 40% nhẹ nhàng, blur sâu */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-md transition-opacity duration-200 animate-in fade-in"
        onClick={onClose}
      />

      {/* Thẻ Modal chuẩn thiết kế Figma */}
      <div className="relative z-10 bg-white rounded-3xl p-6 sm:p-7 max-w-md w-full shadow-2xl border border-[#F1CCA6]/60 animate-modal-in text-left">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <div className="text-[#A05215]">
              <Bookmark size={22} className="stroke-[2.2] fill-[#A05215]/10" />
            </div>
            <h3 className="text-xl font-bold text-[#8C4905]">
              Lưu vào Sổ tay
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-stone-100 hover:bg-stone-200 active:scale-90 flex items-center justify-center text-stone-500 transition-[transform,background-color] duration-150 cursor-pointer touch-manipulation"
            aria-label="Đóng"
          >
            <X size={18} />
          </button>
        </div>

        {/* Thông báo lỗi nếu có */}
        {errorMsg && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-600 font-medium animate-in fade-in duration-150">
            {errorMsg}
          </div>
        )}

        {/* Khối 1: TÊN BÀI TOÁN */}
        <div className="mb-5">
          <label className="block text-[11px] font-bold text-stone-400 tracking-wider uppercase mb-2">
            TÊN BÀI TOÁN
          </label>
          <div className="relative">
            <input
              type="text"
              value={problemTitle}
              onChange={(e) => setProblemTitle(e.target.value)}
              placeholder={isSuggestingTitle ? "AI đang gợi ý tên bài..." : "Nhập tên bài toán gợi nhớ..."}
              disabled={isSuggestingTitle}
              className="w-full px-4 py-3 rounded-2xl bg-stone-50/70 border border-stone-200 text-stone-800 text-sm font-semibold focus:outline-none focus:bg-white focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-[border-color,box-shadow,background-color] duration-150 ease-out"
            />
            {isSuggestingTitle && (
              <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
                <Loader2 size={16} className="text-[#C1762A] animate-spin" />
              </div>
            )}
          </div>
        </div>

        {/* Khối 2: CHỌN NGĂN LƯU TRỮ */}
        <div className="mb-6">
          <label className="block text-[11px] font-bold text-stone-400 tracking-wider uppercase mb-2.5">
            CHỌN NGĂN LƯU TRỮ
          </label>

          {isLoadingPlaylists ? (
            <div className="py-6 flex flex-col items-center justify-center gap-2 text-stone-400 text-xs">
              <Loader2 size={20} className="animate-spin text-[#C1762A]" />
              <span>Đang tải ngăn lưu trữ...</span>
            </div>
          ) : (
            <div className="max-h-52 overflow-y-auto space-y-1 pr-1">
              {playlists.map((pl) => {
                const isSelected = selectedPlaylistIds.includes(pl.id);
                return (
                  <div
                    key={pl.id}
                    onClick={() => togglePlaylist(pl.id)}
                    className="flex items-center justify-between p-2.5 rounded-xl hover:bg-stone-50/90 active:bg-stone-100 transition-[background-color] duration-150 cursor-pointer select-none group touch-manipulation"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={cn(
                          "w-5 h-5 rounded-md flex items-center justify-center transition-[background-color,border-color,transform] duration-150 ease-out shrink-0 group-active:scale-90",
                          isSelected
                            ? "bg-[#A05215] text-white shadow-xs"
                            : "border-2 border-stone-300 bg-white group-hover:border-stone-400"
                        )}
                      >
                        {isSelected && <Check size={14} strokeWidth={3} />}
                      </div>

                      <span
                        className={cn(
                          "text-sm text-stone-800 truncate",
                          isSelected ? "font-bold text-stone-900" : "font-medium"
                        )}
                      >
                        {pl.name}
                      </span>
                    </div>

                    <span className="px-2.5 py-0.5 rounded-lg bg-stone-100 text-stone-500 text-xs font-medium shrink-0 ml-2">
                      {pl.item_count} bài
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Nút + Tạo ngăn lưu trữ mới */}
          <div className="mt-3">
            <button
              type="button"
              onClick={() => setShowCreateBox((prev) => !prev)}
              className="inline-flex items-center gap-1.5 text-sm font-bold text-[#A05215] hover:text-[#8C4905] active:scale-[0.98] transition-[transform,color] duration-150 cursor-pointer mb-2 touch-manipulation"
            >
              <Plus size={16} strokeWidth={2.5} />
              Tạo ngăn lưu trữ mới
            </button>

            {/* Khung nhập tạo ngăn lưu trữ mới */}
            {showCreateBox && (
              <div className="p-2.5 rounded-2xl border-2 border-dashed border-[#F1CCA6] bg-[#FFFBF7] flex items-center gap-2">
                <input
                  type="text"
                  value={newPlaylistName}
                  onChange={(e) => setNewPlaylistName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleCreateAndSavePlaylist();
                    }
                  }}
                  placeholder="Tên ngăn lưu trữ mới"
                  className="flex-1 px-3.5 py-2 rounded-xl bg-white border border-stone-200 text-xs text-stone-800 placeholder:text-stone-400 focus:outline-none focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-[border-color,box-shadow] duration-150"
                />
                <button
                  type="button"
                  onClick={handleCreateAndSavePlaylist}
                  disabled={isCreatingPlaylist || !newPlaylistName.trim()}
                  className="px-4 py-2 bg-[#A05215] hover:bg-[#8C4905] active:scale-[0.96] disabled:opacity-50 text-white text-xs font-bold rounded-xl transition-[transform,background-color] duration-150 shadow-xs cursor-pointer whitespace-nowrap flex items-center gap-1 touch-manipulation"
                >
                  {isCreatingPlaylist ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    "Tạo"
                  )}
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Footer: Hủy & Lưu thay đổi */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2.5 text-stone-500 hover:text-stone-800 active:scale-95 text-sm font-semibold transition-[transform,color] duration-150 cursor-pointer touch-manipulation"
          >
            Hủy
          </button>
          <button
            type="button"
            onClick={handleSaveBookmark}
            disabled={isSaving}
            className="px-6 py-2.5 bg-[#A05215] hover:bg-[#8C4905] active:scale-[0.97] text-white text-sm font-bold rounded-2xl shadow-md shadow-amber-900/10 cursor-pointer transition-[transform,background-color,box-shadow] duration-150 flex items-center gap-2 touch-manipulation"
          >
            {isSaving && <Loader2 size={15} className="animate-spin" />}
            Lưu thay đổi
          </button>
        </div>
      </div>
    </div>
  );
}

export default SavePlaylistModal;
