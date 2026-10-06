import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware bảo vệ các route riêng tư.
 * Tương thích Next.js 16+: dùng NextResponse thay vì withAuth (deprecated).
 * Nếu người dùng chưa đăng nhập (không có cookie session), redirect về trang chủ.
 */
export function middleware(request: NextRequest) {
  // Next-auth lưu session token trong cookie này (JWT strategy)
  const sessionToken =
    request.cookies.get("next-auth.session-token") ||
    request.cookies.get("__Secure-next-auth.session-token");

  if (!sessionToken) {
    // Chưa đăng nhập → redirect về trang chủ
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

// Chỉ áp dụng middleware này cho các đường dẫn bắt đầu bằng /dashboard hoặc /chat
export const config = {
  matcher: ["/dashboard/:path*", "/chat/:path*"],
};
