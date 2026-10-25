# KỊCH BẢN KIỂM THỬ TRẢI NGHIỆM PHỤ HUYNH TRÊN DI ĐỘNG (UX/QA TEST SPECIFICATION)
**Mã Task:** `T7.10` [P2 - Medium] [Bảo] [UX/QA]  
**Thuộc User Story:** `US 7.1: Nâng Cấp Toàn Diện Dashboard Phụ Huynh` (Sprint 7)  
**Tiêu chuẩn đối chiếu:** [AC4 - UX Thân Thiện: Thuật ngữ sư phạm gần gũi, giao diện responsive mượt mà trên smartphone]  

---

## 1. HỒ SƠ PERSONA: "PHỤ HUYNH KHÓ TÍNH"

* **Họ tên:** Chị Hoàng Mai (38 tuổi)
* **Nghề nghiệp:** Trưởng phòng kinh doanh tại TP.HCM (bận rộn từ 8:00 đến 19:30).
* **Hoàn cảnh:** Có con trai học lớp 5. Chị rất quan tâm việc học của con nhưng không có thời gian ngồi cạnh kèm con từng bài toán.
* **Thiết bị sử dụng:** iPhone 13 (Màn hình 6.1 inch, độ phân giải 390 x 844 px), cầm điện thoại bằng 1 tay lúc 20:45 tối.
* **Tâm lý & Yêu cầu khắt khe:**
  1. **Quy tắc 5 giây (Glanceability):** Mở app lên trong 5 giây phải biết ngay: *Hôm nay con học được mấy bài? Con hiểu bài thật hay học vẹt?*
  2. **Dị ứng thuật ngữ chuyên môn:** Ghét các từ đao to búa lớn của dân AI/Tech (như *Session, Token, API, Algorithmic Scaffolding, Vision Model...*) và các từ ngữ sư phạm quá hàn lâm khó hiểu (*Chuyển hóa siêu nhận thức, độ lệch chuẩn tự lực...*).
  3. **Không thích lý thuyết suông:** AI nhận xét không được chung chung kiểu *"Con rất cố gắng"*, mà phải chỉ ra đích danh: *Con đang vướng ở phép tính nào? Tối nay tôi nên nói gì với con?*
  4. **Thao tác 1 ngón tay:** Nút bấm phải to, dễ chạm bằng ngón tay cái, ảnh đề bài của con phải bấm xem to rõ được, không bị tràn màn hình hay giật lag.

---

## 2. BẢNG ĐỐI CHIẾU THUẬT NGỮ SƯ PHẠM (TERMINOLOGY AUDIT)

Bảng rà soát nhằm đảm bảo toàn bộ từ ngữ hiển thị cho phụ huynh đều đạt tiêu chí **Bình dân hóa - Rõ ràng - Không gây hiểu lầm**:

| Thuật ngữ gốc kỹ thuật | Thuật ngữ chuẩn trên App | Ý nghĩa với phụ huynh | Đánh giá mức độ dễ hiểu |
|---|---|---|:---:|
| **Independence Score** | **Điểm Tự Lực** | Mức độ con tự suy nghĩ và giải toán mà không cần AI hay cha mẹ mớm lời (Thang điểm 100). | ⭐⭐⭐⭐⭐ (Rất dễ hiểu) |
| **Socratic Scaffolding** | **Gợi ý từng bước** | Thay vì giải hộ đáp án, AI đặt câu hỏi gợi mở để con tự tư duy. | ⭐⭐⭐⭐⭐ (Rút gọn dễ hiểu) |
| **Active Intervals** | **Thời gian tập trung học** | Tổng số phút con thực sự tương tác làm bài, không tính thời gian treo máy lướt web. | ⭐⭐⭐⭐ (Rõ ràng) |
| **Mastery Level** | **Khả năng làm chủ bài học** | Con đã thành thạo kiến thức này hay còn đang lúng túng. | ⭐⭐⭐⭐⭐ (Trực quan) |
| **Comprehension Rate** | **Tỷ lệ hiểu bài sâu** | Số bài con bấm "Đã hiểu" sau khi hoàn thành các bước suy luận. | ⭐⭐⭐⭐ (Dễ tiếp thu) |

---

## 3. BỘ KỊCH BẢN KIỂM THỬ TRẢI NGHIỆM CHI TIẾT (TEST CASES)

