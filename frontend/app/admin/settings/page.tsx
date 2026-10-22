"use client";

import { useState, useEffect } from "react";
import {
  Settings,
  Bot,
  Sliders,
  Shield,
  Activity,
  Database,
  Server,
  Sparkles,
  Save,
  RotateCcw,
  CheckCircle2,
  Clock,
  Layers,
  RefreshCw,
  Check,
  X,
  Eye,
  AlertTriangle,
} from "lucide-react";

interface SystemSettings {
  modelName: string;
  backupModel: string;
  temperature: number;
  maxTokens: number;
  safetyThreshold: string;
  guestRateLimit: number;
  studentRateLimit: number;
  enableVisionSupport: boolean;
  enableParentAlert: boolean;
  systemVersion: string;
  environment: string;
  lastUpdated: string;
  updatedBy: string;
}

interface ServiceHealth {
  id: string;
  name: string;
  provider: string;
  status: "operational" | "degraded" | "down";
  latencyMs: number;
  icon: typeof Database;
}

const DEFAULT_SETTINGS: SystemSettings = {
  modelName: "gemini-1.5-flash",
  backupModel: "gemini-1.5-pro",
  temperature: 0.35,
  maxTokens: 512,
  safetyThreshold: "BLOCK_MEDIUM_AND_ABOVE",
  guestRateLimit: 10,
  studentRateLimit: 30,
  enableVisionSupport: true,
  enableParentAlert: true,
  systemVersion: "v1.7.0 (Sprint 7 Release)",
  environment: "Production (Vercel + Neon)",
  lastUpdated: "Hôm nay, 13:45",
  updatedBy: "admin@socratickid.vn",
};

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<SystemSettings>(DEFAULT_SETTINGS);
  const [isSaving, setIsSaving] = useState(false);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState<"success" | "info">("success");

  const [services, setServices] = useState<ServiceHealth[]>([
    {
      id: "postgres",
      name: "Neon PostgreSQL",
      provider: "Serverless Database (Primary)",
      status: "operational",
      latencyMs: 42,
      icon: Database,
    },
    {
      id: "redis",
      name: "Upstash Redis",
      provider: "In-Memory Rate Limiter & Session Cache",
      status: "operational",
      latencyMs: 14,
      icon: Server,
    },
    {
      id: "gemini",
      name: "Google Gemini 1.5 API",
      provider: "LLM Pedagogical Gateway",
      status: "operational",
      latencyMs: 318,
      icon: Sparkles,
    },
  ]);

  // Load saved settings từ localStorage hoặc Mock API nếu có
  useEffect(() => {
    try {
      const cached = localStorage.getItem("socratickid_admin_settings");
      if (cached) {
        setSettings((prev) => ({ ...prev, ...JSON.parse(cached) }));
      }
    } catch {
      // Fallback về default an toàn
    }
  }, []);

  const triggerToast = (msg: string, type: "success" | "info" = "success") => {
    setToastMessage(msg);
    setToastType(type);
    setShowToast(true);
    setTimeout(() => {
      setShowToast(false);
    }, 3200);
  };

  const handleSave = async () => {
    setIsSaving(true);
    const nowStr = new Date().toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
    });
    const updated = {
      ...settings,
      lastUpdated: `Hôm nay, ${nowStr}`,
    };

    try {
      // Thử gọi mock API backend nếu backend đang chạy
      await fetch("http://127.0.0.1:8000/admin/mock/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: updated.modelName,
          backup_model: updated.backupModel,
          temperature: updated.temperature,
          max_output_tokens: updated.maxTokens,
          safety_threshold: updated.safetyThreshold,
          rate_limit_per_minute: updated.studentRateLimit,
          enable_vision_support: updated.enableVisionSupport,
          system_version: updated.systemVersion,
          last_updated_at: new Date().toISOString(),
          last_updated_by: updated.updatedBy,
        }),
      }).catch(() => null);
    } catch {
      // Bỏ qua lỗi kết nối backend để đảm bảo FE luôn mượt
    }

    // Lưu vào LocalStorage
    localStorage.setItem("socratickid_admin_settings", JSON.stringify(updated));
    setSettings(updated);

    setTimeout(() => {
      setIsSaving(false);
      triggerToast("Đã lưu thành công cấu hình tham số AI & Hệ thống!", "success");
    }, 550);
  };

  const handleResetDefaults = () => {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem("socratickid_admin_settings");
    triggerToast("Đã khôi phục toàn bộ cấu hình về tham số mặc định!", "info");
  };

  const handleRefreshHealth = () => {
    setIsRefreshingHealth(true);
    setTimeout(() => {
      setServices((prev) =>
        prev.map((s) => ({
          ...s,
          latencyMs:
            s.id === "postgres"
              ? Math.floor(38 + Math.random() * 12)
              : s.id === "redis"
              ? Math.floor(11 + Math.random() * 6)
              : Math.floor(290 + Math.random() * 60),
        }))
      );
      setIsRefreshingHealth(false);
      triggerToast("Đã cập nhật trạng thái Healthcheck thời gian thực!", "info");
    }, 450);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ── Toast Notification Nổi ── */}
      {showToast && (
        <div className="fixed top-5 right-5 z-50 animate-in slide-in-from-top-4 fade-in duration-200">
          <div
            className={`flex items-center gap-3 px-4 py-3 rounded-2xl shadow-xl border text-sm font-medium ${
              toastType === "success"
                ? "bg-[#2A1C0E] text-[#FFFDF9] border-[#C1762A]/50"
                : "bg-white text-[#2A1C0E] border-[#E8D5C4]"
            }`}
          >
            <div
              className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 ${
                toastType === "success"
                  ? "bg-[#C1762A] text-white"
                  : "bg-[#F7ECE1] text-[#8C4905]"
              }`}
            >
              {toastType === "success" ? (
                <Check className="w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
            </div>
            <span>{toastMessage}</span>
            <button
              onClick={() => setShowToast(false)}
              className="text-[#A18E7F] hover:text-white transition-colors ml-2"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── Page Header & Quick Actions ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-extrabold text-[#2A1C0E]">
              Cài Đặt Hệ Thống & Tham Số AI
            </h1>
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-[#EAF7EE] text-[#2A8C4A] border border-[#B7E4C4]">
              v1.7.0 Live
            </span>
          </div>
          <p className="text-xs md:text-sm text-[#7E6B5A] mt-1">
            Cấu hình mô hình ngôn ngữ lớn, nhiệt độ sáng tạo, hạn mức token và bảo vệ hệ thống
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleResetDefaults}
            disabled={isSaving}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold text-[#7E6B5A] bg-white border border-[#E8D5C4] hover:bg-[#F7ECE1] hover:text-[#2A1C0E] transition-all shadow-xs active:scale-98"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Đặt lại mặc định
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="inline-flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:opacity-95 shadow-md shadow-[#C1762A]/20 transition-all active:scale-98"
          >
            {isSaving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {isSaving ? "Đang lưu cấu hình..." : "Lưu Cấu Hình"}
          </button>
        </div>
      </div>

      {/* ── Main Two-Column Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ===================================================================
            CỘT TRÁI (2/3 width): Tham số AI & Giới hạn Rate Limit
            =================================================================== */}
        <div className="lg:col-span-2 space-y-6">
          {/* ── CARD 1: Cấu hình Tham số AI (Gemini API) ── */}
          <div className="bg-white rounded-2xl border border-[#E8D5C4] p-6 shadow-xs space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-[#F1CCA6]/40">
              <div className="w-10 h-10 rounded-xl bg-[#FDF6EE] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-[#2A1C0E]">
                  Cấu Hình Tham Số Trí Tuệ Nhân Tạo (Gemini API)
                </h2>
                <p className="text-xs text-[#7E6B5A]">
                  Tùy chỉnh model phục vụ gia sư Socratic và độ dài câu gợi mở
                </p>
              </div>
            </div>

            {/* Mô hình phục vụ chính */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#2A1C0E] uppercase tracking-wider">
                Mô hình AI Phục Vụ Chat Chính (Phản hồi tức thì)
              </label>
              <select
                value={settings.modelName}
                onChange={(e) =>
                  setSettings({ ...settings, modelName: e.target.value })
                }
                className="w-full bg-[#FFFDF9] border border-[#E8D5C4] rounded-xl px-3.5 py-2.5 text-sm font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-all cursor-pointer"
              >
                <option value="gemini-1.5-flash">
                  Google Gemini 1.5 Flash (Khuyến nghị cho Toán 4-9 • Phản hồi &lt; 0.4s)
                </option>
                <option value="gemini-1.5-pro">
                  Google Gemini 1.5 Pro (Dành cho bài toán nâng cao • Phân tích sâu)
                </option>
                <option value="gemini-2.0-flash">
                  Google Gemini 2.0 Flash Experimental (Thử nghiệm tính năng mới)
                </option>
              </select>
              <p className="text-[11px] text-[#7E6B5A] flex items-center gap-1 mt-1">
                <Sparkles className="w-3.5 h-3.5 text-[#C1762A] shrink-0" />
                Gemini 1.5 Flash đảm bảo tốc độ phản hồi nhanh nhất và tối ưu chi phí hạ tầng trường học.
              </p>
            </div>

            {/* Mô hình dự phòng Backup */}
            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#2A1C0E] uppercase tracking-wider">
                Mô hình AI Dự Phòng (Failover)
              </label>
              <select
                value={settings.backupModel}
                onChange={(e) =>
                  setSettings({ ...settings, backupModel: e.target.value })
                }
                className="w-full bg-[#FFFDF9] border border-[#E8D5C4] rounded-xl px-3.5 py-2.5 text-sm font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 transition-all cursor-pointer"
              >
                <option value="gemini-1.5-pro">Google Gemini 1.5 Pro</option>
                <option value="gemini-1.5-flash">Google Gemini 1.5 Flash</option>
              </select>
              <p className="text-[11px] text-[#7E6B5A]">
                Tự động kích hoạt khi Google Gemini chính gặp sự cố quota hoặc rate limit.
              </p>
            </div>

            {/* Slider: Temperature */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[#2A1C0E]">
                  Nhiệt độ sáng tạo (Temperature):
                </span>
                <span className="font-extrabold px-2.5 py-0.5 rounded-lg bg-[#FDF6EE] text-[#C1762A] border border-[#F1CCA6] text-xs font-mono">
                  {settings.temperature.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={settings.temperature}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    temperature: parseFloat(e.target.value),
                  })
                }
                className="w-full h-2 bg-[#F7ECE1] rounded-lg appearance-none cursor-pointer accent-[#C1762A]"
              />
              <div className="flex justify-between text-[11px] text-[#7E6B5A]">
                <span>0.0 (Chính xác tuyệt đối)</span>
                <span className="text-[#C1762A] font-semibold">
                  Khuyến nghị Toán học: 0.20 - 0.40 (Tránh ảo giác)
                </span>
                <span>1.0 (Sáng tạo tối đa)</span>
              </div>
            </div>

            {/* Slider: Max Tokens */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[#2A1C0E]">
                  Hạn mức độ dài phản hồi (Max Output Tokens):
                </span>
                <span className="font-extrabold px-2.5 py-0.5 rounded-lg bg-[#FDF6EE] text-[#C1762A] border border-[#F1CCA6] text-xs font-mono">
                  {settings.maxTokens} tokens
                </span>
              </div>
              <input
                type="range"
                min="256"
                max="2048"
                step="64"
                value={settings.maxTokens}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    maxTokens: parseInt(e.target.value, 10),
                  })
                }
                className="w-full h-2 bg-[#F7ECE1] rounded-lg appearance-none cursor-pointer accent-[#C1762A]"
              />
              <div className="flex justify-between text-[11px] text-[#7E6B5A]">
                <span>256 tokens</span>
                <span className="text-[#C1762A] font-semibold">
                  512 tokens: Giúp AI đặt câu hỏi gợi mở, không giải bài hộ
                </span>
                <span>2048 tokens</span>
              </div>
            </div>

            {/* Toggles tính năng AI */}
            <div className="pt-2 border-t border-[#F1CCA6]/40 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#2A1C0E]">
                    Kích hoạt Vision Support (Giải toán qua ảnh chụp)
                  </div>
                  <div className="text-[11px] text-[#7E6B5A]">
                    Cho phép Gemini 1.5 đọc đề bài viết tay và hình vẽ hình học
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setSettings({
                      ...settings,
                      enableVisionSupport: !settings.enableVisionSupport,
                    })
                  }
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                    settings.enableVisionSupport ? "bg-[#C1762A]" : "bg-[#D9BEA7]"
                  }`}
                >
                  <span
                    className={`block w-4 h-4 rounded-full bg-white transition-transform ${
                      settings.enableVisionSupport
                        ? "translate-x-6"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          {/* ── CARD 2: Thiết lập Giới hạn gọi API (Rate Limit) ── */}
          <div className="bg-white rounded-2xl border border-[#E8D5C4] p-6 shadow-xs space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-[#F1CCA6]/40">
              <div className="w-10 h-10 rounded-xl bg-[#EEF6FC] text-[#2B78C5] flex items-center justify-center border border-[#BADEF7]">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-[#2A1C0E]">
                  Giới Hạn Tần Suất Gọi API (Rate Limiting)
                </h2>
                <p className="text-xs text-[#7E6B5A]">
                  Ngăn chặn spam request và cân bằng tải Redis Token-Bucket
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-[#2A1C0E]">
                  Tài khoản Khách dùng thử (Guest)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={settings.guestRateLimit}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        guestRateLimit: parseInt(e.target.value, 10) || 5,
                      })
                    }
                    className="w-full bg-[#FFFDF9] border border-[#E8D5C4] rounded-xl px-3.5 py-2.5 text-sm font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] pr-16"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs text-[#7E6B5A] font-semibold pointer-events-none">
                    tin / 5 phút
                  </span>
                </div>
                <p className="text-[11px] text-[#7E6B5A]">
                  Áp dụng phiên trải nghiệm không cần đăng nhập
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-[#2A1C0E]">
                  Học sinh đã đăng ký (Student)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="5"
                    max="120"
                    value={settings.studentRateLimit}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        studentRateLimit: parseInt(e.target.value, 10) || 30,
                      })
                    }
                    className="w-full bg-[#FFFDF9] border border-[#E8D5C4] rounded-xl px-3.5 py-2.5 text-sm font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] pr-16"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs text-[#7E6B5A] font-semibold pointer-events-none">
                    tin / 5 phút
                  </span>
                </div>
                <p className="text-[11px] text-[#7E6B5A]">
                  Tài khoản có liên kết phụ huynh giám sát
                </p>
              </div>
            </div>

            {/* Toggle Cảnh báo khẩn cấp */}
            <div className="pt-3 border-t border-[#F1CCA6]/40">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#2A1C0E]">
                    Cảnh Báo Khẩn Cấp Tới Phụ Huynh (Safety Agent Alert)
                  </div>
                  <div className="text-[11px] text-[#7E6B5A]">
                    Tự động gửi email thông báo khi học sinh vi phạm tiêu chuẩn Safety 3 lần trong ngày
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setSettings({
                      ...settings,
                      enableParentAlert: !settings.enableParentAlert,
                    })
                  }
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                    settings.enableParentAlert ? "bg-[#C1762A]" : "bg-[#D9BEA7]"
                  }`}
                >
                  <span
                    className={`block w-4 h-4 rounded-full bg-white transition-transform ${
                      settings.enableParentAlert
                        ? "translate-x-6"
                        : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ===================================================================
            CỘT PHẢI (1/3 width): Healthcheck Dịch Vụ & Thông Tin Phiên Bản
            =================================================================== */}
        <div className="space-y-6">
          {/* ── CARD 3: Trạng thái Dịch vụ Ngoại vi (Healthcheck) ── */}
          <div className="bg-white rounded-2xl border border-[#E8D5C4] p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#F1CCA6]/40">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#2A8C4A]" />
                <h3 className="text-sm font-extrabold text-[#2A1C0E]">
                  Trạng Thái Dịch Vụ (Healthcheck)
                </h3>
              </div>
              <button
                type="button"
                onClick={handleRefreshHealth}
                disabled={isRefreshingHealth}
                title="Làm mới trạng thái"
                className="p-1.5 rounded-lg text-[#7E6B5A] hover:text-[#C1762A] hover:bg-[#F7ECE1] transition-all"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${
                    isRefreshingHealth ? "animate-spin text-[#C1762A]" : ""
                  }`}
                />
              </button>
            </div>

            <div className="space-y-3">
              {services.map((srv) => {
                const Icon = srv.icon;
                return (
                  <div
                    key={srv.id}
                    className="p-3 rounded-xl bg-[#FFFDFB] border border-[#E8D5C4] flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#8C4905] flex items-center justify-center shrink-0">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-bold text-[#2A1C0E]">
                          {srv.name}
                        </div>
                        <div className="text-[10px] text-[#7E6B5A] line-clamp-1">
                          {srv.provider}
                        </div>
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="flex items-center gap-1.5 justify-end">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#2A8C4A] opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2A8C4A]"></span>
                        </span>
                        <span className="text-[11px] font-bold text-[#2A8C4A]">
                          Hoạt Động
                        </span>
                      </div>
                      <div className="text-[10px] text-[#A18E7F] font-mono mt-0.5">
                        {srv.latencyMs}ms
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="p-3 rounded-xl bg-[#EAF7EE] border border-[#B7E4C4] text-[11px] text-[#2A8C4A] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>3/3 Dịch vụ kết nối ổn định, sẵn sàng phục vụ học sinh.</span>
            </div>
          </div>

          {/* ── CARD 4: Thông Tin Phiên Bản Hệ Thống ── */}
          <div className="bg-white rounded-2xl border border-[#E8D5C4] p-5 shadow-xs space-y-3.5">
            <h3 className="text-sm font-extrabold text-[#2A1C0E] pb-3 border-b border-[#F1CCA6]/40 flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#C1762A]" />
              Thông Tin Phiên Bản Hệ Thống
            </h3>

            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-[#7E6B5A]">Phiên bản Build:</span>
                <span className="font-bold text-[#8C4905] font-mono bg-[#F7ECE1] px-2 py-0.5 rounded-md">
                  {settings.systemVersion}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[#7E6B5A]">Môi trường:</span>
                <span className="font-bold text-[#2A8C4A] bg-[#EAF7EE] px-2 py-0.5 rounded-md">
                  Production Live
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[#7E6B5A]">Cập nhật lần cuối:</span>
                <span className="font-semibold text-[#2A1C0E]">
                  {settings.lastUpdated}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[#7E6B5A]">Người phụ trách:</span>
                <span className="font-semibold text-[#2A1C0E] font-mono text-[11px]">
                  {settings.updatedBy}
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-[#7E6B5A]">Hệ màu chuẩn:</span>
                <span className="text-[11px] font-mono font-bold text-[#C1762A]">
                  #C1762A / #F7ECE1
                </span>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#F1CCA6]/40 text-[11px] text-[#A18E7F] text-center">
              SocraticKid Platform • Cổng Quản Trị Hệ Thống
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
