# KỊCH BẢN KIỂM THỬ E2E TOÀN DIỆN - TASK T9.9 (US 9.2)
# CƠ CHẾ PHẠT ĐIỂM BÀI TRÙNG (ANTI-SPAM) & ĐỒNG BỘ HUY HIỆU DATABASE

**Mã Task:** `Task #282` (Task `T9.9`) [Thiên] [QA/Review]  
**User Story:** `US 9.2: Giảm Điểm Tự Lực Khi Giải Trùng Bài (Anti-Spam) & Đồng Bộ Thành Tựu` (Sprint 9)  
**Tiêu chuẩn đối chiếu:** AC 9.2.1, AC 9.2.2, AC 9.2.3, AC 9.2.4, AC 9.2.5  
**Nguyên tắc nghiệm thu:** 100% Tiêu chí chấp nhận được kiểm thử trực tiếp trên giao diện Web (UI/UX).

---

## 📌 MÔ TẢ CÔNG VIỆC CẦN LÀM (TASK WORK DESCRIPTION)

### 1. Mục đích công việc
Là QA Lead kiêm Nhóm trưởng dự án, chịu trách nhiệm thiết kế bộ kịch bản kiểm thử E2E trên Web cho Task T9.9 thuộc US 9.2. Trực tiếp thực thi kiểm thử chuỗi thao tác giải lặp 5-10 lần cùng một đề bài toán để xác thực thuật toán phạt trần điểm tự lực (Anti-Spam Mastery), xác thực bảo toàn điểm sàn 30đ, đồng thời kiểm tra cơ chế đồng bộ danh sách huy hiệu từ Database để chặn triệt để lỗi lặp popup chúc mừng cúp khi đổi máy hoặc dùng tab ẩn danh.

### 2. Chi tiết các đầu việc thực hiện (Work Breakdown)
1. **Thiết kế ma trận kiểm thử E2E (Test Design):**
   - Xây dựng 10 test cases bao phủ toàn diện 5 tiêu chí chấp nhận (AC 9.2.1 $\rightarrow$ AC 9.2.5).
   - Thiết kế kịch bản giải liên tục 1 đề bài 5 lần kiểm tra thanh điểm giảm dần: $100 \rightarrow 90 \rightarrow 80 \rightarrow 70 \rightarrow 60$ điểm.
   - Thiết kế kịch bản thử nghiệm cày spam bài 10 lần liên tiếp để nghiệm thu điểm sàn an toàn 30đ (AC 9.2.2).
   - Thiết kế kịch bản kiểm tra số lượng "Tổng bài hoàn thành" vẫn nhảy $+1$ đều đặn sau mỗi lần bấm "Đã hiểu" (AC 9.2.3).
   - Thiết kế kịch bản kiểm thử đa thiết bị / tab ẩn danh (Incognito Mode) để xác thực popup cúp "Tự Lập Nhí" chỉ xuất hiện duy nhất 1 lần đầu tiên trong đời (AC 9.2.4).
   - Thiết kế kịch bản kiểm tra trang Kho Huy hiệu / Hồ sơ cá nhân: các huy hiệu đã mở khóa đều sáng màu (Active), các huy hiệu chưa đạt hiển thị màu xám (AC 9.2.5).

2. **Thực thi kiểm thử chức năng trên Web (E2E Web Execution):**
   - Đăng nhập tài khoản học sinh, thực hiện giải bài toán mẫu (VD: *"Tìm x biết 2x + 6 = 16"*).
   - Bấm nút "Đã hiểu" lần 1 $\rightarrow$ Ghi nhận 100đ trọn vẹn và bung modal huy hiệu "Tự Lập Nhí" $\rightarrow$ Đóng modal.
   - Gửi lại bài toán trên lần 2, lần 3, lần 4, lần 5 $\rightarrow$ Quan sát thanh tiến trình `MasteryProgressBar` và tooltip cảnh báo *"Bài giải lại, điểm tối đa là Xđ"*.
   - Mở cửa sổ ẩn danh Chrome (`Ctrl + Shift + N`), đăng nhập lại tài khoản trên $\rightarrow$ Giải tiếp bài toán $\rightarrow$ Xác nhận không bị bung lại popup cúp chúc mừng.
   - Mở kho huy hiệu $\rightarrow$ Kiểm tra trạng thái đồng bộ từ PostgreSQL.

