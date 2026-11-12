"use client";

import React, { useState, useMemo, useEffect } from "react";
import {
  CheckSquare,
  Square,
  Sparkles,
  Trash2,
  Edit3,
  Search,
  RefreshCw,
  Clock,
  ArrowRight,
  CheckCircle2,
  X,
  Save,
  Tag,
  AlertCircle,
  RotateCcw,
} from "lucide-react";
import {
  AuditFeedbackItem,
  ActiveLearningAgent,
  UpdateFeedbackPayload,
} from "@/types/admin";

interface ActiveLearningTableProps {
  items: AuditFeedbackItem[];
  isLoading: boolean;
  isRetraining: boolean;
  onRetrain: (selectedIds: number[]) => Promise<void>;
  onReject: (selectedIds: number[]) => Promise<void>;
  onUpdateItem: (id: number, payload: UpdateFeedbackPayload) => Promise<boolean>;
  onDeleteItem: (id: number) => Promise<boolean>;
  onRefresh: () => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  agentFilter: string;
  setAgentFilter: (agent: string) => void;
}

const AGENT_COLORS: Record<string, { bg: string; text: string; border: string; label: string }> = {
  MISCONCEPTION: {
    bg: "bg-amber-50",
    text: "text-amber-800",
    border: "border-amber-200",
    label: "Hiểu Sai Bản Chất",
  },
  SAFETY: {
    bg: "bg-red-50",
    text: "text-red-700",
    border: "border-red-200",
    label: "An Toàn & Ngôn Từ",
  },
  KNOWLEDGE_TRACING: {
    bg: "bg-blue-50",
    text: "text-blue-700",
    border: "border-blue-200",
    label: "Hỏi Khái Niệm / Lý Thuyết",
  },
  SCAFFOLDING: {
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    border: "border-emerald-200",
    label: "Dẫn Dắt Socratic",
  },
};

const VALID_AGENTS: ActiveLearningAgent[] = [
  "MISCONCEPTION",
  "KNOWLEDGE_TRACING",
  "SAFETY",
  "SCAFFOLDING",
];

