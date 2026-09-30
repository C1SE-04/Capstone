from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

import models, schemas, auth
from database import get_db

router = APIRouter(tags=["Auth"])

@router.post("/register/student", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    normalized_email = user_data.email.lower()
    existing_user = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    new_user = models.User(
        email=normalized_email,
        hashed_password=auth.hash_password(user_data.password),
        role="STUDENT"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/register/monitor", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_monitor(user_data: schemas.AuthInput, db: Session = Depends(get_db)):
    normalized_email = user_data.email.lower()
    existing_user = db.query(models.User).filter(models.User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")

    new_user = models.User(
        email=normalized_email,
        hashed_password=auth.hash_password(user_data.password),
        role="MONITOR"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

from sqlalchemy import func

@router.post("/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Chuẩn hóa email về chữ thường trước khi tra cứu DB — cho phép đăng nhập với mọi kiểu viết hoa
    normalized_username = form_data.username.lower()
    user = (
        db.query(models.User).filter(
            func.lower(models.User.email) == normalized_username
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

@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_access_token(
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db)
):
    token_hash = auth.hash_refresh_token(data.refresh_token)

    stored_token = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.token_hash == token_hash)
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

    # Token cũ không được sử dụng lại
    stored_token.revoked = True

    new_refresh_token = auth.create_refresh_token()

    new_refresh_token_db = models.RefreshToken(
        user_id=user.id,
        token_hash=auth.hash_refresh_token(new_refresh_token),
        expires_at=(
            now + timedelta(days=auth.REFRESH_TOKEN_EXPIRE_DAYS)
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
