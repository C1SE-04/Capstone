import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import google.generativeai as genai
from sqlalchemy.orm import Session

import models
import schemas
import agents.orchestrator as orchestrator
import orchestrator_bridge
from database import get_db
from rate_limit import check_guest_rate_limit

router = APIRouter(tags=["Chat & AI"])

from fastapi.responses import StreamingResponse

@router.post("/chat/orchestrator")
def chat_with_orchestrator(
    request: schemas.GeminiRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
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
    # -------------------------------------------
    


    effective_grade = request.grade_level
    if not (request.session_id and request.session_id.startswith("guest-")):
        if existing_session and existing_session.user_id and existing_session.user_id != "guest-user-id":
            user_in_db = db.query(models.User).filter(models.User.id == existing_session.user_id).first()
            if user_in_db and user_in_db.grade is not None:
                effective_grade = user_in_db.grade

    return StreamingResponse(
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
        media_type="text/event-stream"
    )

@router.post("/gemini/generate")
def generate_gemini(request: schemas.GeminiRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")
    
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        response = model.generate_content(request.prompt)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gemini/models")
def list_available_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured")
    
    genai.configure(api_key=api_key)
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

