# models.py
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    grade = Column(Integer, nullable=True)  # Chỉ dùng cho STUDENT (lớp 4-9)
    session_version = Column(Integer, default=1, nullable=False, server_default="1")  # US 6.2 (T6.10): version để đồng bộ session giữa các tab
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Quan hệ Phụ huynh - Học sinh
    monitored_students = relationship(
        "User", 
        secondary="parent_student_links",
        primaryjoin="User.id == ParentStudentLink.parent_id",
        secondaryjoin="User.id == ParentStudentLink.student_id",
        backref="monitors"
    )

class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    parent_id = Column(
        String, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    student_id = Column(
        String, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    )
    
    # Biệt danh do phụ huynh tự đặt cho con trên giao diện (US 5.2)
    student_nickname = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete=("CASCADE")),
        nullable=False,
        index=True
    )
    token_hash = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )

class OrchestratorLog(Base):
    __tablename__ = "orchestrator_logs"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_query = Column(String, nullable=False)
    target_agent = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String, nullable=True) # Tên phiên chat, có thể sinh tự động
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Composite index: tối ưu query lấy sessions của 1 user, sort theo mới nhất
    __table_args__ = (
        Index("ix_sessions_user_updated", "user_id", "updated_at"),
    )

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", passive_deletes=True, order_by="Message.created_at")
    active_intervals = relationship("SessionActiveInterval", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)
    independence_records = relationship("IndependenceScore", back_populates="session", cascade="all, delete-orphan", passive_deletes=True)

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    session_id = Column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sender_type = Column(String, nullable=False) # "USER", "AGENT_TUTOR", v.v.
    content = Column(String, nullable=False)
    # US 6.4 - Task #173: Lưu đường link HTTPS Cloudinary của ảnh đính kèm (nếu có).
    # DB chỉ lưu URL chuỗi, file thực tế được lưu trên Cloudinary.
    attachment_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Composite index: tối ưu query lấy tin nhắn trong 1 session, sort theo thứ tự thời gian
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )
    
    session = relationship("Session", back_populates="messages")



class SessionStats(Base):
    """Bộ đếm hành vi học tập của học sinh trong từng session chat."""
    __tablename__ = "session_stats"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    session_id = Column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1 session chỉ có 1 bộ stats
        index=True
    )
    # Số lần học sinh trả lời sai liên tiếp trong bài toán hiện tại
    # Reset về 0 khi học sinh trả lời đúng
    consecutive_wrong_count = Column(Integer, default=0, nullable=False)
    # Số lần hệ thống đã đưa ra gợi ý (hint) trong bài toán hiện tại
    # Reset về 0 khi học sinh trả lời đúng
    hint_count = Column(Integer, default=0, nullable=False)
    # Tổng số lần học sinh bấm "Chưa hiểu" trong toàn session
    not_understood_count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SessionActiveInterval(Base):
    """
    Bảng ghi nhận các khoảng thời gian học tập active (thực sự tương tác) trong session chat.
    US 6.3 - Task #168 & #169:
    - Loại trừ thời gian idle (học sinh không gửi tin nhắn > 10 phút).
    - start_time: Thời điểm bắt đầu khoảng active (gửi tin hoặc bấm 'Đang học').
    - end_time: Thời điểm kết thúc tương tác gần nhất trước khi idle.
    - active_seconds: Số giây active thực tế trong khoảng này.
    """
    __tablename__ = "session_active_intervals"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    session_id = Column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    active_seconds = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_active_intervals_user_start", "user_id", "start_time"),
        Index("ix_active_intervals_session_end", "session_id", "end_time"),
    )

    session = relationship("Session", back_populates="active_intervals")


class IndependenceScore(Base):
    """
    US 6.1 - Task #159 & #160:
    Lưu trữ điểm Tự lực (Independence Score) của học sinh sau khi hoàn thành bài toán (bấm 'Đã hiểu').
    - score: Điểm số từ 0 - 100
    - hints_used: Số gợi ý đã dùng trong bài
    - not_understood_count: Số lần bấm 'Chưa hiểu'
    - evaluation: Đánh giá phân loại mức độ tự lực
    """
    # Nội dung đề bài toán trích xuất từ phiên học
    problem_text = Column(String, nullable=True)
    # Mã băm SHA-256 của đề bài đã chuẩn hóa (dùng cho Fast-path deduplication)
    problem_hash = Column(String(64), nullable=True, index=True)
    # Phân loại: NEW_TOPIC | ISOMORPHIC_PRACTICE | EXACT_DUPLICATE
    category = Column(String, default="NEW_TOPIC", nullable=True)
    # Cờ đánh dấu bài trùng lặp (nếu True: chặn không cộng dồn vào total_completed)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    # Lời nhắc nhở nhẹ nhàng nếu là bài trùng lặp EXACT_DUPLICATE
    gentle_reminder = Column(String, nullable=True)
    __tablename__ = "independence_scores"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    session_id = Column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    student_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    score = Column(Integer, nullable=False)
    hints_used = Column(Integer, default=0, nullable=False)
    not_understood_count = Column(Integer, default=0, nullable=False)
    evaluation = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_independence_student_created", "student_id", "created_at"),
        Index("ix_independence_session_created", "session_id", "created_at"),
        Index("ix_independence_student_hash", "student_id", "problem_hash"),
    )

    session = relationship("Session", back_populates="independence_records")
    student = relationship("User", backref="independence_records")


