"use client";

import { useState, useEffect, useCallback } from "react";
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
  AlertTriangle,
  Calendar,
  Cpu,
  KeyRound,
  Terminal,
  History,
  Undo2,
  Lock,
  ArrowRight,
  Send,
  AlertCircle,
  Mail,
  BookOpen,
  Network,
} from "lucide-react";
import { authFetch } from "@/lib/authFetch";

// =====================================================================
// 1. INTERFACES & SCHEMAS (ĐỒNG BỘ BACKEND SCHEMAS - US 10.3)
// =====================================================================

export interface SystemSettingsState {
  // 6 Phân hệ Model Gateway (AC-SET-04)
  primary_model: string;
  parent_insight_model: string;
  classifier_model: string;
  email_model: string;
  flashcard_model: string;
  backup_model: string;

  // Tham số sinh & Sư phạm Socratic
  temperature: number;
  top_p: number;
  max_output_tokens: number;
  socratic_strictness: "STRICT" | "STANDARD" | "FLEXIBLE";
  enable_math_reviewer: boolean;
  enable_vision_support: boolean;
  safety_threshold: string;
  enable_parent_alert: boolean;

  // Giới hạn tần suất (Rate Limiting)
  guest_rate_limit: number;
  student_rate_limit: number;

  // Mốc thời gian mô phỏng SGK (US 9.3 • AC-SET-08)
  mock_curriculum_month: number | null;

  // Metadata hệ thống & API Key
  system_version: string;
  environment: string;
  api_key_masked: string;
  last_updated_at: string;
  last_updated_by: string;
}

export interface ModelOption {
  id: string;
  name: string;
  display_name: string;
  description: string;
  speed: string;
  recommended_for: string;
}

export interface ServiceHealthItem {
  id: string;
  name: string;
  provider: string;
  status: "operational" | "degraded" | "down";
  latency_ms: number;
  detail?: string;
}

export interface AuditItem {
  id: string;
  changed_by: string;
  action: string;
  changed_at: string;
  snapshot: Record<string, unknown>;
  diff_summary: string;
}

export interface PlaygroundResult {
  reply: string;
  latency_ms: number;
  tokens_used: number;
  model_name: string;
  tested_at: string;
}

export interface KeyTestResult {
  status: "SUCCESS" | "FAILED";
  latency_ms: number;
  message: string;
  tested_at: string;
}

// Cấu hình mặc định thế hệ Gemini mới nhất (Sprint 10 - Mặc định Gemini 3.8/3.5/3.1)
const DEFAULT_SETTINGS: SystemSettingsState = {
  primary_model: "gemini-3.8-flash",
  parent_insight_model: "gemini-3.5-flash",
  classifier_model: "gemini-3.1-flash-lite",
  email_model: "gemini-3.1-flash-lite",
  flashcard_model: "gemini-3.5-flash-lite",
  backup_model: "gemini-3.5-flash-lite",
  temperature: 0.35,
  top_p: 0.90,
  max_output_tokens: 512,
  socratic_strictness: "STANDARD",
  enable_math_reviewer: true,
  enable_vision_support: true,
  safety_threshold: "BLOCK_MEDIUM_AND_ABOVE",
  enable_parent_alert: true,
  guest_rate_limit: 10,
  student_rate_limit: 30,
  mock_curriculum_month: null,
  system_version: "v2.0 (Sprint 10 Release)",
  environment: "Production (Neon + Upstash Redis)",
  api_key_masked: "••••••••",
  last_updated_at: "",
  last_updated_by: "admin@socratickid.vn",
};

// Danh mục mô hình Google khuyên dùng chuẩn bị sẵn
const INITIAL_CURATED_MODELS: ModelOption[] = [
  {
    id: "gemini-3.8-flash",
    name: "gemini-3.8-flash",
    display_name: "Gemini 3.8 Flash (Khuyên Dùng)",
    description: "Tối ưu sâu phương pháp Socratic, đo lường nhận thức và đọc ảnh đề bài",
    speed: "Siêu tốc (~0.3s)",
    recommended_for: "Chat Socratic Chính (primary_model)",
  },
  {
    id: "gemini-3.5-flash",
    name: "gemini-3.5-flash",
    display_name: "Gemini 3.5 Flash",
    description: "Cân bằng hoàn hảo tốc độ và phân tích tổng hợp lịch sử học tập dài hạn",
    speed: "Rất nhanh (~0.4s)",
    recommended_for: "Báo Cáo Phụ Huynh (parent_insight_model)",
  },
  {
    id: "gemini-3.1-flash-lite",
    name: "gemini-3.1-flash-lite",
    display_name: "Gemini 3.1 Flash-Lite (Tiết Kiệm)",
    description: "Tiết kiệm chi phí token tới 60%, phản hồi tức thì cho phân loại SGK",
    speed: "Tức thì (~0.15s)",
    recommended_for: "Phân Loại SGK & Email (classifier_model, email_model)",
  },
  {
    id: "gemini-3.5-flash-lite",
    name: "gemini-3.5-flash-lite",
    display_name: "Gemini 3.5 Flash-Lite",
    description: "Trọng lượng nhẹ, ổn định cao, tối ưu rút trích thẻ ghi nhớ & dự phòng",
    speed: "Cực nhanh (~0.2s)",
    recommended_for: "Flashcard & Dự Phòng (flashcard_model, backup_model)",
  },
  {
    id: "gemini-2.5-flash",
    name: "gemini-2.5-flash",
    display_name: "Gemini 2.5 Flash (LTS)",
    description: "Phiên bản ổn định cao, nhận diện hình học và chữ viết tay học sinh",
    speed: "Rất nhanh (~0.35s)",
    recommended_for: "Dự phòng phụ",
  },
];

// Định nghĩa 5 Tabs chuyên nghiệp (T10.3.4)
type TabId = "models" | "pedagogy" | "ratelimits" | "playground" | "audits";

interface TabItem {
  id: TabId;
  label: string;
  subtitle: string;
  icon: typeof Bot;
  badge?: string;
}

const TABS: TabItem[] = [
  {
    id: "models",
    label: "Model Gateway & Routing",
    subtitle: "6 phân hệ & Failover Cascade",
    icon: Cpu,
    badge: "6 Models",
  },
  {
    id: "pedagogy",
    label: "Tham Số Sư Phạm",
    subtitle: "Temperature, Socratic & Reviewer",
    icon: Sliders,
  },
  {
    id: "ratelimits",
    label: "Rate Limits & Quản Trị Khóa",
    subtitle: "Token-Bucket & API Key Readonly",
    icon: Shield,
    badge: "Readonly",
  },
  {
    id: "playground",
    label: "Playground & Healthcheck",
    subtitle: "Sa bàn prompt toán & Ping thật",
    icon: Terminal,
    badge: "Live",
  },
  {
    id: "audits",
    label: "Mock Month & Rollback",
    subtitle: "Mô phỏng SGK & Lịch sử hoàn tác",
    icon: History,
  },
];

