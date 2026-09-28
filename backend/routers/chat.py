import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import google.generativeai as genai
from sqlalchemy.orm import Session

import schemas
import agents.orchestrator as orchestrator
import orchestrator_bridge
from database import get_db

router = APIRouter(tags=["Chat & AI"])

from fastapi.responses import StreamingResponse

@router.post("/chat/orchestrator")
def chat_with_orchestrator(
    request: schemas.GeminiRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
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
                title="Chế độ dùng thử (Mới)"
            )
            db.add(guest_session)
            db.commit()
    else:
        # Với session thật: kiểm tra session_id có tồn tại trong DB không
        # Nếu không tồn tại (ví dụ FE dùng ID local chưa tạo qua /sessions), báo 404
        import models as _models
        existing_session = db.query(_models.Session).filter(
            _models.Session.id == request.session_id
        ).first()
        if not existing_session:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{request.session_id}' không tồn tại. Hãy tạo session qua POST /sessions trước."
            )
    # -------------------------------------------

    return StreamingResponse(
        orchestrator_bridge.process_query_with_orchestrator(
            user_query=request.prompt, 
            session_id=request.session_id, 
            db=db, 
            background_tasks=background_tasks,
            problem_context=request.problem_context,
            answer_status=request.answer_status,  # Đưa trạng thái đúng/sai của học sinh vào
        ),
        media_type="text/event-stream"
    )


@router.post("/chat/comprehension")
def comprehension_response(
    request: schemas.ComprehensionRequest,
    db: Session = Depends(get_db)
):
    """
    Xử lý khi học sinh bấm nút 'Đã hiểu' hoặc 'Chưa hiểu'.
    - understood=True  → ghi nhận, kết thúc.
    - understood=False → tăng bộ đếm not_understood_count, AI giải thích lại (stream).
    """
    import models as _models
    existing = db.query(_models.Session).filter(_models.Session.id == request.session_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Session '{request.session_id}' không tồn tại.")

    return StreamingResponse(
        orchestrator_bridge.process_comprehension_response(
            session_id=request.session_id,
            understood=request.understood,
            db=db,
        ),
        media_type="text/event-stream"
    )


@router.get("/chat/stats/{session_id}", response_model=schemas.SessionStatsResponse)
def get_session_stats(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Lấy bộ đếm học tập hiện tại của 1 session."""
    stats = orchestrator_bridge.get_or_create_session_stats(db, session_id)
    return schemas.SessionStatsResponse(
        session_id=session_id,
        consecutive_wrong_count=stats.consecutive_wrong_count,
        hint_count=stats.hint_count,
        not_understood_count=stats.not_understood_count,
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
