from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/")
def read_root():
    return {"message": "Welcome to Socratic Chatbot API!"}

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
        print("✅ Redis kết nối thành công!")
    except Exception as e:
        print(f"⚠️  Redis không khả dụng: {e}. Rate-limit sẽ bỏ qua (fail-open).")
    # 2. Khởi động task dọn dẹp Guest session
    asyncio.create_task(schedule_guest_cleanup())

@app.on_event("shutdown")
async def shutdown_event():
    # Đóng kết nối Redis khi server dừng
    await close_redis()
    print("🔴 Redis đã đóng kết nối.")