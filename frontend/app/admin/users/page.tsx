"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Users,
  Search,
  Filter,
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  UserX,
  Download,
  Plus,
  RefreshCw,
  X,
  ExternalLink,
  Flame,
  CheckCircle2,
  AlertTriangle,
  Send,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Eye,
  Check,
  FileText,
} from "lucide-react";
import { AdminUser, UserRole, UserStatus } from "@/types/admin";

// Dữ liệu mẫu chuẩn cấu trúc Backend /admin/mock/users (Task T7.31)
const INITIAL_USERS: AdminUser[] = [
  {
    id: "std_1001",
    email: "an.nguyen@gmail.com",
    name: "Nguyễn Minh An",
    role: "STUDENT",
    grade: 5,
    status: "ACTIVE",
    created_at: "2026-09-02T08:00:00Z",
    last_active_at: "2026-10-22T08:15:00Z",
    total_sessions: 56,
    total_problems_solved: 42,
    avg_independence_score: 92,
    streak_days: 12,
    linked_parent: {
      id: "par_2001",
      email: "mai.tran@gmail.com",
      name: "Trần Thị Mai (Mẹ)",
      phone: "0905 123 456",
    },
    linked_students: [],
  },
  {
    id: "par_2001",
    email: "mai.tran@gmail.com",
    name: "Trần Thị Mai",
    role: "MONITOR",
    grade: null,
    status: "ACTIVE",
    created_at: "2026-09-02T08:15:00Z",
    last_active_at: "2026-10-22T08:30:00Z",
    total_sessions: 0,
    total_problems_solved: 0,
    avg_independence_score: null,
    streak_days: 0,
    linked_parent: null,
    linked_students: [
      {
        id: "std_1001",
        email: "an.nguyen@gmail.com",
        name: "Nguyễn Minh An",
        grade: 5,
        avg_independence_score: 92,
      },
    ],
  },
  {
    id: "std_1002",
    email: "huy.dang@school.edu.vn",
    name: "Đặng Quốc Huy",
    role: "STUDENT",
    grade: 7,
    status: "SUSPENDED",
    created_at: "2026-09-15T14:20:00Z",
    last_active_at: "2026-10-21T19:10:00Z",
    total_sessions: 34,
    total_problems_solved: 25,
    avg_independence_score: 48,
    streak_days: 0,
    linked_parent: {
      id: "par_2003",
      email: "tuan.dang@example.com",
      name: "Đặng Quốc Tuấn (Bố)",
      phone: "0934 567 890",
    },
    linked_students: [],
  },
  {
    id: "std_1003",
    email: "nam.le@gmail.com",
    name: "Lê Hoàng Nam",
    role: "STUDENT",
    grade: 8,
    status: "ACTIVE",
    created_at: "2026-09-10T10:30:00Z",
    last_active_at: "2026-10-22T07:45:00Z",
    total_sessions: 78,
    total_problems_solved: 64,
    avg_independence_score: 82,
    streak_days: 4,
    linked_parent: {
      id: "par_2004",
      email: "tung.le@example.com",
      name: "Lê Văn Tùng (Bố)",
      phone: "0912 345 678",
    },
    linked_students: [],
  },
  {
    id: "std_1004",
    email: "kiet.nguyen@example.com",
    name: "Nguyễn Tuấn Kiệt",
    role: "STUDENT",
    grade: 6,
    status: "ACTIVE",
    created_at: "2026-09-02T08:00:00Z",
    last_active_at: "2026-10-22T08:15:00Z",
    total_sessions: 56,
    total_problems_solved: 42,
    avg_independence_score: 85,
    streak_days: 7,
    linked_parent: {
      id: "par_2005",
      email: "hung.nguyen@example.com",
      name: "Nguyễn Văn Hùng (Bố)",
      phone: "0905 888 999",
    },
    linked_students: [],
  },
  {
    id: "par_2002",
    email: "lan.le@example.com",
    name: "Lê Thị Ngọc Lan",
    role: "MONITOR",
    grade: null,
    status: "ACTIVE",
    created_at: "2026-09-10T10:45:00Z",
    last_active_at: "2026-10-21T21:00:00Z",
    total_sessions: 0,
    total_problems_solved: 0,
    avg_independence_score: null,
    streak_days: 0,
    linked_parent: null,
    linked_students: [
      {
        id: "std_1005",
        email: "mai.tran@example.com",
        name: "Trần Phương Mai",
        grade: 4,
        avg_independence_score: 88,
      },
    ],
  },
  {
    id: "std_1005",
    email: "mai.tran@example.com",
    name: "Trần Phương Mai",
    role: "STUDENT",
    grade: 4,
    status: "ACTIVE",
    created_at: "2026-09-12T09:00:00Z",
    last_active_at: "2026-10-22T06:30:00Z",
    total_sessions: 40,
    total_problems_solved: 35,
    avg_independence_score: 88,
    streak_days: 9,
    linked_parent: {
      id: "par_2002",
      email: "lan.le@example.com",
      name: "Lê Thị Ngọc Lan (Mẹ)",
      phone: "0988 777 666",
    },
    linked_students: [],
  },
  {
    id: "adm_0001",
    email: "admin@socratickid.edu.vn",
    name: "Quản Trị Viên SocraticKid",
    role: "ADMIN",
    grade: null,
    status: "ACTIVE",
    created_at: "2026-08-01T00:00:00Z",
    last_active_at: "2026-10-22T09:00:00Z",
    total_sessions: 0,
    total_problems_solved: 0,
    avg_independence_score: null,
    streak_days: 0,
    linked_parent: null,
    linked_students: [],
  },
];

