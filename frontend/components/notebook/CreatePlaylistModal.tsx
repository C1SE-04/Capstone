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
      setError("Vui lòng nhập tên ngăn lưu trữ");
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
      setError("Không thể tạo ngăn lưu trữ. Tên có thể đã tồn tại.");
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
      <div className="relative z-10 bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl border border-[#F1CCA6] animate-in fade-in zoom-in-95 duration-150 text-left">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-50 text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
              <FolderPlus size={18} />
            </div>
            <h3 className="text-base font-bold text-[#1C1917]">
              Tạo ngăn lưu trữ mới
            </h3>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-7 h-7 rounded-lg hover:bg-[#F7ECE1] flex items-center justify-center text-[#7A3E04] hover:text-[#1C1917] transition-colors cursor-pointer"
            aria-label="Đóng"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#8C4905] mb-1.5">
              Tên ngăn lưu trữ
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
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#F7ECE1]/30 border border-[#F1CCA6] text-[#1C1917] text-sm focus:outline-none focus:bg-white focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-all placeholder:text-[#7A3E04]/50"
            />
            {error && (
              <p className="mt-1.5 text-xs text-[#EF4444] font-medium">{error}</p>
            )}
          </div>

          {/* Footer buttons */}
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-[#7A3E04] hover:text-[#1C1917] hover:bg-[#F7ECE1] rounded-xl transition-colors cursor-pointer"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className="px-4 py-2 bg-[#C1762A] hover:bg-[#8C4905] active:scale-[0.98] disabled:opacity-50 text-white text-xs font-bold rounded-xl transition-all duration-150 ease-out shadow-xs flex items-center gap-1.5 cursor-pointer focus-visible:outline-2 focus-visible:outline-[#C1762A]"
            >
              {isSubmitting && <Loader2 size={13} className="animate-spin" />}
              <span>Tạo ngăn lưu trữ</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreatePlaylistModal;
