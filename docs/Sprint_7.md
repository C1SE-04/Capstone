## Sprint 7: Nâng Cấp Phụ Huynh, Game Hóa Học Sinh & Toàn Diện Frontend Admin Portal (17-Oct đến 23-Oct)
*(Phân bổ khối lượng: [Bảo]: 20.5h, [Thông]: 20h, [Thiên]: 21h, [Thống]: 20h)*

**Quy định phân chia vai trò Frontend tránh chồng chéo:**
- **US 7.1 (Phụ huynh)**: Chỉ **[Thiên]** làm Frontend (`AIInsightsCard.tsx`, `SummaryCards.tsx`, `ChildProblemHistory.tsx`). [Bảo] chỉ đóng vai trò kiểm thử UX sư phạm.
- **US 7.2 (Học sinh)**: Chỉ **[Bảo]** làm Frontend (`StreakBadge.tsx`, `BadgeModal.tsx`, `NotebookPage.tsx`, `BookmarkChatDrawer.tsx`). [Thiên] phụ trách Database index và QA.
- **US 7.3 (Admin Portal)**: 
  - **[Bảo]** thiết kế toàn bộ hệ thống UI/UX Trang Admin trên Figma/Wireframe.
  - **Code Frontend chia theo trang cụ thể**: 
    - [Thiên] code: Layout tổng thể (`admin/layout.tsx`, `AdminSidebar.tsx`), Dashboard KPI (`admin/page.tsx`), Giám sát an toàn (`admin/safety/page.tsx`), Cài đặt (`admin/settings/page.tsx`).
    - [Bảo] code: Quản lý người dùng (`admin/users/page.tsx`), Quản lý học liệu (`admin/content/page.tsx`), Rà soát 100% kết nối nút bấm (`click-through router`).

---

### US 7.1: Nâng Cấp Toàn Diện Dashboard Phụ Huynh (AI Learning Insights, Sổ Theo Dõi Bài Tập & Nối Data Thật)
*Mô tả: Là một Phụ huynh, tôi muốn nhận được nhận xét sư phạm tự động từ AI, xem chi tiết lịch sử từng bài toán con đã giải và theo dõi số liệu học tập hoàn toàn chính xác (không dùng dữ liệu giả lập), để tôi nắm bắt kịp thời năng lực và điểm yếu của con mà không cần đọc từng dòng chat.*
- **Mô tả chi tiết:**
  - **Nhận xét sư phạm tự động từ AI (AI Learning Insights)**:
    - Cuối ngày hoặc cuối tuần, hệ thống tổng hợp toàn bộ các bài toán con đã hoàn thành, điểm tự lập và số lần bấm "Chưa hiểu".
    - Gemini phân tích và xuất ra 1 đoạn nhận xét cô đọng: Điểm mạnh, dạng bài còn lúng túng, số gợi ý trung bình, và lời khuyên sư phạm thiết thực cho cha mẹ.
  - **Sổ theo dõi bài tập của con (Child Problem & Session History)**:
    - Hiển thị danh sách các bài toán con đã giải theo ngày/tuần dạng timeline hoặc danh sách thẻ trực quan.
    - Mỗi bài hiển thị: Tên dạng toán (Hình học, Phân số, Tìm X...), ảnh đề bài con đã chụp (thumbnail Cloudinary có thể click phóng to), điểm tự lập đạt được (0-100), số lần bấm "Chưa hiểu".
    - Cho phép phụ huynh bấm vào để xem lại đoạn hội thoại đối thoại ngắn giữa AI và con để hiểu cách con tư duy.
  - **Xóa bỏ dữ liệu Mock – Nối 100% dữ liệu thật từ Database**:
    - **Heatmap thật**: API `/metrics/heatmap` quét bảng `session_active_intervals` theo từng ngày trong năm để tô màu chuyên cần chuẩn GitHub cho phụ huynh.
    - **Summary Cards thật**: Tính tổng số bài hoàn thành dựa trên số bản ghi trong bảng `independence_scores`, tính chuỗi ngày học thật (Streak) thay thế toàn bộ mock cứng.
