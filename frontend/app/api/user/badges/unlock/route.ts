/**
 * File: frontend/app/api/user/badges/unlock/route.ts
 * US 9.2 (Task T9.7 & T9.8) - BFF Proxy: POST /api/user/badges/unlock
 *
 * Mở khóa và đồng bộ huy hiệu học sinh lên Database:
 * - Hỗ trợ cả badge_id đơn lẻ hoặc mảng badge_ids để migrate từ localStorage.
 * - Trả về `is_first_time: true` nếu có ít nhất 1 cúp mới (cho phép hiện modal ăn mừng),
 *   hoặc `is_first_time: false` nếu cúp đã đạt trước đó (chặn popup ăn mừng).
 */

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../../auth/[...nextauth]/route";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "Unauthorized — vui lòng đăng nhập để mở khóa huy hiệu." },
        { status: 401 }
      );
    }

    const body = await req.json().catch(() => ({}));

    // Gửi request sang FastAPI Backend
    const backendRes = await fetch(`${BACKEND_URL}/api/user/badges/unlock`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (backendRes.ok) {
      const data = await backendRes.json();
      return NextResponse.json(data);
    }

    // Fallback thử endpoint không có tiền tố /api
    const fallbackRes = await fetch(`${BACKEND_URL}/user/badges/unlock`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (fallbackRes.ok) {
      const data = await fallbackRes.json();
      return NextResponse.json(data);
    }

    const errData = await backendRes.json().catch(() => ({}));
    return NextResponse.json(
      {
        success: false,
        error: errData.detail || "Không thể mở khóa huy hiệu trên backend.",
      },
      { status: backendRes.status || 500 }
    );
  } catch (error) {
    console.error("[BFF /api/user/badges/unlock POST] Lỗi:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Lỗi kết nối máy chủ.",
      },
      { status: 500 }
    );
  }
}

