# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Dữ liệu gửi lên khi Đăng ký & Đăng nhập
class AuthInput(BaseModel):
    email: EmailStr
    password: str
    grade: Optional[int] = None  # Lớp học (4-9), chỉ bắt buộc cho STUDENT

# Dữ liệu trả về khi Đăng ký thành công
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    grade: Optional[int] = None  # Trả về lớp học nếu có

    class Config:
        from_attributes = True

# Dữ liệu trả về khi Đăng nhập thành công
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str

class GeminiRequest(BaseModel):
    session_id: str
    prompt: str
    problem_context: Optional[dict] = None  # Ngữ cảnh bài toán (correctSolution, v.v.) — dùng cho Trụ 1
    answer_status: Optional[str] = None # 'wrong' hoặc 'correct' (để tính hint)



class SessionCreate(BaseModel):
    title: Optional[str] = "Phòng chat mới"

class MessageResponse(BaseModel):
    id: str
    sender_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    class Config:
        from_attributes = True

class SessionStatsResponse(BaseModel):
    session_id: str
    consecutive_wrong_count: int
    hint_count: int
    not_understood_count: int

    class Config:
        from_attributes = True

class ComprehensionRequest(BaseModel):
    session_id: str
    understood: bool