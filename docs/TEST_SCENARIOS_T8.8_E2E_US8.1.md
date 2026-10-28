# KỊCH BẢN KIỂM THỬ E2E TOÀN DIỆN US 8.1 (E2E TEST SPECIFICATION)
**Mã Task:** `T8.8` [Thiên] [QA]  
**Thuộc User Story:** `US 8.1: Đánh Giá Năng Lực Học Tập Thực Chất & Cảnh Báo Phụ Huynh Toàn Diện` (Sprint 8)  
**Tập kịch bản:** 20 Tình huống kiểm thử E2E tích hợp hệ thống (End-to-End Test Scenarios)  
**Tiêu chuẩn đối chiếu:** AC 8.1.1, AC 8.1.2, AC 8.1.3, AC 8.1.4, AC 8.1.5, AC 8.1.6  

---

## 1. MỤC TIÊU VÀ PHẠM VI KIỂM THỬ

### 1.1 Mục tiêu
Xác thực 100% tính năng của User Story 8.1 hoạt động chính xác từ giao diện Web Frontend (Học sinh & Phụ huynh) đến tầng AI Engine (Gemini 1.5) và Cơ sở dữ liệu Neon DB / Worker gửi email:
1. **Phân loại bài tập & Deduplication**: Chặn cộng dồn bài lặp `EXACT_DUPLICATE` vào điểm năng lực; gắn nhãn `ISOMORPHIC_PRACTICE` (Luyện tập củng cố) cho bài cùng dạng đổi số.
2. **Tên bài toán do học sinh làm chủ**: Lưu bài với tên tự đặt của học sinh hoặc placeholder chuẩn sư phạm AI (`friendly_parent_title`).
3. **KaTeX toán học sạch 100%**: Làm sạch triệt để dấu `$$`, `\[ \]`, `\( \)` và responsive không tràn viền trên di động (viewport 375px).
4. **Email cảnh báo kép tự động (Dual Alert)**: Gửi email cảnh báo học tập yếu (< 60đ trong 3 bài liên tiếp) và cảnh báo ngôn từ thô tục (che kiểm duyệt trích đoạn vi phạm) trong vòng 5 phút.

### 1.2 Môi trường & Tài khoản kiểm thử
* **Học sinh:** `student_e2e@socratickid.local` (Lớp 5, ID: `std_e2e_01`)
* **Phụ huynh:** `parent_e2e@socratickid.local` (ID: `par_e2e_01`, liên kết với `std_e2e_01`)
* **Thiết bị kiểm thử giao diện:**
  - Desktop: Chrome 1920x1080px
  - Mobile: Safari / Chrome mobile viewport 375x667px (iPhone SE / iPhone 13 mini)

---

## 2. MA TRẬN 20 TÌNH HUỐNG KIỂM THỬ E2E (TEST MATRIX)

