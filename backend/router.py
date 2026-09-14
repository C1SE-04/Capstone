import json

# ==========================================
# 1. CÁC HÀM MOCK AGENT (Dữ liệu giả)
# ==========================================
def mock_agent_hoc_vu(user_query: str):
    print(f"[Agent Học Vụ] Đang xử lý: {user_query}")
    return {"agent_name": "Học Vụ", "reply": "Đây là câu trả lời giả lập từ Agent Học Vụ."}

def mock_agent_thong_tin(user_query: str):
    print(f"[Agent Thông Tin] Đang xử lý: {user_query}")
    return {"agent_name": "Thông Tin", "reply": "Đây là câu trả lời giả lập từ Agent Thông Tin."}

def mock_agent_unknown(user_query: str):
    return {"agent_name": "Unknown", "reply": "Xin lỗi, tôi không biết phải chuyển câu hỏi này cho ai."}

# ==========================================
# 2. HÀM ĐIỀU PHỐI CHÍNH (Router Function)
# ==========================================
def agent_router(json_response_tu_gemini: str, user_query: str):
    try:
        # Parse JSON từ Gemini trả về (đã làm ở Task 38)
        data = json.loads(json_response_tu_gemini)
        
        # Giả sử Gemini trả về JSON có field "target_agent" 
        # (VD: "HOC_VU", "THONG_TIN", "KHAC")
        target_agent = data.get("target_agent", "KHAC")
        
        # 3. ĐIỀU HƯỚNG BẰNG MATCH...CASE
        match target_agent:
            case "HOC_VU":
                return mock_agent_hoc_vu(user_query)
            case "THONG_TIN":
                return mock_agent_thong_tin(user_query)
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
