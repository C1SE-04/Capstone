# 📘 Hướng Dẫn Thực Hiện Task: `[FE] Viết code để con cú biết thay đổi cử động dựa vào kết quả từ server trả về`

> **Sprint 4 – US 4.2: Cú Socratic sinh động**
> **Người thực hiện:** [Bảo] – Trùm Frontend
> **Ước tính thời gian:** 4 giờ

---

## 1. 🔍 Phân Tích Nhiệm Vụ

### Task này làm gì?

Hiện tại con cú (`AssistantOwl`) đã được **gắn lên màn hình** (task T2.1 của Bảo đã làm), nhưng cử động của nó **chưa được kết nối với dữ liệu thật từ server**. Nhiệm vụ này yêu cầu:

> **"Bắt" con cú nhìn vào cái cờ cảm xúc (`emotion`) mà server trả về trong JSON, rồi tự động đổi hoạt hình tương ứng một cách mượt mà.**

### Luồng hoạt động hiện tại (đã có)

```
Học sinh gõ tin nhắn
   ↓
ChatPage.tsx gọi fetch đến /chat/orchestrator (Backend)
   ↓
Backend stream về từng dòng SSE: data: {"text": "...", "emotion": "correct"}
   ↓
ChatPage nhận stream → chỉ lưu phần `text` vào messages
   ↓
ChatWindow đọc messages → hiển thị bong bóng chat
   ↓
AssistantOwl nhận prop `emotion` → phát hoạt hình
```

### Vấn đề hiện tại

Nhìn vào `page.tsx` (dòng 342-357), khi nhận stream từ server:

```ts
// ⚠️ HIỆN TẠI: chỉ lưu text, BỎ QUA emotion
if (dataObj.text) {
  aiText += dataObj.text;
  setConversations((prev) =>
    prev.map((c) =>
      c.id === targetConversationId
        ? {
            ...c,
            messages: c.messages.map((m) =>
              m.id === botMessageId ? { ...m, content: aiText } : m
              //                              ^^^^^^^^^^^^^^^^^^
              //              Không có `emotion` ở đây!
            ),
          }
        : c
    )
  );
}
```

Và `ChatWindow.tsx` (dòng 51-54) thì **đọc emotion từ tin nhắn cuối cùng**:

```ts
const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
if (lastAssistantMsg && lastAssistantMsg.emotion) {
  currentEmotion = lastAssistantMsg.emotion as OwlEmotion;
}
```

Nhưng vì `emotion` chưa bao giờ được gán vào message object → con cú **luôn ở trạng thái `idle`**, không bao giờ thay đổi theo phản hồi của server.

### Những gì cần làm trong task này

| # | Việc cần làm | File liên quan |
|---|---|---|
| 1 | **Parse trường `emotion`** từ SSE stream | `app/dashboard/chat/page.tsx` |
| 2 | **Lưu `emotion` vào message object** khi AI trả lời xong | `app/dashboard/chat/page.tsx` |
| 3 | **Xử lý transition mượt mà** giữa các trạng thái cú | `components/chat/AssistantOwl.tsx` |
| 4 | **Xử lý `triggerSilentReexplain`** (luồng "Chưa hiểu") cũng phải gán emotion | `app/dashboard/chat/page.tsx` |

> **Lưu ý:** Không cần sửa `types/chat.ts` (field `emotion` đã có sẵn), không cần sửa `ChatWindow.tsx` (logic đọc emotion đã đúng), không cần cài thêm thư viện nào.

---

## 2. 🌿 Đặt Tên Branch

Làm theo quy ước của team (feature branch từ `dev`):

```bash
git checkout dev
git pull origin dev
git checkout -b feat/us4.2-owl-emotion-state
```

> **Giải thích:** `feat/` = tính năng mới, `us4.2` = User Story 4.2, `owl-emotion-state` = mô tả ngắn gọn.

---

## 3. 📋 Kiểm Tra Thư Viện (Không Cần Cài Thêm)

Mở `package.json` kiểm tra thư viện đã có sẵn:

```json
"lottie-react": "^2.4.0"   ✅ Đã có
```

Thư viện `lottie-react` đã được cài từ task T2.1 của Bảo. File hoạt hình cú cũng đã đủ 5 trạng thái trong `public/lottie/`:

