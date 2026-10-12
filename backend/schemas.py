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
    grade: Optional[int] = None  # Task #132: trả thêm grade_level về FE sau login
    
class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str

class GeminiRequest(BaseModel):
    session_id: str
    prompt: str
    problem_context: Optional[dict] = None  # Ngữ cảnh bài toán (correctSolution, v.v.) — dùng cho Trụ 1
    answer_status: Optional[str] = None # 'wrong' hoặc 'correct' (để tính hint)
    grade_level: Optional[int] = None  # Task #132: lớp học của học sinh, FE gửi lên sau login



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

# --- US 5.2: Parent Dashboard Schemas ---

class PairingCodeResponse(BaseModel):
    pairing_code: str
    expires_in: Optional[int] = None

class LinkStudentRequest(BaseModel):
    pairing_code: str

class UpdateStudentNicknameRequest(BaseModel):
    nickname: str

class LinkedStudentResponse(BaseModel):
    student_id: str
    email: str
    nickname: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- US 5.2: Metrics API Schemas ---

class DailyMetric(BaseModel):
    """Số liệu tổng hợp theo từng ngày (dùng cho biểu đồ tuần)."""
    date: str           # "YYYY-MM-DD"
    message_count: int  # Số tin nhắn học sinh gửi trong ngày
    session_count: int  # Số phòng chat mở trong ngày

class StudentMetricsResponse(BaseModel):
    """Response trả về từ GET /family/students/{student_id}/metrics."""
    student_id: str
    week_start: str     # "YYYY-MM-DD"
    week_end: str       # "YYYY-MM-DD"
    total_messages: int         # Tổng tin nhắn cả tuần (COUNT trong SQL)
    total_sessions: int         # Tổng phòng chat cả tuần (COUNT trong SQL)
    avg_messages_per_day: float # Trung bình tin nhắn/ngày (AVG trong SQL)
    daily: list[DailyMetric]    # Chi tiết từng ngày để vẽ biểu đồ


# --- US 6.3: Idle Detection & Active Metrics (Task #168 & #169) ---

class RestartMetricRequest(BaseModel):
    timestamp: Optional[int] = None
    timestamp_ms: Optional[int] = None
    restart_time: Optional[str] = None
    session_id: Optional[str] = None


class RestartMetricResponse(BaseModel):
    success: bool
    message: str
    session_id: Optional[str] = None
    interval_id: Optional[str] = None
    start_time: Optional[str] = None
    active_seconds: int = 0


# --- US 6.1: Independence / Mastery Score (Task #159 & #160) ---

class IndependenceRecordCreate(BaseModel):
    session_id: str
    student_id: Optional[str] = None
    score: Optional[int] = None
    hints_used: Optional[int] = None
    not_understood_count: Optional[int] = None
    evaluation: Optional[str] = None


class IndependenceRecordResponse(BaseModel):
    id: str
    session_id: str
    student_id: str
    score: int
    hints_used: int
    not_understood_count: int
    evaluation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IndependenceSummaryResponse(BaseModel):
    student_id: str
    average_score: float
    total_completed: int
    latest_score: Optional[int] = None
    evaluation_level: str
    history: list[IndependenceRecordResponse] = []
