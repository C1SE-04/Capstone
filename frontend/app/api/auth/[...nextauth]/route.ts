import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

// Cấu hình NextAuth xử lý xác thực (Authentication)
export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),
    // Cấu hình đăng nhập bằng tài khoản/mật khẩu
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      // Hàm authorize chạy khi người dùng ấn nút Đăng Nhập ở FE
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        try {
          // Gọi sang API của Backend (FastAPI) để xác thực
          const backendUrl =
            process.env.BACKEND_URL ||
            process.env.NEXT_PUBLIC_BACKEND_URL ||
            "http://127.0.0.1:8000";

          const res = await fetch(`${backendUrl}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
              username: credentials.email.toLowerCase(),
              password: credentials.password,
            }),
          });

          if (!res.ok) return null;

          const data = await res.json();

          // Decode JWT payload (Access Token) từ Backend trả về để lấy thông tin user (ID, Email, Role)
          const payload = JSON.parse(
            Buffer.from(data.access_token.split(".")[1], "base64").toString()
          );

          const isPending =
            payload.role === "PENDING" ||
            (payload.role === "STUDENT" && !payload.grade_level);

          // Trả về object user để NextAuth lưu vào phiên đăng nhập (Session)
          return {
            id: payload.sub,
            email: payload.email,
            name: payload.email.split("@")[0], // Dùng phần trước @ làm display name
            role: payload.role,
            grade_level: payload.grade_level,
            access_token: data.access_token,
            refresh_token: data.refresh_token, // US 6.2 (T6.13): lưu refresh_token của Backend
            is_new_user: isPending,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  session: { strategy: "jwt", maxAge: 30 * 60 },
  pages: {
    signIn: "/",
  },
  // Các callback xử lý khi xác thực, tạo Token và Session
  callbacks: {
    // US 8.3 (Task T8.20): Callback signIn gọi Backend POST /auth/google-callback lấy JWT chuẩn
    async signIn({ user, account, profile }) {
      if (account?.provider === "google") {
        try {
          const backendUrl =
            process.env.BACKEND_URL ||
            process.env.NEXT_PUBLIC_BACKEND_URL ||
            "http://127.0.0.1:8000";

          const email = user.email || (profile as any)?.email;
          if (!email) {
            console.error("[NextAuth signIn] Google profile thiếu email");
            return false;
          }

          const googleId = account.providerAccountId || (profile as any)?.sub;
          const name = user.name || (profile as any)?.name;
          const avatarUrl = user.image || (profile as any)?.picture;

          // Gửi thông tin Google profile sang FastAPI backend
          const res = await fetch(`${backendUrl}/auth/google-callback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email,
              google_id: googleId,
              sub: (profile as any)?.sub || googleId,
              name,
              avatar_url: avatarUrl,
            }),
          });

          if (!res.ok) {
            const errText = await res.text().catch(() => "");
            console.error(
              `[NextAuth signIn] Backend /auth/google-callback thất bại: ${res.status} - ${errText}`
            );
            return false;
          }

          const data = await res.json();

          // Gắn dữ liệu định danh và JWT Backend vào user để jwt callback lưu vào token
          user.id = data.user_id;
          user.email = data.email;
          user.name = data.name || user.name || data.email.split("@")[0];
          user.role = data.role;
          user.grade_level = data.grade ?? undefined;
          user.access_token = data.access_token;
          user.refresh_token = data.refresh_token;
          user.is_new_user = data.is_new_user;

          return true;
        } catch (error) {
          console.error(
            "[NextAuth signIn] Lỗi kết nối backend /auth/google-callback:",
            error
          );
          return false;
        }
      }
      return true;
    },

    // Gọi khi tạo hoặc cập nhật JWT token
    async jwt({ token, user, account, trigger, session }) {
      // Lần đăng nhập đầu tiên: map thông tin từ user (từ authorize() hoặc signIn() Google)
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.grade_level = user.grade_level;
        token.access_token = user.access_token;
        token.refresh_token = user.refresh_token; // US 6.2 (T6.13): lưu refresh_token
        token.is_new_user = user.is_new_user;
      }

      // Safeguard: nếu là Google OAuth và chưa có access_token từ user
      if (account?.provider === "google" && !token.access_token && token.email) {
        try {
          const backendUrl =
            process.env.BACKEND_URL ||
            process.env.NEXT_PUBLIC_BACKEND_URL ||
            "http://127.0.0.1:8000";

          const res = await fetch(`${backendUrl}/auth/google-callback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: token.email,
              google_id: account.providerAccountId,
              sub: account.providerAccountId,
              name: token.name,
              avatar_url: token.picture,
            }),
          });

          if (res.ok) {
            const data = await res.json();
            token.id = data.user_id;
            token.role = data.role;
            token.grade_level = data.grade ?? undefined;
            token.access_token = data.access_token;
            token.refresh_token = data.refresh_token;
            token.is_new_user = data.is_new_user;
          }
        } catch (err) {
          console.error("[NextAuth jwt] Fallback Google callback error:", err);
        }
      }

      // Khi client gọi update({ grade_level: X }): cập nhật token ngay trong phiên hiện tại
      if (trigger === "update" && session?.grade_level !== undefined) {
        token.grade_level = session.grade_level;
      }
      // US 8.3: Cập nhật role sau onboarding
      if (trigger === "update" && session?.role !== undefined) {
        token.role = session.role;
      }
      // US 8.3: Cập nhật cờ is_new_user sau onboarding
      if (trigger === "update" && session?.is_new_user !== undefined) {
        token.is_new_user = session.is_new_user;
      }
      // US 6.2 (T6.13): Khi authFetch gọi update({ access_token, refresh_token }) sau khi refresh thành công
      if (trigger === "update" && session?.access_token) {
        token.access_token = session.access_token;
      }
      if (trigger === "update" && session?.refresh_token) {
        token.refresh_token = session.refresh_token;
      }
      return token;
    },

    // Gọi khi Client yêu cầu lấy dữ liệu Session (vd: dùng hook useSession hoặc getServerSession)
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as string | undefined;
        session.user.grade_level = token.grade_level as
          | string
          | number
          | undefined;
        session.user.is_new_user = token.is_new_user as boolean | undefined;
      }
      session.access_token = token.access_token as string | undefined;
      session.refresh_token = token.refresh_token as string | undefined; // US 6.2 (T6.13): expose refresh_token cho authFetch
      session.is_new_user = token.is_new_user as boolean | undefined; // US 8.3: expose cờ is_new_user cho client
      return session;
    },
  },
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
