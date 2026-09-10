# main.py
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, auth
from database import engine, get_db

# Tự động tạo bảng 'users' trong database nếu chưa có
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

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
        role="USER"
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
def login(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    user = (
        db.query(models.User).filter(
            models.User.email == user_data.email 
        ).first()
    )
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
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

    # ---------------------------
    # ROTATE REFRESH TOKEN
    # ---------------------------

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
            "sub": user.id,
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