"use client";

import { useState } from "react";
import { FolderPlus, X, Loader2 } from "lucide-react";

interface CreatePlaylistModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => Promise<boolean>;
}

export function CreatePlaylistModal({
  isOpen,
  onClose,
  onCreate,
}: CreatePlaylistModalProps) {
  const [name, setName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = name.trim();
    if (!clean) {
      setError("Vui lòng nhập tên danh sách phát");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    const success = await onCreate(clean);
    setIsSubmitting(false);

    if (success) {
      setName("");
      onClose();
    } else {
      setError("Không thể tạo danh sách phát. Tên có thể đã tồn tại.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/35 backdrop-blur-xs transition-opacity duration-150 animate-in fade-in"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative z-10 bg-white rounded-xl p-6 max-w-sm w-full shadow-xl border border-stone-200 animate-in fade-in zoom-in-95 duration-150 text-left">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-[#C1762A] flex items-center justify-center border border-amber-200/60">
              <FolderPlus size={18} />
            </div>
            <h3 className="text-base font-bold text-stone-900">
              Tạo danh sách mới
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
            aria-label="Đóng"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-stone-600 mb-1.5">
              Tên danh sách phát
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                if (error) setError(null);
              }}
              placeholder="Ví dụ: Ôn thi HK1, Hình học..."
              autoFocus
              className="w-full px-3.5 py-2.5 rounded-xl bg-stone-50 border border-stone-200 text-stone-800 text-sm focus:outline-none focus:bg-white focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-all placeholder:text-stone-400"
            />
            {error && (
              <p className="mt-1.5 text-xs text-red-600 font-medium">{error}</p>
            )}
          </div>

          {/* Footer buttons */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-lg transition-colors cursor-pointer"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="px-4 py-2 bg-[#C1762A] hover:bg-[#8C4905] active:scale-95 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
            >
              {isSubmitting && <Loader2 size={13} className="animate-spin" />}
              <span>Tạo danh sách</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreatePlaylistModal;
