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
  const isNewUser = (token as any)?.is_new_user === true;

  // 2. [AC 8.3.2] Người dùng mới chưa hoàn tất Onboarding:
  // Bắt buộc chuyển hướng đến /onboarding, chặn truy cập vào mọi trang Dashboard khác
  if (isNewUser) {
    if (path !== "/onboarding") {
      url.pathname = "/onboarding";
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  // 3. [AC 8.3.3] Người dùng đã hoàn tất Onboarding (is_new_user === false):
  // Nếu cố tình truy cập lại /onboarding thì tự động chuyển hướng về Dashboard tương ứng
  if (path === "/onboarding") {
    if (role === "STUDENT") {
      url.pathname = "/dashboard/chat";
    } else if (role === "MONITOR") {
      url.pathname = "/dashboard/monitor";
    } else if (role === "ADMIN") {
      url.pathname = "/admin";
    } else {
      url.pathname = "/";
    }
    return NextResponse.redirect(url);
  }

  // 4. Chặn Quản trị viên (ADMIN) truy cập vào Chat hoặc bất kỳ trang nào của Dashboard
  if (path.startsWith("/dashboard") || path.startsWith("/chat")) {
    if (role === "ADMIN") {
      url.pathname = "/admin";
      return NextResponse.redirect(url);
    }
  }

  // 5. Định tuyến mặc định khi vào thẳng /dashboard
  if (path === "/dashboard") {
    if (role === "STUDENT") {
      url.pathname = "/dashboard/chat";
      return NextResponse.redirect(url);
    } else if (role === "MONITOR") {
      url.pathname = "/dashboard/monitor";
      return NextResponse.redirect(url);
    } else if (role === "ADMIN") {
      url.pathname = "/admin";
      return NextResponse.redirect(url);
    }
  }

  // 6. Chặn Phụ huynh (MONITOR) vào trang Chat của Học sinh
  if (path.startsWith("/dashboard/chat") || path.startsWith("/chat")) {
    if (role === "MONITOR") {
      url.pathname = "/dashboard/monitor"; // Bắn ngược về trang giám sát
      return NextResponse.redirect(url);
    }
  }

  // 7. Chặn Học sinh (STUDENT) vào trang của Phụ huynh
  if (path.startsWith("/dashboard/monitor")) {
    if (role === "STUDENT") {
      url.pathname = "/dashboard/chat"; // Bắn ngược về trang chat
      return NextResponse.redirect(url);
    }
  }

  // 8. Chặn tuyệt đối mọi Role khác ADMIN truy cập vào các trang /admin
  if (path === "/admin" || path.startsWith("/admin/")) {
    if (role !== "ADMIN") {
      if (role === "STUDENT") {
        url.pathname = "/dashboard/chat";
      } else if (role === "MONITOR") {
        url.pathname = "/dashboard/monitor";
      } else {
        url.pathname = "/";
      }
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/chat/:path*",
    "/admin",
    "/admin/:path*",
    "/onboarding",
  ],
};
