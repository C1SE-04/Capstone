"use client";

import { signIn, useSession } from "next-auth/react";

export default function GoogleSignInButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <button
        disabled
        className="flex h-11 w-full max-w-sm items-center justify-center gap-3 rounded-xl bg-white px-5 text-sm font-medium text-[#7A3E04] shadow-xs border border-[#F1CCA6] transition-all sm:w-auto"
      >
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#C1762A] border-t-transparent" />
        Đang tải...
      </button>
    );
  }

  if (session) {
    return (
      <div className="flex h-11 items-center justify-center gap-3 rounded-xl bg-white px-5 text-sm font-medium text-[#1C1917] shadow-xs border border-[#F1CCA6] transition-all">
        <img
          src={session.user?.image || "/globe.svg"}
          alt="Avatar"
          className="h-6 w-6 rounded-full border border-[#F1CCA6]"
        />
        <span>Xin chào, <strong className="text-[#8C4905]">{session.user?.name}</strong></span>
      </div>
    );
  }

  return (
    <button
      onClick={() => signIn("google", { callbackUrl: "/onboarding" })}
      className="group flex h-11 w-full max-w-sm items-center justify-center gap-3 rounded-xl bg-white px-6 text-sm font-semibold text-[#1C1917] shadow-xs border border-[#F1CCA6] transition-all duration-150 ease-out hover:bg-[#F7ECE1]/60 hover:border-[#C1762A] focus-visible:outline-2 focus-visible:outline-[#C1762A] active:scale-[0.98] sm:w-auto"
    >
      <svg className="h-5 w-5 transition-transform group-hover:scale-110" viewBox="0 0 24 24">
        <path
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          fill="#4285F4"
        />
        <path
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          fill="#34A853"
        />
        <path
          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          fill="#FBBC05"
        />
        <path
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          fill="#EA4335"
        />
        <path d="M1 1h22v22H1z" fill="none" />
      </svg>
      Đăng nhập bằng Google
    </button>
  );
}