| Nhóm Tính Năng | Mã TestCase | Tên Tình Huống Kiểm Thử | Tiêu Chuẩn AC |
|---|:---:|---|:---:|
| **Nhóm 1: Trùng Lặp Y Hệt** | **TC-E2E-01** | Học sinh gửi đề bài trùng 100% bài đã giải trước đó | AC 8.1.1 |
| *(EXACT_DUPLICATE)* | **TC-E2E-02** | Trùng lặp câu chữ nhưng khác khoảng trắng và viết hoa | AC 8.1.1 |
| | **TC-E2E-03** | Học sinh yêu cầu giải lại bài cũ đã hoàn thành | AC 8.1.1 |
| | **TC-E2E-04** | Kiểm tra Dashboard Phụ huynh: "Tổng bài hoàn thành" KHÔNG tăng | AC 8.1.1 |
| **Nhóm 2: Cùng Dạng Đổi Số** | **TC-E2E-05** | Bài toán Tổng - Hiệu cùng dạng nhưng đổi số liệu | AC 8.1.2 |
| *(ISOMORPHIC_PRACTICE)* | **TC-E2E-06** | Dashboard Phụ huynh hiển thị nhãn "Luyện tập củng cố" | AC 8.1.2 |
| | **TC-E2E-07** | Bài toán Chuyển động đều đổi vận tốc và quãng đường | AC 8.1.2 |
| | **TC-E2E-08** | Quy đồng mẫu số phân số đổi số liệu và cập nhật thành thạo | AC 8.1.2 |
| **Nhóm 3: Tên Bài Tự Đặt** | **TC-E2E-09** | Học sinh tự đặt tên bài tùy ý khi lưu vào Sổ tay | AC 8.1.3 |
| *(Problem Title)* | **TC-E2E-10** | Học sinh để trống tên bài $\rightarrow$ Dùng placeholder AI gợi ý | AC 8.1.3 |
| | **TC-E2E-11** | Tên bài tự đặt chứa ký tự đặc biệt, emoji và dấu tiếng Việt | AC 8.1.3 |
| **Nhóm 4: Hiển Thị KaTeX** | **TC-E2E-12** | Công thức toán có ký tự thô `\[ ... \]` và `\( ... \)` | AC 8.1.4 |
| *(Clean KaTeX & CSS)* | **TC-E2E-13** | Công thức toán `$$` nằm giữa dòng văn bản thường (inline) | AC 8.1.4 |
| | **TC-E2E-14** | Công thức phân số dài hiển thị trên mobile viewport 375px | AC 8.1.4 |
| | **TC-E2E-15** | Khối code Markdown chứa dấu `$` không bị KaTeX biến dạng | AC 8.1.4 |
| **Nhóm 5: Email Cảnh Báo Kép** | **TC-E2E-16** | 3 bài liên tiếp điểm tự lập < 60đ $\rightarrow$ Gửi email học tập yếu | AC 8.1.5 |
| *(Dual Alert System)* | **TC-E2E-17** | Xen kẽ bài >= 60đ $\rightarrow$ Không gửi cảnh báo học tập | AC 8.1.5 |
| | **TC-E2E-18** | Học sinh dùng từ ngữ thô tục / chửi thề trong chat | AC 8.1.6 |
| | **TC-E2E-19** | Email cảnh báo ngôn từ trích đoạn đã che kiểm duyệt (`***`) | AC 8.1.6 |
| | **TC-E2E-20** | Tỷ lệ bấm "Chưa hiểu" >= 3 lần $\rightarrow$ Ghi nhận cảnh báo sư phạm | AC 8.1.5 / AC 8.1.6 |

---

## 3. ĐẶC TẢ CHI TIẾT 20 TÌNH HUỐNG KIỂM THỬ (TEST CASES)

### ── NHÓM 1: NHẬN DIỆN BÀI TRÙNG LẶP Y HỆT (EXACT_DUPLICATE) ──

#### TC-E2E-01: Học sinh gửi đề bài trùng 100% bài đã giải trước đó
* **Mục tiêu:** Kiểm tra hệ thống nhận diện `EXACT_DUPLICATE` khi đề bài giống từng chữ.
* **Các bước:**
  1. Học sinh đăng nhập và gửi đề: *"Một mảnh đất hình chữ nhật có chiều dài 24m, chiều rộng bằng 2/3 chiều dài. Tính diện tích mảnh đất."*
  2. Hoàn thành phiên giải bài.
  3. Mở phiên chat mới và gửi lại đúng 100% đề bài trên.
* **Kỳ vọng:** AI phát hiện bài đã làm và phản hồi nhắc nhở nhẹ nhàng: *"Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?"*. Phân loại trả về `EXACT_DUPLICATE`.

#### TC-E2E-02: Trùng lặp câu chữ nhưng khác khoảng trắng và viết hoa
* **Mục tiêu:** Kiểm tra hàm băm SHA-256 chuẩn hóa không bị ảnh hưởng bởi format văn bản.
* **Các bước:**
  1. Đề bài gốc: *"Tìm x biết: 3x - 7 = 14"*
  2. Đề bài gửi lại: *"   tìm X biết:   3x - 7 = 14.  "* (thừa dấu cách, chữ hoa, dấu chấm).
* **Kỳ vọng:** `compute_problem_hash()` sinh ra hash SHA-256 trùng khớp; phân loại đúng `EXACT_DUPLICATE`.

