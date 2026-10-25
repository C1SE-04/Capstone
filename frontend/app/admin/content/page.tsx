"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Trash2,
  Edit3,
  Lightbulb,
  X,
  Sparkles,
  Layers,
  GraduationCap,
  MessageSquare,
  Image as ImageIcon,
  Check,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { AdminTopic } from "@/types/admin";

// Dữ liệu mẫu chuẩn cấu trúc Backend /admin/mock/content/topics & Figma Mockup của Bảo (T7.23 & T7.31)
const INITIAL_TOPICS: AdminTopic[] = [
  // Lớp 5
  {
    id: "top_g5_01",
    grade: 5,
    title: "TOAN5-CD-01: Phân Số & Hỗn Số",
    slug: "phan-so-hon-so-toan-5",
    description: "Cộng trừ phân số khác mẫu số, quy đồng mẫu số và các bài toán rút gọn phân số phức tạp.",
    curriculum: "Cánh Diều",
    category: "Số học",
    problem_count: 32,
    active_sessions_count: 890,
    is_enabled: true,
    comprehension_rate: 91.2,
    socratic_prompts: {
      level1: "Đề bài cho biết các phân số này có mẫu số như thế nào với nhau rồi em nhỉ?",
      level2: "Để cộng hai phân số khác mẫu số, bước đầu tiên chúng ta cần đưa chúng về cùng mẫu số chung là bao nhiêu?",
      level3: "Rất tốt! Em hãy lấy tử số mới cộng lại với nhau và kiểm tra xem phân số đã tối giản chưa nhé.",
    },
  },
  {
    id: "top_g5_02",
    grade: 5,
    title: "TOAN5-KNTT-04: Thể Tích Hình Hộp Chữ Nhật",
    slug: "the-tich-hinh-hop-chu-nhat-toan-5",
    description: "Tính diện tích xung quanh, thể tích và các bài toán thực tế về bể nước, mực nước dâng.",
    curriculum: "Kết nối tri thức",
    category: "Hình học",
    problem_count: 28,
    active_sessions_count: 640,
    is_enabled: true,
    comprehension_rate: 88.5,
    socratic_prompts: {
      level1: "Hình hộp chữ nhật trong đề bài có chiều dài, chiều rộng và chiều cao lần lượt là bao nhiêu cm em nhỉ?",
      level2: "Công thức tính thể tích của một hình hộp chữ nhật khi biết ba kích thước a, b, c là gì em nhỉ?",
      level3: "Chính xác! Em hãy thực hiện phép nhân a × b × c và chú ý đơn vị đo thể tích là cm³ hay dm³ nhé.",
    },
  },
  {
    id: "top_g5_03",
    grade: 5,
    title: "TOAN5-CD-08: Toán Chuyển Động Đều (v, s, t)",
    slug: "toan-chuyen-dong-deu-toan-5",
    description: "Hai xe đi ngược chiều gặp nhau, chuyển động cùng chiều đuổi nhau và tính vận tốc trung bình.",
    curriculum: "Cánh Diều",
    category: "Chuyển động",
    problem_count: 45,
    active_sessions_count: 740,
    is_enabled: true,
    comprehension_rate: 78.6,
    socratic_prompts: {
      level1: "Hai xe xuất phát cùng một lúc và đi ngược chiều hay cùng chiều nhau vậy em?",
      level2: "Sau mỗi giờ, hai xe cùng đi được quãng đường bằng tổng hay hiệu vận tốc của hai xe em nhỉ?",
      level3: "Đúng rồi! Vậy thời gian để hai xe gặp nhau sẽ bằng tổng quãng đường chia cho tổng vận tốc.",
    },
  },
  {
    id: "top_g5_04",
    grade: 5,
    title: "TOAN5-CTST-12: Tỉ Số Phần Trăm & Ứng Dụng",
    slug: "ti-so-phan-tram-toan-5",
    description: "Tính tỉ số phần trăm của hai số, tìm giá trị phần trăm của một số và bài toán tính lãi suất gửi tiết kiệm.",
    curriculum: "Chân trời sáng tạo",
    category: "Số học",
    problem_count: 36,
    active_sessions_count: 510,
    is_enabled: true,
    comprehension_rate: 86.4,
    socratic_prompts: {
      level1: "Đề bài yêu cầu chúng ta tìm tỉ số phần trăm giữa số lượng nào với số lượng nào em nhỉ?",
      level2: "Để viết một phân số hoặc thương dưới dạng tỉ số phần trăm, em cần nhân thương đó với 100 rồi thêm ký hiệu %.",
      level3: "Thử chia tử số cho mẫu số xem được số thập phân là bao nhiêu em nhé!",
    },
  },

  // Lớp 4
  {
    id: "top_g4_01",
    grade: 4,
    title: "TOAN4-KNTT-02: Tìm Hai Số Khi Biết Tổng Và Hiệu",
    slug: "tim-hai-so-tong-va-hieu-g4",
    description: "Phương pháp vẽ sơ đồ đoạn thẳng, công thức số lớn = (tổng + hiệu) / 2 và số bé = (tổng - hiệu) / 2.",
    curriculum: "Kết nối tri thức",
    category: "Toán có lời văn",
    problem_count: 38,
    active_sessions_count: 620,
    is_enabled: true,
    comprehension_rate: 93.5,
    socratic_prompts: {
      level1: "Đề bài đã cho chúng ta biết tổng của hai số và hiệu của hai số là bao nhiêu rồi em nhỉ?",
      level2: "Nếu ta bớt đi phần hơn (hiệu) ở số lớn, thì hai phần còn lại sẽ bằng nhau và bằng hai lần số nào?",
      level3: "Tốt lắm! Em hãy tính số bé trước hoặc lấy (tổng + hiệu) chia 2 để tìm ra số lớn nhé.",
    },
  },
  {
    id: "top_g4_02",
    grade: 4,
    title: "TOAN4-CD-05: Góc Nhọn, Góc Tù, Góc Bẹt",
    slug: "goc-nhon-goc-tu-goc-bet-g4",
    description: "Nhận biết các loại góc bằng ê-ke, vẽ hai đường thẳng vuông góc và song song.",
    curriculum: "Cánh Diều",
    category: "Hình học",
    problem_count: 24,
    active_sessions_count: 390,
    is_enabled: true,
    comprehension_rate: 95.0,
    socratic_prompts: {
      level1: "Em hãy đặt góc vuông của ê-ke vào đỉnh góc để kiểm tra xem góc này lớn hơn hay bé hơn góc vuông nhé?",
      level2: "Góc bé hơn góc vuông gọi là góc gì em nhỉ?",
      level3: "Chính xác là góc nhọn! Em ghi đáp án vào vở nhé.",
    },
  },

  // Lớp 6
  {
    id: "top_g6_01",
    grade: 6,
    title: "TOAN6-KNTT-03: Tập Hợp Số Nguyên & Quy Tắc Dấu Ngoặc",
    slug: "so-nguyen-dau-ngoac-g6",
    description: "Cộng trừ số nguyên cùng dấu, khác dấu và quy tắc đổi dấu khi bỏ ngoặc có dấu trừ đằng trước.",
    curriculum: "Kết nối tri thức",
    category: "Số học",
    problem_count: 42,
    active_sessions_count: 680,
    is_enabled: true,
    comprehension_rate: 85.2,
    socratic_prompts: {
      level1: "Trước dấu ngoặc là dấu cộng hay dấu trừ vậy em?",
      level2: "Khi bỏ dấu ngoặc có dấu trừ đằng trước, các dấu bên trong ngoặc sẽ thay đổi như thế nào?",
      level3: "Đúng rồi, cộng thành trừ và trừ thành cộng. Giờ em nhóm các số nguyên dương và số nguyên âm lại nhé.",
    },
  },

  // Lớp 7
  {
    id: "top_g7_01",
    grade: 7,
    title: "TOAN7-CD-02: Tam Giác Bằng Nhau (c-c-c, c-g-c, g-c-g)",
    slug: "tam-giac-bang-nhau-toan-7",
    description: "Chứng minh hai tam giác bằng nhau theo 3 trường hợp cơ bản và ứng dụng chứng minh góc bằng nhau.",
    curriculum: "Cánh Diều",
    category: "Hình học",
    problem_count: 35,
    active_sessions_count: 590,
    is_enabled: true,
    comprehension_rate: 81.8,
    socratic_prompts: {
      level1: "Hai tam giác em đang xét có những cạnh nào hoặc góc nào bằng nhau theo giả thiết?",
      level2: "Góc bằng nhau đó có nằm xen giữa hai cạnh bằng nhau đã biết không em nhỉ?",
      level3: "Tuyệt vời, đó là trường hợp Cạnh - Góc - Cạnh (c-g-c). Em suy ra các cặp cạnh và góc tương ứng bằng nhau nhé.",
    },
  },

  // Lớp 8
  {
    id: "top_g8_01",
    grade: 8,
    title: "TOAN8-KNTT-01: 7 Hằng Đẳng Thức Đáng Nhớ",
    slug: "hang-dang-thuc-dang-nho-g8",
    description: "Bình phương một tổng, bình phương một hiệu, hiệu hai bình phương và ứng dụng phân tích đa thức thành nhân tử.",
    curriculum: "Kết nối tri thức",
    category: "Đại số",
    problem_count: 50,
    active_sessions_count: 920,
    is_enabled: true,
    comprehension_rate: 84.5,
    socratic_prompts: {
      level1: "Biểu thức này có dạng bình phương của một hiệu (A - B)² hay hiệu hai bình phương A² - B² em nhỉ?",
      level2: "Em hãy xác định đâu đóng vai trò là A và đâu đóng vai trò là B trong biểu thức trên?",
      level3: "Chính xác! Giờ em áp dụng công thức khai triển A² - 2AB + B² để tính toán nhé.",
    },
  },

  // Lớp 9
  {
    id: "top_g9_01",
    grade: 9,
    title: "TOAN9-CD-04: Hệ Hai Phương Trình Bậc Nhất Hai Ẩn",
    slug: "he-phuong-trinh-bac-nhat-hai-an-g9",
    description: "Giải hệ phương trình bằng phương pháp thế, phương pháp cộng đại số và giải toán bằng cách lập hệ phương trình.",
    curriculum: "Cánh Diều",
    category: "Đại số",
    problem_count: 48,
    active_sessions_count: 1150,
    is_enabled: true,
    comprehension_rate: 87.0,
    socratic_prompts: {
      level1: "Hệ phương trình này có hệ số của x hoặc y ở hai phương trình đối nhau hoặc bằng nhau chưa em?",
      level2: "Nếu chưa, em có thể nhân phương trình (1) với bao nhiêu để hệ số của x hoặc y bằng nhau?",
      level3: "Đúng rồi! Giờ em trừ hai phương trình theo vế để khử biến x và tìm y trước nhé.",
    },
  },
];

