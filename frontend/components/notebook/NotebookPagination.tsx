"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface NotebookPaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function NotebookPagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
}: NotebookPaginationProps) {
  if (totalPages <= 1) return null;

  const startIdx = (currentPage - 1) * pageSize + 1;
  const endIdx = Math.min(currentPage * pageSize, totalItems);

  // Dãy số trang hiển thị
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      if (currentPage <= 3) {
        pages.push(1, 2, 3, 4, "...", totalPages);
      } else if (currentPage >= totalPages - 2) {
        pages.push(1, "...", totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
      } else {
        pages.push(1, "...", currentPage - 1, currentPage, currentPage + 1, "...", totalPages);
      }
    }
    return pages;
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-5 px-1 select-none border-t border-[#F1CCA6]/60 mt-6">
      {/* Thông tin số lượng hiển thị */}
      <p className="text-xs text-[#7A3E04] font-medium">
        Hiển thị{" "}
        <span className="font-semibold text-[#1C1917] tabular-nums">
          {startIdx} - {endIdx}
        </span>{" "}
        trong{" "}
        <span className="font-semibold text-[#1C1917] tabular-nums">
          {totalItems}
        </span>{" "}
        bài toán (tối đa {pageSize} bài/trang)
      </p>

      {/* Dãy nút chuyển trang */}
      <div className="flex items-center gap-1.5">
        {/* Nút Previous */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          className={cn(
            "inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 ease-out cursor-pointer touch-manipulation focus-visible:outline-2 focus-visible:outline-[#C1762A]",
            currentPage <= 1
              ? "opacity-35 cursor-not-allowed text-[#7A3E04]/60 bg-[#F7ECE1]/50 border border-[#F1CCA6]/40"
              : "text-[#8C4905] bg-white hover:bg-[#F7ECE1] active:scale-[0.98] border border-[#F1CCA6] shadow-xs"
          )}
          aria-label="Trang trước"
        >
          <ChevronLeft size={14} />
          <span className="hidden sm:inline">Trang trước</span>
        </button>

        {/* Các số trang */}
        <div className="flex items-center gap-1">
          {getPageNumbers().map((p, idx) => {
            if (p === "...") {
              return (
                <span
                  key={`ellipsis-${idx}`}
                  className="w-7 h-7 flex items-center justify-center text-xs text-[#7A3E04]/60 font-bold tabular-nums"
                >
                  ...
                </span>
              );
            }

            const pageNum = p as number;
            const isCurrent = pageNum === currentPage;

            return (
              <button
                key={`page-${pageNum}`}
                type="button"
                onClick={() => onPageChange(pageNum)}
                className={cn(
                  "w-7 h-7 rounded-xl text-xs font-semibold transition-all duration-150 ease-out cursor-pointer touch-manipulation flex items-center justify-center tabular-nums focus-visible:outline-2 focus-visible:outline-[#C1762A]",
                  isCurrent
                    ? "bg-[#C1762A] text-white shadow-xs font-bold"
                    : "text-[#8C4905] bg-white hover:bg-[#F7ECE1] active:scale-[0.98] border border-[#F1CCA6]"
                )}
                aria-label={`Đến trang ${pageNum}`}
                aria-current={isCurrent ? "page" : undefined}
              >
                {pageNum}
              </button>
            );
          })}
        </div>

        {/* Nút Next */}
        <button
          type="button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          className={cn(
            "inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 ease-out cursor-pointer touch-manipulation focus-visible:outline-2 focus-visible:outline-[#C1762A]",
            currentPage >= totalPages
              ? "opacity-35 cursor-not-allowed text-[#7A3E04]/60 bg-[#F7ECE1]/50 border border-[#F1CCA6]/40"
              : "text-[#8C4905] bg-white hover:bg-[#F7ECE1] active:scale-[0.98] border border-[#F1CCA6] shadow-xs"
          )}
          aria-label="Trang sau"
        >
          <span className="hidden sm:inline">Trang sau</span>
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

export default NotebookPagination;
