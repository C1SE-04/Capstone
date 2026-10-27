# Sprint 8: Đánh Giá Năng Lực Thực Chất, Game Hóa Tiến Hóa, Đăng Nhập Google & Tự Động Cào Chuyên Đề VietJack (24-Oct đến 30-Oct)
*(Phân bổ khối lượng: [Bảo]: 20.5h, [Thông]: 20.0h, [Thiên]: 21.0h, [Thống]: 19.5h)*

**Quy định phân chia vai trò nhóm (Sprint 8):**
- **[Thống]**: **Trùm Backend** (Chuyên API, Logic Server, Database Neon).
- **[Thông]**: **Kỹ sư AI / Machine Learning**, khi khối lượng Backend nhiều $\rightarrow$ Thông đảm nhận vai trò thứ hai là **Backend (BE)** (phụ trách logic lọc bài lặp và module cào dữ liệu VietJack).
- **[Bảo]**: **Trùm Frontend (FE) & Kịch bản UX**. **Ưu tiên số 1**: Bảo phụ trách toàn bộ hệ thống ngọn lửa chuỗi tiến hóa 7 mốc (Streak 🔥) và giao diện Sổ tay Playlist.
- **[Thiên]**: **Nhóm trưởng / DevOps / QA & Quản lý họp nhóm**. Khi khối lượng Frontend nhiều $\rightarrow$ Thiên đảm nhận vai trò thứ hai là **Frontend (FE)** (phụ trách các trang Admin Portal, Bảng xếp hạng, luồng Onboarding Google và fix CSS/KaTeX).
- **Nguyên tắc phối hợp**: Mỗi User Story có 2 thành viên cùng làm nhịp nhàng (1 Backend + 1 Frontend) để ra tính năng hoàn chỉnh, kiểm thử được ngay trên giao diện web.

---

### US 8.1: Đánh Giá Năng Lực Học Tập Thực Chất & Cảnh Báo Phụ Huynh Toàn Diện
*Mô tả: Là một Phụ huynh, tôi muốn hệ thống đánh giá chính xác năng lực thực chất của con (không cộng dồn bài làm lặp lại), xem tên bài con tự đặt gần gũi, và nhận email cảnh báo kịp thời khi con học yếu hoặc dùng từ ngữ chưa phù hợp, để tôi đồng hành cùng con tốt nhất.*
- **Mô tả chi tiết:**
  - **Phân loại bài tập & Deduplication**:
    - AI tự động phân tích và gán nhãn bài tập thành 3 nhóm:
      * `NEW_TOPIC`: Dạng bài mới $\rightarrow$ Tính điểm năng lực đầy đủ.
      * `ISOMORPHIC_PRACTICE`: Cùng dạng toán nhưng số liệu khác $\rightarrow$ Ghi nhận "Luyện tập củng cố", hiển thị tiến độ thành thạo, không tính trùng dạng.
      * `EXACT_DUPLICATE`: Đề bài trùng lặp y hệt $\rightarrow$ AI nhắc nhở nhẹ nhàng: *"Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?"*, không cộng dồn vào tổng số bài hoàn thành.
  - **Tên bài toán do học sinh làm chủ**:
    - Khi học sinh lưu bài vào Sổ tay, học sinh được tự gõ đặt tên bài toán (nếu để trống, hệ thống dùng tên AI gợi ý chuẩn sư phạm: `[Lớp X] [Chủ đề] – [Tên dạng toán]`).
    - Phụ huynh khi mở Sổ theo dõi bài tập sẽ thấy đúng tên con tự đặt, tạo cảm giác gần gũi và tôn trọng tư duy của con.
  - **Fix triệt để lỗi KaTeX `$$`**: Xử lý bộ lọc preprocessor làm sạch dấu `$$` và `\[ \]` thô, responsive công thức toán trên điện thoại.
  - **Email Cảnh báo kép tự động (Dual Alert)**:
    - *Cảnh báo Học tập*: Tự động gửi email phụ huynh khi con có điểm tự lập < 60 trong 3 bài liên tiếp hoặc tỷ lệ "Chưa hiểu" tăng đột biến.
    - *Cảnh báo Ngôn từ*: Kích hoạt khi Safety Agent phát hiện học sinh dùng ngôn từ tục tĩu, chửi thề, khiêu khích $\rightarrow$ gửi email nhắc nhở ấm áp nhưng nghiêm túc đến cha mẹ kèm trích đoạn vi phạm (đã che bớt từ thô).
