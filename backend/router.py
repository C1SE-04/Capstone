import os
import json
import google.generativeai as genai
from agents.reviewer import LocalReviewerAgent
from agents.agent_prompts import _get_grade_context

# ==========================================
# CHỈ DẪN HỆ THỐNG CHO VAI TRÒ NGƯỜI THẦY
# ==========================================
TEACHER_SYSTEM_INSTRUCTION = """
Bạn là một người THẦY GIÁO (gia sư Socratic AI) giảng dạy học sinh tại Việt Nam.

TÁC PHONG VÀ NGUYÊN TẮC SƯ PHẠM BẮT BUỘC:
1. XƯNG HÔ:
   - LUÔN LUÔN xưng "thầy" và gọi học sinh là "em".
   - TUYỆT ĐỐI KHÔNG BAO GIỜ xưng "Dạ", "vâng ạ", "dạ thưa". Bạn là THẦY GIÁO.

2. KHI NÀO ĐƯỢC NHẮC NHỞ THÁI ĐỘ — CHỈ KHI HỌC SINH:
   ✅ Dùng từ xúc phạm trực tiếp: "mày", "tao", chửi thề (đm, vcl, ...), gọi thầy là "bot ngu", "ông già", v.v.
   ✅ Hú hét vô nghĩa không liên quan bài học: "hú hú", "ê ê ê", gào thét.
   → Khi đó: Nghiêm túc nhắc nhở MỘT LẦN, ngắn gọn, rồi tiếp tục hướng dẫn bài học.

3. TUYỆT ĐỐI KHÔNG NHẮC NHỞ THÁI ĐỘ KHI HỌC SINH:
   ❌ Gửi bài toán ngắn không có lời chào: "1+1 = bao nhiêu", "21+21=?", "= bao nhiêu", "bao nhiêu", "vậy = mấy"
   ❌ Trả lời ngắn gọn không có chủ ngữ: "42", "là 10", "bằng 3/4", "quy đồng", "dạ", "vâng"
   ❌ Dùng từ thông thường nghe có vẻ ngắn/trống: "=", "la bao nhieu", "là bao nhiêu"
   → NHỮNG CÁCH HỎI VÀ TRẢ LỜI NÀY LÀ HOÀN TOÀN BÌNH THƯỜNG. Thầy chỉ cần trả lời nội dung.

4. PHƯƠNG PHÁP SOCRATIC:
   - Khi hướng dẫn học tập, không giải hộ hay đưa đáp án ngay. Hãy đặt câu hỏi gợi mở từng bước nhỏ để học sinh tự suy nghĩ.

5. ĐỘ DÀI:
   - Ngắn gọn, chuẩn mực, từ 2 đến 4 câu.
"""

# ==========================================
# HÀM ĐIỀU PHỐI CHÍNH (Router Function) - CÓ TÍCH HỢP REVIEWER TỰ ĐỘNG SỬA LỖI
# ==========================================
def agent_router(target_agent: str, task_description: str, history_text: str, user_query: str, expected_answer: str = "", grade_level: int = None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        yield "Lỗi: Chưa cấu hình GEMINI_API_KEY"
        return
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        system_instruction=TEACHER_SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            top_p=0.9,
            max_output_tokens=1024,
        )
    )
    grade_context = _get_grade_context(grade_level)
    base_prompt = f"""
    {grade_context}
Vai trò chuyên môn hiện tại: {target_agent}.
Chỉ đạo sư phạm từ Orchestrator: {task_description}

--- LỊCH SỬ TRÒ CHUYỆN ---
{history_text}

--- HỌC SINH VỪA NÓI ---
{user_query}

NHẮC LẠI NGUYÊN TẮC:
- Bạn là THẦY GIÁO, xưng "thầy" gọi "em", TUYỆT ĐỐI KHÔNG xưng "Dạ".
- Chỉ nhắc nhở thái độ khi học sinh dùng từ XÚC PHẠM THỰC SỰ (mày, tao, chửi thề) — câu ngắn, không chào hỏi, không có chủ ngữ là BÌNH THƯỜNG, không nhắc.
- Trả lời ngắn gọn, chuẩn mực (2-4 câu).
"""
    
    reviewer = LocalReviewerAgent()
    max_retries = 2
    current_attempt = 0
    final_text = ""
    prompt = base_prompt

    while current_attempt <= max_retries:
        print("=== PROMPT CHUẨN BỊ GỬI AI ===")
        print(prompt)
        print("================================")
        
        try:
            # Lấy toàn bộ văn bản để Reviewer có thể đánh giá (không stream trực tiếp)
            response = model.generate_content(prompt, stream=False)
            generated_text = response.text
            
            # Chỉ kiểm duyệt gắt gao nếu đang đóng vai SCAFFOLDING_AGENT
            if target_agent == "SCAFFOLDING_AGENT":
                review_result = reviewer.review(user_query, expected_answer, generated_text)
                if not review_result["is_approved"]:
                    current_attempt += 1
                    print(f"[Reviewer Agent 🛑] Từ chối (Lần {current_attempt}/{max_retries}): {review_result['feedback']}")
                    print(f"[Reviewer Agent 🛑] Lý do: {review_result['reasoning']}")
                    
                    # Nạp lại lời mắng vào prompt để ép AI phải sửa lỗi
                    prompt += f"\n\n[HỆ THỐNG KIỂM DUYỆT CẢNH BÁO]: Câu trả lời vừa rồi của bạn bị TỪ CHỐI vì lý do: {review_result['feedback']}. \nHãy sinh lại câu trả lời khác và TUYỆT ĐỐI KHÔNG vi phạm lỗi này nữa."
                    final_text = generated_text  # Backup lỡ như hết số lần thử vẫn ngu
                    continue
            
            # Nếu pass qua được Reviewer hoặc không phải Scaffolding thì chốt đáp án
            final_text = generated_text
            break
            
        except Exception as e:
            yield f" [Lỗi khi gọi AI: {str(e)}]"
            return

    # Sau khi chốt được văn bản xịn, chẻ nhỏ ra để giả lập luồng Stream trả về Frontend cho mượt
    words = final_text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
