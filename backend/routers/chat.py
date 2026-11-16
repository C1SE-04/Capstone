import os
import time
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import google.generativeai as genai
from sqlalchemy.orm import Session
import redis.asyncio as aioredis
from redis_client import get_redis

import models
import schemas
import agents.orchestrator as orchestrator
import orchestrator_bridge
from database import get_db
from rate_limit import check_guest_rate_limit
from services.rate_limiter_service import RateLimiterService
import services.system_config_service as system_config_service

router = APIRouter(tags=["Chat & AI"])

from fastapi.responses import StreamingResponse
from middleware.telemetry_middleware import increment_sse_session, decrement_sse_session
from middleware.gemini_telemetry import generate_with_telemetry


def _tracked_sse_stream(generator, session_id: str | None = None):
    """
    Bọc StreamingResponse generator:
      1. Đo chính xác số phiên SSE active qua TelemetryMiddleware.
      2. Ghi nhận mốc kết thúc stream (Stream DONE) để kích hoạt Socratic Cool-Down 5s cho câu kế tiếp.
    """
    increment_sse_session()
    try:
        for chunk in generator:
            yield chunk
    finally:
        decrement_sse_session()
        if session_id:
            try:
                # Ghi nhận mốc AI kết thúc câu trả lời vào Redis / Memory
                RateLimiterService.record_ai_completion_sync(session_id)
            except Exception:
                pass


@router.post("/chat/orchestrator")
async def chat_with_orchestrator(
    request: schemas.GeminiRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    _: None = Depends(check_guest_rate_limit),  # Task: Rate-limit 10 câu/24h cho Guest
):
    existing_session = None
    # --- AUTO-CREATE GUEST SESSION IF NEEDED ---
    if request.session_id and request.session_id.startswith("guest-"):
        guest_user = db.query(models.User).filter(models.User.id == "guest-user-id").first()
        if not guest_user:
            guest_user = models.User(
                id="guest-user-id", 
                email="guest@socratickid.local", 
                hashed_password="guest", 
                role="GUEST"
            )
            db.add(guest_user)
            db.commit()
            
        guest_session = db.query(models.Session).filter(models.Session.id == request.session_id).first()
        if not guest_session:
            guest_session = models.Session(
                id=request.session_id, 
                user_id="guest-user-id", 
                title="Chế độ dùng thử (Mới)"
            )
            db.add(guest_session)
            db.commit()
    else:
        # Với session thật: kiểm tra session_id có tồn tại trong DB không
        # Nếu không tồn tại (ví dụ FE dùng ID local chưa tạo qua /sessions), tự tạo hoặc báo lỗi
        existing_session = db.query(models.Session).filter(
            models.Session.id == request.session_id
        ).first()
        if not existing_session:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{request.session_id}' không tồn tại. Hãy tạo session qua POST /sessions trước."
            )

        student_user_id = existing_session.user_id or "anonymous-student"

        # ── 1. TASK #359 (T11.1.2): SOCRATIC COOL-DOWN (Tối thiểu 5s từ khi AI trả lời xong) ──
        is_cool, retry_after, delta_t = await RateLimiterService.check_socratic_cooldown(
            redis_client=redis,
            session_id=request.session_id,
            cooldown_seconds=5.0,
        )
        if not is_cool:
            raise RateLimiterService.create_429_exception(
                reason="SOCRATIC_COOL_DOWN",
                message=(
                    "Thầy Socratic nhận thấy em đang gửi câu hỏi rất nhanh. "
                    "Hãy dành ít nhất 5 giây để quan sát hình vẽ và đọc kỹ gợi ý của thầy trước khi hỏi tiếp nhé!"
                ),
                limit=1,
                remaining=0,
                retry_after=retry_after,
                reset_at=int(time.time() + retry_after),
            )

        # ── 2. TASK #358 (T11.1.1): DYNAMIC STUDENT RATE LIMIT THEO ADMIN SETTINGS ──
        sys_settings = system_config_service.get_system_settings(db)
        student_limit = int(sys_settings.get("student_rate_limit", 30))

        is_allowed, info = await RateLimiterService.check_sliding_window(
            redis_client=redis,
            key=f"ratelimit:student:{student_user_id}:chat",
            limit=student_limit,
            window_seconds=60,
        )
        if not is_allowed:
            raise RateLimiterService.create_429_exception(
                reason="STUDENT_LIMIT",
                message=(
                    f"Em đang gửi câu hỏi quá nhanh (vượt quá giới hạn {student_limit} câu/phút). "
                    f"Vui lòng đợi {info['retry_after']} giây trước khi gửi câu tiếp theo nhé!"
                ),
                limit=student_limit,
                remaining=0,
                retry_after=info["retry_after"],
                reset_at=info["reset_at"],
            )

        # ── 3. BẢO VỆ QUOTA TOÀN HỆ THỐNG (GLOBAL GEMINI LIMIT) ──
        global_rpm_limit = int(sys_settings.get("global_gemini_rpm_limit", os.getenv("GLOBAL_GEMINI_RPM_LIMIT", "60")))
        is_global_ok, g_info = await RateLimiterService.check_sliding_window(
            redis_client=redis,
            key="ratelimit:global:gemini_chat",
            limit=global_rpm_limit,
            window_seconds=60,
        )
        if not is_global_ok:
            raise RateLimiterService.create_429_exception(
                reason="GLOBAL_SYSTEM_LIMIT",
                message=(
                    "Hệ thống gia sư AI đang có nhiều bạn cùng đặt câu hỏi. "
                    f"Thầy Socratic đang xử lý, em vui lòng đợi khoảng {g_info['retry_after']} giây nhé!"
                ),
                limit=global_rpm_limit,
                remaining=0,
                retry_after=g_info["retry_after"],
                reset_at=g_info["reset_at"],
            )
    # -------------------------------------------
    


    effective_grade = request.grade_level
    if not (request.session_id and request.session_id.startswith("guest-")):
        if existing_session and existing_session.user_id and existing_session.user_id != "guest-user-id":
            user_in_db = db.query(models.User).filter(models.User.id == existing_session.user_id).first()
            if user_in_db and user_in_db.grade is not None:
                effective_grade = user_in_db.grade

    return StreamingResponse(
        _tracked_sse_stream(
            orchestrator_bridge.process_query_with_orchestrator(
                user_query=request.prompt, 
                session_id=request.session_id, 
                db=db, 
                background_tasks=background_tasks,
                problem_context=request.problem_context,
                answer_status=request.answer_status,
                grade_level=effective_grade,  # US 6.2: lấy lớp học chuẩn xác từ DB
                attachment_url=request.attachment_url, # US 6.4: Truyền link ảnh Cloudinary từ request
            ),
            session_id=request.session_id,
        ),
        media_type="text/event-stream"
    )

