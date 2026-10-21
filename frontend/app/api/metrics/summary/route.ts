import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "../../auth/[...nextauth]/route";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.access_token) {
      return NextResponse.json(
        { error: "Unauthorized — vui lòng đăng nhập." },
        { status: 401 }
      );
    }

    const { searchParams } = req.nextUrl;
    // Nếu không truyền student_id thì lấy từ session của chính học sinh đăng nhập
    const studentId = searchParams.get("student_id") || (session.user as any)?.id;
    const rangeDays = searchParams.get("range_days") || "7";

    if (!studentId) {
      return NextResponse.json(
        { error: "Thiếu tham số student_id." },
        { status: 400 }
      );
    }

    const backendRes = await fetch(
      `${BACKEND_URL}/metrics/summary?student_id=${encodeURIComponent(studentId)}&range_days=${encodeURIComponent(rangeDays)}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          "Content-Type": "application/json",
        },
        cache: "no-store",
      }
    );

    if (!backendRes.ok) {
      const errText = await backendRes.text();
      return NextResponse.json(
        { error: `Backend error: ${backendRes.status}`, details: errText },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("[api/metrics/summary] Error:", error);
    return NextResponse.json(
      { error: "Internal Server Error", message: error?.message },
      { status: 500 }
    );
  }
}
