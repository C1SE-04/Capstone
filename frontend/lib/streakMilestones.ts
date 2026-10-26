/**
 * File: lib/streakMilestones.ts
 * Mô tả: Định nghĩa 7 mốc tiến hóa của Ngọn Lửa Streak (US 8.2) và các helper tính toán cấp bậc.
 */

export interface StreakMilestoneInfo {
  tier: number;
  minDays: number;
  name: string;
  emoji: string;
  flameColor: string; // Tailwind class cho màu lửa
  badgeBg: string;    // Màu nền badge
  badgeBorder: string;// Màu viền badge
  textColor: string;  // Màu chữ
  glowEffect: string; // Hiệu ứng shadow / glow
  description: string;
}

export const STREAK_MILESTONES: StreakMilestoneInfo[] = [
  {
    tier: 0,
    minDays: 0,
    name: "Tia Lửa Mầm",
    emoji: "🌱",
    flameColor: "text-amber-400 fill-amber-200",
    badgeBg: "bg-amber-50",
    badgeBorder: "border-amber-200",
    textColor: "text-amber-700",
    glowEffect: "shadow-xs",
    description: "Khởi đầu hành trình học tập kiên trì.",
  },
  {
    tier: 1,
    minDays: 3,
    name: "Đốm Lửa Khởi Đầu",
    emoji: "✨",
    flameColor: "text-orange-500 fill-orange-300",
    badgeBg: "bg-orange-50",
    badgeBorder: "border-orange-300",
    textColor: "text-orange-700",
    glowEffect: "shadow-sm shadow-orange-200",
    description: "3 ngày liên tục — Ngọn lửa nhỏ đã nhen nhóm!",
  },
  {
    tier: 2,
    minDays: 10,
    name: "Lửa Bập Bùng",
    emoji: "🔥",
    flameColor: "text-red-500 fill-red-300",
    badgeBg: "bg-red-50",
    badgeBorder: "border-red-300",
    textColor: "text-red-700",
    glowEffect: "shadow-md shadow-red-200",
    description: "10 ngày liên tục — Nhiệt huyết rực cháy!",
  },
  {
    tier: 3,
    minDays: 30,
    name: "Lửa Xanh Lam",
    emoji: "💙",
    flameColor: "text-cyan-500 fill-cyan-300",
    badgeBg: "bg-cyan-50",
    badgeBorder: "border-cyan-300",
    textColor: "text-cyan-700",
    glowEffect: "shadow-md shadow-cyan-300",
    description: "30 ngày liên tục — Ngọn lửa nhiệt lượng cao kiên định!",
  },
  {
    tier: 4,
    minDays: 60,
    name: "Lửa Tím Huyền Bí",
    emoji: "🔮",
    flameColor: "text-purple-500 fill-purple-300",
    badgeBg: "bg-purple-50",
    badgeBorder: "border-purple-300",
    textColor: "text-purple-700",
    glowEffect: "shadow-lg shadow-purple-300",
    description: "60 ngày liên tục — Quầng sáng tri thức huyền ảo!",
  },
  {
    tier: 5,
    minDays: 100,
    name: "Lửa Vàng Kim",
    emoji: "👑",
    flameColor: "text-amber-500 fill-yellow-300",
    badgeBg: "bg-gradient-to-r from-amber-50 to-yellow-100",
    badgeBorder: "border-amber-400",
    textColor: "text-amber-800",
    glowEffect: "shadow-lg shadow-amber-300 ring-2 ring-amber-300/50",
    description: "100 ngày liên tục — Vương miện học giả kiệt xuất!",
  },
  {
    tier: 6,
    minDays: 200,
    name: "Lửa Tinh Tú",
    emoji: "🌟",
    flameColor: "text-indigo-500 fill-pink-300",
    badgeBg: "bg-gradient-to-r from-indigo-50 via-purple-50 to-pink-50",
    badgeBorder: "border-indigo-400",
    textColor: "text-indigo-800",
    glowEffect: "shadow-xl shadow-indigo-300 ring-2 ring-indigo-400/50",
    description: "200 ngày liên tục — Tinh tú tỏa sáng rực rỡ!",
  },
  {
    tier: 7,
    minDays: 365,
    name: "Lửa Phượng Hoàng",
    emoji: "🐉",
    flameColor: "text-rose-600 fill-amber-300",
    badgeBg: "bg-gradient-to-r from-rose-100 via-amber-100 to-red-100",
    badgeBorder: "border-rose-500",
    textColor: "text-rose-900",
    glowEffect: "shadow-2xl shadow-rose-400 ring-4 ring-rose-400/60 animate-pulse",
    description: "365 ngày liên tục — Huyền thoại Phượng Hoàng Bất Diệt!",
  },
];

/**
 * Lấy thông tin mốc tiến hóa dựa trên số ngày streak.
 */
export function getStreakMilestone(days: number): StreakMilestoneInfo {
  if (days < 0) days = 0;
  for (let i = STREAK_MILESTONES.length - 1; i >= 0; i--) {
    if (days >= STREAK_MILESTONES[i].minDays) {
      return STREAK_MILESTONES[i];
    }
  }
  return STREAK_MILESTONES[0];
}

/**
 * Tìm mốc tiếp theo để người dùng phấn đấu
 */
export function getNextStreakMilestone(currentDays: number): {
  nextMilestone: StreakMilestoneInfo | null;
  daysRemaining: number;
} {
  const next = STREAK_MILESTONES.find((m) => m.minDays > currentDays);
  if (!next) {
    return { nextMilestone: null, daysRemaining: 0 };
  }
  return {
    nextMilestone: next,
    daysRemaining: next.minDays - currentDays,
  };
}
