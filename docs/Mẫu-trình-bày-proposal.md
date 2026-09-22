**Trình bày system context diagram**



Nhìn vào biểu đồ, trung tâm là hệ thống SocraticKid AI Tutor System, tương tác trực tiếp với 3 actor sẽ sử dụng hệ thống và 3 actor bên ngoài hệ thống:



* Về phía người dùng:



&#x09;\*\*Student (Học sinh):\*\* Gửi các tin nhắn, hình ảnh bài tập và các bước suy luận vào hệ thống. Đổi lại, hệ thống sẽ trả về các gợi ý hướng dẫn thay vì đưa ra đáp án trực tiếp Và kèm thêm câu hỏi để hỏi ngược lại học sinh để học sinh tư duy.



&#x09;Parent (Phụ huynh):\*\* Giám sát tiến trình và lịch sử học tập của học sinh. Hệ thống cung cấp cho phụ huynh các báo cáo theo dõi kiến thức để đánh giá mức độ làm chủ kiến thức và sự tự học của học sinh.



&#x09;Admin (Quản trị viên):\*\* Quản lý người dùng, giám sát hoạt động của các Agent, và nhận về các dữ liệu như lý do từ chối phản hồi của AI hoặc các chỉ số hoạt động.



* Về phía các hệ thống ngoại vi:



&#x09;Google OAuth:\*\* Xử lý luồng xác thực đăng nhập cho Học sinh và Quản trị viên bằng tài khoản google, sau đó trả về Token và thông tin hồ sơ người dùng.



&#x09;Cloud Storage:\*\* Tiếp nhận, xử lý và lưu trữ các hình ảnh bài tập do người dùng tải lên, sau đó trả về các đường dẫn URL công khai.



&#x09;Google Gemini API:\*\* Đóng vai trò là bộ máy suy luận cốt lõi, nhận các yêu cầu từ hệ thống (bao gồm prompt và dữ liệu ảnh OCR), sau đó phân tích và trả về các kết quả phân tích logic  cho SocraticKid.



* Hệ thống của em không phải cứ nhận câu hỏi của học sinh -> gửi thẳng API cho Gemini -> rồi bê nguyên câu trả lời của Gemini trả về cho học sinh. Việc làm như vậy rất rủi ro vì AI có thể sẽ làm lộ đáp án.



Thay vào đó, đằng sau hệ thống SocraticKid là cả một Kiến trúc Đa tác nhân (Multi-Agent Architecture) được thiết kế rất chặt chẽ, hoạt động qua 3 bước chính:



Bước 1 - Người điều phối (Orchestrator): Khi học sinh đặt câu hỏi, luồng dữ liệu sẽ đi qua một Agent đóng vai trò là Người điều phối. Agent này có nhiệm vụ phân tích ý định  của học sinh để quyết định xem bước tiếp theo nên làm gì.

Bước 2 - Nhóm 4 Agents chuyên biệt: Tùy thuộc vào sự điều hướng của Orchestrator, dữ liệu sẽ được xử lý bởi một đội ngũ gồm 4 Agents:

* Scaffolding Agent: Chuyên dẫn dắt, gợi mở giải bài từng bước một theo phương pháp Socratic.
* Misconception Agent: Chuyên phát hiện các bước làm sai, nắn chỉnh lại các bước hiểu sai của học sinh.
* Knowledge Tracing Agent: Chuyên đặt câu hỏi dò tìm xem học sinh có bị hổng kiến thức nền tảng hay không.
* Safety Agent: Chuyên xử lý các giao tiếp ngoài lề, chào hỏi và giữ an toàn nội dung.

Bước 3 - Reviewer Agent (Người kiểm duyệt): Cuối cùng, và cũng là chốt chặn quan trọng nhất, mọi câu trả lời trước khi gửi ra ngoài đều phải đi qua một Reviewer Agent. Nó sẽ đánh giá xem câu trả lời có tuân thủ đúng phương pháp Socratic hay không (tuyệt đối không có đáp án, ngôn từ có phù hợp, có tính gợi mở không). Chỉ khi Reviewer Agent đánh giá 'Pass' (Oke), thì câu trả lời đó mới chính thức được hệ thống gửi về cho học sinh.



(Đây chỉ là ví dụ để ae trong nhóm hiểu về việc chèn prompt của agent gửi geminni)

Cụ thể, một Prompt hoàn chỉnh đưa vào Misconception Agent sẽ bao gồm các khối (block) được lắp ráp lại như sau:



\[Khối Cố định] Vai trò \& Luật: "Bạn là Misconception Agent... Tuyệt đối không đưa đáp án... Chỉ ra chính xác bước học sinh sai..."

\[Khối Động] Đề bài \& Đáp án: Mã code tự động chèn đề bài và đáp án chuẩn (ẩn) vào để AI biết đường so sánh.

\[Khối Động] Lịch sử trò chuyện: Code tự động lấy các đoạn chat trước đó chèn vào để AI nhớ ngữ cảnh.

\[Khối Động] Câu nói mới nhất của học sinh: Chèn chính xác câu mà học sinh vừa gõ sai (Ví dụ: "Em tính ra 5/7").

\[Khối Động đặc biệt] Lời cảnh báo từ Reviewer: Nếu lần gọi trước con Misconception này bị Reviewer đánh rớt (REJECT) vì lỡ nói lộ đáp án, đoạn code sẽ tự động nhét thêm một lời mắng vào Prompt: "Cảnh báo: Bản nháp trước của bạn bị từ chối vì lộ đáp án. Yêu cầu sửa ngay!".

=> Kết luận lại: Đúng là con Misconception Agent chỉ có 1 khuôn Prompt duy nhất, nhưng nhờ cơ chế chèn dữ liệu động (Dynamic), mỗi lần gọi lên Gemini, câu Prompt gửi đi đều là một phiên bản "độc nhất vô nhị", khớp 100% với ngữ cảnh bài toán và lỗi sai hiện tại của học sinh lúc đó.

