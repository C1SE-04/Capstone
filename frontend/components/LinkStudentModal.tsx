"use client";

/**
 * File: components/LinkStudentModal.tsx
 * Mô tả: Modal dành cho Người giám sát (role=MONITOR) để nhập mã liên kết 6 chữ số
 * do Học sinh tạo từ trang Cài đặt. Sau khi liên kết thành công, gọi callback onSuccess.
 *
 * ⚠️ MOCK API TẠM THỜI ⚠️
 * Khi BE hoàn thành endpoint POST /users/me/link-student, hãy thay thế đoạn mock
 * bằng fetch thật (có comment hướng dẫn bên dưới).
 */

import { useState, useRef, useEffect } from "react";
import { X, Link2, CheckCircle2 } from "lucide-react";
import { useSession } from "next-auth/react";

interface LinkStudentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (studentName: string) => void;
}

export default function LinkStudentModal({
  isOpen,
  onClose,
  onSuccess,
}: LinkStudentModalProps) {
  // 6 ô số riêng lẻ để nhập mã
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  const [linkedName, setLinkedName] = useState("");
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const { data: session } = useSession();

  // Reset state mỗi lần modal mở
  useEffect(() => {
    if (isOpen) {
      setDigits(["", "", "", "", "", ""]);
      setErrorMsg("");
      setIsSuccess(false);
      setLinkedName("");
      // Focus vào ô đầu tiên
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const pairingCode = digits.join("");
  const isComplete = pairingCode.length === 6;

  const handleDigitChange = (index: number, value: string) => {
    const cleaned = value.replace(/[^0-9]/g, "").slice(-1);
    const newDigits = [...digits];
    newDigits[index] = cleaned;
    setDigits(newDigits);
    setErrorMsg("");

    // Tự chuyển focus sang ô tiếp theo
    if (cleaned && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/[^0-9]/g, "").slice(0, 6);
    if (pasted) {
      const newDigits = [...digits];
      for (let i = 0; i < 6; i++) {
        newDigits[i] = pasted[i] || "";
      }
      setDigits(newDigits);
      // Focus vào ô cuối cùng có giá trị
      const nextFocus = Math.min(pasted.length, 5);
      inputRefs.current[nextFocus]?.focus();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isComplete) return;

    setIsLoading(true);
    setErrorMsg("");

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/family/link-student`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ pairing_code: pairingCode }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể liên kết. Vui lòng thử lại.");
      }

      const data = await res.json();
      const studentName = data.nickname || data.email?.split("@")?.[0] || "Học sinh";

      /*
      // --- MOCK FALLBACK (chỉ dùng khi chưa có BE) ---
      await new Promise((resolve) => setTimeout(resolve, 800));
      if (parseInt(pairingCode[0]) % 2 !== 0) {
        throw new Error("Mã liên kết không hợp lệ hoặc đã hết hạn.");
      }
      const studentName = "Học sinh Demo";
      */
      setLinkedName(studentName);
      setIsSuccess(true);

      // Tự đóng sau 1.5 giây khi thành công
      setTimeout(() => {
        onSuccess(studentName);
        onClose();
      }, 1500);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Đã xảy ra lỗi hệ thống.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-sm animate-in zoom-in-95 duration-200 border border-[#F1CCA6] relative">
        {/* Nút đóng */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 text-[#C1762A] hover:bg-[#F7ECE1] rounded-full transition-colors cursor-pointer"
          aria-label="Đóng modal"
        >
          <X size={18} />
        </button>

        {isSuccess ? (
          /* Màn hình thành công */
          <div className="flex flex-col items-center text-center py-4 gap-3 animate-in fade-in duration-300">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle2 size={36} className="text-green-500" />
            </div>
            <h3 className="text-xl font-bold text-[#8C4905]">Liên kết thành công!</h3>
            <p className="text-sm text-[#C1762A]">
              Bạn đã kết nối với{" "}
              <span className="font-black text-[#8C4905]">{linkedName}</span>.
            </p>
          </div>
        ) : (
          /* Form nhập mã */
          <>
            {/* Icon + tiêu đề */}
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-[#F7ECE1] rounded-xl flex items-center justify-center">
                <Link2 size={20} className="text-[#C1762A]" />
              </div>
              <h3 className="text-xl font-bold text-[#8C4905]">Thêm học sinh</h3>
            </div>
            <p className="text-sm text-[#C1762A] mb-6 leading-relaxed">
              Nhập mã liên kết 6 chữ số từ trang{" "}
              <span className="font-bold text-[#8C4905]">Cài đặt</span> trên thiết bị của con bạn.
            </p>

            <form onSubmit={handleSubmit}>
              {/* 6 ô nhập số */}
              <label className="block text-sm font-bold text-[#8C4905] mb-3 text-center">
                Mã liên kết
              </label>
              <div className="flex gap-2 justify-center mb-2">
                {digits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(el) => { inputRefs.current[index] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleDigitChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    onPaste={handlePaste}
                    disabled={isLoading}
                    className="w-11 h-14 text-center text-2xl font-black text-[#C1762A] bg-[#F7ECE1] border-2 border-transparent rounded-xl focus:outline-none focus:border-[#C1762A] focus:bg-white transition-all disabled:opacity-60 caret-transparent"
                    aria-label={`Chữ số ${index + 1}`}
                    id={`link-digit-${index}`}
                  />
                ))}
              </div>

              {/* Hint dán nhanh */}
              <p className="text-xs text-center text-[#C1762A]/60 mb-4">
                Bạn có thể dán (Ctrl+V) mã trực tiếp
              </p>

              {/* Thông báo lỗi */}
              {errorMsg && (
                <p className="mb-4 text-sm font-bold text-[#CB6600] text-center animate-in slide-in-from-top-1">
                  {errorMsg}
                </p>
              )}

              {/* Nút hành động */}
              <div className="flex gap-3 mt-2">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isLoading}
                  className="flex-1 py-2.5 rounded-xl border-2 border-[#F1CCA6] text-[#8C4905] font-bold hover:bg-[#F7ECE1] transition-colors disabled:opacity-60 cursor-pointer"
                >
                  Huỷ
                </button>
                <button
                  type="submit"
                  id="link-student-submit"
                  disabled={isLoading || !isComplete}
                  className="flex-1 py-2.5 rounded-xl bg-[#C1762A] text-white font-bold hover:bg-[#8C4905] shadow-md transition-all transform hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0 cursor-pointer flex items-center justify-center gap-2"
                >
                  {isLoading ? (
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    "Xác nhận"
                  )}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
