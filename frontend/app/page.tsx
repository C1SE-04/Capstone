"use client";
import { signIn, signOut, useSession } from "next-auth/react";

export default function Home() {
  const { data: session } = useSession();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50">
      <div className="p-8 bg-white rounded-xl shadow-lg text-center">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">Capstone Project</h1>
        
        {!session ? (
          <button
            onClick={() => signIn("google")}
            className="flex items-center justify-center gap-3 w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm bg-white hover:bg-gray-50 transition-all active:scale-95"
          >
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" className="w-5 h-5" />
            <span className="text-gray-700 font-medium">Đăng nhập với Google</span>
          </button>
        ) : (
          <div>
            <p className="mb-4 text-green-600 font-medium">Xin chào, {session.user?.name}!</p>
            <img src={session.user?.image || ""} alt="Avatar" className="w-16 h-16 rounded-full mx-auto mb-4" />
            <button
              onClick={() => signOut()}
              className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all active:scale-95"
            >
              Đăng xuất
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