```
public/lottie/
├── owl_idle.json        ✅ (đứng im, mặc định)
├── owl_thinking.json    ✅ (đang suy nghĩ)
├── owl_suggesting.json  ✅ (gợi ý)
├── owl_correct.json     ✅ (trả lời đúng)
└── owl_incorrect.json   ✅ (trả lời sai)
```

---

## 4. 🏗️ Phân Tích Code Hiện Tại

### 4.1. `types/chat.ts` – Đã sẵn sàng

```ts
// File: frontend/types/chat.ts
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "sending" | "sent" | "error";
  emotion?: "idle" | "thinking" | "suggesting" | "correct" | "incorrect" | string; // ✅ đã có
}
```

Field `emotion` trong `Message` interface đã tồn tại, không cần sửa.

### 4.2. `AssistantOwl.tsx` – Cần nâng cấp transition

```tsx
// File: frontend/components/chat/AssistantOwl.tsx (HIỆN TẠI)
export function AssistantOwl({ emotion = "idle" }: AssistantOwlProps) {
  const [animationData, setAnimationData] = useState<object | null>(null);

  useEffect(() => {
    const src = EMOTION_SRC[emotion];
    fetch(src)
      .then((res) => res.json())
      .then((data) => setAnimationData(data))  // ← Load file Lottie mới
      .catch((err) => console.error("Failed to load owl animation:", err));
  }, [emotion]);

  if (!animationData) return null;  // ← Khi đang tải → cú biến mất

  return (
    <div className="fixed bottom-0 right-0 z-50 pointer-events-none"
         style={{ width: "clamp(120px, 18vw, 240px)" }}>
      <Lottie animationData={animationData} loop={true} autoplay={true} ... />
    </div>
  );
}
```

**Vấn đề:** Khi `emotion` thay đổi → `animationData` được set về `null` → cú **biến mất một khoảng khắc** trước khi load animation mới → **bị khựng hình, không mượt mà**.

### 4.3. `ChatWindow.tsx` – Không cần sửa

Logic đọc emotion ở dòng 46-55 đã đúng:

```tsx
let currentEmotion: OwlEmotion = "idle";
if (isTyping) {
  currentEmotion = "thinking";   // Khi AI đang gõ → cú suy nghĩ
} else {
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant");
  if (lastAssistantMsg && lastAssistantMsg.emotion) {
    currentEmotion = lastAssistantMsg.emotion as OwlEmotion;  // Đọc emotion từ message cuối
  }
}
```

Luồng này hoạt động **đúng rồi** — chỉ cần `page.tsx` gán `emotion` vào message là xong.

---

## 5. ✍️ Code Cần Viết

### 5.1. Sửa `page.tsx` – Parse và lưu `emotion` từ stream

**Mở file:** `frontend/app/dashboard/chat/page.tsx`

#### Bước 5.1.1 – Thêm biến `lastEmotion` trong hàm `triggerBotResponse`

Tìm đến hàm `triggerBotResponse` (khoảng dòng 251), **tìm đoạn**:

```ts
let aiText = "";
let isDone = false;
```

**Sửa thành:**

```ts
let aiText = "";
let lastEmotion: string | undefined = undefined; // ← THÊM DÒNG NÀY
let isDone = false;
```

#### Bước 5.1.2 – Parse `emotion` từ mỗi chunk SSE (trong `triggerBotResponse`)

Tìm đoạn xử lý `dataObj` trong vòng lặp stream (khoảng dòng 342-356):

```ts
// ⚠️ HIỆN TẠI (chưa có emotion):
if (dataObj.text) {
  aiText += dataObj.text;
  setConversations((prev) =>
    prev.map((c) =>
      c.id === targetConversationId
        ? {
            ...c,
            messages: c.messages.map((m) =>
              m.id === botMessageId ? { ...m, content: aiText } : m
            ),
          }
        : c
    )
  );
}
```

**Sửa thành:**

```ts
// ✅ SAU KHI SỬA (có xử lý emotion):
if (dataObj.text) {
  aiText += dataObj.text;
}
// Parse emotion nếu server trả về (có thể kèm theo text hoặc đứng riêng)
if (dataObj.emotion) {
  lastEmotion = dataObj.emotion;
}
// Cập nhật message với cả text và emotion mới nhất
if (dataObj.text || dataObj.emotion) {
  setConversations((prev) =>
    prev.map((c) =>
      c.id === targetConversationId
        ? {
            ...c,
            messages: c.messages.map((m) =>
              m.id === botMessageId
                ? { ...m, content: aiText, emotion: lastEmotion }
                : m
            ),
          }
        : c
    )
  );
}
```