export default function AdminContentPage() {
  const { data: session } = useSession();

  // State
  const [topics, setTopics] = useState<AdminTopic[]>(INITIAL_TOPICS);
  const [selectedGrade, setSelectedGrade] = useState<number>(5);
  const [searchQuery, setSearchQuery] = useState("");
  const [curriculumFilter, setCurriculumFilter] = useState<string>("ALL");
  const [categoryFilter, setCategoryFilter] = useState<string>("ALL");

  // Modals state
  const [previewTopic, setPreviewTopic] = useState<AdminTopic | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [editingTopic, setEditingTopic] = useState<AdminTopic | null>(null);
  const [deleteTargetTopic, setDeleteTargetTopic] = useState<AdminTopic | null>(null);

  // Form thêm / sửa
  const [formTitle, setFormTitle] = useState("");
  const [formGrade, setFormGrade] = useState<number>(5);
  const [formCurriculum, setFormCurriculum] = useState<"Cánh Diều" | "Kết nối tri thức" | "Chân trời sáng tạo">("Cánh Diều");
  const [formCategory, setFormCategory] = useState<"Số học" | "Hình học" | "Đại số" | "Chuyển động" | "Ứng dụng" | "Toán có lời văn">("Số học");
  const [formDesc, setFormDesc] = useState("");
  const [formLevel1, setFormLevel1] = useState("");
  const [formLevel2, setFormLevel2] = useState("");
  const [formLevel3, setFormLevel3] = useState("");
  const [formProblemCount, setFormProblemCount] = useState<number>(30);

  // Toast feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  }, []);

  // Fetch từ API /admin/mock/content/topics nếu có backend
  const fetchTopics = useCallback(async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${backendUrl}/admin/mock/content/topics`, {
        headers: {
          Authorization: `Bearer ${(session as any)?.access_token || ""}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.items && Array.isArray(data.items)) {
          // Kết hợp dữ liệu socratic prompts phong phú
          setTopics((prev) => {
            const map = new Map(prev.map((t) => [t.id, t]));
            data.items.forEach((item: any) => {
              if (map.has(item.id)) {
                map.set(item.id, { ...map.get(item.id)!, ...item });
              } else {
                map.set(item.id, {
                  id: item.id,
                  grade: item.grade,
                  title: item.title,
                  slug: item.slug,
                  description: item.description,
                  curriculum: "Cánh Diều",
                  category: "Số học",
                  problem_count: item.problem_count || 20,
                  active_sessions_count: item.active_sessions_count || 100,
                  is_enabled: item.is_enabled ?? true,
                  comprehension_rate: 88.0,
                  socratic_prompts: {
                    level1: "Đề bài cho biết những dữ kiện quan trọng nào em nhỉ?",
                    level2: "Để tìm được kết quả, em cần vận dụng công thức hoặc định lý nào?",
                    level3: "Thử tính toán bước cuối cùng và đối chiếu lại với câu hỏi nhé!",
                  },
                });
              }
            });
            return Array.from(map.values());
          });
        }
      }
    } catch {
      // bỏ qua lỗi offline
    }
  }, [session]);

  useEffect(() => {
    if ((session as any)?.access_token) {
      fetchTopics();
    }
  }, [fetchTopics, session]);

  // Lọc chủ đề theo khối lớp đang chọn và các bộ lọc
  const filteredTopics = useMemo(() => {
    return topics.filter((t) => {
      // Khối lớp
      if (t.grade !== selectedGrade) return false;
      // Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchTitle = t.title.toLowerCase().includes(q);
        const matchDesc = t.description.toLowerCase().includes(q);
        const matchSlug = t.slug.toLowerCase().includes(q);
        if (!matchTitle && !matchDesc && !matchSlug) return false;
      }
      // Bộ sách
      if (curriculumFilter !== "ALL" && t.curriculum !== curriculumFilter) return false;
      // Dạng toán
      if (categoryFilter !== "ALL" && t.category !== categoryFilter) return false;

      return true;
    });
  }, [topics, selectedGrade, searchQuery, curriculumFilter, categoryFilter]);

  // Thống kê nhanh cho khối lớp đang chọn
  const gradeStats = useMemo(() => {
    const list = topics.filter((t) => t.grade === selectedGrade);
    const totalTopics = list.length;
    const totalProblems = list.reduce((acc, curr) => acc + curr.problem_count, 0);
    const avgRate =
      totalTopics > 0
        ? Math.round(
            (list.reduce((acc, curr) => acc + curr.comprehension_rate, 0) / totalTopics) * 10
          ) / 10
        : 88.5;
    return { totalTopics, totalProblems, avgRate };
  }, [topics, selectedGrade]);

  // Bật / Tắt chủ đề
  const handleToggleTopic = (id: string, current: boolean) => {
    setTopics((prev) =>
      prev.map((t) => (t.id === id ? { ...t, is_enabled: !current } : t))
    );
    showToast(
      !current
        ? "Đã kích hoạt chủ đề cho AI trợ giảng giải đáp!"
        : "Đã tạm ẩn chủ đề khỏi trợ giảng SocraticKid!"
    );
  };

  // Mở modal thêm chủ đề
  const handleOpenAddModal = () => {
    setEditingTopic(null);
    setFormTitle("");
    setFormGrade(selectedGrade);
    setFormCurriculum("Cánh Diều");
    setFormCategory("Số học");
    setFormDesc("");
    setFormLevel1("");
    setFormLevel2("");
    setFormLevel3("");
    setFormProblemCount(30);
    setIsAddModalOpen(true);
  };

  // Mở modal sửa chủ đề
  const handleOpenEditModal = (t: AdminTopic) => {
    setEditingTopic(t);
    setFormTitle(t.title);
    setFormGrade(t.grade);
    setFormCurriculum(t.curriculum);
    setFormCategory(t.category);
    setFormDesc(t.description);
    setFormLevel1(t.socratic_prompts?.level1 || "");
    setFormLevel2(t.socratic_prompts?.level2 || "");
    setFormLevel3(t.socratic_prompts?.level3 || "");
    setFormProblemCount(t.problem_count);
    setIsAddModalOpen(true);
  };

  // Lưu chủ đề (Thêm mới hoặc Cập nhật)
  const handleSaveTopic = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) {
      showToast("Vui lòng nhập tên chủ đề bài toán!");
      return;
    }

    if (editingTopic) {
      // Cập nhật
      setTopics((prev) =>
        prev.map((t) =>
          t.id === editingTopic.id
            ? {
                ...t,
                title: formTitle.trim(),
                grade: formGrade,
                curriculum: formCurriculum,
                category: formCategory,
                description: formDesc.trim() || t.description,
                problem_count: formProblemCount,
                socratic_prompts: {
                  level1: formLevel1.trim() || t.socratic_prompts.level1,
                  level2: formLevel2.trim() || t.socratic_prompts.level2,
                  level3: formLevel3.trim() || t.socratic_prompts.level3,
                },
              }
            : t
        )
      );
      showToast(`Đã cập nhật chủ đề "${formTitle}" thành công!`);
    } else {
      // Thêm mới
      const newTopic: AdminTopic = {
        id: `top_g${formGrade}_${Date.now().toString().slice(-4)}`,
        grade: formGrade,
        title: formTitle.trim(),
        slug: formTitle
          .toLowerCase()
          .normalize("NFD")
          .replace(/[\u0300-\u036f]/g, "")
          .replace(/[^a-z0-9]+/g, "-")
          .replace(/(^-|-$)+/g, ""),
        description:
          formDesc.trim() ||
          "Chủ đề học liệu mới được chuẩn hóa theo phương pháp khơi mở tư duy Socratic.",
        curriculum: formCurriculum,
        category: formCategory,
        problem_count: formProblemCount,
        active_sessions_count: 0,
        is_enabled: true,
        comprehension_rate: 90.0,
        socratic_prompts: {
          level1: formLevel1.trim() || "Đề bài đã cho chúng ta biết dữ kiện gì quan trọng em nhỉ?",
          level2: formLevel2.trim() || "Em hãy nhớ lại công thức hoặc phương pháp đã học về dạng toán này?",
          level3: formLevel3.trim() || "Hãy thử tính toán bước cuối cùng và đối chiếu lại đáp số nhé!",
        },
      };

      setTopics((prev) => [newTopic, ...prev]);
      showToast(`Đã xuất bản chủ đề "${formTitle}" cho khối Lớp ${formGrade}!`);
      // Chuyển sang tab khối lớp của chủ đề mới
      setSelectedGrade(formGrade);
    }

    setIsAddModalOpen(false);
  };

  // Xóa chủ đề
  const handleConfirmDelete = () => {
    if (!deleteTargetTopic) return;
    setTopics((prev) => prev.filter((t) => t.id !== deleteTargetTopic.id));
    showToast(`Đã xóa chủ đề "${deleteTargetTopic.title}" thành công!`);
    setDeleteTargetTopic(null);
  };

  return (
    <div className="max-w-6xl mx-auto animate-in fade-in duration-500 space-y-6 pb-12 text-[#2A1C0E]">
      {/* ── 1. Page Header (Đồng bộ chuẩn Parent Dashboard) ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-[#C1762A] rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-md">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl md:text-3xl font-extrabold text-[#8C4905] tracking-tight leading-none">
                Quản Lý Học Liệu Toán 4 - 9
              </h1>
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-[#EEF6FC] text-[#2B78C5] border border-[#BADEF7]">
                Task T7.27
              </span>
            </div>
            <p className="text-sm text-[#C1762A] mt-1 font-medium">
              Kho bài học chuẩn hóa theo phương pháp gợi mở Socratic, phân nhóm theo khối lớp và chương trình SGK mới
            </p>
          </div>
        </div>

        <button
          onClick={handleOpenAddModal}
          className="px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 bg-gradient-to-r from-[#C1762A] to-[#8C4905] hover:brightness-105 active:scale-95 text-white shadow-md transition-all duration-200 self-start md:self-auto cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Thêm Chủ Đề Mới</span>
        </button>
      </div>

      {/* ── 2. Grade Navigation Tabs ── */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-[#F1CCA6] scrollbar-none">
        {[4, 5, 6, 7, 8, 9].map((g) => {
          const isActive = selectedGrade === g;
          const count = topics.filter((t) => t.grade === g).length;

          return (
            <button
              key={g}
              onClick={() => setSelectedGrade(g)}
              className={`px-4 py-2.5 rounded-xl font-bold text-xs md:text-sm flex items-center gap-2 whitespace-nowrap transition-all duration-200 cursor-pointer ${
                isActive
                  ? "bg-[#C1762A] text-white shadow-md"
                  : "bg-white text-[#8C4905] hover:bg-[#F7ECE1] border border-[#F1CCA6]"
              }`}
            >
              <span>Lớp {g}</span>
              <span
                className={`text-[11px] px-1.5 py-0.2 rounded-full font-bold ${
                  isActive ? "bg-white/20 text-white" : "bg-[#F7ECE1] text-[#8C4905]"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── 3. Grade Stats Overview Banner ── */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] p-5 md:p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex flex-wrap items-center gap-6 md:gap-8">
          <div>
            <div className="text-xl md:text-2xl font-black text-[#C1762A]">
              {gradeStats.totalTopics}
            </div>
            <div className="text-xs text-[#7E6B5A]">Chủ đề Toán {selectedGrade}</div>
          </div>

          <div className="h-8 w-[1px] bg-[#F1CCA6] hidden sm:block" />

          <div>
            <div className="text-xl md:text-2xl font-black text-[#8C4905]">
              {gradeStats.totalProblems}
            </div>
            <div className="text-xs text-[#7E6B5A]">Bài toán mẫu có sẵn</div>
          </div>

          <div className="h-8 w-[1px] bg-[#F1CCA6] hidden sm:block" />

          <div>
            <div className="text-xl md:text-2xl font-black text-[#2A8C4A]">
              {gradeStats.avgRate}%
            </div>
            <div className="text-xs text-[#7E6B5A]">Độ hiểu bài Socratic</div>
          </div>
        </div>

        <div className="text-xs text-[#8C4905] bg-[#FDF6EE] px-3.5 py-2.5 rounded-xl border border-[#F1CCA6] flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-[#C1762A] shrink-0" />
          <span>
            Bao phủ: <strong>Kết nối tri thức</strong> & <strong>Cánh Diều</strong> & <strong>Chân trời sáng tạo</strong>
          </span>
        </div>
      </div>

      {/* ── 4. Search & Filter Bar ── */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] p-4 md:p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-[#7E6B5A] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Tìm bài học Toán lớp ${selectedGrade}...`}
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

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={curriculumFilter}
              onChange={(e) => setCurriculumFilter(e.target.value)}
              className="bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
            >
              <option value="ALL">Tất cả bộ sách</option>
              <option value="Cánh Diều">Bộ Cánh Diều</option>
              <option value="Kết nối tri thức">Kết nối tri thức (KNTT)</option>
              <option value="Chân trời sáng tạo">Chân trời sáng tạo</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
            >
              <option value="ALL">Tất cả dạng toán</option>
              <option value="Số học">Số học</option>
              <option value="Hình học">Hình học</option>
              <option value="Đại số">Đại số</option>
              <option value="Chuyển động">Chuyển động đều</option>
              <option value="Toán có lời văn">Toán có lời văn</option>
              <option value="Ứng dụng">Ứng dụng thực tế</option>
            </select>

            {(searchQuery || curriculumFilter !== "ALL" || categoryFilter !== "ALL") && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setCurriculumFilter("ALL");
                  setCategoryFilter("ALL");
                }}
                className="px-3 py-2 rounded-xl text-xs font-bold text-[#8C4905] bg-[#F7ECE1] hover:bg-[#F1CCA6] transition-colors"
              >
                Đặt lại
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── 5. Main Topic Table ── */}
      <div className="bg-white rounded-2xl border border-[#F1CCA6] shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs md:text-sm">
            <thead>
              <tr className="bg-[#FBF4ED] border-b border-[#F1CCA6] text-[#8C4905] font-bold text-xs uppercase tracking-wider">
                <th className="py-3.5 px-4">Mã & Tên Chủ Đề</th>
                <th className="py-3.5 px-4">Bài Toán Mẫu</th>
                <th className="py-3.5 px-4">Phương Pháp Socratic</th>
                <th className="py-3.5 px-4">Tỷ Lệ Hiểu</th>
                <th className="py-3.5 px-4 text-center">Trạng Thái</th>
                <th className="py-3.5 px-4 text-right">Thao Tác</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#F1CCA6]/40">
              {filteredTopics.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-[#7E6B5A]">
                    <div className="w-12 h-12 rounded-2xl bg-[#F7ECE1] text-[#C1762A] flex items-center justify-center mx-auto mb-3">
                      <BookOpen className="w-6 h-6" />
                    </div>
                    <p className="font-bold text-[#2A1C0E]">Chưa có chủ đề nào phù hợp bộ lọc</p>
                    <p className="text-xs text-[#7E6B5A] mt-1">
                      Hãy bấm &quot;Thêm Chủ Đề Mới&quot; để bổ sung bài học cho Toán lớp {selectedGrade}
                    </p>
                  </td>
                </tr>
              ) : (
                filteredTopics.map((topic) => (
                  <tr
                    key={topic.id}
                    className="hover:bg-[#FFFDFB] transition-colors group"
                  >
                    {/* Name & Desc */}
                    <td className="py-3.5 px-4 max-w-xs md:max-w-sm">
                      <div className="font-bold text-[#2A1C0E] group-hover:text-[#C1762A] transition-colors">
                        {topic.title}
                      </div>
                      <div className="text-xs text-[#7E6B5A] line-clamp-1 mt-0.5">
                        {topic.description}
                      </div>
                    </td>

                    {/* Problem count */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="font-bold text-xs text-[#2A1C0E]">
                        {topic.problem_count} bài tập
                      </div>
                      <div className="text-[11px] text-[#7E6B5A] flex items-center gap-1 mt-0.5">
                        <ImageIcon className="w-3 h-3 text-[#C1762A]" />
                        <span>Kèm ảnh Cloudinary</span>
                      </div>
                    </td>

                    {/* Socratic Prompts Method */}
                    <td className="py-3.5 px-4">
                      {topic.comprehension_rate >= 85 ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#EAF7EE] text-[#2A8C4A] border border-[#B7E4C4]">
                          <CheckCircle2 className="w-3 h-3" />
                          3 cấp độ gợi ý chuẩn
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FDF3E7] text-[#C1762A] border border-[#F1CCA6]">
                          <AlertTriangle className="w-3 h-3" />
                          Cần tinh chỉnh bước 2
                        </span>
                      )}
                    </td>

                    {/* Comprehension rate */}
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span
                          className={`font-extrabold text-xs ${
                            topic.comprehension_rate >= 85
                              ? "text-[#2A8C4A]"
                              : topic.comprehension_rate >= 75
                              ? "text-[#C1762A]"
                              : "text-[#D93829]"
                          }`}
                        >
                          {topic.comprehension_rate}%
                        </span>
                        <div className="w-12 h-1.5 bg-[#E8D5C4] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              topic.comprehension_rate >= 85
                                ? "bg-[#2A8C4A]"
                                : topic.comprehension_rate >= 75
                                ? "bg-[#C1762A]"
                                : "bg-[#D93829]"
                            }`}
                            style={{ width: `${topic.comprehension_rate}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Toggle Switch */}
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={() => handleToggleTopic(topic.id, topic.is_enabled)}
                        className={`w-9 h-5 rounded-full transition-colors relative cursor-pointer ${
                          topic.is_enabled ? "bg-[#2A8C4A]" : "bg-[#D9BEA7]"
                        }`}
                        title={topic.is_enabled ? "Đang bật" : "Đang tắt"}
                      >
                        <div
                          className={`w-3.5 h-3.5 rounded-full bg-white transition-transform absolute top-[3px] shadow-xs ${
                            topic.is_enabled ? "left-[19px]" : "left-[3px]"
                          }`}
                        />
                      </button>
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setPreviewTopic(topic)}
                          className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-[#F7ECE1] hover:bg-[#F1CCA6] text-[#8C4905] transition-colors flex items-center gap-1"
                          title="Xem 3 bước câu hỏi Socratic"
                        >
                          <Lightbulb className="w-3 h-3 text-[#C1762A]" />
                          <span>Xem Gợi Ý</span>
                        </button>

                        <button
                          onClick={() => handleOpenEditModal(topic)}
                          className="p-1.5 rounded-lg text-xs text-[#7E6B5A] hover:text-[#C1762A] hover:bg-[#F7ECE1] transition-colors"
                          title="Chỉnh sửa chủ đề"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => setDeleteTargetTopic(topic)}
                          className="p-1.5 rounded-lg text-xs text-[#7E6B5A] hover:text-[#D93829] hover:bg-[#FDF0ED] transition-colors"
                          title="Xóa chủ đề"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 6. Modal: Xem Kịch Bản Gợi Mở Socratic (SocraticPreviewModal) ── */}
      {previewTopic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setPreviewTopic(null)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
          />

          <div className="relative bg-white rounded-2xl border border-[#E8D5C4] shadow-2xl max-w-xl w-full overflow-hidden animate-modal-in z-10">
            {/* Header */}
            <div className="bg-[#F7ECE1] border-b border-[#E8D5C4] px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-[#C1762A]" />
                <h3 className="font-extrabold text-base text-[#8C4905]">
                  Kịch Bản Gợi Mở Socratic (3 Cấp Độ)
                </h3>
              </div>
              <button
                onClick={() => setPreviewTopic(null)}
                className="w-7 h-7 rounded-lg text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-black/5 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Body */}
            <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto text-xs md:text-sm">
              <div className="p-3.5 rounded-xl bg-[#FFFDFB] border border-[#F1CCA6]">
                <div className="font-extrabold text-[#2A1C0E] text-base">{previewTopic.title}</div>
                <div className="text-xs text-[#7E6B5A] mt-1">{previewTopic.description}</div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-[#FFF3E6] text-[#C1762A] border border-[#F1CCA6]">
                    {previewTopic.curriculum}
                  </span>
                  <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#F7ECE1] text-[#8C4905]">
                    Khối Lớp {previewTopic.grade}
                  </span>
                </div>
              </div>

              {/* 3 Steps */}
              <div className="space-y-3">
                {/* Level 1 */}
                <div className="p-3.5 rounded-xl bg-[#FBF4ED] border border-[#E8D5C4]">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="w-5 h-5 rounded-full bg-[#C1762A] text-white flex items-center justify-center font-bold text-xs">
                      1
                    </span>
                    <span className="font-bold text-xs text-[#8C4905]">
                      Cấp độ 1: Gợi Mở Nhận Thức Đề Bài (Khi mới đọc đề)
                    </span>
                  </div>
                  <p className="text-xs text-[#2A1C0E] italic pl-7 leading-relaxed">
                    &quot;{previewTopic.socratic_prompts?.level1}&quot;
                  </p>
                </div>

                {/* Level 2 */}
                <div className="p-3.5 rounded-xl bg-[#FBF4ED] border border-[#E8D5C4]">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="w-5 h-5 rounded-full bg-[#8C4905] text-white flex items-center justify-center font-bold text-xs">
                      2
                    </span>
                    <span className="font-bold text-xs text-[#8C4905]">
                      Cấp độ 2: Định Hướng Công Thức & Mô Hình Hóa (Khi bấm Chưa hiểu lần 1)
                    </span>
                  </div>
                  <p className="text-xs text-[#2A1C0E] italic pl-7 leading-relaxed">
                    &quot;{previewTopic.socratic_prompts?.level2}&quot;
                  </p>
                </div>

                {/* Level 3 */}
                <div className="p-3.5 rounded-xl bg-[#FBF4ED] border border-[#E8D5C4]">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="w-5 h-5 rounded-full bg-[#2A8C4A] text-white flex items-center justify-center font-bold text-xs">
                      3
                    </span>
                    <span className="font-bold text-xs text-[#2A8C4A]">
                      Cấp độ 3: Khơi Mở Phép Tính Then Chốt (Khích lệ tự hoàn thành)
                    </span>
                  </div>
                  <p className="text-xs text-[#2A1C0E] italic pl-7 leading-relaxed">
                    &quot;{previewTopic.socratic_prompts?.level3}&quot;
                  </p>
                </div>
              </div>

              {/* Pedagogy Note */}
              <div className="p-3 rounded-xl bg-[#EAF7EE] border border-[#B7E4C4] text-xs text-[#2A8C4A]">
                <strong>Nguyên tắc SocraticKid:</strong> AI tuyệt đối không giải hộ đáp số cuối cùng
                trong cả 3 cấp độ gợi ý, giúp học sinh duy trì điểm tự lập trên 80 điểm.
              </div>
            </div>

            {/* Footer */}
            <div className="bg-[#FBF4ED] border-t border-[#E8D5C4] px-5 py-3 flex items-center justify-between">
              <span className="text-xs text-[#7E6B5A]">
                Tỷ lệ học sinh tự hiểu dạng này: <strong>{previewTopic.comprehension_rate}%</strong>
              </span>
              <button
                onClick={() => setPreviewTopic(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-[#C1762A] text-white hover:bg-[#8C4905] transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 7. Modal: Thêm / Chỉnh Sửa Chủ Đề (AddEditTopicModal) ── */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setIsAddModalOpen(false)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
          />

          <div className="relative bg-white rounded-2xl border border-[#E8D5C4] shadow-2xl max-w-lg w-full overflow-hidden animate-modal-in z-10">
            {/* Header */}
            <div className="bg-[#F7ECE1] border-b border-[#E8D5C4] px-5 py-4 flex items-center justify-between">
              <h3 className="font-extrabold text-base text-[#8C4905]">
                {editingTopic ? "Chỉnh Sửa Chủ Đề Học Liệu" : "+ Thêm Chủ Đề Học Liệu Mới"}
              </h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="w-7 h-7 rounded-lg text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-black/5 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSaveTopic} className="p-5 space-y-3.5 text-xs md:text-sm max-h-[78vh] overflow-y-auto">
              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1">
                  Tên chủ đề bài toán <span className="text-[#D93829]">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="VD: TOAN5-CD-14: Diện Tích Hình Thoi"
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs md:text-sm text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#2A1C0E] mb-1">
                    Khối lớp <span className="text-[#D93829]">*</span>
                  </label>
                  <select
                    value={formGrade}
                    onChange={(e) => setFormGrade(Number(e.target.value))}
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                  >
                    <option value={4}>Lớp 4 (Tiểu học)</option>
                    <option value={5}>Lớp 5 (Tiểu học)</option>
                    <option value={6}>Lớp 6 (THCS)</option>
                    <option value={7}>Lớp 7 (THCS)</option>
                    <option value={8}>Lớp 8 (THCS)</option>
                    <option value={9}>Lớp 9 (THCS)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2A1C0E] mb-1">Bộ sách</label>
                  <select
                    value={formCurriculum}
                    onChange={(e) =>
                      setFormCurriculum(e.target.value as "Cánh Diều" | "Kết nối tri thức" | "Chân trời sáng tạo")
                    }
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                  >
                    <option value="Cánh Diều">Cánh Diều</option>
                    <option value="Kết nối tri thức">Kết nối tri thức (KNTT)</option>
                    <option value="Chân trời sáng tạo">Chân trời sáng tạo</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#2A1C0E] mb-1">Dạng bài</label>
                  <select
                    value={formCategory}
                    onChange={(e) =>
                      setFormCategory(
                        e.target.value as "Số học" | "Hình học" | "Đại số" | "Chuyển động" | "Ứng dụng" | "Toán có lời văn"
                      )
                    }
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs font-semibold text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] cursor-pointer"
                  >
                    <option value="Số học">Số học</option>
                    <option value="Hình học">Hình học</option>
                    <option value="Đại số">Đại số</option>
                    <option value="Chuyển động">Chuyển động đều</option>
                    <option value="Toán có lời văn">Toán có lời văn</option>
                    <option value="Ứng dụng">Ứng dụng thực tế</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#2A1C0E] mb-1">Số bài toán mẫu</label>
                  <input
                    type="number"
                    min={1}
                    value={formProblemCount}
                    onChange={(e) => setFormProblemCount(Number(e.target.value))}
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-2 text-xs md:text-sm text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#2A1C0E] mb-1">Mô tả sư phạm</label>
                <textarea
                  rows={2}
                  value={formDesc}
                  onChange={(e) => setFormDesc(e.target.value)}
                  placeholder="Mô tả nội dung bài học, dạng toán và lưu ý sư phạm..."
                  className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl p-2.5 text-xs text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white resize-none"
                />
              </div>

              {/* Socratic Prompt Inputs */}
              <div className="space-y-2.5 pt-1">
                <div className="font-bold text-xs text-[#8C4905]">
                  Thiết lập câu hỏi gợi ý Socratic mẫu:
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#7E6B5A] mb-1">
                    Cấp độ 1: Gợi mở dữ kiện đề bài
                  </label>
                  <input
                    type="text"
                    value={formLevel1}
                    onChange={(e) => setFormLevel1(e.target.value)}
                    placeholder="VD: Đề bài đã cho chúng ta biết tổng của hai số là bao nhiêu rồi em nhỉ?"
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-1.5 text-xs text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#7E6B5A] mb-1">
                    Cấp độ 2: Định hướng công thức / phương pháp
                  </label>
                  <input
                    type="text"
                    value={formLevel2}
                    onChange={(e) => setFormLevel2(e.target.value)}
                    placeholder="VD: Để tính diện tích hình thoi khi biết độ dài hai đường chéo, công thức là gì em nhỉ?"
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-1.5 text-xs text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-[#7E6B5A] mb-1">
                    Cấp độ 3: Khơi thông phép tính cuối cùng
                  </label>
                  <input
                    type="text"
                    value={formLevel3}
                    onChange={(e) => setFormLevel3(e.target.value)}
                    placeholder="VD: Rất tốt! Em hãy lấy (d1 × d2) chia cho 2 và ghi đáp số kèm đơn vị nhé."
                    className="w-full bg-[#FBF4ED] border border-[#E8D5C4] rounded-xl px-3 py-1.5 text-xs text-[#2A1C0E] focus:outline-hidden focus:border-[#C1762A] focus:bg-white"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="pt-3 border-t border-[#E8D5C4] flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-[#E8D5C4] text-[#2A1C0E] hover:bg-[#F7ECE1] transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-[#C1762A] hover:bg-[#8C4905] text-white shadow-xs transition-colors"
                >
                  {editingTopic ? "Lưu Thay Đổi" : "Xuất Bản Bài Học"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── 8. Modal: Xác Nhận Xóa Chủ Đề (DeleteTopicModal) ── */}
      {deleteTargetTopic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            onClick={() => setDeleteTargetTopic(null)}
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity animate-fade-in"
          />

          <div className="relative bg-white rounded-2xl border border-[#F5BCB4] shadow-2xl max-w-sm w-full overflow-hidden animate-modal-in z-10">
            <div className="bg-[#FDF0ED] border-b border-[#F5BCB4] px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 text-[#D93829]">
                <Trash2 className="w-5 h-5" />
                <h3 className="font-extrabold text-base">Xác Nhận Xóa Chủ Đề</h3>
              </div>
              <button
                onClick={() => setDeleteTargetTopic(null)}
                className="w-7 h-7 rounded-lg text-[#7E6B5A] hover:text-[#2A1C0E] hover:bg-black/5 flex items-center justify-center transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 text-xs md:text-sm text-[#2A1C0E] space-y-2">
              <p>
                Bạn có chắc chắn muốn xóa chủ đề:{" "}
                <strong className="text-[#D93829]">{deleteTargetTopic.title}</strong>?
              </p>
              <p className="text-xs text-[#7E6B5A]">
                Toàn bộ {deleteTargetTopic.problem_count} bài tập mẫu và kịch bản Socratic của chủ đề này sẽ bị gỡ bỏ khỏi AI.
              </p>
            </div>

            <div className="bg-[#FDF0ED]/50 border-t border-[#F5BCB4] px-5 py-3 flex items-center justify-end gap-2.5">
              <button
                onClick={() => setDeleteTargetTopic(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-[#E8D5C4] text-[#2A1C0E] hover:bg-[#F7ECE1] transition-colors"
              >
                Hủy
              </button>
              <button
                onClick={handleConfirmDelete}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-[#D93829] hover:bg-[#B92314] text-white shadow-xs transition-colors"
              >
                Xác Nhận Xóa
              </button>
            </div>
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
