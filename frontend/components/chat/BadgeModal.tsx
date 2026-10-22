"use client";

import React, { useState, useEffect } from "react";
import Lottie from "lottie-react";
import { Sparkles, X, Trophy, CheckCircle2, Lock } from "lucide-react";
import { cn } from "@/lib/utils";

export type BadgeType = "independence_100" | "streak_3" | "photo_solver" | "custom";

export interface BadgeItem {
  id: string;
  type: BadgeType;
  title: string;
  subtitle: string;
  description: string;
  iconUrl: string;
  unlocked: boolean;
  earnedAt?: string;
}

// 3 Huy hiệu chuẩn mực theo đặc tả US 7.2
export const DEFAULT_BADGES: BadgeItem[] = [
  {
    id: "independence_100",
    type: "independence_100",
    title: "Tự Lập Nhí",
    subtitle: "Đạt 100 điểm tự lập",
    description: "Hoàn thành trọn vẹn bài toán với 100 điểm tự lực, không cần đến bất kỳ gợi ý nào!",
    iconUrl: "/badges/orange_star_badge.svg",
    unlocked: false,
  },
  {
    id: "streak_3",
    type: "streak_3",
    title: "Kiên Trì Bền Bỉ",
    subtitle: "Học 3 ngày liên tiếp",
    description: "Duy trì ngọn lửa học tập liên tục trong 3 ngày không gián đoạn!",
    iconUrl: "/badges/orange_arm_badge.svg",
    unlocked: false,
  },
  {
    id: "photo_solver",
    type: "photo_solver",
    title: "Thám Tử Hình Ảnh",
    subtitle: "Giải bài toán bằng ảnh",
    description: "Tải lên và chinh phục thành công bài toán đầu tiên bằng ảnh chụp!",
    iconUrl: "/badges/orange_camera_badge.svg",
    unlocked: false,
  },
];

interface BadgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Huy hiệu vừa được mở khóa để chúc mừng (nếu có) */
  activeBadge?: Partial<BadgeItem>;
  /** Toàn bộ danh sách huy hiệu của học sinh (để xem tổng quan) */
  allBadges?: BadgeItem[];
  /** Đường dẫn file lottie pháo hoa tùy chỉnh (mặc định /lottie/fireworks.json hoặc /lottie/confetti.json) */
  fireworksLottieSrc?: string;
}

