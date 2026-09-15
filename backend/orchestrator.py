import os
import json
import google.generativeai as genai
from router import agent_router
from fastapi import HTTPException

def process_query_with_orchestrator(user_query: str):
    """
    Gọi Gemini API với prompt phân loại (Slow-Path), 
    nhận JSON trả về và đưa cho router phân luồng.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API Key not configured")
        
    genai.configure(api_key=api_key)

    # Tích hợp prompt - Phân loại câu hỏi
    system_prompt = f"""
Bạn là một AI Điều phối (Orchestrator). Nhiệm vụ của bạn là đọc câu hỏi của người dùng và xác định xem bộ phận nào cần giải quyết.
- Nếu câu hỏi liên quan đến lịch học, điểm số, học phí -> Chọn "HOC_VU".
- Nếu câu hỏi liên quan đến cơ sở vật chất, địa chỉ, thông tin chung -> Chọn "THONG_TIN".
- Nếu không thuộc 2 loại trên -> Chọn "KHAC".

Câu hỏi của người dùng: "{user_query}"

Hãy trả về kết quả dưới định dạng JSON đúng chuẩn sau:
{{
    "target_agent": "HOC_VU" | "THONG_TIN" | "KHAC",
    "reason": "Giải thích ngắn gọn lý do phân loại"
}}
"""

    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite')
        # trả về JSON
        response = model.generate_content(
            system_prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        # Lấy kết quả chuỗi JSON thô từ AI Điều phối
        raw_json_str = response.text
        
        # Đưa JSON qua cho Router xử lý phân luồng
        final_result = agent_router(raw_json_str, user_query)
        
        # Gom cả quyết định của Orchestrator và câu trả lời của Agent để trả về
        return {
            "orchestrator_decision": json.loads(raw_json_str),
            "agent_response": final_result
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gemini không trả về chuẩn JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi Orchestrator Service: {str(e)}")
