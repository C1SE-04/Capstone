## 1. Orchestrator Agent (Kiến trúc Zero-API: 3 Trụ Cột Cục Bộ)

Orchestrator đóng vai trò là "Người điều phối", nhận tin nhắn của học sinh và quyết định chuyên gia (Specialized Agent) nào sẽ xử lý.
Trong SocraticKid, Orchestrator chạy **100% cục bộ (Zero-API, không tốn phí Gemini)** thông qua chuỗi 3 Trụ cột nối tiếp:

### 🏛️ Chi Tiết 3 Trụ Cột Điều Phối

#### 1. Trụ 1: Structural Pattern Engine (Quy tắc cấu trúc & Toán học) (~0ms)
* **Bản chất:** Sử dụng biểu thức chính quy (Regex), danh sách từ khóa cố định và thư viện toán học (SymPy & Fraction).
* **Tác dụng:** Bắt tức thì các trường hợp có cấu trúc rõ ràng, không thể nhầm lẫn:
  - Lọc ngôn từ xúc phạm hoặc chủ đề ngoài lề (*chơi game, hỏi tuổi...*) => Chuyển `SAFETY`.
  - Câu chào hỏi thuần túy (*"chào thầy", "hello"...*) => Chuyển `SAFETY`.
  - Câu hỏi lý thuyết dạng *"X là gì?", "thế nào là X"* => Chuyển `KNOWLEDGE_TRACING`.
  - **So khớp toán học trực tiếp:** Tự động tính toán số/phân số học sinh nộp và so sánh với đáp án chuẩn (`correctSolution`):
    - Làm đúng => Chuyển `SCAFFOLDING` (để khen và gợi ý bước tiếp).
    - Làm sai => Chuyển `MISCONCEPTION` (kèm đáp án sai để gợi mở sửa lỗi).

#### 2. Trụ 2: ML Semantic Router (Phân loại ngữ nghĩa bằng Học máy) (~2ms)
* **Bản chất:** Mô hình Machine Learning nhẹ (TF-IDF + Logistic Regression) chạy offline cục bộ, được huấn luyện sẵn từ hơn 500 câu chat thực tế của học sinh.
* **Tác dụng:** Đọc hiểu văn phong tự nhiên, tiếng lóng khi học sinh không nói theo khuôn mẫu của Trụ 1:
  - Phân loại ý định của học sinh vào 4 nhóm: `SCAFFOLDING`, `MISCONCEPTION`, `KNOWLEDGE_TRACING` hoặc `SAFETY`.
  - **Ngưỡng tin cậy (>= 60%):** Nếu mô hình tự tin >= 60% => chọn luôn Agent tương ứng. Nếu phân vân (< 60%), không đoán bừa mà nhường quyền cho Trụ 3.

#### 3. Trụ 3: State Machine (Máy trạng thái & Ngữ cảnh bài học) (~0ms)
* **Bản chất:** Bộ suy luận dựa trên trạng thái bài toán đang mở và lịch sử đối thoại giữa gia sư và học sinh.
* **Tác dụng:** Đóng vai trò là **lưới an toàn cuối cùng** giúp cuộc trò chuyện liền mạch:
  - **Kế thừa ngữ cảnh:** Nếu ở câu trước gia sư đang chữa lỗi (`MISCONCEPTION`) hoặc hỏi lý thuyết (`KNOWLEDGE_TRACING`), thì câu tiếp theo của học sinh sẽ tiếp tục ở luồng đó.
  - **Mặc định an toàn:** Nếu học sinh đang giải dở một bài toán, tự động chuyển về `SCAFFOLDING` để tiếp tục gợi ý từng bước. Đảm bảo 100% không bao giờ nghẽn luồng.

---

### 📥 Đầu vào (Input)
- **Tin nhắn mới nhất (`latest_message`):** Câu nói/hỏi hiện tại của học sinh.
- **Lịch sử hội thoại (`history_text`):** Danh sách các câu trao đổi trước đó giữa gia sư và học sinh.
- **Bối cảnh bài toán (`problem_context`):** Đề bài (`problemText`) và đáp án chuẩn (`correctSolution`) (ẩn với học sinh).