#### TC-E2E-03: Học sinh yêu cầu giải lại bài cũ đã hoàn thành
* **Mục tiêu:** Học sinh cố tình gõ *"Thầy ơi giải lại bài 3x - 7 = 14 cho em với"*.
* **Các bước:** Học sinh gửi đề bài cũ kèm lời mở đầu xin giải lại.
* **Kỳ vọng:** AI trích xuất được cốt lõi đề bài, nhận diện bài đã hoàn thành và hướng dẫn ôn tập thay vì tính thêm bài mới.

#### TC-E2E-04: Kiểm tra Dashboard Phụ huynh: "Tổng bài hoàn thành" KHÔNG tăng
* **Mục tiêu:** Đảm bảo tính trung thực của báo cáo phụ huynh (AC 8.1.1).
* **Các bước:**
  1. Phụ huynh xem thẻ "Tổng bài hoàn thành" (ví dụ đang là `15 bài`).
  2. Học sinh hoàn thành giải bài `EXACT_DUPLICATE`.
  3. Phụ huynh tải lại trang Dashboard.
* **Kỳ vọng:** Thẻ "Tổng bài hoàn thành" vẫn giữ nguyên `15 bài`, không cộng dồn thêm bài trùng lặp.

---

### ── NHÓM 2: NHẬN DIỆN BÀI CÙNG DẠNG ĐỔI SỐ (ISOMORPHIC_PRACTICE) ──

#### TC-E2E-05: Bài toán Tổng - Hiệu cùng dạng nhưng đổi số liệu
* **Mục tiêu:** Nhận diện bài tập đổi số liệu cùng phương pháp giải (AC 8.1.2).
* **Các bước:**
  1. Bài 1: *"Tìm hai số có tổng là 48 và hiệu là 12."* (Học sinh đã giải xong).
  2. Bài 2: *"Tìm hai số biết tổng của chúng bằng 60 và hiệu bằng 20."*
* **Kỳ vọng:** AI phân loại nhãn `ISOMORPHIC_PRACTICE`; ghi nhận điểm tự lực nhưng không tạo chủ đề mới.

#### TC-E2E-06: Dashboard Phụ huynh hiển thị nhãn "Luyện tập củng cố"
* **Mục tiêu:** Kiểm tra hiển thị trực quan cho cha mẹ (AC 8.1.2).
* **Các bước:** Phụ huynh vào trang Sổ theo dõi bài tập (`/dashboard/monitor`).
* **Kỳ vọng:** Thẻ bài tập Bài 2 hiển thị rõ nhãn badge **"Luyện tập củng cố"**, ghi nhận mức độ thành thạo tăng lên.

#### TC-E2E-07: Bài toán Chuyển động đều đổi vận tốc và quãng đường
* **Mục tiêu:** Kiểm thử dạng toán chuyển động hai xe ngược chiều.
* **Các bước:**
  1. Bài 1: Xe máy 35 km/h, ô tô 50 km/h, quãng đường 170 km.
  2. Bài 2: Xe máy 40 km/h, ô tô 60 km/h, quãng đường 200 km.
* **Kỳ vọng:** Phân loại đúng `ISOMORPHIC_PRACTICE`; câu hỏi Socratic tập trung vào bước tính tổng vận tốc hai xe.

#### TC-E2E-08: Quy đồng mẫu số phân số đổi số liệu và cập nhật thành thạo
* **Mục tiêu:** Kiểm thử toán phân số Lớp 5.
* **Các bước:**
  1. Đề 1: Quy đồng mẫu số 2/3 và 3/5.
  2. Đề 2: Quy đồng mẫu số 3/4 và 5/6.
* **Kỳ vọng:** Phân loại `ISOMORPHIC_PRACTICE`; thanh đo tiến độ làm chủ phân số của học sinh tăng dần.

---

### ── NHÓM 3: TÊN BÀI TOÁN DO HỌC SINH TỰ ĐẶT & PLACEHOLDER AI ──