- **Tasks:**
  - **T8.1** [Thông] [AI] Thiết kế Prompt Gemini phân loại bài tập (`NEW_TOPIC`, `ISOMORPHIC_PRACTICE`, `EXACT_DUPLICATE`) và nhận diện bài hỏi lại nhiều lần. (3h)
  - **T8.2** [Thông] [BE] Code logic Backend kiểm tra hash đề bài + gọi Prompt deduplication, chặn cộng dồn bài lặp vào bảng `independence_scores`. (3h)
  - **T8.3** [Thông] [AI] Prompt Gemini sinh tên bài toán mặc định (`friendly_parent_title`) chuẩn sư phạm làm placeholder gợi ý khi lưu bài. (2h)
  - **T8.4** [Thống] [BE] Cập nhật bảng `independence_scores` và API `/parent/child-problems` trả về tên bài toán do học sinh tự đặt. (2h)
  - **T8.5** [Thiên] [FE] Fix triệt để hiển thị KaTeX `$$` trong `ChatMessage.tsx`: preprocessor regex chuẩn hóa và CSS overflow-wrap trên di động. (2h)
  - **T8.6** [Thông] [AI/BE] Thiết kế Prompt & Pydantic Schema cho 2 loại Email Alert (Cảnh báo học tập yếu & Cảnh báo ngôn từ). (2.5h)
  - **T8.7** [Thống] [BE] Cập nhật `orchestrator_logs` thêm trường `notify_parent`, viết background worker gửi Email tự động trong 5 phút. (2.5h)
  - **T8.8** [Thiên] [QA] Viết kịch bản test E2E US 8.1: 20 tình huống gửi bài lặp, đổi số, kiểm tra công thức KaTeX và nhận email cảnh báo. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria – 100% Test Trên Web):**
  - **[AC 8.1.1] Nhận diện bài trùng lặp y hệt:** Học sinh gửi đề bài giống 100% bài đã giải trước đó $\rightarrow$ AI gửi câu nhắc nhở nhẹ; Hoàn thành bài này thì thẻ "Tổng bài hoàn thành" của Phụ huynh KHÔNG tăng thêm.
  - **[AC 8.1.2] Nhận diện bài cùng dạng đổi số (Luyện tập củng cố):** Học sinh giải bài cùng dạng đổi số $\rightarrow$ Thẻ bài tập trên Dashboard phụ huynh hiển thị đúng nhãn "Luyện tập củng cố", không tính trùng dạng mới.
  - **[AC 8.1.3] Hiển thị tên bài tự đặt:** Sổ theo dõi bài tập của phụ huynh hiển thị chính xác tên bài do học sinh tự đặt khi lưu (VD: *"Toán tuổi mẹ con khó nhằn"*); Nếu học sinh không sửa thì hiện tên chuẩn của AI.
  - **[AC 8.1.4] KaTeX sạch 100%:** Toàn bộ công thức toán hiển thị dạng ký hiệu toán học chuẩn, không còn sót ký tự thô `$$` hay `\[ \]`; Responsive mượt mà trên mobile viewport 375px không tràn viền chat.
  - **[AC 8.1.5] Email cảnh báo học tập:** Học sinh giải 3 bài liên tiếp có điểm tự lập < 60đ $\rightarrow$ Phụ huynh nhận email thông báo kèm tóm tắt và lời khuyên sư phạm trong vòng 5 phút.
  - **[AC 8.1.6] Email cảnh báo ngôn từ:** Học sinh dùng từ ngữ thô tục/chửi thề trong chat $\rightarrow$ Phụ huynh nhận email cảnh báo kèm trích đoạn đã kiểm duyệt trong vòng 5 phút.

---

