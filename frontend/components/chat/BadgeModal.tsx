"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import Lottie from "lottie-react";
import { Sparkles, X, Trophy, CheckCircle2, Lock, ArrowRight, Award, Target } from "lucide-react";
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
  /** Yêu cầu nhiệm vụ để mở khóa cúp */
  requirement?: string;
}

// 3 Huy hiệu chuẩn mực theo đặc tả US 7.2 & Sprint 8 (T8.10)
export const DEFAULT_BADGES: BadgeItem[] = [
  {
    id: "independence_100",
    type: "independence_100",
    title: "Tự Lập Nhí",
    subtitle: "Đạt 100 điểm tự lập",
    description: "Hoàn thành trọn vẹn bài toán với 100 điểm tự lực hoàn toàn, không cần đến bất kỳ gợi ý nào từ AI!",
    requirement: "Giải đúng 1 bài toán đạt điểm tự lập tuyệt đối 100/100",
    iconUrl: "/badges/orange_star_badge.svg",
    unlocked: false,
  },
  {
    id: "streak_3",
    type: "streak_3",
    title: "Kiên Trì Bền Bỉ",
    subtitle: "Học 3 ngày liên tiếp",
    description: "Duy trì ngọn lửa học tập liên tục trong 3 ngày không gián đoạn để thắp sáng chuỗi lửa!",
    requirement: "Vào học bài và giải toán liên tục 3 ngày",
    iconUrl: "/badges/orange_arm_badge.svg",
    unlocked: false,
  },
  {
    id: "photo_solver",
    type: "photo_solver",
    title: "Thám Tử Hình Ảnh",
    subtitle: "Giải bài toán bằng ảnh",
    description: "Tải lên ảnh chụp bài toán và cùng AI chinh phục thành công lời giải đầu tiên!",
    requirement: "Gửi 1 ảnh đề bài vào khung chat và hoàn thành bài toán",
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
  /** Đường dẫn file lottie pháo hoa tùy chỉnh */
  fireworksLottieSrc?: string;
}

export function BadgeModal({
  isOpen,
  onClose,
  activeBadge,
  allBadges = DEFAULT_BADGES,
  fireworksLottieSrc = "/lottie/fireworks.json",
}: BadgeModalProps) {
  // Quản lý tab: nếu có activeBadge -> ưu tiên tab "unlock", ngược lại xem "collection"
  const [tabOverride, setTabOverride] = useState<"unlock" | "collection" | null>(null);
  const activeTab = tabOverride ?? (activeBadge ? "unlock" : "collection");

  // Chi tiết huy hiệu đang được chọn để xem trong bộ sưu tập (nếu có)
  const [selectedBadge, setSelectedBadge] = useState<BadgeItem | null>(null);

  // Lottie animation pháo hoa
  const [fireworksAnimation, setFireworksAnimation] = useState<object | null>(null);

  // Tính toán thống kê huy hiệu
  const unlockedBadges = allBadges.filter((b) => b.unlocked);
  const unlockedCount = unlockedBadges.length;
  const totalCount = allBadges.length;
  const isAllLocked = unlockedCount === 0;
  const progressPercent = Math.round((unlockedCount / (totalCount || 1)) * 100);

  // Chỉ kích hoạt hiệu ứng pháo hoa khi đang ăn mừng huy hiệu mới hoặc xem huy hiệu đã mở
  const isCelebrating = (activeTab === "unlock" && Boolean(activeBadge)) || (selectedBadge?.unlocked === true);

  // Tải file Lottie pháo hoa / confetti nếu có sự kiện chúc mừng
  useEffect(() => {
    let isMounted = true;
    if (!isOpen || !isCelebrating) return;

    const loadFireworks = async () => {
      const candidates = [
        fireworksLottieSrc,
        "/lottie/fireworks.json",
        "/lottie/confetti.json",
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

    loadFireworks();
    return () => {
      isMounted = false;
    };
  }, [isOpen, isCelebrating, fireworksLottieSrc]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
      {/* Lớp 1: Backdrop nền tối mờ */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300 animate-in fade-in"
        onClick={onClose}
      />

      {/* Lớp 2: Hiệu ứng pháo hoa & hoa giấy tung bay (CHỈ KHI ĂN MỪNG MỞ KHÓA, pointer-events-none KHÔNG CHẶN CLICK) */}
      {isCelebrating && (
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
            /* Fallback CSS Confetti */
            <div className="relative w-full h-full overflow-hidden">
              {Array.from({ length: 32 }).map((_, i) => {
                const colors = ["#F59E0B", "#F97316", "#EF4444", "#3B82F6", "#8B5CF6", "#10B981"];
                const randomColor = colors[i % colors.length];
                const randomLeft = `${(i * 3.1 + 4) % 94}%`;
                const randomDelay = `${(i * 0.1) % 1.8}s`;
                const randomDuration = `${2.2 + (i % 3) * 0.4}s`;
                const randomSize = 8 + (i % 5);

                return (
                  <span
                    key={i}
                    className="absolute top-0 rounded-xs opacity-90 animate-fall"
                    style={{
                      left: randomLeft,
                      backgroundColor: randomColor,
                      width: `${randomSize}px`,
                      height: `${randomSize * 1.5}px`,
                      animationDelay: randomDelay,
                      animationDuration: randomDuration,
                      transform: `rotate(${i * 25}deg)`,
                    }}
                  />
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Lớp 3: Hộp Thẻ Modal Huy Hiệu */}
      <div className="relative z-20 bg-white rounded-3xl p-5 sm:p-7 max-w-lg w-full shadow-2xl border-2 border-[#F1CCA6] animate-modal-in text-center overflow-hidden flex flex-col max-h-[90vh]">
        {/* Nút đóng góc phải */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-stone-400 hover:text-stone-700 hover:bg-stone-100 rounded-full transition-colors cursor-pointer z-30"
          aria-label="Đóng"
        >
          <X size={20} />
        </button>

        {/* Thanh chuyển Tab (Chỉ hiển thị khi có activeBadge đang ăn mừng) */}
        {activeBadge ? (
          <div className="flex items-center justify-center gap-1.5 p-1 bg-[#F7ECE1] rounded-2xl mb-4 mx-auto w-fit">
            <button
              onClick={() => {
                setTabOverride("unlock");
                setSelectedBadge(null);
              }}
              className={cn(
                "px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5",
                activeTab === "unlock"
                  ? "bg-white text-stone-900 shadow-xs"
                  : "text-stone-500 hover:text-stone-800"
              )}
            >
              <Sparkles size={13} className="text-[#C1762A]" />
              Huy hiệu mới
            </button>
            <button
              onClick={() => {
                setTabOverride("collection");
                setSelectedBadge(null);
              }}
              className={cn(
                "px-4 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5",
                activeTab === "collection"
                  ? "bg-white text-stone-900 shadow-xs"
                  : "text-stone-500 hover:text-stone-800"
              )}
            >
              <Trophy size={13} className="text-[#C1762A]" />
              Bộ sưu tập ({unlockedCount}/{totalCount})
            </button>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-xl bg-[#F7ECE1] flex items-center justify-center text-[#C1762A]">
              <Trophy size={18} />
            </div>
            <h3 className="text-lg font-bold text-stone-900">
              Phòng Huy Hiệu
            </h3>
          </div>
        )}

        {/* NỘI DUNG CHÍNH (Cuộn được nếu màn hình nhỏ) */}
        <div className="overflow-y-auto px-1 flex-1">
          {/* TAB 1: ĂN MỪNG MỞ KHÓA HUY HIỆU MỚI (CHỈ KHI CÓ activeBadge) */}
          {activeTab === "unlock" && activeBadge && (
            <div className="flex flex-col items-center py-2">
              <span className="inline-flex items-center gap-1.5 px-3.5 py-1 bg-[#F7ECE1] text-[#8C4905] text-[11px] font-bold uppercase tracking-wider rounded-full border border-[#F1CCA6] shadow-xs">
                <Sparkles size={13} className="text-[#C1762A] animate-pulse" />
                Mở khóa thành tựu mới!
              </span>

              {/* Khung cúp sáng rực rỡ */}
              <div className="relative w-36 h-36 flex items-center justify-center my-4 rounded-3xl bg-gradient-to-b from-[#FFF7ED] to-[#F7ECE1] border-2 border-[#F1CCA6] shadow-lg shadow-amber-500/10">
                <div className="absolute inset-0 rounded-3xl bg-amber-400/15 blur-xl animate-pulse" />
                <div className="relative z-10 w-24 h-24 transform transition-transform hover:scale-110 duration-300">
                  <Image
                    src={activeBadge.iconUrl || "/badges/orange_star_badge.svg"}
                    alt={activeBadge.title || "Huy hiệu"}
                    width={96}
                    height={96}
                    className="w-full h-full object-contain drop-shadow-md select-none"
                    priority
                  />
                </div>
              </div>

              <h4 className="text-2xl font-extrabold text-stone-900 mb-1 tracking-tight">
                {activeBadge.title?.replace(/[^\p{L}\s]/gu, "").trim()}
              </h4>

              <p className="text-xs font-bold text-[#C1762A] mb-2 px-3 py-0.5 rounded-full bg-amber-50 border border-amber-200/60">
                {activeBadge.subtitle}
              </p>

              <p className="text-xs text-stone-600 max-w-sm leading-relaxed mb-5 font-normal">
                {activeBadge.description || "Chúc mừng bạn đã hoàn thành xuất sắc mục tiêu học tập!"}
              </p>

              <div className="w-full flex flex-col sm:flex-row gap-2 pt-2">
                <button
                  onClick={() => {
                    setTabOverride("collection");
                    setSelectedBadge(null);
                  }}
                  className="flex-1 py-2.5 px-4 bg-stone-100 hover:bg-stone-200 text-stone-800 font-semibold text-xs rounded-xl transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <Trophy size={14} className="text-[#C1762A]" />
                  Xem bộ sưu tập
                </button>
                <button
                  onClick={onClose}
                  className="flex-1 py-2.5 px-4 bg-[#C1762A] hover:bg-[#8C4905] text-white font-bold text-xs rounded-xl transition-colors cursor-pointer shadow-md shadow-amber-900/10 active:scale-[0.99]"
                >
                  Tiếp tục học bài
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: BỘ SƯU TẬP HUY HIỆU */}
          {activeTab === "collection" && (
            <div className="text-left space-y-4">
              {/* CHI TIẾT 1 HUY HIỆU ĐƯỢC CHỌN (POPUP XEM CHI TIẾT) */}
              {selectedBadge ? (
                <div className="p-4 rounded-2xl bg-stone-50 border border-[#F1CCA6] transition-all animate-in fade-in zoom-in-95">
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wide flex items-center gap-1">
                      <Award size={13} className="text-[#C1762A]" />
                      Chi tiết huy hiệu
                    </span>
                    <button
                      onClick={() => setSelectedBadge(null)}
                      className="text-stone-400 hover:text-stone-700 text-xs font-semibold px-2 py-0.5 rounded-md hover:bg-stone-200/60 cursor-pointer"
                    >
                      ← Quay lại
                    </button>
                  </div>

                  <div className="flex items-center gap-3.5 mb-3">
                    <div
                      className={cn(
                        "w-16 h-16 rounded-2xl flex items-center justify-center p-2 relative shrink-0 border",
                        selectedBadge.unlocked
                          ? "bg-[#FFF7ED] border-[#F1CCA6] shadow-sm"
                          : "bg-stone-100 border-stone-200"
                      )}
                    >
                      <Image
                        src={selectedBadge.iconUrl}
                        alt={selectedBadge.title}
                        width={60}
                        height={60}
                        className={cn(
                          "w-full h-full object-contain",
                          !selectedBadge.unlocked && "grayscale contrast-50 opacity-40"
                        )}
                      />
                      {!selectedBadge.unlocked && (
                        <div className="absolute inset-0 bg-stone-900/15 backdrop-blur-[1px] rounded-2xl flex items-center justify-center">
                          <Lock size={18} className="text-stone-700" />
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="font-bold text-stone-900 text-sm truncate">
                          {selectedBadge.title.replace(/[^\p{L}\s]/gu, "").trim()}
                        </h4>
                        {selectedBadge.unlocked ? (
                          <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                            <CheckCircle2 size={11} /> Đã đạt
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-stone-600 bg-stone-200/80 px-2 py-0.5 rounded-full">
                            <Lock size={10} /> Đang khóa (0/1)
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-[#C1762A] mt-0.5">
                        {selectedBadge.subtitle}
                      </p>
                      {selectedBadge.unlocked && selectedBadge.earnedAt && (
                        <p className="text-[10px] text-stone-500 mt-0.5">
                          Ngày đạt: {selectedBadge.earnedAt}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 rounded-xl bg-white border border-stone-200/80">
                      <p className="font-semibold text-stone-800 mb-0.5">Ý nghĩa:</p>
                      <p className="text-stone-600 leading-relaxed font-normal">
                        {selectedBadge.description}
                      </p>
                    </div>

                    {selectedBadge.requirement && (
                      <div className="p-2.5 rounded-xl bg-amber-50/70 border border-amber-200/70 flex items-start gap-2">
                        <Target size={14} className="text-[#C1762A] shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-[#8C4905]">
                            {selectedBadge.unlocked ? "Nhiệm vụ đã hoàn thành:" : "Cách để mở khóa:"}
                          </p>
                          <p className="text-stone-700 font-normal">
                            {selectedBadge.requirement}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ) : null}

              {/* THANH TIẾN ĐỘ THÀNH TỰU GỌN GÀNG */}
              {!selectedBadge && (
                <div className="p-3.5 bg-gradient-to-r from-amber-50/60 to-white rounded-2xl border border-[#F1CCA6] flex items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <Sparkles size={14} className="text-[#C1762A]" />
                      <h4 className="font-bold text-stone-900 text-xs">
                        {isAllLocked ? "Bắt đầu hành trình học tập" : "Tiến độ thành tựu của bạn"}
                      </h4>
                    </div>
                    <p className="text-[11px] text-stone-500 mt-0.5">
                      {isAllLocked
                        ? "Giải toán và giữ chuỗi học tập để mở khóa cúp đầu tiên!"
                        : `Đã chinh phục ${unlockedCount} trên tổng số ${totalCount} danh hiệu`}
                    </p>
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-extrabold text-[#8C4905] bg-[#F7ECE1] px-2.5 py-1 rounded-full border border-[#F1CCA6]">
                      {unlockedCount}/{totalCount} ({progressPercent}%)
                    </span>
                  </div>
                </div>
              )}

              {/* DANH SÁCH TẤT CẢ CÁC HUY HIỆU (KHÓA VS MỞ) */}
              {!selectedBadge && (
                <div>
                  <div className="flex items-center justify-between mb-2 px-1">
                    <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider">
                      Danh sách huy hiệu ({allBadges.length})
                    </span>
                    <span className="text-[11px] text-stone-400">
                      Chạm vào để xem cách mở khóa
                    </span>
                  </div>

                  <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1">
                    {allBadges.map((badge) => {
                      const isUnlocked = badge.unlocked;

                      return (
                        <div
                          key={badge.id}
                          onClick={() => setSelectedBadge(badge)}
                          className={cn(
                            "flex items-center gap-3 p-3 rounded-2xl border transition-all cursor-pointer group",
                            isUnlocked
                              ? "bg-white border-[#F1CCA6] shadow-xs hover:border-amber-400 hover:shadow-md"
                              : "bg-stone-50/80 border-stone-200 opacity-70 hover:opacity-100 hover:bg-stone-100/70"
                          )}
                        >
                          {/* Icon Cúp: Mở (sắc nét rực rỡ) vs Khóa (xám mờ grayscale + ổ khóa) */}
                          <div
                            className={cn(
                              "w-12 h-12 shrink-0 relative flex items-center justify-center rounded-2xl p-1.5 transition-transform group-hover:scale-105",
                              isUnlocked
                                ? "bg-gradient-to-b from-[#FFF7ED] to-[#F7ECE1] border border-[#F1CCA6]"
                                : "bg-stone-100 border border-stone-200"
                            )}
                          >
                            <Image
                              src={badge.iconUrl}
                              alt={badge.title}
                              width={44}
                              height={44}
                              className={cn(
                                "w-full h-full object-contain",
                                !isUnlocked && "grayscale contrast-50 opacity-40"
                              )}
                            />
                            {!isUnlocked && (
                              <div className="absolute inset-0 bg-stone-900/15 backdrop-blur-[1px] rounded-2xl flex items-center justify-center">
                                <Lock size={15} className="text-stone-700" />
                              </div>
                            )}
                          </div>

                          {/* Thông tin cúp */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-bold text-xs text-stone-900 truncate">
                                {badge.title.replace(/[^\p{L}\s]/gu, "").trim()}
                              </span>
                              {isUnlocked ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 shrink-0 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-200">
                                  <CheckCircle2 size={11} /> Đã mở
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-stone-500 shrink-0 bg-stone-200/70 px-1.5 py-0.5 rounded-full">
                                  <Lock size={10} /> 0/1
                                </span>
                              )}
                            </div>

                            <p className="text-[11px] text-[#C1762A] font-semibold truncate">
                              {badge.subtitle}
                            </p>

                            <p className="text-[11px] text-stone-500 line-clamp-1 mt-0.5 font-normal">
                              {isUnlocked ? badge.description : (badge.requirement || badge.description)}
                            </p>
                          </div>

                          <ArrowRight
                            size={14}
                            className="text-stone-300 group-hover:text-[#C1762A] group-hover:translate-x-0.5 transition-all shrink-0"
                          />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Nút đóng chân modal */}
              <div className="pt-2">
                <button
                  onClick={onClose}
                  className="w-full py-2.5 bg-stone-100 hover:bg-stone-200 text-stone-800 font-semibold text-xs rounded-xl transition-colors cursor-pointer"
                >
                  Đóng cửa sổ
                </button>
              </div>
            </div>
          )}
        </div>
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