export default function ActiveLearningTable({
  items,
  isLoading,
  isRetraining,
  onRetrain,
  onReject,
  onUpdateItem,
  onDeleteItem,
  onRefresh,
  searchQuery,
  setSearchQuery,
  agentFilter,
  setAgentFilter,
}: ActiveLearningTableProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [isRejecting, setIsRejecting] = useState(false);

  // State Modal chỉnh sửa
  const [editingItem, setEditingItem] = useState<AuditFeedbackItem | null>(null);
  const [editQuery, setEditQuery] = useState("");
  const [editAgent, setEditAgent] = useState<string>("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Lọc tức thời trên client để giao diện phản hồi 0ms khi admin gõ hoặc chọn filter
  const displayedItems = useMemo(() => {
    return items.filter((item) => {
      const matchSearch =
        !searchQuery.trim() ||
        item.user_query.toLowerCase().includes(searchQuery.toLowerCase().trim()) ||
        item.id.toString().includes(searchQuery.trim());
      const matchAgent =
        agentFilter === "ALL" ||
        item.suggested_agent === agentFilter ||
        item.predicted_agent === agentFilter;
      return matchSearch && matchAgent;
    });
  }, [items, searchQuery, agentFilter]);

  // Tự động dọn dẹp các ID đã chọn nếu chúng không còn tồn tại trong items
  useEffect(() => {
    const existingIds = new Set(items.map((it) => it.id));
    setSelectedIds((prev) => prev.filter((id) => existingIds.has(id)));
  }, [items]);

  // Phím Escape để đóng nhanh modal hiệu chỉnh
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && editingItem) {
        setEditingItem(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [editingItem]);

  // Toggle Chọn tất cả dựa trên danh sách đang hiển thị (displayedItems)
  const isAllSelected =
    displayedItems.length > 0 &&
    displayedItems.every((item) => selectedIds.includes(item.id));
  const isIndeterminate =
    selectedIds.length > 0 && !isAllSelected && displayedItems.some((it) => selectedIds.includes(it.id));

  const handleToggleSelectAll = () => {
    if (isAllSelected) {
      const displayedIdSet = new Set(displayedItems.map((it) => it.id));
      setSelectedIds((prev) => prev.filter((id) => !displayedIdSet.has(id)));
    } else {
      const combined = new Set([...selectedIds, ...displayedItems.map((it) => it.id)]);
      setSelectedIds(Array.from(combined));
    }
  };

  // Toggle chọn từng dòng
  const handleToggleRow = (id: number) => {
    if (isRetraining || isRejecting) return;
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  // Mở modal chỉnh sửa
  const handleOpenEdit = (item: AuditFeedbackItem) => {
    setEditingItem(item);
    setEditQuery(item.user_query);
    setEditAgent(item.suggested_agent);
    setEditError(null);
  };

  // Lưu chỉnh sửa có validation chặt chẽ
  const handleSaveEdit = async () => {
    if (!editingItem) return;
    const cleanQuery = editQuery.trim();
    if (cleanQuery.length < 3) {
      setEditError("Nội dung câu hỏi phải có tối thiểu 3 ký tự.");
      return;
    }
    setIsSavingEdit(true);
    setEditError(null);
    try {
      const ok = await onUpdateItem(editingItem.id, {
        user_query: cleanQuery,
        suggested_agent: editAgent,
      });
      if (ok) {
        setEditingItem(null);
      }
    } finally {
      setIsSavingEdit(false);
    }
  };

  // Xử lý Duyệt và Tái huấn luyện hàng loạt
  const handleBatchRetrain = async () => {
    if (selectedIds.length === 0 || isRetraining || isRejecting) return;
    await onRetrain(selectedIds);
    setSelectedIds([]);
  };

  // Xử lý Bỏ qua mẫu lỗi hàng loạt
  const handleBatchReject = async () => {
    if (selectedIds.length === 0 || isRejecting || isRetraining) return;
    if (!confirm(`Bạn có chắc muốn bỏ qua ${selectedIds.length} mẫu câu đã chọn?`)) return;
    setIsRejecting(true);
    try {
      await onReject(selectedIds);
      setSelectedIds([]);
    } finally {
      setIsRejecting(false);
    }
  };

  // Xóa bộ lọc về mặc định
  const handleResetFilters = () => {
    setSearchQuery("");
    setAgentFilter("ALL");
  };

  return (
    <div className="space-y-4">
      {/* ── 1. Action Toolbar: Dynamic Action Bar chuẩn US 10.4 ── */}
      <div className="bg-white rounded-2xl p-4 border border-[#F1CCA6] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Nhóm Checkbox Chọn tất cả & Badge */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleToggleSelectAll}
            disabled={displayedItems.length === 0 || isRetraining || isRejecting}
            className="flex items-center gap-2 text-sm font-bold text-[#8C4905] hover:text-[#C1762A] transition-colors cursor-pointer disabled:opacity-40"
          >
            {isAllSelected ? (
              <CheckSquare size={19} className="text-[#C1762A]" />
            ) : isIndeterminate ? (
              <div className="w-[19px] h-[19px] rounded bg-amber-100 border border-amber-500 flex items-center justify-center">
                <div className="w-2.5 h-0.5 bg-amber-700 rounded-sm" />
              </div>
            ) : (
              <Square size={19} className="text-stone-400" />
            )}
            <span>
              Chọn tất cả ({displayedItems.length}
              {displayedItems.length !== items.length ? `/${items.length}` : ""} câu)
            </span>
          </button>

          {selectedIds.length > 0 && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6] animate-in fade-in duration-200">
              Đã chọn: {selectedIds.length} / {items.length}
            </span>
          )}
        </div>

        {/* Nhóm Filter & Search */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Search Input */}
          <div className="relative min-w-[220px]">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
            <input
              type="text"
              placeholder="Tìm câu hỏi (Enter để reload)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onRefresh()}
              className="w-full pl-9 pr-3 py-2 text-xs md:text-sm bg-[#FDFBF7] border border-[#F1CCA6] rounded-xl text-[#7A3E04] focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 focus:border-[#C1762A] transition-all"
            />
          </div>

          {/* Filter Agent */}
          <div className="relative">
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              aria-label="Lọc theo nhãn Agent"
              className="pl-3 pr-8 py-2 text-xs md:text-sm bg-[#FDFBF7] border border-[#F1CCA6] rounded-xl text-[#7A3E04] focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 focus:border-[#C1762A] cursor-pointer"
            >
              <option value="ALL">Tất cả Agent đề xuất</option>
              <option value="MISCONCEPTION">Hiểu Sai Bản Chất (MISCONCEPTION)</option>
              <option value="KNOWLEDGE_TRACING">Hỏi Khái Niệm (KNOWLEDGE_TRACING)</option>
              <option value="SAFETY">An Toàn Ngôn Từ (SAFETY)</option>
              <option value="SCAFFOLDING">Dẫn Dắt Socratic (SCAFFOLDING)</option>
            </select>
          </div>

          {/* Nút Làm mới */}
          <button
            onClick={onRefresh}
            disabled={isLoading || isRetraining}
            className="p-2 bg-white text-[#8C4905] border border-[#F1CCA6] rounded-xl hover:bg-[#F7ECE1] active:scale-95 transition-all cursor-pointer disabled:opacity-50"
            title="Tải lại danh sách từ server"
          >
            <RefreshCw size={16} className={isLoading ? "animate-spin text-[#C1762A]" : "text-[#C1762A]"} />
          </button>
        </div>

        {/* Nhóm Action Buttons: Sáng lên khi có mục được chọn */}
        <div className="flex items-center gap-2">
          {/* Nút Bỏ qua mẫu lỗi */}
          <button
            onClick={handleBatchReject}
            disabled={selectedIds.length === 0 || isRejecting || isRetraining}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs md:text-sm font-bold bg-white text-stone-600 border border-stone-200 hover:bg-stone-50 hover:text-stone-800 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-2xs cursor-pointer"
            title="Đánh dấu bỏ qua các câu spam/lỗi đã chọn"
          >
            <Trash2 size={15} className="text-stone-500" />
            <span>{isRejecting ? "Đang bỏ qua..." : "Bỏ qua mẫu lỗi"}</span>
          </button>

          {/* Nút Nổi Bật: Duyệt & Tái Huấn Luyện (Retrain) */}
          <button
            onClick={handleBatchRetrain}
            disabled={selectedIds.length === 0 || isRetraining || isRejecting}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs md:text-sm font-extrabold transition-all shadow-sm cursor-pointer ${
              selectedIds.length > 0 && !isRetraining
                ? "bg-gradient-to-r from-[#C1762A] to-[#8C4905] text-white hover:brightness-110 active:scale-95 ring-2 ring-[#C1762A]/30"
                : "bg-stone-100 text-stone-400 border border-stone-200 cursor-not-allowed"
            }`}
            title="Duyệt các mẫu đã chọn, tái huấn luyện pipeline mô hình và Hot-Reload RAM"
          >
            <Sparkles size={16} className={isRetraining ? "animate-spin" : ""} />
            <span>
              {isRetraining
                ? "Đang huấn luyện & nạp RAM..."
                : `⚡ Duyệt (${selectedIds.length}) & Tái huấn luyện`}
            </span>
          </button>
        </div>
      </div>

      {/* ── 2. Table Component: Bảng hiển thị chi tiết câu hỏi ── */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="bg-[#FAF3EB] border-b border-[#F1CCA6] text-xs font-bold text-[#8C4905] uppercase tracking-wider">
                <th className="py-3.5 px-4 w-12 text-center">
                  <span className="sr-only">Chọn</span>
                </th>
                <th className="py-3.5 px-4 min-w-[280px]">Câu Hỏi Học Sinh</th>
                <th className="py-3.5 px-4 w-44">Nhãn AI Đoán Sai</th>
                <th className="py-3.5 px-4 w-48">Nhãn Đề Xuất Đúng</th>
                <th className="py-3.5 px-4 w-36">Thời Gian</th>
                <th className="py-3.5 px-4 w-28 text-right">Thao Tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F6DECA]">
              {isLoading && items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-[#7A3E04]">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <div className="w-7 h-7 border-3 border-[#C1762A] border-t-transparent rounded-full animate-spin" />
                      <span className="text-xs font-medium">Đang tải danh sách mẫu câu chờ duyệt...</span>
                    </div>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center">
                    <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto text-[#7A3E04]">
                      <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center">
                        <CheckCircle2 size={28} />
                      </div>
                      <h4 className="text-base font-extrabold text-[#8C4905]">
                        Tuyệt vời! Không có câu hỏi nào chờ duyệt
                      </h4>
                      <p className="text-xs text-stone-500">
                        Hệ thống phân luồng Orchestrator đang hoạt động chính xác hoặc toàn bộ câu hỏi lệch đã được duyệt nạp vào mô hình.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : displayedItems.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto text-[#7A3E04]">
                      <div className="w-12 h-12 rounded-2xl bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center">
                        <AlertCircle size={24} />
                      </div>
                      <h4 className="text-sm font-bold text-[#8C4905]">
                        Không tìm thấy câu hỏi nào phù hợp với bộ lọc
                      </h4>
                      <p className="text-xs text-stone-500">
                        Thử điều chỉnh từ khóa tìm kiếm hoặc chọn lại Agent đề xuất.
                      </p>
                      <button
                        onClick={handleResetFilters}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-[#F7ECE1] text-[#8C4905] border border-[#F1CCA6] hover:bg-[#F2DFCD] transition-all cursor-pointer"
                      >
                        <RotateCcw size={13} />
                        <span>Đặt lại bộ lọc</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                displayedItems.map((item) => {
                  const isChecked = selectedIds.includes(item.id);
                  const predBadge = AGENT_COLORS[item.predicted_agent] || {
                    bg: "bg-stone-100",
                    text: "text-stone-700",
                    border: "border-stone-200",
                    label: item.predicted_agent,
                  };
                  const suggBadge = AGENT_COLORS[item.suggested_agent] || {
                    bg: "bg-amber-50",
                    text: "text-amber-800",
                    border: "border-amber-200",
                    label: item.suggested_agent,
                  };

                  return (
                    <tr
                      key={item.id}
                      className={`hover:bg-[#FCF7F2] transition-colors ${
                        isChecked ? "bg-amber-50/50" : ""
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-4 text-center">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={isRetraining || isRejecting}
                          onChange={() => handleToggleRow(item.id)}
                          aria-label={`Chọn câu hỏi: ${item.user_query}`}
                          className="w-4 h-4 rounded text-[#C1762A] focus:ring-[#C1762A] border-[#F1CCA6] cursor-pointer disabled:opacity-40"
                        />
                      </td>

                      {/* Câu hỏi học sinh */}
                      <td className="py-3 px-4">
                        <p className="font-semibold text-stone-900 line-clamp-2 text-sm leading-snug">
                          &ldquo;{item.user_query}&rdquo;
                        </p>
                        <span className="text-[11px] text-stone-400 font-mono">
                          ID: #{item.id}
                        </span>
                      </td>

                      {/* Nhãn AI Đoán Sai */}
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-stone-100 text-stone-600 border border-stone-200 line-through opacity-80">
                          {item.predicted_agent}
                        </span>
                      </td>

                      {/* Nhãn Đề Xuất Đúng */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <ArrowRight size={13} className="text-amber-600 shrink-0" />
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold border ${suggBadge.bg} ${suggBadge.text} ${suggBadge.border} shadow-2xs`}
                          >
                            <Tag size={11} />
                            {item.suggested_agent}
                          </span>
                        </div>
                      </td>

                      {/* Thời Gian */}
                      <td className="py-3 px-4 text-xs text-stone-500 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          <Clock size={12} className="text-stone-400 shrink-0" />
                          <span>
                            {new Date(item.created_at).toLocaleDateString("vi-VN", {
                              day: "2-digit",
                              month: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                      </td>

                      {/* Thao Tác: Sửa / Xóa */}
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleOpenEdit(item)}
                            disabled={isRetraining || isRejecting}
                            className="p-1.5 text-stone-500 hover:text-[#C1762A] hover:bg-[#F7ECE1] rounded-lg transition-colors cursor-pointer disabled:opacity-40"
                            title="Hiệu chỉnh câu hỏi hoặc nhãn"
                          >
                            <Edit3 size={15} />
                          </button>
                          <button
                            onClick={async () => {
                              if (confirm(`Bạn có chắc muốn xóa bản ghi #${item.id}?`)) {
                                await onDeleteItem(item.id);
                              }
                            }}
                            disabled={isRetraining || isRejecting}
                            className="p-1.5 text-stone-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer disabled:opacity-40"
                            title="Xóa bản ghi"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 3. Modal Chỉnh Sửa Câu & Nhãn Trước Khi Duyệt ── */}
      {editingItem && (
        <div
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-2xs flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setEditingItem(null)}
        >
          <div
            className="bg-white rounded-2xl max-w-lg w-full border border-[#F1CCA6] shadow-xl p-6 space-y-5 animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-[#F6DECA] pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
                  <Edit3 size={16} />
                </div>
                <h3 className="text-base font-extrabold text-[#8C4905]">
                  Hiệu Chỉnh Mẫu Câu #{editingItem.id}
                </h3>
              </div>
              <button
                onClick={() => setEditingItem(null)}
                className="text-stone-400 hover:text-stone-600 p-1 rounded-lg"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-[#8C4905] uppercase tracking-wider mb-1.5">
                  Nội dung câu nói của học sinh:
                </label>
                <textarea
                  rows={3}
                  value={editQuery}
                  onChange={(e) => {
                    setEditQuery(e.target.value);
                    if (editError) setEditError(null);
                  }}
                  className="w-full p-3 text-sm bg-[#FDFBF7] border border-[#F1CCA6] rounded-xl text-stone-900 focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 focus:border-[#C1762A]"
                  placeholder="Nhập nội dung câu hỏi sau khi chuẩn hóa..."
                />
                {editError && (
                  <p className="text-xs text-red-600 font-semibold mt-1 flex items-center gap-1">
                    <AlertCircle size={13} />
                    {editError}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-[#8C4905] uppercase tracking-wider mb-1.5">
                  Nhãn đề xuất đúng (Suggested Agent):
                </label>
                <select
                  value={editAgent}
                  onChange={(e) => setEditAgent(e.target.value)}
                  className="w-full p-2.5 text-sm bg-[#FDFBF7] border border-[#F1CCA6] rounded-xl text-stone-900 focus:outline-none focus:ring-2 focus:ring-[#C1762A]/20 focus:border-[#C1762A] cursor-pointer"
                >
                  {VALID_AGENTS.map((agent) => (
                    <option key={agent} value={agent}>
                      {agent} ({AGENT_COLORS[agent]?.label || agent})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 border-t border-[#F6DECA] pt-4">
              <button
                type="button"
                onClick={() => setEditingItem(null)}
                className="px-4 py-2 text-xs md:text-sm font-bold text-stone-600 hover:bg-stone-100 rounded-xl transition-all cursor-pointer"
              >
                Hủy bỏ
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                disabled={isSavingEdit || !editQuery.trim() || editQuery.trim().length < 3}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs md:text-sm font-extrabold bg-[#C1762A] hover:bg-[#8C4905] text-white rounded-xl shadow-xs transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save size={15} />
                <span>{isSavingEdit ? "Đang lưu..." : "Lưu thay đổi"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

