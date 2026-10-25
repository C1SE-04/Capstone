# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

1. **Học sinh (Lớp 4 – 9)**: Người dùng trọng tâm. Cần một gia sư kiên nhẫn, gợi mở từng bước khi gặp bài toán khó, khích lệ tư duy độc lập thay vì đưa sẵn đáp án.
2. **Phụ huynh (Người giám sát - Monitor)**: Cần theo dõi tiến trình học tập, thời gian học, tính kiên trì (Streak), điểm tự lập (Independence Score) và nhận xét sư phạm thông minh từ AI mà không cần ngồi kè kè bên con.
3. **Quản trị viên (Admin)**: Giám sát an toàn nội dung, chất lượng phản hồi AI, kiểm duyệt ngôn từ và quản lý dữ liệu học liệu.

## Product Purpose

SocraticKid là nền tảng AI Gia Sư Socratic dành riêng cho học sinh Việt Nam. Sản phẩm ra đời nhằm giải quyết triệt để vấn nạn học vẹt, ỷ lại vào các công cụ AI giải bài hộ ("chép giải"), giúp học sinh tự mình khám phá ra bản chất vấn đề, hiểu sâu và nhớ lâu toán học.

## Positioning

Khác biệt với ChatGPT, Photomath hay các AI giải toán thông thường, SocraticKid **cam kết 100% không giải hộ bài hay đưa đáp số trực tiếp**. Hệ thống sử dụng phương pháp đàm thoại Socratic:
- Chia nhỏ bài toán phức tạp thành các câu hỏi phụ dẫn dắt.
- Đánh giá chỉ số tự lực (Independence Score từ 0 đến 100).
- Hệ thống Sổ tay Flashcard lưu giữ bí kíp tư duy cốt lõi sau mỗi bài toán hoàn thành.

## Operating Context

- **Thiết bị**: Học sinh và phụ huynh sử dụng trên máy tính bảng, điện thoại di động và máy tính bàn. Giao diện ưu tiên ổn định viewport (`100dvh`), thao tác chạm ngón tay thoải mái, tương thích màn hình cảm ứng.
- **Ngữ cảnh sử dụng**: Góc bàn học vào buổi tối, các buổi tự ôn thi cuối kỳ, hoặc phụ huynh kiểm tra tiến độ học tập của con vào cuối tuần.

## Capabilities and Constraints

- **Khung Chat Socratic**: Hỗ trợ nhập đề bài bằng văn bản hoặc chụp ảnh đề bài tải lên Cloudinary. Tự động nhận diện công thức toán học KaTeX.
- **Game hóa & Tiến trình Tự lực**: Thanh Mastery Score hiển thị mức độ tự lập, biểu tượng ngọn lửa hoạt hình Streak 🔥 theo ngày, Modal chúc mừng mở khóa huy hiệu (Tự lập nhí 100đ, Kiên trì 3 ngày, Thám tử hình ảnh).
- **Sổ tay bài toán yêu thích (Bookmark Flashcards)**: Lưu snapshot đề bài, ảnh đề, bí kíp cốt lõi và mở drawer xem lại chuỗi tin nhắn của riêng bài toán đó.
- **Bảng điều khiển Phụ huynh**: Heatmap thời gian học, biểu đồ tự lực, danh sách bài tập kèm ảnh và Báo cáo Nhận xét Sư phạm (AI Learning Insights).
- **Hàng rào an toàn (Reviewer Agent)**: Giám sát câu từ, kiểm duyệt ngôn từ tiêu cực hoặc câu hỏi lệch lạc.

## Brand Commitments

- **Hệ màu nhận diện**: Phong cách ấm áp, sư phạm và gần gũi:
  - Màu chủ đạo (Primary Accent): Cam đất nung `#C1762A`
  - Màu nhấn đậm (Deep Ink): Nâu gỗ `#8C4905`
  - Màu nền chính (Warm Canvas): Kem trang nhã `#F7ECE1`
  - Màu bề mặt phụ (Secondary Surface): Vàng kem đào `#F1CCA6`
- **Linh vật**: Chú Cú SocraticKid thông thái, đa biểu cảm (nghĩ, gợi ý, khen ngợi, chấn chỉnh).

## Product Principles

1. **Gợi mở trên giải hộ**: Không bao giờ đưa đáp án trước khi học sinh tự bước qua các bước tư duy logic.
2. **Khích lệ tính tự lập**: Mọi tính năng (điểm số, huy hiệu, streak) đều tôn vinh nỗ lực tự suy luận của trẻ.
3. **An toàn & Minh bạch**: Phụ huynh luôn có cái nhìn đầy đủ, trung thực về quá trình học của con mình.
4. **Không giao diện rác (Anti-AI Slop)**: Tránh xa các thiết kế template khuôn mẫu, màu tím neon, hay trang trí lòe loẹt. Mọi chi tiết trên màn hình đều phục vụ trải nghiệm tập trung học toán.
