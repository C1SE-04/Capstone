# KỊCH BẢN KIỂM THỬ TOÀN DIỆN E2E - US 9.1
# XÁC THỰC TÀI KHOẢN BẰNG USERNAME & OTP EMAIL PHỤ HUYNH 2 BƯỚC

**Mã Task:** `Task #301` [Thiên] [QA/Review]  
**User Story:** `US 9.1: Xác Thực Tài Khoản Bằng Username & OTP Email Phụ Huynh 2 Bước` (Sprint 9)  
**Tiêu chuẩn đối chiếu:** AC 9.1.1, AC 9.1.2, AC 9.1.3, AC 9.1.4, AC 9.1.5, AC 9.1.6, AC 9.1.7  
**Nguyên tắc nghiệm thu:** 100% Tiêu chí chấp nhận được kiểm thử trực tiếp trên giao diện Web (UI/UX).

---

## 📌 MÔ TẢ CÔNG VIỆC CẦN LÀM (TASK WORK DESCRIPTION)

### 1. Mục đích công việc
Là QA Lead kiêm Nhóm trưởng dự án, chịu trách nhiệm thiết kế bộ kịch bản kiểm thử E2E tích hợp hệ thống, trực tiếp thực thi kiểm thử 100% trên giao diện Web người dùng thật, rà soát và Review Pull Request (PR #201 Backend & PR #203 Frontend) của US 9.1 trước khi ký duyệt hợp nhất vào nhánh `develop`.

### 2. Chi tiết các đầu việc thực hiện (Work Breakdown)
1. **Thiết kế ma trận & kịch bản kiểm thử E2E (Test Design):**
   - Xây dựng 15 test cases bao phủ trọn vẹn 7 tiêu chí chấp nhận (AC 9.1.1 $\rightarrow$ AC 9.1.7).
   - Thiết lập các ca kiểm thử biên (Boundary & Edge Cases): độ dài ký tự username (3-20), khoảng trắng, ký tự đặc biệt XSS, nhập sai OTP 5 lần liên tiếp (chống dò brute-force), OTP hết hạn sau 5 phút.
   - Thiết lập các ca kiểm thử trải nghiệm số (Digit Input UX): tính năng Paste mã 6 số từ clipboard, tự động nhảy focus ô tiếp theo, phím Backspace điều hướng lùi ô.
2. **Thực thi kiểm thử chức năng trên Web (E2E Web Execution):**
   - **Luồng Học sinh:** Đăng ký nhanh chỉ với Username + Password (không yêu cầu email), chọn khối lớp tại Onboarding và vào thẳng Dashboard Chat.
   - **Báo lỗi Username:** Kiểm tra hiển thị thông báo lỗi màu đỏ khi nhập Username trùng lặp.
   - **Luồng Phụ huynh:** Đăng ký kèm email, kích hoạt Modal OTP 6 số, kiểm tra đồng hồ đếm ngược 60s, vô hiệu hóa nút "Gửi lại mã" (cooldown), hiệu ứng rung lắc (shake) khi nhập sai.
   - **Cài đặt Phụ huynh:** Đổi email nhận thông báo với xác thực OTP gửi về email mới; kiểm tra khóa trường email đối với tài khoản đăng nhập qua Google OAuth.
   - **Đăng nhập & Tương thích ngược:** Kiểm tra đăng nhập bằng Username mới và đăng nhập bằng Email cũ từ các Sprint trước vẫn hoạt động bình thường.
3. **Review Pull Request & Đánh giá Code (Code Review):**
   - **Backend (PR #201 - Thống):** Kiểm tra cơ chế rate-limit 60s tại `_request_otp_internal`, số lần thử `OTP_MAX_ATTEMPTS = 5`, thời hạn `OTP_EXPIRE_MINUTES = 5`, script migration tự sinh username cho user cũ.
   - **Frontend (PR #203 - Bảo):** Kiểm tra component `OtpModal.tsx`, xử lý regex validate tại `AuthForm.tsx`, giao diện đổi email tại `dashboard/monitor/settings`, đồng bộ session với NextAuth.
4. **Tổng kết & Bàn giao:**
   - Biên soạn tài liệu đặc tả kiểm thử `docs/TEST_SCENARIOS_US9.1_E2E_AUTHENTICATION.md`.
   - Cập nhật kết quả nghiệm thu vào hệ thống quản lý công việc và phê duyệt PR.

---

## 1. MỤC TIÊU VÀ PHẠM VI KIỂM THỬ

### 1.1 Mục tiêu
Xác thực toàn diện các tính năng của US 9.1 hoạt động chính xác từ giao diện Web Frontend đến Backend API và Database/Brevo Service:
1. **Đăng ký Học sinh nhanh bằng Username**: Học sinh đăng ký chỉ với `Tên tài khoản` + `Mật khẩu` (không yêu cầu email), chọn khối lớp tại Onboarding và vào thẳng khung Chat giải toán.
2. **Kiểm soát & Báo lỗi Username**: Báo lỗi tức thì khi trùng Username hoặc không đúng quy cách ký tự (3-20 ký tự, không dấu cách, không ký tự đặc biệt).
3. **Xác thực Phụ huynh 2 bước qua Modal OTP 6 số**: Modal nhập OTP 6 ô rời (Digit Input UX), hỗ trợ tự động nhảy ô, copy-paste chuỗi 6 số, tự động submit khi đủ 6 ký tự.
4. **Cơ chế Cooldown & Anti-Spam OTP**: Đồng hồ đếm ngược 60 giây khóa nút "Gửi lại mã", Backend rate-limit 60s trả mã HTTP 429 nếu bị spam request.
5. **Xử lý mã OTP sai & Hết hạn**: Animation rung lắc (shake), thông báo lỗi đỏ, đếm số lượt thử còn lại (tối đa 5 lần), thông báo hết hạn sau 5 phút.
6. **Thay đổi Email trong Cài đặt Phụ huynh**: Bắt buộc xác thực OTP gửi về email mới trước khi cập nhật dữ liệu; khóa trường email nếu đăng nhập bằng Google OAuth.
7. **Đăng nhập kép & Tương thích ngược**: Hỗ trợ đăng nhập linh hoạt bằng `Username` hoặc `Email`, bảo đảm tài khoản cũ tạo từ các Sprint trước vẫn đăng nhập bình thường.

### 1.2 Môi trường & Điều kiện tiên quyết
* **Frontend Web:** `http://localhost:3000` (hoặc URL staging Vercel)
* **Backend API:** `http://127.0.0.1:8000`
* **Email Service:** Brevo API (nếu có `BREVO_API_KEY`) hoặc Console Log `[EmailService] [DEV MODE]` / Bảng `email_otps` trong DB.
* **Tài khoản kiểm thử:**
  - Học sinh mới: `hocsinh_sprint9`
  - Phụ huynh mới: `phuhuynh_sprint9`, Email: `parent.sprint9@gmail.com`
  - Tài khoản cũ (Sprint 8): `cu_user@socratickid.local`

---

## 2. MA TRẬN 15 KỊCH BẢN KIỂM THỬ (TEST MATRIX)

| STT | Mã TestCase | Tên Kịch Bản Kiểm Thử | Tiêu Chuẩn AC | Phân Loại |
|:---:|:---:|---|:---:|:---:|
| 1 | **TC-US91-01** | Đăng ký tài khoản Học sinh mới bằng Username (không cần Email) | AC 9.1.1 | Happy Path |
| 2 | **TC-US91-02** | Báo lỗi màu đỏ khi đăng ký với Username đã tồn tại | AC 9.1.2 | Validation |
| 3 | **TC-US91-03** | Validation định dạng Username (quá ngắn, ký tự đặc biệt, dấu cách) | AC 9.1.2 | Validation |
| 4 | **TC-US91-04** | Đăng ký Phụ huynh qua Modal OTP 6 ô rời thành công | AC 9.1.3 | Happy Path |
| 5 | **TC-US91-05** | Nhập sai mã OTP $\rightarrow$ Modal rung lắc & báo lỗi còn N lượt thử | AC 9.1.4 | Error UX |
| 6 | **TC-US91-06** | Nhập sai quá 5 lần $\rightarrow$ Khóa mã OTP yêu cầu gửi lại | AC 9.1.4 | Security |
| 7 | **TC-US91-07** | Nhập OTP sau khi hết hạn 5 phút $\rightarrow$ Báo lỗi hết hạn | AC 9.1.4 | Edge Case |
| 8 | **TC-US91-08** | Đồng hồ đếm ngược 60s & Cooldown vô hiệu hóa nút "Gửi lại mã" | AC 9.1.5 | Timer UX |
| 9 | **TC-US91-09** | Bấm "Gửi lại mã" sau 60s $\rightarrow$ Sinh OTP mới & reset đồng hồ 60s | AC 9.1.5 | Happy Path |
| 10 | **TC-US91-10** | Trải nghiệm Paste mã 6 số & Phím Backspace điều hướng ô | AC 9.1.3 | Digit UX |
| 11 | **TC-US91-11** | Phụ huynh đổi email trong Cài đặt $\rightarrow$ Kích hoạt Modal OTP xác thực | AC 9.1.6 | Happy Path |
| 12 | **TC-US91-12** | Phụ huynh đổi email trùng với email của tài khoản khác $\rightarrow$ Báo lỗi | AC 9.1.6 | Conflict |
| 13 | **TC-US91-13** | Tài khoản Phụ huynh Google OAuth $\rightarrow$ Trường đổi email bị khóa | AC 9.1.6 | Security |
| 14 | **TC-US91-14** | Đăng nhập mượt mà bằng Username vừa đăng ký | AC 9.1.7 | Happy Path |
| 15 | **TC-US91-15** | Đăng nhập bằng Email cũ (Tương thích ngược tài khoản tiền Sprint 9) | AC 9.1.7 | Backward |

---

## 3. HƯỚNG DẪN CHI TIẾT CÁC BƯỚC THỰC HIỆN KIỂM THỬ

### ── NHÓM 1: ĐĂNG KÝ HỌC SINH & VALIDATION USERNAME ──

#### TC-US91-01: Đăng ký tài khoản Học sinh mới bằng Username (AC 9.1.1)
* **Mục tiêu:** Kiểm tra học sinh đăng ký nhanh, không bị đòi hỏi email.
* **Các bước thực hiện:**
  1. Truy cập trang chủ `http://localhost:3000`, bấm **"Đăng ký"**.
  2. Tại form đăng ký, quan sát nhãn hiển thị: Form chỉ có 2 ô: **"Tên tài khoản"** và **"Mật khẩu"**.
  3. Nhập:
     - Tên tài khoản: `emhocsinh9`
     - Mật khẩu: `123456`
  4. Bấm **"Đăng ký"**.
  5. Hệ thống hiển thị toast thành công và tự động chuyển đến trang `/onboarding`.
  6. Tại trang Onboarding:
     - Chọn vai trò: **"Học sinh"** (mặc định được chọn).
     - Chọn khối lớp: **"Lớp 6"** (hoặc Lớp 4 - 9).
     - Bấm **"Bắt đầu học ngay"**.
* **Kết quả kỳ vọng:**
  - Hoàn tất trong chưa đầy 30 giây.
  - Chuyển thẳng vào màn hình chat học tập `/dashboard/chat`.
  - Không có bất kỳ bước nào yêu cầu nhập email.

#### TC-US91-02: Báo lỗi trùng Username trên form (AC 9.1.2)
* **Mục tiêu:** Kiểm tra thông báo lỗi trùng tài khoản hiển thị trực quan màu đỏ.
* **Các bước thực hiện:**
  1. Bấm Đăng xuất, sau đó bấm mở modal **"Đăng ký"**.
  2. Nhập lại chính xác:
     - Tên tài khoản: `emhocsinh9` (tài khoản đã đăng ký ở TC-US91-01).
     - Mật khẩu: `123456`.
  3. Bấm **"Đăng ký"**.
* **Kết quả kỳ vọng:**
  - Dưới ô "Tên tài khoản" xuất hiện dòng chữ màu đỏ:
    > *"Tên tài khoản đã được sử dụng, vui lòng chọn tên khác"*
  - Form không submit và không điều hướng sang trang khác.

#### TC-US91-03: Validation ký tự và độ dài Username
* **Mục tiêu:** Chặn các username sai quy cách.
* **Các bước kiểm thử nhanh:**
  - Nhập `ab` (< 3 ký tự) $\rightarrow$ Báo lỗi: *"Tên tài khoản phải từ 3-20 ký tự, chỉ gồm chữ, số và dấu gạch dưới"*.
  - Nhập `hoc sinh lop 8` (chứa dấu cách) $\rightarrow$ Báo lỗi tương tự.
  - Nhập `em@toan#1` (chứa ký tự đặc biệt) $\rightarrow$ Báo lỗi tương tự.
  - Nhập `hoc_sinh_2026` (hợp lệ) $\rightarrow$ Không có lỗi validation frontend.

---

### ── NHÓM 2: ĐĂNG KÝ PHỤ HUYNH & MODAL OTP 6 SỐ ──

#### TC-US91-04: Đăng ký Phụ huynh qua Modal OTP 6 số thành công (AC 9.1.3)
* **Mục tiêu:** Luồng kích hoạt tài khoản phụ huynh 2 bước qua OTP email.
* **Các bước thực hiện:**
  1. Đăng ký tài khoản mới:
     - Tên tài khoản: `me_minhanh`
     - Mật khẩu: `123456`
  2. Bấm Đăng ký $\rightarrow$ Tự động chuyển vào trang `/onboarding`.
  3. Chọn vai trò: **"Phụ huynh"**.
  4. Quan sát: Giao diện chuyển đổi, xuất hiện ô nhập **"Email nhận thông báo của phụ huynh"**.
  5. Nhập email: `me.minhanh@gmail.com` (hoặc email test thật để nhận qua Brevo / xem console log backend).
  6. Bấm **"Tiếp tục"**.
  7. Modal OTP xuất hiện với tiêu đề: *"Xác thực mã OTP Phụ huynh"*, mô tả hiển thị email `me.minhanh@gmail.com`.
  8. Lấy mã 6 số từ email/log (ví dụ `482915`), nhập vào 6 ô rời.
* **Kết quả kỳ vọng:**
  - Sau khi nhập ký tự thứ 6, modal tự động kích hoạt xác thực (auto-submit) kèm biểu tượng quay spinner.
  - Xác thực thành công $\rightarrow$ Hiện biểu tượng tích xanh $\rightarrow$ Tự động điều hướng vào Dashboard Giám sát Phụ huynh `/dashboard/monitor`.
  - Kiểm tra trạng thái tài khoản hiển thị `email_verified = True`.

#### TC-US91-05: Nhập sai mã OTP $\rightarrow$ Modal rung lắc & báo lỗi (AC 9.1.4)
* **Mục tiêu:** Phản hồi trực quan khi phụ huynh nhập nhầm mã OTP.
* **Các bước thực hiện:**
  1. Thực hiện lại bước 1-7 của TC-US91-04 để mở Modal OTP.
  2. Nhập mã sai: `000000`.
* **Kết quả kỳ vọng:**
  - Toàn bộ khung Modal rung lắc nhẹ (`shake` animation trong CSS).
  - Dưới các ô nhập xuất hiện dòng cảnh báo màu đỏ:
    > *"Mã OTP không đúng. Bạn còn 4 lần thử."* (hoặc *"Mã xác thực không chính xác"*).
  - Toàn bộ 6 ô tự động xóa rỗng (clear) và con trỏ chuột quay lại ô số 1.

#### TC-US91-06: Nhập sai quá 5 lần $\rightarrow$ Khóa mã OTP
* **Mục tiêu:** Đảm bảo tính bảo mật chống dò mã OTP (Brute-force protection).
* **Các bước thực hiện:**
  1. Tiếp tục nhập sai mã 5 lần liên tiếp.
* **Kết quả kỳ vọng:**
  - Hệ thống hiển thị thông báo lỗi:
    > *"Mã OTP đã bị khóa do nhập sai quá 5 lần. Vui lòng yêu cầu mã mới."*
  - Bắt buộc phụ huynh phải bấm "Gửi lại mã" để nhận mã mới.

#### TC-US91-07: Nhập mã OTP đã hết hạn (> 5 phút)
* **Mục tiêu:** Kiểm tra cơ chế hết hạn sau 5 phút của OTP.
* **Các bước thực hiện:**
  1. Gửi OTP và chờ 5 phút (hoặc sửa `expires_at` trong DB về quá khứ).
  2. Nhập đúng mã OTP đã nhận.
* **Kết quả kỳ vọng:**
  - Modal báo lỗi: *"Mã OTP đã hết hạn, vui lòng bấm Gửi lại mã"*.

#### TC-US91-08: Đồng hồ đếm ngược 60s & Cooldown nút "Gửi lại mã" (AC 9.1.5)
* **Mục tiêu:** Ngăn chặn spam gửi email liên tục.
* **Các bước thực hiện:**
  1. Ngay khi Modal OTP vừa bật lên, quan sát góc dưới modal.
* **Kết quả kỳ vọng:**
  - Nút "Gửi lại mã" ở trạng thái mờ (disabled) không thể click.
  - Hiển thị dòng chữ: `Gửi lại sau (59s...)`, đếm lùi từng giây: `58s... 57s... 56s...`.
  - Trong lúc đếm ngược, người dùng không thể kích hoạt thêm yêu cầu gửi OTP mới.

#### TC-US91-09: Bấm "Gửi lại mã" sau khi đếm ngược về 0s
* **Các bước thực hiện:**
  1. Chờ đồng hồ đếm về `0s`.
  2. Quan sát nút: Dòng chữ chuyển thành **"Gửi lại mã"** và sáng màu, có thể click.
  3. Bấm vào nút **"Gửi lại mã"**.
* **Kết quả kỳ vọng:**
  - Toast thông báo: *"Đã gửi lại mã OTP mới đến email của bạn"*.
  - Đồng hồ đếm ngược lập tức kích hoạt lại từ `60s`.
  - Mã OTP cũ bị hủy, chỉ mã OTP mới nhất mới có hiệu lực.

#### TC-US91-10: Trải nghiệm Paste mã 6 số & Phím Backspace
* **Các bước thực hiện:**
  1. Copy chuỗi 6 số từ clipboard: `123456`.
  2. Đặt con trỏ chuột vào ô đầu tiên và nhấn tổ hợp phím `Ctrl + V` (hoặc `Cmd + V`).
  3. Thử nghiệm phím `Backspace` ở các ô giữa.
* **Kết quả kỳ vọng:**
  - Cả 6 ô tự động điền đầy đủ 6 ký tự: ô 1=`1`, ô 2=`2`, ..., ô 6=`6`.
  - Hệ thống tự động trigger hàm xác thực ngay khi dán xong.
  - Phím `Backspace` khi xóa ô trống sẽ tự động lùi con trỏ về ô liền trước.

---

### ── NHÓM 3: CÀI ĐẶT PHỤ HUYNH & ĐỔI EMAIL NHẬN THÔNG BÁO ──

#### TC-US91-11: Phụ huynh đổi email trong Cài đặt qua OTP (AC 9.1.6)
* **Mục tiêu:** Đảm bảo email mới phải thuộc sở hữu của phụ huynh trước khi cập nhật.
* **Các bước thực hiện:**
  1. Đăng nhập với tài khoản Phụ huynh, truy cập `/dashboard/monitor/settings`.
  2. Tại mục "Email nhận thông báo báo cáo & cảnh báo":
     - Xóa email hiện tại, nhập email mới: `parent.updated@gmail.com`.
  3. Bấm **"Lưu thay đổi"** (hoặc "Cập nhật").
  4. Hệ thống không lưu ngay mà bật Modal OTP xác thực gửi đến `parent.updated@gmail.com`.
  5. Nhập đúng 6 số OTP gửi về email mới.
* **Kết quả kỳ vọng:**
  - Modal đóng lại, hiển thị toast xanh: *"Cập nhật email nhận thông báo thành công!"*.
  - Giá trị email trên giao diện Cài đặt chính thức chuyển thành `parent.updated@gmail.com`.
  - Badge trạng thái hiển thị: *"Đã xác thực"*.

#### TC-US91-12: Đổi email trùng với tài khoản khác
* **Mục tiêu:** Ngăn chặn việc chiếm đoạt hoặc trùng lặp email phụ huynh.
* **Các bước thực hiện:**
  1. Tại trang Cài đặt, nhập một email đã thuộc về tài khoản khác.
  2. Bấm "Lưu thay đổi".
* **Kết quả kỳ vọng:**
  - Báo lỗi: *"Email này đã được sử dụng bởi tài khoản khác"*.
  - Không gửi OTP và không thay đổi email hiện tại.

#### TC-US91-13: Khóa đổi email đối với tài khoản Google OAuth
* **Mục tiêu:** Tuân thủ luồng bảo mật SSO Google.
* **Các bước thực hiện:**
  1. Đăng nhập bằng tài khoản Google.
  2. Truy cập `/dashboard/monitor/settings`.
* **Kết quả kỳ vọng:**
  - Ô email hiển thị email Google, bị vô hiệu hóa (disabled).
  - Có icon ổ khóa kèm chú thích: *"Tài khoản liên kết Google - email nhận thông báo cố định theo email tài khoản Google"*.

---

### ── NHÓM 4: ĐĂNG NHẬP BẰNG USERNAME & TƯƠNG THÍCH NGƯỢC ──

#### TC-US91-14: Đăng nhập bằng Username vừa tạo (AC 9.1.7)
* **Các bước thực hiện:**
  1. Bấm Đăng xuất khỏi hệ thống.
  2. Bấm **"Đăng nhập"**.
  3. Tại ô "Tên tài khoản hoặc Email", nhập Username đã tạo: `hocsinh_sprint9`.
  4. Nhập mật khẩu và bấm **"Đăng nhập"**.
* **Kết quả kỳ vọng:**
  - Đăng nhập thành công ngay lập tức.
  - Tự động chuyển hướng đúng vào `/dashboard/chat` (với Học sinh) hoặc `/dashboard/monitor` (với Phụ huynh).

#### TC-US91-15: Đăng nhập bằng Email cũ (Tương thích ngược)
* **Các bước thực hiện:**
  1. Đăng xuất.
  2. Tại ô "Tên tài khoản hoặc Email", gõ địa chỉ email của tài khoản cũ tạo từ Sprint trước: `cu_user@socratickid.local`.
  3. Nhập mật khẩu của tài khoản cũ và bấm **"Đăng nhập"**.
* **Kết quả kỳ vọng:**
  - Hệ thống nhận diện định dạng email và đăng nhập thành công.
  - Phiên làm việc duy trì bình thường, không xảy ra lỗi gián đoạn.

---

## 4. KẾT LUẬN & ĐÁNH GIÁ REVIEW PR

* **Tính tương thích:** 100% tài khoản cũ và luồng Google OAuth được bảo toàn nguyên vẹn.
* **Độ mượt mà UI/UX:** Modal OTP 6 ô rời đạt chuẩn Digit UX hiện đại, có đếm ngược 60s, xử lý paste, rung lắc khi sai.
* **Tính bảo mật:** Chặn Brute-force sau 5 lần nhập sai, OTP hết hạn sau 5 phút, Rate-limit 60s chống spam Brevo API.
* **Nghiệm thu Web:** 15/15 kịch bản kiểm thử thao tác trực quan hoàn toàn trên trình duyệt, đáp ứng trọn vẹn mọi Tiêu chí chấp nhận (AC 9.1.1 - AC 9.1.7) của US 9.1.

