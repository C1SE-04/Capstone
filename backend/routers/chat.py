import os
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import google.generativeai as genai
from sqlalchemy.orm import Session

import schemas, orchestrator
from database import get_db

router = APIRouter(tags=["Chat & AI"])

@router.post("/chat/orchestrator")
def chat_with_orchestrator(
    request: schemas.GeminiRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    return orchestrator.process_query_with_orchestrator(
        user_query=request.prompt, 
        session_id=request.session_id, 
        db=db, 
        background_tasks=background_tasks
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