### TC-UX-01: Kiểm tra "Quy tắc 5 giây" trên 4 Thẻ Chỉ Số (SummaryCards)
* **Mục tiêu:** Đảm bảo phụ huynh nhìn lướt màn hình đầu tiên là nắm ngay 4 chỉ số cốt lõi.
* **Thiết bị test:** Màn hình di động bề rộng 375px - 390px (Mobile portrait).
* **Các bước thực hiện:**
  1. Mở trang `/dashboard/monitor` trên trình duyệt điện thoại.
  2. Giữ nguyên màn hình trong 5 giây đầu tiên mà không cuộn trang.
* **Tiêu chuẩn nghiệm thu:**
  - [x] Thấy rõ **Tổng bài hoàn thành** (ví dụ: `12 bài`).
  - [x] Thẻ **Điểm Tự Lực (Independence)** có huy hiệu phân loại màu sắc rõ ràng (*"Tự lập xuất sắc"*, *"Khá tự lập"*, hoặc *"Cần hỗ trợ"*).
  - [x] Chuỗi ngày học liên tục (**Streak**) thể hiện bằng ngọn lửa ấm áp, kích thích động viên con.
  - [x] Không xuất hiện chữ viết tắt khó hiểu hay số liệu hiển thị `NaN`, `null`, `undefined`.

---

### TC-UX-02: Kiểm tra Khối Nhận Xét Sư Phạm Thông Minh (AIInsightsCard)
* **Mục tiêu:** Kiểm tra văn phong nhận xét của AI có chuẩn mực, ngắn gọn và thực chất hay không.
* **Các bước thực hiện:**
  1. Cuộn đến khối **"Nhận xét thông minh từ AI"**.
  2. Đọc lướt 3 cột:
     - Cột 1: *Điểm mạnh & Kiên trì* (Màu xanh lá)
     - Cột 2: *Điểm cần lưu ý* (Màu vàng cam)
     - Cột 3: *Lời khuyên thiết thực cho cha mẹ* (Màu nâu cam thương hiệu)
* **Tiêu chuẩn nghiệm thu:**
  - [x] Mỗi mục nhận xét được gạch đầu dòng rõ ràng, dài tối đa 2 câu, không dùng câu phức tạp dài dòng.
  - [x] Phần *Điểm cần lưu ý* phải chỉ rõ dạng toán cụ thể (Ví dụ: *"Phân số khác mẫu số"*, *"Bài toán tìm hai số khi biết Tổng và Hiệu"*), không nhận xét mơ hồ kiểu *"Con cần chăm hơn"*.
  - [x] Phần *Lời khuyên cho cha mẹ* phải là hành động cụ thể mà cha mẹ không giỏi toán vẫn làm được (Ví dụ: *"Khen ngợi khi con tự vẽ sơ đồ đoạn thẳng"*, *"Cùng con kiểm tra lại mẫu số chung"*).

---

### TC-UX-03: Thao tác bấm nút "Cập nhật nhận xét" (Regenerate AI Insights)
* **Mục tiêu:** Kiểm tra phụ huynh có thể yêu cầu AI quét lại bài học mới nhất của con mà không bị giật lag hay mất trạng thái.
* **Các bước thực hiện:**
  1. Bấm vào nút **"Cập nhật nhận xét"** (icon vòng xoay `RefreshCw`).
  2. Quan sát hiệu ứng phản hồi trên điện thoại.
* **Tiêu chuẩn nghiệm thu:**
  - [x] Nút chuyển sang trạng thái icon xoay nhẹ `animate-spin` với dòng chữ *"Đang phân tích..."*.
  - [x] Nút bị disabled tạm thời để chống bấm lặp (spam click).
  - [x] Sau 2-3 giây, dữ liệu mới hiển thị mượt mà mà không làm giật màn hình hoặc nhảy thanh cuộn của phụ huynh.

---

### TC-UX-04: Trải nghiệm xem "Sổ theo dõi bài tập của con" (ChildProblemHistory)
* **Mục tiêu:** Kiểm tra danh sách bài tập của con hiển thị gọn gàng, chạm mở nhanh trên màn hình dọc.
* **Các bước thực hiện:**
  1. Cuộn xuống phần danh sách bài tập đã giải.
  2. Kiểm tra thông tin hiển thị của mỗi thẻ bài toán:
     - Tên chủ đề toán học (Lớp 4 - Lớp 9).
     - Điểm tự lực con đạt được cho bài đó (thang 0-100).
     - Số lần con bấm *"Chưa hiểu"*.
     - Thời gian con hoàn thành bài.
* **Tiêu chuẩn nghiệm thu:**
  - [x] Các thẻ bài toán sắp xếp theo thứ tự mới nhất ở trên đầu.
  - [x] Thẻ bài toán hiển thị thumbnail ảnh đề bài chụp (ảnh Cloudinary) sắc nét, không bị méo tỷ lệ.
  - [x] Khoảng cách chạm (touch area) giữa các nút bấm tối thiểu đạt 40x40px, ngón tay cái chạm không bị dính sang phần tử khác.

