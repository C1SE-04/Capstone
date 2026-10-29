"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Sparkles,
  Search,
  Filter,
  CheckCircle2,
  RefreshCw,
  Code2,
  BookOpen,
  Copy,
  Layers,
  Info,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { authFetch } from "@/lib/authFetch";

interface TopicItem {
  order: number;
  name: string;
  grade: number;
  is_active: boolean;
}

interface GradeDetail {
  grade: number;
  total: number;
  active_count: number;
  inactive_count: number;
  topics: TopicItem[];
  prompt_preview: string;
}

interface PromptCurriculumResponse {
  total_raw: number;
  total_filtered: number;
  grades: Record<string, GradeDetail>;
}

export default function PromptCurriculumPage() {
  const [data, setData] = useState<PromptCurriculumResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Bộ lọc
  const [selectedGrade, setSelectedGrade] = useState<number | "ALL">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal xem Prompt Preview
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await authFetch(
        `${BACKEND_URL}/admin/curriculum/prompt-curriculum`
      );
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setErrorMsg("Không thể tải danh sách dạng toán nạp vào AI Prompt.");
      }
    } catch {
      setErrorMsg("Lỗi kết nối tới máy chủ.");
    } finally {
      setIsLoading(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Gom danh sách tất cả các dạng toán
  const allTopics = useMemo(() => {
    if (!data?.grades) return [];
    const list: TopicItem[] = [];
    Object.keys(data.grades)
      .sort((a, b) => Number(a) - Number(b))
      .forEach((g) => {
        list.push(...(data.grades[g]?.topics || []));
      });
    return list;
  }, [data]);

  // Lọc theo Khối lớp & Tìm kiếm
  const filteredTopics = useMemo(() => {
    return allTopics.filter((t) => {
      if (selectedGrade !== "ALL" && t.grade !== selectedGrade) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        if (!t.name.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [allTopics, selectedGrade, searchQuery]);

  // Thống kê nhanh
  const stats = useMemo(() => {
    const raw = data?.total_raw || 420;
    const filtered = data?.total_filtered || 235;
    const percentReduction = Math.round(((raw - filtered) / raw) * 100);
    const active = allTopics.filter((t) => t.is_active).length;
    return { raw, filtered, percentReduction, active };
  }, [data, allTopics]);

  // Lấy Prompt Preview của lớp đang chọn
  const currentPromptPreview = useMemo(() => {
    if (!data?.grades) return "";
    if (selectedGrade === "ALL") {
      // Mặc định hiển thị lớp 4 khi chọn ALL
      return data.grades["4"]?.prompt_preview || "";
    }
    return data.grades[String(selectedGrade)]?.prompt_preview || "";
  }, [data, selectedGrade]);

  const handleCopyPrompt = () => {
    if (!currentPromptPreview) return;
    navigator.clipboard.writeText(currentPromptPreview);
    setCopiedPrompt(true);
    setTimeout(() => setCopiedPrompt(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* 1. Header Trang & Nút Quay lại */}
      <div className="bg-white rounded-xl border border-stone-200/90 p-5 sm:p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-2">
            <Link
              href="/admin/content"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-stone-500 hover:text-[#C1762A] transition-colors"
            >
              <ArrowLeft size={14} />
              <span>Quay lại Quản lý Học liệu (SGK gốc)</span>
            </Link>

            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-amber-50 text-[#C1762A] border border-amber-200/60 flex items-center justify-center shrink-0">
                <Sparkles size={22} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg sm:text-xl font-bold text-stone-900 tracking-tight">
                    Mục Lục Chuyên Đề Đã Lọc Cho AI Prompt
                  </h1>
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-amber-100/80 text-amber-900 border border-amber-200">
                    {stats.filtered} dạng toán cốt lõi
                  </span>
                </div>
                <p className="text-xs text-stone-500 mt-0.5 max-w-3xl">
                  Chỉ giữ lại các khái niệm & dạng toán thuần túy nạp trực tiếp vào
                  System Prompt (đã loại bỏ bài Luyện tập chung, Ôn tập cuối kỳ và
                  Hoạt động trải nghiệm để tiết kiệm token và định vị chuẩn xác trình
                  độ học sinh).
                </p>
              </div>
            </div>
          </div>

          {/* Cụm nút hành động */}
          <div className="flex items-center gap-2 self-start sm:self-center shrink-0">
            {/* Nút Xem mẫu Prompt AI */}
            <button
              onClick={() => setIsPreviewOpen(true)}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold text-stone-800 bg-stone-100 hover:bg-stone-200/80 border border-stone-200/80 transition-all cursor-pointer active:scale-95 shadow-2xs"
              title="Xem chuỗi Prompt ngữ cảnh thực tế được sinh ra"
            >
              <Code2 size={14} className="text-stone-600" />
              <span>Xem Prompt Mẫu</span>
            </button>

            {/* Nút Làm mới */}
            <button
              onClick={fetchData}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-stone-700 bg-white hover:bg-stone-50 border border-stone-200 transition-all cursor-pointer active:scale-95 shadow-2xs"
              title="Làm mới dữ liệu"
            >
              <RefreshCw size={13} className={cn(isLoading && "animate-spin")} />
              <span className="hidden sm:inline">Làm mới</span>
            </button>
          </div>
        </div>

        {/* 4 Thẻ KPI Tinh Gọn */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-5 mt-5 border-t border-stone-100 text-xs">
          <div className="p-3 rounded-lg bg-stone-50 border border-stone-200/60 flex flex-col justify-between">
            <span className="text-stone-500 font-medium">1. Tổng bài SGK thô:</span>
            <span className="font-bold text-stone-900 text-base mt-1">
              {stats.raw} <span className="text-xs font-normal text-stone-500">bài học</span>
            </span>
          </div>

          <div className="p-3 rounded-lg bg-amber-50/70 border border-amber-200/60 flex flex-col justify-between">
            <span className="text-amber-800 font-medium">2. Đã lọc cho AI Prompt:</span>
            <span className="font-bold text-amber-900 text-base mt-1">
              {stats.filtered} <span className="text-xs font-normal text-amber-700">dạng toán cốt lõi</span>
            </span>
          </div>

          <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-200/60 flex flex-col justify-between">
            <span className="text-emerald-800 font-medium">3. Mức độ tinh gọn:</span>
            <span className="font-bold text-emerald-900 text-base mt-1">
              -{stats.percentReduction}% <span className="text-xs font-normal text-emerald-700">bài thừa & token</span>
            </span>
          </div>

          <div className="p-3 rounded-lg bg-sky-50/70 border border-sky-200/60 flex flex-col justify-between">
            <span className="text-sky-800 font-medium">4. Đang nạp vào Prompt:</span>
            <span className="font-bold text-sky-900 text-base mt-1">
              {stats.active}/{stats.filtered} <span className="text-xs font-normal text-sky-700">kích hoạt</span>
            </span>
          </div>
        </div>
      </div>

      {/* 2. Thanh lọc Khối lớp & Ô Tìm kiếm */}
      <div className="bg-white rounded-xl border border-stone-200/90 p-4 shadow-2xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Tabs Khối Lớp */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
            <span className="text-xs font-bold text-stone-500 uppercase tracking-wider mr-1 shrink-0 flex items-center gap-1">
              <Filter size={12} />
              Khối lớp:
            </span>

            <button
              onClick={() => setSelectedGrade("ALL")}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer",
                selectedGrade === "ALL"
                  ? "bg-[#C1762A] text-white shadow-2xs"
                  : "bg-stone-100 text-stone-600 hover:bg-stone-200/80"
              )}
            >
              Tất cả ({stats.filtered})
            </button>

            {[4, 5, 6, 7, 8, 9].map((g) => {
              const count = data?.grades[String(g)]?.total ?? 0;
              return (
                <button
                  key={g}
                  onClick={() => setSelectedGrade(g)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer",
                    selectedGrade === g
                      ? "bg-[#C1762A] text-white shadow-2xs"
                      : "bg-stone-100 text-stone-600 hover:bg-stone-200/80"
                  )}
                >
                  Toán Lớp {g} ({count})
                </button>
              );
            })}
          </div>

          {/* Ô Tìm Kiếm Nhanh */}
          <div className="relative w-full md:w-72 shrink-0">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm dạng toán (vd: phân số, tỉ lệ...)"
              className="w-full pl-9 pr-8 py-1.5 rounded-lg border border-stone-200 text-xs text-stone-800 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 focus:border-[#C1762A] transition-all bg-stone-50/50"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
              >
                <X size={13} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 3. Bảng Danh Sách Các Dạng Toán Cốt Lõi */}
      <div className="bg-white rounded-xl border border-stone-200/90 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-stone-200 flex items-center justify-between bg-stone-50/50 text-xs text-stone-600 font-medium">
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-[#C1762A]" />
            <span>
              Hiển thị{" "}
              <strong className="text-stone-900 font-bold">
                {filteredTopics.length}
              </strong>{" "}
              dạng toán {selectedGrade !== "ALL" ? `của Toán Lớp ${selectedGrade}` : "trên toàn bộ 6 khối lớp"}
            </span>
          </div>

          {selectedGrade !== "ALL" && (
            <button
              onClick={() => setIsPreviewOpen(true)}
              className="text-[#C1762A] hover:underline font-semibold flex items-center gap-1 cursor-pointer"
            >
              <Code2 size={13} />
              Xem Prompt Toán {selectedGrade}
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="py-20 text-center text-stone-500 space-y-2">
            <RefreshCw size={24} className="animate-spin mx-auto text-[#C1762A]" />
            <p className="text-xs">Đang tải danh sách dạng toán cốt lõi...</p>
          </div>
        ) : errorMsg ? (
          <div className="py-12 text-center text-rose-600 text-xs font-semibold">
            {errorMsg}
          </div>
        ) : filteredTopics.length === 0 ? (
          <div className="py-16 text-center text-stone-400 space-y-2">
            <BookOpen size={28} className="mx-auto text-stone-300" />
            <p className="text-xs">Không tìm thấy dạng toán nào phù hợp với từ khóa.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-stone-50/80 text-stone-600 uppercase font-bold text-[11px] border-b border-stone-200/80">
                <tr>
                  <th className="py-3 px-4 w-14 text-center">STT</th>
                  <th className="py-3 px-4 w-28 text-center">Khối lớp</th>
                  <th className="py-3 px-4">Tên Dạng Toán / Khái Niệm Cốt Lõi Đưa Vào Prompt</th>
                  <th className="py-3 px-4 w-44">Bộ SGK</th>
                  <th className="py-3 px-4 w-48 text-center">Trạng thái nạp AI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {filteredTopics.map((item, idx) => (
                  <tr
                    key={`${item.grade}-${item.name}-${idx}`}
                    className="hover:bg-amber-50/30 transition-colors"
                  >
                    <td className="py-3 px-4 text-center text-stone-400 font-mono">
                      {idx + 1}
                    </td>

                    <td className="py-3 px-4 text-center">
                      <span className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-900 border border-amber-200">
                        Lớp {item.grade}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-semibold text-stone-900 text-[13px]">
                        {item.name}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-stone-500 font-medium">
                      Kết Nối Tri Thức
                    </td>

                    <td className="py-3 px-4 text-center">
                      {item.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 size={12} className="text-emerald-500" />
                          Đang nạp vào Prompt
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-stone-100 text-stone-500 border border-stone-200">
                          Đã ẩn (Tắt trong DB)
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 4. Modal Xem Prompt Mẫu Ngữ Cảnh AI */}
      {isPreviewOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-3xl w-full border border-stone-200 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 sm:p-5 border-b border-stone-200 flex items-center justify-between bg-stone-50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-amber-100 text-[#C1762A] flex items-center justify-center">
                  <Code2 size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-stone-900">
                    System Prompt Ngữ Cảnh:{" "}
                    {selectedGrade === "ALL" ? "Toán Lớp 4 (Mẫu)" : `Toán Lớp ${selectedGrade}`}
                  </h3>
                  <p className="text-[11px] text-stone-500">
                    Đoạn văn bản thực tế được nạp vào AI khi học sinh khối lớp này tương tác
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyPrompt}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-white border border-stone-200 hover:bg-stone-50 text-stone-700 cursor-pointer active:scale-95 transition-all shadow-2xs"
                  title="Sao chép nội dung prompt"
                >
                  <Copy size={13} />
                  <span>{copiedPrompt ? "Đã chép!" : "Sao chép"}</span>
                </button>

                <button
                  onClick={() => setIsPreviewOpen(false)}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-400 hover:text-stone-600 hover:bg-stone-200/60 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="p-5 overflow-y-auto flex-1 bg-stone-900 text-stone-100 font-mono text-xs leading-relaxed">
              <pre className="whitespace-pre-wrap font-mono">
                {currentPromptPreview || "Chưa có dữ liệu prompt preview."}
              </pre>
            </div>

            <div className="p-3 bg-stone-50 border-t border-stone-200 text-right">
              <button
                onClick={() => setIsPreviewOpen(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-bold text-white bg-[#C1762A] hover:bg-[#8C4905] transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

