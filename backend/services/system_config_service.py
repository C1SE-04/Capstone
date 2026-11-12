"""
US 10.3 - System Config Service: Quản Trị Cấu Hình Hệ Thống & Dynamic Hot-Reloading (T10.3.1)
=============================================================================================
Module điều phối toàn bộ cấu hình AI Runtime, tham số sư phạm, rate limit và mock month:
  - get_system_settings()   : Đọc từ Redis Cache (sub-millisecond) -> Fallback Neon PostgreSQL (TTL 300s).
  - update_system_settings(): Cập nhật DB, tự động ghi Audit Trail, Invalidate Redis Cache tức thì.
  - rollback_system_settings(): Khôi phục cấu hình từ snapshot phiên trước (AC-SET-07).
  - get_setting_audits()    : Truy vấn danh sách lịch sử thay đổi cấu hình.

Tương thích đa hạ tầng Redis:
  1. Upstash REST Client (upstash_redis nếu cài đặt và có UPSTASH_REDIS_REST_URL/TOKEN)
  2. Redis-py TLS Client (kết nối trực tiếp REDIS_URL tới Upstash)
  3. Fallback an toàn (Fail-Safe) trực tiếp tới DB khi Redis gặp sự cố mạng/offline
"""

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

from database import SessionLocal
from models import SystemSettings, SystemSettingAudit

# Khóa lưu cache cấu hình hệ thống trên Upstash Redis
CACHE_KEY = "socratic_system_settings_cache"

# TTL thời gian sống của cache: 300 giây (5 phút)
CACHE_TTL_SECONDS = 300

# Giá trị cấu hình mặc định (phục vụ khởi tạo khi DB chưa có row 'current')
DEFAULT_SYSTEM_SETTINGS: Dict[str, Any] = {
    "id": "current",
    "primary_model": "gemini-3.8-flash",
    "parent_insight_model": "gemini-3.5-flash",
    "classifier_model": "gemini-3.1-flash-lite",
    "email_model": "gemini-3.1-flash-lite",
    "flashcard_model": "gemini-3.5-flash-lite",
    "backup_model": "gemini-3.5-flash-lite",
    "temperature": 0.35,
    "top_p": 0.90,
    "max_output_tokens": 512,
    "socratic_strictness": "BALANCED",
    "enable_math_reviewer": True,
    "enable_vision_support": True,
    "safety_threshold": "BLOCK_MEDIUM_AND_ABOVE",
    "enable_parent_alert": True,
    "guest_rate_limit": 10,
    "student_rate_limit": 30,
    "mock_curriculum_month": None,
    "system_version": "v1.7.0",
    "environment": "Production (Neon + Vercel)",
    "last_updated_by": "admin@socratickid.edu.vn",
}

# Danh sách các trường được phép cập nhật từ giao diện Admin
ALLOWED_SETTING_FIELDS = {
    "primary_model",
    "parent_insight_model",
    "classifier_model",
    "email_model",
    "flashcard_model",
    "backup_model",
    "temperature",
    "top_p",
    "max_output_tokens",
    "socratic_strictness",
    "enable_math_reviewer",
    "enable_vision_support",
    "safety_threshold",
    "enable_parent_alert",
    "guest_rate_limit",
    "student_rate_limit",
    "mock_curriculum_month",
    "system_version",
    "environment",
}


# ==============================================================================
# HẠ TẦNG REDIS CACHE (Upstash REST / Redis-py / Fail-Safe)
# ==============================================================================

_sync_redis_client = None
_sync_redis_initialized = False


def _get_sync_redis():
    """
    Khởi tạo Redis client đồng bộ dùng chung để đọc/ghi cache nhanh.
    Hỗ trợ Upstash REST qua upstash_redis (nếu có) hoặc redis-py qua REDIS_URL.
    """
    global _sync_redis_client, _sync_redis_initialized
    if _sync_redis_initialized:
        return _sync_redis_client

    _sync_redis_initialized = True

    # 1. Thử Upstash REST client nếu thư viện upstash_redis khả dụng
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if rest_url and rest_token:
        try:
            import importlib
            upstash_redis = importlib.import_module("upstash_redis")
            _sync_redis_client = getattr(upstash_redis, "Redis")(url=rest_url, token=rest_token)
            return _sync_redis_client
        except (ImportError, Exception):
            pass

    # 2. Thử redis-py với REDIS_URL (kết nối rediss:// tới Upstash)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis
            _sync_redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            return _sync_redis_client
        except (ImportError, Exception):
            pass

    return None