@router.post("/gemini/generate")
def generate_gemini(request: schemas.GeminiRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")
    
    genai.configure(api_key=api_key, transport="rest")
    try:
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        response = generate_with_telemetry(model, request.prompt, "gemini-3.5-flash-lite", "Chat")
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gemini/models")
def list_available_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")
    
    genai.configure(api_key=api_key, transport="rest")
    try:
        models = [
            m.name for m in genai.list_models() 
            if "generateContent" in m.supported_generation_methods
        ]
        return {"supported_models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/comprehension")
def submit_comprehension_feedback(
    req: schemas.ComprehensionRequest,
    db: Session = Depends(get_db)
):
    import models as _models
    stats = db.query(_models.SessionStats).filter(
        _models.SessionStats.session_id == req.session_id
    ).first()
    
    if not stats:
        # Nếu chưa có thì tạo mới
        stats = _models.SessionStats(session_id=req.session_id)
        db.add(stats)
        
    independence_data = None
    deduplication_data = None
    if req.understood:
        # Task #160 & US 8.1 (T8.2): Tính điểm tự lực, kiểm tra hash đề bài & chặn cộng dồn bài lặp
        from routers.independence import save_independence_score
        record = save_independence_score(db=db, session_id=req.session_id)
        independence_data = {
            "id": record.id,
            "score": record.score,
            "hints_used": record.hints_used,
            "not_understood_count": record.not_understood_count,
            "evaluation": record.evaluation,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "is_duplicate": record.is_duplicate,
            "category": record.category,
            "friendly_parent_title": record.friendly_parent_title,
            # US 9.2: Metadata cảnh báo và điểm trần cho bài giải trùng
            "repeat_count": getattr(record, "repeat_count", 1),
            "max_score": getattr(record, "max_score", 100),
            "repeat_warning": getattr(record, "repeat_warning", None),
        }
        deduplication_data = {
            "category": record.category,
            "is_duplicate": record.is_duplicate,
            "gentle_reminder": record.gentle_reminder
        }
        stats.consecutive_wrong_count = 0
        stats.hint_count = 0
    else:
        stats.not_understood_count += 1
        
    db.commit()
    db.refresh(stats)
    
    return {
        "status": "success",
        "message": "Feedback recorded",
        "independence": independence_data,
        "deduplication": deduplication_data,
        "stats": {
            "consecutive_wrong_count": stats.consecutive_wrong_count,
            "hint_count": stats.hint_count,
            "not_understood_count": stats.not_understood_count
        }
    }


@router.get("/chat/stats/{session_id}", response_model=schemas.SessionStatsResponse)
def get_session_stats(session_id: str, db: Session = Depends(get_db)):
    import models as _models
    stats = db.query(_models.SessionStats).filter(
        _models.SessionStats.session_id == session_id
    ).first()
    
    if not stats:
        return schemas.SessionStatsResponse(
            session_id=session_id,
            consecutive_wrong_count=0,
            hint_count=0,
            not_understood_count=0
        )
        
    return stats

