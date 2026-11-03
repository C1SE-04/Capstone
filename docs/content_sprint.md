# Kế Hoạch 12 Sprint Dự Án SocraticKid (Thực chiến Jira/Agile)

**Quy định anh em team:**
- Quy mô team: 4 mạng (Gắn tên cụ thể để chia việc cho khối lượng ĐỀU NHAU).
  - **[Thống]**: **Trùm Backend** (Chuyên API, Auth, Logic Server).
  - **[Bảo]**: **Trùm Frontend & Kịch bản UX** (Chuyên giao diện Next.js, CSS, và đóng vai học sinh nghĩ kịch bản để test hệ thống).
  - **[Thông]**: **Kỹ sư AI / Machine Learning Engineer** (Chuyên train mô hình, viết Prompt, test luồng phản hồi).
  - **[Thiên]**: **Nhóm trưởng / DevOps / QA** (Chuyên quản lý Database, Deploy, Test E2E, Review code, và làm các Document nghiên cứu công nghệ mới).
- Thời gian: 1 Sprint = 1 tuần (7 ngày) (Áp dụng từ Sprint 3).
- Khối lượng: Chia sao cho Thống và Thông code mệt thì Bảo và Thiên sẽ lo nghĩ kịch bản, làm tài liệu nghiên cứu, test chéo. Hễ Frontend (Bảo) hay Nhóm trưởng (Thiên) rảnh là kéo task của Sprint sau lên làm trước. Bất cứ công nghệ nào lạ đều phải có task "Nghiên cứu" cho Nhóm trưởng hoặc dev phụ trách.

---

## Sprint 1: Lên Móng Hạ Tầng & Đăng Nhập (Đã xong)
*(Sprint này anh em đã làm setup Vercel, Neon DB, Github với luồng đăng nhập)*

---

## Sprint 2: Trả Nợ Code Cũ & Xây Dựng Bộ Não AI (Test qua FastAPI)
**(Thời gian: 05-Sep đến 18-Sep - Sprint 2 tuần)**

### US 2.1: Sửa lỗi tồn đọng, hoàn thiện tài liệu và phần đăng nhập
*Mô tả: Là một Lập trình viên, tôi muốn dọn dẹp code cũ và chuẩn hóa luồng đăng nhập để hệ thống có nền tảng vững chắc cho các tính năng AI.*
- **Tasks:**
  - [Thông] [Document] Cập nhật file README.md và CONTRIBUTING.md (1.5h)
  - [Thông] [Document] Viết file hướng dẫn Nghiệm thu Sprint 1 (2h)
  - [Thiên] [Database] Tạo nhánh Môi trường Database trên Neon.tech (1h)
  - [Thống] [BE] Cấu trúc lại luồng Xác thực Access/Refresh Token (2.5h)
  - [Thiên] [Document] Viết Database Dictionary giải thích các bảng (2h)
  - [Thiên] [DevOps] Thiết lập biến môi trường Cloud Secrets (1h)
  - [Thống] [QA] Viết Unit Test cho API Auth Middleware (2h)
  - [Bảo] [QA] Test hiệu năng và trải nghiệm người dùng luồng đăng nhập Email/Password. (1.5h)
  - [Thiên] [DevOps] Setup Github Actions: Cứ ai push code lên nhánh Dev là tự động chạy test FastAPI. (2.5h)
  - [Thiên] [Management] Review PR: Đọc soát toàn bộ code/tài liệu của Thống, Bảo, Thông đẩy lên, gỡ rối conflict và Merge code. (2h)

### US 2.2: Nghiên cứu tổng quan luồng chạy của các con Agent
*Mô tả: Là một Kỹ sư AI, tôi muốn xác định rõ luồng chạy và dữ liệu đầu vào/ra của các Agent để cả team có chung một bức tranh tổng thể trước khi bắt đầu code.*
- **Tasks:**
  - [Thông] [AI] Đóng vai học sinh: Liệt kê 20 kịch bản thực tế (chửi thề, lười biếng, hỏi lạc đề) làm đầu vào cho AI. (2.5h)
  - [Thông] [Research] Nghiên cứu: Đọc tài liệu Google Gemini (streaming, JSON format). Viết file `GEMINI_RESEARCH.md`. (2h)
  - [Thông] [AI] Chốt lại đầu vào/đầu ra (Input/Output JSON) giữa các con Agent để ráp code không bị lệch. (1.5h)
  - [Thông] [Document] Viết 1 file tài liệu ngắn `AI_FLOW.md` chốt luồng để anh em nhìn vào đó mà code. (1.5h)
  - [Thống] [QA] Setup Postman Collection sẵn sàng với các biến môi trường để test API của AI. (1h)
  - [Thống] [BE] Làm thử 1 cái script nhỏ gọi thử 1 con Gemini lên xem nó trả lời có đúng format không. (1h)
  - [Cả Team] [Management] Cả team họp 30 phút rà lại cái sơ đồ luồng này do [D] chủ trì. (1h)
  - [Thiên] [Design] Vẽ sơ đồ kiến trúc hệ thống tổng thể (System Architecture) trên Draw.io cho oai. (2h)
  - [Thiên] [Management] Review PR: Duyệt file AI_FLOW và các kịch bản của team, chốt kiến trúc hệ thống và Merge tài liệu. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - Tài liệu kịch bản kiểm thử (`test_scenarios.md`) hoàn thành với ít nhất 20 tình huống thực tế bao quát 4 nhóm: hỏi bài đúng, đòi giải hộ, hỏi lạc đề, và chửi thề/toxic.
  - File nghiên cứu `docs/GEMINI_RESEARCH.md` được hoàn thiện, ghi nhận chi tiết cơ chế Structured Outputs, Streaming và có kèm code mẫu Python chạy được.
  - Thống nhất và chốt cấu trúc JSON Schema chuẩn cho toàn bộ Input/Output dữ liệu trao đổi giữa các Agent (Orchestrator, Tutor, Checker, Safety).
  - Tài liệu luồng `docs/AI_FLOW.md` và sơ đồ kiến trúc hệ thống (`docs/architecture.png`) hoàn thiện, trực quan hóa đầy đủ luồng đi từ Frontend đến Gemini API.
  - Postman Collection cùng script test Python (`test_gemini.py`) kết nối thành công tới Gemini API, xác thực dữ liệu trả về đúng JSON Schema quy định.

---

## Sprint 3: Giao diện cơ bản & Trải nghiệm Trò chuyện (19-Sep đến 25-Sep)
*(Phân bổ khối lượng: [Bảo]: 12h, [Thông]: 19h, [Thiên]: 19h, [Thống]: 19h)*

### US 3.1: Giao diện Đăng nhập & Trang khách
*Mô tả: Là một Khách truy cập, tôi muốn có trang Đăng nhập và Trang chủ thân thiện để tôi dễ dàng hiểu hệ thống và bắt đầu sử dụng.*
- **Mô tả chi tiết:**
  - **Trang chủ tĩnh (Landing Page)**:
    - Cung cấp giao diện giới thiệu hệ thống trực quan cho khách chưa có tài khoản.
    - Hiển thị tốt trên cả điện thoại và máy tính (responsive).
    - Có nút điều hướng chuyển sang form đăng nhập/đăng ký.
  - **Đăng ký tài khoản mới**:
    - Form đăng ký yêu cầu nhập Email và Mật khẩu.
    - Tự động validate dữ liệu (định dạng email, mật khẩu trống) trực tiếp ở Frontend.
    - Xử lý lỗi từ API (ví dụ: email bị trùng) và báo lỗi rõ ràng.
    - Hiển thị hiệu ứng loading trong lúc xử lý để ngăn spam click.
  - **Đăng nhập hệ thống**:
    - Xác thực người dùng bằng thư viện NextAuth.
    - Kiểm tra lỗi nhập liệu và hiện loading tương tự như form đăng ký.
    - Báo lỗi nếu sai thông tin, chuyển hướng mượt mà vào màn hình Chat khi thành công.
