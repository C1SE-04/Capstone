from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from middleware import JWTMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",  # Phòng trường hợp trình duyệt fetch bằng IP
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thêm JWT Middleware vào ứng dụng
app.add_middleware(JWTMiddleware)

@app.get("/")
def read_root():
    return {"message": "CORS đã sẵn sàng!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FastAPI is healthy and CORS is working!"}

@app.get("/api/protected")
def protected_route(request: Request):
    # Route này không nằm trong public_paths nên sẽ phải đi qua middleware
    return {
        "message": "Bạn đã vượt qua middleware thành công!",
        "user_info": request.state.user
    }