def _read_from_cache() -> Optional[Dict[str, Any]]:
    """Đọc dữ liệu cấu hình từ Redis Cache. Trả về None nếu cache miss hoặc lỗi."""
    client = _get_sync_redis()
    if client is None:
        return None

    try:
        from middleware.telemetry_middleware import push_cache_event
    except Exception:
        push_cache_event = None  # type: ignore

    try:
        raw = client.get(CACHE_KEY)
        if raw:
            if push_cache_event is not None:
                push_cache_event(hit=True)
            if isinstance(raw, str):
                return json.loads(raw)
            elif isinstance(raw, dict):
                return raw
        if push_cache_event is not None:
            push_cache_event(hit=False)
    except Exception as err:
        # Lỗi mạng Redis -> ghi log nhẹ và fallback DB an toàn, không để crash hệ thống
        if push_cache_event is not None:
            push_cache_event(hit=False)
        print(f"[SystemConfigService] ⚠️ Lỗi đọc Redis Cache: {err} — Fallback sang DB.")
    return None


def _write_to_cache(data: Dict[str, Any]) -> None:
    """Ghi dữ liệu cấu hình vào Redis Cache với TTL = 300s."""
    client = _get_sync_redis()
    if client is None:
        return

    try:
        raw_json = json.dumps(data, ensure_ascii=False)
        client.set(CACHE_KEY, raw_json, ex=CACHE_TTL_SECONDS)
    except Exception as err:
        print(f"[SystemConfigService] ⚠️ Lỗi ghi Redis Cache: {err}")


def _invalidate_cache() -> None:
    """Xóa khóa cấu hình trên Redis Cache để kích hoạt Hot-Reloading tức thì."""
    client = _get_sync_redis()
    if client is None:
        return

    try:
        client.delete(CACHE_KEY)
    except Exception as err:
        print(f"[SystemConfigService] ⚠️ Lỗi xóa Redis Cache: {err}")


# ==============================================================================
# HÀM CHUYỂN ĐỔI ENTITY -> DICT
# ==============================================================================

def _model_to_dict(setting: SystemSettings) -> Dict[str, Any]:
    """Chuyển đổi ORM SystemSettings sang dict JSON-serializable an toàn."""
    val = getattr(setting, "last_updated_at", None)
    if isinstance(val, datetime):
        updated_at_str = val.isoformat()
    elif isinstance(val, str):
        updated_at_str = val
    else:
        updated_at_str = datetime.now(timezone.utc).isoformat()

    return {
        "id": setting.id,
        "primary_model": setting.primary_model,
        "parent_insight_model": setting.parent_insight_model,
        "classifier_model": setting.classifier_model,
        "email_model": setting.email_model,
        "flashcard_model": setting.flashcard_model,
        "backup_model": setting.backup_model,
        "temperature": float(setting.temperature) if setting.temperature is not None else 0.35,
        "top_p": float(setting.top_p) if setting.top_p is not None else 0.90,
        "max_output_tokens": int(setting.max_output_tokens) if setting.max_output_tokens is not None else 512,
        "socratic_strictness": setting.socratic_strictness,
        "enable_math_reviewer": bool(setting.enable_math_reviewer),
        "enable_vision_support": bool(setting.enable_vision_support),
        "safety_threshold": setting.safety_threshold,
        "enable_parent_alert": bool(setting.enable_parent_alert),
        "guest_rate_limit": int(setting.guest_rate_limit) if setting.guest_rate_limit is not None else 10,
        "student_rate_limit": int(setting.student_rate_limit) if setting.student_rate_limit is not None else 30,
        "mock_curriculum_month": setting.mock_curriculum_month,
        "system_version": setting.system_version,
        "environment": setting.environment,
        "last_updated_at": updated_at_str,
        "last_updated_by": setting.last_updated_by,
    }


# ==============================================================================
# NGHIỆP VỤ CHÍNH (Core Business Logic)
# ==============================================================================