### US 8.2: Game Hóa Tiến Hóa (Streak 🔥), Sổ Tay Playlist (Tự Đặt Tên) & Bảng Xếp Hạng
*Mô tả: Là một Học sinh, tôi muốn chuỗi ngày học của mình có hình ảnh ngọn lửa tiến hóa độc đáo, có thể thi đua trên bảng xếp hạng khối lớp/toàn server, và lưu bài toán vào các danh sách yêu thích với tên bài do chính tôi đặt.*
- **Mô tả chi tiết:**
  - **Ngọn lửa Streak 🔥 7 mốc tiến hóa (Ưu tiên Bảo FE)**:
    - *3 ngày*: ✨ Đốm Lửa Khởi Đầu (cam nhỏ, rung nhẹ).
    - *10 ngày*: 🔥 Lửa Bập Bùng (cam đỏ bốc mạnh + confetti nhỏ).
    - *30 ngày*: 💙 Lửa Xanh Lam (lửa xanh nhiệt lượng cao + đốm sao).
    - *60 ngày*: 🔮 Lửa Tím Huyền Bí (lửa tím lấp lánh + quầng sáng).
    - *100 ngày*: 👑 Lửa Vàng Kim (vương miện lửa vàng + pháo hoa lớn).
    - *200 ngày*: 🌟 Lửa Tinh Tú (ngôi sao cháy rực, tia sáng đa sắc + huy hiệu huyền thoại).
    - *365 ngày*: 🐉 Lửa Phượng Hoàng (phượng hoàng lửa toàn màn hình + vinh danh toàn server).
  - **Bảng xếp hạng chuỗi ngày học (Streak Leaderboard)**:
    - Trang `/dashboard/leaderboard`: Top học sinh có chuỗi ngày học cao nhất.
    - Bộ lọc tối giản & chuẩn xác: **Lọc theo Khối lớp (Lớp 4 → 9)** và **Toàn Server**.
    - Bảo vệ riêng tư: Chỉ hiện Tên hiển thị, Avatar, Khối lớp, Số ngày Streak và Rank.
  - **Sổ tay Playlist YouTube-style & Tự đặt tên bài**:
    - Khi bấm ⭐ *"Lưu vào Sổ tay"*, mở Popup gồm:
      1. Ô nhập: **Tên bài toán** (AI điền sẵn gợi ý, học sinh có thể gõ đè sửa theo ý mình).
      2. Danh sách checkbox các Playlist (Yêu thích, Ôn thi HK1...).
      3. Nút **"➕ Tạo danh sách mới"**: Mở thêm ô nhập tên danh sách $\rightarrow$ bấm Lưu là tạo mới danh sách và tự động lưu luôn bài toán vào đó.
    - Trang Sổ tay: Sidebar danh sách bên trái + Lưới thẻ bên phải + Phân trang 10 bài/trang.
  - **AI nhận diện bài toán tối giản**: Regex Trụ 1 Orchestrator nhận diện `4/2`, `10:2`, `3*5`... điều phối Socratic đúng phép tính.
