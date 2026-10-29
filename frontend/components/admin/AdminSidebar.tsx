"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import {
  LayoutDashboard,
  Users,
  BookOpen,
  ShieldAlert,
  Settings,
  LogOut,
  X,
  ShieldCheck,
  FileText,
} from "lucide-react";

interface AdminSidebarProps {
  onCloseMobile?: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: {
    text: string;
    variant: "counter" | "danger" | "soft" | "new";
  };
}

interface NavGroup {
  groupTitle: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    groupTitle: "Tổng quan",
    items: [
      {
        name: "KPI Dashboard",
        href: "/admin",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    groupTitle: "Quản lý hệ thống",
    items: [
      {
        name: "Quản lý Users",
        href: "/admin/users",
        icon: Users,
      },
      {
        name: "Học liệu Toán 4-9",
        href: "/admin/content",
        icon: BookOpen,
      },
      {
        name: "Giám sát Safety AI",
        href: "/admin/safety",
        icon: ShieldAlert,
      },
      {
        name: "Tra Cứu Logs",
        href: "/admin/logs",
        icon: FileText,
      },
    ],
  },
  {
    groupTitle: "Cấu hình",
    items: [
      {
        name: "Cài đặt hệ thống",
        href: "/admin/settings",
        icon: Settings,
      },
    ],
  },
];

export default function AdminSidebar({ onCloseMobile }: AdminSidebarProps) {
  const pathname = usePathname();
  const { data: session } = useSession();

  const userName = session?.user?.name || "Quản Trị Viên";
  const userEmail = session?.user?.email || "admin@socratickid.edu.vn";

  const isItemActive = (href: string) => {
    if (href === "/admin") {
      return pathname === "/admin";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-72 h-full bg-[#F1CCA6] border-r border-[#C1762A]/20 flex flex-col justify-between shrink-0 select-none">
      {/* ── Brand Header (Đồng bộ chuẩn Parent Dashboard) ── */}
      <div>
        <div className="p-5 border-b border-[#C1762A]/20 flex items-center justify-between">
          <Link
            href="/admin"
            onClick={onCloseMobile}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-full overflow-hidden flex items-center justify-center hover:opacity-80 transition-opacity bg-[#F7ECE1] shadow-xs">
              <img
                src="/logo.png"
                alt="SocraticKid Logo"
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <h2 className="text-[#8C4905] font-extrabold italic text-lg tracking-tight leading-none">
                SocraticKid
              </h2>
              <p className="text-xs text-[#C1762A] font-bold mt-1 tracking-wide uppercase">
                Cổng Quản Trị
              </p>
            </div>
          </Link>

          {/* Nút đóng sidebar trên Mobile */}
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 rounded-lg text-[#8C4905] hover:bg-[#F7ECE1] transition-colors"
              aria-label="Đóng thanh điều hướng"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* ── Nav Items ── */}
        <nav className="p-3 space-y-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.groupTitle} className="space-y-1">
              <div className="px-3 text-xs font-bold text-[#8C4905] uppercase tracking-wider">
                {group.groupTitle}
              </div>

              <div className="space-y-1">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = isItemActive(item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={onCloseMobile}
                      className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-bold transition-all duration-150 ${
                        active
                          ? "bg-[#C1762A] text-white shadow-md transform hover:-translate-y-0.5"
                          : "text-[#8C4905] hover:bg-[#F7ECE1]/70"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Icon
                          className={`w-4 h-4 flex-shrink-0 transition-colors ${
                            active ? "text-white" : "text-[#8C4905]"
                          }`}
                        />
                        <span className="truncate">{item.name}</span>
                      </div>

                      {/* Badges / Counters */}
                      {item.badge && (
                        <div className="flex-shrink-0 ml-2">
                          {item.badge.variant === "danger" && (
                            <span className="bg-[#D93829] text-white text-[11px] font-bold px-2 py-0.5 rounded-full shadow-xs">
                              {item.badge.text}
                            </span>
                          )}
                          {item.badge.variant === "soft" && (
                            <span
                              className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                                active
                                  ? "bg-white/20 text-white"
                                  : "bg-[#F7ECE1] text-[#8C4905] border border-[#C1762A]/20"
                              }`}
                            >
                              {item.badge.text}
                            </span>
                          )}
                          {item.badge.variant === "new" && (
                            <span
                              className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${
                                active
                                  ? "bg-white text-[#C1762A]"
                                  : "bg-[#2A8C4A] text-white"
                              }`}
                            >
                              {item.badge.text}
                            </span>
                          )}
                        </div>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* ── Footer: Mini Profile & Đăng Xuất (Đồng bộ MonitorSidebar) ── */}
      <div className="p-4 border-t border-[#C1762A]/20 flex items-center justify-between bg-[#F1CCA6]">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {session?.user?.image ? (
            <img
              src={session.user.image}
              alt="Avatar"
              className="w-9 h-9 rounded-full border border-[#C1762A] shadow-xs"
            />
          ) : (
            <div className="w-9 h-9 bg-[#C1762A] rounded-full flex items-center justify-center text-white font-bold text-sm shadow-xs">
              {userName.charAt(0) || "A"}
            </div>
          )}
          <div className="min-w-0">
            <p className="text-sm font-bold text-[#8C4905] truncate">
              {userName}
            </p>
            <p className="text-xs text-[#C1762A] font-semibold flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-[#C1762A]" />
              Quản trị viên
            </p>
          </div>
        </div>

        <button
          onClick={() => signOut({ callbackUrl: "/" })}
          className="p-2 text-[#8C4905] hover:bg-[#F7AD62]/30 rounded-lg transition-colors cursor-pointer"
          title="Đăng xuất khỏi hệ thống"
        >
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
