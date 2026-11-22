import type { DefaultSession, DefaultUser } from "next-auth";
import type { DefaultJWT } from "next-auth/jwt";

// 1. Mở rộng session và user của next-auth
declare module "next-auth" {
  interface Session {
    access_token?: string;
    refresh_token?: string;
    is_new_user?: boolean;
    user: {
      id: string;
      role?: string;
      grade_level?: string | number;
      is_new_user?: boolean;
    } & DefaultSession["user"];
  }

  interface User extends DefaultUser {
    id: string;
    role?: string;
    access_token?: string;
    refresh_token?: string;
    grade_level?: string | number;
    is_new_user?: boolean;
  }
}

// 2. Mở rộng JWT của next-auth/jwt
declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    id: string;
    role?: string;
    access_token?: string;
    refresh_token?: string;
    grade_level?: string | number;
    is_new_user?: boolean;
  }
}