def get_system_settings(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Lấy cấu hình hệ thống hiện hành:
      1. Đọc từ Redis Cache (thời gian phản hồi < 1ms).
      2. Nếu Cache Miss: Truy vấn Neon PostgreSQL (bảng system_settings id='current').
      3. Tự động nạp vào Redis Cache với TTL = 300s.
    """
    # 1. Thử đọc từ Cache
    cached = _read_from_cache()
    if cached is not None:
        return cached

    # 2. Cache Miss: Fallback đọc từ Neon DB
    close_db_after = False
    if db is None:
        db = SessionLocal()
        close_db_after = True

    try:
        setting = db.query(SystemSettings).filter_by(id="current").first()

        # Nếu chưa có row trong DB (DB mới tạo): Khởi tạo bản ghi Singleton 'current'
        if not setting:
            setting = SystemSettings(**DEFAULT_SYSTEM_SETTINGS)
            db.add(setting)
            db.commit()
            db.refresh(setting)

        data = _model_to_dict(setting)

        # 3. Ghi vào Redis Cache cho các request sau
        _write_to_cache(data)
        return data

    finally:
        if close_db_after:
            db.close()


def update_system_settings(
    new_data: Dict[str, Any],
    changed_by: str = "admin@socratickid.edu.vn",
    change_summary: str = "Cập nhật cấu hình hệ thống",
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Cập nhật cấu hình hệ thống:
      1. Ghi dữ liệu mới vào DB Neon (Singleton 'current').
      2. Lưu vết snapshot vào bảng system_setting_audits (Audit Trail).
      3. Xóa Redis Cache để kích hoạt Hot-Reloading tức thì cho học sinh.
    """
    close_db_after = False
    if db is None:
        db = SessionLocal()
        close_db_after = True

    try:
        setting = db.query(SystemSettings).filter_by(id="current").first()
        if not setting:
            setting = SystemSettings(**DEFAULT_SYSTEM_SETTINGS)
            db.add(setting)
            db.commit()
            db.refresh(setting)

        # Snapshot cấu hình trước khi sửa (Previous Config)
        previous_config = _model_to_dict(setting)

        # Cập nhật các trường hợp lệ (bỏ qua id, bảo mật không lưu api key)
        for key, value in new_data.items():
            if key in ALLOWED_SETTING_FIELDS and hasattr(setting, key):
                setattr(setting, key, value)

        setting.last_updated_by = changed_by
        setting.last_updated_at = datetime.now(timezone.utc)

        # Tạo bản ghi Audit Log phục vụ Rollback 1-Click
        new_config_snapshot = _model_to_dict(setting)
        # Bổ sung timestamp mới vào snapshot
        new_config_snapshot["last_updated_by"] = changed_by
        new_config_snapshot["last_updated_at"] = setting.last_updated_at.isoformat()

        audit = SystemSettingAudit(
            id=uuid.uuid4().hex,
            changed_by=changed_by,
            change_summary=change_summary,
            previous_config=previous_config,
            new_config=new_config_snapshot,
            created_at=datetime.now(timezone.utc),
        )
        db.add(audit)
        db.commit()
        db.refresh(setting)

        # Invalidate Cache để học sinh chat câu kế tiếp nhận ngay model mới
        _invalidate_cache()

        result_data = _model_to_dict(setting)
        # Nạp lại cache mới ngay lập tức
        _write_to_cache(result_data)
        return result_data

    finally:
        if close_db_after:
            db.close()


def rollback_system_settings(
    audit_id: str,
    changed_by: str = "admin@socratickid.edu.vn",
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Hoàn tác cấu hình 1-Click (Rollback - AC-SET-07):
    Tìm bản ghi audit theo audit_id và áp dụng previous_config trở lại DB.
    """
    close_db_after = False
    if db is None:
        db = SessionLocal()
        close_db_after = True

    try:
        audit = db.query(SystemSettingAudit).filter_by(id=audit_id).first()
        if not audit:
            raise ValueError(f"Không tìm thấy bản ghi Audit Log với ID: {audit_id}")

        restored_payload = audit.previous_config
        summary = f"Hoàn tác về phiên trước (Audit #{audit_id[:8]}): {audit.change_summary}"

        return update_system_settings(
            new_data=restored_payload,
            changed_by=changed_by,
            change_summary=summary,
            db=db,
        )

    finally:
        if close_db_after:
            db.close()


def get_setting_audits(limit: int = 10, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Truy vấn danh sách lịch sử thay đổi cấu hình gần nhất (sắp xếp mới nhất trước)."""
    close_db_after = False
    if db is None:
        db = SessionLocal()
        close_db_after = True

    try:
        audits = (
            db.query(SystemSettingAudit)
            .order_by(SystemSettingAudit.created_at.desc())
            .limit(limit)
            .all()
        )

        results = []
        for a in audits:
            created_str = (
                a.created_at.isoformat()
                if isinstance(a.created_at, datetime)
                else str(a.created_at or "")
            )
            results.append({
                "id": a.id,
                "changed_by": a.changed_by,
                "change_summary": a.change_summary,
                "previous_config": a.previous_config,
                "new_config": a.new_config,
                "created_at": created_str,
            })
        return results

    finally:
        if close_db_after:
            db.close()


def invalidate_system_settings_cache() -> None:
    """Hàm công khai xóa Redis Cache khi cần ép buộc làm mới từ bên ngoài."""
    _invalidate_cache()


# ==============================================================================
# CLASS WRAPPER (Facade Pattern)
# ==============================================================================

class SystemConfigService:
    """Class đại diện dịch vụ quản trị cấu hình hệ thống (Facade)."""

    get_settings = staticmethod(get_system_settings)
    update_settings = staticmethod(update_system_settings)
    rollback = staticmethod(rollback_system_settings)
    get_audits = staticmethod(get_setting_audits)
    invalidate_cache = staticmethod(invalidate_system_settings_cache)