- **Tasks:**
  - **T8.9** [Bảo] [FE] Thiết kế & Code bộ animation ngọn lửa Streak 7 mốc tiến hóa trong `StreakBadge.tsx`. (4h)
  - **T8.10** [Bảo] [FE] Nâng cấp `BadgeModal.tsx`: Xử lý Empty State khi chưa có cúp, badge khóa vs mở + hiệu ứng pháo hoa. (2h)
  - **T8.11** [Thống] [BE] Thiết kế bảng `bookmark_playlists`, `bookmark_playlist_items`, API CRUD playlist & lưu bài kèm tên học sinh đặt. (3h)
  - **T8.12** [Bảo] [FE] Code Popup lưu bài Sổ tay dạng Playlist (YouTube-style): Ô nhập tên bài + Checkbox danh sách + Tạo playlist mới tự động lưu. (3.5h)
  - **T8.13** [Bảo] [FE] Nâng cấp Trang Sổ tay `notebook/page.tsx`: Sidebar playlist + Lưới thẻ + Phân trang 10 bài/trang. (3h)
  - **T8.14** [Thống] [BE] Code API `GET /metrics/streak-leaderboard` tính top học sinh có chuỗi ngày cao nhất (lọc theo Khối lớp & Toàn server). (2.5h)
  - **T8.15** [Thiên] [FE] Code Trang Bảng xếp hạng Streak `/dashboard/leaderboard`: Giao diện bảng xếp hạng, bộ lọc Khối lớp & Toàn server, rank vinh danh. (2h)
  - **T8.16** [Thông] [AI/BE] Regex Trụ 1 Orchestrator nhận diện biểu thức tối giản `4/2`, `10:2`... điều phối Socratic trực tiếp. (2h)
  - **T8.35** [Bảo] [Design/FE] Thiết kế bộ icon/huy hiệu Streak 7 mốc & mockup Figma cho Popup Playlist. (3h)
  - **T8.36** [Bảo] [UX/QA] Đóng vai học sinh kiểm thử trải nghiệm vuốt chạm Lửa chuỗi, lưu bài và chuyển trang trên mobile. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria – 100% Test Trên Web):**
  - **[AC 8.2.1] Hiển thị 7 ngọn lửa tiến hóa:** Đạt các mốc 3, 10, 30, 60, 100, 200, 365 ngày hiển thị đúng icon ngọn lửa và hiệu ứng hoạt ảnh động trên header chat.
  - **[AC 8.2.2] Sửa lỗi Empty State huy hiệu:** Tài khoản mới mở Modal huy hiệu không hiện cúp sáng; hiển thị cúp mờ màu xám, icon ổ khóa, thanh tiến độ 0/1 và lời nhắn khích lệ.
  - **[AC 8.2.3] Popup Playlist lưu bài có sẵn:** Bấm ⭐ Lưu bài $\rightarrow$ Hiện popup có ô sửa tên bài và danh sách checkbox playlist; Chọn danh sách bấm Lưu $\rightarrow$ Thông báo thành công và lưu đúng bài.
  - **[AC 8.2.4] Tạo playlist mới tự động add bài:** Bấm "➕ Tạo danh sách mới", nhập tên list và tên bài $\rightarrow$ Bấm Lưu $\rightarrow$ Hệ thống tạo list mới và đưa luôn bài toán vào list đó (kiểm tra thấy ngay trong tab Sổ tay).
  - **[AC 8.2.5] Phân trang Sổ tay 10 bài/trang:** Trang `/dashboard/notebook` có sidebar playlist bên trái; Bên phải hiển thị đúng tối đa 10 bài/trang kèm nút chuyển trang Previous/Next hoạt động mượt mà.
  - **[AC 8.2.6] Bảng xếp hạng Streak:** Trang `/dashboard/leaderboard` hiển thị top học sinh, chuyển đổi mượt mà giữa bộ lọc "Toàn Server" và "Khối Lớp (4-9)", bảo mật không lộ email.
  - **[AC 8.2.7] Nhận diện bài toán tối giản:** Nhập `4/2` hoặc `10:2` $\rightarrow$ AI không báo lỗi mà gợi mở câu hỏi Socratic dạng chia kẹo ngay lập tức.

---

### US 8.3: Đăng Nhập Google OAuth (Kích Hoạt End-to-End)
*Mô tả: Là một Người dùng mới hoặc hiện tại, tôi muốn có thể đăng nhập nhanh bằng tài khoản Google chỉ với 1 click mà vẫn được cấp quyền JWT đầy đủ để gọi các tính năng Chat, Sổ tay và Báo cáo.*
- **Mô tả chi tiết:**
  - Khắc phục triệt để lỗi 401 hiện tại khi đăng nhập Google do Backend chưa có endpoint xử lý token.
  - **Luồng End-to-End**:
    1. Frontend NextAuth nhận Google Profile $\rightarrow$ gọi Backend `POST /auth/google-callback`.
    2. Backend kiểm tra email: nếu chưa có thì tạo mới user (`google_oauth=True`, `hashed_password=None`), trả về JWT chuẩn kèm cờ `is_new_user`.
    3. Nếu là user mới $\rightarrow$ FE tự động chuyển hướng đến `/onboarding` để chọn Vai trò (Học sinh/Phụ huynh) và Khối lớp.