- **Tasks:**
  - [Bảo] [FE] Code giao diện Trang chủ tĩnh bằng Next.js + Tailwind. (4h)
  - [Bảo] [FE] Code form Đăng nhập / Đăng ký bằng useState thuần và xử lý sự kiện DOM. (3h)
  - [Bảo] [FE] Cấu hình NextAuth (signIn) và gắn vào form giao diện, xử lý trạng thái loading/error. (2h)
  - [Bảo] [FE] Làm responsive cho Mobile. (1.5h)
  - [Thống] [BE] Code logic Đăng ký (Register) bằng Next.js API Route và mã hoá mật khẩu (bcrypt). (3h)
  - [Thiên] [QA] Viết script test UI tự động hoặc test tay kỹ trên điện thoại. (1.5h)
  - [Thiên] [Management] Review PR, kiểm tra tính ổn định của giao diện và thực hiện Merge. (1h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Luồng đăng nhập:** Người dùng nhập email/pass đúng, Khi bấm "Đăng nhập", Thì hệ thống lưu token và chuyển hướng vào trang Chat.
  - **[AC2] Responsive:** Người dùng mở bằng điện thoại, Khi xem trang chủ, Thì các khối thông tin xếp dọc không bị vỡ chữ hay tràn viền.
  - **[AC3] Xử lý lỗi đăng nhập:** Người dùng nhập sai mật khẩu hoặc tài khoản chưa tồn tại, Khi bấm "Đăng nhập", Thì hệ thống báo lỗi rõ ràng "Sai email hoặc mật khẩu".
  - **[AC4] Luồng đăng ký:** Người dùng đăng ký với email đã được sử dụng, Khi bấm "Đăng ký", Thì hệ thống hiển thị thông báo lỗi "Email này đã tồn tại".
  - **[AC5] Trạng thái Loading:** Khi người dùng bấm nút Submit, Thì nút đó sẽ tự động chuyển sang trạng thái Loading (có spinner quay) để ngăn người dùng bấm đúp gửi request nhiều lần.
  - **[AC6] Validation tại Frontend:** Người dùng nhập email thiếu ký tự "@" hoặc bỏ trống trường bắt buộc, Khi bấm Đăng nhập/Đăng ký, Thì form lập tức báo viền đỏ và từ chối gọi API Backend.

### US 3.2: Khung Chat và Gợi ý Socratic
*Mô tả: Là một Học sinh , tôi muốn gõ câu hỏi Toán vào khung chat và nhận được gợi ý từng bước (chứ không phải đáp án cuối) để tôi tự suy nghĩ ra bài giải.*
- **Mô tả chi tiết:**
  - **Khung giao diện Chat chính**:
    - Khu vực nhập liệu tự động co giãn theo lượng chữ và hỗ trợ đính kèm hình ảnh.
    - Tự động cuộn xuống khi có tin nhắn mới (auto-scroll).
    - Hiển thị mượt mà các công thức toán học bằng định dạng Markdown/LaTeX.
  - **Tương tác Socratic ngầm**:
    - Backend điều phối AI qua các bước xử lý ngầm khi người dùng gửi bài toán.
    - Đảm bảo AI không đưa ra đáp án thẳng mà chỉ hỏi ngược lại để gợi mở.
    - Hiển thị trạng thái "Đang suy nghĩ..." trên UI trong lúc AI xử lý.
  - **Phục hồi và lưu trữ bối cảnh**:
    - Hệ thống tự động ghi nhớ các câu chat gần nhất (ngữ cảnh).
    - AI vẫn hiểu được câu trả lời ngắn gọn (vd: "dạ 5") nhờ bối cảnh trước đó.
    - Lịch sử chat được lưu trữ vào Database, đảm bảo F5 không bị mất dữ liệu.
  - **Thanh điều hướng (Sidebar)**:
    - Liệt kê danh sách các đoạn hội thoại cũ (Hành trình) để học sinh xem lại.
    - Cho phép chuyển đổi qua lại giữa các lịch sử chat mượt mà.
    - Nút "Hành trình mới" giúp dọn sạch khung chat để bắt đầu một phiên hỏi đáp mới.
- **Tasks:**
  - [Bảo] [FE] Code giao diện khung chat chính (ô nhập tự co giãn, bong bóng chat render Markdown/Toán). (3h)
  - [Thiên] [FE] Xử lý State React thuần để đồng bộ trạng thái Sidebar và Chat. (1h)
  - [Thiên] [FE] Tích hợp chức năng cuộn tự động (smooth auto-scroll). (1h)
  - [Thiên] [FE] Code giao diện Dashboard và Sidebar hiển thị danh sách bài học. (2h)
  - [Thiên] [FE] Tích hợp nút "Chat mới" trên Sidebar. (1h)
  - [Thông] [AI] Code Trụ 1 (Structural Engine) dùng Regex và SymPy để lọc từ cấm, tính toán phân số (Đôn từ Sprint 4). (4.5h)
  - [Thông] [AI] Tạo tập dữ liệu `intent_data.csv` (thu thập và gán nhãn mẫu câu phân loại ý định). (2.5h)
  - [Thông] [AI] Code mô hình ML Trụ 2 (TF-IDF + Logistic Regression), huấn luyện và xuất file. (4h)
  - [Thông] [AI] Kích hoạt Trụ 3 (State Machine): Code logic đọc ngữ cảnh hội thoại để điều hướng khi câu chat quá ngắn. (3h)
  - [Thông] [QA] Viết script Benchmark đo kiểm độ trễ và độ chính xác của bộ não điều phối (Đôn từ Sprint 4). (3h)
  - [Thông] [AI] Viết prompt cho AI Gia Sư: Tuyệt đối không cho kết quả, chỉ hỏi ngược lại để gợi ý. (2h)
  - [Thống] [BE] Viết hàm Backend gom 5 câu chat gần nhất làm ngữ cảnh. (3h)
  - [Thống] [BE] Làm API `/chat` nối giao diện FE với Agent Gia sư (bọc qua router ngầm). (4h)
  - [Thống] [BE] Tối ưu Streaming Response trả từng chữ về Frontend. (4h)
  - [Thống] [BE] Code API tạo Session mới và lấy danh sách Session cũ. (2h)
  - [Thống] [Database] Mở bảng Session và Message bằng Prisma để ghi log lại. (3h)
  - [Thiên] [Database] Tối ưu index Database để lôi lịch sử ra nhanh hơn. (2h)
  - [Thiên] [DevOps] Bơm request thử tải API `/chat` xem có lỗi treo server không. (2h)
  - [Thiên] [QA] Viết kịch bản Test E2E luồng chat và trực tiếp chat thử tìm lỗi. (2h)
  - [Thiên] [Management] Review PR thanh Sidebar và test tính năng chuyển đổi lịch sử cũ. (1h)
  - [Thiên] [Management] Review PR toàn bộ luồng chat E2E và chốt merge. (1h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Tương tác chat:** Học sinh nhập tin nhắn và gửi, Khi đó giao diện hiện bong bóng chat của học sinh lập tức, hệ thống có hiệu ứng "Đang suy nghĩ..." và trả về câu trả lời của AI.
  - **[AC2] Phương pháp Socratic:** Học sinh gõ "Giải cho em bài 2x = 4", Khi AI trả lời, Thì nội dung hiển thị phải là câu hỏi gợi ý, tuyệt đối không chứa chữ "x = 2".
  - **[AC3] Phân loại ngầm (Trụ 2):** Học sinh gõ câu trò chuyện phiếm "Nay trời đẹp quá", Khi AI trả lời, Thì nội dung phải lái lại về việc học, chứng tỏ Router ngầm hoạt động tốt.
  - **[AC4] Phục hồi ngữ cảnh (Trụ 3):** Học sinh gõ một câu cụt lủn "dạ 5", Khi đó hệ thống dựa vào câu chat trước để hiểu đây là kết quả của phép tính và trả về đúng phản hồi xác nhận.
  - **[AC5] Sidebar & History:** Học sinh F5 trình duyệt, lịch sử chat vẫn được giữ nguyên và Sidebar hiển thị đúng bài học hiện tại.

---

## Sprint 4: Kiểm duyệt AI & Tương tác Cú Socratic (26-Sep đến 02-Oct)
*(Phân bổ khối lượng: [Bảo]: 12h, [Thông]: 19h, [Thiên]: 19h, [Thống]: 19h)*

### US 4.1: An toàn Sư phạm (Reviewer Agent)
*Mô tả: Là một Phụ huynh, tôi muốn hệ thống tự động kiểm duyệt gắt gao câu trả lời của AI để chắc chắn không lọt đáp án ra ngoài cho con tôi.*
- **Mô tả chi tiết:**
  - **Kiểm duyệt tự động qua Giám thị (Reviewer)**:
    - Tích hợp Agent Giám thị hoạt động hoàn toàn ngầm ở Backend.
    - Chuyên đọc và kiểm tra lại câu trả lời do Agent Gia sư tạo ra.
    - Đảm bảo mọi phản hồi tuân thủ nguyên tắc sư phạm (không giải hộ, không chứa đáp án).
  - **Vòng lặp sửa sai tự động (Self-Correction)**:
    - Tự động ép Gia sư viết lại câu khác an toàn hơn nếu phát hiện vi phạm luật.
    - Giữ nguyên trạng thái "Đang suy nghĩ..." ở ngoài UI để không làm học sinh phân tâm.
    - Giới hạn số lần lặp tối đa để tránh treo server.
  - **Xử lý và ghi nhận vi phạm**:
    - Ghi log chi tiết vào bảng Message trong Database khi có vi phạm bị chặn.
    - Trả về một cờ (flag) vi phạm cho Frontend.
    - Hiển thị cảnh báo nhỏ (Toast) trên màn hình một cách tinh tế.
- **Tasks:**
  - [Thông] [AI] Viết prompt và rule cho Giám thị (Reviewer) chấm điểm Gia Sư về mức độ lộ đáp án. (4.5h)
  - [Thông] [AI] Cấu hình tham số Temperature và Top-K cho mô hình Gemini để giảm rủi ro Hallucination. (2h)
  - [Thống] [BE] Code logic agent `reviewer.py` (498 dòng), xử lý vòng lặp yêu cầu AI sinh lại câu nếu vi phạm. (6h)
  - [Thống] [BE] Viết hàm lưu log vi phạm vào bảng Message để phục vụ thống kê. (4h)
  - [Bảo] [FE] Xử lý sự kiện nhận cờ vi phạm từ Backend để hiển thị cảnh báo (Toast) trên màn hình. (4h)
  - [Thiên] [QA] Lên kịch bản test bằng file `Test_Scenarios_All_Agents.xlsx` cho 20 trường hợp chửi thề, toxic. (4h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] AI tự kiểm duyệt:** AI Gia sư lỡ sinh ra câu trả lời chứa đáp án cuối, Khi đó con Giám thị chạy ngầm sẽ chặn lại, vòng lặp tự bắt Gia sư viết lại câu khác an toàn hơn trước khi trả về cho UI.

### US 4.2: Hoạt hình Cú Socratic
*Mô tả: Là một Học sinh, tôi muốn có một trợ lý ảo đồng hành trong suốt quá trình giải toán nhằm tăng tính tương tác.*
- **Mô tả chi tiết:**
  - **Nhân vật ảo đồng hành**:
    - Tích hợp component Cú Socratic bằng Lottie animation ở góc màn hình.
    - Bố trí UI hợp lý để nhân vật không che khuất nội dung chat chính.
    - Hỗ trợ đổi các biểu cảm phong phú, sống động.
  - **Phản hồi cảm xúc theo ngữ cảnh**:
    - Hệ thống AI phân tích câu chat của học sinh để gán nhãn cảm xúc phù hợp.
    - Backend truyền nhãn này xuống Frontend qua luồng streaming.
    - Tự động kích hoạt hoạt ảnh tương ứng (vd: đang nghĩ, gợi ý, khen ngợi).
  - **Trải nghiệm mượt mà không độ trễ**:
    - Frontend xử lý preload và cache các file Lottie.
    - Chuyển đổi giữa các trạng thái hoạt hình diễn ra lập tức.
    - Đảm bảo không gây lag hay giật khựng cho luồng chat đang chạy.
- **Tasks:**
  - [Bảo] [FE] Code component `SocraticOwl.tsx` (134 dòng) dùng Lottie-web hoặc lottie-react. (4h)
  - [Bảo] [FE] Tích hợp logic chuyển đổi các trạng thái animation (`idle`, `thinking`, `hint`, `correct`, `wrong`). (4h)
  - [Thiên] [FE] Tinh chỉnh CSS để cú Socratic nổi bật nhưng không che khuất đoạn hội thoại chính. (3h)
  - [Thiên] [FE] Xử lý hiệu ứng chuyển đổi (transition) ổn định giữa các trạng thái. (3h)
  - [Thông] [AI] Tinh chỉnh Orchestrator để quyết định và trả về cờ trạng thái cảm xúc (emotion flag) trong JSON. (5h)
  - [Thông] [AI] Kiểm thử và điều chỉnh logic phân luồng cảm xúc khớp với ngữ cảnh của học sinh. (4h)
  - [Thông] [QA] Viết script đo lường thời gian trễ do gọi thêm file Lottie ở FE. (3.5h)
  - [Thống] [BE] Cấu trúc luồng dữ liệu Streaming để đẩy cờ trạng thái xuống UI theo thời gian thực. (6h)
  - [Thống] [DevOps] Setup cơ chế Cache tĩnh cho các file Lottie trên server để tránh load lại nhiều lần. (3h)
  - [Thiên] [QA] Chạy kịch bản test E2E trực tiếp cho Cú Socratic và luồng chặn của Reviewer trên đa nền tảng. (5h)
  - [Thiên] [Management] Review PR, họp chốt UI/UX của Cú Socratic và duyệt merge code. (4h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Trạng thái phản hồi:** Hệ thống đang gọi API tới Gemini, Khi đó Cú Socratic trên màn hình chuyển sang trạng thái "thinking" (đang suy nghĩ). Khi có kết quả, Cú tự động đổi sang trạng thái "hint" hoặc "correct".

---

## Sprint 5: Khảo sát Đầu vào & Bảng điều khiển Phụ huynh (03-Oct đến 09-Oct)
*(Phân bổ khối lượng: [Bảo]: 12h, [Thông]: 19h, [Thiên]: 19h, [Thống]: 19h)*

### US 5.1: Khảo sát Đầu vào (Onboarding)
*Mô tả: Là một Học sinh mới, tôi muốn chọn khối lớp và mục tiêu học tập lúc đăng ký để AI có thể hỗ trợ tôi đúng trọng tâm.*
- **Mô tả chi tiết:**
  - **Luồng khảo sát thông tin bắt buộc**:
    - Học sinh mới tạo tài khoản phải đi qua quy trình khảo sát (Stepper đa bước).
    - Tự động chặn và ép quay lại form nếu người dùng cố tình truy cập vào trang Chat.
    - Đảm bảo thu thập đủ thông tin cơ bản trước khi bắt đầu học.
  - **Cập nhật hồ sơ người dùng**:
    - Thu thập các thông tin như khối lớp, mục tiêu, và sở thích.
    - Gửi dữ liệu qua API và lưu chặt chẽ vào Database.
    - Dùng thông tin này để định hình vĩnh viễn "Hồ sơ cá nhân" của học sinh.
  - **Cá nhân hóa AI theo độ tuổi**:
    - Cung cấp "bối cảnh nền" (context) cho AI dựa trên khối lớp thu thập được.
    - Tự động điều chỉnh độ khó của bài toán do AI đưa ra.
    - Tinh chỉnh cách xưng hô và mức độ phức tạp của ngôn từ cho phù hợp với lứa tuổi.
- **Tasks:**
  - [Bảo] [FE] Code luồng giao diện `onboarding/page.tsx` (336 dòng) chia thành nhiều bước (Stepper). (6h)
  - [Thiên] [FE] Code form thu thập thông tin khối lớp, mục tiêu học tập, xử lý state giữa các bước. (4h)
  - [Thống] [BE] Code Next.js API Route `api/user/onboarding/route.ts` để lưu thông tin khảo sát vào DB. (4h)
  - [Thống] [BE] Viết logic chặn người dùng nếu chưa hoàn thành onboarding thì không cho vào trang Chat. (4h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Bắt buộc hoàn thành:** Học sinh vừa tạo tài khoản và cố truy cập `/learn`, Khi đó hệ thống sẽ tự động chuyển hướng về trang `/onboarding`.

### US 5.2: Bảng điều khiển Phụ huynh (Parent Dashboard)
*Mô tả: Là một Phụ huynh, tôi muốn theo dõi được thời gian học và thành tích của con mình trên một giao diện trực quan.*
- **Mô tả chi tiết:**
  - **Giao diện giám sát độc lập**:
    - Xây dựng màn hình Dashboard riêng biệt dành cho tài khoản role Phụ huynh.
    - Tách bạch hoàn toàn UI so với màn hình Chat của học sinh.
    - Tích hợp thanh Sidebar để dễ dàng quản lý và chuyển đổi danh sách con cái.
  - **Trực quan hóa dữ liệu học tập**:
    - Tính toán tổng thời gian học và tần suất tương tác thông qua API.
    - Vẽ các biểu đồ thống kê trực quan (ví dụ: số giờ học theo tuần/tháng).
    - Giúp phụ huynh dễ dàng đánh giá mức độ chuyên cần của con.
  - **Bảo mật và Phân quyền**:
    - Ngăn chặn Phụ huynh tự ý truy cập hoặc thao tác vào màn hình học tập của con.
    - Ngăn chặn Học sinh xem báo cáo tổng thể của phụ huynh.
    - Duy trì tính riêng tư và phân quyền đúng vai trò truy cập.
- **Tasks:**
  - [Bảo] [FE] Code giao diện `parent/page.tsx` (520 dòng) có thanh Sidebar riêng biệt cho Phụ huynh. (6h)
  - [Thiên] [FE] Tích hợp thư viện biểu đồ hiển thị tần suất học tập của con. (4h)
  - [Thống] [BE] Code API `api/parent/children/route.ts` truy xuất danh sách con cái và lịch sử học. (6h)
  - [Thống] [BE] Code API `api/metrics/route.ts` tổng hợp dữ liệu thời gian học theo tuần/tháng. (5h)
  - [Thông] [AI] Phân tích data khảo sát để thiết kế hệ thống Agent Prompts phân tầng theo độ tuổi. (5h)
  - [Thông] [AI] Code module `frontend/lib/agent-prompts.ts` để nạp linh hoạt prompt tùy thuộc vào khối lớp. (6h)
  - [Thông] [AI] Viết prompt test giả lập các học sinh lớp 3, lớp 6, lớp 9 để đánh giá câu trả lời của AI. (4h)
  - [Thông] [QA] Đánh giá chéo chất lượng câu hỏi Socratic cho từng độ tuổi để đảm bảo không quá khó. (4h)
  - [Thiên] [Database] Tối ưu hóa truy vấn SQL (Prisma) cho API metrics để tính tổng điểm nhanh chóng. (4h)
  - [Thiên] [QA] Test kỹ cơ chế phân quyền (Phụ huynh không thể truy cập giao diện Học sinh và ngược lại). (4h)
  - [Thiên] [QA] Chạy Postman kiểm thử giới hạn rate limit của API metrics. (1h)
  - [Thiên] [Management] Cập nhật tài liệu cấu trúc dữ liệu mới và Review PR các màn hình Onboarding/Parent. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Thống kê chính xác:** Học sinh học 3 phiên trong tuần, mỗi phiên 20 phút. Khi phụ huynh mở Dashboard, Thì biểu đồ hiển thị chính xác tổng 60 phút học tập trong tuần đó.
  - **[AC2] AI thích ứng độ tuổi:** Học sinh chọn khối lớp 3, Khi đó câu trả lời của AI sẽ dùng ngôn từ đơn giản, dễ hiểu hơn so với học sinh khối lớp 9.

---

## Sprint 6: Nâng cấp Trải nghiệm & Hoàn thiện Hệ thống (10-Oct đến 16-Oct)
*(Phân bổ khối lượng: [Bảo]: 16h, [Thông]: 19h, [Thiên]: 19h, [Thống]: 19h)*

### US 6.1: Đo lường Điểm Tự Lực & Dashboard Phụ Huynh Nâng Cao
*Mô tả: Là một phụ huynh, tôi muốn theo dõi điểm tự lực (Independence/Mastery Score) và sự tiến bộ của con qua các biểu đồ chi tiết trên Dashboard, để nắm bắt mức độ học tập độc lập của con mà không cần phụ thuộc quá nhiều vào gợi ý.*
- **Mô tả chi tiết:**
  - **Chấm điểm tự lực tự động**:
    - AI ngầm phân tích quá trình hội thoại và đếm số lượng gợi ý học sinh đã dùng.
    - Quy đổi thành điểm "Independence" dựa trên barem nội bộ (0 gợi ý → 100đ, nhiều gợi ý → điểm giảm dần).
    - Đánh giá ngay sau khi học sinh bấm "Đã hiểu" (hoàn thành bài toán).
  - **Lưu trữ & Cập nhật tiến độ**:
    - API `api/independence` tiếp nhận điểm từ AI và lưu vào DB.
    - Ghi nhận lịch sử điểm số theo từng phiên học để phục vụ phân tích xu hướng.
    - Cập nhật tiến trình Mastery trên Sidebar Chat để học sinh theo dõi mức độ tích lũy.
  - **Trực quan hóa trên Dashboard Phụ huynh**:
    - **Summary Cards** (4 thẻ tóm tắt): Tổng bài hoàn thành, Điểm Independence trung bình, Streak học liên tiếp (ngày), Tổng giờ học tuần này.
    - **Line Chart điểm Independence** theo thời gian (ngày): Xu hướng điểm tự lực qua các ngày học để phụ huynh thấy con ngày càng tự lập.
    - **Activity Heatmap**: Biểu đồ nhiệt theo dõi mật độ và khung giờ học tập của con trong tuần/tháng.
    - **Dropdown lọc thời gian**: 7 ngày / 30 ngày → tất cả biểu đồ và chỉ số tự cập nhật.
- **Tasks:**
  - **T6.1** [Thông] [AI] Xây dựng thuật toán ngầm đánh giá tự lực: đếm số Hint dùng, số lần "Chưa hiểu", thời gian giải → tính điểm. (5h)
  - **T6.2** [Thông] [AI] Xây dựng barem điểm Independence: 0 gợi ý → 100đ, nhiều gợi ý → điểm giảm dần. Xuất kết quả dạng JSON. (2h)
  - **T6.3** [Thống] [BE] Code API `api/independence/route.ts` để tiếp nhận điểm từ AI và lưu vào DB. (3h)
  - **T6.4** [Thống] [BE] Sửa luồng bấm "Đã hiểu" trong API `/chat`: kích hoạt tính điểm và gọi T6.3 lưu kết quả. (2h)
  - **T6.5** [Bảo] [FE] Hiển thị thanh tiến trình Mastery trên Sidebar Chat: cập nhật real-time khi điểm mới về. (3h)
  - **T6.6** [Thiên] [FE] Code UI component `<ActivityHeatmap />` (biểu đồ nhiệt hoạt động học theo ngày) cho Parent Dashboard với Recharts. (2h) *(Bắt đầu ngay — UI tĩnh)*
  - **T6.7** [Thông] [AI/BE] Xây dựng Pydantic Schemas chuẩn hóa dữ liệu điểm tự lực & metrics học tập cho Parent Dashboard. (2h)
  - **T6.8** [Thiên] [FE] Code UI Summary Cards (4 thẻ) + Dropdown lọc thời gian cho Parent Dashboard. Build UI tĩnh trước. (3h) *(Bắt đầu ngay — UI tĩnh)*
  - **T6.9** [Thiên] [FE] Tích hợp Line chart điểm Independence trên Parent Dashboard với Recharts, ráp nối API metrics khi backend hoàn tất. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Tính & Lưu điểm tự lực:** Học sinh giải bài với 0–2 gợi ý → bấm "Đã hiểu" → API lưu điểm vào DB, điểm số được ghi nhận vào tiến trình học tập của học sinh.
  - **[AC2] Phân hóa theo mức độ trợ giúp:** Học sinh bấm "Chưa hiểu" 3 lần, dùng nhiều Hint → điểm Independence được tính thấp hơn tương ứng với mức độ trợ giúp.
  - **[AC3] Hiển thị trên Dashboard Phụ huynh:** Phụ huynh vào trang Dashboard thấy 4 thẻ tóm tắt (trong đó có Điểm Independence TB), biểu đồ đường (Line Chart) thể hiện sự thay đổi điểm tự lực qua các ngày và biểu đồ nhiệt (Heatmap) thể hiện mức độ chuyên cần.
  - **[AC4] Lọc thời gian:** Chuyển bộ lọc 7 ngày / 30 ngày → dữ liệu và các biểu đồ cập nhật chính xác.

### US 6.2: Fix Lỗi Tab Ẩn Danh Không Đồng Bộ Dữ Liệu Lớp
*Mô tả: Là một học sinh, khi đăng nhập cùng 1 tài khoản ở tab ẩn danh và tab thường, tôi muốn thông tin lớp học của mình được đồng bộ chính xác ở cả 2 tab, không bị lệch dữ liệu khi cập nhật.*

> ⚠️ US này chỉ có [Thiên] (FE) và [Thống] (BE) thực hiện.

- **Mô tả chi tiết:**
  - **Nguyên nhân gốc rễ**: Tab ẩn danh dùng storage riêng biệt với tab thường. Khi cập nhật `grade_level` ở tab thường, tab ẩn danh vẫn giữ session cũ → AI nhận sai lớp.
  - **Giải pháp phía Backend**: Thêm `session_version` vào DB. Mỗi khi cập nhật `grade_level` → tăng version. Mỗi request chat → middleware kiểm tra version token vs DB.
  - **Giải pháp phía Frontend**:
    - Khi nhận flag `SESSION_STALE` → tự gọi `update()` của NextAuth để refresh session mà **không đăng xuất**.
    - Dùng `BroadcastChannel API` để thông báo sang các tab cùng browser (không ẩn danh) cập nhật ngay.
- **Tasks:**
  - **T6.10** [Thống] [BE] Thêm trường `session_version` (integer) vào bảng User, tạo migration. (2h)
  - **T6.11** [Thống] [BE] Sửa middleware API `/chat`: Kiểm tra `session_version` token vs DB. Nếu lệch → trả `401` kèm body `{ error: "SESSION_STALE" }`. (3h)
  - **T6.12** [Thiên] [FE] Làm `BroadcastChannel` trong trang Settings: Sau khi cập nhật lớp thành công → broadcast event `GRADE_UPDATED` sang các tab cùng browser để trigger `update()`. (2h) *(Bắt đầu ngay — chỉ sửa Settings page)*
  - **T6.13** [Thiên] [FE] Xử lý flag `SESSION_STALE` trong fetch wrapper: Khi nhận `401 SESSION_STALE` → tự gọi `update()` của NextAuth → retry request. (3h)
  - **T6.14** [Thiên] [QA] Test kịch bản tab ẩn danh & tab thường đồng bộ lớp không cần logout, kiểm tra không có regression auth, review PR & merge. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Đồng bộ tab cùng browser (không ẩn danh):** Mở 2 tab thường. Đổi lớp ở tab 1. Gửi tin nhắn ở tab 2 → AI nhận đúng lớp mới, không cần đăng xuất.
  - **[AC2] Đồng bộ tab ẩn danh:** Đổi lớp ở tab thường. Vào tab ẩn danh gửi tin nhắn → hệ thống tự phát hiện session lỗi thời → tự refresh → AI nhận đúng lớp mới.
  - **[AC3] Không logout bắt buộc:** Quá trình đồng bộ xảy ra tự động, người dùng KHÔNG bị văng ra màn hình đăng nhập.

### US 6.3: Thông Báo Idle & Dừng Tính Giờ Học
*Mô tả: Là một phụ huynh, tôi muốn thời gian học của con được tính chính xác — nếu con không tương tác 10 phút, hệ thống dừng tính giờ và nhắc con có còn học không, để Dashboard không báo sai số giờ học.*
- **Mô tả chi tiết:**
  - **Phát hiện không hoạt động (Idle Detection)**:
    - Đếm thời gian kể từ lần **gửi tin nhắn** cuối cùng.
    - Sau **10 phút không gửi** → hiển thị modal: *"Bạn vẫn còn đang học chứ? 🦉"* và **dừng tính giờ** ngay từ lúc đó.
  - **Tiếp tục học**:
    - Học sinh bấm **"Đang học"** → modal đóng, **tiếp tục tính giờ** từ thời điểm bấm nút.
    - Nếu không bấm → giờ học vẫn dừng mãi cho đến khi có hành động tiếp theo.
  - **Liên tục theo dõi**: Cứ 10 phút idle tiếp theo lại hiện lại thông báo.
- **Tasks:**
  - **T6.15** [Bảo] [FE] Viết Hook `useIdleTimer(timeout: 10min)`: Dùng `setTimeout` reset mỗi khi `onSendMessage` được gọi. Khi timeout → dispatch event `IDLE_DETECTED`. (3h)
  - **T6.16** [Bảo] [FE] Làm UI Modal thông báo *"Bạn vẫn đang học chứ?"*: Overlay mờ nền, nút **"Đang học"** để tiếp tục. Khi bấm nút → gửi timestamp restart lên BE và reset timer. (2h)
  - **T6.17** [Thống] [BE] Sửa API `api/metrics`: Thay vì tính `end_time - start_time` toàn session, chỉ cộng các khoảng `active_seconds` thực sự (exclude thời gian idle). (3h)
  - **T6.18** [Thống] [BE] Nhận timestamp restart từ FE khi học sinh bấm "Đang học" → ghi nhận khoảng active mới vào DB. (2h)
  - **T6.19** [Thiên] [QA] Test E2E Idle Detection: Vào chat, không gửi tin 10 phút → modal xuất hiện. Bấm "Đang học" → tiếp tục 5 phút → lên Dashboard Phụ huynh → biểu đồ chỉ ghi nhận ~5 phút, không tính 10 phút idle. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Hiện thông báo:** Vào chat, gửi 1 tin nhắn rồi để yên 10 phút → Modal *"Bạn vẫn đang học chứ?"* xuất hiện với nút "Đang học".
  - **[AC2] Tính giờ chính xác:** Bấm "Đang học" → tiếp tục tương tác 5 phút → Dashboard Phụ huynh chỉ ghi ~5 phút (không tính 10 phút idle).
  - **[AC3] Lặp lại:** Sau khi bấm "Đang học", nếu lại không gửi tin 10 phút → modal xuất hiện lần nữa.

### US 6.4: Đính Kèm Ảnh & Chụp Ảnh Qua Chat
*Mô tả: Là một học sinh, tôi muốn gửi ảnh bài toán (chụp vở, ảnh sẵn có trên máy) lên chat để AI có thể đọc nội dung và hỗ trợ tôi giải theo phương pháp Socratic.*
- **Mô tả chi tiết:**
  - **Trên máy tính (Desktop)**:
    - Nhấn dấu **`+`** bên cạnh ô nhập liệu → mở dialog chọn file ảnh (PNG, JPG, WEBP).
    - Hỗ trợ **Paste ảnh** trực tiếp từ clipboard (`Ctrl+V` / `Cmd+V`) vào ô chat.
    - Preview ảnh nhỏ trong ô nhập trước khi gửi, có nút X để xóa.
  - **Trên điện thoại (Mobile)**:
    - Nhấn dấu **`+`** → hiện menu 2 lựa chọn:
      - 📷 **Camera**: Mở camera chụp ngay (`capture="environment"`).
      - 🖼️ **Thư viện ảnh**: Chọn ảnh sẵn có trên thiết bị.
  - **Xử lý phía Backend & AI (Cloudinary Storage Pipeline)**:
    - Frontend tải ảnh lên dịch vụ lưu trữ đám mây **Cloudinary** (miễn phí 25 credits ~ 10-15GB lưu trữ, trọn đời), nhận về đường link HTTPS công khai (CDN siêu tốc).
    - Database Neon chỉ lưu chuỗi link URL ảnh (`attachmentUrl`) trong bảng `ChatMessage`, giúp DB siêu nhẹ (chỉ tốn ~80 bytes/ảnh) và không lo đầy bộ nhớ.
    - Backend lấy dữ liệu ảnh từ Cloudinary nạp vào Gemini model **`gemini-3.5-flash-lite`**.
    - AI đọc ảnh toán học và phản hồi Socratic (trích xuất đề bài LaTeX + gợi ý bước 1, tuyệt đối không giải thẳng đáp án).
- **Tasks:**
  - **T6.20** [Bảo] [FE] Nâng cấp `ChatInput.tsx`: Thêm handler `onPaste` nhận ảnh từ clipboard. Tích hợp `<input type="file" accept="image/*">` ẩn, kích hoạt bằng nút `+`. Hiển thị thumbnail preview + nút X để gỡ ảnh. Tích hợp upload ảnh lên Cloudinary lấy link URL. (5h)
  - **T6.21** [Bảo] [FE] Mobile Bottom Sheet khi bấm `+`: Hiện 2 lựa chọn — *Camera* (`<input capture="environment">`) và *Thư viện* (`<input>` không có `capture`). Tích hợp upload Cloudinary đồng bộ với Desktop. (3h)
  - **T6.22** [Thống] [BE] Tích hợp Cloudinary SDK & Cập nhật API/DB: Cấu hình Cloudinary SDK trên Backend, cung cấp API upload/ký chữ ký ảnh an toàn. Cập nhật bảng `ChatMessage` lưu trường `attachmentUrl` dạng link HTTPS Cloudinary (DB siêu nhẹ). (4h)
  - **T6.23** [Thông] [AI] Tích hợp Gemini Vision xử lý ảnh từ Cloudinary URL: Nạp ảnh từ Cloudinary vào payload gọi `gemini-3.5-flash-lite` trong Tutor Agent. Phối hợp Prompt Socratic Vision để AI trích xuất đề và hỏi gợi mở, không lộ đáp số. (4h)
  - **T6.24** [Thông] [AI] Nghiên cứu Gemini Multimodal API (đọc docs, test qua Postman với ảnh Cloudinary/Base64), viết bộ test cases đọc ảnh toán học với model `gemini-3.5-flash-lite`. (6h)
  - **T6.25** [Thiên] [QA] Test toàn diện: Paste ảnh Ctrl+V desktop, upload file, chụp camera mobile, chọn thư viện mobile. Kiểm tra ảnh hiển thị mượt mà từ CDN Cloudinary, kiểm tra AI Socratic không lộ đáp số. Test edge cases (>5MB, sai định dạng). Review & hoàn tất Sprint 6. (3h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Paste ảnh trên Desktop:** Nhấn `Ctrl+V` (hoặc `Cmd+V`) vào ô chat → ảnh bài toán hiển thị preview nhỏ kèm nút X để xóa. Bấm gửi → ảnh xuất hiện trong bong bóng chat, AI đọc đúng đề bài và phản hồi câu hỏi gợi mở bước 1 (tuyệt đối không lộ đáp số).
  - **[AC2] Chọn file ảnh trên Desktop:** Bấm nút **`+`** bên cạnh ô nhập liệu → mở hộp thoại chọn file trên máy tính → chọn ảnh bài toán (PNG, JPG, WEBP) → ảnh hiện preview trong ô nhập → bấm gửi → tin nhắn kèm ảnh xuất hiện trong khung chat và AI phản hồi Socratic.
  - **[AC3] Chụp ảnh trực tiếp trên Mobile:** Trên điện thoại, bấm nút **`+`** → menu xuất hiện → chọn **Camera** → camera điện thoại mở lên chụp ảnh → ảnh xuất hiện trong khung chat và gửi cho AI thành công.
  - **[AC4] Chọn ảnh từ Thư viện trên Mobile:** Trên điện thoại, bấm nút **`+`** → chọn **Thư viện ảnh** → thư viện ảnh trên máy mở ra → chọn ảnh bài toán → ảnh xuất hiện trong khung chat và gửi đi thành công.
  - **[AC5] Kiểm tra định dạng & dung lượng (Validation):** Khi chọn hoặc dán file nặng quá 5MB hoặc file không phải là ảnh (như PDF, DOCX) → giao diện lập tức hiện thông báo lỗi *"Chỉ hỗ trợ ảnh dưới 5MB"* và không cho gửi.
  - **[AC6] Xem lại ảnh trong lịch sử chat:** Tải lại trang (F5) hoặc mở lại danh sách phiên trò chuyện cũ → toàn bộ ảnh bài tập đã gửi trước đó vẫn hiển thị đầy đủ, rõ nét trong khung chat.

### 📌 Sơ Đồ Phụ Thuộc Task – Sprint 6

**US 6.1 (Điểm Tự Lực & Dashboard Phụ Huynh)**
```
T6.1 (Thông: Thuật toán) ──► T6.2 (Thông: Barem điểm)
T6.3 (Thống: API independence) ──► T6.4 (Thống: Sửa /chat)
                                         ├──► T6.5 (Bảo: FE Progress bar)
                                         └──► T6.9 (Thiên: FE Line chart)
T6.6 (Thiên: Activity Heatmap UI tĩnh) ← Độc lập, làm ngay Day 1
T6.7 (Thông: Xây dựng Pydantic Schemas metrics)
T6.8 (Thiên: Summary Cards UI tĩnh) ← Độc lập, làm ngay Day 1
T6.8 + T6.7 + T6.3 ──► T6.9 (Thiên: FE Line chart Recharts)
```

**US 6.2 (Fix Tab Ẩn Danh) — Chỉ Thiên + Thống**
```
T6.10 (Thống: session_version DB) ──► T6.11 (Thống: Middleware SESSION_STALE)
                                            └──► T6.13 (Thiên: FE auto refresh)
T6.12 (Thiên: BroadcastChannel) ← Độc lập, làm ngay Day 1
T6.11 + T6.12 + T6.13 ──► T6.14 (Thiên: QA & Merge)
```

**US 6.3 (Idle Detection)**
```
T6.15 (Bảo: Hook useIdleTimer) ──► T6.16 (Bảo: Modal UI)
T6.17 (Thống: API active_seconds) ──► T6.18 (Thống: Timestamp restart)
T6.16 + T6.18 ──► T6.19 (Thiên: QA)
```

**US 6.4 (Đính kèm ảnh - Cloudinary Storage Pipeline)**
```
T6.20 (Bảo: FE paste+upload Cloudinary) ──► T6.21 (Bảo: FE mobile bottom sheet)
T6.22 (Thống: BE Cloudinary SDK + DB URL)
T6.24 (Thông: Research Vision Cloudinary) ──► T6.23 (Thông: Gemini Vision + Socratic Prompt)
T6.20 + T6.22 + T6.23 ──► T6.25 (Thiên: QA & Tổng kết)
```

**Tóm tắt phân công cuối cùng:**
| Thành viên | Giờ | Tasks |
|---|---|---|
| **[Bảo]** | 16h | T6.5 (3h) + T6.15 (3h) + T6.16 (2h) + T6.20 (5h) + T6.21 (3h) |
| **[Thống]** | 19h | T6.3 (3h) + T6.4 (2h) + T6.10 (2h) + T6.11 (3h) + T6.17 (3h) + T6.18 (2h) + T6.22 (4h) |
| **[Thông]** | 19h | T6.1 (5h) + T6.2 (2h) + T6.7 (2h) + T6.23 (4h) + T6.24 (6h) |
| **[Thiên]** | 19h | T6.6 (2h) + T6.8 (3h) + T6.9 (2h) + T6.12 (2h) + T6.13 (3h) + T6.14 (2h) + T6.19 (2h) + T6.25 (3h) |

> ⭐ **Thiên bắt đầu ngay Day 1 (không cần đợi ai):** T6.6 (Activity Heatmap UI tĩnh: 2h) → T6.8 (Summary Cards UI tĩnh: 3h) → T6.12 (BroadcastChannel Settings: 2h)

---

## Sprint 7: Nâng Cấp Phụ Huynh, Game Hóa Học Sinh & Toàn Diện Frontend Admin Portal (17-Oct đến 23-Oct)
*(Phân bổ khối lượng: [Bảo]: 20.5h, [Thông]: 20h, [Thiên]: 21h, [Thống]: 20h)*

**Quy định phân chia vai trò Frontend tránh chồng chéo:**
- **US 7.1 (Phụ huynh)**: Chỉ **[Thiên]** làm Frontend (`AIInsightsCard.tsx`, `SummaryCards.tsx`, `ChildProblemHistory.tsx`). [Bảo] chỉ đóng vai trò kiểm thử UX sư phạm.
- **US 7.2 (Học sinh)**: Chỉ **[Bảo]** làm Frontend (`StreakBadge.tsx`, `BadgeModal.tsx`, `NotebookPage.tsx`, `BookmarkChatDrawer.tsx`). [Thiên] phụ trách Database index và QA.
- **US 7.3 (Admin Portal)**: 
  - **[Bảo]** thiết kế toàn bộ hệ thống UI/UX Trang Admin trên Figma/Wireframe.
  - **Code Frontend chia theo trang cụ thể**: 
    - [Thiên] code: Layout tổng thể (`admin/layout.tsx`, `AdminSidebar.tsx`), Dashboard KPI (`admin/page.tsx`), Giám sát an toàn (`admin/safety/page.tsx`), Cài đặt (`admin/settings/page.tsx`).
    - [Bảo] code: Quản lý người dùng (`admin/users/page.tsx`), Quản lý học liệu (`admin/content/page.tsx`), Rà soát 100% kết nối nút bấm (`click-through router`).

---

### US 7.1: Nâng Cấp Toàn Diện Dashboard Phụ Huynh (AI Learning Insights, Sổ Theo Dõi Bài Tập & Nối Data Thật)
*Mô tả: Là một Phụ huynh, tôi muốn nhận được nhận xét sư phạm tự động từ AI, xem chi tiết lịch sử từng bài toán con đã giải và theo dõi số liệu học tập hoàn toàn chính xác (không dùng dữ liệu giả lập), để tôi nắm bắt kịp thời năng lực và điểm yếu của con mà không cần đọc từng dòng chat.*
- **Mô tả chi tiết:**
  - **Nhận xét sư phạm tự động từ AI (AI Learning Insights)**:
    - Cuối ngày hoặc cuối tuần, hệ thống tổng hợp toàn bộ các bài toán con đã hoàn thành, điểm tự lập và số lần bấm "Chưa hiểu".
    - Gemini phân tích và xuất ra 1 đoạn nhận xét cô đọng: Điểm mạnh, dạng bài còn lúng túng, số gợi ý trung bình, và lời khuyên sư phạm thiết thực cho cha mẹ.
  - **Sổ theo dõi bài tập của con (Child Problem & Session History)**:
    - Hiển thị danh sách các bài toán con đã giải theo ngày/tuần dạng timeline hoặc danh sách thẻ trực quan.
    - Mỗi bài hiển thị: Tên dạng toán (Hình học, Phân số, Tìm X...), ảnh đề bài con đã chụp (thumbnail Cloudinary có thể click phóng to), điểm tự lập đạt được (0-100), số lần bấm "Chưa hiểu".
    - Cho phép phụ huynh bấm vào để xem lại đoạn hội thoại đối thoại ngắn giữa AI và con để hiểu cách con tư duy.
  - **Xóa bỏ dữ liệu Mock – Nối 100% dữ liệu thật từ Database**:
    - **Heatmap thật**: API `/metrics/heatmap` quét bảng `session_active_intervals` theo từng ngày trong năm để tô màu chuyên cần chuẩn GitHub cho phụ huynh.
    - **Summary Cards thật**: Tính tổng số bài hoàn thành dựa trên số bản ghi trong bảng `independence_scores`, tính chuỗi ngày học thật (Streak) thay thế toàn bộ mock cứng.
- **Tasks:**
  - **T7.1** [P0 - Critical] [Thông] [AI] Nghiên cứu & Thiết kế Prompt Gemini sinh Báo cáo Nhận xét Sư phạm (AI Learning Insights) cho phụ huynh dựa trên tổng số bài, dạng toán và điểm tự lực. (3h)
  - **T7.2** [P0 - Critical] [Thông] [AI] Chuẩn hóa Pydantic Schema cho AI Insights (`AiInsightReportResponse`: strengths, weak_points, recommendations, summary). (1.5h)
  - **T7.3** [P1 - High] [Thống] [BE] Viết hàm background service quét dữ liệu tuần của học sinh, gọi Gemini sinh AI Insights và lưu vào bảng `parent_ai_insights`. (2.5h)
  - **T7.4** [P1 - High] [Thống] [BE] Code API `/metrics/heatmap` quét bảng `session_active_intervals` tính tổng thời gian active từng ngày trong 16-24 tuần. (2.5h)
  - **T7.5** [P1 - High] [Thống] [BE] Code API `/metrics/summary` tính toán số liệu thật cho Summary Cards (tổng bài hoàn thành từ `independence_scores`, chuỗi ngày học Streak liên tiếp). (2h)
  - **T7.6** [P1 - High] [Thống] [BE] Code API `/parent/child-problems` trả về danh sách bài tập con đã giải kèm ảnh đề bài Cloudinary, điểm tự lực và đoạn chat tóm tắt. (2.5h)
  - **T7.7** [P1 - High] [Thiên] [FE] Code component `<AIInsightsCard />` (khối nhận xét AI thông minh có icon trực quan, huy hiệu đánh giá và lời khuyên sư phạm). (2.5h)
  - **T7.8** [P1 - High] [Thiên] [FE] Nối API thật xóa bỏ mock trong `SummaryCards.tsx` và cấu hình lại `ActivityHeatmap.tsx` nhận dữ liệu thật từ `/metrics/heatmap`. (2.5h)
  - **T7.9** [P1 - High] [Thiên] [FE] Code component `<ChildProblemHistory />` (320 dòng): danh sách timeline bài tập con đã giải, tích hợp modal phóng to ảnh Cloudinary và popup xem đoạn đối thoại tư duy của con. (3h)
  - **T7.10** [P2 - Medium] [Bảo] [UX/QA] Đóng vai phụ huynh khó tính: Lên kịch bản kiểm thử trải nghiệm xem báo cáo, kiểm tra tính dễ hiểu của các thuật ngữ sư phạm trên điện thoại. (1.5h)
  - **T7.11** [P2 - Medium] [Thiên] [QA] Viết kịch bản test E2E: Học sinh giải 3 bài thật -> Phụ huynh F5 thấy ngay điểm tự lập cập nhật, heatmap đổi màu, AI insight phân tích đúng dạng bài. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] AI Learning Insights:** Phụ huynh vào trang Monitor thấy khối nhận xét AI nêu rõ điểm mạnh, điểm yếu và lời khuyên dành cho con dựa trên dữ liệu thật.
  - **[AC2] Lịch sử bài tập chi tiết:** Danh sách bài tập của con hiển thị đầy đủ tên bài, điểm tự lực, ảnh đề bài chụp và bấm vào đọc được đoạn hội thoại giải bài của con.
  - **[AC3] 100% Data thật:** Summary Cards và Heatmap lấy dữ liệu thực tế từ DB, không còn số liệu mock `completedProblems: 18` hay `generateMockHeatmapData`.
  - **[AC4] UX thân thiện:** Thuật ngữ nhận xét sư phạm gần gũi, giao diện responsive mượt mà trên cả máy tính lẫn smartphone.

---

### US 7.2: Cơ Chế Game Hóa & Sổ Tay Bài Toán Yêu Thích Cho Học Sinh (Streak 🔥, Huy Hiệu & Bookmark Notebook)
*Mô tả: Là một Học sinh, tôi muốn theo dõi chuỗi ngày học liên tục (Streak), mở khóa các huy hiệu tự lập và có Sổ tay lưu lại các bài toán yêu thích, để tôi có động lực học tập mỗi ngày và dễ dàng ôn tập lại trước kỳ thi.*
- **Mô tả chi tiết:**
  - **Cơ chế Game hóa (Streak 🔥 & Huy hiệu Tự Lập)**:
    - Hiển thị biểu tượng ngọn lửa hoạt hình Streak 🔥 kèm số ngày học liên tục ở góc trên khung chat.
    - Hệ thống huy hiệu khích lệ:
      * 🏅 *Tự lập nhí*: Hoàn thành bài toán với 100 điểm tự lực (0 gợi ý).
      * 🔥 *Kiên trì*: Học liên tục 3 ngày không gián đoạn.
      * 📸 *Thám tử hình ảnh*: Tải lên và giải bài toán đầu tiên bằng ảnh.
    - Modal chúc mừng khi học sinh mở khóa được huy hiệu mới với hiệu ứng pháo hoa vui nhộn.
  - **Sổ tay bài toán yêu thích (Bookmark Notebook)**:
    - Sau khi hoàn thành bài toán và bấm "Đã hiểu", xuất hiện nút **⭐ "Lưu vào Sổ tay"**.
    - Tab **"📖 Sổ tay"** hiển thị danh sách các bài đã lưu dưới dạng Thẻ Flashcard (Đề bài, Ảnh chụp, Bí kíp cần nhớ do AI đúc kết, Đáp số cuối cùng).
    - Nút **`[💬 Xem lại đoạn chat]`**: Mở ngăn kéo (Drawer) hiển thị ĐÚNG đoạn chat từ câu học sinh hỏi đề bài đến lúc bấm "Đã hiểu".
    - **Lọc thông minh qua Gemini (Boundary Extraction)**: Nếu bài trước đó bị bỏ dở hoặc học sinh đổi bài giữa chừng, Gemini tự động nhận diện và chỉ trích xuất đúng các tin nhắn của bài toán vừa hoàn thành, loại bỏ hoàn toàn các câu chat của bài cũ bỏ dở.
- **Tasks:**
  - **T7.12** [P0 - Critical] [Thống] [BE] Thiết kế Model `Bookmark` trong `models.py` (lưu snapshot tin nhắn, ảnh đề bài, bí kíp, đáp số, `independence_score_id`) và tạo DB migration. (2.5h)
  - **T7.13** [P1 - High] [Thống] [BE] Code API CRUD `/bookmarks`: Tạo bookmark, lấy danh sách theo học sinh/chủ đề, xóa bookmark, lấy chi tiết bookmark. (3h)
  - **T7.14** [P1 - High] [Thống] [BE] Code logic tính Streak 🔥 liên tục theo ngày và bảng `student_badges` ghi nhận mở khóa huy hiệu (Tự lập nhí 100đ, Kiên trì 3 ngày, Thám tử hình ảnh). (2.5h)
  - **T7.15** [P0 - Critical] [Thông] [AI] Xây dựng logic Gemini tự nhận diện ranh giới bài toán (Boundary Extraction): Lọc đúng tin nhắn từ đề bài đến câu chúc mừng, tự loại bỏ bài cũ bỏ dở nếu học sinh đổi đề giữa chừng. (3h)
  - **T7.16** [P1 - High] [Thông] [AI] Viết Prompt Gemini tự động trích xuất Đề bài, Bí kíp cốt lõi (1-2 công thức) và Đáp số chốt để tạo dữ liệu Thẻ Flashcard. (2.5h)
  - **T7.17** [P1 - High] [Bảo] [FE] Nâng cấp khung Chat: Thêm nút ⭐ "Lưu vào Sổ tay" xuất hiện ngay dưới bong bóng chúc mừng của AI sau khi học sinh bấm "Đã hiểu". (2h)
  - **T7.18** [P1 - High] [Bảo] [FE] Code UI biểu tượng ngọn lửa hoạt hình Streak 🔥 ở header chat và Modal chúc mừng mở khóa Huy hiệu (`BadgeModal.tsx`) với hiệu ứng pháo hoa. (2h)
  - **T7.19** [P1 - High] [Bảo] [FE] Code Trang Sổ tay (`/dashboard/notebook/page.tsx` - 310 dòng): Giao diện lưới thẻ Flashcard hiện đại, bộ lọc theo môn/dạng toán, nút xem ảnh bài tập phóng to. (3h)
  - **T7.20** [P1 - High] [Bảo] [FE] Code Drawer ngăn kéo xem lại đoạn chat (`BookmarkChatDrawer.tsx`): Tái sử dụng `ChatMessage.tsx` hiển thị đúng mảng tin nhắn của riêng bài đó. (2.5h)
  - **T7.21** [P2 - Medium] [Thiên] [Database] Tối ưu hóa Index cho bảng `bookmarks` (`student_id`, `created_at`) và chạy script migration an toàn trên Neon DB. (1.5h)
  - **T7.22** [P2 - Medium] [Thông] [QA] Đóng vai học sinh: Test kịch bản 20 tình huống lưu bài (giải xong bài 1 lưu bài 1; giải dở bài 1 nhảy sang bài 2 bấm lưu bài 2 xem có bị lẫn tin nhắn không). (2.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Streak & Badges:** Học sinh học ngày thứ 2 liên tiếp thì Streak tăng lên 2 🔥; khi giải bài đạt 100đ thì nhận thông báo mở khóa huy hiệu "Tự lập nhí".
  - **[AC2] Lưu Sổ tay chính xác:** Bấm "⭐ Lưu bài" thì bài toán xuất hiện trong tab Sổ tay với đầy đủ đề bài, ảnh và bí kíp tóm tắt.
  - **[AC3] Xem lại đoạn chat không lẫn bài cũ:** Bấm xem lại đoạn chat trong Sổ tay chỉ hiển thị các câu của riêng bài đó, kể cả trước đó học sinh có bỏ dở một bài khác.
  - **[AC4] Hiệu năng:** Mở drawer xem lại đoạn chat mở tức thì dưới 0.2s nhờ dùng chat snapshot JSON độc lập.

---

### US 7.3: Thiết Kế & Xây Dựng Toàn Diện Giao Diện Quản Trị Hệ Thống (Admin Portal Frontend)
*Mô tả: Là một Quản trị viên, tôi muốn có một giao diện Admin hoàn chỉnh, đẹp mắt với đầy đủ các trang và điều hướng nút bấm mượt mà, để sẵn sàng quản lý người dùng, nội dung và giám sát hệ sinh thái SocraticKid.*
- **Mô tả chi tiết:**
  - **Yêu cầu kỹ thuật**:
    - Tập trung hoàn thiện 100% phần **Thiết kế & Code Frontend** cho toàn bộ cổng Admin (chưa cần ráp luồng xử lý database bên trong).
    - Tất cả các trang từ lớn đến nhỏ, từ chính đến phụ đều phải được dựng trang đầy đủ.
    - **Ấn vào bất kỳ button, menu item hay link nào đều phải chuyển trang đúng**, có trạng thái loading, modal mẫu hoặc thông báo trực quan.
  - **Hệ thống các màn hình Admin cần xây dựng**:
    1. **Layout Admin tổng thể** (`admin/layout.tsx`): Sidebar quản trị chuyên nghiệp, Header hiển thị thông tin Admin, Breadcrumbs điều hướng.
    2. **Dashboard Thống kê Tổng quan** (`admin/page.tsx`): Thẻ KPI (Tổng Users, Học sinh, Phụ huynh, Phiên chat), biểu đồ tăng trưởng người dùng (DAU/MAU) và biểu đồ lượng token AI tiêu thụ.
    3. **Quản lý Người dùng** (`admin/users/page.tsx`): Bảng dữ liệu người dùng (Học sinh, Phụ huynh), thanh tìm kiếm, bộ lọc vai trò, nút xem chi tiết tài khoản và nút Khóa/Mở khóa tài khoản.
    4. **Quản lý Chủ đề Học liệu** (`admin/content/page.tsx`): Danh sách chủ đề Toán lớp 4-9, nút "Thêm chủ đề mới" mở Modal, nút chỉnh sửa và xóa bài học mẫu.
    5. **Giám sát An toàn & Chất lượng AI** (`admin/safety/page.tsx`): Danh sách cảnh báo vi phạm ngôn từ, nhật ký các câu hỏi bị chặn bởi Safety Agent, thống kê tỷ lệ học sinh bấm "Chưa hiểu".
    6. **Cài đặt Hệ thống** (`admin/settings/page.tsx`): Giao diện cấu hình tham số AI (chọn Model, giới hạn token, nhiệt độ sáng tạo temperature) và thông tin phiên bản.
- **Tasks:**
  - **T7.23** [P0 - Critical] [Bảo] [Design] Thiết kế toàn bộ Design System & Mockup Figma cho Admin Portal: Hệ màu quản trị đồng bộ nhận diện SocraticKid (Màu cam chủ đạo #C1762A / Warm Amber / Nền kem #F7ECE1), typography, bộ icon, các layout con. (3h)
  - **T7.24** [P0 - Critical] [Thiên] [FE] Dựng khung Admin Layout tổng thể (`admin/layout.tsx`, `AdminSidebar.tsx`, `AdminHeader.tsx`, `Breadcrumbs.tsx`) với cơ chế chuyển tab mượt mà. (2.5h)
  - **T7.25** [P1 - High] [Thiên] [FE] Code Trang Dashboard Thống kê Tổng quan (`admin/page.tsx` - 280 dòng): 4 thẻ KPI tổng, biểu đồ DAU/MAU và biểu đồ tiêu thụ Token AI (Recharts). (2.5h)
  - **T7.26** [P1 - High] [Bảo] [FE] Code Trang Quản lý Người dùng (`admin/users/page.tsx` - 320 dòng): Data Table danh sách user, thanh search, bộ lọc role, badge trạng thái, modal chi tiết user và nút Khóa/Mở tài khoản. (3h)
  - **T7.27** [P1 - High] [Bảo] [FE] Code Trang Quản lý Học liệu (`admin/content/page.tsx` - 240 dòng): Danh sách chủ đề Toán lớp 4-9, nút "Thêm chủ đề mới" mở Form Drawer, nút sửa/xóa bài học mẫu. (2h)
  - **T7.28** [P1 - High] [Thiên] [FE] Code Trang Giám sát An toàn (`admin/safety/page.tsx` - 210 dòng): Bảng log các câu chat bị Safety chặn (toxic/jailbreak) và biểu đồ tỷ lệ học sinh bấm "Chưa hiểu". (2h)
  - **T7.29** [P2 - Medium] [Thiên] [FE] Code Trang Cài đặt Hệ thống (`admin/settings/page.tsx` - 190 dòng): Giao diện chỉnh model AI (Gemini Flash/Pro), chỉnh temperature, max tokens, và thông tin version. (1.5h)
  - **T7.30** [P1 - High] [Bảo] [FE] Rà soát và kết nối 100% nút bấm, link điều hướng, nút quay lại trên toàn bộ các trang Admin (Đảm bảo không còn bất kỳ nút chết/dead-click nào). (1.5h)
  - **T7.31** [P0 - Critical] [Thống] [BE] Tạo router mock data `/admin/mock` cung cấp dữ liệu giả lập có cấu trúc chuẩn cho toàn bộ trang Admin để FE render siêu thực tế. (2.5h)
  - **T7.32** [P1 - High] [Thông] [QA] Đóng vai Quản trị viên: Click-through kiểm thử 100% các nút bấm trên toàn bộ 6 trang Admin, kiểm tra lỗi console, giao diện responsive tablet/laptop. (3h)
  - **T7.33** [P3 - Low] [Thông] [Document] Viết tài liệu hướng dẫn vận hành tính năng mới cho Phụ huynh, Sổ tay và Hướng dẫn sử dụng Admin Portal. (2h)
  - **T7.34** [P1 - High] [Thiên] [Management/QA] Review PR toàn bộ mã nguồn Frontend Admin, giải quyết conflict, dọn dẹp branch và chốt nghiệm thu Sprint 7. (1.5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Thiết kế đồng bộ & Chuyên nghiệp:** Toàn bộ hệ thống giao diện Admin có phong cách thiết kế hiện đại, đồng bộ theo bản thiết kế của Bảo.
  - **[AC2] Điều hướng 100% hoạt động (Click-through):** Mọi nút bấm, menu con, tab, icon trên toàn bộ giao diện Admin khi click đều chuyển trang hoặc kích hoạt modal tương ứng, không có nút chết (dead link).
  - **[AC3] Phân định rõ vai trò FE:** Bảo và Thiên phối hợp mượt mà ở các trang Admin được phân chia, không xung đột hay trùng lặp code.
  - **[AC4] Dữ liệu mẫu chuẩn cấu trúc:** Các trang Admin dùng mock data chuẩn cấu trúc Backend, sẵn sàng kết nối DB ở Sprint sau mà không phải sửa lại UI.

---

### 📌 Sơ Đồ Phụ Thuộc Task – Sprint 7

**US 7.1 (Dashboard Phụ Huynh)**
```
T7.1 (Thông: Prompt AI) ──► T7.2 (Thông: Schema) ──► T7.3 (Thống: BE Service) ──► T7.7 (Thiên: FE AI Card)
T7.4 (Thống: API Heatmap) ──► T7.8 (Thiên: FE Heatmap thật)
T7.5 (Thống: API Summary) ──► T7.8 (Thiên: FE Cards thật)
T7.6 (Thống: API Child Problems) ──► T7.9 (Thiên: FE Child History)
T7.7 + T7.8 + T7.9 ──► T7.10 (Bảo: UX Test) ──► T7.11 (Thiên: QA E2E)
```

**US 7.2 (Học Sinh - Streak & Sổ Tay)**
```
T7.12 (Thống: Model Bookmark) ──► T7.13 (Thống: API CRUD)
T7.15 (Thông: Gemini Boundary) ──► T7.16 (Thông: Prompt Flashcard) ──► T7.13
T7.14 (Thống: BE Streak/Badges) ──► T7.18 (Bảo: FE Streak/Badges)
T7.13 + T7.16 ──► T7.17 (Bảo: Nút Lưu) ──► T7.19 (Bảo: Trang Sổ tay) ──► T7.20 (Bảo: Drawer)
T7.12 ──► T7.21 (Thiên: Neon Index)
T7.19 + T7.20 ──► T7.22 (Thông: Test 20 tình huống lưu bài)
```

**US 7.3 (Admin Portal Frontend)**
```
T7.23 (Bảo: Design UI Figma) ──► T7.24 (Thiên: Admin Layout)
                               ├──► T7.25 (Thiên: Dashboard KPI)
                               ├──► T7.26 (Bảo: FE Users Table)
                               ├──► T7.27 (Bảo: FE Content)
                               ├──► T7.28 (Thiên: FE Safety)
                               └──► T7.29 (Thiên: FE Settings)
T7.31 (Thống: API Mock Admin) ──► T7.25 + T7.26
T7.24 đến T7.29 ──► T7.30 (Bảo: Rà soát 100% nút bấm) ──► T7.32 (Thông: QA Click-through) ──► T7.34 (Thiên: Review PR)
```

---

### 📌 Bảng Phân Bổ Công Việc Sprint 7:
| Thành viên | Tổng Giờ | Chi tiết Tasks |
| :--- | :--- | :--- |
| **[Bảo]** | **20.5h** | T7.10 (1.5h) + T7.17 (2h) + T7.18 (2h) + T7.19 (3h) + T7.20 (2.5h) + T7.23 (3h) + T7.26 (3h) + T7.27 (2h) + T7.30 (1.5h) |
| **[Thiên]** | **21.0h** | T7.7 (2.5h) + T7.8 (2.5h) + T7.9 (3h) + T7.11 (1.5h) + T7.21 (1.5h) + T7.24 (2.5h) + T7.25 (2.5h) + T7.28 (2h) + T7.29 (1.5h) + T7.34 (1.5h) |
| **[Thống]** | **20.0h** | T7.3 (2.5h) + T7.4 (2.5h) + T7.5 (2h) + T7.6 (2.5h) + T7.12 (2.5h) + T7.13 (3h) + T7.14 (2.5h) + T7.31 (2.5h) |
| **[Thông]** | **20.0h** | T7.1 (3h) + T7.2 (1.5h) + T7.15 (3h) + T7.16 (2.5h) + T7.22 (2.5h) + T7.32 (3h) + T7.33 (2h) + Setup prompt môi trường (2.5h) |

> ⭐ **Bắt đầu ngay Day 1 (Không bị nghẽn phụ thuộc chéo):**
> - **Bảo**: Thiết kế Wireframe/UI Admin (T7.23) $\rightarrow$ Code UI Streak & Badges (T7.18).
> - **Thiên**: Code UI Sổ theo dõi bài tập của con (T7.9) $\rightarrow$ Dựng Layout Admin & Sidebar (T7.24).
> - **Thống**: Viết API Heatmap thật (T7.4) $\rightarrow$ Model Bookmark & API CRUD (T7.12).
> - **Thông**: Viết Prompt AI Learning Insights (T7.1) $\rightarrow$ Viết Prompt Gemini Boundary Extraction (T7.15).


