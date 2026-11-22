/**
 * File: types/leaderboard.ts
 * Mô tả: Types và Interfaces cho tính năng Bảng xếp hạng Chuỗi ngày học (Streak Leaderboard) - US 8.2 & Task 8.15.
 */

export interface StreakLeaderboardItem {
  rank: number;
  student_id: string;
  display_name: string;
  avatar?: string | null;
  grade?: number | null;
  streak_days: number;
  max_streak?: number | null;
  is_current_user: boolean;
}

export interface StreakLeaderboardResponse {
  scope: string; // "ALL" hoặc "GRADE_{grade}"
  grade?: number | null;
  total_participants: number;
  leaderboard: StreakLeaderboardItem[];
  current_user_entry?: StreakLeaderboardItem | null;
}

export type GradeFilter = "ALL" | 4 | 5 | 6 | 7 | 8 | 9;

export interface StreakMilestone {
  days: number;
  name: string;
  badgeEmoji: string;
  colorClass: string;
  glowClass: string;
  bgLightClass: string;
  description: string;
}
