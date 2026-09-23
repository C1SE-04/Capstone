from fastapi import FastAPI
import models
from database import engine

# Import các routers
from routers import auth, users, chat, sessions

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

# Đăng ký (include) các module API
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(sessions.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Socratic Chatbot API!"}