- **Tasks:**
  - **T7.1** [Thông] [AI] Nghiên cứu & Thiết kế Prompt Gemini sinh Báo cáo Nhận xét Sư phạm (AI Learning Insights) cho phụ huynh dựa trên tổng số bài, dạng toán và điểm tự lực. (3h)
  - **T7.2** [Thông] [AI] Chuẩn hóa Pydantic Schema cho AI Insights (`AiInsightReportResponse`: strengths, weak_points, recommendations, summary). (1.5h)
  - **T7.3** [Thống] [BE] Viết hàm background service quét dữ liệu tuần của học sinh, gọi Gemini sinh AI Insights và lưu vào bảng `parent_ai_insights`. (2.5h)
  - **T7.4** [Thống] [BE] Code API `/metrics/heatmap` quét bảng `session_active_intervals` tính tổng thời gian active từng ngày trong 16-24 tuần. (2.5h)
  - **T7.5** [Thống] [BE] Code API `/metrics/summary` tính toán số liệu thật cho Summary Cards (tổng bài hoàn thành từ `independence_scores`, chuỗi ngày học Streak liên tiếp). (2h)
  - **T7.6** [Thống] [BE] Code API `/parent/child-problems` trả về danh sách bài tập con đã giải kèm ảnh đề bài Cloudinary, điểm tự lực và đoạn chat tóm tắt. (2.5h)
  - **T7.7** [Thiên] [FE] Code component `<AIInsightsCard />` (khối nhận xét AI thông minh có icon trực quan, huy hiệu đánh giá và lời khuyên sư phạm). (2.5h)
  - **T7.8** [Thiên] [FE] Nối API thật xóa bỏ mock trong `SummaryCards.tsx` và cấu hình lại `ActivityHeatmap.tsx` nhận dữ liệu thật từ `/metrics/heatmap`. (2.5h)
  - **T7.9** [Thiên] [FE] Code component `<ChildProblemHistory />` (320 dòng): danh sách timeline bài tập con đã giải, tích hợp modal phóng to ảnh Cloudinary và popup xem đoạn đối thoại tư duy của con. (3h)
  - **T7.10** [Bảo] [UX/QA] Đóng vai phụ huynh khó tính: Lên kịch bản kiểm thử trải nghiệm xem báo cáo, kiểm tra tính dễ hiểu của các thuật ngữ sư phạm trên điện thoại. (1.5h)
  - **T7.11** [Thiên] [QA] Viết kịch bản test E2E: Học sinh giải 3 bài thật -> Phụ huynh F5 thấy ngay điểm tự lập cập nhật, heatmap đổi màu, AI insight phân tích đúng dạng bài. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] AI Learning Insights:** Phụ huynh vào trang Monitor thấy khối nhận xét AI nêu rõ điểm mạnh, điểm yếu và lời khuyên dành cho con dựa trên dữ liệu thật.
  - **[AC2] Lịch sử bài tập chi tiết:** Danh sách bài tập của con hiển thị đầy đủ tên bài, điểm tự lực, ảnh đề bài chụp và bấm vào đọc được đoạn hội thoại giải bài của con.
  - **[AC3] 100% Data thật:** Summary Cards và Heatmap lấy dữ liệu thực tế từ DB, không còn số liệu mock `completedProblems: 18` hay `generateMockHeatmapData`.
  - **[AC4] UX thân thiện:** Thuật ngữ nhận xét sư phạm gần gũi, giao diện responsive mượt mà trên cả máy tính lẫn smartphone.

---

