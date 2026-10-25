"use client";

import { useEffect } from "react";
import { AlertTriangle, X, UploadCloud } from "lucide-react";
import { createPortal } from "react-dom";

interface FileTooLargeToastProps {
  isOpen: boolean;
  onClose: () => void;
  message?: string;
  fileSizeMb?: number;
  duration?: number;
}

export function FileTooLargeToast({
  isOpen,
  onClose,
  message,
  fileSizeMb,
  duration = 5000,
}: FileTooLargeToastProps) {
  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [isOpen, onClose, duration]);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed top-5 left-1/2 -translate-x-1/2 z-[99999] w-[92vw] max-w-md animate-in slide-in-from-top-6 fade-in duration-300 ease-out">
      <div className="bg-white rounded-2xl p-4 shadow-xl border border-[#F1CCA6] text-gray-800 flex items-start gap-3.5">
        {/* Warning Icon Badge */}
        <div className="w-10 h-10 rounded-xl bg-[#F7ECE1] border border-[#F1CCA6] flex items-center justify-center text-[#8C4905] shrink-0">
          <AlertTriangle size={20} />
        </div>

        {/* Message Content */}
        <div className="flex-1 min-w-0 pt-0.5">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-amber-900">
              Dung lượng ảnh vượt quá 5MB!
            </h4>
            {fileSizeMb && (
              <span className="text-[11px] font-extrabold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                {fileSizeMb.toFixed(1)} MB
              </span>
            )}
          </div>
          <p className="text-xs text-amber-800/90 mt-1 leading-relaxed">
            {message ||
              "Hệ thống chỉ hỗ trợ tải lên hình ảnh bài tập có kích thước tối đa 5MB. Vui lòng chụp lại hoặc chọn ảnh nhẹ hơn nhé!"}
          </p>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-amber-700/70 hover:text-amber-900 hover:bg-amber-100 transition-colors shrink-0 cursor-pointer"
          title="Đóng thông báo"
          aria-label="Đóng thông báo"
        >
          <X size={16} />
        </button>
      </div>
    </div>,
    document.body
  );
}
