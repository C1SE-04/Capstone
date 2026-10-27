/**
 * File: app/api/metrics/streak-leaderboard/route.ts
 * Mô tả: BFF Proxy chuyển tiếp request từ Next.js Client sang FastAPI Backend:
 *        GET /metrics/streak-leaderboard?grade=...&limit=...
 * - Task: T8.15 (US 8.2)
 * - Tự động đính kèm access_token của học sinh/người dùng từ getServerSession.
 * - Hỗ trợ lọc theo khối lớp (grade: 4-9) hoặc xem Toàn Server (grade=None).
 */

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "Unauthorized — Vui lòng đăng nhập để xem bảng xếp hạng." },
        { status: 401 }
      );
    }

    const { searchParams } = req.nextUrl;
    const grade = searchParams.get("grade");
    const limit = searchParams.get("limit") || "50";

    const backendParams = new URLSearchParams();
    if (grade && grade !== "ALL") {
      backendParams.set("grade", grade);
    }
    if (limit) {
      backendParams.set("limit", limit);
    }

    const backendUrl = `${BACKEND_URL}/metrics/streak-leaderboard?${backendParams.toString()}`;

    const backendRes = await fetch(backendUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      cache: "no-store",
    });

    if (!backendRes.ok) {
      const errText = await backendRes.text();
      return NextResponse.json(
        {
          error: `Lỗi kết nối máy chủ (${backendRes.status})`,
          details: errText,
        },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("[api/metrics/streak-leaderboard] Lỗi:", error);
    return NextResponse.json(
      {
        error: "Internal Server Error",
        message: error?.message || "Không thể tải dữ liệu bảng xếp hạng",
      },
      { status: 500 }
    );
  }
}
