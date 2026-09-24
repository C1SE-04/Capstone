import os
import json
import google.generativeai as genai

# ==========================================
# HÀM ĐIỀU PHỐI CHÍNH (Router Function) - CÓ STREAMING
# ==========================================
def agent_router(target_agent: str, task_description: str, history_text: str, user_query: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        yield "Lỗi: Chưa cấu hình GEMINI_API_KEY"
        return
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.5-flash-lite")
    
    prompt = f"""
Bạn là một gia sư AI đóng vai trò: {target_agent}.
Nhiệm vụ của bạn: {task_description}

--- LỊCH SỬ TRÒ CHUYỆN ---
{history_text}

--- HỌC SINH ---
{user_query}

Hãy trả lời học sinh. Trả lời trực tiếp, thân thiện, súc tích (dưới 3 câu nếu có thể).
"""
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f" [Lỗi khi gọi AI: {str(e)}]"
