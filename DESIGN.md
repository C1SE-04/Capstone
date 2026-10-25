---
name: SocraticKid Design System
description: Hệ thống thiết kế sư phạm ấm áp, tinh tế và khơi mở tư duy cho SocraticKid
colors:
  primary: "#C1762A"
  primary-hover: "#8C4905"
  primary-gradient-end: "#8C4905"
  ink: "#8C4905"
  ink-body: "#1C1917"
  ink-muted: "#7A3E04"
  neutral-bg: "#F7ECE1"
  surface-card: "#FFFFFF"
  surface-secondary: "#F1CCA6"
  surface-accent: "#F7AD62"
  border-warm: "#F1CCA6"
  success: "#10B981"
  success-bg: "#ECFDF5"
  warning: "#F59E0B"
  error: "#EF4444"
typography:
  display:
    fontFamily: "var(--font-geist-sans), system-ui, sans-serif"
    fontSize: "clamp(2rem, 5vw, 3.5rem)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  heading:
    fontFamily: "var(--font-geist-sans), system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.015em"
  body:
    fontFamily: "var(--font-geist-sans), system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  mono:
    fontFamily: "var(--font-geist-mono), monospace"
    fontSize: "0.875rem"
    fontWeight: 500
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  section: "64px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    padding: "10px 20px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
---

## Overview

SocraticKid hướng tới trải nghiệm học toán tích cực, gợi mở và đáng tin cậy. Thiết kế sử dụng tông màu ấm áp lấy cảm hứng từ đất nung, giấy tập và gỗ tự nhiên, loại bỏ hoàn toàn các màu tím neon công nghệ lạnh lùng của AI thông thường.

## Colors

- **Primary Accent (`#C1762A`)**: Điểm nhấn hành động chính, nút gửi bài, đường viền active, chỉ số tiến trình.
- **Deep Ink (`#8C4905`)**: Màu chữ tiêu đề, icon thương hiệu và các điểm nhấn nhận diện mạnh mẽ.
- **Warm Canvas (`#F7ECE1`)**: Nền chủ đạo toàn ứng dụng, giúp mắt học sinh không bị lóa khi ngồi học lâu vào buổi tối.
- **Surface Secondary (`#F1CCA6`)**: Bề mặt phân tầng phụ, viền thẻ và thanh sidebar.
- **Body Text (`#1C1917` / `text-stone-900`)**: Mực đen than mềm đạt chuẩn tương phản WCAG AA (> 7:1 trên nền trắng).

## Typography

- **Phông chữ chủ đạo**: Geist Sans (`var(--font-geist-sans)`) mang lại sự sắc sảo, hiện đại và chuẩn xác cho các con số, công thức toán học và văn bản tiếng Việt có dấu.
- **Tiêu đề (Headings)**: Sử dụng độ đậm cao (`font-bold` hoặc `font-extrabold`) với `letter-spacing: -0.02em` để tạo sự dứt khoát.
- **Nội dung đàm thoại**: Giữ kích thước thoải mái `15px` (`text-[15px]`) với khoảng cách dòng rộng rãi `leading-relaxed` để trẻ nhỏ dễ theo dõi từng bước gợi ý.

## Layout

- **Hệ lưới**: Cấu trúc linh hoạt dựa trên CSS Grid và Flexbox, hạn chế tối đa các phép tính chia % thủ công.
- **Ổn định Viewport**: Toàn bộ các khung màn hình chính (Chat, Monitor, Dashboard) sử dụng `h-[100dvh]` để ngăn ngừa tình trạng nhảy layout khi thanh địa chỉ trên trình duyệt di động co giãn.
- **Căn lề**: Lề lùi đều đặn chuẩn 16px – 24px trên thiết bị di động và căn giữa tối đa `max-w-7xl` trên màn hình lớn.

## Elevation & Depth

- Ưu tiên phân tách bề mặt bằng các bước chuyển tông màu nhẹ nhàng (`tone steps`) giữa `#F7ECE1`, `#F1CCA6` và `white` thay vì đổ bóng dày.
- Chỉ sử dụng viền mỏng 1px (`border border-[#F1CCA6]`) kết hợp bóng đổ cực nhẹ (`shadow-xs` hoặc `shadow-sm`) để giữ cho giao diện luôn thoáng đãng.

## Shapes

- Bo góc chủ đạo: `rounded-2xl` (16px) cho các khung thẻ, bong bóng tin nhắn và modal.
- Nút bấm và ô nhập liệu: `rounded-xl` (12px) vừa vặn với ngón tay học sinh.
- Các huy hiệu nhỏ, badge trạng thái: `rounded-full` gọn gàng.

## Components

- **Khung Chat**: Bong bóng AI nền trắng viền kem; bong bóng học sinh màu cam đất nung chữ trắng; bong bóng khen ngợi viền xanh ngọc bích.
- **Thẻ Flashcard Sổ tay**: Cấu trúc rõ ràng gồm Đề bài ➔ Bí kíp cốt lõi ➔ Điểm tự lập ➔ Nút xem lại đối thoại tư duy.
- **Nút hành động (Buttons)**: Luôn đi kèm hiệu ứng nảy nút xúc giác (`active:scale-[0.98]` hoặc `active:scale-95`) để mang lại cảm giác phản hồi tức thì.

## Do's and Don'ts

### Do's
- Luôn đảm bảo tỷ lệ tương phản chữ trên nền tối thiểu 4.5:1 (WCAG AA).
- Luôn xử lý đầy đủ 4 trạng thái: Loading Skeleton, Empty State, Error Feedback và Success State.
- Sử dụng các icon nét đơn chính xác từ Lucide React.

### Don'ts
- Không sử dụng màu đen thuần thô ráp `#000000`.
- Không sử dụng gradient tím neon AI (`from-purple-600 to-indigo-600`).
- Không đặt các thẻ đối xứng rập khuôn 3 cột thiếu chiều sâu.
- Không dùng hiệu ứng rung giật quá đà (`animate-bounce`) cho các phần tử UI cố định; ưu tiên chuyển động mượt mà `ease-out`.
