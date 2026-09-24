# models.py
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
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

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Composite index: tối ưu query lấy tin nhắn trong 1 session, sort theo thứ tự thời gian
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )
    
    session = relationship("Session", back_populates="messages")