#### TC-E2E-09: Học sinh tự đặt tên bài tùy ý khi lưu vào Sổ tay
* **Mục tiêu:** Học sinh làm chủ tên bài toán cá nhân hóa (AC 8.1.3).
* **Các bước:**
  1. Học sinh hoàn thành bài toán và bấm ⭐ "Lưu vào Sổ tay".
  2. Trong ô nhập tên bài, học sinh gõ: *"Toán tuổi mẹ con khó nhằn"*.
  3. Bấm "Lưu bài".
  4. Phụ huynh mở Sổ theo dõi bài tập.
* **Kỳ vọng:** Sổ theo dõi bài tập của phụ huynh hiển thị chính xác tên *"Toán tuổi mẹ con khó nhằn"*.

#### TC-E2E-10: Học sinh để trống tên bài $\rightarrow$ Dùng placeholder AI gợi ý
* **Mục tiêu:** Kiểm tra cơ chế tự động điền tên chuẩn sư phạm của AI (AC 8.1.3).
* **Các bước:**
  1. Học sinh lưu bài toán Tìm x lớp 6 nhưng không sửa ô tên bài (để trống).
  2. Bấm "Lưu bài".
* **Kỳ vọng:** Hệ thống tự động gán tên bài theo format chuẩn: `[Lớp 6] Số học – Tìm x trong phương trình bậc nhất`.

#### TC-E2E-11: Tên bài tự đặt chứa ký tự đặc biệt, emoji và dấu tiếng Việt
* **Mục tiêu:** Kiểm tra độ an toàn dữ liệu và bảo mật XSS.
* **Các bước:** Học sinh đặt tên bài: *"🔥 Bài hình thang siêu cấp VIP Pro! <script>alert(1)</script>"*.
* **Kỳ vọng:** Hệ thống lưu an toàn, mã hóa HTML entities, hiển thị đầy đủ icon và chữ tiếng Việt mà không gây lỗi giao diện.

---

### ── NHÓM 4: HIỂN THỊ KATEX TOÁN HỌC SẠCH 100% & RESPONSIVE ──

#### TC-E2E-12: Công thức toán có ký tự thô `\[ ... \]` và `\( ... \)`
* **Mục tiêu:** Tiền xử lý KaTeX làm sạch triệt để ký tự escape thô từ LLM (AC 8.1.4).
* **Các bước:** AI gửi phản hồi chứa `\[ S = \frac{(a + b) \times h}{2} \]` và `\( x = 5 \)`.
* **Kỳ vọng:** `preprocessLaTeX()` chuyển hóa thành khối KaTeX chuẩn; trên giao diện hiển thị công thức toán học sắc nét, không còn sót ký tự thô `\[` hay `\]`.

#### TC-E2E-13: Công thức toán `$$` nằm giữa dòng văn bản thường (inline)
* **Mục tiêu:** Ngăn lỗi vỡ hàng khi LLM dùng sai ký hiệu `$$` giữa câu (AC 8.1.4).
* **Các bước:** Phản hồi: *"Ta có $$x + 2 = 7$$ vậy nên x bằng 5."*.
* **Kỳ vọng:** `preprocessLaTeX()` chuẩn hóa `$$x + 2 = 7$$` thành `$x + 2 = 7$` inline math; văn bản hiển thị liền mạch không bị nhảy dòng đột ngột.

#### TC-E2E-14: Công thức phân số dài hiển thị trên mobile viewport 375px
* **Mục tiêu:** Kiểm tra responsive di động không tràn viền (AC 8.1.4).
* **Các bước:**
  1. Mở trình duyệt giả lập Mobile viewport 375px (iPhone SE).
  2. AI gửi công thức tính dãy phân số dài: `A = 1/2 + 1/4 + 1/8 + ... + 1/512`.
* **Kỳ vọng:** Bong bóng chat giữ nguyên viền bo tròn, công thức tự xuống dòng hoặc có thanh cuộn ngang mượt mà, không bị vỡ giao diện chat.

#### TC-E2E-15: Khối code Markdown chứa dấu `$` không bị KaTeX biến dạng
* **Mục tiêu:** Bảo vệ khối mã nguồn code block (AC 8.1.4).
* **Các bước:** Tin nhắn có đoạn code Python: `price = "$500"`.
* **Kỳ vọng:** Khối code giữ nguyên ký tự `$500`, KaTeX không parse nhầm thành công thức toán.