export function BadgeModal({
  isOpen,
  onClose,
  activeBadge,
  allBadges = DEFAULT_BADGES,
  fireworksLottieSrc = "/lottie/fireworks.json",
}: BadgeModalProps) {
  const [activeTab, setActiveTab] = useState<"unlock" | "collection">(
    activeBadge ? "unlock" : "collection"
  );
  const [fireworksAnimation, setFireworksAnimation] = useState<object | null>(null);

  // Huy hiệu hiển thị trọng tâm
  const currentBadge: BadgeItem = {
    id: activeBadge?.id || "independence_100",
    type: activeBadge?.type || "independence_100",
    title: activeBadge?.title || "Tự Lập Nhí",
    subtitle: activeBadge?.subtitle || "Đạt 100 điểm tự lập",
    description:
      activeBadge?.description ||
      "Bạn đã giải xong bài toán với 100 điểm tự lực hoàn toàn mà không cần xem gợi ý!",
    iconUrl: activeBadge?.iconUrl || "/badges/orange_star_badge.svg",
    unlocked: true,
    earnedAt: activeBadge?.earnedAt || "Hôm nay",
  };

  // Cập nhật tab khi activeBadge thay đổi
  useEffect(() => {
    if (activeBadge) {
      setActiveTab("unlock");
    } else {
      setActiveTab("collection");
    }
  }, [activeBadge]);

  // Tải file Lottie pháo hoa / confetti nếu có
  useEffect(() => {
    let isMounted = true;
    const loadFireworks = async () => {
      const candidates = [
        fireworksLottieSrc,
        "/lottie/confetti.json",
        "/lottie/fireworks.json",
        "/lottie/celebration.json",
      ];
      for (const src of candidates) {
        try {
          const res = await fetch(src);
          if (res.ok) {
            const data = await res.json();
            if (isMounted && data && (data.layers || data.v)) {
              setFireworksAnimation(data);
              return;
            }
          }
        } catch {
          // Bỏ qua và thử file tiếp theo
        }
      }
    };

    if (isOpen) {
      loadFireworks();
    }
    return () => {
      isMounted = false;
    };
  }, [isOpen, fireworksLottieSrc]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Lớp 1: Backdrop nền tối mờ */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
        onClick={onClose}
      />

      {/* Lớp 2: Lottie Pháo Hoa hoặc CSS Fireworks Fallback (pointer-events-none để KHÔNG CHẶN CLICK) */}
      <div className="fixed inset-0 pointer-events-none z-10 flex items-center justify-center overflow-hidden">
        {fireworksAnimation ? (
          <div className="w-full h-full max-w-4xl flex items-center justify-center">
            <Lottie
              animationData={fireworksAnimation}
              loop={true}
              autoplay={true}
              style={{ width: "100%", height: "100%" }}
            />
          </div>
        ) : (
          /* CSS Confetti & Sparkles Fallback: Tung hoa giấy rực rỡ */
          <div className="relative w-full h-full overflow-hidden">
            {Array.from({ length: 30 }).map((_, i) => {
              const colors = ["#F59E0B", "#F97316", "#EF4444", "#3B82F6", "#8B5CF6", "#10B981"];
              const randomColor = colors[i % colors.length];
              const randomLeft = `${(i * 3.3 + 5) % 95}%`;
              const randomDelay = `${(i * 0.12) % 2}s`;
              const randomDuration = `${2 + (i % 3) * 0.5}s`;
              const randomSize = 8 + (i % 6);

              return (
                <span
                  key={i}
                  className="absolute top-0 rounded-xs opacity-90 animate-fall"
                  style={{
                    left: randomLeft,
                    backgroundColor: randomColor,
                    width: `${randomSize}px`,
                    height: `${randomSize * 1.4}px`,
                    animationDelay: randomDelay,
                    animationDuration: randomDuration,
                    transform: `rotate(${i * 24}deg)`,
                  }}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Lớp 3: Hộp Thẻ Modal Huy Hiệu (z-20 nằm nổi trên cùng) */}
      <div className="relative z-20 bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border-2 border-[#F1CCA6] animate-modal-in text-center overflow-hidden">
        {/* Nút đóng góc phải */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors cursor-pointer z-30"
          aria-label="Đóng"
        >
          <X size={20} />
        </button>

        {/* Thanh chọn Tab: Chúc mừng vừa mở / Bộ sưu tập */}
        <div className="flex items-center justify-center gap-1.5 p-1 bg-[#F7ECE1] rounded-2xl mb-6 mx-auto w-fit">
          <button
            onClick={() => setActiveTab("unlock")}
            className={cn(
              "px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer",
              activeTab === "unlock"
                ? "bg-white text-stone-900 shadow-xs"
                : "text-stone-500 hover:text-stone-800"
            )}
          >
            Huy hiệu mới
          </button>
          <button
            onClick={() => setActiveTab("collection")}
            className={cn(
              "px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5",
              activeTab === "collection"
                ? "bg-white text-stone-900 shadow-xs"
                : "text-stone-500 hover:text-stone-800"
            )}
          >
            <Trophy size={13} className="text-[#C1762A]" />
            Bộ sưu tập
          </button>
        </div>

        {/* TAB 1: HIỂN THỊ CHÚC MỪNG MỞ KHÓA */}
        {activeTab === "unlock" && (
          <div className="flex flex-col items-center">
            {/* Khung hiển thị huy hiệu thanh lịch */}
            <div className="relative w-36 h-36 flex items-center justify-center my-3 rounded-3xl bg-[#F7ECE1]/50 border border-[#F1CCA6]/60">
              <div className="relative z-10 w-24 h-24 transform transition-transform hover:scale-105 duration-300">
                <img
                  src={currentBadge.iconUrl}
                  alt={currentBadge.title}
                  className="w-full h-full object-contain select-none"
                />
              </div>
            </div>

            {/* Nhãn trạng thái */}
            <span className="inline-block mt-2 px-3 py-1 bg-[#F7ECE1] text-[#8C4905] text-[11px] font-bold uppercase tracking-wider rounded-full border border-[#F1CCA6]">
              Mở khóa thành tựu
            </span>

            <h3 className="text-xl font-bold text-stone-900 mt-2.5 mb-1">
              {currentBadge.title.replace(/[^\p{L}\s]/gu, "").trim()}
            </h3>

            <p className="text-xs font-semibold text-[#C1762A] mb-2">
              {currentBadge.subtitle}
            </p>

            <p className="text-xs text-stone-600 max-w-xs leading-relaxed mb-6 font-normal">
              {currentBadge.description}
            </p>

            {/* Nút hành động chính chuẩn thiết kế SocraticKid */}
            <button
              onClick={onClose}
              className="w-full py-3 px-6 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-sm rounded-xl transition-colors cursor-pointer active:scale-[0.99]"
            >
              Tiếp tục học bài
            </button>
          </div>
        )}

        {/* TAB 2: BỘ SƯU TẬP 3 HUY HIỆU CỐT LÕI */}
        {activeTab === "collection" && (
          <div className="text-left">
            <div className="flex items-center justify-between mb-4 pb-2.5 border-b border-stone-100">
              <div>
                <h4 className="font-bold text-stone-900 text-sm">
                  Thành tích học tập
                </h4>
                <p className="text-[11px] text-stone-500 font-medium">
                  Cột mốc ghi nhận sự nỗ lực và tự lập của bạn
                </p>
              </div>
              <span className="text-xs font-semibold text-[#8C4905] bg-[#F7ECE1] px-2.5 py-1 rounded-full border border-[#F1CCA6]">
                {allBadges.filter((b) => b.unlocked).length}/{allBadges.length} đã đạt
              </span>
            </div>

            <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
              {allBadges.map((badge) => (
                <div
                  key={badge.id}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-2xl border transition-all",
                    badge.unlocked
                      ? "bg-white border-[#F1CCA6] shadow-xs"
                      : "bg-stone-50/70 border-stone-200/80 opacity-60"
                  )}
                >
                  <div className="w-11 h-11 shrink-0 relative flex items-center justify-center rounded-xl bg-[#F7ECE1]/60 p-1">
                    <img
                      src={badge.iconUrl}
                      alt={badge.title}
                      className={cn(
                        "w-full h-full object-contain",
                        !badge.unlocked && "grayscale contrast-50 opacity-40"
                      )}
                    />
                    {!badge.unlocked && (
                      <div className="absolute inset-0 bg-stone-900/20 backdrop-blur-[1px] rounded-xl flex items-center justify-center">
                        <Lock size={15} className="text-stone-700" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-bold text-xs text-stone-900 truncate">
                        {badge.title.replace(/[^\p{L}\s]/gu, "").trim()}
                      </span>
                      {badge.unlocked && (
                        <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
                      )}
                    </div>
                    <p className="text-[11px] text-[#C1762A] font-semibold">
                      {badge.subtitle}
                    </p>
                    <p className="text-[11px] text-stone-500 line-clamp-2 mt-0.5 leading-normal">
                      {badge.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={onClose}
              className="w-full mt-4 py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-800 font-semibold text-xs rounded-xl transition-colors cursor-pointer"
            >
              Đóng
            </button>
          </div>
        )}
      </div>

      {/* Keyframe animation cho hoa giấy rơi */}
      <style jsx>{`
        @keyframes fall {
          0% {
            transform: translateY(-20px) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(720deg);
            opacity: 0;
          }
        }
        .animate-fall {
          animation: fall linear forwards;
        }
      `}</style>
    </div>
  );
}

export default BadgeModal;
