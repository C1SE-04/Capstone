"use client";

import { useState, useEffect } from "react";
import {
  RefreshCw,
  CheckCircle2,
  X,
  AlertCircle,
  Clock,
  BookOpen,
  ArrowRight,
  Database,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SyncVietjackResult } from "@/types/admin";

interface SyncVietjackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSync: () => Promise<SyncVietjackResult | null>;
  onSuccessDone?: () => void;
}

export function SyncVietjackModal({
  isOpen,
  onClose,
  onSync,
  onSuccessDone,
}: SyncVietjackModalProps) {
  const [phase, setPhase] = useState<"idle" | "crawling" | "success" | "error">("idle");
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [activeGradeIndex, setActiveGradeIndex] = useState<number>(0);
  const [result, setResult] = useState<SyncVietjackResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const GRADES = [4, 5, 6, 7, 8, 9];

  // Bắt đầu cào tự động khi mở modal
  useEffect(() => {
    if (!isOpen) {
      setPhase("idle");
      setProgressPercent(0);
      setActiveGradeIndex(0);
      setResult(null);
      setErrorMessage(null);
      return;
    }

    let isMounted = true;
    let timerId: NodeJS.Timeout | null = null;

    const startProcess = async () => {
      setPhase("crawling");
      setProgressPercent(15);
      setActiveGradeIndex(0);

      // Mô phỏng tiến trình 2-4 giây theo đúng tiêu chí Sprint 8 [AC 8.4.1]
      const stepInterval = 450; // Mỗi 450ms hoàn tất 1 lớp
      let currentStep = 0;

      const progressInterval = setInterval(() => {
        currentStep++;
        if (!isMounted) return;

        if (currentStep <= GRADES.length) {
          setActiveGradeIndex(currentStep);
          setProgressPercent(Math.min(92, Math.round((currentStep / GRADES.length) * 88)));
        }
      }, stepInterval);

      try {
        const syncRes = await onSync();
        clearInterval(progressInterval);

        if (!isMounted) return;

        if (syncRes && syncRes.success) {
          setProgressPercent(100);
          setActiveGradeIndex(GRADES.length);
          setResult(syncRes);
          setPhase("success");
          onSuccessDone?.();
        } else {
          setPhase("error");
          setErrorMessage(syncRes?.message || "Quá trình đồng bộ từ VietJack không thành công.");
        }
      } catch (err: unknown) {
        clearInterval(progressInterval);
        if (isMounted) {
          setPhase("error");
          setErrorMessage(err instanceof Error ? err.message : "Lỗi kết nối máy chủ khi cào dữ liệu.");
        }
      }
    };

    timerId = setTimeout(startProcess, 200);

    return () => {
      isMounted = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [isOpen, onSync, onSuccessDone]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity duration-150 animate-in fade-in"
        onClick={phase === "crawling" ? undefined : onClose}
      />

      {/* Modal Dialog */}
      <div className="relative z-10 bg-white rounded-xl p-6 sm:p-7 max-w-lg w-full shadow-2xl border border-stone-200 animate-in fade-in zoom-in-95 duration-150 text-left">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-stone-100">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-amber-50 text-[#C1762A] border border-amber-200/70 flex items-center justify-center shrink-0">
              <RefreshCw size={18} className={cn(phase === "crawling" && "animate-spin")} />
            </div>
            <div>
              <h3 className="text-base font-bold text-stone-900">
                Đồng Bộ Mục Lục Toán VietJack
              </h3>
              <p className="text-xs text-stone-500">
                Tự động bóc tách chuẩn SGK Kết Nối Tri Thức cho lớp 4 - 9
              </p>
            </div>
          </div>

          {phase !== "crawling" && (
            <button
              type="button"
              onClick={onClose}
              className="w-7 h-7 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-400 hover:text-stone-700 transition-colors cursor-pointer"
              aria-label="Đóng"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Thân Modal */}
        <div className="py-5 space-y-4">
          {/* Thanh tiến trình Progress Bar */}
          <div>
            <div className="flex items-center justify-between text-xs font-semibold mb-1.5">
              <span className="text-stone-700 flex items-center gap-1.5">
                {phase === "crawling" ? (
                  <>
                    <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                    Đang cào dữ liệu từ VietJack...
                  </>
                ) : phase === "success" ? (
                  <span className="text-emerald-700 font-bold flex items-center gap-1">
                    <CheckCircle2 size={14} className="text-emerald-600" />
                    Đã hoàn tất đồng bộ 100%
                  </span>
                ) : (
                  <span className="text-red-600 flex items-center gap-1">
                    <AlertCircle size={14} />
                    Gặp sự cố
                  </span>
                )}
              </span>
              <span className="text-[#C1762A] font-bold">{progressPercent}%</span>
            </div>

            <div className="w-full h-2.5 bg-stone-100 rounded-full overflow-hidden border border-stone-200">
              <div
                className={cn(
                  "h-full transition-all duration-300 ease-out",
                  phase === "error"
                    ? "bg-red-500"
                    : "bg-gradient-to-r from-amber-500 to-[#C1762A]"
                )}
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>

          {/* Danh sách các khối lớp đang cào */}
          <div className="bg-stone-50/80 rounded-xl p-3 border border-stone-200/80 space-y-2">
            <p className="text-[11px] font-bold text-stone-500 uppercase tracking-wider px-1">
              Tiến trình bóc tách từng khối lớp:
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {GRADES.map((g, idx) => {
                const isFinished = activeGradeIndex > idx;
                const isCurrent = activeGradeIndex === idx && phase === "crawling";

                return (
                  <div
                    key={`grade-step-${g}`}
                    className={cn(
                      "flex items-center justify-between px-2.5 py-1.5 rounded-lg border text-xs transition-all",
                      isFinished
                        ? "bg-white border-emerald-200 text-emerald-800 shadow-2xs"
                        : isCurrent
                        ? "bg-amber-50 border-amber-300 text-amber-900 font-bold shadow-2xs"
                        : "bg-white/60 border-stone-200/60 text-stone-400"
                    )}
                  >
                    <span className="font-semibold">Toán Lớp {g}</span>
                    {isFinished ? (
                      <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
                    ) : isCurrent ? (
                      <RefreshCw size={12} className="animate-spin text-[#C1762A] shrink-0" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-stone-200 shrink-0" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Khối kết quả khi cào thành công */}
          {phase === "success" && result && (
            <div className="p-4 rounded-xl bg-emerald-50/90 border border-emerald-200 animate-in fade-in duration-200 space-y-2">
              <div className="flex items-center gap-2 text-emerald-900 font-bold text-sm">
                <CheckCircle2 size={17} className="text-emerald-600" />
                <span>Đồng bộ thành công dữ liệu SGK mới!</span>
              </div>
              <p className="text-xs text-emerald-800 leading-relaxed font-medium">
                {result.message}
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-1 text-xs text-emerald-700">
                <span className="flex items-center gap-1 font-semibold">
                  <Database size={13} />
                  {result.current_total_in_db || result.total_synced} chuyên đề trong DB
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={13} />
                  {result.elapsed_seconds} giây
                </span>
                <span className="flex items-center gap-1">
                  <BookOpen size={13} />
                  Đủ 6 khối lớp (4 - 9)
                </span>
              </div>
            </div>
          )}

          {/* Khối lỗi nếu có */}
          {phase === "error" && errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <AlertCircle size={14} className="text-red-600" />
                Chưa thể hoàn tất đồng bộ
              </p>
              <p className="text-[11px] text-red-600 leading-relaxed">
                {errorMessage}
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-stone-100">
          {phase === "crawling" ? (
            <p className="text-xs text-stone-400 italic">
              Vui lòng giữ nguyên cửa sổ trong vài giây...
            </p>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-lg transition-colors cursor-pointer"
              >
                Đóng
              </button>
              {phase === "success" && (
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 bg-[#C1762A] hover:bg-[#8C4905] text-white text-xs font-bold rounded-lg transition-all shadow-xs flex items-center gap-1.5 cursor-pointer"
                >
                  <span>Xem bảng chuyên đề</span>
                  <ArrowRight size={13} />
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default SyncVietjackModal;
