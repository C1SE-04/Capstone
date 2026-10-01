"use client";

import { useEffect, useState, useRef } from "react";
import Lottie from "lottie-react";

// Types cho emotion
export type OwlEmotion =
  | "idle"
  | "thinking"
  | "suggesting"
  | "correct"
  | "incorrect";

interface AssistantOwlProps {
  emotion?: OwlEmotion;
}

// Map emotion -> đường dẫn file JSON trong public/
const EMOTION_SRC: Record<OwlEmotion, string> = {
  idle: "/lottie/owl_idle.json",
  thinking: "/lottie/owl_thinking.json",
  suggesting: "/lottie/owl_suggesting.json",
  correct: "/lottie/owl_correct.json",
  incorrect: "/lottie/owl_incorrect.json",
};

// Cache để không tải lại cùng một file nhiều lần trong session
const animationCache = new Map<string, object>();

export function AssistantOwl({ emotion = "idle" }: AssistantOwlProps) {
  // Animation đang được Lottie phát
  const [currentAnimation, setCurrentAnimation] = useState<object | null>(null);
  // Emotion đang được hiển thị (để so sánh tránh re-render vô ích)
  const [displayedEmotion, setDisplayedEmotion] = useState<OwlEmotion>(emotion);
  // Cờ fade-out: true = đang mờ dần trước khi chuyển animation mới
  const [isFading, setIsFading] = useState(false);
  // Ref để tránh race condition khi emotion đổi nhanh liên tục
  const latestEmotionRef = useRef<OwlEmotion>(emotion);

  // Hàm load animation từ file JSON (ưu tiên từ cache trước)
  const loadAnimation = async (
    targetEmotion: OwlEmotion,
  ): Promise<object | null> => {
    const src = EMOTION_SRC[targetEmotion];

    // Trả về ngay từ cache nếu đã tải rồi
    if (animationCache.has(src)) {
      return animationCache.get(src)!;
    }

    try {
      const res = await fetch(src);
      const data = await res.json();
      animationCache.set(src, data); // Lưu vào cache
      return data;
    } catch (err) {
      console.error("Failed to load owl animation:", err);
      return null;
    }
  };

  // Tải sẵn animation `idle` ngay khi component mount
  // → Cú xuất hiện ngay lập tức, không cần đợi người dùng gõ gì
  useEffect(() => {
    loadAnimation("idle").then((data) => {
      if (data) {
        setCurrentAnimation(data);
        setDisplayedEmotion("idle");
      }
    });
  }, []);

  // Khi `emotion` prop thay đổi → chuyển animation với hiệu ứng fade
  useEffect(() => {
    // Cập nhật ref để các async callback biết emotion mới nhất
    latestEmotionRef.current = emotion;

    // Nếu emotion không thay đổi, bỏ qua (tránh flicker)
    if (emotion === displayedEmotion) return;

    // Bước 1: Bắt đầu fade-out (opacity về 0 trong 200ms)
    const fadeTimer = setTimeout(() => {
      setIsFading(true);
    }, 0);

    // Bước 2: Sau 200ms, load animation mới và hiển thị lên
    const timer = setTimeout(async () => {
      // Nếu trong thời gian chờ, emotion đã đổi thêm lần nữa → bỏ qua lần này
      if (latestEmotionRef.current !== emotion) return;

      const data = await loadAnimation(emotion);

      // Kiểm tra lại sau await (race condition với async)
      if (latestEmotionRef.current !== emotion) return;

      if (data) {
        setCurrentAnimation(data);
        setDisplayedEmotion(emotion);
      }

      // Bước 3: Fade-in animation mới (opacity về 1)
      setIsFading(false);
    }, 200);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [emotion]);

  // Chưa có animation → không render (tránh layout shift)
  if (!currentAnimation) return null;

  return (
    <div
      className="block relative self-start mt-4 ml-2 md:ml-0 md:mt-0 md:self-end shrink-0 w-[62px] h-[62px] md:w-[90px] md:h-[90px] md:mb-6 pointer-events-none"
      style={{
        // Hiệu ứng fade: opacity đổi mượt mà trong 200ms khi chuyển trạng thái
        opacity: isFading ? 0 : 1,
        transition: "opacity 200ms ease-in-out",
      }}
    >
      <Lottie
        animationData={currentAnimation}
        loop={true}
        autoplay={true}
        style={{ width: "100%", height: "100%", display: "block" }}
      />
    </div>
  );
}
