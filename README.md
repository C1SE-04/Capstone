# Capstone1

    SocraticKid: A Pedagogically Safe Agentic Tutor with Dynamic Scaffolding

AI Tutor chủ động nhưng không làm bài thay trẻ
Pain point
Nhiều chatbot đưa đáp án quá sớm, khiến trẻ phụ thuộc vào AI và giảm quá trình tự suy nghĩ.
Điểm nghiên cứu – sáng tạo
Xây dựng Agentic AI có các agent chuyên biệt:
• Knowledge Tracing Agent: ước lượng kiến thức hiện tại.
• Misconception Agent: phát hiện hiểu sai.
• Scaffolding Agent: lựa chọn mức gợi ý.
• Safety Agent: kiểm tra nội dung phù hợp lứa tuổi.
Hệ thống áp dụng “intentional friction”: trẻ phải thực hiện một bước suy luận trước khi được
nhận gợi ý tiếp theo. Đây là hướng quan trọng vì nghiên cứu gần đây cho thấy agent giáo dục
phải cân bằng giữa tự động hóa và nỗ lực nhận thức của người học.
AI ghi nhận lịch sử học, điều chỉnh mức gợi ý và tạo bài tiếp theo.

## 🚀 Môi trường Triển khai (Deployment)

- **Frontend (Vercel):** `https://socratickid.vercel.app/`
- **Backend (Render):** `https://capstone-backend-r12q.onrender.com`

## 🤖 Kiến Trúc Multi-Model Quota Pooling (Sprint 10 - US 10.4)

SocraticKid sử dụng **6 phân hệ Gemini độc lập** để tối đa hóa hạn mức Free Tier:

| Biến Môi Trường | Model Mặc Định | Vai Trò | Bể Quota |
|:---|:---|:---|:---:|
| `GEMINI_CHAT_MODEL` | `gemini-3.8-flash` | Chat Socratic Chính | Bể 1 (15 RPM) |
| `GEMINI_INSIGHT_MODEL` | `gemini-3.5-flash` | Báo Cáo Phụ Huynh | Bể 2 (15 RPM) |
| `GEMINI_CLASSIFIER_MODEL` | `gemini-3.1-flash-lite` | Phân Loại SGK & Tiêu Đề | Bể 3 (15 RPM) |
| `GEMINI_EMAIL_MODEL` | `gemini-3.1-flash-lite` | Soạn Email Cảnh Báo | Bể 3 (chia sẻ) |
| `GEMINI_FLASHCARD_MODEL` | `gemini-3.5-flash-lite` | Flashcard / Tiện Ích | Bể 4 (15 RPM) |
| `GEMINI_BACKUP_MODEL` | `gemini-3.5-flash-lite` | Dự Phòng Chung | Bể 4 (chia sẻ) |

> **Tổng năng lực:** 4 bể × 15 RPM = **60 RPM & 6,000 RPD** trên 1 API Key miễn phí.

> ⚠️ **Lưu ý:** `gemini-1.5-flash` và `gemini-2.5-flash` đã bị Google khai tử (404 Not Found). Không sử dụng các model này.

## ⚙️ Cài Đặt Nhanh (Quick Setup)

```bash
# 1. Clone repo
git clone <repo-url>

# 2. Cấu hình Backend
cd backend
cp .env.example .env
# Chỉnh sửa .env: điền GEMINI_API_KEY và DATABASE_URL

# 3. Khởi chạy Backend
pip install -r requirements.txt
uvicorn main:app --reload

# 4. Cấu hình Frontend
cd ../frontend
cp .env.example .env.local
# Chỉnh sửa .env.local: điền NEXT_PUBLIC_BACKEND_URL

# 5. Khởi chạy Frontend
npm install
npm run dev
```
