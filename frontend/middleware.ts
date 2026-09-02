import { withAuth } from "next-auth/middleware";

/**
 * Middleware bảo vệ các route riêng tư.
 * Nếu người dùng chưa đăng nhập, sẽ tự động chuyển hướng về trang chủ (signIn: '/').
 */
export default withAuth({
  pages: {
    signIn: "/", // Nếu chưa đăng nhập, tự động đá về trang chủ
  },
});

// Chỉ áp dụng middleware này cho các đường dẫn bắt đầu bằng /dashboard hoặc /chat
export const config = {
  matcher: ["/dashboard/:path*", "/chat/:path*"],
};
