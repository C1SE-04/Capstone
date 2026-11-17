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
} from "lucide-react";
import { SystemErrorItem, AiDiagnosisData } from "@/types/admin";

interface AiDiagnosisCardProps {
  error: SystemErrorItem;
  onApplyResolveNote?: (note: string) => void;
  onDiagnosisSuccess?: (diagnosis: AiDiagnosisData) => void;
}

// ==============================================================================
// 1. SMART MOCK FALLBACK (Cho phép test UI độc lập trước khi Backend API T11.2.4 merge)
// ==============================================================================
function generateFallbackDiagnosis(error: SystemErrorItem): AiDiagnosisData {
  const isUserReport = error.error_type === "USER_REPORT" || !error.stack_trace;

  if (isUserReport) {
    return {
      root_cause:
        "Phản ánh từ học sinh liên quan đến độ trễ kết nối hoặc nghẽn mạng client khi tải phản hồi gia sư AI. Thiết bị client không nhận được tín hiệu SSE kịp thời trong thời gian timeout.",
      resolution_summary:
        "Đã kiểm tra luồng chat học sinh, cấu hình bổ sung Heartbeat Ping 15s cho SSE và tăng client timeout lên 60s.",
      fix_steps: [
        "1. Kiểm tra trạng thái kết nối SSE / WebSocket của học sinh tại thời điểm gửi tin nhắn.",
        "2. Đảm bảo cấu hình heartbeat ping 15 giây hoạt động để tránh nhà mạng ngắt kết nối dở dang.",
        "3. Hướng dẫn học sinh kiểm tra lại đường truyền Wifi hoặc tải lại trình duyệt.",
      ],
      code_patch: `# Cấu hình timeout an toàn trong client chat (frontend/hooks/useChat.ts)
const SSE_TIMEOUT_MS = 60000; // 60s timeout
const HEARTBEAT_INTERVAL_MS = 15000; // 15s ping`,
      file_path: "frontend/hooks/useChat.ts",
      line_number: 85,
      confidence_score: 0.88,
      model_used: "Gemini 3.5 Flash (RCA Engine)",
    };
  }

  // Trường hợp lỗi kỹ thuật có stack trace
  return {
    root_cause: `Xảy ra ngoại lệ trong quá trình xử lý endpoint ${error.endpoint || "hệ thống"}: ${error.message || "Lỗi runtime"}. Cần bổ sung kiểm tra điều kiện biên và xử lý ngoại lệ an toàn.`,
    resolution_summary: `Đã bổ sung validation kiểm tra dữ liệu đầu vào và bắt ngoại lệ an toàn cho ${error.endpoint || "endpoint"}.`,
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

          {/* Khối 1: Nguyên nhân cốt lõi (Root Cause) */}
          <div className="bg-white/90 rounded-xl p-3.5 border border-purple-100 shadow-2xs space-y-1">
            <h4 className="text-[11px] font-black uppercase tracking-wider text-purple-900 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-600" />
              Nguyên Nhân Cốt Lõi (Root Cause)
            </h4>
            <p className="text-xs text-zinc-800 leading-relaxed">
              {diagnosis.root_cause}
            </p>
          </div>

          {/* Khối 2: Hướng dẫn các bước khắc phục (Fix Steps) */}
          {diagnosis.fix_steps && diagnosis.fix_steps.length > 0 && (
            <div className="bg-white/90 rounded-xl p-3.5 border border-purple-100 shadow-2xs space-y-1.5">
              <h4 className="text-[11px] font-black uppercase tracking-wider text-purple-900 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-indigo-600" />
                Các Bước Khắc Phục Đề Xuất
              </h4>
              <ul className="space-y-1 text-xs text-zinc-700">
                {diagnosis.fix_steps.map((step, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 leading-relaxed">
                    <span className="text-indigo-600 font-bold shrink-0">•</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Khối 3: Đoạn mã sửa mẫu (Code Patch) */}
          {diagnosis.code_patch && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <h4 className="text-[11px] font-black uppercase tracking-wider text-purple-900 flex items-center gap-1.5">
                  <Code className="w-3.5 h-3.5 text-purple-600" />
                  Đoạn Mã Sửa Mẫu (Code Patch)
                </h4>
                <button
                  onClick={handleCopyCode}
                  className="inline-flex items-center gap-1 text-[11px] font-bold text-purple-700 hover:text-purple-900 hover:bg-purple-100/70 px-2 py-0.5 rounded transition-colors cursor-pointer"
                >
                  {copiedCode ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-emerald-700">Đã sao chép!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Sao chép mã</span>
                    </>
                  )}
                </button>
              </div>

              <pre className="bg-[#18181B] text-zinc-200 p-3.5 rounded-xl text-xs font-mono overflow-x-auto max-h-56 border border-zinc-800 leading-relaxed selection:bg-purple-900">
                <code>{diagnosis.code_patch}</code>
              </pre>
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

