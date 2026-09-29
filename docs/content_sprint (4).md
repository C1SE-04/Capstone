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

### US 4.1: Trải nghiệm học tập thoải mái và An toàn ngầm
*Mô tả: Là học sinh, tôi muốn việc học diễn ra mượt mà, tự động gợi ý lúc bí và không bị bắt bẻ lặt vặt. Là phụ huynh, tôi muốn hệ thống âm thầm kiểm duyệt để con không bao giờ xem được đáp án trước.*
- **Mô tả chi tiết:**
  - **Không bắt bẻ xưng hô**: Trả lời cụt lủn kiểu "quy đồng", "15" vẫn cứ là bình thường, miễn là đúng. Hệ thống chỉ nhắc nhở khi nào nói tục chửi bậy thôi.
  - **Nút "Đã hiểu / Chưa hiểu"**: Lúc trả lời đúng, thay vì phải tự gõ, hệ thống hiện sẵn 2 nút để bấm cho lẹ.
  - **Thầy tự hiểu ý (Hint ngầm)**: Hệ thống đếm ngầm, nếu học sinh sai liên tiếp ở 1 câu (tầm 5 lần) thì thầy AI tự động mớm cho một chút gợi ý cách làm, không cần học sinh phải mở miệng hỏi.
  - **Chống kẹt ở chữ "Chưa hiểu"**: Đếm xem học sinh bấm "Chưa hiểu" mấy lần. Lần 1 thì thầy đổi cách giảng. Lần 2 thì thầy chẻ nhỏ bài toán ra. Lần 3 mà vẫn không hiểu thì thôi, thầy giải luôn cho xem rồi đổi qua bài khác dễ hơn để làm lại.
  - **Giám thị soi bài (Reviewer ngầm)**: Có một con AI khác đóng vai Giám thị đứng đằng sau, chuyên đọc lại bài của thầy Gia sư chuẩn bị gửi, để chắc chắn thầy không lỡ miệng nói ra đáp án.
  - **Tự sửa sai**: Nếu Giám thị thấy lỗi, sẽ bắt thầy Gia sư viết lại (cho sửa tối đa 2 lần). Lúc này màn hình của học sinh vẫn hiện "Đang suy nghĩ...", không làm các em xao nhãng.
  - **Báo cáo lại (Toast)**: Lưu lại mấy lần thầy Gia sư nói hớ vào database. Đồng thời hiện một cái thông báo nho nhỏ ở góc màn hình cho người lớn biết là hệ thống vừa chặn thành công một phản hồi không tốt.
