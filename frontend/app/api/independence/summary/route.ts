/**
 * Task: T6.5 (US 6.1) — BFF Proxy: GET /api/independence/summary
 *
 * Lấy dữ liệu tổng hợp điểm Tự lực (Mastery / Independence) của học sinh:
 *   - average_score: Điểm tự lực trung bình (0 - 100)
 *   - total_completed: Tổng số bài hoàn thành
 *   - latest_score: Điểm của bài giải gần nhất
 *   - evaluation_level: Mức độ đánh giá sư phạm
 */

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.access_token) {
      // Trả về dữ liệu mặc định ban đầu nếu chưa đăng nhập hoặc đang dùng thử
      return NextResponse.json({
        student_id: null,
        average_score: 0,
        total_completed: 0,
        latest_score: null,
        evaluation_level: "Bắt đầu học để tính điểm",
        history: [],
      });
    }

    const { searchParams } = req.nextUrl;
    const studentId = searchParams.get("student_id");
    const query = studentId ? `?student_id=${encodeURIComponent(studentId)}` : "";

    const backendRes = await fetch(`${BACKEND_URL}/independence/summary${query}`, {
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

    // Nếu backend trả về lỗi hoặc chưa có dữ liệu, trả về fallback an toàn
    return NextResponse.json({
      student_id: (session.user as any)?.id || null,
      average_score: 0,
      total_completed: 0,
      latest_score: null,
      evaluation_level: "Chưa có dữ liệu",
      history: [],
    });
  } catch (error) {
    console.error("[api/independence/summary] Error:", error);
    return NextResponse.json(
      {
        student_id: null,
        average_score: 0,
        total_completed: 0,
        latest_score: null,
        evaluation_level: "Chưa có dữ liệu",
        history: [],
      },
      { status: 200 }
    );
  }
}
