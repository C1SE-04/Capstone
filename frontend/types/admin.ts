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