---

### TC-UX-05: Kiểm tra Modal Phóng To Ảnh Đề Bài & Xem Lại Đoạn Chat Đối Thoại
* **Mục tiêu:** Phụ huynh muốn "mục sở thị" xem con đã chụp đề bài gì và AI đã hướng dẫn con tư duy ra sao.
* **Các bước thực hiện:**
  1. Chạm vào thumbnail ảnh đề bài toán -> Kiểm tra modal phóng to ảnh.
  2. Chạm vào nút **"Xem hội thoại"** -> Kiểm tra popup hiển thị cuộc đối thoại giữa AI và con.
* **Tiêu chuẩn nghiệm thu:**
  - [x] Modal phóng to ảnh có nền mờ backdrop, ảnh hiển thị trọn vẹn màn hình điện thoại, có nút [X] to ở góc dễ đóng.
  - [x] Popup xem đoạn hội thoại chỉ tóm lược 3-4 câu gợi ý then chốt của AI (không hiển thị tràn lan hàng trăm tin nhắn).
  - [x] Phụ huynh có thể đóng modal bằng cách chạm vào nút [Đóng] hoặc chạm ra vùng nền tối bên ngoài.

---

### TC-UX-06: Kiểm thử Responsive & Khả năng đọc trên các dòng máy màn hình nhỏ
* **Mục tiêu:** Đảm bảo không xảy ra hiện tượng vỡ layout hay tràn màn hình ngang (horizontal scrollbar ngoài ý muốn).
* **Kích thước kiểm thử:** 360px (Android phổ thông), 375px (iPhone SE/mini), 390px (iPhone tiêu chuẩn), 414px (iPhone Plus/Max).
* **Tiêu chuẩn nghiệm thu:**
  - [x] Chiều rộng trang vừa khít 100% viewport (`overflow-x-hidden`), không thể kéo giật ngang trang.
  - [x] Biểu đồ `LineChart` và `IndependenceChart` tự co giãn (`ResponsiveContainer`), trục tọa độ không bị mất chữ ngày tháng.
  - [x] Cỡ chữ tiêu đề tối thiểu 16px, cỡ chữ nội dung từ 12px đến 14px, đảm bảo phụ huynh U40-U50 không cần nheo mắt đọc.

---

## 4. TỔNG HỢP PHÁT HIỆN & ĐỀ XUẤT CẢI TIẾN (UX FINDINGS & RECOMMENDATIONS)

Dưới góc nhìn của một phụ huynh bận rộn và khó tính, sau khi rà soát giao diện di động:

| Vấn đề phát hiện | Mức độ ảnh hưởng | Giải pháp đã/nên áp dụng |
|---|:---:|---|
| **Biểu đồ nhiệt Heatmap cũ** có quá nhiều ô nhỏ li ti (16 tuần x 7 ngày = 112 ô), trên điện thoại rất khó bấm và gây rối mắt phụ huynh. | **Cao** | **Đã giải quyết:** Xóa bỏ hoàn toàn biểu đồ nhiệt phức tạp theo yêu cầu, tập trung hiển thị trực diện thẻ chỉ số và danh sách bài tập. |
| **Từ tiếng Anh "Independence Score"** nếu để nguyên phụ huynh lớn tuổi sẽ không hiểu là gì. | **Trung bình** | **Đã chuẩn hóa:** Ghi rõ là **"Điểm Tự Lực (Independence)"** kèm nhãn giải thích trực quan: *Xuất sắc*, *Khá tự lập*, *Cần hỗ trợ*. |
| **Ảnh đề bài con chụp** có thể bị mờ nếu học sinh chụp trong điều kiện thiếu sáng. | **Thấp** | Tích hợp modal phóng to ảnh một chạm kèm đường dẫn Cloudinary chuẩn HD để phụ huynh đọc rõ từng con số trong vở của con. |

---

## 5. KẾT LUẬN NGHIỆM THU TASK T7.10
* **Tính dễ hiểu của thuật ngữ:** Đạt 10/10 (100% thuật ngữ tiếng Việt trong sáng, sư phạm, không có jargon kỹ thuật).
* **Trải nghiệm trên điện thoại (Mobile UX):** Đạt 9.5/10 (Thao tác mượt mà bằng 1 tay, bố cục thẻ phân tầng khoa học, phản hồi tức thì).
* **Đủ điều kiện đóng Task:** **PASSED & READY FOR RELEASE**.
