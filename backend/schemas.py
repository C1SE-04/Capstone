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
    session_version: Optional[int] = 1  # US 6.2: phiên bản session của user

    class Config:
        from_attributes = True

# Dữ liệu trả về khi Đăng nhập thành công
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    grade: Optional[int] = None  # Task #132: trả thêm grade_level về FE sau login
    session_version: Optional[int] = 1  # US 6.2: phiên bản session của user
    
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
    attachment_url: Optional[str] = None  # US 6.4 - Task #173: URL ảnh Cloudinary đã upload (nếu có)



class SessionCreate(BaseModel):
    title: Optional[str] = "Phòng chat mới"

class MessageResponse(BaseModel):
    id: str
    sender_type: str
    content: str
    attachment_url: Optional[str] = None  # US 6.4 - Task #173: URL ảnh đính kèm từ Cloudinary
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


class SummaryCardsMetric(BaseModel):
    completed_problems: int = 0
    avg_independence_score: float = 0.0
    mastery_level: str = "Chưa có dữ liệu"
    streak_days: int = 0
    total_active_minutes: int = 0
    total_active_hours: float = 0.0


class IndependenceTrendPoint(BaseModel):
    """Điểm dữ liệu theo ngày cho Line Chart Recharts."""
    date: str                  # "YYYY-MM-DD"
    display_date: str          # "DD/MM" để hiển thị trục X Recharts
    score: int                 # Điểm Independence trung bình trong ngày (10 - 100)
    problems_count: int = 1    # Số bài giải trong ngày
    avg_hints: float = 0.0     # Số gợi ý trung bình dùng


class ActivityHeatmapPoint(BaseModel):
    """Điểm dữ liệu cho Biểu đồ hoạt động học."""
    date: str                  # "YYYY-MM-DD"
    day_of_week: str           # "Thứ Hai", "Thứ Ba", ...
    active_minutes: int = 0    # Số phút tương tác học tập thực tế
    intensity_level: int = 0   # Mức nhiệt từ 0 (không học) đến 4 (học nhiều > 45p)


class MasteryDistribution(BaseModel):
    """Thống kê tỷ lệ phân bố các mức độ tự lực theo barem sư phạm."""
    excellent_count: int = 0       # >= 80 điểm
    good_count: int = 0            # 60 - 79 điểm
    developing_count: int = 0      # 40 - 59 điểm
    needs_support_count: int = 0   # < 40 điểm


class ParentDashboardMetricsResponse(BaseModel):
    """
    Schema phản hồi tổng hợp cho API Dashboard Phụ Huynh."""
    student_id: str
    time_range: str = "7d"         # "7d" hoặc "30d"
    start_date: str                # "YYYY-MM-DD"
    end_date: str                  # "YYYY-MM-DD"
    summary_cards: SummaryCardsMetric
    independence_trend: list[IndependenceTrendPoint] = []
    activity_heatmap: list[ActivityHeatmapPoint] = []
    mastery_distribution: MasteryDistribution

    class Config:
        from_attributes = True


class HeatmapDayItem(BaseModel):
    """Điểm dữ liệu ngày trong Heatmap, tương thích 100% với HeatmapDay ở Frontend."""
    date: str                  # "YYYY-MM-DD"
    minutes: int = 0           # số phút học thực tế (0 = không học)
    active_minutes: int = 0    # alias cho số phút
    intensity_level: int = 0   # 0 (0p), 1 (1-20p), 2 (21-45p), 3 (46-75p), 4 (>75p)


class ActivityHeatmapResponse(BaseModel):
    """Phản hồi API GET /metrics/heatmap theo chuẩn GitHub Contribution Graph."""
    student_id: str
    weeks: int
    days: int
    start_date: str
    end_date: str
    total_active_minutes: int
    total_study_hours: float
    data: list[HeatmapDayItem] = []


class SummaryCardsResponse(BaseModel):
    """Phản hồi API GET /metrics/summary chứa số liệu thật thay thế mock data."""
    student_id: str
    time_range: str
    start_date: str
    end_date: str
    # Snake_case
    completed_problems: int
    completed_change: Optional[str] = "+0%"
    independence_score: int
    independence_level: str
    current_streak: int
    max_streak: int
    total_study_hours: float
    avg_minutes_per_day: int
    total_active_minutes: int
    # CamelCase aliases (tương thích trực tiếp với interface SummaryMetrics ở Frontend)
    completedProblems: int
    completedChange: Optional[str] = "+0%"
    independenceScore: int
    independenceLevel: str
    currentStreak: int
    maxStreak: int
    totalStudyHours: float
    avgMinutesPerDay: int


