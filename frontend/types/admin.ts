export type UserRole = "STUDENT" | "MONITOR" | "ADMIN";
export type UserStatus = "ACTIVE" | "SUSPENDED";

export interface LinkedStudent {
  id: string;
  email: string;
  name: string;
  grade?: number | null;
  avg_independence_score?: number | null;
}

export interface LinkedParent {
  id: string;
  email: string;
  name: string;
  phone?: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  grade?: number | null;
  status: UserStatus;
  created_at: string;
  last_active_at: string;
  total_sessions: number;
  total_problems_solved: number;
  avg_independence_score?: number | null;
  streak_days: number;
  linked_parent?: LinkedParent | null;
  linked_students?: LinkedStudent[];
}

export interface AdminTopic {
  id: string;
  grade: number;
  title: string;
  slug: string;
  description: string;
  curriculum: "Cánh Diều" | "Kết nối tri thức" | "Chân trời sáng tạo";
  category: "Số học" | "Hình học" | "Đại số" | "Chuyển động" | "Ứng dụng" | "Toán có lời văn";
  problem_count: number;
  active_sessions_count: number;
  is_enabled: boolean;
  comprehension_rate: number;
  socratic_prompts: {
    level1: string;
    level2: string;
    level3: string;
  };
}

export interface CurriculumTopicItem {
  id: string;
  grade: number;
  book_series: string;
  semester?: number | null;
  chapter_name: string;
  topic_name: string;
  order_index: number;
  school_year?: string | null;
  is_active: boolean;
  source_url?: string | null;
  description?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface SyncVietjackResult {
  success: boolean;
  total_synced: number;
  current_total_in_db: number;
  grades: number[];
  message: string;
  elapsed_seconds: number;
  source?: "LIVE_CRAWL" | "FALLBACK_JSON";
}

export type ViolationType =
  | "TOXIC"
  | "JAILBREAK"
  | "OFF_TOPIC"
  | "SENSITIVE"
  | "PROFANITY"
  | "ROUTING"
  | "SAFETY"
  | string;
export type SeverityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;
export type ActionTaken =
  | "BLOCKED"
  | "WARNED"
  | "REDIRECTED"
  | "NOTIFIED_PARENT"
  | "ROUTED"
  | "RECORDED"
  | string;
export type TargetAgent =
  | "AGENT_TUTOR"
  | "AGENT_SAFETY"
  | "ORCHESTRATOR"
  | "SAFETY_AGENT"
  | string;
export type AuditLogStatus = "PENDING" | "RESOLVED" | "DISMISSED";

export interface SafetyConversationContext {
  problem_title?: string;
  ai_prompt_before: string;
  student_message: string;
  guardrail_triggered_rule: string;
  safety_response_sent: string;
  session_id?: string;
}

export interface AdminSafetyLogItem {
  id: string;
  timestamp: string;
  student_id: string;
  student_name?: string;
  student_email: string;
  user_id?: string;
  email?: string;
  student_grade?: number | null;
  message_snippet: string;
  user_query?: string;
  violation_type: ViolationType;
  severity: SeverityLevel;
  action_taken: ActionTaken;
  target_agent: TargetAgent;
  flagged_reason: string;
  notify_parent?: boolean;
  parent_notified_at?: string | null;
  status?: AuditLogStatus;
  conversation_context?: SafetyConversationContext;
}

export interface AdminDifficultTopicStat {
  topic: string;
  grade: number;
  not_understood_count: number;
  average_hints: number;
  comprehension_rate?: number;
  pedagogical_feedback?: string;
}

export interface AdminSafetyStatsResponse {
  total_alerts: number;
  blocked_queries_count: number;
  jailbreak_attempts: number;
  toxic_language_count: number;
  comprehension_rate_percent: number;
  not_understood_rate_percent: number;
  common_difficult_topics: AdminDifficultTopicStat[];
}
