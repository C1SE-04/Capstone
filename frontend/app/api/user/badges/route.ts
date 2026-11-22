/**
 * File: frontend/app/api/user/badges/route.ts
 * US 9.2 (Task T9.7 & T9.8) - BFF Proxy: GET & POST /api/user/badges
 *
 * Proxy giữa Next.js Frontend và Python FastAPI Backend:
 * - GET: Lấy danh sách toàn bộ huy hiệu đã mở khóa của học sinh từ DB.
 * - POST: Mở khóa / đồng bộ huy hiệu lên DB.
 */

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.access_token) {
      return NextResponse.json(
        {
          success: true,
          badge_ids: [],
          badges: [],
          message: "Guest hoặc chưa đăng nhập.",
        },
        { status: 200 }
      );
    }

    const backendRes = await fetch(`${BACKEND_URL}/api/user/badges`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (backendRes.ok) {
      const data = await backendRes.json();
      return NextResponse.json(data);
    }

    // Nếu endpoint /api/user/badges không tìm thấy, thử fallback /user/badges
    const fallbackRes = await fetch(`${BACKEND_URL}/user/badges`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (fallbackRes.ok) {
      const data = await fallbackRes.json();
      return NextResponse.json(data);
    }

    return NextResponse.json(
      {
        success: false,
        badge_ids: [],
        badges: [],
        error: "Không thể lấy danh sách huy hiệu từ backend.",
      },
      { status: backendRes.status || 500 }
    );
  } catch (error) {
    console.error("[BFF /api/user/badges GET] Lỗi kết nối backend:", error);
    return NextResponse.json(
      {
        success: false,
        badge_ids: [],
        badges: [],
        error: "Lỗi kết nối máy chủ.",
      },
      { status: 500 }
    );
  }
}

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

    // Fallback nếu không có prefix /api
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
        error: errData.detail || "Lỗi mở khóa huy hiệu từ backend.",
      },
      { status: backendRes.status || 500 }
    );
  } catch (error) {
    console.error("[BFF /api/user/badges POST] Lỗi kết nối backend:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Lỗi kết nối máy chủ khi mở khóa huy hiệu.",
      },
      { status: 500 }
    );
  }
}