- **Tasks:**
  - **T8.17** [Thiên] [DevOps] Thiết lập Google Cloud Console, tạo OAuth Client ID/Secret, cấu hình `.env` cho frontend/backend. (1h)
  - **T8.18** [Thống] [BE] Migration DB: Thêm `google_id`, `oauth_provider` vào bảng `users`, cho phép `hashed_password` nullable. (1.5h)
  - **T8.19** [Thống] [BE] Endpoint `POST /auth/google-callback`: Logic tìm/tạo user Google, sinh JWT chuẩn của backend kèm cờ `is_new_user`. (3h)
  - **T8.20** [Thiên] [FE] Cấu hình NextAuth callback `signIn` và session trong `[...nextauth]/route.ts` nối với backend lấy JWT. (1.5h)
  - **T8.21** [Thiên] [FE] Nâng cấp trang `/onboarding`: Luồng chọn Vai trò (Học sinh/Phụ huynh) và Khối lớp cho user Google mới. (2h)
  - **T8.22** [Thiên] [QA] Test E2E luồng Google Login: Click đăng nhập Google $\rightarrow$ Onboarding $\rightarrow$ Chat gọi API Backend thành công. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria – 100% Test Trên Web):**
  - **[AC 8.3.1] Đăng nhập 1-click thành công:** Click nút "Đăng nhập với Google" $\rightarrow$ Đăng nhập trơn tru, cấp JWT chuẩn, gọi các API `/chat` và `/bookmarks` không còn lỗi 401.
  - **[AC 8.3.2] Onboarding bắt buộc cho user Google mới:** Tài khoản Google lần đầu đăng nhập tự động bị chuyển hướng sang `/onboarding`, chọn xong Vai trò và Khối lớp mới được vào Dashboard chính; Cố tình gõ URL khác bị chặn lại.
  - **[AC 8.3.3] User cũ vào thẳng Dashboard:** Tài khoản Google đã từng onboarding khi đăng nhập lại được vào thẳng Dashboard/Chat, giữ nguyên phiên làm việc và lịch sử bài tập.

---

### US 8.4: Chương Trình Học Linh Động – Tự Động Cào Dữ Liệu Chuyên Đề Từ VietJack & Quản Lý Qua Admin
*Mô tả: Là một Quản trị viên và Kỹ sư hệ thống, tôi muốn hệ thống tự động cào và đồng bộ danh mục chuyên đề môn Toán từ nguồn mở chuẩn (VietJack) vào cơ sở dữ liệu chỉ với 1 click, để chương trình học luôn đúng với năm hiện tại mà dev không cần sửa code mỗi năm.*
- **Mô tả chi tiết:**
  - **Crawler Service Backend (`curriculum_crawler.py`)**:
    - Dùng `BeautifulSoup` + `requests` cào trực tiếp cây mục lục chuẩn SGK mới (Kết Nối Tri Thức, Cánh Diều) từ VietJack cho môn Toán lớp 4 $\rightarrow$ lớp 9.
    - Tự động bóc tách: Khối lớp, Tên Chủ đề/Chương lớn, Tên bài học, Thứ tự và niên khóa.
    - Endpoint `POST /admin/curriculum/sync-vietjack` kích hoạt cào và upsert vào bảng `curriculum_topics` (Neon DB).
  - **Admin Portal (`admin/content`)**:
    - Nút bấm nổi bật: **`[ 🔄 Cào & Đồng Bộ Từ VietJack ]`**.
    - Bấm 1 click $\rightarrow$ Modal hiển thị tiến độ và thông báo số bài cập nhật thành công trong 2–4 giây.
    - Admin chỉ việc vào xem, kiểm tra, có thể sửa tên hoặc toggle Bật/Tắt (`is_active`) nếu trường có giảm tải riêng.
  - **Tích hợp AI Engine**: `agent_prompts.py` đọc DB `curriculum_topics` (cache 5 phút). Khi chương trình đổi, AI tự động nắm bắt kiến thức mới mà dev không sửa code.
- **Tasks:**
  - **T8.23** [Thống] [BE] Thiết kế bảng `curriculum_topics` trên Neon DB và tạo migration an toàn. (1.5h)
  - **T8.24** [Thông] [BE] Viết module crawler `curriculum_crawler.py` (BeautifulSoup bóc tách mục lục Toán 4-9 từ VietJack). (3.5h)
  - **T8.25** [Thống] [BE] Endpoint API `POST /admin/curriculum/sync-vietjack` kích hoạt crawler và upsert chuyên đề vào DB. (2h)
  - **T8.26** [Thông] [AI/BE] Cập nhật hàm `_load_curriculum()` trong `agent_prompts.py`: Query DB `curriculum_topics` kèm cache 5 phút. (2h)
  - **T8.27** [Bảo] [FE] Giao diện Admin `admin/content`: Nút `[🔄 Cào & Đồng bộ từ VietJack]`, modal loading tiến độ, bảng chuyên đề, toggle ẩn/hiện. (3h)
  - **T8.29** [Thiên] [QA/BE] Kiểm thử an toàn script cào VietJack: Xử lý timeout, lỗi mạng, rate-limit và cơ chế fallback DB. (1h)
