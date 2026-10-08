"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";

const GRADES = [4, 5, 6, 7, 8, 9];
const PAIRING_CODE_TTL_SECONDS = 15 * 60; // 15 phút

export default function SettingsPage() {
  const { data: session, update } = useSession();

  // Lấy lớp hiện tại từ session — parse sang number vì NextAuth có thể trả về string
  const rawGrade = session?.user?.grade_level ?? null;
  const currentGrade: number | null = rawGrade !== null ? Number(rawGrade) : null;

  const [selectedGrade, setSelectedGrade] = useState<number | null>(currentGrade);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [pendingGrade, setPendingGrade] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Pairing Code states
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [isGeneratingCode, setIsGeneratingCode] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState(false);
  // Countdown 15 phút (tính bằng giây)
  const [countdown, setCountdown] = useState<number>(0);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Khởi động countdown khi có mã mới
  const startCountdown = () => {
    if (countdownRef.current) clearInterval(countdownRef.current);
    setCountdown(PAIRING_CODE_TTL_SECONDS);
    countdownRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(countdownRef.current!);
          // Mã hết hạn → reset về trạng thái chưa có mã
          setPairingCode(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // Dọn dẹp interval khi unmount
  useEffect(() => {
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []);

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
      // Gọi API thật lên Backend để lưu lớp học mới vào NeonDB
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

      // Sau khi DB cập nhật thành công, đồng bộ lại session NextAuth
      await update({ grade_level: pendingGrade });

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

  const generatePairingCode = async () => {
    setIsGeneratingCode(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/family/pairing-code`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session?.access_token}`,
        },
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Không thể tạo mã");
      }

      const data = await res.json();
      setPairingCode(data.pairing_code);
      startCountdown();
    } catch (error) {
      console.error(error);
    } finally {
      setIsGeneratingCode(false);
    }
  };

  const handleCopyCode = async () => {
    if (!pairingCode) return;
    await navigator.clipboard.writeText(pairingCode);
    setCopyFeedback(true);
    setTimeout(() => setCopyFeedback(false), 2000);
  };

  // Format countdown thành mm:ss
  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  // Tính % tiến trình (countdown càng giảm, bar càng cạn)
  const countdownPercent = (countdown / PAIRING_CODE_TTL_SECONDS) * 100;

  // Màu bar: xanh → vàng → đỏ
  const barColor =
    countdownPercent > 50
      ? "#22c55e"   // xanh lá
      : countdownPercent > 20
      ? "#f59e0b"   // vàng
      : "#ef4444";  // đỏ

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

      {/* Liên kết với Phụ huynh */}
      <div className="bg-white rounded-2xl shadow-sm border border-[#F1CCA6] p-6 mt-6 mb-6">
        <h2 className="text-lg font-bold text-[#8C4905] mb-1 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Liên kết với Phụ huynh
        </h2>
        <p className="text-sm text-[#C1762A] mb-4 leading-relaxed">
          Tạo mã liên kết để bố mẹ có thể xem tiến độ học tập của bạn trên bảng điều khiển phụ huynh.
        </p>

        {pairingCode ? (
          /* --- Đã có mã: hiển thị mã + countdown --- */
          <div className="bg-[#F7ECE1] p-4 rounded-xl border border-[#F1CCA6] space-y-4 animate-in fade-in duration-300">
            {/* Mã và nút copy */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[#8C4905] font-bold uppercase tracking-wider mb-1">Mã của bạn</p>
                <p className="text-3xl font-black text-[#C1762A] tracking-[0.2em]">{pairingCode}</p>
              </div>
              <button
                onClick={handleCopyCode}
                className="px-4 py-2 bg-white text-[#8C4905] font-bold rounded-lg border border-[#F1CCA6] hover:bg-gray-50 transition-all shadow-sm cursor-pointer flex items-center gap-1.5 min-w-[80px] justify-center"
              >
                {copyFeedback ? (
                  <span className="text-green-600 animate-in fade-in duration-200">✓ Đã copy</span>
                ) : (
                  "Copy"
                )}
              </button>
            </div>

            {/* Countdown bar */}
            <div className="space-y-1.5">
              <div className="relative w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="absolute left-0 top-0 h-full rounded-full transition-all duration-1000 ease-linear"
                  style={{
                    width: `${countdownPercent}%`,
                    backgroundColor: barColor,
                  }}
                />
              </div>
              <p className="text-xs text-[#8C4905]/70 text-center">
                Mã liên kết sẽ hết hạn sau{" "}
                <span
                  className="font-black"
                  style={{ color: barColor }}
                >
                  {formatCountdown(countdown)}
                </span>
              </p>
            </div>

            {/* Nút tạo lại */}
            <button
              onClick={generatePairingCode}
              disabled={isGeneratingCode}
              className="w-full py-2 rounded-xl border-2 border-[#C1762A] text-[#C1762A] font-bold text-sm hover:bg-[#F1CCA6] transition-colors disabled:opacity-60 cursor-pointer"
            >
              {isGeneratingCode ? "Đang tạo mã mới..." : "Tạo mã mới"}
            </button>
          </div>
        ) : (
          /* --- Chưa có mã: hiện nút lấy mã --- */
          <button
            id="get-pairing-code-btn"
            onClick={generatePairingCode}
            disabled={isGeneratingCode}
            className="w-full py-3 rounded-xl bg-[#C1762A] text-white font-bold hover:bg-[#8C4905] shadow-md transition-all transform hover:-translate-y-0.5 disabled:opacity-60 disabled:hover:translate-y-0 cursor-pointer flex items-center justify-center gap-2"
          >
            {isGeneratingCode ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Đang tạo mã...
              </>
            ) : "Lấy mã liên kết"}
          </button>
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