class ProblemBookmark(Base):
    """
    US 7.2 - Task T7.7:
    Sổ Tay Bài Toán Yêu Thích (Bookmark Notebook).
    Lưu snapshot của bài toán khi học sinh bấm "Lưu vào Sổ tay" sau khi bấm "Đã hiểu".
    - problem_snapshot: Nội dung đề bài (tin nhắn USER đầu tiên trong session)
    - attachment_url: URL ảnh đề bài trên Cloudinary (nếu có)
    - chat_summary: Đoạn chat tóm tắt (3 tin nhắn USER đầu tiên, nối bằng " | ")
    - independence_score: Điểm tự lực tại thời điểm lưu
    - note: Ghi chú tuỳ ý của học sinh
    """
    __tablename__ = "problem_bookmarks"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    student_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    session_id = Column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Snapshot đề bài tại thời điểm lưu (tin nhắn USER đầu tiên trong session)
    problem_snapshot = Column(String, nullable=True)
    # URL ảnh đề bài Cloudinary (nếu học sinh upload ảnh)
    attachment_url = Column(String, nullable=True)
    # Tóm tắt đoạn chat (3 tin nhắn USER đầu tiên, giúp học sinh nhớ lại bài)
    chat_summary = Column(String, nullable=True)
    # Điểm tự lực (Independence Score) tại thời điểm lưu
    independence_score = Column(Integer, nullable=True)
    # Tên bài toán do học sinh tự đặt hoặc AI gợi ý (US 8.2)
    title = Column(String, nullable=True)
    # Ghi chú tuỳ ý của học sinh
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Index hỗ trợ tìm kiếm nhanh theo học sinh và session
        Index("ix_bookmarks_student_session", "student_id", "session_id"),
        Index("ix_bookmarks_student_created", "student_id", "created_at"),
    )

    student = relationship("User", backref="bookmarks")
    session = relationship("Session", backref="bookmarks")


class BookmarkPlaylist(Base):
    """
    US 8.2: Danh sách phát / Thư mục Sổ Tay (Bookmark Playlist) phong cách YouTube.
    Học sinh có thể tạo nhiều playlist (Yêu thích, Ôn thi HK1, ...) để gom nhóm bài toán.
    """
    __tablename__ = "bookmark_playlists"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    student_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    color = Column(String, nullable=True)        # Mã màu HEX phân loại (VD: #F59E0B)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_bookmark_playlists_student_created", "student_id", "created_at"),
        Index("ix_bookmark_playlists_student_name", "student_id", "name"),
    )

    student = relationship("User", backref="bookmark_playlists")
    items = relationship(
        "BookmarkPlaylistItem",
        back_populates="playlist",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BookmarkPlaylistItem.added_at.desc()",
    )