- **Tiêu chí chấp nhận (Acceptance Criteria – 100% Test Trên Web):**
  - **[AC 8.4.1] Nút cào 1-click trên Admin:** Bấm `[ 🔄 Cào & Đồng Bộ Từ VietJack ]` trên trang `admin/content` $\rightarrow$ Modal hiển thị loading tiến độ và thông báo cào thành công đủ chuyên đề Toán lớp 4-9 trong 2-4 giây.
  - **[AC 8.4.2] Bảng chuyên đề đầy đủ:** Bảng trên `admin/content` hiển thị rõ: Khối lớp, Chương lớn, Tên bài học, Học kỳ; Có dropdown lọc theo lớp và thanh tìm kiếm tên bài học.
  - **[AC 8.4.3] Toggle ẩn/hiện chuyên đề tức thì:** Gạt Toggle switch chuyển bài sang "Ẩn" $\rightarrow$ Trạng thái cập nhật ngay trong DB và hiển thị badge xám.
  - **[AC 8.4.4] Prompt AI nhận diện động:** Học sinh hỏi kiến thức lớp đang học $\rightarrow$ AI đối chiếu chính xác danh mục chuyên đề trong DB để phản hồi, không cần sửa code hay redeploy backend.

---

### US 8.5: Tinh Chỉnh Admin Portal Theo Phản Hồi Sprint Review 7
*Mô tả: Là một Quản trị viên, tôi muốn giao diện Admin phản ánh đúng thực tế vận hành: tra cứu được log theo từng tài khoản khi hỗ trợ khách hàng, bỏ thống kê không cần thiết và theo dõi biểu đồ tài nguyên AI chính xác.*
- **Mô tả chi tiết:**
  - **Bỏ thống kê ẩn danh**: Trang `admin/users` giữ vai trò là danh mục xem tài khoản, trạng thái hoạt động và tra cứu log của từng user cụ thể.
  - **Tra cứu Log theo tài khoản**: Bổ sung thanh tìm kiếm `user_id` / `email` trên trang `admin/logs` để lọc log đúng người dùng cần hỗ trợ.
  - **Biểu đồ AI thực tế**: Thay biểu đồ Flash vs Pro bằng **Tổng token tiêu thụ theo ngày** và **Latency trung bình (ms)** theo ngày.
- **Tasks:**
  - **T8.28** [Thiên] [FE] Điều chỉnh `admin/users/page.tsx`: Gỡ bỏ phần thống kê ẩn danh, giữ bảng user xem trạng thái tài khoản. (1h)
  - **T8.29B** [Thống] [BE] API Admin Logs lọc theo tài khoản: `GET /admin/logs?user_id=...&email=...`. (1.5h)
  - **T8.30** [Thiên] [FE] Cập nhật `admin/safety/page.tsx` và `admin/logs`: Thêm thanh search Email/UserID để tra cứu log theo tài khoản. (1h)
  - **T8.31** [Thiên] [FE] Điều chỉnh biểu đồ `admin/page.tsx`: Total token/ngày + Latency trung bình thay vì Flash vs Pro. (1.5h)
  - **T8.32** [Thiên] [Management] Chủ trì 2 buổi họp nhóm (Sprint Planning đầu tuần + Mid-sprint sync), quản lý tiến độ Jira. (2h)
  - **T8.33** [Thiên] [Management/QA] Review toàn bộ PR code, giải quyết conflict, kiểm thử bảo mật & chốt nghiệm thu Sprint 8. (3h)
  - **T8.34** [Thông] [Document] Viết tài liệu bàn giao tính năng mới Sprint 8 & cập nhật test report. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria – 100% Test Trên Web):**
  - **[AC 8.5.1] Gỡ bỏ thống kê ẩn danh:** Trang `admin/users` không còn biểu đồ ẩn danh người dùng, bảng danh sách user hiển thị rõ ràng thông tin và nút xem log.
  - **[AC 8.5.2] Tra cứu log theo email/user_id:** Nhập email vào ô tìm kiếm trên `admin/logs` $\rightarrow$ Bảng chỉ hiển thị đúng các sự kiện và lỗi của tài khoản đó.
  - **[AC 8.5.3] Biểu đồ Token & Latency:** Trang `admin/page.tsx` hiển thị biểu đồ kết hợp tổng token tiêu thụ và độ trễ latency trung bình (ms) theo từng ngày; Hover chuột hiện tooltip đầy đủ số liệu.

