"use client";

import React, { useState, useEffect } from "react";
import Lottie from "lottie-react";
import { Flame, Trophy, Sparkles, Crown, Star } from "lucide-react";
import { cn } from "@/lib/utils";

/** Cấu hình 7 mốc tiến hóa Streak chuẩn màu từ Figma (Task T8.9 & T8.35) */
export interface StreakTierConfig {
  minDays: number;
  name: string;
  badgeLabel: string;
  labelColor: string;       // Mã màu chữ số ngày (Figma text color)
  bgBadge: string;          // Màu nền nút badge
  borderBadge: string;      // Viền nút
  hoverBg: string;          // Màu hover
  flamePrimary: string;     // Màu thân lửa chính
  flameCore: string;        // Màu tâm sáng của lửa
  glowColor: string;        // Quầng sáng drop-shadow
  animationClass: string;   // Hoạt ảnh
  accessoryIcon?: "crown" | "star" | "sparkles";
}

export const STREAK_TIERS: StreakTierConfig[] = [
  {
    minDays: 365,
    name: "Lửa Phượng Hoàng",
    badgeLabel: "Phượng Hoàng",
    labelColor: "#DF632D",
    bgBadge: "bg-[#FFF4ED]",
    borderBadge: "border-[#DF632D]/50 hover:border-[#DF632D]",
    hoverBg: "hover:bg-[#FFE8DC]",
    flamePrimary: "#F77C2C",
    flameCore: "#FFE18A",
    glowColor: "rgba(223, 99, 45, 0.45)",
    animationClass: "animate-phoenix",
  },
  {
    minDays: 200,
    name: "Lửa Tinh Tú",
    badgeLabel: "Tinh Tú",
    labelColor: "#7460C2",
    bgBadge: "bg-[#F5F2FF]",
    borderBadge: "border-[#7460C2]/50 hover:border-[#7460C2]",
    hoverBg: "hover:bg-[#EBE5FF]",
    flamePrimary: "#6D5AC5",
    flameCore: "#FFD66B",
    glowColor: "rgba(116, 96, 194, 0.4)",
    animationClass: "animate-star-twinkle",
    accessoryIcon: "star",
  },
  {
    minDays: 100,
    name: "Lửa Vàng Kim",
    badgeLabel: "Vàng Kim",
    labelColor: "#AB7A16",
    bgBadge: "bg-[#FEFCE8]",
    borderBadge: "border-[#F7B728]/60 hover:border-[#AB7A16]",
    hoverBg: "hover:bg-[#FEF9C3]",
    flamePrimary: "#F7B728",
    flameCore: "#FFF0A0",
    glowColor: "rgba(247, 183, 40, 0.4)",
    animationClass: "animate-star-twinkle",
    accessoryIcon: "crown",
  },
  {
    minDays: 60,
    name: "Lửa Tím Huyền Bí",
    badgeLabel: "Tím Huyền Bí",
    labelColor: "#8450D8",
    bgBadge: "bg-[#FAF5FF]",
    borderBadge: "border-[#8450D8]/40 hover:border-[#8450D8]",
    hoverBg: "hover:bg-[#F3E8FF]",
    flamePrimary: "#8450D8",
    flameCore: "#F2CFFF",
    glowColor: "rgba(132, 80, 216, 0.35)",
    animationClass: "animate-flame-pulse",
    accessoryIcon: "sparkles",
  },
  {
    minDays: 30,
    name: "Lửa Xanh Lam",
    badgeLabel: "Xanh Lam",
    labelColor: "#2675E9",
    bgBadge: "bg-[#F0F7FF]",
    borderBadge: "border-[#2675E9]/40 hover:border-[#2675E9]",
    hoverBg: "hover:bg-[#E0F0FE]",
    flamePrimary: "#2675E9",
    flameCore: "#B7F4FF",
    glowColor: "rgba(38, 117, 233, 0.35)",
    animationClass: "animate-flame-pulse",
  },
  {
    minDays: 10,
    name: "Lửa Bập Bùng",
    badgeLabel: "Bập Bùng",
    labelColor: "#E46538",
    bgBadge: "bg-[#FFF2EE]",
    borderBadge: "border-[#E46538]/40 hover:border-[#E46538]",
    hoverBg: "hover:bg-[#FFE4DC]",
    flamePrimary: "#F25338",
    flameCore: "#FFDC7D",
    glowColor: "rgba(228, 101, 56, 0.3)",
    animationClass: "animate-flame-bob",
  },
  {
    minDays: 3,
    name: "Đốm Lửa Khởi Đầu",
    badgeLabel: "Khởi Đầu",
    labelColor: "#E97924",
    bgBadge: "bg-[#FFF7ED]",
    borderBadge: "border-[#E97924]/40 hover:border-[#E97924]",
    hoverBg: "hover:bg-[#FFEDD5]",
    flamePrimary: "#FF902F",
    flameCore: "#FFD477",
    glowColor: "rgba(233, 121, 36, 0.25)",
    animationClass: "animate-flame-flicker",
  },
];

