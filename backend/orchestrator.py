import os
import json
import time
import google.generativeai as genai
from router import agent_router
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import models

from chat_utils import get_recent_chat_context

def save_orchestrator_log(db: Session, user_query: str, target_agent: str, reason: str):
    try:
        new_log = models.OrchestratorLog(
            user_query=user_query,
            target_agent=target_agent,
            reason=reason
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving orchestrator log: {e}")

def process_query_with_orchestrator(user_query: str, session_id: str, db: Session, background_tasks: BackgroundTasks):
    """
    Gọi Gemini API với prompt phân loại (Slow-Path), 
    nhận JSON trả về và đưa cho router phân luồng.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API Key not configured")
        
    genai.configure(api_key=api_key)

    # 1. Lưu tin nhắn của học sinh vào Database
    user_msg = models.Message(session_id=session_id, sender_type="USER", content=user_query)
    db.add(user_msg)
    db.commit()

    # 2. Lấy 5 tin nhắn ngữ cảnh (bao gồm cả tin nhắn vừa lưu)
    chat_history = get_recent_chat_context(db, session_id, limit=5)
    
    # Format lịch sử thành chuỗi văn bản cho AI dễ đọc
    history_text = "\n".join([f"[{msg['role'].upper()}]: {msg['parts'][0]}" for msg in chat_history])

    # 3. Tích hợp prompt - Phân loại câu hỏi (Orchestrator)
    system_prompt = f"""
Bạn là một AI Điều phối (Orchestrator) trong một hệ thống Chatbot học tập theo phương pháp Socratic (dẫn dắt học sinh tư duy, không đưa đáp án trực tiếp).
Nhiệm vụ của bạn là đọc toàn bộ Lịch sử đoạn chat dưới đây, đặc biệt chú ý vào [Tin nhắn mới nhất của học sinh], để quyết định xem Agent nào phù hợp nhất để xử lý tiếp theo:

- "SAFETY_AGENT": Chọn nếu tin nhắn chứa ngôn từ độc hại, bạo lực, vi phạm tiêu chuẩn cộng đồng hoặc không phù hợp với lứa tuổi học sinh.
- "KNOWLEDGE_TRACING_AGENT": Chọn nếu học sinh mới bắt đầu học một chủ đề hoặc cần được hệ thống đánh giá/kiểm tra lại nền tảng kiến thức hiện tại.
- "MISCONCEPTION_AGENT": Chọn nếu học sinh đưa ra một câu trả lời sai, thể hiện sự hiểu lầm (logic sai, khái niệm sai).
- "SCAFFOLDING_AGENT": Chọn nếu học sinh đang bế tắc, yêu cầu gợi ý hoặc cần được dẫn dắt từng bước để tự tìm ra câu trả lời (mà không đưa ra đáp án trực tiếp).
- "UNKNOWN_AGENT": Chọn nếu không rơi vào các trường hợp trên.

--- LỊCH SỬ CHAT GẦN ĐÂY ---
{history_text}
----------------------------

Hãy trả về kết quả dưới định dạng JSON đúng chuẩn sau:
{{
    "target_agent": "SAFETY_AGENT" | "KNOWLEDGE_TRACING_AGENT" | "MISCONCEPTION_AGENT" | "SCAFFOLDING_AGENT" | "UNKNOWN_AGENT",
    "reason": "Giải thích ngắn gọn tại sao lại chọn Agent này dựa trên ngữ cảnh đoạn chat"
}}
"""

    max_retries = 3
    retry_delay = 1
    response = None

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-3.5-flash-lite')
            # trả về JSON
            response = model.generate_content(
                system_prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            break
        except Exception as e:
            error_msg = str(e).lower()
            is_rate_limit = any(keyword in error_msg for keyword in ["429", "rate limit", "quota", "resource exhausted"])
            
            if attempt == max_retries - 1:
                if is_rate_limit:
                    raise HTTPException(status_code=429, detail="Gemini API rate limit exceeded. Please try again later.")
                raise HTTPException(status_code=500, detail=f"Lỗi Orchestrator Service: {str(e)}")
            
            time.sleep(retry_delay * (2 ** attempt))

    try:
        # Lấy kết quả chuỗi JSON thô từ AI Điều phối
        raw_json_str = response.text.strip()
        
        # Làm sạch JSON nếu có markdown formatting
        if raw_json_str.startswith("```json"):
            raw_json_str = raw_json_str[7:]
        elif raw_json_str.startswith("```"):
            raw_json_str = raw_json_str[3:]
        if raw_json_str.endswith("```"):
            raw_json_str = raw_json_str[:-3]
        raw_json_str = raw_json_str.strip()
        
        # Parse JSON để lấy thông tin log
        decision = json.loads(raw_json_str)
        target_agent = decision.get("target_agent", "UNKNOWN_AGENT")
        reason = decision.get("reason", "")
        
        # Thêm task lưu log chạy ngầm (Bất đồng bộ)
        background_tasks.add_task(save_orchestrator_log, db, user_query, target_agent, reason)

        # Đưa JSON qua cho Router xử lý phân luồng
        final_result = agent_router(raw_json_str, user_query)
        
        # 4. Lưu tin nhắn trả lời của AI vào Database
        ai_reply_content = final_result.get("reply", "")
        if ai_reply_content:
            ai_msg = models.Message(session_id=session_id, sender_type="AGENT_TUTOR", content=ai_reply_content)
            db.add(ai_msg)
            db.commit()

        # Gom cả quyết định của Orchestrator và câu trả lời của Agent để trả về
        return {
            "orchestrator_decision": decision,
            "agent_response": final_result,
            "debug_context": history_text
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gemini không trả về chuẩn JSON")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Orchestrator Service: {str(e)}")