### US 7.2: Cơ Chế Game Hóa & Sổ Tay Bài Toán Yêu Thích Cho Học Sinh (Streak 🔥, Huy Hiệu & Bookmark Notebook)
*Mô tả: Là một Học sinh, tôi muốn theo dõi chuỗi ngày học liên tục (Streak), mở khóa các huy hiệu tự lập và có Sổ tay lưu lại các bài toán yêu thích, để tôi có động lực học tập mỗi ngày và dễ dàng ôn tập lại trước kỳ thi.*
- **Mô tả chi tiết:**
  - **Cơ chế Game hóa (Streak 🔥 & Huy hiệu Tự Lập)**:
    - Hiển thị biểu tượng ngọn lửa hoạt hình Streak 🔥 kèm số ngày học liên tục ở góc trên khung chat.
    - Hệ thống huy hiệu khích lệ:
      * 🏅 *Tự lập nhí*: Hoàn thành bài toán với 100 điểm tự lực (0 gợi ý).
      * 🔥 *Kiên trì*: Học liên tục 3 ngày không gián đoạn.
      * 📸 *Thám tử hình ảnh*: Tải lên và giải bài toán đầu tiên bằng ảnh.
    - Modal chúc mừng khi học sinh mở khóa được huy hiệu mới với hiệu ứng pháo hoa vui nhộn.
  - **Sổ tay bài toán yêu thích (Bookmark Notebook)**:
    - Sau khi hoàn thành bài toán và bấm "Đã hiểu", xuất hiện nút **⭐ "Lưu vào Sổ tay"**.
    - Tab **"📖 Sổ tay"** hiển thị danh sách các bài đã lưu dưới dạng Thẻ Flashcard (Đề bài, Ảnh chụp, Bí kíp cần nhớ do AI đúc kết, Đáp số cuối cùng).
    - Nút **`[💬 Xem lại đoạn chat]`**: Mở ngăn kéo (Drawer) hiển thị ĐÚNG đoạn chat từ câu học sinh hỏi đề bài đến lúc bấm "Đã hiểu".
    - **Lọc thông minh qua Gemini (Boundary Extraction)**: Nếu bài trước đó bị bỏ dở hoặc học sinh đổi bài giữa chừng, Gemini tự động nhận diện và chỉ trích xuất đúng các tin nhắn của bài toán vừa hoàn thành, loại bỏ hoàn toàn các câu chat của bài cũ bỏ dở.
