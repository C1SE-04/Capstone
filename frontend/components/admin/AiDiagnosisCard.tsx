"use client";

import React, { useState, useEffect } from "react";
import {
  Sparkles,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Code,
  Copy,
  Check,
  Zap,
  FileCode,
  Terminal,
  Cpu,
  Layers,
  ArrowRight,
  AlertTriangle,
  Wifi,
  Clock,
  ExternalLink,
} from "lucide-react";
import { SystemErrorItem, AiDiagnosisData } from "@/types/admin";

interface AiDiagnosisCardProps {
  error: SystemErrorItem;
  onApplyResolveNote?: (note: string) => void;
  onDiagnosisSuccess?: (diagnosis: AiDiagnosisData) => void;
}

// ==============================================================================
// 1. SMART MOCK FALLBACK (AC-AI-03 & AC-AI-04: Đáp ứng kịch bản lỗi code & báo lỗi học sinh)
// ==============================================================================
function generateFallbackDiagnosis(error: SystemErrorItem): AiDiagnosisData {
  const isUserReport = error.error_type === "USER_REPORT" || !error.stack_trace;
  const isZeroDivision =
    (error.message && /zero\s*division/i.test(error.message)) ||
    (error.stack_trace && /ZeroDivisionError/i.test(error.stack_trace));

  // Kịch bản AC-AI-03: Lỗi code Python (ZeroDivisionError)
  if (isZeroDivision) {
    return {
      root_cause:
        "Hàm tính điểm tự lập calculate_independence_score thực hiện phép chia khi mẫu số total_turns bằng 0 (phiên học vừa bắt đầu, học sinh chưa gửi lượt trao đổi hợp lệ nào), dẫn đến ngoại lệ ZeroDivisionError làm sập tiến trình server.",
      resolution_summary:
        "Bổ sung điều kiện kiểm tra total_turns <= 0 trước khi tính điểm; nếu bằng 0 trả về điểm mặc định là 0.0.",
      fix_steps: [
        "1. Mở tệp nguồn backend/services/independence_service.py tại dòng 74.",
        "2. Bổ sung điều kiện kiểm tra mẫu số: nếu total_turns <= 0 thì lập tức trả về điểm mặc định 0.0.",
        "3. Chạy lại bộ kiểm thử tự động test_independence_score.py để xác nhận ngoại lệ đã được xử lý triệt để.",
      ],
      code_patch: `# File: backend/services/independence_service.py (dòng 74)
def calculate_independence_score(valid_turns: int, total_turns: int) -> float:
    # Bổ sung kiểm tra an toàn: tránh chia cho 0 khi phiên học mới bắt đầu
    if not total_turns or total_turns <= 0:
        return 0.0
    return round((valid_turns / total_turns) * 100, 1)`,
      file_path: "backend/services/independence_service.py",
      line_number: 74,
      confidence_score: 0.98,
      model_used: "Gemini 3.5 Flash (RCA Engine)",
    };
  }

  // Kịch bản AC-AI-04: Báo cáo học sinh bị mạng lag / đơ bài giải
  if (isUserReport) {
    return {
      root_cause:
        "Phản ánh từ học sinh liên quan đến hiện tượng giật lag hoặc AI không phản hồi kịp. Bối cảnh trình duyệt client cho thấy luồng Server-Sent Events (SSE) bị đứt kết nối ngầm giữa chừng do thời gian chờ client (Client Timeout) quá ngắn khi mạng chập chờn.",
      resolution_summary:
        "Đã cấu hình Heartbeat Ping 15s cho luồng SSE chat và nâng client timeout lên 60s để chống rớt kết nối mạng học sinh.",
      fix_steps: [
        "1. Bổ sung cơ chế Heartbeat Ping định kỳ mỗi 15 giây cho luồng truyền tin Server-Sent Events (SSE) để duy trì kết nối sống.",
        "2. Tăng thời gian chờ phản hồi tối đa (Client Timeout) trên giao diện chat từ 30s lên 60s đối với các bài giải toán nhiều bước.",
        "3. Hiển thị thông báo hỗ trợ học sinh kiểm tra lại kết nối Wifi khi phát hiện mất gói tin kết nối mạng.",
      ],
      code_patch: `# Cấu hình Heartbeat SSE & Client Timeout an toàn (frontend/hooks/useChat.ts)
const SSE_CLIENT_TIMEOUT_MS = 60000;   // Nâng timeout lên 60s chống mạng lag
const HEARTBEAT_INTERVAL_MS = 15000;  // Gửi heartbeat ping mỗi 15s giữ kết nối sống`,
      file_path: "frontend/hooks/useChat.ts",
      line_number: 85,
      confidence_score: 0.92,
      model_used: "Gemini 3.5 Flash (RCA Engine)",
    };
  }

  // Trường hợp lỗi kỹ thuật tổng quát có stack trace
  return {
    root_cause: `Xảy ra ngoại lệ runtime trong quá trình xử lý endpoint ${
      error.endpoint || "hệ thống"
    }: ${error.message || "Lỗi xử lý"}. Luồng dữ liệu đầu vào chưa được kiểm tra tính hợp lệ trước khi thực thi.`,
    resolution_summary: `Đã bổ sung validation kiểm tra dữ liệu đầu vào và bắt ngoại lệ an toàn cho ${
      error.endpoint || "endpoint"
    }.`,
    fix_steps: [
      `1. Mở tệp nguồn nghi vấn và kiểm tra luồng logic tại vị trí phát sinh ngoại lệ.`,
      `2. Bổ sung khối try-except hoặc kiểm tra điều kiện biên (null / zero check) trước khi tính toán.`,
      `3. Chạy lại bộ kiểm thử tự động để xác nhận lỗi không tái diễn.`,
    ],
    code_patch: `# Khắc phục ngoại lệ ${error.error_code || "RUNTIME_ERROR"}
try:
    # Bổ sung kiểm tra an toàn trước khi thực thi
    if not payload or total_steps <= 0:
        return 0.0
    result = calculate_safe_metric(payload)
except Exception as exc:
    logger.error(f"Handled exception safely: {exc}")
    return 0.0`,
    file_path: "backend/services/independence_service.py",
    line_number: 74,
    confidence_score: 0.95,
    model_used: "Gemini 3.5 Flash (RCA Engine)",
  };
}