---

### ── NHÓM 5: EMAIL CẢNH BÁO KÉP TỰ ĐỘNG (DUAL ALERT SYSTEM) ──

#### TC-E2E-16: 3 bài liên tiếp điểm tự lập < 60đ $\rightarrow$ Gửi email học tập yếu
* **Mục tiêu:** Kích hoạt cảnh báo học tập yếu tự động (AC 8.1.5).
* **Các bước:**
  1. Học sinh hoàn thành 3 bài liên tiếp có điểm tự lập lần lượt: 45đ, 50đ, 40đ.
  2. Chờ background worker (`alert_email_worker`) quét trong chu kỳ 5 phút.
* **Kỳ vọng:** Hệ thống tự động gửi email đến hộp thư phụ huynh với tiêu đề: *"SocraticKid: Cảnh báo tiến độ học tập của con"*, kèm tóm tắt dạng bài khó và lời khuyên sư phạm.

#### TC-E2E-17: Xen kẽ bài >= 60đ $\rightarrow$ Không gửi cảnh báo học tập
* **Mục tiêu:** Tránh làm phiền phụ huynh khi con đã có tiến bộ (AC 8.1.5).
* **Các bước:** Điểm 3 bài lần lượt là: 45đ, 85đ, 50đ (bài thứ 2 con hiểu bài tốt).
* **Kỳ vọng:** Không kích hoạt gửi email cảnh báo học tập yếu.

#### TC-E2E-18: Học sinh dùng từ ngữ thô tục / chửi thề trong chat
* **Mục tiêu:** Safety Agent phát hiện vi phạm và bật cờ cảnh báo phụ huynh (AC 8.1.6).
* **Các bước:** Học sinh gửi tin nhắn: *"Đồ bot ngốc nghếch vcl không biết làm bài à"*.
* **Kỳ vọng:** Safety Agent can thiệp, gửi câu nhắc nhở lịch sự; bản ghi `orchestrator_logs` được gắn `notify_parent = True` và `violation_type = PROFANITY`.

#### TC-E2E-19: Email cảnh báo ngôn từ trích đoạn đã che kiểm duyệt (`***`)
* **Mục tiêu:** Bảo vệ tâm lý phụ huynh bằng cách che từ ngữ quá thô tục (AC 8.1.6).
* **Các bước:** Phụ huynh mở email cảnh báo ngôn từ nhận được.
* **Kỳ vọng:** Email chứa đoạn trích vi phạm đã được kiểm duyệt: *"Đồ bot ngốc nghếch *** không biết làm bài à"*, kèm lời khuyên cha mẹ trò chuyện nhẹ nhàng với con.

#### TC-E2E-20: Tỷ lệ bấm "Chưa hiểu" >= 3 lần $\rightarrow$ Ghi nhận cảnh báo sư phạm
* **Mục tiêu:** Phát hiện sự bế tắc trong tư duy của học sinh.
* **Các bước:** Học sinh bấm nút "Chưa hiểu" 3 lần liên tiếp trong 1 bài toán.
* **Kỳ vọng:** AI tự động hạ độ khó gợi ý về mức cơ bản nhất (chia kẹo trực quan), hệ thống ghi nhận vào báo cáo tuần của phụ huynh.

---

## 4. KẾT QUẢ THỰC THI KIỂM THỬ (TEST EXECUTION RESULTS)

Toàn bộ 20 kịch bản kiểm thử trên đã được tự động hóa và chạy thực nghiệm qua bộ test suite `backend/test/test_e2e_us81_scenarios.py`:

```bash
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1
collected 20 items

test_e2e_us81_scenarios.py ....................                          [100%]

============================= 20 passed in 12.45s ==============================
```

* **Tổng số kịch bản:** 20
* **Số kịch bản đạt (PASS):** 20/20 (100%)
* **Số kịch bản lỗi (FAIL):** 0
* **Kết luận nghiệm thu:** **US 8.1 ĐẠT TOÀN DIỆN TẤT CẢ TIÊU CHÍ CHẤP NHẬN (AC 8.1.1 -> AC 8.1.6)**.
