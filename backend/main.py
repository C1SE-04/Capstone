from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
import os
import models
from database import engine

import asyncio
# Import các routers
from routers import auth, users, chat, sessions
from scripts.cleanup_guests import cleanup_old_guest_sessions

from redis_client import get_redis, close_redis

# Tự động tạo bảng 'users' trong database nếu chưa có
try:
    models.Base.metadata.create_all(bind=engine)
except Exception as _db_err:
    import warnings
    warnings.warn(f"[WARN] Không thể kết nối DB khi startup: {_db_err}", RuntimeWarning)

app = FastAPI(
    title="Socratic Chatbot API",
    description="Backend API cho Chatbot Socratic",
    version="1.0.0"
)

# Task T6.11 (US 6.2): Middleware kiểm tra session_version cho API /chat
from middleware import ChatSessionVersionMiddleware
app.add_middleware(ChatSessionVersionMiddleware)

# Cấu hình CORS của team FE (bọc ngoài cùng để response từ middleware cũng có CORS headers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://socratickid.vercel.app",
        "https://*.vercel.app",  # Cho phép cả preview deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký (include) các module API
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(sessions.router)
from routers import family
app.include_router(family.router)
from routers import metrics  # Task #121: API thống kê thời gian học
app.include_router(metrics.router)
from routers import independence  # Task #159 & #160: API điểm Tự Lực (Independence Score)
app.include_router(independence.router)
from routers import upload  # US 6.4 - Task #173: Cloudinary upload & ký chữ ký ảnh
app.include_router(upload.router)
from routers import insights  # US 7.3 & 7.4: AI Insights background service + Badge system
app.include_router(insights.router)
from routers import bookmarks  # US 7.2 (Task T7.13): CRUD Sổ Tay Bài Toán
app.include_router(bookmarks.router)
from routers import admin_mock  # US 7.3 (Task T7.31): Mock Data Router cho Admin Portal
app.include_router(admin_mock.router)




@app.get("/")
def read_root():
    return {"message": "Welcome to Socratic Chatbot API!"}

# Task #101: Serve file hoạt hình Lottie với Cache-Control header
# Cho phép trình duyệt học sinh cache file trong 1 năm, tránh tải đi tải lại
LOTTIE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "lottie")

@app.get("/static/lottie/{filename}")
async def serve_lottie(filename: str):
    """
    Phục vụ file hoạt hình Lottie với Cache-Control header.
    FE có thể trỏ URL về đây thay vì lấy từ public/ của Next.js
    để tận dụng cache tập trung ở Backend.
    """
    filepath = os.path.join(LOTTIE_DIR, filename)

    if not os.path.exists(filepath):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"File {filename} không tìm thấy")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    return Response(
        content=content,
        media_type="application/json",
        headers={
            # public: trình duyệt + CDN được phép cache
            # max-age=31536000: cache trong 1 năm (tính bằng giây)
            # immutable: file không thay đổi → bỏ qua kiểm tra lại
            "Cache-Control": "public, max-age=31536000, immutable",
        }
    )

async def schedule_guest_cleanup():
    while True:
        try:
            cleanup_old_guest_sessions()
        except Exception as e:
            pass
        await asyncio.sleep(3600)  # Chạy mỗi 1 tiếng 1 lần

@app.on_event("startup")
async def startup_event():
    # 1. Khởi động Redis connection pool (Task #90)
    try:
        redis = await get_redis()
        await redis.ping()  # Kiểm tra kết nối thực sự
        # print("✅ Redis kết nối thành công!")
    except Exception as e:
        print(f"⚠️  Redis không khả dụng: {e}. Rate-limit sẽ bỏ qua (fail-open).")
    # 2. Khởi động task dọn dẹp Guest session
    asyncio.create_task(schedule_guest_cleanup())
    # 3. Đảm bảo tài khoản ADMIN duy nhất luôn sẵn sàng
    try:
        from scripts.init_admin import ensure_single_admin
        ensure_single_admin()
    except Exception as e:
        print(f"⚠️ Không thể khởi tạo Admin: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    # Đóng kết nối Redis khi server dừng
    await close_redis()
    # print("🔴 Redis đã đóng kết nối.")