3. **Review Pull Request & Đánh giá Code (Code Review):**
   - **Backend (PR #205 - Thống):** Rà soát công thức phạt `max_score = max(30, 100 - (repeat_count - 1) * 10)` trong `backend/routers/independence.py`, đồng bộ điểm sàn 30đ tại `backend/agents/independence_evaluator.py`, bảng `user_unlocked_badges` và API unlock badges.
   - **Frontend (PR #206 - Bảo):** Rà soát `frontend/lib/badgeStorage.ts`, hàm `migrateLocalStorageBadgesToDB`, cờ `celebrated = true` và các BFF routes proxy `/api/user/badges`.

4. **Tổng kết & Bàn giao:**
   - Biên soạn tài liệu `docs/TEST_SCENARIOS_T9.9_US9.2_ANTI_SPAM_BADGES.md`.
   - Cập nhật kết quả nghiệm thu và nghiệm thu đóng Task #282.

---

## 2. MA TRẬN 10 KỊCH BẢN KIỂM THỬ (TEST MATRIX)

| STT | Mã TestCase | Tên Tình Huống Kiểm Thử | Tiêu Chuẩn AC | Phân Loại |
|:---:|:---:|---|:---:|:---:|
| 1 | **TC-T99-01** | Lần 1: Giải bài toán mới hoàn toàn không dùng gợi ý $\rightarrow$ Đạt trọn vẹn 100/100đ | AC 9.2.1 | Happy Path |
| 2 | **TC-T99-02** | Lần 2: Giải lại bài cũ lần 1 $\rightarrow$ Áp dụng trần 90đ & hiện thông báo bài giải lại | AC 9.2.1 | Anti-Spam |
| 3 | **TC-T99-03** | Lần 3: Giải lại bài cũ lần 2 $\rightarrow$ Áp dụng trần 80đ | AC 9.2.1 | Anti-Spam |
| 4 | **TC-T99-04** | Lần 4 & Lần 5: Tiếp tục giải lại $\rightarrow$ Thanh điểm giảm dần xuống 70đ và 60đ | AC 9.2.1 | Regression |
| 5 | **TC-T99-05** | Spam giải lại bài cũ 10 lần liên tiếp $\rightarrow$ Bảo toàn điểm sàn tối thiểu 30đ | AC 9.2.2 | Edge Case |
| 6 | **TC-T99-06** | Kiểm tra bộ đếm "Tổng bài đã giải" trên thanh tiến trình Mastery nhảy $+1$ đều đặn | AC 9.2.3 | Progress Bar |
| 7 | **TC-T99-07** | Đạt 100đ lần đầu $\rightarrow$ Bung modal chúc mừng huy hiệu "Tự Lập Nhí" | AC 9.2.4 | Celebration |
| 8 | **TC-T99-08** | Mở tab ẩn danh (Incognito) đăng nhập lại $\rightarrow$ Tuyệt đối KHÔNG bung lại popup cúp | AC 9.2.4 | Persistence |
| 9 | **TC-T99-09** | Kiểm tra Kho Huy hiệu: Huy hiệu đã mở khóa sáng màu (Active), chưa đạt màu xám | AC 9.2.5 | Profile UI |
| 10 | **TC-T99-10** | Tự động migrate huy hiệu cũ từ `localStorage` lên Database khi đăng nhập | AC 9.2.5 | Migration |

---

## 3. HƯỚNG DẪN CHI TIẾT CÁC BƯỚC THỰC HIỆN KIỂM THỬ

### ── NHÓM 1: CHUỖI GIẢI LẶP 5 LẦN KIỂM TRA PHẠT ĐIỂM TRẦN (AC 9.2.1) ──

#### Đề bài toán mẫu sử dụng để test:
> *"Một hình chữ nhật có chiều dài 15m, chiều rộng 10m. Tính chu vi hình chữ nhật đó."*

#### TC-T99-01: Lần 1 - Giải bài mới hoàn toàn (100đ)
* **Các bước:**
  1. Đăng nhập tài khoản học sinh (VD: `student_test_92`).
  2. Tại khung chat, nhập đề bài toán mẫu trên và bấm gửi.
  3. AI phản hồi câu hỏi gợi ý bước đầu $\rightarrow$ Học sinh trả lời chính xác: *"Chu vi bằng (15 + 10) x 2 = 50m"*.
  4. AI chúc mừng học sinh đã giải đúng.
  5. Học sinh bấm nút **"Đã hiểu"** (không bấm gợi ý hay chưa hiểu lần nào).
* **Kết quả kỳ vọng:**
  - Nhận trọn vẹn **100/100đ** điểm tự lực.
  - Thanh tiến trình Mastery góc trái trên Sidebar cập nhật điểm số mới.
  - Bung popup chúc mừng huy hiệu *"Tự Lập Nhí"* (lần đầu đạt 100đ).
  - Bấm nút **"Tiếp tục học"** để đóng modal huy hiệu.

#### TC-T99-02: Lần 2 - Giải lại đúng đề bài trên (Trần 90đ)
* **Các bước:**
  1. Mở một phiên chat mới (bấm nút "Cuộc trò chuyện mới" hoặc chat tiếp).
  2. Gửi lại đúng 100% đề bài toán mẫu ở TC-T99-01.
  3. Hoàn thành bài toán không dùng gợi ý $\rightarrow$ Bấm nút **"Đã hiểu"**.
* **Kết quả kỳ vọng:**
  - Điểm tự lực bài này đạt tối đa **90/100đ** (bị phạt 10% điểm trần).
  - Phù hiệu/thông báo hiển thị rõ: *"Điểm tự lực: 90/100 (Bài giải lại, điểm tối đa là 90đ)"*.
  - Tuyệt đối không xuất hiện lại modal chúc mừng huy hiệu "Tự Lập Nhí".

#### TC-T99-03: Lần 3 - Giải lại lần 2 (Trần 80đ)
* **Các bước:**
  1. Gửi lại đề bài trên lần thứ 3.
  2. Hoàn thành bài toán $\rightarrow$ Bấm **"Đã hiểu"**.
* **Kết quả kỳ vọng:**
  - Điểm tự lực tối đa đạt **80/100đ**.
  - Hệ thống ghi nhận mức trần 80đ chính xác.

#### TC-T99-04: Lần 4 và Lần 5 - Tiếp tục giải lại (Trần 70đ và 60đ)
* **Các bước:**
  1. Lần 4: Gửi lại đề bài $\rightarrow$ Bấm "Đã hiểu" $\rightarrow$ Điểm tối đa đạt **70/100đ**.
  2. Lần 5: Gửi lại đề bài $\rightarrow$ Bấm "Đã hiểu" $\rightarrow$ Điểm tối đa đạt **60/100đ**.
* **Kết quả kỳ vọng:**
  - Thanh điểm trên thanh tiến trình Mastery (`MasteryProgressBar`) cập nhật điểm trung bình giảm dần một cách mượt mà theo đúng công thức $100 - (N - 1) \times 10$.

---

### ── NHÓM 2: BẢO TOÀN ĐIỂM SÀN 30Đ & BỘ ĐẾM BÀI HOÀN THÀNH (AC 9.2.2 & AC 9.2.3) ──

#### TC-T99-05: Cày spam bài lặp 10 lần liên tiếp $\rightarrow$ Điểm sàn 30đ (AC 9.2.2)
* **Mục tiêu:** Chứng minh barem không phạt âm điểm hoặc về 0đ mà giữ vững sàn 30đ.
* **Các bước:**
  1. Tiếp tục gửi đề bài trên đến lần thứ 8, 9, 10.
  2. Tại lần 10, học sinh giải đúng và bấm "Đã hiểu".
* **Kết quả kỳ vọng:**
  - Theo công thức: $100 - (10 - 1) \times 10 = 10$ điểm $\rightarrow$ Hệ thống áp dụng hàm $\max(30, 10) = 30$ điểm.
  - Điểm nhận được cố định ở mức sàn **30đ**, không bị hạ thấp hơn.
  - Barem sư phạm giữa `independence_evaluator.py` và `independence.py` hoạt động đồng bộ hoàn hảo.

#### TC-T99-06: Bộ đếm "Tổng bài đã giải" vẫn nhảy +1 đều đặn (AC 9.2.3)
* **Mục tiêu:** Khuyến khích học sinh chăm chỉ ôn luyện lại bài cũ.
* **Các bước:**
  1. Trước khi bấm "Đã hiểu" ở lần thứ 4, ghi nhớ số lượng bài trên thanh Mastery (VD: đang hiển thị `3 bài xong`).
  2. Bấm "Đã hiểu" cho bài giải lại lần 4.
  3. Bấm "Đã hiểu" cho bài giải lại lần 5.
* **Kết quả kỳ vọng:**
  - Con số trên thanh Mastery nhảy lên tương ứng: `4 bài xong` $\rightarrow$ `5 bài xong`.
  - Vào trang Hồ sơ cá nhân / Dashboard Phụ huynh: Thẻ "Tổng bài hoàn thành" vẫn ghi nhận tăng đủ $+1$ bài cho mỗi lần ôn tập thành công.

---

### ── NHÓM 3: ĐỒNG BỘ HUY HIỆU DATABASE & CHẶN POPUP TAB ẨN DANH (AC 9.2.4 & AC 9.2.5) ──

#### TC-T99-07: Lần đầu đạt huy hiệu "Tự Lập Nhí" bung modal chúc mừng (AC 9.2.4)
* **Các bước:**
  1. Với tài khoản mới tinh, giải bài đầu tiên đạt 100đ.
* **Kết quả kỳ vọng:**
  - Bung modal huy hiệu *"Tự Lập Nhí"* với hiệu ứng ăn mừng pháo hoa / icon cúp vàng.
  - Backend gọi API `POST /api/user/badges/unlock` lưu bản ghi vào bảng `user_unlocked_badges`.

#### TC-T99-08: Mở tab ẩn danh (Incognito) đăng nhập lại $\rightarrow$ Không popup lặp (AC 9.2.4)
* **Mục tiêu:** Nghiệm thu dứt điểm lỗi lặp popup phiền hà khi đổi thiết bị hoặc mở tab ẩn danh.
* **Các bước:**
  1. Mở cửa sổ trình duyệt ẩn danh (Incognito Mode / InPrivate).
  2. Truy cập `http://localhost:3000`, đăng nhập bằng tài khoản `student_test_92` đã đạt cúp ở trên.
  3. Vào phòng chat `/dashboard/chat`.
  4. Thực hiện giải một bài toán bất kỳ và bấm "Đã hiểu".
* **Kết quả kỳ vọng:**
  - Hệ thống tự động gọi `initBadgeSession()` đồng bộ danh sách badge từ Database máy chủ về và đánh dấu cờ `celebrated = true`.
  - Khi hoàn thành bài toán, **TUYỆT ĐỐI KHÔNG xuất hiện lại popup chúc mừng cúp "Tự Lập Nhí"**.

#### TC-T99-09: Kiểm tra hiển thị chuẩn trong Kho Huy hiệu (AC 9.2.5)
* **Các bước:**
  1. Vào menu mở popup/trang Kho Huy hiệu.
* **Kết quả kỳ vọng:**
  - Huy hiệu "Tự Lập Nhí" hiển thị **sáng màu (Active)**, kèm ngày giờ mở khóa chính xác.
  - Các huy hiệu khác chưa mở khóa vẫn hiển thị **màu xám / viền mờ (Locked)**.

#### TC-T99-10: Tự động migrate huy hiệu cũ từ `localStorage` lên Database (AC 9.2.5)
* **Các bước:**
  1. Mở DevTools Console (`F12`), giả lập tạo một badge cũ trong `localStorage`:
     ```javascript
     localStorage.setItem("socratic_unlocked_badges_student_test_92", JSON.stringify({
       "streak_3_days": { unlockedAt: new Date().toISOString(), celebrated: true }
     }));
     ```
  2. Đăng xuất và đăng nhập lại vào tài khoản `student_test_92`.
* **Kết quả kỳ vọng:**
  - Hàm `migrateLocalStorageBadgesToDB()` trong `badgeStorage.ts` tự động phát hiện và gửi request đồng bộ lên `POST /api/user/badges/unlock`.
  - Bản ghi `streak_3_days` được lưu vĩnh viễn vào DB PostgreSQL mà không gây xung đột.

---

## 4. KẾT LUẬN & ĐÁNH GIÁ REVIEW PR

* **Thuật toán Anti-Spam:** Hoạt động chính xác theo barem $100 - (N - 1) \times 10$, điểm sàn 30đ bảo vệ tâm lý học sinh không bị ức chế.
* **Đồng bộ hóa Cloud:** Giải quyết triệt để vấn đề phụ thuộc `localStorage` cục bộ, huy hiệu đi theo tài khoản trên mọi thiết bị.
* **Độ bao phủ nghiệm thu:** 10/10 kịch bản kiểm thử thao tác trực tiếp trên trình duyệt Web đạt kết quả như thiết kế, đủ điều kiện phê duyệt hoàn thành Task T9.9 và đóng Task #282.

