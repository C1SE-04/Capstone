# Toàn Bộ Luồng Chạy Của Dự Án Khi Học Sinh Gửi Tin Nhắn

Dưới đây là từng bước chi tiết từ lúc học sinh gõ phím đến lúc nhận lại câu trả lời từ AI Socratic, bao gồm đường dẫn file cụ thể cho từng xử lý:

## Giai đoạn 1: Frontend (Giao diện người dùng)

1. **Nhập và Gửi Tin Nhắn (`frontend/components/chat/ChatInput.tsx`)**:
   - Học sinh gõ tin nhắn vào ô `textarea` tự động co giãn.
   - Khi nhấn Enter, hàm `handleSend` được kích hoạt. Nó kiểm tra điều kiện (không rỗng, không mất kết nối, AI không bận) và gửi nội dung đi thông qua hàm prop `onSendMessage`.

2. **Quản Lý Component Chat (`frontend/components/chat/ChatWindow.tsx`)**:
   - Tin nhắn của học sinh được đưa vào danh sách hiển thị trên UI.
   - Component này nhận hàm `onSendMessage` từ component cha (thường là trang chính). Thông qua đó, Frontend sẽ gửi một request `POST` tới API endpoint của backend (`/chat/orchestrator`).

## Giai đoạn 2: Backend - Cổng Tiếp Nhận (FastAPI Router)

3. **Tiếp Nhận Request (`backend/routers/chat.py`)**:
   - Endpoint `@router.post("/chat/orchestrator")` nhận request (chứa nội dung `prompt`, `session_id`, `problem_context`, v.v.).
   - Tại đây, hệ thống tự động kiểm tra `session_id`. Nếu là người dùng đang dùng thử (bắt đầu bằng `guest-`), nó sẽ tự động khởi tạo dữ liệu `User` và `Session` cho khách giả lập trong cơ sở dữ liệu (Database).
   - Tiếp theo, router gọi hàm `process_query_with_orchestrator()` và trả về một luồng **StreamingResponse** (Server-Sent Events) nhằm gửi dữ liệu trả về Frontend từng phần nhỏ một (tạo hiệu ứng gõ chữ của AI).

## Giai đoạn 3: Backend - Điều Phối Viên (Orchestrator Bridge)

4. **Xử Lý Ngữ Cảnh Và Thống Kê Học Tập (`backend/orchestrator_bridge.py`)**:
   - **Lưu Database**: Tin nhắn của học sinh được lưu ngay vào bảng `Message`.
   - **Cập Nhật Thống Kê (SessionStats)**: Dựa trên trạng thái trả lời (đúng hay sai trước đó), hệ thống cập nhật `consecutive_wrong_count` (số lần sai liên tiếp) và `hint_count` (số lần gợi ý).
   - **Chiến Lược Sư Phạm (`teaching_mode`)**:
     - *socratic*: Học sinh sai ≤ 2 lần → Chỉ đặt câu hỏi gợi mở, không giải thích thẳng.
     - *hint*: Học sinh sai > 2 lần và chưa dùng quá giới hạn 2 lần gợi ý → Gợi ý rõ ràng hơn một chút.
     - *reveal*: Đã hết quyền trợ giúp (gợi ý) → Giải thẳng các bước và kết quả.
   - Hệ thống cũng lấy lịch sử hội thoại gần nhất từ Database để làm ngữ cảnh.

