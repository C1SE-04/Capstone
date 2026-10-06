"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";

const GRADES = [4, 5, 6, 7, 8, 9];

export default function SettingsPage() {
  const { data: session, update } = useSession();

  // Lấy lớp hiện tại từ session (nếu T5.7 chưa xong, ép kiểu để tạm không báo lỗi TS)
  // Mặc định tạm thời là null nếu session chưa trả về grade
  const currentGrade = (session?.user as any)?.grade ?? null;

  const [selectedGrade, setSelectedGrade] = useState<number | null>(currentGrade);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingGrade, setPendingGrade] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleGradeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newGrade = Number(e.target.value);
    if (newGrade === currentGrade) return;
    setPendingGrade(newGrade);
    setShowConfirmDialog(true);
  };

  const handleConfirm = async () => {
    if (!pendingGrade) return;
    setIsLoading(true);
    setErrorMsg("");

    try {
      // ⚠️ MOCK API TẠM THỜI ⚠️
      // Vì T5.3 (BE) chưa làm xong nên mình giả lập API delay 800ms
      // Sau khi T5.3 có API thật, sẽ uncomment đoạn code fetch bên dưới
      await new Promise(resolve => setTimeout(resolve, 800));

      /*
      // --- KHI CÓ API THẬT CỦA T5.3, HÃY DÙNG ĐOẠN NÀY ---
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/users/me/grade`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ grade: pendingGrade }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể cập nhật lớp học");
      }
      */

      // Cập nhật session (Yêu cầu T5.7 hoàn thành để hoạt động mượt)
      await update({ grade: pendingGrade });
      
      // Cập nhật UI
      setSelectedGrade(pendingGrade);
      setSuccessMsg(` Đã đổi sang Lớp ${pendingGrade} thành công!`);
      setTimeout(() => setSuccessMsg(""), 3000);
      
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Đã xảy ra lỗi hệ thống");
      setSelectedGrade(currentGrade);
    } finally {
      setIsLoading(false);
      setShowConfirmDialog(false);
      setPendingGrade(null);
    }
  };

  const handleCancel = () => {
    setSelectedGrade(currentGrade);
    setPendingGrade(null);
    setShowConfirmDialog(false);
  };

  return (
    <div className="max-w-2xl mx-auto animate-in fade-in duration-500 pb-10">
      <h1 className="text-3xl font-extrabold text-[#8C4905] mb-8 tracking-tight">
        Cài đặt cá nhân
      </h1>

      {/* Thông tin tài khoản */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6 mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-4 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Thông tin tài khoản
        </h2>
        <div className="space-y-3 text-sm text-[#8C4905]">
          <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]">
            <span className="font-medium text-[#C1762A]">Email</span>
            <span className="font-bold">{session?.user?.email || "—"}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#F1CCA6]">
            <span className="font-medium text-[#C1762A]">Vai trò</span>
            <span className="font-bold uppercase">{session?.user?.role || "—"}</span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="font-medium text-[#C1762A]">Lớp hiện tại</span>
            <span className="font-bold text-[#8C4905]">
              {currentGrade ? `Lớp ${currentGrade}` : "Chưa cập nhật (đợi Session T5.7)"}
            </span>
          </div>
        </div>
      </div>

      {/* Đổi lớp học */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-1 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Đổi lớp học 
        </h2>
        <p className="text-sm text-[#C1762A] mb-4 leading-relaxed">
          Socratic AI sẽ tự động điều chỉnh độ khó, xưng hô và kiến thức theo đúng trình độ lớp mới ngay sau khi bạn lưu.
        </p>

        <label className="block text-sm font-bold text-[#8C4905] mb-2">
          Chọn khối lớp
        </label>
        <select
          value={selectedGrade ?? ""}
          onChange={handleGradeChange}
          disabled={isLoading}
          className="w-full px-4 py-3 rounded-xl bg-[#F7ECE1] text-[#000000] border border-transparent focus:outline-none focus:ring-2 focus:ring-[#F7AD62] cursor-pointer disabled:opacity-60 transition-shadow"
        >
          <option value="" disabled>-- Chọn khối lớp --</option>
          {GRADES.map((g) => (
            <option key={g} value={g}>Lớp {g}</option>
          ))}
        </select>

        {successMsg && (
          <p className="mt-3 text-sm font-bold text-green-600 animate-in slide-in-from-top-1">{successMsg}</p>
        )}
        {errorMsg && (
          <p className="mt-3 text-sm font-bold text-[#CB6600] animate-in slide-in-from-top-1">{errorMsg}</p>
        )}
      </div>

      {/* Confirmation Modal */}
      {showConfirmDialog && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-sm animate-in zoom-in-95 duration-200 border border-[#F1CCA6]">
            <h3 className="text-xl font-bold text-[#8C4905] mb-3">Xác nhận đổi lớp</h3>
            <p className="text-[#C1762A] mb-8 leading-relaxed">
              Bạn đang chuyển sang <span className="font-black text-[#8C4905]">Lớp {pendingGrade}</span>. Hành trình học tập và tư duy của AI sẽ được đồng bộ hoá ngay lập tức.
            </p>
            <div className="flex gap-4">
              <button
                onClick={handleCancel}
                disabled={isLoading}
                className="flex-1 py-2.5 rounded-xl border-2 border-[#F1CCA6] text-[#8C4905] font-bold hover:bg-[#F7ECE1] transition-colors disabled:opacity-60 cursor-pointer"
              >
                Huỷ
              </button>
              <button
                onClick={handleConfirm}
                disabled={isLoading}
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
          </div>
        </div>
      )}
    </div>
  );
}
