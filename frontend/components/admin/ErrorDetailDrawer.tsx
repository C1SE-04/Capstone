"use client";

import React, { useState } from "react";
import {
  X,
  User,
  Clock,
  Terminal,
  Code,
  CheckCircle2,
  Copy,
  Check,
  Laptop,
  Smartphone,
  Globe,
  Monitor,
  Cpu,
  Layers,
  ShieldAlert,
  AlertTriangle,
  Info,
  Calendar,
  Compass,
} from "lucide-react";
import {
  SystemErrorItem,
  SystemErrorSeverity,
  SystemErrorType,
  SystemErrorStatus,
} from "@/types/admin";

interface ErrorDetailDrawerProps {
  error: SystemErrorItem | null;
  isOpen: boolean;
  onClose: () => void;
  onResolve: (errorId: string, note: string) => Promise<void>;
  isResolving?: boolean;
}

// ==============================================================================
// 1. BADGE HELPERS
// ==============================================================================

function SeverityBadge({ severity }: { severity: SystemErrorSeverity }) {
  const normalized = severity?.toUpperCase();

  if (normalized === "CRITICAL") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-red-100 text-red-800 border border-red-300 shadow-xs">
        <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
        CRITICAL (500)
      </span>
    );
  }

  if (normalized === "WARNING") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300 shadow-xs">
        <span className="w-2 h-2 rounded-full bg-amber-500" />
        WARNING (Timeout)
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-blue-100 text-blue-800 border border-blue-300 shadow-xs">
      <span className="w-2 h-2 rounded-full bg-blue-500" />
      INFO (User Report)
    </span>
  );
}

function StatusBadge({ status }: { status: SystemErrorStatus }) {
  const isResolved = status?.toUpperCase() === "RESOLVED";

  if (isResolved) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        Đã xử lý
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
      <Clock className="w-3.5 h-3.5 text-rose-500" />
      Đang mở (OPEN)
    </span>
  );
}

function formatDateTime(isoString?: string | null) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return new Intl.DateTimeFormat("vi-VN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return isoString;
  }
}

// ==============================================================================
// 2. SYNTAX HIGHLIGHTED STACK TRACE (Task T9.22b & AC 9.5.5)
// Tự động phân tích cú pháp Python Traceback: File, Line, Function và Exception
// ==============================================================================

function SyntaxHighlightedStackTrace({ trace }: { trace: string }) {
  const lines = trace.split("\n");

  return (
    <div className="bg-[#18181B] text-zinc-200 p-4 rounded-xl text-xs font-mono overflow-x-auto max-h-80 border border-zinc-800 leading-relaxed selection:bg-red-900/60 space-y-1">
      {lines.map((line, idx) => {
        const lineNum = idx + 1;

        // Dòng header Traceback
        if (line.trim().startsWith("Traceback")) {
          return (
            <div key={idx} className="text-zinc-400 font-bold flex">
              <span className="w-8 shrink-0 text-zinc-600 select-none text-right pr-3">{lineNum}</span>
              <span>{line}</span>
            </div>
          );
        }

        // Dòng File "path", line X, in func
        if (line.trim().startsWith("File ")) {
          const match = line.match(/^\s*File\s+"([^"]+)",\s*line\s+(\d+)(?:,\s*in\s+(.+))?/);
          if (match) {
            const [, filePath, lineNo, funcName] = match;
            return (
              <div key={idx} className="flex">
                <span className="w-8 shrink-0 text-zinc-600 select-none text-right pr-3">{lineNum}</span>
                <span>
                  <span className="text-zinc-500">{"  File "}</span>
                  <span className="text-emerald-400 font-semibold underline underline-offset-2">"{filePath}"</span>
                  <span className="text-zinc-500">, line </span>
                  <span className="text-amber-400 font-bold">{lineNo}</span>
                  {funcName && (
                    <>
                      <span className="text-zinc-500">, in </span>
                      <span className="text-purple-300 font-bold">{funcName}</span>
                    </>
                  )}
                </span>
              </div>
            );
          }
        }

        // Dòng Exception cuối cùng (ví dụ ZeroDivisionError: ..., TimeoutError: ...)
        if (/^[a-zA-Z0-9_.]*(?:Error|Exception|Crash|Timeout|Warning):/i.test(line.trim())) {
          const colonIdx = line.indexOf(":");
          const errName = line.slice(0, colonIdx);
          const errMsg = line.slice(colonIdx + 1);
          return (
            <div
              key={idx}
              className="bg-red-950/60 text-red-200 px-2 py-1 -mx-2 rounded flex border-l-4 border-red-500 mt-2 font-bold"
            >
              <span className="w-8 shrink-0 text-red-500 select-none text-right pr-3">{lineNum}</span>
              <span>
                <span className="text-rose-300 font-black tracking-wide">{errName}:</span>
                <span className="text-red-100">{errMsg}</span>
              </span>
            </div>
          );
        }

        // Các dòng code thông thường
        return (
          <div key={idx} className="flex">
            <span className="w-8 shrink-0 text-zinc-600 select-none text-right pr-3">{lineNum}</span>
            <span className="text-zinc-300">{line}</span>
          </div>
        );
      })}
    </div>
  );
}

