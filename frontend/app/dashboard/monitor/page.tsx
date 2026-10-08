"use client";

/**
 * File: app/dashboard/monitor/page.tsx
 * Mô tả: Trang chính của Dashboard Phụ huynh (MONITOR).
 * - Hiển thị thông tin tổng quan về học sinh đang được chọn.
 * - Các thẻ thống kê: lớp học, số buổi học, môn học gần nhất.
 * - Phần lịch sử chat gần nhất (mock data có comment thay bằng API thật).
 *
 * ⚠️ Mock data — Thay bằng API thật khi BE có endpoint:
 *   GET /family/students/{student_id}/summary
 */

import { useMonitorContext } from "./layout";
import { StatCard } from "@/components/monitor/StatCard";
import {
  BookOpen,
  MessageCircle,
  GraduationCap,
  Clock,
  UserPlus,
  TrendingUp,
} from "lucide-react";
import { useRouter } from "next/navigation";

// --- MOCK DATA ---
// Xoá và thay bằng fetch API thật khi BE sẵn sàng
const MOCK_STUDENT_STATS: Record<
  string,
  {
    grade: number;
    totalSessions: number;
    lastSubject: string;
    lastActive: string;
    recentChats: { date: string; subject: string; summary: string }[];
  }
> = {
  default: {
    grade: 6,
    totalSessions: 24,
    lastSubject: "Toán học",
    lastActive: "Hôm nay, 20:15",
    recentChats: [
      {
        date: "07/10/2026",
        subject: "Toán",
        summary: "Ôn tập phân số và số thập phân lớp 6",
      },
      {
        date: "06/10/2026",
        subject: "Tiếng Việt",
        summary: "Phân tích văn bản truyện ngắn",
      },
      {
        date: "05/10/2026",
        subject: "Khoa học",
        summary: "Tìm hiểu về hệ mặt trời",
      },
    ],
  },
};

export default function MonitorPage() {
  const { selectedStudent } = useMonitorContext();
  const router = useRouter();

  // Nếu chưa chọn con nào
  if (!selectedStudent) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-5 text-center">
        <div className="w-20 h-20 bg-[#F1CCA6] rounded-3xl flex items-center justify-center">
          <UserPlus size={36} className="text-[#C1762A]" />
        </div>
        <h2 className="text-2xl font-extrabold text-[#8C4905]">
          Chưa có học sinh nào
        </h2>
        <p className="text-[#C1762A] max-w-xs leading-relaxed">
          Nhấn <span className="font-bold text-[#8C4905]">&quot;Thêm con&quot;</span> ở
          thanh bên trái để liên kết với tài khoản học sinh của con.
        </p>
      </div>
    );
  }

  // Lấy mock data theo student_id, hoặc dùng default
  const stats =
    MOCK_STUDENT_STATS[selectedStudent.student_id] ?? MOCK_STUDENT_STATS["default"];

  /*
  // --- KHI CÓ API THẬT, THAY BẰNG ĐOẠN NÀY ---
  // const [stats, setStats] = useState(null);
  // useEffect(() => {
  //   const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
  //   fetch(`${backendUrl}/family/students/${selectedStudent.student_id}/summary`, {
  //     headers: { Authorization: `Bearer ${session?.access_token}` },
  //   })
  //     .then(r => r.json())
  //     .then(setStats);
  // }, [selectedStudent.student_id]);
  */

  const displayName =
    selectedStudent.nickname || selectedStudent.email.split("@")[0];

  return (
    <div className="max-w-4xl mx-auto animate-in fade-in duration-500">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-[#C1762A] rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-md">
            {displayName.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-[#8C4905] tracking-tight leading-none">
              {displayName}
            </h1>
            <p className="text-sm text-[#C1762A] mt-1">{selectedStudent.email}</p>
          </div>
        </div>
        <p className="text-[#C1762A] font-medium mt-3">
          Tổng quan hoạt động học tập của con bạn
        </p>
      </div>

      {/* Thẻ thống kê */}
      <section className="mb-8">
        <h2 className="text-lg font-bold text-[#8C4905] mb-4 flex items-center gap-2">
          <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
          Thống kê nhanh
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard
            icon={<GraduationCap size={22} className="text-[#C1762A]" />}
            label="Lớp học"
            value={`Lớp ${stats.grade}`}
            sub="Cấp THCS"
          />
          <StatCard
            icon={<MessageCircle size={22} className="text-[#C1762A]" />}
            label="Số buổi học"
            value={stats.totalSessions}
            sub="Tổng cộng"
          />
          <StatCard
            icon={<BookOpen size={22} className="text-[#C1762A]" />}
            label="Môn gần nhất"
            value={stats.lastSubject}
            sub={stats.lastActive}
          />
        </div>
      </section>

      {/* Lịch sử chat gần nhất */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-[#8C4905] flex items-center gap-2">
            <span className="w-1.5 h-6 bg-[#C1762A] rounded-full inline-block" />
            Buổi học gần đây
          </h2>
          <span className="text-xs text-[#C1762A] bg-[#F1CCA6] px-3 py-1 rounded-full font-bold">
            Mock data
          </span>
        </div>

        {stats.recentChats.length === 0 ? (
          <div className="bg-white rounded-2xl border border-[#F1CCA6] p-8 text-center">
            <Clock size={32} className="text-[#C1762A]/40 mx-auto mb-3" />
            <p className="text-[#8C4905]/60 font-medium">Chưa có buổi học nào.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {stats.recentChats.map((chat, idx) => (
              <div
                key={idx}
                className="bg-white rounded-2xl border border-[#F1CCA6] p-5 flex items-start gap-4 hover:shadow-md transition-shadow"
              >
                {/* Icon môn */}
                <div className="w-10 h-10 bg-[#F7ECE1] rounded-xl flex items-center justify-center shrink-0">
                  <TrendingUp size={18} className="text-[#C1762A]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-[#C1762A] bg-[#F7ECE1] px-2 py-0.5 rounded-full">
                      {chat.subject}
                    </span>
                    <span className="text-xs text-[#8C4905]/50">{chat.date}</span>
                  </div>
                  <p className="text-sm text-[#8C4905] font-medium leading-relaxed">
                    {chat.summary}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Ghi chú mock */}
        <p className="mt-4 text-xs text-[#C1762A]/60 text-center">
          ⚠️ Dữ liệu mẫu — Sẽ hiển thị lịch sử thật khi BE có{" "}
          <code className="font-mono bg-[#F1CCA6] px-1 rounded">
            GET /family/students/{"{id}"}/summary
          </code>
        </p>
      </section>
    </div>
  );
}