### 📤 Đầu ra (Output - JSON / `RoutingResult`)  
```json
{
  "selected_agent": "<SCAFFOLDING | MISCONCEPTION | KNOWLEDGE_TRACING | SAFETY>",
  "task_description": "<Sinh tự động bằng Dynamic Template Engine, ghép ngữ cảnh vào mẫu câu chỉ đạo sư phạm>",
  "routing_scratchpad": "<Nhật ký vết (Audit/Trace Log) ghi lại Trụ cột nào đã xử lý và lý do cụ thể>"
}
```

> **Ghi chú về cơ chế Zero-API:**
> * `task_description`: Không dùng LLM viết văn, mà dùng **Dynamic Template Engine** nhúng trực tiếp đề bài, đáp án học sinh làm sai hoặc khái niệm lý thuyết vào các khung câu chuẩn sư phạm Socratic.
> * `routing_scratchpad`: Đóng vai trò là **Trace Log** giải thích minh bạch: Trụ cột nào (Trụ 1, 2 hay 3) đã bắt được câu này và căn cứ vào đâu (Khớp toán học, xác suất ML hay lịch sử).

---

### 💡 Các ví dụ thực tế (Examples)

#### Ví dụ 1: Trụ 1 (Structural) — Học sinh tính đúng đáp số toán học
* **Đề bài:** Tìm mẫu số chung của 3 và 4 (Đáp án: 12).
* **Học sinh:** "Dạ em lấy 3 nhân 4 bằng 12 ạ."
* **Orchestrator Output:**
```json
{
  "selected_agent": "SCAFFOLDING",
  "task_description": "Học sinh cần hỗ trợ bài: 'Tìm mẫu số chung của 3 và 4'. Dùng phương pháp Socratic: đặt câu hỏi gợi mở cho bước tiếp theo, tuyệt đối không giải hộ toàn bộ bài. (Học sinh tính đúng: 12 ✓)",
  "routing_scratchpad": "[Trụ1] Math match CORRECT: 12 == 12"
}
```

#### Ví dụ 2: Trụ 1 (Structural) — Học sinh tính sai đáp số
* **Đề bài:** Phép tính 1/2 + 1/3 (Đáp án: 5/6).
* **Học sinh:** "Em cộng lại ra 2/5 ạ."
* **Orchestrator Output:**
```json
{
  "selected_agent": "MISCONCEPTION",
  "task_description": "Học sinh nộp đáp án '2/5' — chưa chính xác (đáp án đúng: '5/6'). Bài: Phép tính 1/2 + 1/3. Dùng câu hỏi Socratic để học sinh tự tìm ra bước tính sai. Tuyệt đối không tiết lộ đáp án đúng.",
  "routing_scratchpad": "[Trụ1] Math mismatch: 2/5 != 5/6"
}
```

#### Ví dụ 3: Trụ 2 (ML Semantic Router) — Văn phong tự nhiên, không theo khuôn mẫu
* **Học sinh:** "Thầy ơi em làm tới bước nhân chéo rồi mà giờ tịt ngòi không biết đi đâu tiếp."
* **Orchestrator Output:**
```json
{
  "selected_agent": "SCAFFOLDING",
  "task_description": "Học sinh cần được dẫn dắt từng bước. Dùng phương pháp Socratic: hỏi về bước học sinh vừa làm, rồi đặt câu hỏi cho bước tiếp theo. Không giải hộ.",
  "routing_scratchpad": "[Trụ2 - ML Semantic Router]: SCAFFOLDING (84.5%)"
}
```

#### Ví dụ 4: Trụ 3 (State Machine) — Tiếp tục ngữ cảnh hội thoại
* **Ngữ cảnh:** Ở câu trước, gia sư vừa hỏi học sinh về lý thuyết phân số tối giản.
* **Học sinh nhắn ngắn gọn:** "Dạ chưa hiểu lắm."
* **Orchestrator Output:**
```json
{
  "selected_agent": "KNOWLEDGE_TRACING",
  "task_description": "Học sinh đang hỏi về khái niệm/lý thuyết: 'Dạ chưa hiểu lắm'. Đặt 1-2 câu hỏi ngắn thăm dò để xác định học sinh đang hiểu đến đâu trước khi giải thích. Không giảng ngay, phải kiểm tra nền tảng trước.",
  "routing_scratchpad": "[Trụ3 - StateMachine]: Tiếp tục ngữ cảnh 'KNOWLEDGE_TRACING' từ lịch sử."
}
```