- **Tasks:**
  - **T7.12** [Thống] [BE] Thiết kế Model `Bookmark` trong `models.py` (lưu snapshot tin nhắn, ảnh đề bài, bí kíp, đáp số, `independence_score_id`) và tạo DB migration. (2.5h)
  - **T7.13** [Thống] [BE] Code API CRUD `/bookmarks`: Tạo bookmark, lấy danh sách theo học sinh/chủ đề, xóa bookmark, lấy chi tiết bookmark. (3h)
  - **T7.14** [Thống] [BE] Code logic tính Streak 🔥 liên tục theo ngày và bảng `student_badges` ghi nhận mở khóa huy hiệu (Tự lập nhí 100đ, Kiên trì 3 ngày, Thám tử hình ảnh). (2.5h)
  - **T7.15** [Thông] [AI] Xây dựng logic Gemini tự nhận diện ranh giới bài toán (Boundary Extraction): Lọc đúng tin nhắn từ đề bài đến câu chúc mừng, tự loại bỏ bài cũ bỏ dở nếu học sinh đổi đề giữa chừng. (3h)
  - **T7.16** [Thông] [AI] Viết Prompt Gemini tự động trích xuất Đề bài, Bí kíp cốt lõi (1-2 công thức) và Đáp số chốt để tạo dữ liệu Thẻ Flashcard. (2.5h)
  - **T7.17** [Bảo] [FE] Nâng cấp khung Chat: Thêm nút ⭐ "Lưu vào Sổ tay" xuất hiện ngay dưới bong bóng chúc mừng của AI sau khi học sinh bấm "Đã hiểu". (2h)
  - **T7.18** [Bảo] [FE] Code UI biểu tượng ngọn lửa hoạt hình Streak 🔥 ở header chat và Modal chúc mừng mở khóa Huy hiệu (`BadgeModal.tsx`) với hiệu ứng pháo hoa. (2h)
  - **T7.19** [Bảo] [FE] Code Trang Sổ tay (`/dashboard/notebook/page.tsx` - 310 dòng): Giao diện lưới thẻ Flashcard hiện đại, bộ lọc theo môn/dạng toán, nút xem ảnh bài tập phóng to. (3h)
  - **T7.20** [Bảo] [FE] Code Drawer ngăn kéo xem lại đoạn chat (`BookmarkChatDrawer.tsx`): Tái sử dụng `ChatMessage.tsx` hiển thị đúng mảng tin nhắn của riêng bài đó. (2.5h)
  - **T7.21** [Thiên] [Database] Tối ưu hóa Index cho bảng `bookmarks` (`student_id`, `created_at`) và chạy script migration an toàn trên Neon DB. (1.5h)
  - **T7.22** [Thông] [QA] Đóng vai học sinh: Test kịch bản 20 tình huống lưu bài (giải xong bài 1 lưu bài 1; giải dở bài 1 nhảy sang bài 2 bấm lưu bài 2 xem có bị lẫn tin nhắn không). (2.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Streak & Badges:** Học sinh học ngày thứ 2 liên tiếp thì Streak tăng lên 2 🔥; khi giải bài đạt 100đ thì nhận thông báo mở khóa huy hiệu "Tự lập nhí".
  - **[AC2] Lưu Sổ tay chính xác:** Bấm "⭐ Lưu bài" thì bài toán xuất hiện trong tab Sổ tay với đầy đủ đề bài, ảnh và bí kíp tóm tắt.
  - **[AC3] Xem lại đoạn chat không lẫn bài cũ:** Bấm xem lại đoạn chat trong Sổ tay chỉ hiển thị các câu của riêng bài đó, kể cả trước đó học sinh có bỏ dở một bài khác.
  - **[AC4] Hiệu năng:** Mở drawer xem lại đoạn chat mở tức thì dưới 0.2s nhờ dùng chat snapshot JSON độc lập.

---

### US 7.3: Thiết Kế & Xây Dựng Toàn Diện Giao Diện Quản Trị Hệ Thống (Admin Portal Frontend)
*Mô tả: Là một Quản trị viên, tôi muốn có một giao diện Admin hoàn chỉnh, đẹp mắt với đầy đủ các trang và điều hướng nút bấm mượt mà, để sẵn sàng quản lý người dùng, nội dung và giám sát hệ sinh thái SocraticKid.*
- **Mô tả chi tiết:**
  - **Yêu cầu kỹ thuật**:
    - Tập trung hoàn thiện 100% phần **Thiết kế & Code Frontend** cho toàn bộ cổng Admin (chưa cần ráp luồng xử lý database bên trong).
    - Tất cả các trang từ lớn đến nhỏ, từ chính đến phụ đều phải được dựng trang đầy đủ.
    - **Ấn vào bất kỳ button, menu item hay link nào đều phải chuyển trang đúng**, có trạng thái loading, modal mẫu hoặc thông báo trực quan.
  - **Hệ thống các màn hình Admin cần xây dựng**:
    1. **Layout Admin tổng thể** (`admin/layout.tsx`): Sidebar quản trị chuyên nghiệp, Header hiển thị thông tin Admin, Breadcrumbs điều hướng.
    2. **Dashboard Thống kê Tổng quan** (`admin/page.tsx`): Thẻ KPI (Tổng Users, Học sinh, Phụ huynh, Phiên chat), biểu đồ tăng trưởng người dùng (DAU/MAU) và biểu đồ lượng token AI tiêu thụ.
    3. **Quản lý Người dùng** (`admin/users/page.tsx`): Bảng dữ liệu người dùng (Học sinh, Phụ huynh), thanh tìm kiếm, bộ lọc vai trò, nút xem chi tiết tài khoản và nút Khóa/Mở khóa tài khoản.
    4. **Quản lý Chủ đề Học liệu** (`admin/content/page.tsx`): Danh sách chủ đề Toán lớp 4-9, nút "Thêm chủ đề mới" mở Modal, nút chỉnh sửa và xóa bài học mẫu.
    5. **Giám sát An toàn & Chất lượng AI** (`admin/safety/page.tsx`): Danh sách cảnh báo vi phạm ngôn từ, nhật ký các câu hỏi bị chặn bởi Safety Agent, thống kê tỷ lệ học sinh bấm "Chưa hiểu".
    6. **Cài đặt Hệ thống** (`admin/settings/page.tsx`): Giao diện cấu hình tham số AI (chọn Model, giới hạn token, nhiệt độ sáng tạo temperature) và thông tin phiên bản.
- **Tasks:**
  - **T7.23** [Bảo] [Design] Thiết kế toàn bộ Design System & Mockup Figma cho Admin Portal: Chuẩn hóa hệ màu nhận diện SocraticKid (Cam chủ đạo #C1762A, hover #8C4905, nền kem #F7ECE1, #F1CCA6), typography, bộ icon, các layout con. (3h)
  - **T7.24** [Thiên] [FE] Dựng khung Admin Layout tổng thể (`admin/layout.tsx`, `AdminSidebar.tsx`, `AdminHeader.tsx`, `Breadcrumbs.tsx`) với cơ chế chuyển tab mượt mà. (2.5h)
  - **T7.25** [Thiên] [FE] Code Trang Dashboard Thống kê Tổng quan (`admin/page.tsx` - 280 dòng): 4 thẻ KPI tổng, biểu đồ DAU/MAU và biểu đồ tiêu thụ Token AI (Recharts). (2.5h)
  - **T7.26** [Bảo] [FE] Code Trang Quản lý Người dùng (`admin/users/page.tsx` - 320 dòng): Data Table danh sách user, thanh search, bộ lọc role, badge trạng thái, modal chi tiết user và nút Khóa/Mở tài khoản. (3h)
  - **T7.27** [Bảo] [FE] Code Trang Quản lý Học liệu (`admin/content/page.tsx` - 240 dòng): Danh sách chủ đề Toán lớp 4-9, nút "Thêm chủ đề mới" mở Form Drawer, nút sửa/xóa bài học mẫu. (2h)
  - **T7.28** [Thiên] [FE] Code Trang Giám sát An toàn (`admin/safety/page.tsx` - 210 dòng): Bảng log các câu chat bị Safety chặn (toxic/jailbreak) và biểu đồ tỷ lệ học sinh bấm "Chưa hiểu". (2h)
  - **T7.29** [Thiên] [FE] Code Trang Cài đặt Hệ thống (`admin/settings/page.tsx` - 190 dòng): Giao diện chỉnh model AI (Gemini Flash/Pro), chỉnh temperature, max tokens, và thông tin version. (1.5h)
  - **T7.30** [Bảo] [FE] Rà soát và kết nối 100% nút bấm, link điều hướng, nút quay lại trên toàn bộ các trang Admin (Đảm bảo không còn bất kỳ nút chết/dead-click nào). (1.5h)
  - **T7.31** [Thống] [BE] Tạo router mock data `/admin/mock` cung cấp dữ liệu giả lập có cấu trúc chuẩn cho toàn bộ trang Admin để FE render siêu thực tế. (2.5h)
  - **T7.32** [Thông] [QA] Đóng vai Quản trị viên: Click-through kiểm thử 100% các nút bấm trên toàn bộ 6 trang Admin, kiểm tra lỗi console, giao diện responsive tablet/laptop. (3h)
  - **T7.33** [Thông] [Document] Viết tài liệu hướng dẫn vận hành tính năng mới cho Phụ huynh, Sổ tay và Hướng dẫn sử dụng Admin Portal. (2h)
  - **T7.34** [Thiên] [Management/QA] Review PR toàn bộ mã nguồn Frontend Admin, giải quyết conflict, dọn dẹp branch và chốt nghiệm thu Sprint 7. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Thiết kế đồng bộ & Chuyên nghiệp:** Toàn bộ hệ thống giao diện Admin có phong cách thiết kế hiện đại, đồng bộ theo bản thiết kế của Bảo.
  - **[AC2] Điều hướng 100% hoạt động (Click-through):** Mọi nút bấm, menu con, tab, icon trên toàn bộ giao diện Admin khi click đều chuyển trang hoặc kích hoạt modal tương ứng, không có nút chết (dead link).
  - **[AC3] Phân định rõ vai trò FE:** Bảo và Thiên phối hợp mượt mà ở các trang Admin được phân chia, không xung đột hay trùng lặp code.
  - **[AC4] Dữ liệu mẫu chuẩn cấu trúc:** Các trang Admin dùng mock data chuẩn cấu trúc Backend, sẵn sàng kết nối DB ở Sprint sau mà không phải sửa lại UI.

---

### 📌 Sơ Đồ Phụ Thuộc Task – Sprint 7

**US 7.1 (Dashboard Phụ Huynh)**
```
T7.1 (Thông: Prompt AI) ──► T7.2 (Thông: Schema) ──► T7.3 (Thống: BE Service) ──► T7.7 (Thiên: FE AI Card)
T7.4 (Thống: API Heatmap) ──► T7.8 (Thiên: FE Heatmap thật)
T7.5 (Thống: API Summary) ──► T7.8 (Thiên: FE Cards thật)
T7.6 (Thống: API Child Problems) ──► T7.9 (Thiên: FE Child History)
T7.7 + T7.8 + T7.9 ──► T7.10 (Bảo: UX Test) ──► T7.11 (Thiên: QA E2E)
```

**US 7.2 (Học Sinh - Streak & Sổ Tay)**
```
T7.12 (Thống: Model Bookmark) ──► T7.13 (Thống: API CRUD)
T7.15 (Thông: Gemini Boundary) ──► T7.16 (Thông: Prompt Flashcard) ──► T7.13
T7.14 (Thống: BE Streak/Badges) ──► T7.18 (Bảo: FE Streak/Badges)
T7.13 + T7.16 ──► T7.17 (Bảo: Nút Lưu) ──► T7.19 (Bảo: Trang Sổ tay) ──► T7.20 (Bảo: Drawer)
T7.12 ──► T7.21 (Thiên: Neon Index)
T7.19 + T7.20 ──► T7.22 (Thông: Test 20 tình huống lưu bài)
```

**US 7.3 (Admin Portal Frontend)**
```
T7.23 (Bảo: Design UI Figma) ──► T7.24 (Thiên: Admin Layout)
                               ├──► T7.25 (Thiên: Dashboard KPI)
                               ├──► T7.26 (Bảo: FE Users Table)
                               ├──► T7.27 (Bảo: FE Content)
                               ├──► T7.28 (Thiên: FE Safety)
                               └──► T7.29 (Thiên: FE Settings)
T7.31 (Thống: API Mock Admin) ──► T7.25 + T7.26
T7.24 đến T7.29 ──► T7.30 (Bảo: Rà soát 100% nút bấm) ──► T7.32 (Thông: QA Click-through) ──► T7.34 (Thiên: Review PR)
```

---

### 📌 Bảng Phân Bổ Công Việc Sprint 7:
| Thành viên | Tổng Giờ | Chi tiết Tasks |
| :--- | :--- | :--- |
| **[Bảo]** | **20.5h** | T7.10 (1.5h) + T7.17 (2h) + T7.18 (2h) + T7.19 (3h) + T7.20 (2.5h) + T7.23 (3h) + T7.26 (3h) + T7.27 (2h) + T7.30 (1.5h) |
| **[Thiên]** | **21.0h** | T7.7 (2.5h) + T7.8 (2.5h) + T7.9 (3h) + T7.11 (1.5h) + T7.21 (1.5h) + T7.24 (2.5h) + T7.25 (2.5h) + T7.28 (2h) + T7.29 (1.5h) + T7.34 (1.5h) |
| **[Thống]** | **20.0h** | T7.3 (2.5h) + T7.4 (2.5h) + T7.5 (2h) + T7.6 (2.5h) + T7.12 (2.5h) + T7.13 (3h) + T7.14 (2.5h) + T7.31 (2.5h) |
| **[Thông]** | **20.0h** | T7.1 (3h) + T7.2 (1.5h) + T7.15 (3h) + T7.16 (2.5h) + T7.22 (2.5h) + T7.32 (3h) + T7.33 (2h) + Setup prompt môi trường (2.5h) |

> ⭐ **Bắt đầu ngay Day 1 (Không bị nghẽn phụ thuộc chéo):**
> - **Bảo**: Thiết kế Wireframe/UI Admin (T7.23) $\rightarrow$ Code UI Streak & Badges (T7.18).
> - **Thiên**: Code UI Sổ theo dõi bài tập của con (T7.9) $\rightarrow$ Dựng Layout Admin & Sidebar (T7.24).
> - **Thống**: Viết API Heatmap thật (T7.4) $\rightarrow$ Model Bookmark & API CRUD (T7.12).
> - **Thông**: Viết Prompt AI Learning Insights (T7.1) $\rightarrow$ Viết Prompt Gemini Boundary Extraction (T7.15).