/** Lấy cấu hình tier dựa trên số ngày streak */
export function getStreakTier(streak: number): StreakTierConfig | null {
  if (streak < 3) return null;
  return STREAK_TIERS.find((tier) => streak >= tier.minDays) ?? null;
}

interface StreakBadgeProps {
  /** Số ngày học liên tục (nếu không truyền sẽ tự fetch từ API) */
  streak?: number;
  /** Kỷ lục chuỗi ngày học */
  maxStreak?: number;
  /** Callback khi click vào badge */
  onClick?: () => void;
  className?: string;
  /** Đường dẫn file lottie tùy chỉnh (mặc định /lottie/streak_flame.json hoặc /lottie/flame.json) */
  lottieSrc?: string;
  /** Callback trả về số ngày streak sau khi tải xong để kiểm tra thành tựu */
  onStreakLoaded?: (streak: number) => void;
}

/**
 * Component render chính xác 100% vector SVG của từng mốc ngọn lửa từ Figma Canvas (Task T8.9 & T8.35).
 * Tọa độ và đường cong Bézier được trích xuất trực tiếp từ bản vẽ thiết kế chuẩn.
 */
export function FigmaStreakFlame({
  tier,
  className,
}: {
  tier: StreakTierConfig;
  className?: string;
}) {
  const commonProps = {
    className: cn("w-full h-full", className),
    fill: "none",
    xmlns: "http://www.w3.org/2000/svg",
    style: { filter: `drop-shadow(0 0 3px ${tier.glowColor})` },
  };

  switch (tier.minDays) {
    case 3:
      return (
        <svg viewBox="128 324 144 144" {...commonProps}>
          <path
            d="M200 369C203.375 387 220.25 392.625 220.25 410.625C220.25 426.375 210.125 437.625 195.5 437.625C179.75 437.625 169.625 427.5 170.75 412.875C171.875 399.375 182 392.625 184.25 383.625C184.25 396 188.75 399.375 192.125 399.375C188.75 387 196.625 380.25 200 369Z"
            fill="#FF902F"
          />
          <path
            d="M196.625 406.125C197.75 417.375 207.875 418.5 205.625 427.5C204.5 432 201.125 435.375 195.5 435.375C188.75 435.375 184.25 430.875 185.375 426.375C186.5 418.5 193.25 415.125 196.625 406.125Z"
            fill="#FFD477"
          />
          <path
            d="M227 364.5C228.05 367.95 230.3 370.2 233.75 371.25C230.3 372.3 228.05 374.55 227 378C225.95 374.55 223.7 372.3 220.25 371.25C223.7 370.2 225.95 367.95 227 364.5Z"
            fill="#FFB845"
          />
          <path
            d="M167.375 390.375C168.618 390.375 169.625 389.368 169.625 388.125C169.625 386.882 168.618 385.875 167.375 385.875C166.132 385.875 165.125 386.882 165.125 388.125C165.125 389.368 166.132 390.375 167.375 390.375Z"
            fill="#FFC56A"
          />
        </svg>
      );

    case 10:
      return (
        <svg viewBox="378 324 144 144" {...commonProps}>
          <path
            d="M450 337.5C454.5 363.375 482.625 367.875 477 397.125C488.25 392.625 490.5 381.375 489.375 376.875C505.125 394.875 505.125 412.875 497.25 428.625C488.25 448.875 469.125 457.875 450 457.875C420.75 457.875 399.375 439.875 399.375 415.125C399.375 398.25 409.5 383.625 423 372.375C419.625 392.625 425.25 397.125 429.75 398.25C421.875 372.375 446.625 363.375 450 337.5Z"
            fill="#F25338"
          />
          <path
            d="M450 357.75C454.5 382.5 475.875 391.5 473.625 412.875C472.5 434.25 461.25 450 444.375 451.125C420.75 452.25 409.5 433.125 415.125 417.375C419.625 405 427.5 400.5 432 396C427.5 416.25 439.875 417.375 438.75 406.125C434.25 387 447.75 378 450 357.75Z"
            fill="#FF962F"
          />
          <path
            d="M451.125 399.375C452.25 415.125 470.25 421.875 468 435.375C466.875 446.625 459 453.375 448.875 453.375C435.375 453.375 427.5 444.375 429.75 433.125C432 421.875 444.375 416.25 451.125 399.375Z"
            fill="#FFDC7D"
          />
          <path
            d="M394.875 361.125L399.375 366.75"
            strokeWidth="3"
            strokeLinecap="round"
            stroke="#F36C45"
          />
          <path
            d="M495 355.5L499.5 351"
            strokeWidth="3"
            strokeLinecap="round"
            stroke="#FFB33E"
          />
          <path
            d="M398.25 388.35C399.617 388.35 400.725 387.242 400.725 385.875C400.725 384.508 399.617 383.4 398.25 383.4C396.883 383.4 395.775 384.508 395.775 385.875C395.775 387.242 396.883 388.35 398.25 388.35Z"
            fill="#FFB33E"
          />
          <path
            d="M504 374.625C505.243 374.625 506.25 373.618 506.25 372.375C506.25 371.132 505.243 370.125 504 370.125C502.757 370.125 501.75 371.132 501.75 372.375C501.75 373.618 502.757 374.625 504 374.625Z"
            fill="#F36C45"
          />
        </svg>
      );

    case 30:
      return (
        <svg viewBox="628 324 144 144" {...commonProps}>
          <path
            d="M700 337.5C704.5 363.375 732.625 367.875 727 397.125C738.25 392.625 740.5 381.375 739.375 376.875C755.125 394.875 755.125 412.875 747.25 428.625C738.25 448.875 719.125 457.875 700 457.875C670.75 457.875 649.375 439.875 649.375 415.125C649.375 398.25 659.5 383.625 673 372.375C669.625 392.625 675.25 397.125 679.75 398.25C671.875 372.375 696.625 363.375 700 337.5Z"
            fill="#2675E9"
          />
          <path
            d="M701.125 358.875C704.5 382.5 729.25 392.625 723.625 417.375C718 439.875 705.625 451.125 692.125 448.875C671.875 445.5 660.625 430.875 667.375 416.25C671.875 405 678.625 398.25 682 392.625C678.625 410.625 688.75 416.25 689.875 403.875C687.625 388.125 697.75 375.75 701.125 358.875Z"
            fill="#36B6F6"
          />
          <path
            d="M701.125 399.375C702.25 415.125 720.25 421.875 718 435.375C716.875 446.625 709 453.375 698.875 453.375C685.375 453.375 677.5 444.375 679.75 433.125C682 421.875 694.375 416.25 701.125 399.375Z"
            fill="#B7F4FF"
          />
          <path
            d="M743.875 344.25C744.925 348.45 747.55 351.075 751.75 352.125C747.55 353.175 744.925 355.8 743.875 360C742.825 355.8 740.2 353.175 736 352.125C740.2 351.075 742.825 348.45 743.875 344.25Z"
            fill="#53BDF6"
          />
          <path
            d="M648.25 373.5C649.3 375.45 650.8 376.95 652.75 378C650.8 379.05 649.3 380.55 648.25 382.5C647.2 380.55 645.7 379.05 643.75 378C645.7 376.95 647.2 375.45 648.25 373.5Z"
            fill="#2675E9"
          />
          <path
            d="M752.875 391.5C754.118 391.5 755.125 390.493 755.125 389.25C755.125 388.007 754.118 387 752.875 387C751.632 387 750.625 388.007 750.625 389.25C750.625 390.493 751.632 391.5 752.875 391.5Z"
            fill="#81DCFB"
          />
        </svg>
      );

    case 60:
      return (
        <svg viewBox="878 324 144 144" {...commonProps}>
          <path
            d="M1002.65 380.383C1013.73 401.229 999.145 430.661 970.07 446.121C940.994 461.581 908.439 457.214 897.354 436.367C886.27 415.521 900.855 386.089 929.93 370.629C959.006 355.169 991.561 359.536 1002.65 380.383Z"
            strokeWidth="3"
            stroke="#DBC8FF"
          />
          <path
            d="M950 337.5C954.5 363.375 982.625 367.875 977 397.125C988.25 392.625 990.5 381.375 989.375 376.875C1005.12 394.875 1005.12 412.875 997.25 428.625C988.25 448.875 969.125 457.875 950 457.875C920.75 457.875 899.375 439.875 899.375 415.125C899.375 398.25 909.5 383.625 923 372.375C919.625 392.625 925.25 397.125 929.75 398.25C921.875 372.375 946.625 363.375 950 337.5Z"
            fill="#8450D8"
          />
          <path
            d="M951.125 360C955.625 381.375 979.25 390.375 973.625 415.125C970.25 434.25 960.125 447.75 943.25 450C926.375 450 910.625 434.25 917.375 418.5C920.75 407.25 927.5 399.375 932 393.75C928.625 414 939.875 417.375 939.875 405C936.5 387 948.875 375.75 951.125 360Z"
            fill="#B57CF0"
          />
          <path
            d="M951.125 399.375C952.25 415.125 970.25 421.875 968 435.375C966.875 446.625 959 453.375 948.875 453.375C935.375 453.375 927.5 444.375 929.75 433.125C932 421.875 944.375 416.25 951.125 399.375Z"
            fill="#F2CFFF"
          />
          <path
            d="M992.75 340.875C993.8 345.075 996.425 347.7 1000.62 348.75C996.425 349.8 993.8 352.425 992.75 356.625C991.7 352.425 989.075 349.8 984.875 348.75C989.075 347.7 991.7 345.075 992.75 340.875Z"
            fill="#A66BE4"
          />
          <path
            d="M897.125 370.125C898.175 372.825 900.05 374.7 902.75 375.75C900.05 376.8 898.175 378.675 897.125 381.375C896.075 378.675 894.2 376.8 891.5 375.75C894.2 374.7 896.075 372.825 897.125 370.125Z"
            fill="#B984F0"
          />
          <path
            d="M998.375 429.75C999.425 431.7 1000.93 433.2 1002.88 434.25C1000.93 435.3 999.425 436.8 998.375 438.75C997.325 436.8 995.825 435.3 993.875 434.25C995.825 433.2 997.325 431.7 998.375 429.75Z"
            fill="#B984F0"
          />
        </svg>
      );

    case 100:
      return (
        <svg viewBox="1128 324 144 144" {...commonProps}>
          <path
            d="M1200 366.75C1205.62 382.5 1224.75 385.875 1222.5 403.875L1236 391.5C1249.5 408.375 1250.62 420.75 1243.88 435.375C1236 452.25 1218 460.125 1200 460.125C1176.38 460.125 1153.88 445.5 1153.88 423C1153.88 407.25 1162.88 397.125 1173 390.375C1170.75 407.25 1177.5 412.875 1183.12 411.75C1177.5 392.625 1196.62 384.75 1200 366.75Z"
            fill="#F7B728"
          />
          <path
            d="M1201.12 401.625C1202.25 417.375 1220.25 424.125 1218 437.625C1216.87 450 1209 456.75 1198.87 456.75C1185.37 456.75 1177.5 447.75 1179.75 436.5C1182 425.25 1194.37 418.5 1201.12 401.625Z"
            fill="#FFF0A0"
          />
          <path
            d="M1169.62 367.875L1162.88 342L1184.25 353.25L1200 334.125L1215.75 353.25L1237.12 342L1230.38 367.875H1169.62Z"
            fill="#E5A821"
          />
          <path
            d="M1171.88 361.125H1228.12L1225.88 371.25H1174.12L1171.88 361.125Z"
            fill="#FFC743"
          />
          <path
            d="M1162.88 344.25C1164.74 344.25 1166.25 342.739 1166.25 340.875C1166.25 339.011 1164.74 337.5 1162.88 337.5C1161.01 337.5 1159.5 339.011 1159.5 340.875C1159.5 342.739 1161.01 344.25 1162.88 344.25Z"
            fill="#E5A821"
          />
          <path
            d="M1200 337.5C1201.86 337.5 1203.38 335.989 1203.38 334.125C1203.38 332.261 1201.86 330.75 1200 330.75C1198.14 330.75 1196.62 332.261 1196.62 334.125C1196.62 335.989 1198.14 337.5 1200 337.5Z"
            fill="#E5A821"
          />
          <path
            d="M1237.12 344.25C1238.99 344.25 1240.5 342.739 1240.5 340.875C1240.5 339.011 1238.99 337.5 1237.12 337.5C1235.26 337.5 1233.75 339.011 1233.75 340.875C1233.75 342.739 1235.26 344.25 1237.12 344.25Z"
            fill="#E5A821"
          />
          <path
            d="M1142.62 366.75C1143.68 370.2 1145.93 372.45 1149.38 373.5C1145.93 374.55 1143.68 376.8 1142.62 380.25C1141.57 376.8 1139.32 374.55 1135.88 373.5C1139.32 372.45 1141.57 370.2 1142.62 366.75Z"
            fill="#EBA928"
          />
          <path
            d="M1137 356.625L1133.62 352.125"
            strokeWidth="2.5"
            strokeLinecap="round"
            stroke="#EBA928"
          />
          <path
            d="M1148.25 352.125L1151.62 347.625"
            strokeWidth="2.5"
            strokeLinecap="round"
            stroke="#EBA928"
          />
          <path
            d="M1256.25 367.875C1257.3 371.325 1259.55 373.575 1263 374.625C1259.55 375.675 1257.3 377.925 1256.25 381.375C1255.2 377.925 1252.95 375.675 1249.5 374.625C1252.95 373.575 1255.2 371.325 1256.25 367.875Z"
            fill="#EBA928"
          />
          <path
            d="M1251.75 352.125L1248.38 347.625"
            strokeWidth="2.5"
            strokeLinecap="round"
            stroke="#EBA928"
          />
          <path
            d="M1264.12 358.875L1267.5 354.375"
            strokeWidth="2.5"
            strokeLinecap="round"
            stroke="#EBA928"
          />
        </svg>
      );

    case 200:
      return (
        <svg viewBox="1378 324 144 144" {...commonProps}>
          <path
            d="M1450 345.375L1488.25 360V405C1488.25 429.75 1471.38 447.75 1450 459C1428.62 447.75 1411.75 429.75 1411.75 405V360L1450 345.375Z"
            fill="#E9E5FC"
          />
          <path
            d="M1450 352.125L1481.5 364.5V405C1481.5 425.25 1466.88 441 1450 451.125C1433.12 441 1418.5 425.25 1418.5 405V364.5L1450 352.125Z"
            fill="#6D5AC5"
          />
          <path
            d="M1448.87 346.5C1455.62 361.125 1471.37 362.25 1470.25 376.875C1481.5 373.5 1483.75 365.625 1483.75 365.625C1490.5 383.625 1484.87 402.75 1473.62 412.875L1428.62 415.125C1410.62 403.875 1408.37 388.125 1416.25 373.5C1418.5 383.625 1424.12 385.875 1429.75 384.75C1427.5 367.875 1445.5 358.875 1448.87 346.5Z"
            fill="#FFA64C"
          />
          <path
            d="M1450 366.75L1459.26 388.879L1483.16 390.847L1464.97 406.496L1470.5 429.84L1450 417.375L1429.5 429.84L1435.03 406.496L1416.83 390.847L1440.74 388.879L1450 366.75Z"
            fill="#FFD66B"
          />
          <path
            d="M1450 382.5L1455.29 394.346L1468.19 395.719L1458.56 404.404L1461.24 417.094L1450 410.625L1438.76 417.094L1441.44 404.404L1431.81 395.719L1444.71 394.346L1450 382.5Z"
            fill="#FFF4C2"
          />
          <path
            d="M1499.5 381.375C1500.55 384.825 1502.8 387.075 1506.25 388.125C1502.8 389.175 1500.55 391.425 1499.5 394.875C1498.45 391.425 1496.2 389.175 1492.75 388.125C1496.2 387.075 1498.45 384.825 1499.5 381.375Z"
            fill="#A376E8"
          />
          <path
            d="M1401.62 380.25C1402.68 382.95 1404.55 384.825 1407.25 385.875C1404.55 386.925 1402.68 388.8 1401.62 391.5C1400.57 388.8 1398.7 386.925 1396 385.875C1398.7 384.825 1400.57 382.95 1401.62 380.25Z"
            fill="#36B8D6"
          />
          <path
            d="M1415.12 344.25L1410.62 337.5"
            strokeWidth="3"
            strokeLinecap="round"
            stroke="#5CA8EE"
          />
          <path
            d="M1489.38 344.25L1495 336.375"
            strokeWidth="3"
            strokeLinecap="round"
            stroke="#D780CD"
          />
          <path
            d="M1450 442.125C1451.24 442.125 1452.25 441.118 1452.25 439.875C1452.25 438.632 1451.24 437.625 1450 437.625C1448.76 437.625 1447.75 438.632 1447.75 439.875C1447.75 441.118 1448.76 442.125 1450 442.125Z"
            fill="#E6D7FF"
          />
        </svg>
      );

    case 365:
      return (
        <svg viewBox="1628 324 144 144" {...commonProps}>
          <path
            d="M1695.5 397.125C1675.25 384.75 1660.62 369 1644.88 346.5C1643.75 373.5 1655 393.75 1674.12 409.5C1658.38 406.125 1648.25 398.25 1638.12 387C1642.62 412.875 1660.62 428.625 1683.12 429.75L1696.62 417.375L1695.5 397.125Z"
            fill="#F77C2C"
          />
          <path
            d="M1704.5 397.125C1724.75 384.75 1739.38 369 1755.12 346.5C1756.25 373.5 1745 393.75 1725.88 409.5C1741.62 406.125 1751.75 398.25 1761.88 387C1757.38 412.875 1739.38 428.625 1716.88 429.75L1703.38 417.375L1704.5 397.125Z"
            fill="#F77C2C"
          />
          <path
            d="M1648.25 355.5C1658.38 380.25 1675.25 393.75 1691 402.75L1684.25 414C1667.38 400.5 1655 380.25 1648.25 355.5Z"
            fill="#FFBD45"
          />
          <path
            d="M1751.75 355.5C1741.62 380.25 1724.75 393.75 1709 402.75L1715.75 414C1732.62 400.5 1745 380.25 1751.75 355.5Z"
            fill="#FFBD45"
          />
          <path
            d="M1698.88 411.75C1689.88 421.875 1679.75 438.75 1682 459C1692.13 451.125 1696.63 442.125 1700 435.375C1703.38 446.625 1709 457.875 1720.25 463.5C1720.25 442.125 1710.13 423 1705.63 412.875L1698.88 411.75Z"
            fill="#F65A31"
          />
          <path
            d="M1700 419.625C1694.38 435.375 1696.63 448.875 1700 457.875C1707.88 444.375 1709 433.125 1704.5 420.75L1700 419.625Z"
            fill="#FFBD45"
          />
          <path
            d="M1702.25 351L1695.5 338.625L1709 344.25C1713.5 344.25 1718 348.75 1719.12 354.375L1728.12 358.875L1716.87 363.375C1711.25 365.625 1712.37 372.375 1714.62 380.25C1720.25 397.125 1721.37 409.5 1710.12 419.625C1704.5 425.25 1695.5 425.25 1688.75 419.625C1676.37 410.625 1682 397.125 1689.87 383.625C1696.62 372.375 1700 362.25 1696.62 355.5L1702.25 351Z"
            fill="#F65A31"
          />
          <path
            d="M1702.25 370.125C1706.75 387 1710.12 397.125 1706.75 407.25C1704.5 415.125 1698.87 417.375 1694.37 411.75C1689.87 405 1696.62 398.25 1700 391.5C1703.37 382.5 1702.25 374.625 1702.25 370.125Z"
            fill="#FFE18A"
          />
          <path
            d="M1710.12 355.275C1711.24 355.275 1712.15 354.368 1712.15 353.25C1712.15 352.132 1711.24 351.225 1710.12 351.225C1709.01 351.225 1708.1 352.132 1708.1 353.25C1708.1 354.368 1709.01 355.275 1710.12 355.275Z"
            fill="#63382D"
          />
          <path
            d="M1700 324C1701.05 325.2 1702.17 326.325 1703.38 327.375C1702.17 328.425 1701.05 329.55 1700 330.75C1698.95 329.55 1697.83 328.425 1696.62 327.375C1697.83 326.325 1698.95 325.2 1700 324Z"
            fill="#EEAB31"
          />
          <path
            d="M1641.5 432C1642.55 433.95 1644.05 435.45 1646 436.5C1644.05 437.55 1642.55 439.05 1641.5 441C1640.45 439.05 1638.95 437.55 1637 436.5C1638.95 435.45 1640.45 433.95 1641.5 432Z"
            fill="#F7B73D"
          />
          <path
            d="M1757.38 433.125C1758.43 435.075 1759.93 436.575 1761.88 437.625C1759.93 438.675 1758.43 440.175 1757.38 442.125C1756.33 440.175 1754.83 438.675 1752.88 437.625C1754.83 436.575 1756.33 435.075 1757.38 433.125Z"
            fill="#F7B73D"
          />
        </svg>
      );

    default:
      return null;
  }
}

