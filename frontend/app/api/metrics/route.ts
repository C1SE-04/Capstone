/**
 * Task #121: BFF Proxy — api/metrics/route.ts
 *
 * Đây là lớp trung gian (BFF - Backend for Frontend) giữa React UI và Python FastAPI.
 * Nhiệm vụ:
 *   1. Kiểm tra NextAuth Session (user đã đăng nhập chưa, lấy access_token).
 *   2. Forward request + access_token sang Python backend GET /metrics/study-time.
 *   3. Trả kết quả về cho React component để vẽ biểu đồ.
 *
 * Cách Frontend gọi:
 *   GET /api/metrics?student_id=xxx&mode=weekly&start_date=2024-10-07
 */

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../auth/[...nextauth]/route";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    // 1. Lấy session NextAuth (bao gồm access_token của Python backend)
    const session = await getServerSession(authOptions);

    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "Unauthorized — vui lòng đăng nhập." },
        { status: 401 }
      );
    }

    // 2. Đọc query params từ request của FE
    const { searchParams } = req.nextUrl;
    const studentId = searchParams.get("student_id");
    const mode = searchParams.get("mode") || "weekly";
    const startDate = searchParams.get("start_date"); // optional, dạng YYYY-MM-DD

    if (!studentId) {
      return NextResponse.json(
        { error: "Thiếu tham số student_id." },
        { status: 400 }
      );
    }

    // 3. Build URL tới Python backend
    const backendParams = new URLSearchParams({
      student_id: studentId,
      mode,
      ...(startDate ? { start_date: startDate } : {}),
    });

    const backendRes = await fetch(
      `${BACKEND_URL}/metrics/study-time?${backendParams.toString()}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        // Không cache — luôn lấy dữ liệu thật thời gian thực
        cache: "no-store",
      }
    );

    // 4. Trả về response từ Python (bao gồm cả status code lỗi nếu có)
    const data = await backendRes.json();

    return NextResponse.json(data, { status: backendRes.status });
  } catch (error: unknown) {
    console.error("[api/metrics] Error:", error);
    return NextResponse.json(
      { error: "Internal Server Error", details: String(error) },
      { status: 500 }
    );
  }
}