class BookmarkPlaylistItem(Base):
    """
    US 8.2: Bảng liên kết N-N giữa BookmarkPlaylist và ProblemBookmark.
    Một bài toán có thể thuộc nhiều playlist (checkbox YouTube-style).
    """
    __tablename__ = "bookmark_playlist_items"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    playlist_id = Column(
        String,
        ForeignKey("bookmark_playlists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bookmark_id = Column(
        String,
        ForeignKey("problem_bookmarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, default=0, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_playlist_items_unique", "playlist_id", "bookmark_id", unique=True),
        Index("ix_playlist_items_playlist", "playlist_id", "added_at"),
        Index("ix_playlist_items_bookmark", "bookmark_id"),
    )

    playlist = relationship("BookmarkPlaylist", back_populates="items")
    bookmark = relationship("ProblemBookmark", backref="playlist_items")



class ParentAiInsight(Base):
    """
    US 7.3 (Task T7.8):
    Lưu kết quả báo cáo AI Learning Insights do background service sinh ra.
    - Mỗi record tương ứng với 1 lần chạy weekly scan cho 1 học sinh.
    - report_json: Nội dung JSON đầy đủ của AiInsightReportResponse.
    - period_start / period_end: Khoảng thời gian dữ liệu được phân tích (thường là 7 ngày).
    - is_fallback: True nếu Gemini gặp lỗi và dùng báo cáo dự phòng.
    """
    __tablename__ = "parent_ai_insights"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    student_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Khoảng thời gian phân tích (start → end, mặc định 7 ngày gần nhất)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    # Toàn bộ JSON báo cáo (summary, strengths, weak_points, recommendations, mastery_assessment)
    report_json = Column(String, nullable=False)
    # Điểm tự lực trung bình trong kỳ (lưu riêng để query nhanh, không cần parse JSON)
    avg_independence_score = Column(Integer, nullable=True)
    # Tổng số bài giải trong kỳ
    total_problems = Column(Integer, default=0, nullable=False)
    # True nếu Gemini lỗi và dùng báo cáo fallback
    is_fallback = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Tối ưu query lấy insight mới nhất của 1 học sinh
        Index("ix_ai_insights_student_created", "student_id", "created_at"),
    )

    student = relationship("User", backref="ai_insights")


# ────────────────────────────────────────────────────────────────────────────
# US 7.4 (Task T7.9): Hệ thống Huy Hiệu (Badge System)
# ────────────────────────────────────────────────────────────────────────────

# Danh mục tất cả huy hiệu trong hệ thống
BADGE_CATALOG = {
    # ── Huy hiệu theo Streak ──────────────────────────────────────────────
    "streak_3":   {"name": "Ngọn Lửa Nhỏ",   "description": "Học 3 ngày liên tiếp",  "category": "streak",  "threshold": 3},
    "streak_7":   {"name": "Tuần Bứt Phá",    "description": "Học 7 ngày liên tiếp",  "category": "streak",  "threshold": 7},
    "streak_14":  {"name": "Kiên Định 2 Tuần","description": "Học 14 ngày liên tiếp", "category": "streak",  "threshold": 14},
    "streak_30":  {"name": "Siêu Sao Tháng",  "description": "Học 30 ngày liên tiếp", "category": "streak",  "threshold": 30},
    # ── Huy hiệu theo số bài hoàn thành ──────────────────────────────────
    "problems_5":   {"name": "Người Bắt Đầu",   "description": "Hoàn thành 5 bài toán",   "category": "problems", "threshold": 5},
    "problems_20":  {"name": "Người Chăm Chỉ",  "description": "Hoàn thành 20 bài toán",  "category": "problems", "threshold": 20},
    "problems_50":  {"name": "Nhà Toán Học",    "description": "Hoàn thành 50 bài toán",  "category": "problems", "threshold": 50},
    "problems_100": {"name": "Huyền Thoại",     "description": "Hoàn thành 100 bài toán", "category": "problems", "threshold": 100},
    # ── Huy hiệu theo điểm Tự Lực ────────────────────────────────────────
    "independence_60": {"name": "Tự Lực Tốt",      "description": "Đạt điểm tự lực TB >= 60", "category": "independence", "threshold": 60},
    "independence_80": {"name": "Tự Lực Xuất Sắc", "description": "Đạt điểm tự lực TB >= 80", "category": "independence", "threshold": 80},
}


class StudentBadge(Base):
    """
    US 7.4 (Task T7.9):
    Lưu các huy hiệu học sinh đã mở khóa.
    - badge_key: Khóa định danh huy hiệu (VD: "streak_7", "problems_50")
    - Mỗi học sinh chỉ nhận mỗi huy hiệu 1 lần (unique constraint).
    """
    __tablename__ = "student_badges"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    student_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Khóa huy hiệu (tham chiếu BADGE_CATALOG, VD: "streak_7")
    badge_key = Column(String, nullable=False)
    # Tên huy hiệu (lưu snapshot để không phụ thuộc BADGE_CATALOG)
    badge_name = Column(String, nullable=False)
    # Mô tả huy hiệu
    badge_description = Column(String, nullable=True)
    # Phân loại (streak / problems / independence)
    category = Column(String, nullable=False)
    # Thời điểm mở khóa
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Mỗi học sinh chỉ nhận mỗi huy hiệu 1 lần
        Index("ix_student_badges_unique", "student_id", "badge_key", unique=True),
        Index("ix_student_badges_student", "student_id", "unlocked_at"),
    )