> **Giải thích:** Server có thể gửi `emotion` trong cùng chunk với `text` (ví dụ: `{"text":"Chúc mừng em!", "emotion":"correct"}`), hoặc gửi riêng. Code trên xử lý cả hai trường hợp.

#### Bước 5.1.3 – Sửa tương tự trong `triggerSilentReexplain`

Tìm hàm `triggerSilentReexplain` (khoảng dòng 154), tìm đoạn:

```ts
let aiText = "";
let isDone = false;
```

**Sửa thành:**

```ts
let aiText = "";
let lastEmotion: string | undefined = undefined; // ← THÊM DÒNG NÀY
let isDone = false;
```

Rồi tìm đoạn xử lý `dataObj.text` trong hàm này:

```ts
// ⚠️ HIỆN TẠI:
if (dataObj.text) {
  aiText += dataObj.text;
  setConversations((prev) =>
    prev.map((c) =>
      c.id === conversationId
        ? {
            ...c,
            messages: c.messages.map((m) =>
              m.id === botMessageId ? { ...m, content: aiText } : m
            ),
          }
        : c
    )
  );
}
```

**Sửa thành:**

```ts
// ✅ SAU KHI SỬA:
if (dataObj.text) {
  aiText += dataObj.text;
}
if (dataObj.emotion) {
  lastEmotion = dataObj.emotion;
}
if (dataObj.text || dataObj.emotion) {
  setConversations((prev) =>
    prev.map((c) =>
      c.id === conversationId
        ? {
            ...c,
            messages: c.messages.map((m) =>
              m.id === botMessageId
                ? { ...m, content: aiText, emotion: lastEmotion }
                : m
            ),
          }
        : c
    )
  );
}
```

---

### 5.2. Sửa `AssistantOwl.tsx` – Transition mượt mà, không bị khựng hình

**Mở file:** `frontend/components/chat/AssistantOwl.tsx`

**Thay thế toàn bộ nội dung file bằng code sau:**

```tsx
"use client";

import { useEffect, useState, useRef } from "react";
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
  const loadAnimation = async (targetEmotion: OwlEmotion): Promise<object | null> => {
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
  }, [emotion]);

  // Chưa có animation → không render (tránh layout shift)
  if (!currentAnimation) return null;

  return (
    <div
      className="fixed bottom-0 right-0 z-50 pointer-events-none"
      style={{
        width: "clamp(120px, 18vw, 240px)",
        // Hiệu ứng fade: opacity đổi mượt mà trong 200ms khi chuyển trạng thái
        opacity: isFading ? 0 : 1,
        transition: "opacity 200ms ease-in-out",
      }}
    >
      <Lottie
        animationData={currentAnimation}
        loop={true}
        autoplay={true}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
```

> **Giải thích kỹ thuật quan trọng:**
>
> - **`animationCache`**: Map lưu sẵn các file JSON đã tải. Lần thứ 2 đổi về cùng emotion → dùng cache, **không tải lại từ network**, load gần như tức thì.
> - **`isFading`**: Khi emotion thay đổi, cú mờ dần (`opacity: 0`) trong 200ms, sau đó đổi animation và hiện lại (`opacity: 1`). Người dùng thấy chuyển cảnh mượt mà, không bị "giật" hay "biến mất đột ngột".
> - **`latestEmotionRef`**: Nếu emotion thay đổi 2 lần liên tiếp rất nhanh (ví dụ: `idle` → `thinking` → `correct`), ref này đảm bảo chỉ load và hiển thị animation của emotion **mới nhất**, tránh hiện animation cũ do async không theo thứ tự.
> - **Preload `idle`**: Animation idle được tải ngay khi component mount → con cú xuất hiện ngay lập tức.

---

## 6. 🧪 Kiểm Tra Chức Năng (Acceptance Criteria)

Sau khi code xong, tự test các kịch bản sau:

