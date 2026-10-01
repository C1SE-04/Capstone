import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import google.generativeai as genai
from sqlalchemy.orm import Session

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
    # --- AUTO-CREATE GUEST SESSION IF NEEDED ---
    if request.session_id and request.session_id.startswith("guest-"):
        import models
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
                title="Cháº¿ Ä‘á»™ dÃ¹ng thá»­ (Má»›i)"
            )
            db.add(guest_session)
            db.commit()
    else:
        # Vá»›i session tháº­t: kiá»ƒm tra session_id cÃ³ tá»“n táº¡i trong DB khÃ´ng
        # Náº¿u khÃ´ng tá»“n táº¡i (vÃ­ dá»¥ FE dÃ¹ng ID local chÆ°a táº¡o qua /sessions), bÃ¡o 404
        import models as _models
        existing_session = db.query(_models.Session).filter(
            _models.Session.id == request.session_id
        ).first()
        if not existing_session:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{request.session_id}' khÃ´ng tá»“n táº¡i. HÃ£y táº¡o session qua POST /sessions trÆ°á»›c."
            )
    # -------------------------------------------
    


    return StreamingResponse(
        orchestrator_bridge.process_query_with_orchestrator(
            user_query=request.prompt, 
            session_id=request.session_id, 
            db=db, 
            background_tasks=background_tasks,
            problem_context=request.problem_context,
            answer_status=request.answer_status,
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
        # Náº¿u chÆ°a cÃ³ thÃ¬ táº¡o má»›i
        stats = _models.SessionStats(session_id=req.session_id)
        db.add(stats)
        
    if req.understood:
        stats.consecutive_wrong_count = 0
        stats.hint_count = 0
    else:
        stats.not_understood_count += 1
        
    db.commit()
    db.refresh(stats)
    
    return {
        "status": "success",
        "message": "Feedback recorded",
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