- **Tasks:**
  - [Thông] [AI] Viết lại lời căn dặn (prompt) trong `agent_prompts.py`: Dặn AI thoáng hơn trong xưng hô, chỉ giận khi học sinh chửi bậy. (3h)
  - [Thông] [AI] Viết lời căn dặn cho con Giám thị (không lộ đáp án, vui vẻ) và ép nó bớt nói nhảm (giảm Temperature). (4h)
  - [Thống] [BE] Tạo thêm bộ đếm số lần sai liên tiếp và số lần bấm "Chưa hiểu". (2h)
  - [Thống] [BE] Code luồng Hint ngầm (sai 5 lần tự gợi ý) và luồng xử lý bấm "Chưa hiểu". (4h)
  - [Thống] [BE] Code logic cho con Giám thị chấm điểm bài của Gia sư, nếu rớt thì bắt viết lại bản nháp khác (Self-Correction). (6h)
  - [Thống] [BE] Lưu lại lịch sử mấy câu lỡ miệng của Gia sư vào database. (2h)
  - [Bảo] [FE] Làm 2 cái nút "Đã hiểu/Chưa hiểu" hiện ra lấp chỗ cái ô nhập chữ, nhấn vào là tự gửi luôn. (4h)
  - [Bảo] [FE] Làm cái bảng thông báo nho nhỏ (Toast) trượt ra trượt vào ở góc màn hình. (2h)
  - [Thiên] [QA] Vô đóng giả học sinh lì lợm: gõ cụt lủn, làm sai 5 lần liên tiếp xem hệ thống phản ứng sao. (3h)
  - [Thiên] [QA] Test luồng Giám thị: Cố tình hỏi ép lấy đáp án xem có bị chặn không, xem thông báo nhỏ có hiện không. (4h)
  - [Thiên] [Management] Đọc lại code của anh em, gom lại rồi gộp (merge). (3h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Trả lời cụt lủn:** Gõ đúng mỗi chữ "quy đồng", hệ thống vẫn đi tiếp bình thường, không bắt bẻ "phải xưng em gọi thầy". Chỉ khi nào chửi bậy mới bị nhắc nhở.
  - **[AC2] Tự mớm gợi ý & Hiện nút:** Cố tình làm sai 5 lần, thầy AI tự hé lộ công thức cho làm tiếp. Khi làm đúng 1 bước, khung chat tự biến thành 2 nút bấm "Đã hiểu" và "Chưa hiểu".
  - **[AC3] Thoát kẹt:** Cố tình bấm "Chưa hiểu" 3 lần, thầy AI đưa luôn lời giải hoàn chỉnh rồi đổi qua câu khác dễ hơn.
  - **[AC4] Tuyệt đối giấu đáp án:** Dù học sinh có ép "cho xin đáp án đi", thầy AI vẫn lảng tránh khéo léo và không nói ra con số cuối cùng.
  - **[AC5] Sửa sai ngầm & Báo cáo:** Dù cố ép AI nói đáp án, hệ thống sẽ tự vật lộn viết lại ngầm bên trong. Trên màn hình sẽ hiện một thông báo nhỏ xíu "Hệ thống vừa chặn phản hồi không phù hợp" rồi trượt đi mất, không làm vướng mắt học sinh.

### US 4.2: Cú Socratic sinh động
*Mô tả: Là một học sinh, mình thích có một bạn trợ lý ảo (con cú) chuyển động trên màn hình, biết vui buồn theo bài làm của mình để việc học đỡ nhàm chán.*
- **Mô tả chi tiết:**
  - **Giao diện con cú**: Gắn một hình động (Lottie) con cú vào góc màn hình, vừa đủ nhìn, không che mất chữ của đoạn chat.
  - **Biết bộc lộ cảm xúc**: Dựa vào câu chat, hệ thống gửi thêm một cái cờ (cảm xúc). Con cú sẽ đổi điệu bộ theo đó: lúc thì gật gù suy nghĩ, lúc thì vỗ tay khen đúng, lúc thì an ủi khi làm sai.
  - **Chạy mượt**: Hoạt hình phải tải nhanh, đổi trạng thái mượt, không làm giật hay đơ cái khung chat bên cạnh.
- **Tasks:**
  - [Bảo] [FE] Bỏ thư viện Lottie vào, gắp con cú lên màn hình với 5 trạng thái (đứng im, suy nghĩ, gợi ý, làm đúng, làm sai). (4h)
  - [Bảo] [FE] Viết code để con cú biết thay đổi cử động dựa vào kết quả từ server trả về. (4h)
  - [Thiên] [FE] Canh chỉnh lại CSS để con cú nằm gọn ở một góc, không đè lên chữ. (3h)
  - [Thiên] [FE] Làm cho con cú đổi từ trạng thái này sang trạng thái kia mượt mà, không bị khựng hình. (3h)
  - [Thông] [AI] Sửa lại luồng định tuyến (Orchestrator) để nó trả thêm cái cờ cảm xúc. (4h)
  - [Thông] [AI] Test thử xem AI có thả đúng biểu cảm không (làm đúng thì phải báo là correct chứ đừng báo sai). (3h)
  - [Thống] [BE] Sửa API để nó nhét thêm cái cờ cảm xúc này vào cục JSON trả về cho Frontend. (3h)
  - [Thống] [BE] Nhớ đệm (cache) mấy file hoạt hình trên server để máy học sinh không phải tải đi tải lại. (3h)
  - [Thiên] [QA] Mở web trên máy tính, điện thoại bấm loạn lên xem con cú có bị lag hay che khuất chữ không. (4h)
  - [Thiên] [Management] Bàn bạc chốt vị trí con cú, đọc lại code và gộp. (3h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Đang suy nghĩ:** Gửi câu hỏi xong, trong lúc chờ thầy AI trả lời thì con cú ở góc làm điệu bộ ôm đầu suy nghĩ.
  - **[AC2] Trả lời đúng:** Gõ đúng đáp án, thầy AI vừa khen thì con cú cũng đổi sang điệu bộ vỗ tay vui vẻ.
  - **[AC3] Trả lời sai:** Gõ sai đáp án, con cú đổi sang điệu bộ động viên, lắc đầu nhẹ.
  - **[AC4] Không che chữ:** Mở web bằng điện thoại, con cú nằm ngoan ở góc, chữ trong bong bóng chat vẫn đọc được ngon lành, không bị đè khuất.
  - **[AC5] Mượt mà:** Chữ đang chạy ra từng dòng mà con cú vẫn cử động mượt, không có cảm giác máy bị đơ.

### US 4.3: Cho khách dùng thử 10 câu (Guest Trial)
*Mô tả: Là một học sinh mới ghé web, mình muốn lướt thử hỏi vài câu toán xem hệ thống hay không rồi mới tạo tài khoản. Nhưng hệ thống phải nhắc nhẹ nếu mình dùng hết lượt, chứ đừng im re không phản hồi.*
- **Mô tả chi tiết:**
  - **Nhớ thiết bị**: Gắn cho mỗi trình duyệt một cái ID ẩn. Lỡ học sinh tải lại trang hay tắt đi mở lại thì số câu đã hỏi vẫn được tính tiếp, không lo bị mất bài.
  - **Luật dùng thử**: Mỗi người khách chỉ được hỏi 10 câu. Cứ sau 24 tiếng thì hệ thống lại cấp cho 10 câu mới.
  - **Báo hết lượt dễ thương**: Lúc hỏi sang câu 11, thay vì báo lỗi khó hiểu, hệ thống hiện ra một cái bảng nhỏ nhắc: "Hôm nay xài hết lượt rồi nhé, đợi mai quay lại hoặc đăng nhập luôn để học tẹt ga." Có kèm chữ login bấm vào được.
- **Tasks:**
  - [Bảo] [FE] Viết code tạo ID giấu vào trình duyệt (localStorage) rồi cứ mỗi lần gọi API thì kẹp theo cái ID này. (3h)
  - [Thống] [BE] Lưu mấy cái ID này vô database, kèm theo số đếm xem nó hỏi được mấy câu rồi. (3h)
  - [Thống] [BE] Chặn cổng (Middleware): Ai hỏi quá 10 câu trong 24 tiếng thì trả về lỗi 403. Còn qua ngày hôm sau thì reset số đếm về 0. (4h)
  - [Thiên] [FE] Vẽ cái bảng thông báo hết lượt dễ thương, có sẵn cái chữ "login" để bấm vào là qua trang đăng nhập. (3h)
  - [Thiên] [QA] Đóng giả khách vô hỏi 5 câu, tắt web mở lại hỏi tiếp xem có bị chặn ở câu thứ 11 không. Xong chỉnh đồng hồ qua ngày mai xem có được hỏi lại không. (4h)
  - [Thiên] [Management] Đọc lại code, kiểm tra xem có ai dễ dàng ăn gian cái ID này không, rồi gộp code. (2h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Chống F5 ăn gian:** Hỏi 5 câu, tải lại trang, hỏi tiếp 5 câu nữa. Tới câu 11 là bị chặn lại và hiện bảng báo hết lượt.
  - **[AC2] Tắt máy mở lại:** Đang xài nửa chừng lỡ tắt ngang tab trình duyệt. Mở lại vô trang đó, chat tiếp, đụng tới câu 11 vẫn bị chặn như thường.
  - **[AC3] Chữ bấm được:** Trên cái bảng thông báo hết lượt, bấm vào chữ "login" là nó bay sang trang đăng nhập ngay lập tức.
  - **[AC4] Đợi 24 tiếng:** Lùi đồng hồ (hoặc nhờ dev giả lập) qua ngày hôm sau, vô lại web là lại được chat tiếp 10 câu mới như chưa có gì xảy ra.

---

### 📌 Trình tự làm việc Sprint 4 (Ai chờ ai)

Nhìn vô đây để biết việc của mình có cần phải đợi người khác làm xong không nhé:

**Nhóm US 4.1 (Trải nghiệm & An toàn ngầm):**
```
[Thông] Chỉnh lại cách ăn nói cho AI, dặn dò Giám thị
    └──→ [Thống] Viết code bắt lỗi (reviewer.py)
              └──→ [Thống] Viết code vòng lặp bắt viết lại nháp
              └──→ [Bảo]   Làm cái bảng thông báo (Toast) trên web

[Thống] Đếm số lần Sai và số lần bấm Chưa hiểu
    └──→ [Thống] Code luồng Hint ngầm + Luồng Chưa hiểu
              └──→ [Bảo]   Làm 2 cái nút bấm Đã hiểu/Chưa hiểu

[Thiên] Test thử hết mấy kịch bản chửi bậy, ép số, lỳ lợm...  (phải chờ 2 luồng trên xong hết)
```
> ✅ **Anh em vô làm song song liền:** Thông lo dàn cảnh cho AI, Thống đi đếm số lần sai, Bảo dựng sẵn khung giao diện 2 cái nút và bảng Toast bằng data giả, Thiên ngồi nghĩ kịch bản chửi bậy để test.

**Nhóm US 4.2 (Cú Socratic):**
```
[Thông] Chế ra mấy cái cờ cảm xúc từ câu chat
    └──→ [Thống] Nhét cờ cảm xúc vô API trả về
              └──→ [Bảo]   Gắn con cú và bắt nó chuyển động theo cờ
              └──→ [Thiên] Chỉnh lại dáng đứng của con cú, cho nó mượt   (làm song song với Bảo)
              └──→ [Thiên] Xách đt thoại ra test E2E                       (chờ mọi thứ xong)
```
> ✅ **Anh em vô làm song song liền:** Thông ngồi phân loại cảm xúc, Bảo lấy hình con cú 5 trạng thái ốp vô trước cho nó nhúc nhích giả, Thiên chỉnh vị trí con cú, Thống chuẩn bị chỗ chứa file trên server.

**Nhóm US 4.3 (Cho khách dùng thử 10 câu):**
```
[Bảo] Chế cái ID lén giấu vô máy người dùng
    └──→ (Bảo cứ làm rẹt rẹt, khỏi đợi Backend)

[Thống] Chừa chỗ trong Database để đếm số câu của ID
    └──→ [Thống] Chặn chốt bắt lỗi 403 nếu lố 10 câu
              └──→ [Thiên] Hiện bảng thông báo hết lượt dễ thương  (chờ Thống trả đúng lỗi)
              └──→ [Thiên] Test thử ngắt kết nối, F5...            (chờ xong hết)
```
> ✅ **Anh em vô làm song song liền:** Bảo code cái ID, Thống làm bộ đếm dưới DB, Thiên thiết kế cái bảng thông báo với nút login.
--

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

## Sprint 6: Đánh giá Năng lực (Mastery) & Thử nghiệm A/B (10-Oct đến 16-Oct)
*(Phân bổ khối lượng: [Bảo]: 12h, [Thông]: 19h, [Thiên]: 19h, [Thống]: 19h)*

### US 6.1: Đo lường điểm Độc lập (Independence/Mastery)
*Mô tả: Là một Hệ thống, tôi muốn tự động chấm điểm mức độ tự lực của học sinh để đánh giá sự tiến bộ của các em.*
- **Mô tả chi tiết:**
  - **Chấm điểm tự lực tự động**:
    - AI ngầm phân tích quá trình hội thoại và đếm số lượng gợi ý học sinh đã dùng.
    - Quy đổi thành điểm "Independence" (Độc lập) dựa trên barem nội bộ.
    - Đánh giá ngay sau khi học sinh giải quyết xong bài toán.
  - **Tổng hợp và cập nhật tiến độ**:
    - API tiếp nhận điểm, ghi nhận vào Database và chạy Job tổng hợp lại.
    - Cập nhật tức thì thanh tiến trình (Progress bar) hoặc huy hiệu trên giao diện.
    - Đảm bảo hiển thị real-time để tạo động lực học tập.
  - **Hiệu ứng khen thưởng trực quan**:
    - Khuyến khích tinh thần tự học bằng các phần thưởng UI.
    - Frontend tự động kích hoạt hiệu ứng pháo hoa (Confetti) rực rỡ.
    - Chỉ áp dụng khi học sinh đạt điểm tuyệt đối (giải bài nhanh, ít nhờ gợi ý).
- **Tasks:**
  - [Thông] [AI] Cấu hình thuật toán nội bộ AI tự động đánh giá mức độ tự lực của học sinh sau mỗi bài toán. (5h)
  - [Thông] [AI] Xây dựng barem điểm Independence (gợi ý ít -> điểm cao, giải hộ -> điểm thấp). (4h)
  - [Thống] [BE] Code API `api/independence/route.ts` để tiếp nhận và lưu trữ điểm số từ AI trả về. (5h)
  - [Thống] [BE] Viết Job chạy ngầm/cron tính trung bình cộng điểm Independence cho toàn bộ học sinh. (5h)
  - [Bảo] [FE] Hiển thị huy hiệu / thanh tiến trình Mastery trên giao diện Chat để khích lệ học sinh. (6h)
  - [Thiên] [FE] Viết hiệu ứng chúc mừng (Confetti) khi học sinh đạt điểm Independence tuyệt đối. (4h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Cộng điểm tự lực:** Học sinh tự giải được bài toán sau 2 gợi ý, Khi đó điểm Mastery của học sinh được cộng thêm vào cơ sở dữ liệu và hiển thị thanh tiến trình thay đổi.

### US 6.2: Thử nghiệm A/B (Experiments)
*Mô tả: Là một Kỹ sư, tôi muốn cấu hình và phân luồng học sinh thử nghiệm các phiên bản AI khác nhau (A/B testing).*
- **Mô tả chi tiết:**
  - **Phân luồng học sinh ngầm**:
    - Sử dụng thuật toán Hash ngẫu nhiên để tự động chia học sinh mới vào nhóm thử nghiệm (A hoặc B).
    - Quá trình phân luồng diễn ra âm thầm, không làm ảnh hưởng đến trải nghiệm (UX).
    - Gắn cờ (flag) phân luồng vĩnh viễn cho tài khoản đó.
  - **Cấu hình động cho Quản trị viên**:
    - Xây dựng giao diện Admin chuyên biệt cho việc quản lý A/B Testing.
    - Cho phép chủ động bật/tắt tính năng mới hoặc thay đổi tỷ lệ phân luồng.
    - Không yêu cầu sửa mã nguồn hay deploy lại hệ thống khi thay đổi.
  - **Phân tích đối soát chất lượng**:
    - Thu thập và xuất báo cáo so sánh dữ liệu thực tế giữa 2 nhóm.
    - Tập trung đo lường các chỉ số kỹ thuật như độ trễ (Latency).
    - Phân tích độ chính xác của AI để ra quyết định chốt phiên bản nâng cấp cuối cùng.
- **Tasks:**
  - [Bảo] [FE] Code giao diện `admin/experiments/page.tsx` (517 dòng) để cấu hình A/B test bật/tắt tính năng. (6h)
  - [Thiên] [FE] Tạo các Hook (`useExperiment`) để các component UI kiểm tra trạng thái A/B test. (3h)
  - [Thống] [BE] Tích hợp logic phân luồng học sinh (Hash tỷ lệ % ngẫu nhiên) vào nhóm A/B khi gọi API `/chat`. (5h)
  - [Thống] [Database] Bơm dữ liệu giả đa dạng bằng `prisma/seed.ts` để phục vụ test biểu đồ A/B. (4h)
  - [Thông] [AI] Phân tích Logs của nhóm A và B (prompt A vs prompt B) xem mô hình nào phản hồi tốt hơn. (6h)
  - [Thông] [AI] Rút trích dữ liệu từ DB để tạo báo cáo so sánh độ trễ (latency) giữa 2 phiên bản AI. (4h)
  - [Thiên] [QA] Test xác suất phân luồng: Đăng nhập 100 tài khoản giả lập xem có đúng xấp xỉ 50-50 hay không. (5h)
  - [Thiên] [DevOps] Mở rộng Database Storage (NeonDB) chuẩn bị đón lượng dữ liệu thực tế lớn. (4h)
  - [Thiên] [Management] Kiểm tra tiến độ tổng thể của thử nghiệm A/B, duyệt và Merge PR. (3h)
- **Tiêu chí chấp nhận (Acceptance Criteria):**
  - **[AC1] Phân luồng chính xác:** Cấu hình thử nghiệm A (Model Cũ) - 50% và B (Model Mới) - 50%, Khi tạo tài khoản mới, hệ thống phân bổ người dùng vào nhóm A hoặc B và ghi nhận cờ (flag) này vĩnh viễn.

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