5. **Phân Luồng Thông Minh (`backend/agents/orchestrator.py`)**:
   - `OrchestratorAgent` sử dụng cấu trúc "Zero-API" (không cần gọi đến các mô hình ngôn ngữ lớn đắt tiền) thông qua **3 Trụ cột** để quyết định sẽ gọi Agent (nhân viên AI) nào xử lý:
     - *Trụ 1 (Structural)*: Sử dụng Regex phân tích các từ khóa:
       - Từ khóa xấu/xúc phạm/ngoài lề → Gọi `SAFETY_AGENT`
       - Hỏi lý thuyết → Gọi `KNOWLEDGE_TRACING_AGENT`
       - Tín hiệu không hiểu bài/cần cầu cứu → Gọi `SCAFFOLDING_AGENT`
       - Phân tích toán học xem kết quả đúng/sai → Gọi `MISCONCEPTION_AGENT` nếu có hiểu lầm.
     - *Trụ 2 (ML Model)*: (Nếu Trụ 1 thất bại) Chạy mô hình học máy cục bộ (`local_orchestrator.pkl`) để phân loại ý định người dùng.
     - *Trụ 3 (State Machine)*: (Dự phòng cuối cùng) Kế thừa trạng thái Agent của câu hỏi trước đó để giữ đúng luồng hội thoại.
   - Sau khi quyết định xong, nó trả về `target_agent` sẽ chịu trách nhiệm cho câu hỏi, đồng thời kèm theo chỉ đạo (task description).

## Giai đoạn 4: Backend - Sinh Câu Trả Lời (LLM Router & Reviewer)

6. **Gọi AI Với Các Chỉ Đạo Nghiêm Ngặt (`backend/router.py`)**:
   - Một bản `task_description` chi tiết được gộp từ quyết định của `OrchestratorAgent` và chiến lược sư phạm `teaching_mode`.
   - Hàm `agent_router` được kích hoạt. Nó truyền cấu hình `TEACHER_SYSTEM_INSTRUCTION` (Bắt buộc xưng "thầy", gọi "em", tuyệt đối không xưng "dạ", nhắc nhở khi học sinh vô lễ) vào mô hình AI (như `gemini-3.5-flash-lite`).
   - Mô hình AI bắt đầu sinh câu trả lời.
   - **Kiểm duyệt tự động (Reviewer)**: Trong hàm này, nếu `target_agent` là `SCAFFOLDING_AGENT`, kết quả sinh ra phải đi qua `LocalReviewerAgent` ở background. Nếu bị đánh giá là tiết lộ đáp án thẳng hoặc vi phạm nguyên tắc Socratic, Reviewer sẽ từ chối và nạp "lời nhắc/mắng" vào prompt để ép AI sinh lại (hệ thống cho phép thử lại tối đa 2 lần).

7. **Trả Về Frontend (Streaming) (`backend/router.py`)**:
   - Khi câu trả lời vượt qua bước kiểm duyệt, backend sẽ "chẻ" văn bản ra thành từng từ (hoặc từng đoạn nhỏ) và dùng lệnh `yield` đẩy dần về Frontend để hiển thị nhanh chóng. Đồng thời, nó gửi kèm sự kiện (event) thông báo quyết định của Orchestrator.

## Giai đoạn 5: Backend & Frontend - Lưu Trữ Và Đánh Giá Hiểu Bài

8. **Lưu Tin Nhắn AI Và Yêu Cầu Phản Hồi (`backend/orchestrator_bridge.py`)**:
   - Toàn bộ nội dung trả về của AI sau khi sinh xong sẽ được lưu vào Database với `sender_type="AGENT_TUTOR"`.
   - Đặc biệt, nếu học sinh vừa trả lời đúng HOẶC hệ thống vừa phải chạy chế độ "chỉ thẳng đáp án" (`reveal`), backend sẽ tự động đẩy thêm một sự kiện mang tên `ask_comprehension` về Frontend.

9. **Frontend Hiển Thị Phản Hồi (`frontend/components/chat/ChatWindow.tsx` & `frontend/components/chat/UnderstandingButtons.tsx`)**:
   - Frontend (`ChatWindow.tsx`) nhận luồng dữ liệu stream và hiển thị hiệu ứng AI đang gõ từng chữ.
   - Khi nhận được sự kiện `ask_comprehension`, Frontend sẽ tự động hiển thị hai nút **Đã hiểu** / **Chưa hiểu** bên dưới tin nhắn (`UnderstandingButtons.tsx`).
   - *(Trường hợp học sinh nhấn "Chưa hiểu", Frontend sẽ gọi API tới `/chat/comprehension` ở `backend/routers/chat.py`, backend cập nhật thống kê chưa hiểu và hệ thống sẽ bắt AI chạy luồng giải thích lại bằng cách lấy ví dụ thực tế hoàn toàn khác).*
