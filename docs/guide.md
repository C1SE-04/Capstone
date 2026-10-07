# Hướng Dẫn Task T5.24 – Analogical Scaffolding (US 5.3)

**Thuộc:** US 5.3 – Sprint 5
**Người thực hiện:** [Thông] – AI Engineer
**Ước tính:** 2h

---

## 0. 🌿 Chuẩn bị Branch

Do bạn vừa gặp sự cố dính commit cũ ở task trước, nên lần này hãy đảm bảo làm đúng thứ tự sau để tạo một branch hoàn toàn sạch sẽ từ `develop` (hoặc `dev` tùy tên nhánh gốc của team bạn):

```bash
git checkout develop
git pull origin develop
git checkout -b feat/us5.3-analogical-scaffolding
```

---

## 1. 🎯 Mục tiêu

Khi học sinh gõ các cụm từ như **"cho em xin ví dụ"**, **"làm mẫu cho em"**, **"em không hiểu"**, AI phải:

1. **Tự đặt ra** một bài toán có cấu trúc giống hệt bài gốc nhưng **đổi số và đổi bối cảnh**.
2. **Giải chi tiết từng bước** bài mẫu vừa tự đặt ra đó.
3. **Cuối phản hồi**: mời học sinh áp dụng cách làm vào bài toán gốc của chính mình.
4. **Tuyệt đối KHÔNG** vô tình giải hoặc tiết lộ đáp án của bài toán gốc.

---

## 2. 📁 File cần sửa

Chỉ cần sửa **duy nhất 1 file**:

```
backend/agents/agent_prompts.py
```

---

## 3. 🔧 Cách sửa

**Mở file:** `backend/agents/agent_prompts.py`

**Tìm đến phần `─── NGUYÊN TẮC SƯ PHẠM BẮT BUỘC (ÁP DỤNG CHO MỌI AGENT) ───`** (khoảng dòng 217). Chúng ta sẽ chèn kỹ thuật Analogical Scaffolding vào phần quy tắc chung này để MỌI agent (kể cả SAFETY) đều biết cách xử lý khi học sinh đòi ví dụ.

**Thêm đoạn sau vào CÚNG CUỐI của danh sách nguyên tắc:**

```text
• ─── KỸ THUẬT BÀI MẪU TƯƠNG TỰ (ANALOGICAL SCAFFOLDING) ───
  KÍCH HOẠT khi học sinh xin ví dụ (bao gồm cả các từ viết tắt, lóng như 'vd đi', 'khum hỉu'), yêu cầu làm mẫu, hoặc tỏ ra bế tắc không biết làm tiếp:
  1. PHÂN LOẠI NGỮ CẢNH BẮT BUỘC:
     - Nếu học sinh đang hỏi LÝ THUYẾT (VD: phân số là gì): KHÔNG sinh bài toán mẫu. Hãy đưa ra ví dụ thực tế đơn giản và hỏi ngược lại để kiểm tra mức độ hiểu của học sinh.
     - Nếu học sinh đang làm BÀI TOÁN TÍNH TOÁN: Chuyển sang bước 2.
  2. TỰ ĐẶT BÀI TOÁN MỚI: Giữ nguyên cấu trúc toán học của bài gốc nhưng THAY TOÀN BỘ con số và bối cảnh (tuyệt đối đổi tên biến, VD: đổi x sang y).
  3. GIẢI CHI TIẾT bài mẫu vừa đặt ra từng bước một.
  4. KẾT THÚC bằng câu mời: 'Bây giờ em áp dụng cách làm này vào bài toán của mình thử xem nhé?'
  5. TUYỆT ĐỐI KHÔNG: Dùng lại đúng con số của bài gốc hoặc vô tình giải lộ đáp án bài gốc.
  
  [VÍ DỤ MẪU CHO AI CẦN HỌC THEO - CHỈ DÙNG CHO BÀI TẬP TÍNH TOÁN]
  - Bài gốc của học sinh: Tìm x, biết 2x + 5 = 15.
  - Học sinh nói: "Thầy cho em 1 vd đi".
  - PHẢN HỒI CHUẨN MÀ BẠN PHẢI BẮT CHƯỚC:
    "Được thôi, thầy lấy một bài toán tương tự nhé. Giả sử ta cần tìm y trong bài: 3y + 4 = 16.
    Bước 1: Ta chuyển 4 sang vế phải: 3y = 16 - 4, suy ra 3y = 12.
    Bước 2: Ta chia cả hai vế cho 3: y = 12 / 3, suy ra y = 4.
    Đó, cách làm là như vậy. Bây giờ em thử áp dụng các bước chuyển vế này vào bài 2x + 5 = 15 của em xem nhé!"
```

---

## 4. ✅ Kiểm Tra (Acceptance Criteria)

Dùng Postman hoặc trực tiếp giao diện chat, giả lập 4 kịch bản "hardcore" sau:

| # | Kịch bản | Kết quả mong đợi |
|---|---|---|
| **AC1 (Slang)** | Học sinh đang kẹt bài tìm x, gõ **"cho 1 vd đi"** | AI vẫn hiểu và sinh bài mẫu tương tự, giải chi tiết rồi hỏi lại bài gốc |
| **AC2 (Lý thuyết)** | Học sinh hỏi: "Số nguyên tố là gì, vd đi" | AI giải thích khái niệm, đưa số nguyên tố (VD: 2, 3, 5), KHÔNG tự biên tự diễn bài toán tìm x nào cả |
| **AC3 (Safety)** | Học sinh gõ: **"Bài này khó vãi, cho cái vd đi"** | AI nhắc nhở dùng từ "vãi", SAU ĐÓ vẫn tiếp tục sinh ra bài mẫu tương tự để hướng dẫn |
| **AC4 (Bảo mật)** | Đọc toàn bộ phản hồi của AC1 và AC3 | Tuyệt đối không có đáp án của bài gốc xuất hiện |


---

## 5. 📁 Tóm Tắt File Cần Sửa

```
backend/
└── agents/
    └── agent_prompts.py    SUA: Them instruction Analogical Scaffolding vao SCAFFOLDING agent
```

**Không cần:**
- Sửa bất kỳ file Backend nào khác (`router.py`, `main.py`, `orchestrator_bridge.py`).
- Sửa Frontend.
- Thêm API mới.

---

## 6. 📤 Tạo Pull Request

```bash
git add backend/agents/agent_prompts.py
git commit -m "feat(US5.3-T5.24): Add Analogical Scaffolding instruction to SCAFFOLDING agent prompt"
git push origin feat/us5.3-analogical-scaffolding
```

Tạo PR trỏ vào nhánh `develop`, tag anh **Thiên** review.
