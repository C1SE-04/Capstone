"use client";

import { useState } from "react";

interface AddStudentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (studentName: string) => void;
}

export default function AddStudentModal({ isOpen, onClose, onSuccess }: AddStudentModalProps) {
  const [pairingCode, setPairingCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pairingCode.length !== 6) {
      setErrorMsg("Mã liên kết phải gồm 6 chữ số.");
      return;
    }

    setIsLoading(true);
    setErrorMsg("");

    try {
      // MOCK API - Gỉa lập gọi API liên kết
      await new Promise(resolve => setTimeout(resolve, 800));
      
      // Giả lập thành công nếu mã bắt đầu bằng số chẵn, thất bại nếu số lẻ
      if (parseInt(pairingCode[0]) % 2 !== 0) {
        throw new Error("Mã liên kết không hợp lệ hoặc đã hết hạn");
      }

      // Khi có API thật, sẽ dùng mã này gọi /api/link-student
      onSuccess("Học sinh Demo");
      setPairingCode("");
      onClose();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Đã xảy ra lỗi");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-sm animate-in zoom-in-95 duration-200 border border-[#F1CCA6]">
        <h3 className="text-xl font-bold text-[#8C4905] mb-2">Thêm học sinh</h3>
        <p className="text-sm text-[#C1762A] mb-6 leading-relaxed">
          Nhập mã liên kết 6 chữ số từ thiết bị của con bạn để bắt đầu theo dõi.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-bold text-[#8C4905] mb-2">
              Mã liên kết
            </label>
            <input
              type="text"
              maxLength={6}
              value={pairingCode}
              onChange={(e) => {
                const val = e.target.value.replace(/[^0-9]/g, ""); // Chỉ cho nhập số
                setPairingCode(val);
                setErrorMsg("");
              }}
              placeholder="Ví dụ: 123456"
              disabled={isLoading}
              className="w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-3xl tracking-[0.3em] font-black text-center text-[#C1762A] placeholder:text-[#F1CCA6] placeholder:tracking-normal placeholder:font-normal placeholder:text-base border border-transparent focus:outline-none focus:ring-2 focus:ring-[#F7AD62] disabled:opacity-60 transition-all"
            />
            {errorMsg && (
              <p className="mt-2 text-sm font-bold text-[#CB6600] animate-in slide-in-from-top-1 text-center">
                {errorMsg}
              </p>
            )}
          </div>

          <div className="flex gap-4 mt-8">
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
              disabled={isLoading || pairingCode.length !== 6}
              className="flex-1 py-2.5 rounded-xl bg-[#C1762A] text-white font-bold hover:bg-[#8C4905] shadow-md transition-all transform hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0 cursor-pointer flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              ) : "Xác nhận"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