export function StreakBadge({
  streak: initialStreak,
  maxStreak: initialMaxStreak,
  onClick,
  className,
  lottieSrc = "/lottie/streak_flame.json",
  onStreakLoaded,
}: StreakBadgeProps) {
  const [fetchedStreak, setFetchedStreak] = useState<number>(0);
  const [fetchedMaxStreak, setFetchedMaxStreak] = useState<number>(0);
  const [lottieAnimation, setLottieAnimation] = useState<object | null>(null);
  const [showTooltip, setShowTooltip] = useState(false);

  // Derive state trực tiếp từ props hoặc từ API fetch (tránh setState trong effect)
  const streak = initialStreak !== undefined ? initialStreak : fetchedStreak;
  const maxStreak = initialMaxStreak !== undefined ? initialMaxStreak : fetchedMaxStreak;

  // Nếu không truyền streak từ ngoài, tự động query từ /api/metrics/summary
  useEffect(() => {
    if (initialStreak !== undefined) {
      onStreakLoaded?.(initialStreak);
      return;
    }

    let isMounted = true;
    const fetchStreak = async () => {
      try {
        const res = await fetch("/api/metrics/summary?range_days=7");
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            const currentVal = data.currentStreak ?? data.current_streak ?? 0;
            const currentMax = data.maxStreak ?? data.max_streak ?? 0;
            setFetchedStreak(currentVal);
            setFetchedMaxStreak(currentMax);
            onStreakLoaded?.(currentVal);
          }
        }
      } catch (err) {
        console.debug("[StreakBadge] Không thể lấy streak từ metrics/summary:", err);
      }
    };

    fetchStreak();
    return () => {
      isMounted = false;
    };
  }, [initialStreak, onStreakLoaded]);

  // Thử tải file Lottie hoạt hình ngọn lửa nếu có sẵn
  useEffect(() => {
    let isMounted = true;
    const loadLottie = async () => {
      const candidates = [lottieSrc, "/lottie/flame.json", "/lottie/fire.json"];
      for (const src of candidates) {
        try {
          const res = await fetch(src);
          if (res.ok) {
            const data = await res.json();
            if (isMounted && data && (data.layers || data.v)) {
              setLottieAnimation(data);
              return;
            }
          }
        } catch {
          // Bỏ qua và thử file tiếp theo
        }
      }
    };

    loadLottie();
    return () => {
      isMounted = false;
    };
  }, [lottieSrc]);

  const hasStreak = streak > 0;
  const tier = getStreakTier(streak);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        type="button"
        onClick={onClick}
        aria-label={`Chuỗi ngày học: ${streak} ngày`}
        style={{
          boxShadow: tier ? `0 2px 10px ${tier.glowColor}` : undefined,
        }}
        className={cn(
          "group flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs sm:text-sm font-semibold transition-all duration-200 border select-none cursor-pointer active:scale-95",
          tier
            ? `${tier.bgBadge} ${tier.borderBadge} ${tier.hoverBg}`
            : "bg-white text-stone-400 border-stone-200 hover:border-stone-300 hover:text-stone-600 shadow-xs",
          className
        )}
      >
        {/* Khối Hoạt hình Ngọn lửa - Chỉ xuất hiện khi đạt từ mốc 3 ngày (Đốm Lửa Khởi Đầu) trở lên */}
        {tier && (
          <div
            className={cn(
              "relative flex items-center justify-center shrink-0",
              tier.minDays === 365 ? "w-7 h-7" : "w-6 h-6",
              tier.animationClass
            )}
          >
            <FigmaStreakFlame tier={tier} />
          </div>
        )}

        {/* Số ngày Streak */}
        <span
          className="font-bold tracking-tight text-sm tabular-nums"
          style={{
            color: tier ? tier.labelColor : "#A8A29E",
          }}
        >
          {streak}
        </span>

        {/* Nhãn chữ trên desktop */}
        <span
          className="hidden md:inline font-medium text-xs"
          style={{
            color: tier ? tier.labelColor : "#A8A29E",
            opacity: tier ? 0.8 : 0.7,
          }}
        >
          ngày
        </span>
      </button>

      {/* Tooltip giải thích khi hover */}
      {showTooltip && (
        <div
          className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-60 p-3 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border text-xs z-50 animate-in fade-in zoom-in-95 duration-200 pointer-events-none"
          style={{
            borderColor: tier ? tier.labelColor : "#E7E5E4",
          }}
        >
          <div className="flex items-center justify-between font-bold mb-1">
            <div
              className="flex items-center gap-1.5"
              style={{ color: tier ? tier.labelColor : "#78716C" }}
            >
              {tier ? (
                <Sparkles size={14} className="text-amber-500" />
              ) : (
                <span className="w-2 h-2 rounded-full bg-stone-300" />
              )}
              <span>{tier ? tier.name : "Chuỗi ngày học liên tục"}</span>
            </div>
            {tier && (
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-full font-semibold"
                style={{
                  backgroundColor: tier.bgBadge,
                  color: tier.labelColor,
                }}
              >
                {tier.badgeLabel}
              </span>
            )}
          </div>

          <p className="text-stone-600 mb-2 leading-relaxed">
            {tier
              ? `Bạn đã học liên tục ${streak} ngày! Hãy duy trì mỗi ngày để nâng cấp ngọn lửa học tập.`
              : streak > 0
              ? `Bạn đã học liên tục ${streak} ngày. Duy trì đến mốc 3 ngày để thắp sáng Đốm Lửa Khởi Đầu đầu tiên!`
              : "Học bài ngay hôm nay để bắt đầu chuỗi ngày học và thắp sáng ngọn lửa!"}
          </p>

          {maxStreak > 0 && (
            <div className="flex items-center gap-1.5 pt-1.5 border-t border-stone-100 text-[11px] text-[#C1762A] font-semibold">
              <Trophy size={13} className="text-amber-500" />
              <span>Kỷ lục cao nhất: {maxStreak} ngày</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default StreakBadge;