class CloudinaryUploadResponse(BaseModel):
    """Response trả về sau khi upload ảnh lên Cloudinary thành công."""
    success: bool
    url: str                    # HTTPS URL công khai để FE hiển thị và lưu vào DB
    public_id: str              # ID của file trên Cloudinary (dùng để xóa/quản lý sau này)
    secure_url: str             # URL https:// (bao giờ cũng giống url khi upload secure=True)
    format: str                 # Định dạng file: jpg, png, webp, v.v.
    width: Optional[int] = None
    height: Optional[int] = None
    bytes: Optional[int] = None # Kích thước file (bytes)


class CloudinarySignatureResponse(BaseModel):
    """Response trả về chữ ký an toàn để FE upload thẳng lên Cloudinary (unsigned upload)."""
    signature: str
    timestamp: int
    api_key: str
    cloud_name: str
    folder: str


# --- US 7.1: Child Problems API (Task T7.6) ---

class ChildProblemItem(BaseModel):
    """Thông tin 1 bài toán con đã giải, trả về cho Dashboard Phụ Huynh."""
    session_id: str                          # ID session chứa bài toán
    session_title: Optional[str] = None      # Tiêu đề phòng chat (nếu có)
    completed_at: datetime                   # Thời điểm hoàn thành (timestamp IndependenceScore)
    score: int                               # Điểm tự lực (0–100)
    hints_used: int                          # Số gợi ý đã dùng
    not_understood_count: int                # Số lần bấm "Chưa hiểu"
    evaluation: Optional[str] = None        # Nhãn đánh giá mức độ ("Xuất sắc", "Khá", ...)
    attachment_url: Optional[str] = None    # Ảnh đề bài từ Cloudinary (nếu có)
    chat_summary: Optional[str] = None      # Đoạn chat tóm tắt (3 tin nhắn USER đầu tiên)

    class Config:
        from_attributes = True


class ChildProblemsResponse(BaseModel):
    """Phản hồi API GET /parent/child-problems."""
    student_id: str
    total: int                               # Tổng số bài đã giải
    page: int
    page_size: int
    items: list[ChildProblemItem] = []


# --- US 7.2: Bookmark / Notebook Schema (Task T7.7) ---

class BookmarkCreate(BaseModel):
    """Body gửi lên khi học sinh lưu bài toán vào Sổ Tay."""
    session_id: str
    note: Optional[str] = None              # Ghi chú tuỳ ý của học sinh


class BookmarkResponse(BaseModel):
    """Thông tin 1 bookmark trả về."""
    id: str
    student_id: str
    session_id: str
    session_title: Optional[str] = None
    problem_snapshot: Optional[str] = None  # Đề bài (nội dung tin nhắn USER đầu tiên)
    attachment_url: Optional[str] = None    # Ảnh đề bài Cloudinary
    chat_summary: Optional[str] = None      # Tóm tắt đoạn chat khi lưu
    independence_score: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ========================================================
# --- US 7.1: AI Learning Insights Schemas (Task T7.2) ---
# ========================================================

class TopicBreakdownItem(BaseModel):
    """Thống kê chi tiết kết quả học theo từng dạng toán cụ thể."""
    topic_name: str
    problems_solved: int = 0
    avg_independence: float = 0.0
    hints_used: int = 0
    not_understood: int = 0


class AiInsightReportResponse(BaseModel):
    """
    Schema phản hồi cốt lõi của Báo Cáo Nhận Xét Sư Phạm từ AI.
    Được sinh ra từ Gemini và kiểm duyệt qua Pydantic v2.
    """
    summary: str
    strengths: list[str] = []
    weak_points: list[str] = []
    recommendations: list[str] = []
    mastery_assessment: Optional[str] = "Đang tiến bộ"
    is_fallback: Optional[bool] = False
    fallback_reason: Optional[str] = None

    class Config:
        from_attributes = True


class AiInsightGenerateRequest(BaseModel):
    """Dữ liệu đầu vào yêu cầu sinh Báo Cáo Nhận Xét Sư Phạm cho 1 học sinh."""
    student_id: str
    student_name: str
    grade_level: int
    period_description: Optional[str] = "7 ngày gần nhất"
    total_problems_completed: int
    average_independence_score: float
    total_hints_used: int = 0
    total_not_understood_count: int = 0
    topic_breakdown: list[TopicBreakdownItem] = []


class ParentAiInsightResponse(BaseModel):
    """
    Schema đầy đủ trả về cho Frontend Parent Dashboard (API GET /parent/insights).
    Tương thích với giao diện <AIInsightsCard />.
    """
    student_id: str
    student_name: Optional[str] = None
    period_description: str = "Tuần này"
    insight: AiInsightReportResponse
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
