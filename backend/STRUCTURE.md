# Cấu Trúc Backend — Socratic Chatbot

## Tổng quan

```
backend/
├── main.py                    # Entrypoint FastAPI: đăng ký routers, middleware, startup/shutdown
├── models.py                  # SQLAlchemy ORM models (tất cả bảng DB)
├── schemas.py                 # Pydantic schemas (request/response)
├── database.py                # Cấu hình kết nối DB (SQLAlchemy engine, SessionLocal)
├── dependencies.py            # FastAPI dependency injection (get_current_user, ...)
├── auth.py                    # Hàm helper xác thực: hash/verify password, tạo JWT token
├── middleware.py              # Custom middleware (ChatSessionVersionMiddleware)
├── chat_utils.py              # Helper lấy lịch sử chat context cho Gemini
├── orchestrator_bridge.py     # Bridge điều phối giữa FastAPI ↔ Orchestrator agent
├── rate_limit.py              # Middleware giới hạn tần suất request
├── redis_client.py            # Kết nối Redis (rate limit, pairing code, ...)
├── requirements.txt           # Danh sách thư viện Python
│
├── routers/                   # Các module API được chia theo tính năng
│   ├── auth.py                # Đăng ký / Đăng nhập / Refresh token / Logout
│   ├── admin_mock.py          # Mock RESTful APIs /admin/mock/... cho Admin Portal
│   ├── bookmarks.py           # CRUD /bookmarks — Sổ Tay Bài Toán Yêu Thích
│   ├── chat.py                # Chat với AI (stream SSE) + thống kê session
│   ├── family.py              # Liên kết Phụ Huynh ↔ Học Sinh (pairing code)
│   ├── independence.py        # Điểm Tự Lực (Independence Score) sau khi giải bài
│   ├── insights.py            # AI Insights (background service) + Badge system
│   ├── metrics.py             # Thống kê học tập (heatmap, summary, streak, ...)
│   ├── sessions.py            # Quản lý phòng chat (tạo, xoá, đổi tên)
│   ├── upload.py              # Upload ảnh lên Cloudinary
│   └── users.py               # Thông tin người dùng
│
├── agents/                    # Các module AI Agent (KHÔNG chỉnh sửa khi không cần)
│   ├── orchestrator.py        # Điều phối routing đến đúng agent theo câu hỏi
│   ├── tutor_agent.py         # Agent gia sư Socratic (câu hỏi dẫn dắt)
│   ├── parent_insights_prompt.py  # Prompt + hàm gọi Gemini sinh báo cáo sư phạm
│   ├── flashcard_prompt.py    # Tạo flashcard từ session chat
│   └── boundary_extractor.py  # Trích xuất ranh giới bài toán từ ảnh
│
├── scripts/                   # Script tiện ích, migration DB, debug (chạy 1 lần)
│   ├── cleanup_guests.py      # Xóa session Guest cũ hơn 24h (chạy mỗi 1 giờ)
│   ├── drop_column.py         # Xóa cột pairing_code khỏi bảng users (đã dùng 1 lần)
│   ├── fix_db.py              # Thêm cột pairing_code (đã dùng 1 lần)
│   ├── simulate_link.py       # Giả lập liên kết phụ huynh-học sinh qua Redis
│   ├── migrate_*.py           # Các migration tạo bảng / index mới trên Neon DB
│   ├── verify_*.py            # Kiểm tra bảng / index đã tồn tại chưa
│   └── eval_orchestrator.py   # Đánh giá chất lượng routing của orchestrator
│
├── test/                      # Test tự động (chạy để verify logic)
│   ├── test_admin_mock.py           # Test API /admin/mock/... cho Admin Portal
│   ├── test_bookmarks_crud.py       # Test CRUD /bookmarks
│   ├── test_insights_badges.py      # Test AI Insights + Badge system
│   ├── test_heatmap_summary_metrics.py  # Test /metrics/heatmap + /metrics/summary
│   ├── test_child_problems_bookmark.py  # Test /parent/child-problems
│   ├── test_child_problems_lite.py      # Test nhẹ (không import toàn bộ app)
│   ├── test_ai_insights_schema.py       # Test schema AiInsightReportResponse
│   ├── test_boundary_extractor.py       # Test trích xuất ranh giới bài toán
│   ├── test_flashcard_prompt.py         # Test sinh flashcard từ Gemini
│   ├── test_flow.py                     # Test luồng link phụ huynh-học sinh (live)
│   └── test_link.py                     # Test gọi API link-student (live)
│
├── static/                    # File tĩnh (Lottie animation, v.v.)
│   └── lottie/
├── DOCS_ORCHESTRATOR.md       # Tài liệu kiến trúc Multi-Agent & Orchestrator
└── STRUCTURE.md               # Tài liệu cấu trúc thư mục backend (file này)
```

## Quy tắc thêm code mới

| Loại file             | Đặt ở đâu      |
|-----------------------|----------------|
| API endpoint mới      | `routers/`     |
| DB model mới          | `models.py`    |
| Pydantic schema mới   | `schemas.py`   |
| Script migration DB   | `scripts/`     |
| Test tự động          | `test/`        |
| AI Agent / Prompt     | `agents/`      |

## Ghi chú quan trọng

- **Không sửa file trong `agents/`** trừ khi có yêu cầu rõ ràng
- Sau mỗi migration, chạy `scripts/verify_tables.py` để xác nhận bảng đã tạo
- Test file đặt trong `test/`, đặt tên theo dạng `test_<tính_năng>.py`