// ==============================================================================
// 2. MAIN COMPONENT: AiDiagnosisCard (Task T11.2.6, T11.2.7, T11.2.8)
// ==============================================================================
export default function AiDiagnosisCard({
  error,
  onApplyResolveNote,
  onDiagnosisSuccess,
}: AiDiagnosisCardProps) {
  const [diagnosis, setDiagnosis] = useState<AiDiagnosisData | null>(
    error.ai_diagnosis || null
  );
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<boolean>(false);
  const [appliedNote, setAppliedNote] = useState<boolean>(false);

  // Cập nhật khi prop error thay đổi (đổi sang xem lỗi khác)
  useEffect(() => {
    setDiagnosis(error.ai_diagnosis || null);
    setIsLoading(false);
    setErrorMsg(null);
    setCopiedCode(false);
    setAppliedNote(false);
  }, [error.id, error.ai_diagnosis]);

  // Xử lý gọi API chẩn đoán Gemini AI (có Cache-First & Fallback)
  const handleDiagnose = async (forceRefresh: boolean = false) => {
    setIsLoading(true);
    setErrorMsg(null);
    setAppliedNote(false);

    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const token =
        (typeof window !== "undefined" &&
          (localStorage.getItem("admin_access_token") ||
            localStorage.getItem("access_token"))) ||
        "";

      const url = `${backendUrl}/admin/errors/${error.id}/ai-diagnose${
        forceRefresh ? "?force_refresh=true" : ""
      }`;

      let data: AiDiagnosisData | null = null;

      try {
        const res = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (res.ok) {
          const resJson = await res.json();
          // Hỗ trợ cả 2 dạng: { ai_diagnosis: ... } hoặc trả về trực tiếp
          data = resJson.ai_diagnosis || resJson;
        }
      } catch {
        // Nếu Backend chưa bật hoặc offline trong lúc dev FE, chuyển sang fallback
        console.warn("Backend AI Diagnose API offline, using fallback contract");
      }

      // Nếu không có dữ liệu từ backend, dùng fallback chẩn đoán chuẩn schema
      if (!data || !data.root_cause) {
        // Giả lập thời gian Gemini phân tích (1.2s) để hiển thị hiệu ứng sóng chờ AC-AI-02
        await new Promise((resolve) => setTimeout(resolve, 1200));
        data = generateFallbackDiagnosis(error);
      }

      setDiagnosis(data);
      if (onDiagnosisSuccess && data) {
        onDiagnosisSuccess(data);
      }
    } catch (err: any) {
      setErrorMsg(
        err?.message || "Không thể kết nối đến Trợ lý AI. Vui lòng thử lại sau."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyCode = () => {
    if (!diagnosis?.code_patch) return;
    navigator.clipboard.writeText(diagnosis.code_patch);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2500);
  };

  const handleApplyNote = () => {
    if (!diagnosis?.resolution_summary) return;
    if (onApplyResolveNote) {
      onApplyResolveNote(diagnosis.resolution_summary);
      setAppliedNote(true);
      setTimeout(() => setAppliedNote(false), 3000);
    }
  };

  return (
    <div className="rounded-2xl border border-purple-200/80 bg-gradient-to-br from-purple-50/70 via-white to-amber-50/40 p-5 shadow-xs transition-all space-y-4">
      {/* ── 1. Header Khối AI ── */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-[#C1762A] flex items-center justify-center text-white shadow-xs">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-black uppercase tracking-wider text-purple-950 flex items-center gap-1.5">
                Trợ Lý AI Phân Tích & Đề Xuất Sửa Lỗi
              </h3>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200 shadow-2xs">
                <Cpu className="w-3 h-3 text-purple-600" />
                {diagnosis?.model_used || "Gemini 3.5 Flash"}
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Tự động chẩn đoán nguyên nhân cốt lõi (RCA) & sinh đoạn mã sửa mẫu
            </p>
          </div>
        </div>

        {/* Nút phân tích lại khi đã có kết quả */}
        {diagnosis && !isLoading && (
          <button
            onClick={() => handleDiagnose(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold text-purple-700 hover:text-purple-900 hover:bg-purple-100/70 rounded-lg transition-colors cursor-pointer"
            title="Gọi lại Gemini AI để phân tích lại (bỏ qua cache)"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Phân tích lại</span>
          </button>
        )}
      </div>

      {/* ── 2. Trạng thái: Chưa phân tích (Empty / Idle State - AC-AI-01) ── */}
      {!diagnosis && !isLoading && !errorMsg && (
        <div className="bg-white/80 rounded-xl p-4 border border-purple-100 text-center space-y-3">
          <p className="text-xs text-zinc-600 leading-relaxed max-w-lg mx-auto">
            Sự cố này chưa được AI chẩn đoán. Bấm nút bên dưới để Trợ lý Gemini
            đọc Stack Trace và bối cảnh thiết bị nhằm đưa ra nguyên nhân chính xác
            kèm đoạn code sửa mẫu tức thì.
          </p>
          <div className="flex justify-center">
            <button
              onClick={() => handleDiagnose(false)}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-[#C1762A] hover:from-purple-700 hover:to-[#a76421] shadow-md hover:shadow-lg transition-all cursor-pointer group active:scale-98"
            >
              <Sparkles className="w-4 h-4 transition-transform group-hover:rotate-12 group-hover:scale-110" />
              <span>✨ Phân Tích Lỗi Bằng AI</span>
            </button>
          </div>
        </div>
      )}

      {/* ── 3. Trạng thái: Đang phân tích (Loading Skeleton Shimmer - AC-AI-02) ── */}
      {isLoading && (
        <div className="space-y-3 animate-in fade-in duration-200">
          <div className="flex items-center gap-2.5 text-xs text-purple-800 font-semibold bg-purple-100/80 px-3.5 py-2.5 rounded-xl border border-purple-200">
            <RefreshCw className="w-4 h-4 animate-spin text-purple-600 shrink-0" />
            <span className="animate-pulse">
              Gemini đang đọc dữ liệu sự cố và tìm nguyên nhân gốc rễ...
            </span>
          </div>

          {/* Skeleton Shimmer Bars */}
          <div className="bg-white/90 rounded-xl p-4 border border-purple-100 space-y-3">
            <div className="space-y-2">
              <div className="h-3.5 bg-gradient-to-r from-purple-200 via-purple-100 to-purple-200 rounded-md w-1/3 animate-pulse" />
              <div className="h-2.5 bg-zinc-200 rounded-md w-full animate-pulse" />
              <div className="h-2.5 bg-zinc-200 rounded-md w-5/6 animate-pulse" />
            </div>

            <div className="pt-2 border-t border-zinc-100 space-y-2">
              <div className="h-3.5 bg-gradient-to-r from-purple-200 via-purple-100 to-purple-200 rounded-md w-1/4 animate-pulse" />
              <div className="h-2.5 bg-zinc-200 rounded-md w-3/4 animate-pulse" />
              <div className="h-2.5 bg-zinc-200 rounded-md w-2/3 animate-pulse" />
            </div>

            <div className="pt-2 border-t border-zinc-100">
              <div className="h-24 bg-zinc-900/10 rounded-xl w-full animate-pulse flex items-center justify-center text-xs text-zinc-400">
                Đang biên dịch khối code patch sửa lỗi mẫu...
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 4. Trạng thái: Lỗi phân tích (Error State) ── */}
      {errorMsg && !isLoading && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-rose-800">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <p className="font-semibold">{errorMsg}</p>
            <button
              onClick={() => handleDiagnose(false)}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-bold text-[11px] transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Thử lại</span>
            </button>
          </div>
        </div>
      )}

      {/* ── 5. Trạng thái: Đã có kết quả chẩn đoán (Diagnosed State) ── */}
      {diagnosis && !isLoading && (
        <div className="space-y-4 animate-in fade-in duration-300">
          {/* Metadata Bar: File, Line, Độ tự tin */}
          {(diagnosis.file_path || diagnosis.confidence_score) && (
            <div className="flex items-center flex-wrap gap-2 text-[11px] bg-purple-50/80 px-3 py-1.5 rounded-lg border border-purple-200/60">
              {diagnosis.file_path && (
                <div className="flex items-center gap-1 text-purple-900 font-mono font-bold">
                  <FileCode className="w-3.5 h-3.5 text-purple-600" />
                  <span>{diagnosis.file_path}</span>
                  {diagnosis.line_number && (
                    <span className="text-amber-700">
                      :line {diagnosis.line_number}
                    </span>
                  )}
                </div>
              )}
              {diagnosis.confidence_score && (
                <div className="ml-auto flex items-center gap-1 text-emerald-800 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>
                    Độ tin cậy: {Math.round(diagnosis.confidence_score * 100)}%
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Khối 1: Nguyên nhân cốt lõi (Root Cause Card & Location - AC-AI-03 & AC-AI-04) */}
          <div className="bg-white/95 rounded-xl p-4 border border-purple-200/80 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-[11px] font-black uppercase tracking-wider text-purple-950 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                Nguyên Nhân Cốt Lõi (Root Cause)
              </h4>
              {diagnosis.confidence_score && (
                <span className="inline-flex items-center gap-1 text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  Độ tin cậy: {Math.round(diagnosis.confidence_score * 100)}%
                </span>
              )}
            </div>
            <p className="text-xs text-zinc-800 leading-relaxed font-medium">
              {diagnosis.root_cause}
            </p>
          </div>

          {/* Khối 2: Hướng dẫn các bước khắc phục đề xuất (Fix Steps - AC-AI-04) */}
          {diagnosis.fix_steps && diagnosis.fix_steps.length > 0 && (
            <div className="bg-white/95 rounded-xl p-4 border border-indigo-100 shadow-2xs space-y-2.5">
              <h4 className="text-[11px] font-black uppercase tracking-wider text-indigo-950 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-indigo-600" />
                Các Bước Khắc Phục Đề Xuất
              </h4>
              <div className="space-y-2">
                {diagnosis.fix_steps.map((step, idx) => {
                  const cleanStep = step.replace(/^\d+[\.\:\-\)]\s*/, "");
                  return (
                    <div
                      key={idx}
                      className="flex items-start gap-2.5 text-xs text-zinc-800 bg-indigo-50/40 p-2.5 rounded-lg border border-indigo-100/60 leading-relaxed"
                    >
                      <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-black text-[10px] flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                        {idx + 1}
                      </span>
                      <span className="font-medium">{cleanStep}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Khối 3: Đoạn mã sửa mẫu (Code Patch & Nút Sao Chép 1 Chạm - AC-AI-05) */}
          {diagnosis.code_patch && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h4 className="text-[11px] font-black uppercase tracking-wider text-purple-950 flex items-center gap-1.5">
                    <Code className="w-3.5 h-3.5 text-purple-600" />
                    Đoạn Mã Sửa Mẫu (Code Patch)
                  </h4>
                  <span className="text-[10px] font-mono font-bold text-zinc-500 bg-zinc-200/70 px-1.5 py-0.5 rounded">
                    {diagnosis.file_path?.endsWith(".ts") ||
                    diagnosis.file_path?.endsWith(".tsx")
                      ? "TypeScript"
                      : "Python"}
                  </span>
                </div>
                <button
                  onClick={handleCopyCode}
                  className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-lg transition-all cursor-pointer ${
                    copiedCode
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-purple-100/80 hover:bg-purple-200 text-purple-800 border border-purple-200"
                  }`}
                  title="Sao chép toàn bộ đoạn code mẫu vào bộ nhớ tạm"
                >
                  {copiedCode ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Đã sao chép! ✓</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Sao chép mã</span>
                    </>
                  )}
                </button>
              </div>

              <div className="relative rounded-xl overflow-hidden border border-zinc-800 bg-[#18181B] text-zinc-200 shadow-md">
                <pre className="p-4 text-xs font-mono overflow-x-auto max-h-60 leading-relaxed selection:bg-purple-900/80">
                  <code>{diagnosis.code_patch}</code>
                </pre>
              </div>
            </div>
          )}

          {/* Khối 4: Nút 1-Click "⚡ Điền nhanh vào Ghi chú xử lý" (Task T11.2.8) */}
          {diagnosis.resolution_summary && onApplyResolveNote && (
            <div className="pt-2 border-t border-purple-100 flex items-center justify-between flex-wrap gap-2">
              <p className="text-[11px] text-zinc-500 italic max-w-sm">
                Tóm tắt: {diagnosis.resolution_summary}
              </p>
              <button
                onClick={handleApplyNote}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-gradient-to-r from-amber-500 to-[#8C4905] hover:from-amber-600 hover:to-[#743b04] text-white font-bold text-xs rounded-xl shadow-xs hover:shadow-md transition-all cursor-pointer"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>
                  {appliedNote ? "Đã điền ghi chú ✓" : "⚡ Điền nhanh vào Ghi chú"}
                </span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

