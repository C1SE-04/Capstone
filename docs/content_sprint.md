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
  - **T6.7** [Thông] [AI/Arch] Tư vấn thiết kế schema API metrics & định dạng chỉ số điểm tự lực phục vụ hiển thị Parent Dashboard. (2h)
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
  - **Xử lý phía Backend & AI**:
    - Upload ảnh lên Vercel Blob, nhận về URL công khai.
    - Truyền URL kèm tin nhắn vào Gemini Vision.
    - AI đọc ảnh và phản hồi Socratic (không giải thẳng đáp án).
- **Tasks:**
  - **T6.20** [Bảo] [FE] Nâng cấp `ChatInput.tsx`: Thêm handler `onPaste` nhận ảnh từ clipboard. Tích hợp `<input type="file" accept="image/*">` ẩn, kích hoạt bằng nút `+`. Hiển thị thumbnail preview + nút X. (5h)
  - **T6.21** [Bảo] [FE] Mobile Bottom Sheet khi bấm `+`: Hiện 2 lựa chọn — *Camera* (`<input capture="environment">`) và *Thư viện* (`<input>` không có `capture`). (3h)
  - **T6.22** [Thống] [BE] Code API `api/upload/route.ts`: Nhận file ảnh, upload Vercel Blob, trả URL. Validate loại file (chỉ image/*) và kích thước tối đa 5MB. Đồng thời sửa API `/chat` để nhận thêm trường `image_url`. (4h)
  - **T6.23** [Thông] [AI] Cập nhật Orchestrator + Agent Prompt: Khi có `image_url` → AI dùng Gemini Vision phân tích ảnh trước khi gợi ý → tuyệt đối không giải thẳng đáp án từ ảnh. (4h)
  - **T6.24** [Thông] [AI] Nghiên cứu Gemini Vision API (đọc docs, test qua Postman), viết test cases đọc ảnh toán học. Tinh chỉnh prompt Vision sau khi có API thật. (6h)
  - **T6.25** [Thiên] [QA] Test toàn diện: Paste ảnh Ctrl+V desktop, upload file, chụp camera mobile, chọn thư viện mobile. Kiểm tra AI Socratic. Test edge cases (>5MB, sai định dạng). Review & hoàn tất Sprint 6. (3h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Paste ảnh Desktop:** `Ctrl+V` vào ô chat → ảnh hiện preview nhỏ. Bấm gửi → AI đọc ảnh, phản hồi Socratic (không lộ đáp án).
  - **[AC2] Upload file Desktop:** Bấm `+` → chọn file ảnh → preview hiện → gửi → AI phản hồi.
  - **[AC3] Camera Mobile:** Bấm `+` → chọn *Camera* → camera điện thoại mở → chụp → preview → gửi được.
  - **[AC4] Thư viện Mobile:** Bấm `+` → chọn *Thư viện ảnh* → gallery mở → chọn ảnh → preview → gửi.
  - **[AC5] Validation:** File >5MB hoặc không phải ảnh → báo lỗi "Chỉ hỗ trợ ảnh dưới 5MB", không gửi.

### 📌 Sơ Đồ Phụ Thuộc Task – Sprint 6

**US 6.1 (Điểm Tự Lực & Dashboard Phụ Huynh)**
```
T6.1 (Thông: Thuật toán) ──► T6.2 (Thông: Barem điểm)
T6.3 (Thống: API independence) ──► T6.4 (Thống: Sửa /chat)
                                         ├──► T6.5 (Bảo: FE Progress bar)
                                         └──► T6.9 (Thiên: FE Line chart)
T6.6 (Thiên: Activity Heatmap UI tĩnh) ← Độc lập, làm ngay Day 1
T6.7 (Thông: Tư vấn schema API metrics)
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

**US 6.4 (Đính kèm ảnh)**
```
T6.20 (Bảo: FE paste+upload desktop) ──► T6.21 (Bảo: FE mobile bottom sheet)
T6.22 (Thống: BE upload API + /chat)
T6.24 (Thông: Research Vision) ──► T6.23 (Thông: Orchestrator + prompt Vision)
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

## Sprint 7: Quản trị Hệ thống (Admin Users & Content) & Đóng gói (17-Oct đến 23-Oct)
*(Phân bổ khối lượng: [Bảo]: 12h, [Thông]: 19h, [Thiên]: 19h, [Thống]: 19h)*

### US 7.1: Quản lý Người dùng & Chỉ số hệ thống
*Mô tả: Là một Quản trị viên, tôi muốn quản lý danh sách người dùng và theo dõi các chỉ số tăng trưởng của hệ thống.*
- **Mô tả chi tiết:**
  - **Dashboard phân tích tổng quan**:
    - Xây dựng màn hình thống kê trung tâm dành riêng cho Quản trị viên (Admin).
    - Đo lường và hiển thị lượng người dùng hoạt động hằng ngày (DAU) và hằng tháng (MAU).
    - Sử dụng các biểu đồ trực quan để dễ dàng nắm bắt đà tăng trưởng.
  - **Công cụ quản lý tài khoản**:
    - Cung cấp một bảng dữ liệu (Data Table) mạnh mẽ, load nhanh.
    - Hỗ trợ tính năng liệt kê và phân trang toàn bộ danh sách người dùng.
    - Cho phép tìm kiếm chính xác và lọc người dùng theo tên/email.
  - **Quyền lực can thiệp hệ thống**:
    - Cấp quyền giám sát trạng thái của bất kỳ tài khoản nào.
    - Cho phép Admin vô hiệu hóa (ban) các người dùng vi phạm chính sách.
    - Theo dõi tổng thể lượng phiên chat đang hoạt động để đánh giá tình trạng tải máy chủ.
- **Tasks:**
  - [Thiên] [FE] Code Layout tổng cho Admin (`admin/layout.tsx`, `AdminUserMenu.tsx`). (3h)
  - [Bảo] [FE] Code trang `admin/users/page.tsx` (318 dòng) có bảng dữ liệu (Table), tìm kiếm và phân trang. (6h)
  - [Thiên] [FE] Code trang tổng quan `StatsCharts.tsx` (304 dòng) hiển thị DAU, MAU (Active Users). (4h)
  - [Thống] [BE] Code API REST lấy danh sách toàn bộ người dùng, tìm kiếm theo email/tên cho Admin. (6h)
  - [Thống] [BE] Code API lấy dữ liệu thống kê tổng (số lượt chat/ngày) cho biểu đồ Admin. (5h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Dashboard Admin:** Khi tài khoản Admin đăng nhập, màn hình hiển thị trực quan biểu đồ số người dùng hoạt động và danh sách chi tiết các tài khoản.

### US 7.2: Quản lý Nội dung học (Content) & Release Dự án
*Mô tả: Là một Giáo viên (Admin), tôi muốn quản lý các chủ đề và nội dung bài học được hệ thống cung cấp.*
- **Mô tả chi tiết:**
  - **Quản trị hệ thống học liệu**:
    - Cung cấp giao diện CRUD chuyên dụng cho Giáo viên hoặc Admin.
    - Dễ dàng thêm mới, chỉnh sửa hoặc xóa bỏ các chủ đề bài học/toán học.
    - Vận hành mượt mà thông qua UI mà không cần kỹ năng lập trình (code).
  - **Đánh giá tự động chất lượng AI**:
    - Áp dụng quy trình kiểm thử khắt khe trước khi phát hành dự án.
    - Xây dựng script Python chạy Auto-Eval đánh giá AI trên bộ đề toán học khó.
    - Đảm bảo AI suy luận chuẩn xác, không gặp tình trạng ảo giác (hallucination).
  - **Đảm bảo tiêu chuẩn Production**:
    - Rà soát bảo mật mã nguồn kỹ lưỡng, đảm bảo không rò rỉ API key.
    - Cấu hình phân quyền chặn đứng user thường gọi vào endpoint Admin.
    - Bàn giao đầy đủ tài liệu kỹ thuật để sẵn sàng deploy chính thức bản Release v1.0.
- **Tasks:**
  - [Bảo] [FE] Code giao diện `admin/content/page.tsx` (196 dòng) (Quản lý các chủ đề Toán học). (6h)
  - [Thống] [BE] Code API `api/admin/content/route.ts` và `api/content/[contentId]/route.ts` thao tác CRUD. (8h)
  - [Thông] [AI] Viết script Python đánh giá tự động (Auto-Eval) chất lượng phản hồi tổng thể của hệ thống. (7h)
  - [Thông] [AI] Xây dựng bộ test set cuối cùng gồm 200 câu toán khó để benchmark hệ thống trước Release. (6h)
  - [Thông] [QA] Tổng hợp báo cáo độ chính xác của AI cho giáo viên quản lý nội dung xem. (6h)
  - [Thiên] [QA] Chạy Security Test (Pentest nhẹ) rà soát bảo mật: Đảm bảo user thường không truy cập được API Admin. (5h)
  - [Thiên] [Management] Chốt tài liệu tổng kết hệ thống, cập nhật file `docs/workflow.md` (469 dòng). (3h)
  - [Thiên] [Management] Dọn dẹp codebase (Xoá branch cũ, xoá log rác), họp Review dự án tổng kết. (2h)
  - [Thiên] [DevOps] Deploy toàn bộ hệ thống bản Release v1.0 ra Production và quay video Demo. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Sẵn sàng Release:** Mã nguồn sạch sẽ, không lộ API Key, hệ thống triển khai thành công trên môi trường Production và tài liệu được bàn giao đầy đủ.