---

## 2. Specialized Agent (Ví dụ: Scaffolding, Misconception)

Specialized Agent (Chuyên gia) là cốt lõi tạo ra nội dung phản hồi cho học sinh theo phương pháp Socratic.

### 📥 Đầu vào (Input)
- **Vai trò (Agent Role):** (VD: SCAFFOLDING)
- **Task Description:** Nhận từ Orchestrator.
- **Lịch sử hội thoại & Tin nhắn mới nhất.**
- **Bối cảnh bài toán:** Đề bài và đáp án đúng.
- **Lý do từ chối (Reject Reason):** (Nếu bị Reviewer đánh rớt ở vòng trước).

### 📤 Đầu ra (Output - JSON)
```json
{
  "internal_scratchpad": "<Chuỗi suy luận, giải toán nội bộ để đối chiếu với học sinh>",
  "draft_response": "<Câu trả lời nháp gửi cho học sinh, tiếng Việt, có dùng LaTeX $...$>",
  "knowledge_level_estimate": "<BEGINNER | INTERMEDIATE | ADVANCED>"
}
```

### 💡 Ví dụ (Example)
**Học sinh:** "Tiếp theo lấy tử số phân số 1 nhân với 4, mẫu cũng nhân 4 đúng không thầy?"
**Specialized Agent (SCAFFOLDING) Output:**
```json
{
  "internal_scratchpad": "Học sinh đã hiểu cách quy đồng, với mẫu chung 12, phân số đầu tiên mẫu là 3 thì phải nhân cả tử và mẫu với 4. Bước này hoàn toàn chính xác.",
  "draft_response": "Đúng rồi em! Mình phải nhân cả tử và mẫu với 4. Vậy phân số đầu tiên của em sẽ trở thành gì nào?",
  "knowledge_level_estimate": "INTERMEDIATE"
}
```

---

## 3. Reviewer Agent (Pillar 3 / Local Reviewer)

Reviewer Agent đóng vai trò là "Giám thị", duyệt lại câu trả lời nháp (draft_response) của Specialized Agent trước khi gửi cho học sinh để đảm bảo không vi phạm nguyên tắc sư phạm (như giải giùm, lộ đáp án).

### 📥 Đầu vào (Input)
- **Tin nhắn gốc của học sinh:** Để Reviewer hiểu ngữ cảnh.
- **Bản nháp (Draft Response):** Câu trả lời do Specialized Agent tạo.
- **Bối cảnh bài toán:** Đề bài và đáp án.

### 📤 Đầu ra (Output - JSON)
```json
{
  "decision": "<PASS | REJECT>",
  "confidence_score": <Số thập phân từ 0.0 đến 1.0>,
  "reject_reason": "<Mô tả chi tiết lỗi và cách sửa (Nếu PASS thì để rỗng hoặc null)>"
}
```

### 💡 Ví dụ (Example)

**Trường hợp 1: PASS (Chấp nhận bản nháp)**
**Draft Response:** "Đúng rồi em! Mình phải nhân cả tử và mẫu với 4. Vậy phân số đầu tiên của em sẽ trở thành gì nào?"
**Reviewer Output:**
```json
{
  "decision": "PASS",
  "confidence_score": 0.95,
  "reject_reason": null
}
```

**Trường hợp 2: REJECT (Từ chối vì giải giùm/lộ đáp án)**
**Draft Response:** "Đúng rồi, tử nhân 4, mẫu nhân 4 thì ta sẽ được phân số mới là 8/12 em nhé."
**Reviewer Output:**
```json
{
  "decision": "REJECT",
  "confidence_score": 0.20,
  "reject_reason": "Bản nháp vi phạm lỗi NGHIÊM TRỌNG: Lộ đáp án trung gian (đã tính sẵn ra 8/12 thay học sinh). Cần sửa lại: Chỉ xác nhận cách nhân là đúng và hỏi học sinh kết quả bằng bao nhiêu."
}
```