---

### 📌 Sơ Đồ Phụ Thuộc Task – Sprint 8

**US 8.1 (Năng Lực Thực Chất & Cảnh Báo Phụ Huynh)**
```
T8.1 (Thông: Prompt Deduplicate) ──► T8.2 (Thông: BE Deduplicate Logic)
T8.3 (Thông: Prompt Friendly Title) ──► T8.4 (Thống: BE Child Problems Title)
T8.6 (Thông: Prompt Alert Email) ──► T8.7 (Thống: BE Email Worker)
T8.5 (Thiên: FE Fix KaTeX)
T8.2 + T8.4 + T8.7 + T8.5 ──► T8.8 (Thiên: QA Test E2E US 8.1)
```

**US 8.2 (Game Hóa Lửa Chuỗi & Sổ Tay Playlist)**
```
T8.35 (Bảo: Design Figma Lửa & Playlist) ──► T8.9 (Bảo: FE Lửa 7 Mốc Animation)
T8.11 (Thống: BE Playlist DB/API) ──► T8.12 (Bảo: FE Popup Playlist) ──► T8.13 (Bảo: FE Sổ Tay)
T8.14 (Thống: BE Leaderboard API) ──► T8.15 (Thiên: FE Leaderboard Page)
T8.16 (Thông: AI Regex Toán Tối Giản)
T8.9 + T8.10 + T8.13 ──► T8.36 (Bảo: UX Test Học Sinh Mobile)
```

**US 8.3 (Google OAuth End-to-End)**
```
T8.17 (Thiên: Google Cloud Setup) ──► T8.18 (Thống: DB Migration google_id)
                                  ──► T8.19 (Thống: BE /auth/google-callback)
                                  ──► T8.20 (Thiên: FE NextAuth callback)
                                  ──► T8.21 (Thiên: FE Onboarding Google)
T8.19 + T8.20 + T8.21 ──► T8.22 (Thiên: QA E2E Google Login)
```

**US 8.4 (Chương Trình Học Cào VietJack) & US 8.5 (Admin Portal)**
```
T8.23 (Thống: DB curriculum_topics) ──► T8.24 (Thông: BE Crawler VietJack) ──► T8.25 (Thống: API Sync)
T8.25 ──► T8.26 (Thông: AI _load_curriculum DB)
T8.25 ──► T8.27 (Bảo: FE Admin Nút Cào VietJack & Toggle)
T8.29B (Thống: API Filter Logs) ──► T8.30 (Thiên: FE Filter Logs)
T8.28 + T8.30 + T8.31 (Thiên: FE Admin Updates)
Toàn bộ tasks ──► T8.32 + T8.33 (Thiên: Họp & Review PR) + T8.34 (Thông: Document)
```

---

### 📌 Bảng Phân Bổ Công Việc Sprint 8:

