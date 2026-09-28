# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Dữ liệu gửi lên khi Đăng ký & Đăng nhập
class AuthInput(BaseModel):
    email: EmailStr
    password: str

# Dữ liệu trả về khi Đăng ký thành công
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str

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
    # answer_status: FE gửi lên để BE biết học sinh vừa trả lời đúng hay sai
    # Các giá trị hợp lệ: None (chưa biết), "correct" (đúng), "wrong" (sai)
    answer_status: Optional[str] = None


class ComprehensionRequest(BaseModel):
    """Request gửi lên khi học sinh bấm nút 'Đã hiểu' hoặc 'Chưa hiểu'."""
    session_id: str
    understood: bool  # True = Đã hiểu, False = Chưa hiểu


class SessionStatsResponse(BaseModel):
    """Trả về số liệu học tập của 1 session cho FE."""
    session_id: str
    consecutive_wrong_count: int
    hint_count: int
    not_understood_count: int

    class Config:
        from_attributes = True



class SessionCreate(BaseModel):
    title: Optional[str] = "Phòng chat mới"

class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True