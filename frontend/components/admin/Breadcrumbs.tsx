"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";

interface PathConfig {
  label: string;
  href: string;
}

const ROUTE_LABELS: Record<string, string> = {
  admin: "Dashboard",
  users: "Quản lý Users",
  content: "Học liệu Toán 4-9",
  safety: "Giám sát Safety AI",
  settings: "Cài đặt hệ thống",
};

export default function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean); // ['admin', 'users']

  // Tạo danh sách đường dẫn breadcrumb
  const crumbs: PathConfig[] = [{ label: "Admin Portal", href: "/admin" }];

  if (segments.length > 1) {
    let accumulatedPath = "";
    segments.forEach((seg, idx) => {
      accumulatedPath += `/${seg}`;
      if (idx === 0) return; // Đã có Admin Portal ở root
      const label = ROUTE_LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1);
      crumbs.push({
        label,
        href: accumulatedPath,
      });
    });
  } else if (segments.length === 1 && segments[0] === "admin") {
    crumbs.push({
      label: "KPI Dashboard",
      href: "/admin",
    });
  }

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs md:text-sm">
      {crumbs.map((crumb, index) => {
        const isLast = index === crumbs.length - 1;

        return (
          <div key={crumb.href + index} className="flex items-center gap-1.5">
            {index > 0 && (
              <ChevronRight className="w-3.5 h-3.5 text-[#7E6B5A] flex-shrink-0" />
            )}
            {isLast ? (
              <span className="font-bold text-[#8C4905]">
                {crumb.label}
              </span>
            ) : (
              <Link
                href={crumb.href}
                className="font-medium text-[#7E6B5A] hover:text-[#C1762A] transition-colors"
              >
                {crumb.label}
              </Link>
            )}
          </div>
        );
      })}
    </nav>
  );
}