export default function AdminUsersPage() {
  const router = useRouter();
  const { data: session } = useSession();

  // State danh sách users
  const [users, setUsers] = useState<AdminUser[]>(INITIAL_USERS);
  const [isLoading, setIsLoading] = useState(false);

  // Bộ lọc
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("ALL");
  const [gradeFilter, setGradeFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  // Selection
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);

  // Modals state
  const [detailUser, setDetailUser] = useState<AdminUser | null>(null);
  const [banTargetUser, setBanTargetUser] = useState<AdminUser | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Form tạm khóa tài khoản
  const [banReason, setBanReason] = useState("Vi phạm ngôn từ thiếu văn hóa (Toxic)");
  const [banDuration, setBanDuration] = useState("24 Giờ");
  const [banNote, setBanNote] = useState("");

  // Form tạo người dùng mới
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserRole, setNewUserRole] = useState<UserRole>("STUDENT");
  const [newUserGrade, setNewUserGrade] = useState<number>(5);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  }, []);

  // Fetch từ API /admin/mock/users nếu backend đang chạy, có fallback tự động
  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const params = new URLSearchParams();
      if (roleFilter !== "ALL") params.append("role", roleFilter);
      if (statusFilter !== "ALL") params.append("status_filter", statusFilter);
      if (gradeFilter !== "ALL") params.append("grade", gradeFilter);
      if (searchQuery.trim()) params.append("search", searchQuery.trim());

      const res = await fetch(`${backendUrl}/admin/mock/users?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${(session as any)?.access_token || ""}`,
        },
      });

      if (res.ok) {
        const data = await res.json();
        if (data.items && Array.isArray(data.items)) {
          setUsers(data.items);
          setIsLoading(false);
          return;
        }
      }
    } catch {
      // Dùng state nội bộ nếu không kết nối được backend
    }
    setIsLoading(false);
  }, [roleFilter, statusFilter, gradeFilter, searchQuery, session]);

  useEffect(() => {
    // Chỉ thử fetch backend nếu có session token
    if ((session as any)?.access_token) {
      fetchUsers();
    }
  }, [fetchUsers, session]);

  // Lọc dữ liệu client-side mượt mà
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // Tìm kiếm
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchName = u.name.toLowerCase().includes(q);
        const matchEmail = u.email.toLowerCase().includes(q);
        const matchParent = u.linked_parent?.name.toLowerCase().includes(q);
        const matchStudent = u.linked_students?.some((s) => s.name.toLowerCase().includes(q));
        if (!matchName && !matchEmail && !matchParent && !matchStudent) return false;
      }
      // Role
      if (roleFilter !== "ALL" && u.role !== roleFilter) return false;
      // Grade
      if (gradeFilter !== "ALL") {
        if (u.role !== "STUDENT" || u.grade !== Number(gradeFilter)) return false;
      }
      // Status
      if (statusFilter !== "ALL" && u.status !== statusFilter) return false;

      return true;
    });
  }, [users, searchQuery, roleFilter, gradeFilter, statusFilter]);

  // Thống kê nhanh
  const stats = useMemo(() => {
    const total = users.length;
    const students = users.filter((u) => u.role === "STUDENT").length;
    const parents = users.filter((u) => u.role === "MONITOR").length;
    const suspended = users.filter((u) => u.status === "SUSPENDED").length;
    return { total, students, parents, suspended };
  }, [users]);

  // Checkbox Select All
  const isAllSelected =
    filteredUsers.length > 0 && selectedUserIds.length === filteredUsers.length;

  const handleSelectAll = () => {
    if (isAllSelected) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(filteredUsers.map((u) => u.id));
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedUserIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Điều hướng xem log chi tiết của tài khoản (Task T8.28 / US 8.5 - Hỗ trợ CSKH)
  const handleViewUserLogs = (user: AdminUser) => {
    // Điều hướng sang trang Giám sát Safety / Audit Log kèm query search email để lọc ngay log của user đó
    router.push(`/admin/safety?search=${encodeURIComponent(user.email)}`);
  };

  // Khóa / Mở khóa tài khoản
  const handleConfirmBan = async () => {
    if (!banTargetUser) return;
    const updatedStatus: UserStatus = "SUSPENDED";

    // Cập nhật state cục bộ
    setUsers((prev) =>
      prev.map((u) => (u.id === banTargetUser.id ? { ...u, status: updatedStatus } : u))
    );

    // Cố gắng gọi API PATCH nếu có backend
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      await fetch(`${backendUrl}/admin/mock/users/${banTargetUser.id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${(session as any)?.access_token || ""}`,
        },
        body: JSON.stringify({ status: "SUSPENDED", reason: banReason, duration: banDuration }),
      });
    } catch {
      // bỏ qua lỗi offline
    }

    showToast(`Đã tạm khóa tài khoản ${banTargetUser.name} (${banDuration})!`);
    setBanTargetUser(null);
    if (detailUser?.id === banTargetUser.id) {
      setDetailUser((prev) => (prev ? { ...prev, status: "SUSPENDED" } : null));
    }
  };

  const handleUnbanUser = async (user: AdminUser) => {
    const updatedStatus: UserStatus = "ACTIVE";
    setUsers((prev) =>
      prev.map((u) => (u.id === user.id ? { ...u, status: updatedStatus } : u))
    );

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      await fetch(`${backendUrl}/admin/mock/users/${user.id}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${(session as any)?.access_token || ""}`,
        },
        body: JSON.stringify({ status: "ACTIVE" }),
      });
    } catch {
      // bỏ qua lỗi offline
    }

    showToast(`Đã mở khóa tài khoản cho ${user.name}!`);
    if (detailUser?.id === user.id) {
      setDetailUser((prev) => (prev ? { ...prev, status: "ACTIVE" } : null));
    }
  };

  // Thao tác hàng loạt (Bulk Actions)
  const handleBulkBan = () => {
    setUsers((prev) =>
      prev.map((u) =>
        selectedUserIds.includes(u.id) && u.role !== "ADMIN"
          ? { ...u, status: "SUSPENDED" }
          : u
      )
    );
    showToast(`Đã tạm khóa các tài khoản được chọn (bảo vệ tài khoản Admin)!`);
    setSelectedUserIds([]);
  };

  const handleBulkUnban = () => {
    setUsers((prev) =>
      prev.map((u) =>
        selectedUserIds.includes(u.id) ? { ...u, status: "ACTIVE" } : u
      )
    );
    showToast(`Đã mở khóa ${selectedUserIds.length} tài khoản được chọn!`);
    setSelectedUserIds([]);
  };

  // Xuất file CSV / Excel
  const handleExportCSV = () => {
    const headers = [
      "Mã ID",
      "Họ và tên",
      "Email",
      "Vai trò",
      "Khối lớp",
      "Điểm tự lực",
      "Streak ngày",
      "Trạng thái",
      "Lần active cuối",
    ];

    const rows = filteredUsers.map((u) => [
      u.id,
      `"${u.name}"`,
      u.email,
      u.role,
      u.grade || "",
      u.avg_independence_score ?? "",
      u.streak_days,
      u.status,
      u.last_active_at,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8,\uFEFF" +
      [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `SocraticKid_Users_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast(`Đã xuất ${filteredUsers.length} tài khoản ra file CSV!`);
  };

  // Tạo người dùng mới
  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUserName.trim() || !newUserEmail.trim()) {
      showToast("Vui lòng điền họ tên và email hợp lệ!");
      return;
    }

    const newUser: AdminUser = {
      id: `${newUserRole.toLowerCase().slice(0, 3)}_${Date.now().toString().slice(-4)}`,
      name: newUserName.trim(),
      email: newUserEmail.trim(),
      role: newUserRole,
      grade: newUserRole === "STUDENT" ? newUserGrade : null,
      status: "ACTIVE",
      created_at: new Date().toISOString(),
      last_active_at: new Date().toISOString(),
      total_sessions: 0,
      total_problems_solved: 0,
      avg_independence_score: newUserRole === "STUDENT" ? 100 : null,
      streak_days: 0,
      linked_parent: null,
      linked_students: [],
    };

    setUsers((prev) => [newUser, ...prev]);
    showToast(`Đã tạo tài khoản ${newUserName} thành công!`);
    setIsCreateModalOpen(false);
    setNewUserName("");
    setNewUserEmail("");
  };

  // Đặt lại bộ lọc
  const handleResetFilters = () => {
    setSearchQuery("");
    setRoleFilter("ALL");
    setGradeFilter("ALL");
    setStatusFilter("ALL");
    showToast("Đã đặt lại toàn bộ bộ lọc!");
  };

  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-500 space-y-6 pb-12 text-[#2A1C0E]">
      {/* ── 1. Page Header (Đồng bộ chuẩn Parent Dashboard) ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-[#C1762A] rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-md">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl md:text-3xl font-extrabold text-[#8C4905] tracking-tight leading-none">
                Quản Lý Người Dùng
              </h1>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#FFF3E6] text-[#C1762A] border border-[#F1CCA6]">
                {filteredUsers.length} Users
              </span>
            </div>
            <p className="text-sm text-[#C1762A] mt-1 font-medium">
              Danh sách tài khoản định danh Học sinh & Phụ huynh, theo dõi trạng thái hoạt động và tra cứu log chăm sóc khách hàng
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={handleExportCSV}
            className="btn btn-secondary px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-1.5 bg-white border border-[#F1CCA6] hover:border-[#C1762A] text-[#8C4905] transition-all duration-200 active:scale-[0.98] shadow-sm"
          >
            <Download className="w-4 h-4 text-[#C1762A]" />
            <span>Xuất Excel</span>
          </button>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-1.5 bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 active:scale-95 text-white shadow-md transition-all duration-200"
          >
            <Plus className="w-4 h-4" />
            <span>Thêm Người Dùng</span>
          </button>
        </div>
      </div>

      {/* ── 2. Quick Stat Chips (Đồng bộ SummaryCards - Định danh tài khoản) ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200">
          <div className="text-xs font-bold uppercase tracking-wider text-[#C1762A]">Tổng Tài Khoản</div>
          <div className="text-2xl font-black text-[#8C4905] mt-1.5">{stats.total}</div>
          <div className="text-xs text-[#C1762A]/70 mt-1">Định danh hệ thống</div>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200">
          <div className="text-xs font-bold uppercase tracking-wider text-[#C1762A]">Học Sinh</div>
          <div className="text-2xl font-black text-[#C1762A] mt-1.5">{stats.students}</div>
          <div className="text-xs text-[#C1762A]/70 mt-1">Tài khoản học sinh</div>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200">
          <div className="text-xs font-bold uppercase tracking-wider text-[#2B78C5]">Phụ Huynh</div>
          <div className="text-2xl font-black text-[#2B78C5] mt-1.5">{stats.parents}</div>
          <div className="text-xs text-[#2B78C5]/70 mt-1">Người giám sát</div>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-[#F1CCA6] shadow-sm hover:shadow-md transition-all duration-200">
          <div className="text-xs font-bold uppercase tracking-wider text-[#D93829]">Tạm Khóa</div>
          <div className="text-2xl font-black text-[#D93829] mt-1.5">{stats.suspended}</div>
          <div className="text-xs text-[#D93829]/70 mt-1">Vi phạm tiêu chuẩn</div>
        </div>
      </div>

      {/* ── 3. Search & Filter Bar ── */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] p-4 md:p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center justify-between">
          {/* Input Search */}
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-[#7E6B5A] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo tên học sinh, email, phụ huynh..."
              className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl pl-9 pr-8 py-2 text-xs md:text-sm text-[#2A1C0E] placeholder-[#7E6B5A] focus:outline-hidden focus:border-[#C1762A] focus:bg-white transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#7E6B5A] hover:text-[#2A1C0E]"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Dropdown Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
            >
              <option value="ALL">Tất cả vai trò</option>
              <option value="STUDENT">Học sinh (STUDENT)</option>
              <option value="MONITOR">Phụ huynh (MONITOR)</option>
              <option value="ADMIN">Quản trị viên (ADMIN)</option>
            </select>

            <select
              value={gradeFilter}
              onChange={(e) => setGradeFilter(e.target.value)}
              className="bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
            >
              <option value="ALL">Tất cả khối lớp</option>
              <option value="4">Lớp 4</option>
              <option value="5">Lớp 5</option>
              <option value="6">Lớp 6</option>
              <option value="7">Lớp 7</option>
              <option value="8">Lớp 8</option>
              <option value="9">Lớp 9</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
            >
              <option value="ALL">Tất cả trạng thái</option>
              <option value="ACTIVE">Đang hoạt động</option>
              <option value="SUSPENDED">Bị tạm khóa</option>
            </select>

            {(searchQuery || roleFilter !== "ALL" || gradeFilter !== "ALL" || statusFilter !== "ALL") && (
              <button
                onClick={handleResetFilters}
                className="px-3 py-2 rounded-xl text-xs font-bold text-[#8C4905] bg-[#F7ECE1] hover:bg-[#F1CCA6] transition-colors"
              >
                Đặt lại
              </button>
            )}
          </div>
        </div>

        {/* ── 3.1 Bulk Action Bar (Hiện khi chọn ít nhất 1 dòng) ── */}
        {selectedUserIds.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[#F1CCA6]/60 flex items-center justify-between flex-wrap gap-2 animate-fade-in bg-[#FFFDFB] p-2.5 rounded-xl">
            <div className="flex items-center gap-2 text-xs font-bold text-[#8C4905]">
              <span className="w-5 h-5 rounded-full bg-[#C1762A] text-white flex items-center justify-center text-[11px]">
                {selectedUserIds.length}
              </span>
              <span>Đã chọn {selectedUserIds.length} tài khoản</span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleBulkBan}
                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#FDF0ED] text-[#D93829] border border-[#F5BCB4] hover:bg-[#FBE4E1] transition-colors"
              >
                Khóa hàng loạt
              </button>
              <button
                onClick={handleBulkUnban}
                className="px-3 py-1.5 rounded-lg text-xs font-bold bg-[#EAF7EE] text-[#2A8C4A] border border-[#B7E4C4] hover:bg-[#D9F3E1] transition-colors"
              >
                Mở khóa hàng loạt
              </button>
              <button
                onClick={() => setSelectedUserIds([])}
                className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#7E6B5A] hover:bg-[#F7ECE1] transition-colors"
              >
                Bỏ chọn
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── 4. Main Data Table ── */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs md:text-sm">
            <thead>
              <tr className="bg-[#FBF4ED] border-b border-[#F1CCA6] text-[#8C4905] font-bold text-xs uppercase tracking-wider">
                <th className="py-3.5 px-4 w-10">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={handleSelectAll}
                    className="rounded border-[#E8D5C4] text-[#C1762A] focus:ring-[#C1762A] cursor-pointer"
                  />
                </th>
                <th className="py-3.5 px-4">Người dùng</th>
                <th className="py-3.5 px-4">Vai trò</th>
                <th className="py-3.5 px-4">Thông tin học tập & Gia đình</th>
                <th className="py-3.5 px-4">Điểm Tự Lực</th>
                <th className="py-3.5 px-4">Trạng thái</th>
                <th className="py-3.5 px-4 text-right">Thao tác</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#F1CCA6]/40">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-16 text-center">
                    <div className="flex flex-col items-center justify-center gap-2.5">
                      <svg
                        className="animate-spin h-8 w-8 text-[#C1762A]"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8v8H4z"
                        />
                      </svg>
                      <p className="text-xs font-semibold text-[#8C4905]">
                        Đang đồng bộ dữ liệu người dùng...
                      </p>
                    </div>
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-[#7E6B5A]">
                    <div className="w-12 h-12 rounded-2xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center mx-auto mb-3">
                      <Search className="w-6 h-6" />
                    </div>
                    <p className="font-bold text-[#2A1C0E]">Không tìm thấy người dùng phù hợp</p>
                    <p className="text-xs text-[#7E6B5A] mt-1">
                      Thử thay đổi từ khóa tìm kiếm hoặc bấm &quot;Đặt lại&quot; bộ lọc
                    </p>
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => {
                  const isSelected = selectedUserIds.includes(user.id);
                  const initials = user.name
                    .split(" ")
                    .map((w) => w[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase();

                  return (
                    <tr
                      key={user.id}
                      className={`hover:bg-[#FFFDFB] transition-colors ${
                        isSelected ? "bg-[#FFF9F3]" : ""
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleToggleSelect(user.id)}
                          className="rounded border-[#E8D5C4] text-[#C1762A] focus:ring-[#C1762A] cursor-pointer"
                        />
                      </td>

                      {/* User Info */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 shadow-2xs ${
                              user.role === "STUDENT"
                                ? "bg-[#FFF3E6] text-[#C1762A] border border-[#F1CCA6]"
                                : user.role === "MONITOR"
                                ? "bg-[#EBF4FC] text-[#2B78C5] border border-[#BADEF7]"
                                : "bg-[#F3E8FF] text-[#7C3AED] border border-[#DDD6FE]"
                            }`}
                          >
                            {initials}
                          </div>
                          <div className="min-w-0">
                            <div className="font-bold text-[#2A1C0E] hover:text-[#C1762A] transition-colors truncate">
                              {user.name}
                            </div>
                            <div className="text-xs text-[#7E6B5A] truncate">{user.email}</div>
                          </div>
                        </div>
                      </td>

                      {/* Role Badge */}
                      <td className="py-3 px-4">
                        {user.role === "STUDENT" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-[#FFF3E6] text-[#C1762A] border border-[#F1CCA6]">
                            <GraduationCap className="w-3 h-3" />
                            Học sinh
                          </span>
                        )}
                        {user.role === "MONITOR" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-[#EBF4FC] text-[#2B78C5] border border-[#BADEF7]">
                            <UserCheck className="w-3 h-3" />
                            Phụ huynh
                          </span>
                        )}
                        {user.role === "ADMIN" && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-[#F3E8FF] text-[#7C3AED] border border-[#DDD6FE]">
                            <ShieldCheck className="w-3 h-3" />
                            Quản trị
                          </span>
                        )}
                      </td>

                      {/* Academic / Family Link Info */}
                      <td className="py-3 px-4">
                        {user.role === "STUDENT" ? (
                          <div>
                            <div className="font-semibold text-xs text-[#2A1C0E]">
                              Khối Lớp {user.grade}
                            </div>
                            <div className="text-[11px] text-[#7E6B5A] flex items-center gap-2 mt-0.5">
                              {user.linked_parent ? (
                                <span>PH: {user.linked_parent.name.split(" ")[0]}...</span>
                              ) : (
                                <span className="text-[#A18E7F]">Chưa nối PH</span>
                              )}
                              {user.streak_days > 0 && (
                                <span className="inline-flex items-center gap-0.5 text-[#C1762A] font-bold">
                                  <Flame className="w-3 h-3 fill-[#C1762A]" />
                                  {user.streak_days}d
                                </span>
                              )}
                            </div>
                          </div>
                        ) : user.role === "MONITOR" ? (
                          <div>
                            <div className="font-semibold text-xs text-[#2A1C0E]">
                              Đã liên kết {user.linked_students?.length || 0} con
                            </div>
                            <div className="text-[11px] text-[#7E6B5A] truncate max-w-[180px]">
                              {user.linked_students && user.linked_students.length > 0
                                ? user.linked_students.map((s) => s.name).join(", ")
                                : "Chưa có học sinh"}
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-[#7E6B5A]">Hệ thống</span>
                        )}
                      </td>

                      {/* Independence Score */}
                      <td className="py-3 px-4">
                        {user.avg_independence_score !== null &&
                        user.avg_independence_score !== undefined ? (
                          <div className="flex items-center gap-2">
                            <div className="w-14 h-1.5 bg-[#E8D5C4] rounded-full overflow-hidden flex-shrink-0">
                              <div
                                className={`h-full rounded-full transition-all duration-300 ${
                                  user.avg_independence_score >= 80
                                    ? "bg-[#C1762A]"
                                    : user.avg_independence_score >= 60
                                    ? "bg-[#F59E0B]"
                                    : "bg-[#D93829]"
                                }`}
                                style={{ width: `${user.avg_independence_score}%` }}
                              />
                            </div>
                            <span
                              className={`font-bold text-xs ${
                                user.avg_independence_score >= 80
                                  ? "text-[#8C4905]"
                                  : user.avg_independence_score >= 60
                                  ? "text-[#F59E0B]"
                                  : "text-[#D93829]"
                              }`}
                            >
                              {user.avg_independence_score}/100
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-[#A18E7F]">N/A</span>
                        )}
                      </td>

                      {/* Status Badge */}
                      <td className="py-3 px-4">
                        {user.status === "ACTIVE" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#EAF7EE] text-[#2A8C4A] border border-[#B7E4C4]">
                            <span className="w-1.5 h-1.5 rounded-full bg-[#2A8C4A]" />
                            Hoạt động
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#FDF0ED] text-[#D93829] border border-[#F5BCB4]">
                            <span className="w-1.5 h-1.5 rounded-full bg-[#D93829]" />
                            Tạm khóa
                          </span>
                        )}
                      </td>

                      {/* Action Buttons */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleViewUserLogs(user)}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#EBF4FC] hover:bg-[#D5E9FA] text-[#2B78C5] border border-[#BADEF7] flex items-center gap-1 transition-colors shadow-2xs"
                            title={`Xem nhật ký log hoạt động của ${user.name}`}
                          >
                            <FileText className="w-3.5 h-3.5" />
                            <span>Xem Log</span>
                          </button>

                          <button
                            onClick={() => setDetailUser(user)}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#F7ECE1] hover:bg-[#F1CCA6] text-[#8C4905] transition-colors"
                            title="Xem chi tiết hồ sơ"
                          >
                            Chi tiết
                          </button>

                          {user.role === "ADMIN" ? (
                            <span className="text-[11px] font-bold px-2 py-1 rounded-lg bg-[#F3E8FF] text-[#7C3AED] border border-[#DDD6FE]">
                              Admin Root
                            </span>
                          ) : user.status === "ACTIVE" ? (
                            <button
                              onClick={() => setBanTargetUser(user)}
                              className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#FFFDFB] text-[#D93829] border border-[#F5BCB4] hover:bg-[#FDF0ED] transition-colors"
                              title="Khóa tài khoản"
                            >
                              Khóa
                            </button>
                          ) : (
                            <button
                              onClick={() => handleUnbanUser(user)}
                              className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#C1762A] text-white hover:bg-[#8C4905] transition-colors"
                              title="Mở khóa tài khoản"
                            >
                              Mở khóa
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── 5. Pagination Bar ── */}
        <div className="bg-[#FBF4ED] border-t border-[#E8D5C4] px-4 py-3 flex items-center justify-between text-xs text-[#7E6B5A]">
          <div>
            Hiển thị <span className="font-bold text-[#2A1C0E]">{filteredUsers.length}</span> trên tổng số{" "}
            <span className="font-bold text-[#2A1C0E]">{users.length}</span> người dùng
          </div>

          <div className="flex items-center gap-1">
            <button
              disabled
              className="w-7 h-7 rounded-lg border border-[#E8D5C4] flex items-center justify-center text-[#7E6B5A] opacity-50 cursor-not-allowed"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button className="w-7 h-7 rounded-lg bg-[#C1762A] text-white font-bold flex items-center justify-center">
              1
            </button>
            <button
              onClick={() => showToast("Đã tải trang 2")}
              className="w-7 h-7 rounded-lg border border-[#E8D5C4] hover:bg-[#F7ECE1] text-[#2A1C0E] flex items-center justify-center font-medium"
            >
              2
            </button>
            <button
              onClick={() => showToast("Đã tải trang 3")}
              className="w-7 h-7 rounded-lg border border-[#E8D5C4] hover:bg-[#F7ECE1] text-[#2A1C0E] flex items-center justify-center font-medium"
            >
              3
            </button>
            <button
              onClick={() => showToast("Đã tải trang kế tiếp")}
              className="w-7 h-7 rounded-lg border border-[#E8D5C4] hover:bg-[#F7ECE1] flex items-center justify-center text-[#2A1C0E]"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ── 6. Modal: Chi Tiết Hồ Sơ User (UserDetailModal) ── */}
      {detailUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setDetailUser(null)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
          />

          <div className="relative bg-white rounded-2xl border border-[#E8D5C4] shadow-2xl max-w-lg w-full overflow-hidden animate-modal-in z-10">
            {/* Header Modal */}
            <div className="bg-[#F7ECE1] border-b border-[#E8D5C4] px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base text-[#8C4905]">
                  Chi Tiết Hồ Sơ Người Dùng
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white text-[#7E6B5A] border border-[#E8D5C4]">
                  {detailUser.id}
                </span>
              </div>
              <button
                onClick={() => setDetailUser(null)}
                className="w-7 h-7 rounded-lg text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-black/5 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body Modal */}
            <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto">
              {/* User Identity Banner */}
              <div className="flex items-center gap-3.5 p-3.5 rounded-xl bg-[#FFFDFB] border border-[#F1CCA6]/60">
                <div className="w-12 h-12 rounded-xl bg-[#FFF3E6] text-[#C1762A] border border-[#F1CCA6] flex items-center justify-center text-base font-extrabold shadow-2xs">
                  {detailUser.name
                    .split(" ")
                    .map((w) => w[0])
                    .join("")
                    .slice(0, 2)
                    .toUpperCase()}
                </div>
                <div>
                  <h3 className="font-extrabold text-[#2A1C0E] text-base">{detailUser.name}</h3>
                  <p className="text-xs text-[#7E6B5A]">{detailUser.email}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#FFF3E6] text-[#C1762A] border border-[#F1CCA6]">
                      {detailUser.role === "STUDENT"
                        ? `Học sinh Lớp ${detailUser.grade}`
                        : detailUser.role === "MONITOR"
                        ? "Phụ huynh (MONITOR)"
                        : "Quản trị viên (ADMIN)"}
                    </span>
                    <span
                      className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                        detailUser.status === "ACTIVE"
                          ? "bg-[#EAF7EE] text-[#2A8C4A] border border-[#B7E4C4]"
                          : "bg-[#FDF0ED] text-[#D93829] border border-[#F5BCB4]"
                      }`}
                    >
                      {detailUser.status === "ACTIVE" ? "Đang hoạt động" : "Bị tạm khóa"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Learning Stats Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-[#FBF4ED] p-3 rounded-xl border border-[#E8D5C4]/70">
                  <span className="text-[#7E6B5A] block mb-1">Điểm tự lập trung bình:</span>
                  <span className="text-base font-extrabold text-[#C1762A]">
                    {detailUser.avg_independence_score !== null
                      ? `${detailUser.avg_independence_score}/100`
                      : "Không áp dụng"}
                  </span>
                </div>
                <div className="bg-[#FBF4ED] p-3 rounded-xl border border-[#E8D5C4]/70">
                  <span className="text-[#7E6B5A] block mb-1">Chuỗi ngày học liên tục:</span>
                  <span className="text-base font-extrabold text-[#8C4905] flex items-center gap-1">
                    <Flame className="w-4 h-4 fill-[#C1762A] text-[#C1762A]" />
                    {detailUser.streak_days} ngày
                  </span>
                </div>
                <div className="bg-[#FBF4ED] p-3 rounded-xl border border-[#E8D5C4]/70">
                  <span className="text-[#7E6B5A] block mb-1">Tổng phiên đối thoại AI:</span>
                  <span className="text-base font-extrabold text-[#2A1C0E]">
                    {detailUser.total_sessions} phiên
                  </span>
                </div>
                <div className="bg-[#FBF4ED] p-3 rounded-xl border border-[#E8D5C4]/70">
                  <span className="text-[#7E6B5A] block mb-1">Bài toán giải thành công:</span>
                  <span className="text-base font-extrabold text-[#2A8C4A]">
                    {detailUser.total_problems_solved} bài
                  </span>
                </div>
              </div>

              {/* Family Connections */}
              <div className="border border-[#E8D5C4] rounded-xl p-3.5 bg-white">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#8C4905] mb-2">
                  Liên Kết Gia Đình
                </h4>
                {detailUser.role === "STUDENT" ? (
                  detailUser.linked_parent ? (
                    <div className="flex items-center justify-between text-xs">
                      <div>
                        <div className="font-bold text-[#2A1C0E]">
                          {detailUser.linked_parent.name}
                        </div>
                        <div className="text-[#7E6B5A]">{detailUser.linked_parent.email}</div>
                      </div>
                      <span className="text-xs text-[#C1762A] font-semibold">
                        SĐT: {detailUser.linked_parent.phone || "Chưa cập nhật"}
                      </span>
                    </div>
                  ) : (
                    <p className="text-xs text-[#7E6B5A]">Chưa có tài khoản phụ huynh liên kết.</p>
                  )
                ) : detailUser.role === "MONITOR" ? (
                  detailUser.linked_students && detailUser.linked_students.length > 0 ? (
                    <div className="space-y-1.5">
                      {detailUser.linked_students.map((st) => (
                        <div
                          key={st.id}
                          className="flex items-center justify-between text-xs p-2 rounded-lg bg-[#FBF4ED]"
                        >
                          <span className="font-semibold text-[#2A1C0E]">{st.name}</span>
                          <span className="text-[#C1762A] font-bold">
                            Lớp {st.grade} • {st.avg_independence_score}đ
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-[#7E6B5A]">Chưa liên kết học sinh nào.</p>
                  )
                ) : (
                  <p className="text-xs text-[#7E6B5A]">Tài khoản quản trị viên hệ thống.</p>
                )}
              </div>

              {/* Recent Accomplishments */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#8C4905] mb-2">
                  Bài Toán Giải Gần Nhất
                </h4>
                <div className="space-y-2 text-xs">
                  <div className="p-2.5 rounded-xl bg-[#FBF4ED] border border-[#E8D5C4] flex items-center justify-between">
                    <div>
                      <div className="font-bold text-[#2A1C0E]">Toán 5: Phân số & Hỗn số</div>
                      <div className="text-[11px] text-[#7E6B5A]">Hoàn thành hôm nay • 0 gợi ý</div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-[#EAF7EE] text-[#2A8C4A] font-extrabold text-[11px]">
                      100đ
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-[#FBF4ED] border border-[#E8D5C4] flex items-center justify-between">
                    <div>
                      <div className="font-bold text-[#2A1C0E]">Toán 5: Diện tích hình thang</div>
                      <div className="text-[11px] text-[#7E6B5A]">Hoàn thành hôm qua • 1 gợi ý</div>
                    </div>
                    <span className="px-2 py-0.5 rounded-full bg-[#FFF3E6] text-[#C1762A] font-extrabold text-[11px]">
                      85đ
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer Modal */}
            <div className="bg-[#FBF4ED] border-t border-[#E8D5C4] px-5 py-3 flex items-center justify-between gap-3">
              <button
                onClick={() => setDetailUser(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-[#E8D5C4] text-[#2A1C0E] hover:bg-[#F7ECE1] transition-colors"
              >
                Đóng
              </button>

              <div className="flex items-center gap-2 flex-wrap justify-end">
                <button
                  onClick={() => {
                    handleViewUserLogs(detailUser);
                    setDetailUser(null);
                  }}
                  className="px-3.5 py-2 rounded-xl text-xs font-bold bg-[#EBF4FC] text-[#2B78C5] border border-[#BADEF7] hover:bg-[#D5E9FA] flex items-center gap-1.5 transition-colors shadow-2xs"
                  title={`Tra cứu nhật ký log và phiên chat của ${detailUser.name}`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Xem Log Tài Khoản</span>
                </button>

                <button
                  onClick={() => showToast(`Đã gửi báo cáo học tập của ${detailUser.name} tới phụ huynh!`)}
                  className="px-3.5 py-2 rounded-xl text-xs font-bold bg-[#FDF6EE] text-[#C1762A] border border-[#F1CCA6] hover:bg-[#FBECE0] transition-colors"
                >
                  Gửi Báo Cáo Phụ Huynh
                </button>

                {detailUser.role === "ADMIN" ? (
                  <span className="text-xs font-bold text-[#7C3AED] px-3.5 py-2 rounded-xl bg-[#F3E8FF] border border-[#DDD6FE]">
                    Tài khoản Admin Duy Nhất
                  </span>
                ) : detailUser.status === "ACTIVE" ? (
                  <button
                    onClick={() => {
                      setBanTargetUser(detailUser);
                    }}
                    className="px-3.5 py-2 rounded-xl text-xs font-bold bg-[#D93829] text-white hover:bg-[#B92314] transition-colors"
                  >
                    Khóa Tài Khoản
                  </button>
                ) : (
                  <button
                    onClick={() => handleUnbanUser(detailUser)}
                    className="px-3.5 py-2 rounded-xl text-xs font-bold bg-[#2A8C4A] text-white hover:bg-[#23773F] transition-colors"
                  >
                    Mở Khóa Ngay
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 7. Modal: Tạm Khóa Tài Khoản (BanUserModal) ── */}
      {banTargetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setBanTargetUser(null)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
          />

          <div className="relative bg-white rounded-2xl border border-[#F5BCB4] shadow-2xl max-w-md w-full overflow-hidden animate-modal-in z-10">
            {/* Header */}
            <div className="bg-[#FDF0ED] border-b border-[#F5BCB4] px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-[#D93829]">
                <ShieldAlert className="w-5 h-5" />
                <h3 className="font-extrabold text-base">Xác Nhận Tạm Khóa Tài Khoản</h3>
              </div>
              <button
                onClick={() => setBanTargetUser(null)}
                className="w-7 h-7 rounded-lg text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-black/5 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body */}
            <div className="p-5 space-y-4 text-xs md:text-sm">
              <p className="text-[#2A1C0E] leading-relaxed">
                Bạn đang thực hiện thao tác tạm khóa tài khoản của{" "}
                <strong className="text-[#D93829]">{banTargetUser.name}</strong> ({banTargetUser.email}).
                Học sinh/Phụ huynh sẽ không thể đăng nhập hoặc tiếp tục chat với AI cho đến khi được mở khóa.
              </p>

              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1.5">
                  Lý do khóa tài khoản <span className="text-[#D93829]">*</span>
                </label>
                <select
                  value={banReason}
                  onChange={(e) => setBanReason(e.target.value)}
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                >
                  <option>Vi phạm ngôn từ thiếu văn hóa (Toxic)</option>
                  <option>Cố tình spam câu hỏi đòi giải hộ</option>
                  <option>Thử nghiệm Prompt Injection / Jailbreak</option>
                  <option>Theo yêu cầu của Phụ huynh học sinh</option>
                  <option>Tài khoản có dấu hiệu chia sẻ bất thường</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1.5">
                  Thời hạn khóa
                </label>
                <select
                  value={banDuration}
                  onChange={(e) => setBanDuration(e.target.value)}
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                >
                  <option>24 Giờ</option>
                  <option>3 Ngày</option>
                  <option>7 Ngày</option>
                  <option>30 Ngày</option>
                  <option>Vĩnh viễn (Chỉ định Admin cấp cao)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1.5">
                  Ghi chú nội bộ cho Ban Quản Trị
                </label>
                <textarea
                  rows={2}
                  value={banNote}
                  onChange={(e) => setBanNote(e.target.value)}
                  placeholder="Ghi chú thêm về bối cảnh vi phạm..."
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl p-2.5 text-xs text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white resize-none"
                />
              </div>
            </div>

            {/* Footer */}
            <div className="bg-[#FDF0ED]/50 border-t border-[#F5BCB4] px-5 py-3 flex items-center justify-end gap-2.5">
              <button
                onClick={() => setBanTargetUser(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-[#E8D5C4] text-[#2A1C0E] hover:bg-[#F7ECE1] transition-colors"
              >
                Hủy Bỏ
              </button>
              <button
                onClick={handleConfirmBan}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-[#D93829] hover:bg-[#B92314] text-white shadow-xs transition-colors"
              >
                Xác Nhận Khóa
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 8. Modal: Tạo Người Dùng Mới (CreateUserModal) ── */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setIsCreateModalOpen(false)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
          />

          <div className="relative bg-white rounded-2xl border border-[#E8D5C4] shadow-2xl max-w-md w-full overflow-hidden animate-modal-in z-10">
            {/* Header */}
            <div className="bg-[#F7ECE1] border-b border-[#E8D5C4] px-5 py-4 flex items-center justify-between">
              <h3 className="font-extrabold text-base text-[#8C4905]">
                + Thêm Tài Khoản Người Dùng Mới
              </h3>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="w-7 h-7 rounded-lg text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-black/5 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleCreateUser} className="p-5 space-y-3.5 text-xs md:text-sm">
              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1">
                  Họ và tên <span className="text-[#D93829]">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newUserName}
                  onChange={(e) => setNewUserName(e.target.value)}
                  placeholder="VD: Trần Bảo An"
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs md:text-sm text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1">
                  Địa chỉ Email <span className="text-[#D93829]">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={newUserEmail}
                  onChange={(e) => setNewUserEmail(e.target.value)}
                  placeholder="VD: baoan.tran@example.com"
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs md:text-sm text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#2A1C0E] mb-1">
                    Vai trò <span className="text-[#D93829]">*</span>
                  </label>
                  <select
                    value={newUserRole}
                    onChange={(e) => setNewUserRole(e.target.value as UserRole)}
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                  >
                    <option value="STUDENT">Học sinh</option>
                    <option value="MONITOR">Phụ huynh</option>
                    <option value="ADMIN">Quản trị viên</option>
                  </select>
                </div>

                {newUserRole === "STUDENT" && (
                  <div>
                    <label className="block text-xs font-bold text-[#2A1C0E] mb-1">Khối lớp</label>
                    <select
                      value={newUserGrade}
                      onChange={(e) => setNewUserGrade(Number(e.target.value))}
                      className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                    >
                      <option value={4}>Lớp 4</option>
                      <option value={5}>Lớp 5</option>
                      <option value={6}>Lớp 6</option>
                      <option value={7}>Lớp 7</option>
                      <option value={8}>Lớp 8</option>
                      <option value={9}>Lớp 9</option>
                    </select>
                  </div>
                )}
              </div>

              <div className="pt-2 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-[#E8D5C4] text-[#2A1C0E] hover:bg-[#F7ECE1] transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-[#C1762A] hover:bg-[#8C4905] text-white shadow-xs transition-colors"
                >
                  Tạo Tài Khoản
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 9. Toast Notification Pill ── */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-message-pop">
          <div className="bg-[#2A1C0E] text-white px-4 py-3 rounded-xl border-l-4 border-[#C1762A] shadow-xl flex items-center gap-2.5 text-xs md:text-sm font-medium">
            <CheckCircle2 className="w-4 h-4 text-[#C1762A] flex-shrink-0" />
            <span>{toastMessage}</span>
          </div>
        </div>
      )}
    </div>
  );
}
