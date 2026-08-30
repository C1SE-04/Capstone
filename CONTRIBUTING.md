# Hướng dẫn Đóng góp (Contributing Guidelines)

Chào mừng bạn đến với dự án **SocraticKid**! Chúng tôi rất vui mừng khi bạn tham gia đóng góp để xây dựng một "vũ trụ khám phá tri thức" dành cho học sinh. 

Để đảm bảo chất lượng code và quá trình làm việc nhóm mượt mà, vui lòng tuân thủ các nguyên tắc và tiêu chuẩn lập trình dưới đây khi đóng góp vào repo này.

---

## 1. Tiêu chuẩn Mã nguồn (Coding Standards)

Dự án này sử dụng kiến trúc Monorepo với 2 phần chính: **Backend (Python/FastAPI)** và **Frontend (TypeScript/Next.js/React)**. Vui lòng tuân thủ chặt chẽ convention của từng môi trường.

### 1.1 Backend (Python)

- **Biến và Hàm (Variables & Functions):** Sử dụng `snake_case`. 
  *Ví dụ:* `list_sessions`, `create_session`, `health_check`.
- **Lớp và Mô hình (Classes & Pydantic Models):** Sử dụng `PascalCase`. 
  *Ví dụ:* `CreateSessionRequest`, `ChatSession`, `ChatMessage`.
- **Tệp tin và Thư mục (Files & Directories):** Sử dụng `snake_case`.
  *Ví dụ:* `main.py`, `session.py`, `agent_prompts.py`.
- **Hằng số (Constants):** Sử dụng `UPPER_SNAKE_CASE`.
- **Comment & Type Hinting:** 
  - Khuyến khích sử dụng Type Hinting đầy đủ trong Python (ví dụ: `def get_session_messages(session_id: str) -> list:`).
  - Viết docstring ("""...""") cho các hàm chức năng và endpoint chính.

### 1.2 Frontend (TypeScript/React/Next.js)

- **Component (React Components):** Sử dụng `PascalCase` cho tên file (nếu là component tái sử dụng) và tên hàm.
  *Ví dụ:* `GuestHome.tsx`, `UserDashboard.tsx`, `function HomePage()`.
- **Biến, Hàm, Hook (Variables, Functions, Hooks):** Sử dụng `camelCase`.
  *Ví dụ:* `const [isLoading, setIsLoading] = useState(false);`, `useSession`, `geistMono`.
- **Định dạng file Next.js App Router:** Các file đặc thù của Next.js (như `page.tsx`, `layout.tsx`, `globals.css`) phải dùng `kebab-case` hoặc chữ thường hoàn toàn theo đúng quy chuẩn Next.js.
- **Kiểu dữ liệu (Interfaces/Types):** Sử dụng `PascalCase`.
  *Ví dụ:* `interface UserProps`, `type MessagePayload`.

---

## 2. Quy trình Làm việc (Git Workflow)

1. **Fork và Clone:**
   Fork repository này về tài khoản GitHub của bạn và clone về máy.
2. **Tạo Branch Mới:**
   - Tạo nhánh tính năng/sửa lỗi từ nhánh `main` hoặc nhánh `develop` (tuỳ quy ước đang dùng).
   - Đặt tên nhánh mô tả rõ ràng: `feature/ten-tinh-nang`, `bugfix/ten-loi`, `hotfix/...`.
3. **Commit:**
   - Viết thông điệp commit rõ ràng, mạch lạc, tốt nhất bằng tiếng Anh hoặc tiếng Việt rõ nghĩa. 
   - Ví dụ: `feat: Thêm chức năng ghim session` hoặc `fix: Cập nhật lỗi UI hiển thị loading skeleton`.
4. **Push & Pull Request (PR):**
   - Đẩy nhánh (Push) lên fork của bạn.
   - Tạo Pull Request hướng tới nhánh chính của repo gốc.
   - Viết mô tả rõ ràng trong PR về những gì đã thay đổi và lý do.

## 3. Cấu trúc Thư mục

Hãy giữ mã nguồn của bạn vào đúng nơi quy định:
- `backend/routes/`: Chứa các endpoint API.
- `frontend/app/`: Chứa các trang và layout (Next.js App Router).
- `frontend/app/components/`: Chứa các React components tái sử dụng.

## 4. Quy ước thông điệp Commit (Commit Convention)

Chúng tôi áp dụng chuẩn **Conventional Commits**. Thông điệp commit của bạn cần theo định dạng sau:
`<type>: <mô tả ngắn gọn>`

Các loại `<type>` thường dùng:
- `feat`: Thêm một tính năng mới.
- `fix`: Sửa lỗi (bug).
- `docs`: Cập nhật tài liệu (README, CONTRIBUTING, v.v.).
- `style`: Cải thiện format code (khoảng trắng, dấu phẩy, v.v.) không làm thay đổi logic.
- `refactor`: Viết lại code nhưng không thay đổi chức năng hay sửa lỗi.
- `chore`: Cập nhật cấu hình, build tool, package.json.

*Ví dụ:* `feat: Thêm chức năng hiển thị bong bóng chat` hoặc `fix: Khắc phục lỗi crash ở trang chủ`

## 5. Cài đặt và Chạy dự án cục bộ (Local Development)

### 5.1 Chạy Frontend (Next.js)
1. Di chuyển vào thư mục frontend: `cd frontend`
2. Cài đặt các gói phụ thuộc: `npm install`
3. Cài đặt và cập nhật Database bằng Prisma:
   - `npm run db:push`
   - `npm run db:seed`
4. Khởi chạy server development: `npm run dev`
5. Kiểm tra code trước khi commit: `npm run lint`

### 5.2 Chạy Backend (Python/FastAPI)
1. Di chuyển vào thư mục backend: `cd backend`
2. Khuyến khích tạo Virtual Environment: `python -m venv venv` và kích hoạt (`source venv/bin/activate` hoặc `venv\Scripts\activate` trên Windows).
3. Cài đặt thư viện: `pip install -r requirements.txt`
4. Khởi chạy server: `uvicorn main:app --reload --port 8000`

---

Cảm ơn bạn đã dành thời gian đóng góp cho **SocraticKid**! Mọi ý kiến thắc mắc bạn có thể tạo Issue để thảo luận thêm.
