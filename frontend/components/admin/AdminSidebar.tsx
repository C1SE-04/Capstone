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
        badge: { text: "12.4k", variant: "soft" },
      },
      {
        name: "Học liệu Toán 4-9",
        href: "/admin/content",
        icon: BookOpen,
        badge: { text: "Mới", variant: "new" },
      },
      {
        name: "Giám sát Safety AI",
        href: "/admin/safety",
        icon: ShieldAlert,
        badge: { text: "3", variant: "danger" },
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

  const userName = session?.user?.name || "Nguyễn Văn Bảo";
  const userEmail = session?.user?.email || "admin@socratickid.vn";
  const userInitials = userName
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "AD";

  const isItemActive = (href: string) => {
    if (href === "/admin") {
      return pathname === "/admin";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className="w-64 h-full bg-[#FFFDF9] border-r border-[#E8D5C4] flex flex-col justify-between select-none">
      {/* ── Brand Header ── */}
      <div>
        <div className="h-16 px-5 border-b border-[#E8D5C4] flex items-center justify-between">
          <Link
            href="/admin"
            onClick={onCloseMobile}
            className="flex items-center gap-3 group"
          >
            <div className="w-[38px] h-[38px] rounded-[10px] bg-gradient-to-br from-[#C1762A] to-[#8C4905] text-white flex items-center justify-center font-extrabold text-lg shadow-[0_3px_8px_rgba(193,118,42,0.25)] transition-transform group-hover:scale-105">
              S
            </div>
            <div>
              <div className="font-extrabold text-[#C1762A] text-base leading-tight tracking-tight">
                SocraticKid
              </div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-[#7E6B5A]">
                Cổng Quản Trị
              </div>
            </div>
          </Link>

          {/* Nút đóng sidebar trên Mobile */}
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1.5 rounded-lg text-[#7E6B5A] hover:bg-[#F7ECE1] hover:text-[#8C4905] transition-colors"
              aria-label="Đóng thanh điều hướng"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* ── Nav Items ── */}
        <nav className="p-3 space-y-5">
          {NAV_GROUPS.map((group) => (
            <div key={group.groupTitle} className="space-y-1">
              <div className="px-3 text-[11px] font-bold uppercase tracking-wider text-[#A18E7F]">
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
                      className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150 ${
                        active
                          ? "bg-[#C1762A] text-white shadow-[0_3px_10px_rgba(193,118,42,0.3)]"
                          : "text-[#4A3B2C] hover:bg-[#F7ECE1] hover:text-[#8C4905]"
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Icon
                          className={`w-[18px] h-[18px] flex-shrink-0 transition-colors ${
                            active ? "text-white" : "text-[#7E6B5A]"
                          }`}
                        />
                        <span className="truncate">{item.name}</span>
                      </div>

                      {/* Badges / Counters */}
                      {item.badge && (
                        <div className="flex-shrink-0 ml-2">
                          {item.badge.variant === "danger" && (
                            <span className="bg-[#D93829] text-white text-[11px] font-bold px-1.5 py-0.5 rounded-full">
                              {item.badge.text}
                            </span>
                          )}
                          {item.badge.variant === "soft" && (
                            <span
                              className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                                active
                                  ? "bg-white/20 text-white"
                                  : "bg-[#F1CCA6] text-[#8C4905]"
                              }`}
                            >
                              {item.badge.text}
                            </span>
                          )}
                          {item.badge.variant === "new" && (
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                active
                                  ? "bg-white/25 text-white"
                                  : "bg-[#EEF6FC] text-[#2B78C5] border border-[#BADEF7]"
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

      {/* ── Footer: Admin Profile & Logout ── */}
      <div className="p-3 border-t border-[#E8D5C4] bg-[#FFFDF9]">
        <div className="flex items-center gap-2.5 p-2 rounded-xl hover:bg-[#F7ECE1]/60 transition-colors">
          <div className="w-9 h-9 rounded-full bg-[#F1CCA6] border-2 border-[#C1762A] flex items-center justify-center font-extrabold text-[#8C4905] text-xs flex-shrink-0 shadow-sm">
            {userInitials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-bold text-[#2A1C0E] truncate">
              {userName}
            </div>
            <div className="text-[10px] font-semibold text-[#C1762A] truncate">
              Super Admin
            </div>
          </div>
          <button
            onClick={() => signOut({ callbackUrl: "/" })}
            title="Đăng xuất khỏi Cổng Quản Trị"
            className="p-1.5 rounded-lg border border-[#E8D5C4] text-[#7E6B5A] hover:bg-[#FDF0ED] hover:text-[#D93829] hover:border-[#F5BCB4] transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
