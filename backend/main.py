from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
def read_root():
    return {"message": "CORS đã sẵn sàng!"}

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "FastAPI is healthy and CORS is working!"}