"use client";

import { useEffect, useState } from "react";
import Lottie from "lottie-react";

// Types cho emotion
export type OwlEmotion = "idle" | "thinking" | "suggesting" | "correct" | "incorrect";

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

export function AssistantOwl({ emotion = "idle" }: AssistantOwlProps) {
  const [animationData, setAnimationData] = useState<object | null>(null);

  useEffect(() => {
    const src = EMOTION_SRC[emotion];
    fetch(src)
      .then((res) => res.json())
      .then((data) => setAnimationData(data))
      .catch((err) => console.error("Failed to load owl animation:", err));
  }, [emotion]);

  if (!animationData) return null;

  return (
    <div
      className="fixed bottom-0 right-0 z-50 pointer-events-none"
      style={{ width: "clamp(120px, 18vw, 240px)" }}
    >
      <Lottie
        animationData={animationData}
        loop={true}
        autoplay={true}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
