import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

/**
 * Middleware bảo vệ các route riêng tư và phân quyền theo Role.
 */
export async function middleware(request: NextRequest) {
  // getToken sẽ tự động parse JWT token của NextAuth từ cookie
  const token = await getToken({ 
    req: request, 
    secret: process.env.NEXTAUTH_SECRET 
  });

  const url = request.nextUrl.clone();

  // 1. Chưa đăng nhập → redirect về trang chủ
  if (!token) {
    url.pathname = "/";
    return NextResponse.redirect(url);
  }

  const role = token.role as string;
  const path = request.nextUrl.pathname;

  // 2. Định tuyến mặc định khi vào thẳng /dashboard
  if (path === "/dashboard") {
    if (role === "STUDENT") {
      url.pathname = "/dashboard/chat";
      return NextResponse.redirect(url);
    } else if (role === "MONITOR") {
      url.pathname = "/dashboard/monitor";
      return NextResponse.redirect(url);
    }
  }

  // 3. Chặn Phụ huynh (MONITOR) vào trang của Học sinh
  if (path.startsWith("/dashboard/chat")) {
    if (role === "MONITOR") {
      url.pathname = "/dashboard/monitor"; // Bắn ngược về trang giám sát
      return NextResponse.redirect(url);
    }
  }

  // 4. Chặn Học sinh (STUDENT) vào trang của Phụ huynh
  if (path.startsWith("/dashboard/monitor")) {
    if (role === "STUDENT") {
      url.pathname = "/dashboard/chat"; // Bắn ngược về trang chat
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/chat/:path*"],
};
