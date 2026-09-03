import NextAuth, { DefaultSession, DefaultUser } from "next-auth";
import { JWT, DefaultJWT } from "next-auth/jwt";

// 1. Mở rộng session và user của next-auth
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      role?: string;
    } & DefaultSession["user"];
  }

  interface User extends DefaultUser {
    id: string;
    role?: string;
  }
}

// 2. Mở rộng JWT của next-auth/jwt
declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    id: string;
    role?: string;
  }
}