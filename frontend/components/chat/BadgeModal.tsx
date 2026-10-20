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
    title: "Tự Lập Nhí 🏅",
    subtitle: "Đạt 100 điểm tự lập",
    description: "Hoàn thành trọn vẹn bài toán với 100 điểm tự lực, không cần đến bất kỳ gợi ý nào!",
    iconUrl: "/badges/orange_star_badge.svg",
    unlocked: true,
  },
  {
    id: "streak_3",
    type: "streak_3",
    title: "Kiên Trì Bền Bỉ 🔥",
    subtitle: "Học 3 ngày liên tiếp",
    description: "Duy trì ngọn lửa học tập liên tục trong 3 ngày không gián đoạn!",
    iconUrl: "/badges/orange_star_badge.svg",
    unlocked: false,
  },
  {
    id: "photo_solver",
    type: "photo_solver",
    title: "Thám Tử Hình Ảnh 📸",
    subtitle: "Giải bài toán bằng ảnh",
    description: "Tải lên và chinh phục thành công bài toán đầu tiên bằng ảnh chụp!",
    iconUrl: "/badges/orange_star_badge.svg",
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
    title: activeBadge?.title || "Tự Lập Nhí 🏅",
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
      <div className="relative z-20 bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full shadow-2xl border-2 border-[#F1CCA6] animate-in zoom-in-95 duration-300 text-center overflow-hidden">
        {/* Nút đóng góc phải */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors cursor-pointer z-30"
          aria-label="Đóng"
        >
          <X size={20} />
        </button>

        {/* Thanh chọn Tab: Chúc mừng vừa mở / Bộ sưu tập */}
        <div className="flex items-center justify-center gap-2 p-1 bg-[#F7ECE1] rounded-2xl mb-6 mx-auto w-fit">
          <button
            onClick={() => setActiveTab("unlock")}
            className={cn(
              "px-4 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer",
              activeTab === "unlock"
                ? "bg-white text-[#C1762A] shadow-xs"
                : "text-[#8C4905]/70 hover:text-[#8C4905]"
            )}
          >
            Huy hiệu mới 🎉
          </button>
          <button
            onClick={() => setActiveTab("collection")}
            className={cn(
              "px-4 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5",
              activeTab === "collection"
                ? "bg-white text-[#C1762A] shadow-xs"
                : "text-[#8C4905]/70 hover:text-[#8C4905]"
            )}
          >
            <Trophy size={13} />
            Bộ sưu tập
          </button>
        </div>

        {/* TAB 1: HIỂN THỊ CHÚC MỪNG MỞ KHÓA */}
        {activeTab === "unlock" && (
          <div className="flex flex-col items-center">
            {/* Vầng hào quang ánh sáng xoay tròn phía sau Huy hiệu */}
            <div className="relative w-40 h-40 flex items-center justify-center my-2">
              {/* Sunburst Glow Halo */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-yellow-300/40 via-amber-400/30 to-orange-500/20 blur-xl animate-pulse" />
              
              {/* Vòng tia sáng */}
              <div
                className="absolute inset-[-12px] rounded-full border-2 border-dashed border-amber-300/60 animate-spin"
                style={{ animationDuration: "14s" }}
              />

              {/* Ngôi sao lấp lánh xung quanh */}
              <Sparkles
                size={24}
                className="absolute top-2 left-3 text-amber-400 animate-bounce"
                style={{ animationDelay: "0.2s" }}
              />
              <Sparkles
                size={20}
                className="absolute bottom-3 right-4 text-orange-400 animate-bounce"
                style={{ animationDelay: "0.5s" }}
              />

              {/* Hình Huy Hiệu SVG với hiệu ứng Pop-in Scale */}
              <div className="relative z-10 w-32 h-32 transform transition-transform hover:scale-105 duration-300 drop-shadow-[0_10px_20px_rgba(230,81,0,0.35)] animate-in zoom-in-50 duration-500">
                <img
                  src={currentBadge.iconUrl}
                  alt={currentBadge.title}
                  className="w-full h-full object-contain select-none"
                />
              </div>
            </div>

            {/* Tiêu đề chúc mừng */}
            <span className="inline-block mt-2 px-3 py-1 bg-amber-100 text-[#C1762A] text-xs font-black uppercase tracking-wider rounded-full border border-amber-200">
              Mở Khóa Thành Tựu Mới
            </span>

            <h3 className="text-2xl font-black text-[#8C4905] mt-2 mb-1">
              {currentBadge.title}
            </h3>

            <p className="text-sm font-bold text-[#C1762A] mb-2">
              {currentBadge.subtitle}
            </p>

            <p className="text-xs text-gray-600 max-w-xs leading-relaxed mb-6">
              {currentBadge.description}
            </p>

            {/* Nút hành động chính */}
            <button
              onClick={onClose}
              className="w-full py-3.5 px-6 bg-gradient-to-r from-[#C1762A] via-[#E65100] to-[#F7AD62] hover:from-[#A45E1B] hover:to-[#E65100] text-white font-black text-sm rounded-2xl shadow-lg hover:shadow-orange-200/80 transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
            >
              Tuyệt vời, tiếp tục học!
            </button>
          </div>
        )}

        {/* TAB 2: BỘ SƯU TẬP 3 HUY HIỆU CỐT LÕI */}
        {activeTab === "collection" && (
          <div className="text-left">
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-gray-100">
              <h4 className="font-black text-[#8C4905] text-sm">
                Danh hiệu Gamification SocraticKid
              </h4>
              <span className="text-xs font-bold text-[#C1762A] bg-orange-50 px-2 py-0.5 rounded-full border border-orange-200">
                {allBadges.filter((b) => b.unlocked).length}/{allBadges.length} đã đạt
              </span>
            </div>

            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {allBadges.map((badge) => (
                <div
                  key={badge.id}
                  className={cn(
                    "flex items-center gap-3 p-3 rounded-2xl border transition-all",
                    badge.unlocked
                      ? "bg-gradient-to-r from-amber-500/10 to-orange-500/5 border-[#F7AD62]/60 shadow-2xs"
                      : "bg-gray-50/80 border-gray-200 opacity-60"
                  )}
                >
                  <div className="w-12 h-12 shrink-0 relative flex items-center justify-center">
                    <img
                      src={badge.iconUrl}
                      alt={badge.title}
                      className={cn(
                        "w-full h-full object-contain",
                        !badge.unlocked && "grayscale contrast-75"
                      )}
                    />
                    {!badge.unlocked && (
                      <div className="absolute inset-0 bg-black/30 rounded-full flex items-center justify-center">
                        <Lock size={16} className="text-white drop-shadow" />
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-black text-xs text-[#8C4905] truncate">
                        {badge.title}
                      </span>
                      {badge.unlocked && (
                        <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                      )}
                    </div>
                    <p className="text-[11px] text-[#C1762A] font-semibold">
                      {badge.subtitle}
                    </p>
                    <p className="text-[10px] text-gray-500 line-clamp-2 mt-0.5">
                      {badge.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={onClose}
              className="w-full mt-5 py-2.5 bg-[#F7ECE1] hover:bg-[#F1CCA6] text-[#8C4905] font-bold text-xs rounded-xl transition-colors cursor-pointer"
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
