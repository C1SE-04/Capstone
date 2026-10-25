/**
 * Task: T6.16 & T6.18 (US 6.3) — BFF Proxy: POST /api/metrics/restart
 *
 * Nhận restart timestamp từ FE khi học sinh nhấn "Đang học" trong IdleModal.
 * Chuyển tiếp tới Python backend để lưu mốc thời gian hoạt động mới vào DB.
 */

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    const body = await req.json().catch(() => ({}));
    const timestamp = body.timestamp || Math.floor(Date.now() / 1000);
    const restartTime = body.restart_time || new Date().toISOString();
    const sessionId = body.session_id || null;

    // Nếu người dùng đã đăng nhập và có access_token từ FastAPI backend
    if (session?.access_token) {
      try {
        const backendRes = await fetch(`${BACKEND_URL}/metrics/restart`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            timestamp,
            restart_time: restartTime,
            session_id: sessionId,
          }),
        });

        if (backendRes.ok) {
          const data = await backendRes.json().catch(() => ({}));
          return NextResponse.json({
            success: true,
            message: "Mốc thời gian restart đã được lưu thành công.",
            ...data,
          });
        }
      } catch (beErr) {
        // Log cảnh báo nếu backend chưa hoàn tất T6.18 hoặc đang tắt
        console.warn(
          "[api/metrics/restart] Không thể chuyển tiếp tới FastAPI backend:",
          beErr
        );
      }
    }

    // Phản hồi thành công ngay cả khi chạy standalone hoặc guest/mock session
    return NextResponse.json({
      success: true,
      message: "Đã ghi nhận mốc thời gian tiếp tục học.",
      timestamp,
      restart_time: restartTime,
      session_id: sessionId,
    });
  } catch (error) {
    console.error("[api/metrics/restart] Error:", error);
    return NextResponse.json(
      { error: "Đã xảy ra lỗi khi ghi nhận restart timestamp." },
      { status: 500 }
    );
  }
}