// ==============================================================================
// 3. PARSE DEVICE & CLIENT CONTEXT (Task T9.22b: Context thiết bị)
// ==============================================================================

interface ParsedDeviceContext {
  deviceType: string;
  os: string;
  browser: string;
  screenResolution: string;
  ipAddress: string;
  sessionId?: string | null;
  messageId?: string | null;
}

function extractDeviceContext(payloadStr?: string | null): ParsedDeviceContext {
  let context: ParsedDeviceContext = {
    deviceType: "Máy tính (Desktop PC)",
    os: "Windows 11 / Desktop OS",
    browser: "Google Chrome (V8 Engine)",
    screenResolution: "1920 x 1080 (FHD)",
    ipAddress: "127.0.0.1 (Localhost)",
    sessionId: null,
    messageId: null,
  };

  if (!payloadStr) return context;

  try {
    const parsed = typeof payloadStr === "string" ? JSON.parse(payloadStr) : payloadStr;

    if (parsed.session_id) context.sessionId = parsed.session_id;
    if (parsed.message_id) context.messageId = parsed.message_id;

    if (parsed.client_context && typeof parsed.client_context === "object") {
      const c = parsed.client_context;
      if (c.device) context.deviceType = c.device;
      if (c.os) context.os = c.os;
      if (c.browser) context.browser = c.browser;
      if (c.screen) context.screenResolution = c.screen;
      if (c.ip) context.ipAddress = c.ip;
    }
  } catch {
    // Giữ mặc định nếu parse lỗi
  }

  return context;
}

// ==============================================================================
// 4. MAIN COMPONENT: ErrorDetailDrawer (Task T9.22b)
// ==============================================================================

