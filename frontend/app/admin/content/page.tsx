"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  BookOpen,
  Search,
  Filter,
  RefreshCw,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Database,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CurriculumTopicItem, SyncVietjackResult } from "@/types/admin";
import { SyncVietjackModal } from "@/components/admin/SyncVietjackModal";
import { authFetch } from "@/lib/authFetch";

const PAGE_SIZE = 15; // Phân trang 15 chuyên đề mỗi trang trong bảng quản trị

export default function AdminContentPage() {
  const [topics, setTopics] = useState<CurriculumTopicItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Bộ lọc & Tìm kiếm
  const [selectedGrade, setSelectedGrade] = useState<number | "ALL">("ALL");
  const [selectedSemester, setSelectedSemester] = useState<number | "ALL">("ALL");
  const [selectedStatus, setSelectedStatus] = useState<"ALL" | "ACTIVE" | "INACTIVE">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Modal đồng bộ VietJack
  const [isSyncModalOpen, setIsSyncModalOpen] = useState(false);

  // Trạng thái Toggle đang gửi request
  const [togglingId, setTogglingId] = useState<string | null>(null);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

  // Hiển thị toast thông báo
  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  }, []);

  // 1. Fetch danh sách chuyên đề từ Backend DB (curriculum_topics)
  const fetchTopics = useCallback(async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/curriculum/topics`);
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : data.items || [];
        setTopics(items);
      } else {
        // Fallback thử endpoint mock nếu cần
        const mockRes = await authFetch(`${BACKEND_URL}/admin/mock/curriculum/topics`);
        if (mockRes.ok) {
          const data = await mockRes.json();
          const items = Array.isArray(data) ? data : data.items || [];
          setTopics(items);
        } else {
          setErrorMsg("Chưa thể tải danh mục chuyên đề từ cơ sở dữ liệu.");
        }
      }
    } catch {
      setErrorMsg("Lỗi kết nối mạng tới máy chủ quản trị.");
    } finally {
      setIsLoading(false);
    }
  }, [BACKEND_URL]);

  useEffect(() => {
    let ignore = false;
    const init = async () => {
      try {
        const res = await authFetch(`${BACKEND_URL}/admin/curriculum/topics`);
        if (res.ok && !ignore) {
          const data = await res.json();
          setTopics(Array.isArray(data) ? data : data.items || []);
        } else {
          const mockRes = await authFetch(`${BACKEND_URL}/admin/mock/curriculum/topics`);
          if (mockRes.ok && !ignore) {
            const data = await mockRes.json();
            setTopics(Array.isArray(data) ? data : data.items || []);
          }
        }
      } catch {
        if (!ignore) setErrorMsg("Lỗi nạp dữ liệu chuyên đề.");
      } finally {
        if (!ignore) setIsLoading(false);
      }
    };
    init();
    return () => {
      ignore = true;
    };
  }, [BACKEND_URL]);

  // 2. Kích hoạt cào và đồng bộ từ VietJack
  const handleSyncVietjack = useCallback(async (): Promise<SyncVietjackResult | null> => {
    try {
      const res = await authFetch(`${BACKEND_URL}/admin/curriculum/sync-vietjack`, {
        method: "POST",
      });

      if (res.ok) {
        const result: SyncVietjackResult = await res.json();
        return result;
      } else {
        const mockRes = await authFetch(`${BACKEND_URL}/admin/mock/curriculum/sync-vietjack`, {
          method: "POST",
        });
        if (mockRes.ok) {
          return await mockRes.json();
        }
      }
      return null;
    } catch {
      return null;
    }
  }, [BACKEND_URL]);

  const handleSyncSuccessDone = useCallback(() => {
    fetchTopics();
    showToast("Đã đồng bộ thành công chuyên đề môn Toán từ VietJack!");
  }, [fetchTopics, showToast]);

  // 3. Toggle trạng thái Ẩn/Hiện tức thì theo [AC 8.4.3]
  const handleToggleTopic = async (topicId: string, currentActive: boolean) => {
    if (togglingId === topicId) return;

    // Optimistic Update: cập nhật ngay trên giao diện
    const newActive = !currentActive;
    setTopics((prev) =>
      prev.map((t) => (t.id === topicId ? { ...t, is_active: newActive } : t))
    );
    setTogglingId(topicId);

    try {
      const res = await authFetch(
        `${BACKEND_URL}/admin/curriculum/topics/${topicId}/toggle`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_active: newActive }),
        }
      );

      if (res.ok) {
        showToast(
          newActive
            ? "Đã bật chuyên đề thành công!"
            : "Đã chuyển chuyên đề sang trạng thái Ẩn (giảm tải)."
        );
      } else {
        // Rollback nếu lỗi
        setTopics((prev) =>
          prev.map((t) => (t.id === topicId ? { ...t, is_active: currentActive } : t))
        );
        showToast("Lỗi cập nhật trạng thái chuyên đề trên máy chủ.");
      }
    } catch {
      setTopics((prev) =>
        prev.map((t) => (t.id === topicId ? { ...t, is_active: currentActive } : t))
      );
      showToast("Lỗi mạng khi cập nhật trạng thái.");
    } finally {
      setTogglingId(null);
    }
  };

  // Lọc và sắp xếp danh sách chuyên đề theo đúng thứ tự bài học từ trên xuống dưới
  const filteredTopics = useMemo(() => {
    return topics
      .filter((t) => {
        // Lọc khối lớp
        if (selectedGrade !== "ALL" && t.grade !== selectedGrade) {
          return false;
        }
        // Lọc học kỳ
        if (selectedSemester !== "ALL" && t.semester !== selectedSemester) {
          return false;
        }
        // Lọc trạng thái
        if (selectedStatus === "ACTIVE" && !t.is_active) {
          return false;
        }
        if (selectedStatus === "INACTIVE" && t.is_active) {
          return false;
        }
        // Tìm kiếm theo từ khóa
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const inTopic = t.topic_name?.toLowerCase().includes(q);
          const inChapter = t.chapter_name?.toLowerCase().includes(q);
          const inBook = t.book_series?.toLowerCase().includes(q);
          if (!inTopic && !inChapter && !inBook) return false;
        }
        return true;
      })
      .sort((a, b) => {
        // Ưu tiên khối lớp trước, sau đó sắp xếp theo order_index (từ Bài 1 đến Bài cuối)
        if (a.grade !== b.grade) return a.grade - b.grade;
        return (a.order_index ?? 0) - (b.order_index ?? 0);
      });
  }, [topics, selectedGrade, selectedSemester, selectedStatus, searchQuery]);

  // Phân trang
  const totalItems = filteredTopics.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const paginatedTopics = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredTopics.slice(start, start + PAGE_SIZE);
  }, [filteredTopics, currentPage]);

  // Thống kê nhanh
  const stats = useMemo(() => {
    const total = topics.length;
    const active = topics.filter((t) => t.is_active).length;
    const inactive = total - active;
    return { total, active, inactive };
  }, [topics]);

  return (
    <div className="space-y-6">
      {/* Toast thông báo */}
      {toastMessage && (
        <div className="fixed top-5 right-5 z-[70] px-4 py-2.5 rounded-xl bg-stone-900 text-white text-xs font-semibold shadow-xl border border-stone-700 animate-in fade-in slide-in-from-top-2 duration-150 flex items-center gap-2">
          <CheckCircle2 size={15} className="text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* 1. Header Trang & Nút Cào VietJack 1-Click ([AC 8.4.1]) */}
      <div className="bg-white rounded-xl border border-stone-200/90 p-5 sm:p-6 shadow-2xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-xl bg-amber-50 text-[#C1762A] border border-amber-200/60 flex items-center justify-center shrink-0">
              <BookOpen size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-bold text-stone-900 tracking-tight">
                  Quản Lý Chuyên Đề & Học Liệu
                </h1>
                <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-stone-100 text-stone-700">
                  {stats.total} chuyên đề
                </span>
              </div>
              <p className="text-xs text-stone-500 mt-0.5">
                Chương trình học môn Toán chuẩn SGK mới (Kết Nối Tri Thức, Cánh Diều) lớp 4 đến lớp 9
              </p>
            </div>
          </div>

          {/* Cụm nút hành động bên phải */}
          <div className="flex items-center gap-2.5 self-start lg:self-auto">
            {/* Nút Xem danh sách các bài sau khi lọc nạp vào AI Prompt */}
            <Link
              href="/admin/content/prompt-topics"
              className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-xl text-xs font-bold text-amber-950 bg-amber-50 hover:bg-amber-100/90 border border-amber-300/80 transition-all shadow-2xs active:scale-95 cursor-pointer touch-manipulation group"
              title="Xem danh sách 235 dạng toán cốt lõi sau khi lọc nạp vào System Prompt AI"
            >
              <Sparkles size={14} className="text-[#C1762A] group-hover:scale-110 transition-transform" />
              <span>Xem Bài Lọc Cho AI Prompt</span>
            </Link>

            {/* Nút Cào & Đồng bộ từ VietJack nổi bật theo Sprint 8 */}
            <button
              onClick={() => setIsSyncModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-[#C1762A] hover:bg-[#8C4905] active:scale-95 transition-all shadow-xs cursor-pointer touch-manipulation group"
              title="Kích hoạt tự động cào và đồng bộ mục lục SGK mới từ VietJack"
            >
              <RefreshCw size={14} className="group-hover:rotate-180 transition-transform duration-500" />
              <span>Cào & Đồng bộ từ VietJack</span>
            </button>

            {/* Nút Tải lại danh sách */}
            <button
              onClick={fetchTopics}
              disabled={isLoading}
              className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-stone-700 bg-white hover:bg-stone-50 border border-stone-200 transition-all cursor-pointer active:scale-95 shadow-2xs"
              title="Làm mới bảng"
            >
              <RefreshCw size={13} className={cn(isLoading && "animate-spin")} />
              <span className="hidden sm:inline">Làm mới</span>
            </button>
          </div>
        </div>

        {/* 3 Thẻ thống kê nhanh */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-5 mt-5 border-t border-stone-100 text-xs">
          <div className="p-3 rounded-lg bg-stone-50 border border-stone-200/60 flex items-center justify-between">
            <span className="text-stone-500 font-medium">Tổng bài học trong DB:</span>
            <span className="font-bold text-stone-900">{stats.total} bài</span>
          </div>
          <div className="p-3 rounded-lg bg-emerald-50/70 border border-emerald-200/60 flex items-center justify-between">
            <span className="text-emerald-700 font-medium">Đang kích hoạt (Active):</span>
            <span className="font-bold text-emerald-800">{stats.active} bài</span>
          </div>
          <div className="p-3 rounded-lg bg-stone-100/70 border border-stone-200/60 flex items-center justify-between">
            <span className="text-stone-500 font-medium">Đã ẩn (Giảm tải):</span>
            <span className="font-bold text-stone-700">{stats.inactive} bài</span>
          </div>
        </div>
      </div>

      {/* 2. Thanh lọc theo khối lớp & Bộ tìm kiếm */}
      <div className="bg-white rounded-xl border border-stone-200/90 p-4 shadow-2xs space-y-3">
        {/* Hàng Tabs chọn khối lớp (4 - 9) */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          <span className="text-xs font-bold text-stone-500 uppercase tracking-wider mr-1 shrink-0 flex items-center gap-1">
            <Filter size={12} />
            Khối lớp:
          </span>
          <button
            onClick={() => {
              setSelectedGrade("ALL");
              setCurrentPage(1);
            }}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0 transition-all cursor-pointer",
              selectedGrade === "ALL"
                ? "bg-[#C1762A] text-white shadow-2xs font-bold"
                : "bg-stone-50 text-stone-700 hover:bg-stone-100 border border-stone-200"
            )}
          >
            Tất cả lớp (4 - 9)
          </button>
          {[4, 5, 6, 7, 8, 9].map((g) => (
            <button
              key={`grade-btn-${g}`}
              onClick={() => {
                setSelectedGrade(g);
                setCurrentPage(1);
              }}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-semibold shrink-0 transition-all cursor-pointer",
                selectedGrade === g
                  ? "bg-[#C1762A] text-white shadow-2xs font-bold"
                  : "bg-stone-50 text-stone-700 hover:bg-stone-100 border border-stone-200"
              )}
            >
              Toán Lớp {g}
            </button>
          ))}
        </div>

        {/* Hàng ô tìm kiếm và các dropdown lọc chi tiết */}
        <div className="pt-2 border-t border-stone-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5 flex-1 min-w-0">
            {/* Ô tìm kiếm */}
            <div className="relative w-72 sm:w-80">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400"
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Tìm kiếm bài học, chương lớn..."
                className="w-full pl-9 pr-3 py-1.5 bg-stone-50/50 border border-stone-200 rounded-lg text-xs text-stone-800 placeholder:text-stone-400 focus:outline-none focus:bg-white focus:border-[#C1762A] focus:ring-1 focus:ring-[#C1762A]/20 transition-all shadow-2xs"
              />
            </div>

            {/* Dropdown Học kỳ */}
            <select
              value={selectedSemester}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedSemester(val === "ALL" ? "ALL" : Number(val));
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 bg-white border border-stone-200 rounded-lg text-xs font-semibold text-stone-700 hover:border-stone-300 focus:outline-none focus:border-[#C1762A] cursor-pointer shadow-2xs transition-all"
            >
              <option value="ALL">Tất cả học kỳ</option>
              <option value="1">Học kỳ 1</option>
              <option value="2">Học kỳ 2</option>
            </select>

            {/* Dropdown Trạng thái */}
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value as any);
                setCurrentPage(1);
              }}
              className="px-2.5 py-1.5 bg-white border border-stone-200 rounded-lg text-xs font-semibold text-stone-700 hover:border-stone-300 focus:outline-none focus:border-[#C1762A] cursor-pointer shadow-2xs transition-all"
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="ACTIVE">Đang bật (Active)</option>
              <option value="INACTIVE">Đã ẩn (Disabled)</option>
            </select>
          </div>

          <span className="text-xs text-stone-500 font-medium">
            Tìm thấy <strong className="text-stone-800">{filteredTopics.length}</strong> chuyên đề
          </span>
        </div>
      </div>

      {/* 3. Bảng Chuyên Đề Đầy Đủ ([AC 8.4.2] & [AC 8.4.3]) */}
      <div className="bg-white rounded-xl border border-stone-200/90 shadow-2xs overflow-hidden">
        {isLoading ? (
          /* Skeleton Loader */
          <div className="p-6 space-y-3 animate-pulse">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-12 bg-stone-100 rounded-lg w-full" />
            ))}
          </div>
        ) : errorMsg ? (
          /* Error State */
          <div className="p-10 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
              <AlertCircle size={22} />
            </div>
            <p className="text-xs text-stone-600">{errorMsg}</p>
            <button
              onClick={fetchTopics}
              className="px-3.5 py-1.5 bg-[#C1762A] text-white rounded-lg text-xs font-bold hover:bg-[#8C4905] transition-colors cursor-pointer"
            >
              Tải lại
            </button>
          </div>
        ) : filteredTopics.length === 0 ? (
          /* Empty State */
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-stone-100 text-stone-400 flex items-center justify-center mx-auto">
              <Layers size={22} />
            </div>
            <p className="text-sm font-bold text-stone-800">
              Không tìm thấy chuyên đề phù hợp với bộ lọc
            </p>
            <p className="text-xs text-stone-500">
              Vui lòng thử điều chỉnh lại khối lớp, học kỳ hoặc bấm nút Cào VietJack để nạp thêm dữ liệu.
            </p>
          </div>
        ) : (
          /* Bảng dữ liệu chính */
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-stone-700">
              <thead className="bg-stone-50/80 text-stone-500 uppercase tracking-wider text-[11px] font-bold border-b border-stone-200">
                <tr>
                  <th className="py-3 px-4 w-12 text-center">#</th>
                  <th className="py-3 px-4 w-28">Khối lớp</th>
                  <th className="py-3 px-4 w-20">Học kỳ</th>
                  <th className="py-3 px-4 min-w-[220px]">Chương lớn / Chủ đề</th>
                  <th className="py-3 px-4 min-w-[260px]">Tên bài học / Chuyên đề</th>
                  <th className="py-3 px-4 w-36">Bộ SGK</th>
                  <th className="py-3 px-4 w-32">Trạng thái</th>
                  <th className="py-3 px-4 w-28 text-center">Bật / Ẩn</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 font-medium">
                {paginatedTopics.map((topic, idx) => {
                  const globalIdx = (currentPage - 1) * PAGE_SIZE + idx + 1;
                  const isToggling = togglingId === topic.id;

                  return (
                    <tr
                      key={topic.id}
                      className={cn(
                        "hover:bg-stone-50/80 transition-colors",
                        !topic.is_active && "bg-stone-50/30 text-stone-400"
                      )}
                    >
                      {/* STT */}
                      <td className="py-3 px-4 text-center text-stone-400 text-[11px]">
                        {globalIdx}
                      </td>

                      {/* Khối lớp */}
                      <td className="py-3 px-4">
                        <span
                          className={cn(
                            "inline-flex items-center px-2 py-0.5 rounded-md font-bold text-[11px]",
                            topic.grade === 4 && "bg-blue-50 text-blue-800 border border-blue-200",
                            topic.grade === 5 && "bg-amber-50 text-amber-900 border border-amber-200",
                            topic.grade === 6 && "bg-emerald-50 text-emerald-800 border border-emerald-200",
                            topic.grade === 7 && "bg-purple-50 text-purple-800 border border-purple-200",
                            topic.grade === 8 && "bg-rose-50 text-rose-800 border border-rose-200",
                            topic.grade === 9 && "bg-indigo-50 text-indigo-800 border border-indigo-200"
                          )}
                        >
                          Lớp {topic.grade}
                        </span>
                      </td>

                      {/* Học kỳ */}
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-stone-100 text-stone-600 font-semibold text-[11px]">
                          {topic.semester ? `HK ${topic.semester}` : "Cả năm"}
                        </span>
                      </td>

                      {/* Chương lớn */}
                      <td className="py-3 px-4 font-semibold text-stone-800">
                        {topic.chapter_name}
                      </td>

                      {/* Tên bài học */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={cn(
                              "font-bold",
                              topic.is_active ? "text-stone-900" : "text-stone-400 line-through"
                            )}
                          >
                            {topic.topic_name}
                          </span>
                          {topic.source_url && (
                            <a
                              href={topic.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-stone-400 hover:text-[#C1762A] transition-colors"
                              title="Xem trang gốc VietJack"
                            >
                              <ExternalLink size={12} />
                            </a>
                          )}
                        </div>
                      </td>

                      {/* Bộ SGK */}
                      <td className="py-3 px-4 text-stone-500 text-[11px]">
                        <div>{topic.book_series}</div>
                        {topic.school_year && (
                          <div className="text-[10px] text-stone-400">{topic.school_year}</div>
                        )}
                      </td>

                      {/* Badge Trạng thái theo [AC 8.4.3] */}
                      <td className="py-3 px-4">
                        {topic.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                            Đang bật
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-stone-100 text-stone-500 border border-stone-200 text-[11px] font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-stone-400" />
                            Đã ẩn
                          </span>
                        )}
                      </td>

                      {/* Toggle Switch Bật/Tắt tức thì theo [AC 8.4.3] */}
                      <td className="py-3 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => handleToggleTopic(topic.id, topic.is_active)}
                          disabled={isToggling}
                          className={cn(
                            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 touch-manipulation",
                            topic.is_active ? "bg-[#C1762A]" : "bg-stone-300",
                            isToggling && "opacity-50 cursor-wait"
                          )}
                          title={topic.is_active ? "Gạt để ẩn chuyên đề này" : "Gạt để bật lại chuyên đề này"}
                          aria-label="Toggle trạng thái"
                        >
                          <span
                            className={cn(
                              "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transform transition duration-200 ease-in-out",
                              topic.is_active ? "translate-x-4" : "translate-x-0"
                            )}
                          />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* 4. Phân trang */}
        {totalPages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-stone-50/60 border-t border-stone-200 text-xs">
            <span className="text-stone-500 font-medium">
              Hiển thị <strong className="text-stone-800">{(currentPage - 1) * PAGE_SIZE + 1}</strong> đến{" "}
              <strong className="text-stone-800">
                {Math.min(currentPage * PAGE_SIZE, totalItems)}
              </strong>{" "}
              trong <strong className="text-stone-800">{totalItems}</strong> chuyên đề
            </span>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage <= 1}
                className="px-2.5 py-1.5 rounded-lg border border-stone-200 bg-white text-stone-600 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed font-semibold flex items-center gap-1 cursor-pointer"
              >
                <ChevronLeft size={13} />
                <span>Trước</span>
              </button>

              <span className="px-3 py-1 font-bold text-stone-700">
                {currentPage} / {totalPages}
              </span>

              <button
                type="button"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage >= totalPages}
                className="px-2.5 py-1.5 rounded-lg border border-stone-200 bg-white text-stone-600 hover:bg-stone-50 disabled:opacity-40 disabled:cursor-not-allowed font-semibold flex items-center gap-1 cursor-pointer"
              >
                <span>Sau</span>
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 5. Modal Tiến Độ Cào Dữ Liệu VietJack (2 - 4 giây) theo [AC 8.4.1] */}
      <SyncVietjackModal
        isOpen={isSyncModalOpen}
        onClose={() => setIsSyncModalOpen(false)}
        onSync={handleSyncVietjack}
        onSuccessDone={handleSyncSuccessDone}
      />
    </div>
  );
}
