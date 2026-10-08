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
from cleanup_guests import cleanup_old_guest_sessions
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

# Cấu hình CORS của team FE
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

@app.on_event("shutdown")
async def shutdown_event():
    # Đóng kết nối Redis khi server dừng
    await close_redis()
    # print("🔴 Redis đã đóng kết nối.")