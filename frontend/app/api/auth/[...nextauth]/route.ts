import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";
import { PrismaAdapter } from "@next-auth/prisma-adapter";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// Cấu hình NextAuth xử lý xác thực (Authentication)
export const authOptions: NextAuthOptions = {
  // PrismaAdapter giúp lưu trữ session/user vào database (tuy nhiên ta đang dùng JWT nên adapter này có thể chỉ dùng cho GoogleProvider)
  adapter: PrismaAdapter(prisma),
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
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
          const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
          const res = await fetch(`${backendUrl}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
              username: credentials.email,
              password: credentials.password,
            }),
          });

          if (!res.ok) return null;

          const data = await res.json();

          // Decode JWT payload (Access Token) từ Backend trả về để lấy thông tin user (ID, Email, Role)
          const payload = JSON.parse(
            Buffer.from(data.access_token.split(".")[1], "base64").toString()
          );

          // Trả về object user để NextAuth lưu vào phiên đăng nhập (Session)
          return {
            id: payload.sub,
            email: payload.email,
            name: payload.email.split("@")[0], // Dùng phần trước @ làm display name
            role: payload.role,
            access_token: data.access_token,
          };
        } catch {
          return null;
        }
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: "/",
  },
  // Các callback xử lý khi tạo Token và Session
  callbacks: {
    // Gọi khi tạo hoặc cập nhật JWT token
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.role = user.role;
        token.access_token = user.access_token;
      }
      return token;
    },
    // Gọi khi Client yêu cầu lấy dữ liệu Session (vd: dùng hook useSession)
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as string | undefined;
        session.access_token = token.access_token as string | undefined;
      }
      return session;
    },
  },
};

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