| Thành viên | Tổng Giờ | Chi tiết Tasks Sprint 8 |
| :--- | :---: | :--- |
| **[Bảo]** *(Trùm FE - Ưu tiên Lửa chuỗi & Sổ tay)* | **20.5h** | • **T8.9** (4h): FE Lửa chuỗi 7 mốc tiến hóa animation (`StreakBadge.tsx`)<br>• **T8.10** (2h): FE Sửa `BadgeModal.tsx` Empty State + Cúp khóa/mở<br>• **T8.12** (3.5h): FE Popup lưu bài Sổ tay dạng Playlist (YouTube-style)<br>• **T8.13** (3h): FE Nâng cấp Trang Sổ tay Sidebar Playlist + Phân trang 10 bài<br>• **T8.27** (3h): FE Admin Content nút Cào VietJack & Toggle chuyên đề<br>• **T8.35** (3h): Design Figma bộ huy hiệu Lửa chuỗi 7 mốc & Popup Playlist<br>• **T8.36** (2h): Đóng vai học sinh UX test vuốt chạm Lửa chuỗi, lưu bài mobile |
| **[Thông]** *(AI & Hỗ trợ Backend)* | **20.0h** | • **T8.1** (3h): AI Prompt Gemini phân loại bài tập deduplication<br>• **T8.2** (3h): **[BE]** Logic kiểm tra hash đề bài & chặn cộng dồn bài lặp<br>• **T8.3** (2h): AI Prompt sinh tên bài toán mặc định (`friendly_parent_title`)<br>• **T8.6** (2.5h): AI/BE Prompt & Pydantic Schema cho 2 loại Email Alert<br>• **T8.16** (2h): AI Regex Trụ 1 Orchestrator nhận diện toán tối giản `4/2`<br>• **T8.24** (3.5h): **[BE]** Viết module crawler `curriculum_crawler.py` (BeautifulSoup cào VietJack)<br>• **T8.26** (2h): **[BE]** Cập nhật `_load_curriculum()` query DB `curriculum_topics`<br>• **T8.34** (2h): Viết tài liệu bàn giao tính năng mới & test report |
| **[Thống]** *(Trùm Backend)* | **19.5h** | • **T8.4** (2h): BE Cập nhật bảng `independence_scores` & API trả tên bài học sinh đặt<br>• **T8.7** (2.5h): BE Worker gửi Email cảnh báo phụ huynh tự động trong 5 phút<br>• **T8.11** (3h): BE Bảng `bookmark_playlists` + API CRUD Playlist & lưu bài<br>• **T8.14** (2.5h): BE API `GET /metrics/streak-leaderboard` lọc Khối lớp & Toàn server<br>• **T8.18** (1.5h): BE Migration thêm `google_id`, `oauth_provider` vào `users`<br>• **T8.19** (3h): BE Endpoint `POST /auth/google-callback` xử lý upsert user & JWT<br>• **T8.23** (1.5h): BE Tạo bảng `curriculum_topics` trên Neon DB<br>• **T8.25** (2h): BE Endpoint API `POST /admin/curriculum/sync-vietjack`<br>• **T8.29B** (1.5h): BE API Admin Logs lọc theo tài khoản `user_id` / `email` |
| **[Thiên]** *(Nhóm trưởng / QA / Họp & Hỗ trợ FE)* | **21.0h** | • **T8.5** (2h): **[FE]** Fix triệt để KaTeX `$$` trong `ChatMessage.tsx` & CSS mobile<br>• **T8.8** (1.5h): QA Test E2E US 8.1 (bài lặp, đổi số, email alert)<br>• **T8.15** (2h): **[FE]** Code Trang Bảng xếp hạng Streak `/dashboard/leaderboard`<br>• **T8.17** (1h): DevOps Setup Google Cloud Console OAuth Client ID/Secret<br>• **T8.20** (1.5h): **[FE]** Cấu hình NextAuth callback `signIn` lấy JWT backend<br>• **T8.21** (2h): **[FE]** Nâng cấp trang `/onboarding` chọn Role/Lớp cho Google user<br>• **T8.22** (1.5h): QA Test E2E luồng Google Login end-to-end<br>• **T8.28** (1h): **[FE]** Gỡ bỏ thống kê ẩn danh trên `admin/users`<br>• **T8.30** (1h): **[FE]** Thêm thanh tìm kiếm Email/UserID trên `admin/logs`<br>• **T8.31** (1.5h): **[FE]** Sửa biểu đồ `admin/page.tsx` sang tổng token & latency<br>• **T8.29** (1h): QA Kiểm thử an toàn script cào VietJack (timeout/fallback)<br>• **T8.32** (2h): Management Chủ trì họp nhóm Sprint Planning & Mid-sprint sync<br>• **T8.33** (3h): Review PR toàn bộ mã nguồn, gỡ conflict và chốt nghiệm thu Sprint 8 |

> ⭐ **Bắt đầu ngay Day 1 (Không bị nghẽn phụ thuộc chéo):**
> - **Bảo**: Thiết kế Figma bộ huy hiệu Lửa chuỗi 7 mốc (T8.35) $\rightarrow$ Code animation `StreakBadge.tsx` (T8.9).
> - **Thông**: Viết Prompt phân loại bài tập deduplication (T8.1) $\rightarrow$ Viết module cào dữ liệu VietJack (T8.24).
> - **Thống**: Viết endpoint Google callback `/auth/google-callback` (T8.19) $\rightarrow$ Tạo bảng `curriculum_topics` (T8.23).
> - **Thiên**: Setup Google Cloud Console OAuth Client (T8.17) $\rightarrow$ Fix triệt để KaTeX `$$` trong `ChatMessage.tsx` (T8.5).