export default function ErrorDetailDrawer({
  error,
  isOpen,
  onClose,
  onResolve,
  isResolving = false,
}: ErrorDetailDrawerProps) {
  const [copiedTrace, setCopiedTrace] = useState<boolean>(false);
  const [copiedPayload, setCopiedPayload] = useState<boolean>(false);
  const [resolveNote, setResolveNote] = useState<string>("");

  if (!isOpen || !error) return null;

  const deviceContext = extractDeviceContext(error.request_payload);

  const handleCopyStackTrace = () => {
    if (!error.stack_trace) return;
    navigator.clipboard.writeText(error.stack_trace);
    setCopiedTrace(true);
    setTimeout(() => setCopiedTrace(false), 2500);
  };

  const handleCopyPayload = () => {
    if (!error.request_payload) return;
    navigator.clipboard.writeText(error.request_payload);
    setCopiedPayload(true);
    setTimeout(() => setCopiedPayload(false), 2500);
  };

  const handleActionResolve = () => {
    onResolve(error.id, resolveNote.trim() || "Đã kiểm tra và xử lý xong");
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop mờ nền */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity animate-in fade-in duration-200"
      />

      {/* Drawer trượt bên phải */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-2xl bg-white shadow-2xl flex flex-col h-full overflow-hidden animate-in slide-in-from-right duration-200 border-l border-[#C1762A]/30">
          {/* ── 1. Drawer Header ── */}
          <div className="p-6 border-b border-[#C1762A]/20 bg-[#F7ECE1]/60 flex items-center justify-between shrink-0">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-base font-extrabold text-[#1C1917]">
                  {error.error_code}
                </span>
                <SeverityBadge severity={error.severity} />
                <StatusBadge status={error.status} />
              </div>
              <p className="text-xs text-[#78716C] flex items-center gap-1.5 mt-0.5">
                <Calendar className="w-3.5 h-3.5 text-[#C1762A]" />
                Thời gian ghi nhận: {formatDateTime(error.created_at)}
              </p>
            </div>

            <button
              onClick={onClose}
              className="p-2 text-[#78716C] hover:text-[#1C1917] hover:bg-white rounded-xl transition-colors cursor-pointer"
              aria-label="Đóng Drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* ── 2. Drawer Content (Cuộn độc lập) ── */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Card 1: Thông tin người dùng (AC 9.5.3) */}
            <div className="bg-[#F7ECE1]/40 rounded-xl p-4 border border-[#C1762A]/20 space-y-2">
              <h3 className="text-xs font-bold text-[#8C4905] uppercase tracking-wider flex items-center gap-1.5">
                <User className="w-4 h-4 text-[#C1762A]" />
                Tài Khoản Gặp Sự Cố
              </h3>
              {error.user_id ? (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-[#78716C]">User ID:</span>{" "}
                    <span className="font-mono font-bold text-[#1C1917]">
                      {error.user_id}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#78716C]">Username:</span>{" "}
                    <span className="font-bold text-[#1C1917]">
                      {error.username || "Chưa thiết lập"}
                    </span>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[#78716C]">Email tài khoản:</span>{" "}
                    <span className="font-semibold text-[#1C1917]">
                      {error.user_email || "Không có email"}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-stone-600 italic">
                  Sự cố xảy ra từ người dùng vãng lai (khách chưa đăng nhập) hoặc tác vụ nền hệ thống.
                </p>
              )}
            </div>

            {/* Card 2: Context Thiết Bị & Trình Duyệt (Task T9.22b) */}
            <div className="bg-stone-50 rounded-xl p-4 border border-stone-200 space-y-2.5">
              <h3 className="text-xs font-bold text-[#78716C] uppercase tracking-wider flex items-center gap-1.5">
                <Laptop className="w-4 h-4 text-[#C1762A]" />
                Context Thiết Bị & Môi Trường Client
              </h3>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <Monitor className="w-3.5 h-3.5 text-stone-500 shrink-0" />
                  <div>
                    <span className="text-stone-500 block text-[10px] uppercase font-bold">Thiết Bị</span>
                    <span className="font-semibold text-[#1C1917]">{deviceContext.deviceType}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Cpu className="w-3.5 h-3.5 text-stone-500 shrink-0" />
                  <div>
                    <span className="text-stone-500 block text-[10px] uppercase font-bold">Hệ Điều Hành</span>
                    <span className="font-semibold text-[#1C1917]">{deviceContext.os}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 text-stone-500 shrink-0" />
                  <div>
                    <span className="text-stone-500 block text-[10px] uppercase font-bold">Trình Duyệt Web</span>
                    <span className="font-semibold text-[#1C1917]">{deviceContext.browser}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Compass className="w-3.5 h-3.5 text-stone-500 shrink-0" />
                  <div>
                    <span className="text-stone-500 block text-[10px] uppercase font-bold">Độ Phân Giải Màn Hình</span>
                    <span className="font-semibold text-[#1C1917]">{deviceContext.screenResolution}</span>
                  </div>
                </div>

                {deviceContext.sessionId && (
                  <div className="col-span-2 pt-1 border-t border-stone-200 flex items-center gap-2">
                    <span className="text-[11px] text-stone-500">Mã phiên (Session ID):</span>
                    <span className="font-mono text-[11px] font-bold text-[#8C4905]">
                      {deviceContext.sessionId}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Card 3: Endpoint & Thông Điệp */}
            <div className="space-y-3">
              <div>
                <h3 className="text-xs font-bold text-[#78716C] uppercase tracking-wider mb-1">
                  API Endpoint Bị Lỗi
                </h3>
                <div className="bg-stone-100 px-3 py-2 rounded-lg font-mono text-xs text-[#1C1917] border border-stone-200">
                  {error.endpoint || "/chat/message"}
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-[#78716C] uppercase tracking-wider mb-1">
                  Nội Dung Sự Cố / Phản Ánh
                </h3>
                <div className="bg-rose-50/70 p-3.5 rounded-xl border border-rose-200 text-xs font-medium text-rose-950 leading-relaxed">
                  {error.message}
                </div>
              </div>
            </div>

            {/* Card 4: Request Payload (Đã Mask Bảo Mật) */}
            {error.request_payload && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold text-[#78716C] uppercase tracking-wider flex items-center gap-1.5">
                    <Code className="w-4 h-4 text-[#C1762A]" />
                    Request Payload (Đã Bảo Mật Mask Token/OTP)
                  </h3>
                  <button
                    onClick={handleCopyPayload}
                    className="text-xs text-[#8C4905] hover:text-[#C1762A] flex items-center gap-1 font-bold cursor-pointer"
                  >
                    {copiedPayload ? (
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                    <span>{copiedPayload ? "Đã sao chép!" : "Sao chép Payload"}</span>
                  </button>
                </div>

                <pre className="bg-[#18181B] text-zinc-200 p-4 rounded-xl text-xs font-mono overflow-x-auto max-h-48 border border-zinc-800">
                  <code>{error.request_payload}</code>
                </pre>
              </div>
            )}

            {/* Card 5: Full Stack Trace có Highlight Cú Pháp (Task T9.22b & AC 9.5.5) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-[#78716C] uppercase tracking-wider flex items-center gap-1.5">
                  <Terminal className="w-4 h-4 text-red-600" />
                  Full Stack Trace Kỹ Thuật (Highlight Cú Pháp Python)
                </h3>
                {error.stack_trace && (
                  <button
                    onClick={handleCopyStackTrace}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-red-100 text-red-800 hover:bg-red-200 rounded-lg text-xs font-bold transition-colors cursor-pointer"
                  >
                    {copiedTrace ? (
                      <Check className="w-3.5 h-3.5 text-emerald-700" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                    <span>{copiedTrace ? "Đã chép Trace!" : "Sao chép Stack Trace"}</span>
                  </button>
                )}
              </div>

              {error.stack_trace ? (
                <SyntaxHighlightedStackTrace trace={error.stack_trace} />
              ) : (
                <div className="bg-stone-50 border border-stone-200 p-4 rounded-xl text-xs text-[#78716C] italic text-center">
                  Không có Stack Trace kỹ thuật (Sự cố được phản ánh trực tiếp từ học sinh trên khung chat).
                </div>
              )}
            </div>

            {/* Card 6: Thao tác xử lý sự cố (AC 9.5.6) */}
            <div className="pt-4 border-t border-[#C1762A]/20 space-y-3">
              <h3 className="text-xs font-bold text-[#8C4905] uppercase tracking-wider">
                Thao Tác Xử Lý Sự Cố
              </h3>

              {error.status === "RESOLVED" ? (
                <div className="bg-emerald-50 border border-emerald-200 p-4 rounded-xl space-y-1.5 text-xs text-emerald-900">
                  <div className="flex items-center gap-2 font-bold text-emerald-800">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Sự cố này đã được giải quyết thành công!</span>
                  </div>
                  <p className="text-[11px] text-emerald-700">
                    Thời gian giải quyết: {formatDateTime(error.resolved_at)}
                  </p>
                  {error.resolved_note && (
                    <p className="text-[11px] text-emerald-800 font-medium mt-1">
                      Ghi chú: {error.resolved_note}
                    </p>
                  )}
                </div>
              ) : (
                <div className="space-y-3 bg-[#F7ECE1]/40 p-4 rounded-xl border border-[#C1762A]/20">
                  <div>
                    <label className="text-xs font-semibold text-[#1C1917] block mb-1">
                      Ghi chú cách giải quyết (tùy chọn):
                    </label>
                    <input
                      type="text"
                      placeholder="Ví dụ: Đã sửa chia cho 0 / Đã điều chỉnh timeout Gemini lên 45s..."
                      value={resolveNote}
                      onChange={(e) => setResolveNote(e.target.value)}
                      className="w-full px-3 py-2 bg-white border border-[#C1762A]/30 rounded-lg text-xs focus:outline-hidden focus:ring-2 focus:ring-[#C1762A]"
                    />
                  </div>

                  <button
                    onClick={handleActionResolve}
                    disabled={isResolving}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition-all shadow-md cursor-pointer disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{isResolving ? "Đang xử lý..." : "Đánh Dấu Đã Xử Lý (RESOLVED)"}</span>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* ── 3. Drawer Footer ── */}
          <div className="p-4 border-t border-[#C1762A]/20 bg-[#F7ECE1]/40 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-white text-[#8C4905] border border-[#C1762A]/30 rounded-xl text-xs font-bold hover:bg-[#F7ECE1] transition-colors cursor-pointer"
            >
              Đóng Drawer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