| # | Kịch bản | Cách test | Kết quả mong đợi |
|---|---|---|---|
| **AC1** | Đang suy nghĩ | Gõ câu hỏi và gửi | Con cú chuyển sang trạng thái **suy nghĩ** (`owl_thinking.json`) trong lúc chờ AI |
| **AC2** | Trả lời đúng | Server trả về `"emotion": "correct"` | Con cú **vỗ tay vui vẻ** (`owl_correct.json`) |
| **AC3** | Trả lời sai | Server trả về `"emotion": "incorrect"` | Con cú **lắc đầu động viên** (`owl_incorrect.json`) |
| **AC4** | Transition mượt | Đổi qua lại nhiều lần | Cú fade-out → fade-in mượt mà, **không bị khựng hình** hay biến mất |
| **AC5** | Không ảnh hưởng chat | Chat đang stream text | Con cú cử động mà **chat vẫn chạy bình thường**, không bị lag |

### Cách bật server để test

```bash
# Terminal 1: chạy Backend
cd d:\Document\Capstone\backend
# (theo hướng dẫn backend team)

# Terminal 2: chạy Frontend
cd d:\Document\Capstone\frontend
npm run dev
```

Mở trình duyệt: `http://localhost:3000`

### Giả lập khi server chưa trả `emotion` (test thủ công UI)

Nếu backend chưa gửi field `emotion`, tạm thời **hardcode** vào `page.tsx` để kiểm tra UI:

```ts
// Thêm TẠM vào cuối vòng lặp stream, sau khi isDone = true:
// ⚠️ XÓA ĐOẠN NÀY SAU KHI TEST XONG
if (isDone && !lastEmotion) {
  // Thay "correct" bằng "incorrect" hoặc "suggesting" để thử từng trạng thái
  setConversations((prev) =>
    prev.map((c) =>
      c.id === targetConversationId
        ? {
            ...c,
            messages: c.messages.map((m) =>
              m.id === botMessageId ? { ...m, emotion: "correct" } : m
            ),
          }
        : c
    )
  );
}
```

---

## 7. 📁 Tóm Tắt File Cần Sửa

```
frontend/
├── app/
│   └── dashboard/
│       └── chat/
│           └── page.tsx           ← SỬA: thêm parse + lưu emotion vào 2 hàm
└── components/
    └── chat/
        └── AssistantOwl.tsx       ← SỬA: thêm cache + transition fade mượt mà
```

**Không cần:**
- ❌ Cài thêm thư viện nào (`lottie-react` đã có sẵn trong `package.json`)
- ❌ Tạo file mới
- ❌ Sửa `types/chat.ts` (field `emotion` đã có)
- ❌ Sửa `ChatWindow.tsx` (logic đọc emotion đã đúng)
- ❌ Tạo thêm file Lottie (5 trạng thái đã đủ trong `public/lottie/`)

---

## 8. 📤 Tạo Pull Request

Sau khi làm xong và test ổn:

```bash
git add components/chat/AssistantOwl.tsx
git add app/dashboard/chat/page.tsx
git commit -m "feat(US4.2): Owl animation responds to server emotion flag"
git push origin feat/us4.2-owl-emotion-state
```

Lên GitHub tạo PR:
- **Base branch:** `dev`
- **PR title:** `[FE][US4.2] Owl emotion state from server response`
- **Assign reviewer:** Thiên (theo T2.8: Review code FE của Bảo và gộp)

---

## 9. ⚠️ Phụ Thuộc Cần Biết

Task này **phụ thuộc vào** team khác:

| Người | Task | Trạng thái | Lý do |
|---|---|---|---|
| **Thông** (AI) | T2.3: Gắn cờ `emotion` vào Orchestrator | Cần đợi | Nếu Thông chưa xong, server chưa trả `emotion` → dùng hardcode ở trên để test UI trước |
| **Thống** (BE) | T2.5: Nhét cờ emotion vào JSON stream trả về | Cần đợi | Nếu Thống chưa nhét vào SSE, FE parse không thấy gì |

> ✅ **Không cần ngồi đợi:** Bảo code phần FE với hardcode giả trước, chờ Thông + Thống xong thì ráp thật vào là done. Làm song song như sơ đồ phụ thuộc trong sprint đã nêu.

---

*Hướng dẫn này thuộc dự án Capstone — sẽ hoàn thiện tương đương SocraticKid về chức năng và cách hoạt động.*