export default function AdminSettingsPage() {
  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  // Tab navigation state
  const [activeTab, setActiveTab] = useState<TabId>("models");

  // Core settings state
  const [settings, setSettings] = useState<SystemSettingsState>(DEFAULT_SETTINGS);
  const [availableModels, setAvailableModels] = useState<ModelOption[]>(
    INITIAL_CURATED_MODELS
  );
  const [enableFailover, setEnableFailover] = useState<boolean>(true);

  // Loading flags
  const [isLoadingSettings, setIsLoadingSettings] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isSyncingModels, setIsSyncingModels] = useState<boolean>(false);
  const [isPingingKey, setIsPingingKey] = useState<boolean>(false);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState<boolean>(false);
  const [isRunningPlayground, setIsRunningPlayground] = useState<boolean>(false);
  const [isRollingBack, setIsRollingBack] = useState<string | null>(null);

  // Dynamic feedback results
  const [keyTestResult, setKeyTestResult] = useState<KeyTestResult | null>(null);
  const [healthServices, setHealthServices] = useState<ServiceHealthItem[]>([
    {
      id: "postgres",
      name: "Neon PostgreSQL",
      provider: "Serverless Database (Neon Cloud)",
      status: "operational",
      latency_ms: 45,
      detail: "Kết nối bền vững Neon",
    },
    {
      id: "redis",
      name: "Upstash Redis",
      provider: "Hot-Reload Cache & Rate Limiting",
      status: "operational",
      latency_ms: 18,
      detail: "TTL 300s cache hoạt động",
    },
    {
      id: "gemini",
      name: "Google Gemini API Gateway",
      provider: "LLM Pedagogical Inference Engine",
      status: "operational",
      latency_ms: 295,
      detail: "Khóa Gemini sẵn sàng",
    },
    {
      id: "smtp",
      name: "Brevo SMTP Mailer",
      provider: "Email Alert Sư Phạm & Safety Alert",
      status: "operational",
      latency_ms: 82,
      detail: "Cổng gửi thư phụ huynh",
    },
  ]);
  const [audits, setAudits] = useState<AuditItem[]>([]);

  // Mini Playground states
  const [playgroundPrompt, setPlaygroundPrompt] = useState<string>(
    "Giải phương trình: 2x + 5 = 15. Hãy gợi mở bước đầu tiên cho học sinh lớp 7."
  );
  const [playgroundModel, setPlaygroundModel] = useState<string>("gemini-3.8-flash");
  const [playgroundResult, setPlaygroundResult] = useState<PlaygroundResult | null>(
    null
  );

  // Toast notification state
  const [showToast, setShowToast] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string>("");
  const [toastType, setToastType] = useState<"success" | "info" | "error">(
    "success"
  );

  const triggerToast = (
    msg: string,
    type: "success" | "info" | "error" = "success"
  ) => {
    setToastMessage(msg);
    setToastType(type);
    setShowToast(true);
    setTimeout(() => {
      setShowToast(false);
    }, 3500);
  };

  // =====================================================================
  // 2. TẢI CẤU HÌNH TỪ BACKEND QUA authFetch (GỌI TRỰC TIẾP API NEON & REDIS)
  // =====================================================================
  const loadSettings = useCallback(async () => {
    setIsLoadingSettings(true);
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings({
          primary_model: data.primary_model || "gemini-3.8-flash",
          parent_insight_model: data.parent_insight_model || "gemini-3.5-flash",
          classifier_model: data.classifier_model || "gemini-3.1-flash-lite",
          email_model: data.email_model || "gemini-3.1-flash-lite",
          flashcard_model: data.flashcard_model || "gemini-3.5-flash-lite",
          backup_model: data.backup_model || "gemini-3.5-flash-lite",
          temperature: typeof data.temperature === "number" ? data.temperature : 0.35,
          top_p: typeof data.top_p === "number" ? data.top_p : 0.90,
          max_output_tokens: data.max_output_tokens || 512,
          socratic_strictness: data.socratic_strictness || "STANDARD",
          enable_math_reviewer:
            data.enable_math_reviewer !== undefined
              ? Boolean(data.enable_math_reviewer)
              : true,
          enable_vision_support:
            data.enable_vision_support !== undefined
              ? Boolean(data.enable_vision_support)
              : true,
          safety_threshold: data.safety_threshold || "BLOCK_MEDIUM_AND_ABOVE",
          enable_parent_alert:
            data.enable_parent_alert !== undefined
              ? Boolean(data.enable_parent_alert)
              : true,
          guest_rate_limit: data.guest_rate_limit || 10,
          student_rate_limit: data.student_rate_limit || 30,
          mock_curriculum_month:
            data.mock_curriculum_month !== undefined
              ? data.mock_curriculum_month
              : null,
          system_version: data.system_version || "v2.0 (Sprint 10 Release)",
          environment: data.environment || "Production (Neon + Upstash Redis)",
          api_key_masked: data.api_key_masked || "••••••••",
          last_updated_at: data.last_updated_at || "Vừa khởi tạo",
          last_updated_by: data.last_updated_by || "admin@socratickid.vn",
        });
      } else {
        triggerToast("Không thể tải cấu hình từ server, vui lòng thử lại.", "error");
      }
    } catch (err) {
      console.error("[Admin Settings] Lỗi tải settings:", err);
      triggerToast("Lỗi kết nối Backend Admin Settings.", "error");
    } finally {
      setIsLoadingSettings(false);
    }
  }, [BACKEND_URL]);

  // Tải danh sách audits
  const loadAudits = useCallback(async () => {
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/settings/audits?limit=10`);
      if (res.ok) {
        const data = await res.json();
        setAudits(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.warn("[Admin Settings] Không thể tải danh sách audits:", err);
    }
  }, [BACKEND_URL]);

  // Tải healthcheck thật
  const refreshHealth = useCallback(async () => {
    setIsRefreshingHealth(true);
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/settings/health`);
      if (res.ok) {
        const data = await res.json();
        if (data.services && Array.isArray(data.services)) {
          setHealthServices(data.services);
          triggerToast("Đã cập nhật trạng thái Healthcheck thời gian thực!", "info");
        }
      } else {
        triggerToast("Lỗi khi kiểm tra trạng thái dịch vụ.", "error");
      }
    } catch {
      triggerToast("Không thể kết nối dịch vụ Healthcheck.", "error");
    } finally {
      setIsRefreshingHealth(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    loadSettings();
    loadAudits();
  }, [loadSettings, loadAudits]);

  // =====================================================================
  // 3. LƯU CẤU HÌNH (PUT /admin/settings) — HOT-RELOADING TỨC THÌ
  // =====================================================================
  const handleSave = async () => {
    setIsSaving(true);
    try {
      const payload = {
        primary_model: settings.primary_model,
        parent_insight_model: settings.parent_insight_model,
        classifier_model: settings.classifier_model,
        email_model: settings.email_model,
        flashcard_model: settings.flashcard_model,
        backup_model: settings.backup_model,
        temperature: settings.temperature,
        top_p: settings.top_p,
        max_output_tokens: settings.max_output_tokens,
        socratic_strictness: settings.socratic_strictness,
        enable_math_reviewer: settings.enable_math_reviewer,
        enable_vision_support: settings.enable_vision_support,
        safety_threshold: settings.safety_threshold,
        enable_parent_alert: settings.enable_parent_alert,
        guest_rate_limit: settings.guest_rate_limit,
        student_rate_limit: settings.student_rate_limit,
        mock_curriculum_month: settings.mock_curriculum_month,
        system_version: settings.system_version,
        environment: settings.environment,
      };

      const res = await authFetch(`${BACKEND_URL}/admin/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const updated = await res.json();
        setSettings((prev) => ({
          ...prev,
          last_updated_at: updated.last_updated_at || "Vừa xong",
          last_updated_by: updated.last_updated_by || prev.last_updated_by,
        }));
        triggerToast(
          "Đã lưu vĩnh viễn vào DB & Hot-Reload cache Redis tức thì!",
          "success"
        );
        loadAudits(); // Cập nhật danh sách audit trail ngay lập tức
      } else {
        const errorData = await res.json().catch(() => ({}));
        triggerToast(
          errorData.detail || "Không thể lưu cấu hình, vui lòng thử lại.",
          "error"
        );
      }
    } catch (err) {
      console.error("[Admin Settings] Lỗi lưu cấu hình:", err);
      triggerToast("Lỗi kết nối khi lưu cấu hình.", "error");
    } finally {
      setIsSaving(false);
    }
  };

  // Đồng bộ danh sách Model từ Google API
  const handleSyncModels = async () => {
    setIsSyncingModels(true);
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/settings/models`);
      if (res.ok) {
        const models: ModelOption[] = await res.json();
        if (Array.isArray(models) && models.length > 0) {
          setAvailableModels(models);
          triggerToast(
            `Đã đồng bộ ${models.length} mô hình chính thức từ Google API!`,
            "success"
          );
        }
      } else {
        triggerToast("Không thể đồng bộ danh sách model từ Google.", "error");
      }
    } catch {
      triggerToast("Lỗi kết nối khi đồng bộ mô hình Google.", "error");
    } finally {
      setIsSyncingModels(false);
    }
  };

  // Test Ping API Key đo latency thật (AC-SET-03)
  const handleTestKey = async () => {
    setIsPingingKey(true);
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/settings/test-key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const data: KeyTestResult = await res.json();
        setKeyTestResult(data);
        if (data.status === "SUCCESS") {
          triggerToast(
            `Ping Gemini thành công! Độ trễ: ${data.latency_ms}ms`,
            "success"
          );
        } else {
          triggerToast(`Ping Gemini thất bại: ${data.message}`, "error");
        }
      } else {
        triggerToast("Không thể gửi yêu cầu Ping API Key.", "error");
      }
    } catch {
      triggerToast("Lỗi mạng khi kiểm tra kết nối API Key.", "error");
    } finally {
      setIsPingingKey(false);
    }
  };

  // Chạy thử nghiệm Mini Playground (AC-SET-05)
  const handleRunPlayground = async () => {
    if (!playgroundPrompt.trim()) {
      triggerToast("Vui lòng nhập câu hỏi hoặc bài toán thử nghiệm.", "error");
      return;
    }
    setIsRunningPlayground(true);
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/settings/test-playground`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: playgroundModel,
          prompt: playgroundPrompt,
          temperature: settings.temperature,
        }),
      });
      if (res.ok) {
        const data: PlaygroundResult = await res.json();
        setPlaygroundResult(data);
        triggerToast("Phản hồi Socratic đã được sinh thành công!", "success");
      } else {
        triggerToast("Lỗi khi chạy thử nghiệm Playground.", "error");
      }
    } catch {
      triggerToast("Lỗi kết nối máy chủ Playground.", "error");
    } finally {
      setIsRunningPlayground(false);
    }
  };

  // Hoàn tác cấu hình 1-Click (AC-SET-07)
  const handleRollback = async (auditId: string) => {
    if (
      !confirm(
        "Bạn có chắc chắn muốn hoàn tác cấu hình hệ thống về phiên lịch sử này không?"
      )
    ) {
      return;
    }
    setIsRollingBack(auditId);
    try {
      const res = await authFetch(
        `${BACKEND_URL}/admin/settings/rollback/${auditId}`,
        {
          method: "POST",
        }
      );
      if (res.ok) {
        triggerToast("Đã khôi phục thành công cấu hình phiên trước!", "success");
        loadSettings();
        loadAudits();
      } else {
        triggerToast("Không thể hoàn tác cấu hình.", "error");
      }
    } catch {
      triggerToast("Lỗi kết nối khi thực hiện hoàn tác.", "error");
    } finally {
      setIsRollingBack(null);
    }
  };

  // Đặt lại mặc định
  const handleResetDefaults = () => {
    if (
      confirm(
        "Bạn có chắc muốn đặt lại toàn bộ tham số về cấu hình mặc định chuẩn Sprint 10?"
      )
    ) {
      setSettings(DEFAULT_SETTINGS);
      triggerToast("Đã nạp lại cấu hình mặc định. Nhấn Lưu để lưu vào DB.", "info");
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-14 text-[#1C1917]">
      {/* ── Toast Notification Nổi ── */}
      {showToast && (
        <div className="fixed top-5 right-5 z-50 animate-in slide-in-from-top-4 fade-in duration-200">
          <div
            className={`flex items-center gap-3 px-4 py-3 rounded-2xl shadow-xl border text-sm font-medium ${
              toastType === "success"
                ? "bg-[#1C1917] text-white border-[#C1762A]/60"
                : toastType === "error"
                ? "bg-[#FEF2F2] text-[#991B1B] border-[#FCA5A5]"
                : "bg-white text-[#1C1917] border-[#F1CCA6]"
            }`}
          >
            <div
              className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 ${
                toastType === "success"
                  ? "bg-[#C1762A] text-white"
                  : toastType === "error"
                  ? "bg-[#EF4444] text-white"
                  : "bg-[#F7ECE1] text-[#8C4905]"
              }`}
            >
              {toastType === "success" ? (
                <Check className="w-4 h-4" />
              ) : toastType === "error" ? (
                <AlertCircle className="w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
            </div>
            <span className="font-semibold">{toastMessage}</span>
            <button
              onClick={() => setShowToast(false)}
              className="opacity-70 hover:opacity-100 transition-opacity ml-2 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── Page Header & Global Actions ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-[#F1CCA6] shadow-xs">
        <div className="flex items-center gap-4 min-w-0 max-w-3xl">
          <div className="w-13 h-13 bg-gradient-to-br from-[#C1762A] to-[#8C4905] rounded-2xl flex items-center justify-center text-white shadow-md shrink-0">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl md:text-3xl font-extrabold text-[#8C4905] tracking-tight">
                Cài Đặt Hệ Thống & Tham Số AI
              </h1>
              <span className="text-[11px] font-extrabold px-2.5 py-0.5 rounded-full bg-[#ECFDF5] text-[#10B981] border border-[#A7F3D0]">
                {settings.system_version} • Hot-Reloading
              </span>
            </div>
            <p className="text-xs md:text-sm text-[#7A3E04] mt-1 font-medium">
              Trung tâm kiểm soát 6 phân hệ Model Gateway, tham số sư phạm Socratic, bảo mật khóa và kiểm thử thực tế
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 self-start md:self-auto">
          <button
            type="button"
            onClick={handleResetDefaults}
            disabled={isSaving || isLoadingSettings}
            className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs md:text-sm font-bold text-[#7A3E04] bg-white border border-[#F1CCA6] hover:bg-[#F7ECE1] hover:text-[#1C1917] hover:border-[#C1762A] transition-all shadow-xs active:scale-95 cursor-pointer whitespace-nowrap"
          >
            <RotateCcw className="w-3.5 h-3.5 text-[#C1762A]" />
            <span>Đặt lại mặc định</span>
          </button>

          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving || isLoadingSettings}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs md:text-sm font-bold text-white bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 shadow-sm transition-all active:scale-95 cursor-pointer whitespace-nowrap"
          >
            {isSaving ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>{isSaving ? "Đang lưu Neon & Redis..." : "Lưu Cấu Hình"}</span>
          </button>
        </div>
      </div>

      {/* ── Status Bar Nhỏ: Thời gian cập nhật & Người thực hiện ── */}
      <div className="flex flex-wrap items-center justify-between text-xs text-[#7A3E04] bg-[#F7ECE1]/60 px-4 py-2 rounded-xl border border-[#F1CCA6]/70">
        <div className="flex items-center gap-2">
          <Clock className="w-3.5 h-3.5 text-[#C1762A]" />
          <span>
            Lần lưu gần nhất:{" "}
            <strong className="text-[#8C4905] font-semibold">
              {settings.last_updated_at || "Chưa cập nhật"}
            </strong>
          </span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">
            Thực hiện bởi:{" "}
            <span className="font-mono text-[#1C1917]">
              {settings.last_updated_by}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
          <span>Redis TTL 300s Active</span>
        </div>
      </div>

      {/* ===================================================================
          BỐ CỤC 5 TABS CHUYÊN NGHIỆP (T10.3.4)
          =================================================================== */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] shadow-xs p-2">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-1.5">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex flex-col text-left p-3.5 rounded-xl transition-all cursor-pointer relative ${
                  isActive
                    ? "bg-[#F7ECE1] text-[#8C4905] border-2 border-[#C1762A] shadow-xs"
                    : "text-[#7A3E04] hover:bg-[#F7ECE1]/50 border border-transparent hover:border-[#F1CCA6]/60"
                }`}
              >
                <div className="flex items-center justify-between w-full mb-1">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      isActive
                        ? "bg-[#C1762A] text-white"
                        : "bg-[#F7ECE1] text-[#C1762A]"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  {tab.badge && (
                    <span
                      className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded-md ${
                        isActive
                          ? "bg-[#C1762A] text-white"
                          : "bg-[#F1CCA6]/60 text-[#8C4905]"
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </div>
                <span className="font-extrabold text-xs md:text-sm tracking-tight text-[#1C1917] line-clamp-1">
                  {tab.label}
                </span>
                <span className="text-[11px] text-[#7A3E04] line-clamp-1 mt-0.5">
                  {tab.subtitle}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ===================================================================
          TAB 1: MODEL GATEWAY & ROUTING (AC-SET-04)
          =================================================================== */}
      {activeTab === "models" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Header công cụ đồng bộ */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-2xl border border-[#F1CCA6]">
            <div>
              <h2 className="text-base font-extrabold text-[#1C1917] flex items-center gap-2">
                <Cpu className="w-5 h-5 text-[#C1762A]" />
                Phân Bổ 6 Phân Hệ Mô Hình Độc Lập
              </h2>
              <p className="text-xs text-[#7A3E04] mt-0.5">
                Mỗi tác vụ học tập được giao phó cho đúng model tối ưu để cân đối sâu giữa chi phí token và tốc độ phản hồi
              </p>
            </div>
            <button
              type="button"
              onClick={handleSyncModels}
              disabled={isSyncingModels}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold text-[#8C4905] bg-[#F7ECE1] border border-[#F1CCA6] hover:bg-[#F1CCA6]/50 hover:border-[#C1762A] transition-all cursor-pointer whitespace-nowrap self-start sm:self-auto"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 text-[#C1762A] ${
                  isSyncingModels ? "animate-spin" : ""
                }`}
              />
              <span>{isSyncingModels ? "Đang truy vấn Google API..." : "Đồng bộ từ Google API"}</span>
            </button>
          </div>

          {/* Grid 6 Dropdown Models */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {/* 1. Chat Socratic Chính */}
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center font-bold text-xs">
                  1
                </div>
                <div>
                  <h3 className="text-xs font-extrabold text-[#1C1917] uppercase tracking-wider">
                    Chat Socratic Chính
                  </h3>
                  <span className="text-[10px] text-[#7A3E04] font-mono">
                    primary_model (Chatbot trực tiếp)
                  </span>
                </div>
              </div>
              <select
                value={settings.primary_model}
                onChange={(e) =>
                  setSettings({ ...settings, primary_model: e.target.value })
                }
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 cursor-pointer"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} • {m.speed}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-[#7A3E04] leading-relaxed">
                🎯 Khuyến nghị: <strong className="text-[#8C4905]">gemini-3.8-flash</strong> — Tối ưu sư phạm gợi mở từng bước, không giải bài hộ.
              </p>
            </div>

            {/* 2. Báo Cáo Phụ Huynh */}
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center font-bold text-xs">
                  2
                </div>
                <div>
                  <h3 className="text-xs font-extrabold text-[#1C1917] uppercase tracking-wider">
                    Báo Cáo Phụ Huynh
                  </h3>
                  <span className="text-[10px] text-[#7A3E04] font-mono">
                    parent_insight_model
                  </span>
                </div>
              </div>
              <select
                value={settings.parent_insight_model}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    parent_insight_model: e.target.value,
                  })
                }
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 cursor-pointer"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} • {m.speed}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-[#7A3E04] leading-relaxed">
                🎯 Khuyến nghị: <strong className="text-[#8C4905]">gemini-3.5-flash</strong> — Phân tích dữ liệu học tập tổng thể, lời văn ấm áp.
              </p>
            </div>

            {/* 3. Phân Loại SGK & Đặt Tiêu Đề */}
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center font-bold text-xs">
                  3
                </div>
                <div>
                  <h3 className="text-xs font-extrabold text-[#1C1917] uppercase tracking-wider">
                    Phân Loại Dạng Bài SGK
                  </h3>
                  <span className="text-[10px] text-[#7A3E04] font-mono">
                    classifier_model
                  </span>
                </div>
              </div>
              <select
                value={settings.classifier_model}
                onChange={(e) =>
                  setSettings({ ...settings, classifier_model: e.target.value })
                }
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 cursor-pointer"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} • {m.speed}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-[#7A3E04] leading-relaxed">
                🎯 Khuyến nghị: <strong className="text-[#8C4905]">gemini-3.1-flash-lite</strong> — Nhận diện dạng bài toán tức thì dưới 0.2s.
              </p>
            </div>

            {/* 4. Email Cảnh Báo Sư Phạm */}
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center font-bold text-xs">
                  4
                </div>
                <div>
                  <h3 className="text-xs font-extrabold text-[#1C1917] uppercase tracking-wider">
                    Email Cảnh Báo Phụ Huynh
                  </h3>
                  <span className="text-[10px] text-[#7A3E04] font-mono">
                    email_model
                  </span>
                </div>
              </div>
              <select
                value={settings.email_model}
                onChange={(e) =>
                  setSettings({ ...settings, email_model: e.target.value })
                }
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 cursor-pointer"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} • {m.speed}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-[#7A3E04] leading-relaxed">
                🎯 Khuyến nghị: <strong className="text-[#8C4905]">gemini-3.1-flash-lite</strong> — Sinh tiêu đề và thư cảnh báo tinh tế.
              </p>
            </div>

            {/* 5. Rút Trích Flashcard & Bookmark */}
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center font-bold text-xs">
                  5
                </div>
                <div>
                  <h3 className="text-xs font-extrabold text-[#1C1917] uppercase tracking-wider">
                    Rút Trích Flashcard
                  </h3>
                  <span className="text-[10px] text-[#7A3E04] font-mono">
                    flashcard_model
                  </span>
                </div>
              </div>
              <select
                value={settings.flashcard_model}
                onChange={(e) =>
                  setSettings({ ...settings, flashcard_model: e.target.value })
                }
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 cursor-pointer"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} • {m.speed}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-[#7A3E04] leading-relaxed">
                🎯 Khuyến nghị: <strong className="text-[#8C4905]">gemini-3.5-flash-lite</strong> — Trích lọc công thức then chốt chuẩn KaTeX.
              </p>
            </div>

            {/* 6. Mô hình Dự Phòng Failover */}
            <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 shadow-xs space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center font-bold text-xs">
                  6
                </div>
                <div>
                  <h3 className="text-xs font-extrabold text-[#1C1917] uppercase tracking-wider">
                    Dự Phòng Khẩn Cấp (Failover)
                  </h3>
                  <span className="text-[10px] text-[#7A3E04] font-mono">
                    backup_model
                  </span>
                </div>
              </div>
              <select
                value={settings.backup_model}
                onChange={(e) =>
                  setSettings({ ...settings, backup_model: e.target.value })
                }
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20 cursor-pointer"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} • {m.speed}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-[#7A3E04] leading-relaxed">
                🎯 Khuyến nghị: <strong className="text-[#8C4905]">gemini-3.5-flash-lite</strong> — Tự động tiếp quản khi trạm chính gặp sự cố quota.
              </p>
            </div>
          </div>

          {/* Sơ đồ Failover Cascade Trực Quan */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#F1CCA6]/40">
              <h3 className="text-sm font-extrabold text-[#1C1917] flex items-center gap-2">
                <Network className="w-4 h-4 text-[#C1762A]" />
                Sơ Đồ Cơ Chế Điều Phối & Phục Hồi Thất Bại (Failover Cascade 3 Nấc)
              </h3>
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-bold text-[#1C1917]">
                  {enableFailover ? "Đang bật Failover" : "Đã tắt Failover"}
                </span>
                <button
                  type="button"
                  onClick={() => setEnableFailover(!enableFailover)}
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                    enableFailover ? "bg-[#C1762A]" : "bg-[#F1CCA6]"
                  }`}
                >
                  <span
                    className={`block w-4 h-4 rounded-full bg-white transition-transform ${
                      enableFailover ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-4 rounded-xl bg-[#ECFDF5] border border-[#A7F3D0] space-y-1.5">
                <div className="font-extrabold text-[#10B981] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
                  Nấc 1: Model Chính ({settings.primary_model})
                </div>
                <p className="text-[#047857] leading-relaxed">
                  Tiếp nhận 100% tin nhắn Socratic từ học sinh. Nếu Gemini trả về 429 hoặc 503, tự động chuyển tiếp sang Nấc 2 trong 50ms.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#FEF3C7] border border-[#FDE68A] space-y-1.5">
                <div className="font-extrabold text-[#92400E] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#D97706]"></span>
                  Nấc 2: Trạm Dự Phòng ({settings.backup_model})
                </div>
                <p className="text-[#B45309] leading-relaxed">
                  Kích hoạt tức thì với mô hình nhẹ hơn để duy trì trải nghiệm chat mượt mà của học sinh mà không để đứt gãy phiên học.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-[#F7ECE1] border border-[#F1CCA6] space-y-1.5">
                <div className="font-extrabold text-[#8C4905] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#C1762A]"></span>
                  Nấc 3: Quy Tắc Heuristic Cố Định
                </div>
                <p className="text-[#7A3E04] leading-relaxed">
                  Nếu mạng quốc tế đứt đoạn, hệ thống dùng bộ câu hỏi sư phạm mẫu đã lưu sẵn trong mã nguồn để hướng dẫn học sinh suy nghĩ.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          TAB 2: THAM SỐ SƯ PHẠM (PEDAGOGY)
          =================================================================== */}
      {activeTab === "pedagogy" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-6">
            <div className="flex items-center gap-3 pb-4 border-b border-[#F1CCA6]/40">
              <div className="w-10 h-10 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
                <Sliders className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-[#1C1917]">
                  Hiệu Chỉnh Tham Số Sư Phạm & Trí Tuệ Nhân Tạo
                </h2>
                <p className="text-xs text-[#7A3E04]">
                  Quy định mức độ chặt chẽ trong phương pháp Socratic và kiểm duyệt câu trả lời trước khi gửi đến học sinh
                </p>
              </div>
            </div>

            {/* Slider: Temperature */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[#1C1917]">
                  Nhiệt độ sáng tạo (Temperature):
                </span>
                <span className="font-extrabold px-2.5 py-0.5 rounded-lg bg-[#F7ECE1] text-[#C1762A] border border-[#F1CCA6] text-xs font-mono">
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
              <div className="flex justify-between text-[11px] text-[#7A3E04]">
                <span>0.0 (Chính xác tuyệt đối)</span>
                <span className="text-[#C1762A] font-semibold">
                  Khuyến nghị Toán học: 0.20 - 0.40 (Tránh ảo giác số học)
                </span>
                <span>1.0 (Sáng tạo tối đa)</span>
              </div>
            </div>

            {/* Slider: Top-P */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[#1C1917]">
                  Ngưỡng chọn lọc xác suất (Top-P):
                </span>
                <span className="font-extrabold px-2.5 py-0.5 rounded-lg bg-[#F7ECE1] text-[#C1762A] border border-[#F1CCA6] text-xs font-mono">
                  {settings.top_p.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0.5"
                max="1"
                step="0.05"
                value={settings.top_p}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    top_p: parseFloat(e.target.value),
                  })
                }
                className="w-full h-2 bg-[#F7ECE1] rounded-lg appearance-none cursor-pointer accent-[#C1762A]"
              />
              <div className="flex justify-between text-[11px] text-[#7A3E04]">
                <span>0.50 (Tập trung cao độ)</span>
                <span className="text-[#C1762A] font-semibold">
                  Khuyến nghị: 0.85 - 0.95
                </span>
                <span>1.00 (Mở rộng từ vựng)</span>
              </div>
            </div>

            {/* Slider: Max Output Tokens */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-[#1C1917]">
                  Hạn mức độ dài phản hồi (Max Output Tokens):
                </span>
                <span className="font-extrabold px-2.5 py-0.5 rounded-lg bg-[#F7ECE1] text-[#C1762A] border border-[#F1CCA6] text-xs font-mono">
                  {settings.max_output_tokens} tokens
                </span>
              </div>
              <input
                type="range"
                min="256"
                max="2048"
                step="64"
                value={settings.max_output_tokens}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    max_output_tokens: parseInt(e.target.value, 10),
                  })
                }
                className="w-full h-2 bg-[#F7ECE1] rounded-lg appearance-none cursor-pointer accent-[#C1762A]"
              />
              <div className="flex justify-between text-[11px] text-[#7A3E04]">
                <span>256 tokens</span>
                <span className="text-[#C1762A] font-semibold">
                  512 tokens: Giúp AI đặt câu hỏi gợi mở ngắn gọn 2-4 câu, không giải bài hộ
                </span>
                <span>2048 tokens</span>
              </div>
            </div>

            {/* Bộ 3 nấc Socratic Strictness */}
            <div className="space-y-2 pt-2">
              <label className="block text-xs font-bold text-[#1C1917] uppercase tracking-wider">
                Mức Độ Nghiêm Ngặt Sư Phạm (Socratic Strictness)
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  {
                    id: "STRICT",
                    title: "Chặt chẽ (Strict)",
                    desc: "Tuyệt đối không giải hộ dù học sinh nài nỉ hay đòi đáp án.",
                  },
                  {
                    id: "STANDARD",
                    title: "Tiêu chuẩn (Khuyên dùng)",
                    desc: "Gợi mở từng bước nhỏ, cung cấp bài tập tương tự khi bế tắc.",
                  },
                  {
                    id: "FLEXIBLE",
                    title: "Linh hoạt (Flexible)",
                    desc: "Được phép giải thích toàn diện bài toán khi học sinh thử sai 3 lần.",
                  },
                ].map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() =>
                      setSettings({
                        ...settings,
                        socratic_strictness: item.id as "STRICT" | "STANDARD" | "FLEXIBLE",
                      })
                    }
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      settings.socratic_strictness === item.id
                        ? "border-[#C1762A] bg-[#F7ECE1] text-[#8C4905] shadow-xs"
                        : "border-[#F1CCA6] bg-white text-[#7A3E04] hover:border-[#C1762A]/50"
                    }`}
                  >
                    <div className="font-extrabold text-xs text-[#1C1917] flex items-center justify-between">
                      <span>{item.title}</span>
                      {settings.socratic_strictness === item.id && (
                        <Check className="w-3.5 h-3.5 text-[#C1762A]" />
                      )}
                    </div>
                    <p className="text-[11px] mt-1 line-clamp-2">{item.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Các Toggles Sư Phạm */}
            <div className="pt-4 border-t border-[#F1CCA6]/40 space-y-4">
              {/* Toggle Math Reviewer */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#1C1917]">
                    Kích hoạt Local Reviewer Agent (Fact-Check Toán Học Tự Động)
                  </div>
                  <div className="text-[11px] text-[#7A3E04]">
                    Kiểm duyệt câu trả lời trước khi gửi ra màn hình học sinh để ngăn chặn việc buột miệng nói ra đáp án
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setSettings({
                      ...settings,
                      enable_math_reviewer: !settings.enable_math_reviewer,
                    })
                  }
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                    settings.enable_math_reviewer ? "bg-[#C1762A]" : "bg-[#F1CCA6]"
                  }`}
                >
                  <span
                    className={`block w-4 h-4 rounded-full bg-white transition-transform ${
                      settings.enable_math_reviewer ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              {/* Toggle Vision Support */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#1C1917]">
                    Hỗ Trợ Giải Toán Qua Ảnh Chụp (Vision Support)
                  </div>
                  <div className="text-[11px] text-[#7A3E04]">
                    Cho phép Gemini phân tích đề bài viết tay và hình vẽ hình học trong phiên học
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setSettings({
                      ...settings,
                      enable_vision_support: !settings.enable_vision_support,
                    })
                  }
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                    settings.enable_vision_support ? "bg-[#C1762A]" : "bg-[#F1CCA6]"
                  }`}
                >
                  <span
                    className={`block w-4 h-4 rounded-full bg-white transition-transform ${
                      settings.enable_vision_support ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              {/* Toggle Parent Alert */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-[#1C1917]">
                    Cảnh Báo Học Tập Yếu Qua Email Tới Phụ Huynh (Academic & Safety Alert)
                  </div>
                  <div className="text-[11px] text-[#7A3E04]">
                    Tự động kích hoạt khi học sinh gặp khó khăn liên tục 3 bài hoặc vi phạm tiêu chuẩn an toàn
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setSettings({
                      ...settings,
                      enable_parent_alert: !settings.enable_parent_alert,
                    })
                  }
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${
                    settings.enable_parent_alert ? "bg-[#C1762A]" : "bg-[#F1CCA6]"
                  }`}
                >
                  <span
                    className={`block w-4 h-4 rounded-full bg-white transition-transform ${
                      settings.enable_parent_alert ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          TAB 3: RATE LIMITS & QUẢN TRỊ KHÓA (AC-SET-03)
          =================================================================== */}
      {activeTab === "ratelimits" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Card Rate Limiting */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-[#F1CCA6]/40">
              <div className="w-10 h-10 rounded-xl bg-[#EEF6FC] text-[#2B78C5] flex items-center justify-center border border-[#BADEF7]">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-[#1C1917]">
                  Giới Hạn Tần Suất Gọi API (Upstash Redis Token-Bucket)
                </h2>
                <p className="text-xs text-[#7A3E04]">
                  Cân bằng tải và ngăn chặn spam request gây cạn kiệt ngân sách Gemini API
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-[#1C1917]">
                  Khách Dùng Thử (Guest)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={settings.guest_rate_limit}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        guest_rate_limit: parseInt(e.target.value, 10) || 5,
                      })
                    }
                    className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3.5 py-2.5 text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] pr-18"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs text-[#7A3E04] font-semibold pointer-events-none">
                    tin / 5 phút
                  </span>
                </div>
                <p className="text-[11px] text-[#7A3E04]">
                  Áp dụng cho học sinh chưa đăng nhập tài khoản.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-bold text-[#1C1917]">
                  Học Sinh Đã Đăng Ký (Student)
                </label>
                <div className="relative">
                  <input
                    type="number"
                    min="5"
                    max="120"
                    value={settings.student_rate_limit}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        student_rate_limit: parseInt(e.target.value, 10) || 30,
                      })
                    }
                    className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3.5 py-2.5 text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] pr-18"
                  />
                  <span className="absolute right-3.5 top-2.5 text-xs text-[#7A3E04] font-semibold pointer-events-none">
                    tin / 5 phút
                  </span>
                </div>
                <p className="text-[11px] text-[#7A3E04]">
                  Áp dụng cho tài khoản học sinh đã kích hoạt và liên kết phụ huynh.
                </p>
              </div>
            </div>
          </div>

          {/* Card Quản Trị Khóa API Key Readonly & Test Ping (AC-SET-03) */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-5">
            <div className="flex items-center justify-between pb-4 border-b border-[#F1CCA6]/40">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
                  <KeyRound className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-extrabold text-[#1C1917] flex items-center gap-2">
                    Trạng Thái Khóa Google Gemini API
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#ECFDF5] text-[#10B981] border border-[#A7F3D0]">
                      Bảo mật cao • Readonly
                    </span>
                  </h2>
                  <p className="text-xs text-[#7A3E04]">
                    Theo kiến trúc Sprint 10, khóa API được nạp trực tiếp qua biến môi trường server (.env), tuyệt đối không lưu vào Database
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={handleTestKey}
                disabled={isPingingKey}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 shadow-xs transition-all cursor-pointer whitespace-nowrap"
              >
                <Activity
                  className={`w-3.5 h-3.5 ${isPingingKey ? "animate-spin" : ""}`}
                />
                <span>{isPingingKey ? "Đang ping Gemini..." : "Test Ping Khóa"}</span>
              </button>
            </div>

            {/* Readonly Key Display */}
            <div className="p-4 rounded-xl bg-[#F7ECE1]/40 border border-[#F1CCA6] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <span className="text-xs text-[#7A3E04] font-semibold">
                  Mã khóa nhận dạng đang kích hoạt:
                </span>
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-[#C1762A]" />
                  <span className="font-mono text-sm font-bold text-[#1C1917] tracking-widest bg-white px-3 py-1 rounded-lg border border-[#F1CCA6]">
                    {settings.api_key_masked}
                  </span>
                </div>
              </div>

              {keyTestResult && (
                <div
                  className={`px-3 py-2 rounded-xl border text-xs font-bold flex items-center gap-2 ${
                    keyTestResult.status === "SUCCESS"
                      ? "bg-[#ECFDF5] text-[#10B981] border-[#A7F3D0]"
                      : "bg-[#FEF2F2] text-[#DC2626] border-[#FCA5A5]"
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>
                    {keyTestResult.message} • {keyTestResult.latency_ms}ms
                  </span>
                </div>
              )}
            </div>

            <div className="text-[11px] text-[#7A3E04] bg-[#F7ECE1]/60 p-3.5 rounded-xl border border-[#F1CCA6]/60 leading-relaxed">
              💡 <strong>Lưu ý quản trị:</strong> Để thay đổi hoặc luân chuyển khóa API Key mới, Quản trị viên vui lòng cập nhật biến môi trường <code className="font-mono bg-white px-1.5 py-0.5 rounded border border-[#F1CCA6]">GEMINI_API_KEY</code> trên bảng điều khiển hạ tầng (Render / Railway / VPS) để đảm bảo tuân thủ tiêu chuẩn an toàn bảo mật dữ liệu.
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          TAB 4: PLAYGROUND & HEALTHCHECK (AC-SET-05 & AC-SET-06)
          =================================================================== */}
      {activeTab === "playground" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* ── CARD PLAYGROUND ── */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-5">
            <div className="flex items-center gap-3 pb-4 border-b border-[#F1CCA6]/40">
              <div className="w-10 h-10 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
                <Terminal className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-[#1C1917] flex items-center gap-2">
                  Sa Bàn Mini Playground Socratic Toán Học
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#ECFDF5] text-[#10B981] border border-[#A7F3D0]">
                    AC-SET-05
                  </span>
                </h2>
                <p className="text-xs text-[#7A3E04]">
                  Thử nghiệm câu hỏi hoặc đề bài toán để kiểm tra phong cách phản hồi của mô hình mà không cần mở phiên chat học sinh
                </p>
              </div>
            </div>

            {/* Input & Controls */}
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="sm:w-1/3">
                  <label className="block text-xs font-bold text-[#1C1917] mb-1">
                    Chọn Model Thử Nghiệm:
                  </label>
                  <select
                    value={playgroundModel}
                    onChange={(e) => setPlaygroundModel(e.target.value)}
                    className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3 py-2 text-xs font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A]"
                  >
                    {availableModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="sm:w-2/3 flex items-end gap-2">
                  <div className="flex-1">
                    <label className="block text-xs font-bold text-[#1C1917] mb-1">
                      Các prompt mẫu sư phạm:
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        "x + 5 = 12",
                        "Tính diện tích hình thang",
                        "1/2 + 3/4 = ?",
                        "Em không biết làm bài này",
                      ].map((sample) => (
                        <button
                          key={sample}
                          type="button"
                          onClick={() => setPlaygroundPrompt(sample)}
                          className="text-[11px] font-medium px-2 py-1 rounded-lg bg-[#F7ECE1] text-[#8C4905] hover:bg-[#F1CCA6] transition-colors cursor-pointer"
                        >
                          {sample}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#1C1917] mb-1">
                  Nội dung đề bài hoặc câu hỏi học sinh:
                </label>
                <textarea
                  rows={3}
                  value={playgroundPrompt}
                  onChange={(e) => setPlaygroundPrompt(e.target.value)}
                  placeholder="Nhập bài toán hoặc câu hỏi tại đây..."
                  className="w-full bg-white border border-[#F1CCA6] rounded-xl p-3 text-xs md:text-sm text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] focus:ring-2 focus:ring-[#C1762A]/20"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleRunPlayground}
                  disabled={isRunningPlayground}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs md:text-sm font-bold text-white bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 shadow-sm transition-all cursor-pointer whitespace-nowrap"
                >
                  <Send
                    className={`w-4 h-4 ${isRunningPlayground ? "animate-pulse" : ""}`}
                  />
                  <span>
                    {isRunningPlayground ? "Đang gọi Gemini sinh lời giải..." : "Thử Nghiệm Prompt"}
                  </span>
                </button>
              </div>
            </div>

            {/* Kết Quả Playground */}
            {playgroundResult && (
              <div className="p-4 rounded-xl bg-[#F7ECE1]/40 border border-[#F1CCA6] space-y-3">
                <div className="flex items-center justify-between text-xs text-[#7A3E04] pb-2 border-b border-[#F1CCA6]/40">
                  <span className="font-bold text-[#8C4905]">
                    Phản hồi từ {playgroundResult.model_name}:
                  </span>
                  <div className="flex items-center gap-3 font-mono text-[11px]">
                    <span>Độ trễ: {playgroundResult.latency_ms}ms</span>
                    <span>•</span>
                    <span>Tokens: {playgroundResult.tokens_used}</span>
                  </div>
                </div>
                <p className="text-xs md:text-sm text-[#1C1917] whitespace-pre-line leading-relaxed font-sans">
                  {playgroundResult.reply}
                </p>
              </div>
            )}
          </div>

          {/* ── CARD HEALTHCHECK THỰC TẾ (AC-SET-06) ── */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#F1CCA6]/40">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-[#10B981]" />
                <h3 className="text-sm font-extrabold text-[#1C1917]">
                  Trạng Thái Kết Nối 4 Dịch Vụ Cốt Lõi (Healthcheck Thực Tế)
                </h3>
              </div>
              <button
                type="button"
                onClick={refreshHealth}
                disabled={isRefreshingHealth}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-[#8C4905] bg-[#F7ECE1] hover:bg-[#F1CCA6]/60 transition-all cursor-pointer"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 text-[#C1762A] ${
                    isRefreshingHealth ? "animate-spin" : ""
                  }`}
                />
                <span>Làm mới ping</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {healthServices.map((srv) => {
                const isOp = srv.status === "operational";
                return (
                  <div
                    key={srv.id}
                    className="p-4 rounded-xl bg-white border border-[#F1CCA6] space-y-2 shadow-2xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#1C1917]">
                        {srv.name}
                      </span>
                      <span
                        className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                          isOp
                            ? "bg-[#ECFDF5] text-[#10B981]"
                            : "bg-[#FEF2F2] text-[#DC2626]"
                        }`}
                      >
                        {isOp ? "Hoạt động" : "Gián đoạn"}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#7A3E04] line-clamp-1">
                      {srv.provider}
                    </p>
                    <div className="flex items-center justify-between pt-1 border-t border-[#F1CCA6]/30 text-xs font-mono">
                      <span className="text-[#7A3E04]">Độ trễ:</span>
                      <span className="font-bold text-[#C1762A]">
                        {srv.latency_ms}ms
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================
          TAB 5: MOCK MONTH & ROLLBACK (AC-SET-07 & AC-SET-08)
          =================================================================== */}
      {activeTab === "audits" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Mô Phỏng Thời Gian Học Kỳ SGK (US 9.3 • AC-SET-08) */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-3 pb-3 border-b border-[#F1CCA6]/40">
              <div className="w-10 h-10 rounded-xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center border border-[#F1CCA6]">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-extrabold text-[#1C1917]">
                    Mô Phỏng Thời Gian Học Kỳ SGK Phục Vụ Nghiệm Thu
                  </h2>
                  <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]">
                    US 9.3 • AC-SET-08
                  </span>
                </div>
                <p className="text-xs text-[#7A3E04]">
                  Giả lập mốc thời gian để Hội đồng nghiệm thu kiểm thử phản hồi thích ứng theo tiến độ chương trình học
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="block text-xs font-bold text-[#1C1917] uppercase tracking-wider">
                Chọn Chế Độ Thời Gian Kiểm Thử
              </label>
              <select
                value={
                  !settings.mock_curriculum_month
                    ? "auto"
                    : String(settings.mock_curriculum_month)
                }
                onChange={(e) => {
                  const val = e.target.value;
                  setSettings({
                    ...settings,
                    mock_curriculum_month: val === "auto" ? null : parseInt(val, 10),
                  });
                }}
                className="w-full bg-white border border-[#F1CCA6] rounded-xl px-3.5 py-2.5 text-xs md:text-sm font-semibold text-[#1C1917] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
              >
                <option value="auto">
                  🟢 Thời gian thực hệ thống (Tự động theo ngày giờ thực tế của server)
                </option>
                <option value="10">
                  🍂 Học kỳ 1 — Tháng 10 (Nghiệm thu bài HK2 chưa học & bài thăm dò HK1)
                </option>
                <option value="3">
                  🌸 Học kỳ 2 — Tháng 3 (Nghiệm thu bài cùng kỳ HK2 & bài kỳ trước HK1)
                </option>
                <option value="7">
                  🏖️ Kỳ nghỉ hè — Tháng 7 (Nghiệm thu câu hỏi thăm dò & ôn tập hè)
                </option>
              </select>
            </div>
          </div>

          {/* Bảng Lịch Sử Thay Đổi & Hoàn Tác 1-Click (AC-SET-07) */}
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#F1CCA6]/40">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-[#C1762A]" />
                <h3 className="text-sm font-extrabold text-[#1C1917]">
                  Nhật Ký Cấu Hình & Hoàn Tác 1-Click (Audit Trail Rollback)
                </h3>
              </div>
              <button
                type="button"
                onClick={loadAudits}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-[#8C4905] bg-[#F7ECE1] hover:bg-[#F1CCA6]/60 transition-all cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5 text-[#C1762A]" />
                <span>Tải lại lịch sử</span>
              </button>
            </div>

            {audits.length === 0 ? (
              <div className="p-8 text-center text-xs text-[#7A3E04] bg-[#F7ECE1]/30 rounded-xl border border-dashed border-[#F1CCA6]">
                Chưa có bản ghi lịch sử nào được ghi nhận. Hãy chỉnh sửa và lưu cấu hình để tạo phiên mới.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#F1CCA6] text-[#7A3E04] font-bold">
                      <th className="pb-2.5">Thời Gian</th>
                      <th className="pb-2.5">Người Đổi</th>
                      <th className="pb-2.5">Tóm Tắt Thay Đổi</th>
                      <th className="pb-2.5 text-right">Thao Tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F1CCA6]/40">
                    {audits.map((item) => (
                      <tr key={item.id} className="hover:bg-[#F7ECE1]/40">
                        <td className="py-3 font-mono text-[11px] text-[#1C1917]">
                          {item.changed_at}
                        </td>
                        <td className="py-3 font-semibold text-[#8C4905]">
                          {item.changed_by}
                        </td>
                        <td className="py-3 text-[#7A3E04] max-w-xs truncate">
                          {item.diff_summary || "Cập nhật tham số hệ thống"}
                        </td>
                        <td className="py-3 text-right">
                          <button
                            type="button"
                            onClick={() => handleRollback(item.id)}
                            disabled={isRollingBack === item.id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-[#C1762A] bg-[#F7ECE1] border border-[#F1CCA6] hover:bg-[#C1762A] hover:text-white transition-all cursor-pointer"
                          >
                            <Undo2 className="w-3 h-3" />
                            <span>
                              {isRollingBack === item.id
                                ? "Đang khôi phục..."
                                : "Khôi phục phiên này"}
                            </span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
