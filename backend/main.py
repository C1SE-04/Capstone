from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv
import google.generativeai as genai
import orchestrator


load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, schemas, auth, dependencies
from database import engine, get_db
from fastapi.security import OAuth2PasswordRequestForm

# Tự động tạo bảng 'users' trong database nếu chưa có
try:
    models.Base.metadata.create_all(bind=engine)
except Exception as _db_err:
    import warnings
    warnings.warn(f"[WARN] Không thể kết nối DB khi startup: {_db_err}", RuntimeWarning)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. API ĐĂNG KÝ
@app.post("/register/student", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    # tạo user, hash pass và lưu vào DB
    new_user = models.User(
        email=user_data.email,
        hashed_password=auth.hash_password(user_data.password),
        role="STUDENT"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/register/monitor", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_monitor(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    # tạo user, hash pass và lưu vào DB
    new_user = models.User(
        email=user_data.email,
        hashed_password=auth.hash_password(user_data.password),
        role="MONITOR"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = (
        db.query(models.User).filter(
            models.User.email == form_data.username
        ).first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng"
        )

    raw_refresh_token = auth.create_refresh_token()
    refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(raw_refresh_token),
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
        ),
        revoked=False
    )
    db.add(refresh_token_db)
    db.commit()
    
    access_token = auth.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "bearer"
    }


@app.post("/refresh", response_model=schemas.TokenResponse)
def refresh_access_token(
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db)
):
    token_hash = auth.hash_refresh_token(
        data.refresh_token
    )

    stored_token = (
        db.query(models.RefreshToken)
        .filter(
            models.RefreshToken.token_hash == token_hash
        )
        .first()
    )

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ"
        )

    if stored_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã bị thu hồi"
        )

    now = datetime.now(timezone.utc)

    if stored_token.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token đã hết hạn"
        )

    user = (
        db.query(models.User)
        .filter(models.User.id == stored_token.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User không tồn tại"
        )
    # ROTATE REFRESH TOKEN

    # Token cũ không được sử dụng lại
    stored_token.revoked = True

    new_refresh_token = auth.create_refresh_token()

    new_refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(
            new_refresh_token
        ),
        expires_at=(
            now
            + timedelta(
                days=auth.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )
    )

    db.add(new_refresh_token_db)

    # Tạo access token mới
    new_access_token = auth.create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role
        }
    )

    db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }
    
@app.get("/user/me")
def get_current_user_info(current_user: dict = Depends(dependencies.get_current_user)):
    return {"message": "Thông tin người dùng hiện tại", "user": current_user}

@app.get("/monitor/dashboard")
def monitor_dashboard(current_user: dict = Depends(dependencies.require_role(["MONITOR"]))):
    return {"message": "Chào mừng cán sự lớp", "user": current_user}

@app.delete("/students/{student_id}")
def delete_student(student_id: int, current_user: dict = Depends(dependencies.require_role(["ADMIN"]))):
    return {"message": f"Đã xoá sinh viên {student_id}"}

@app.post("/chat/orchestrator")
def chat_with_orchestrator(request: schemas.GeminiRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return orchestrator.process_query_with_orchestrator(request.prompt, db, background_tasks)

@app.post("/gemini/generate")
def generate_gemini(request: schemas.GeminiRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")
    
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        response = model.generate_content(request.prompt)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/gemini/models")
def list_available_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")
    genai.configure(api_key=api_key)
    try:
        models = [
            m.name for m in genai.list_models() 
            if "generateContent" in m.supported_generation_methods
        ]
        return {"supported_models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))