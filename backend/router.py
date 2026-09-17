import json

# ==========================================
# 1. CÁC HÀM MOCK AGENT (Dữ liệu giả)
# ==========================================
def mock_agent_safety(user_query: str):
    print(f"[Safety Agent] Đang xử lý: {user_query}")
    return {"agent_name": "Safety Agent", "reply": "Nội dung đã được kiểm duyệt an toàn."}

def mock_agent_knowledge_tracing(user_query: str):
    print(f"[Knowledge Tracing Agent] Đang xử lý: {user_query}")
    return {"agent_name": "Knowledge Tracing Agent", "reply": "Đang đánh giá nền tảng kiến thức của học sinh..."}

def mock_agent_misconception(user_query: str):
    print(f"[Misconception Agent] Đang xử lý: {user_query}")
    return {"agent_name": "Misconception Agent", "reply": "Phát hiện lỗi logic trong câu trả lời của học sinh."}

def mock_agent_scaffolding(user_query: str):
    print(f"[Scaffolding Agent] Đang xử lý: {user_query}")
    return {"agent_name": "Scaffolding Agent", "reply": "Đang phân tích để đưa ra gợi ý phù hợp (không đưa đáp án)."}

def mock_agent_unknown(user_query: str):
    return {"agent_name": "Unknown Agent", "reply": "Không rõ người dùng đang cần gì, trả về mặc định."}

# ==========================================
# 2. HÀM ĐIỀU PHỐI CHÍNH (Router Function)
# ==========================================
def agent_router(json_response_tu_gemini: str, user_query: str):
    try:
        data = json.loads(json_response_tu_gemini)
        target_agent = data.get("target_agent", "UNKNOWN_AGENT")
        
        # 3. ĐIỀU HƯỚNG BẰNG MATCH...CASE
        match target_agent:
            case "SAFETY_AGENT":
                return mock_agent_safety(user_query)
            case "KNOWLEDGE_TRACING_AGENT":
                return mock_agent_knowledge_tracing(user_query)
            case "MISCONCEPTION_AGENT":
                return mock_agent_misconception(user_query)
            case "SCAFFOLDING_AGENT":
                return mock_agent_scaffolding(user_query)
            case _:
                return mock_agent_unknown(user_query)
                
    except json.JSONDecodeError:
        return {"error": "Lỗi phân tích JSON từ Gemini"}


if __name__ == "__main__":
    # Giả lập 1: Gemini phân tích câu hỏi thuộc về Học vụ, trả về JSON này
    fake_gemini_json_1 = '{"target_agent": "HOC_VU"}'
    cau_hoi_1 = "Cho mình hỏi học phí kỳ này đóng bao nhiêu?"
    
    print(f"User: {cau_hoi_1}")
    ket_qua_1 = agent_router(fake_gemini_json_1, cau_hoi_1)
    print(f"Kết quả Router: {ket_qua_1}\n")

    # Giả lập 2: Gemini phân tích câu hỏi thuộc về Thông tin
    fake_gemini_json_2 = '{"target_agent": "THONG_TIN"}'
    cau_hoi_2 = "Trường mình có mấy cơ sở vậy?"
    
    print(f"User: {cau_hoi_2}")
    ket_qua_2 = agent_router(fake_gemini_json_2, cau_hoi_2)
    print(f"Kết quả Router: {ket_qua_2}\n")
