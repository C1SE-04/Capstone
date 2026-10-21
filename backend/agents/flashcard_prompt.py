from typing import List, Dict, Any, Optional
import os
import json
import google.generativeai as genai
from schemas import FlashcardContent

# ========================================================
# 1. SYSTEM INSTRUCTION SƯ PHẠM CHO FLASHCARD EXTRACTION
# ========================================================
FLASHCARD_EXTRACTION_SYSTEM_INSTRUCTION = """
Bạn là một Chuyên gia Biên soạn Học liệu Toán học Sư phạm Tiểu học & THCS của hệ thống SocraticKid.
Nhiệm vụ của bạn là: Đọc đoạn đối thoại giải toán giữa Học sinh và Gia sư AI, sau đó đúc kết bài toán thành MỘT THẺ FLASHCARD ÔN TẬP THÔNG MINH.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC QUY TẮC SAU:
1. ĐỀ BÀI TOÁN (problem_statement):
   - Viết lại đề bài một cách hoàn chỉnh, mạch lạc, dễ hiểu.
   - Chuẩn hóa toàn bộ số liệu và công thức toán học bằng định dạng LaTeX ($...$ hoặc $$...$$).
   - Nếu học sinh hỏi bài bằng ảnh, hãy căn cứ vào ngữ cảnh đối thoại để viết lại đầy đủ đề bài chữ.

2. BÍ KÍP CỐT LÕI (key_takeaway) - QUAN TRỌNG NHẤT:
   - Đúc kết ngắn gọn từ 1 đến 2 câu chứa công thức then chốt, định lý hoặc mẹo tư duy cốt lõi đã giúp giải bài toán này.
   - Lời văn ngắn gọn, dễ thuộc lòng, dùng công thức LaTeX chuẩn.
   - Ví dụ:
     * Dạng Tổng - Tỉ: "Bước 1: Tìm tổng số phần bằng nhau. Bước 2: Giá trị 1 phần = Tổng : Số phần. Bước 3: Tìm từng số."
     * Phân số: "Muốn cộng hai phân số khác mẫu: Quy đồng mẫu số rồi cộng các tử số với nhau, giữ nguyên mẫu số chung."
     * Hình học: "Định lý Pytago: Trong tam giác vuông, bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông ($a^2 + b^2 = c^2$)."

3. ĐÁP SỐ CHỐT (final_answer):
   - Ghi lại kết quả cuối cùng đã được xác nhận là chính xác trong đoạn chat.
   - Ngắn gọn, có đơn vị đo nếu có (ví dụ: "$x = 3$", "5/6", "15 cm", "40 tuổi").

4. DẠNG TOÁN (topic_tag):
   - Gán 1 nhãn chuyên đề ngắn gọn (2-4 từ) như: "Phân số", "Tìm X", "Hình học", "Toán tỉ số", "Toán chuyển động", "Số thập phân".

5. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - Trả về JSON thuần túy (Plain JSON).
   - TUYỆT ĐỐI KHÔNG bọc trong ```json ... ``` hoặc ký tự ngoài JSON.
"""

def _format_chat_for_flashcard(messages: List[Dict[str, Any]]) -> str:
    """Chuyển danh sách tin nhắn thành chuỗi văn bản cho Gemini đọc."""
    lines = []
    for msg in messages:
        sender = msg.get("sender_type", "USER")
        content = msg.get("content", "").strip()
        lines.append(f"{sender}: {content}")
    return "\n".join(lines)


def generate_flashcard_content(
    messages: List[Dict[str, Any]],
    api_key: Optional[str] = None,
) -> FlashcardContent:
    """
    Gọi Gemini API để đúc kết bài toán thành Thẻ Flashcard.
    Đồng bộ model qua biến môi trường GEMINI_MODEL (mặc định gemini-3.5-flash-lite).
    """
    if not messages:
        return _fallback_flashcard(problem_text="Không có dữ liệu bài toán")

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        first_user_msg = next((m.get("content", "") for m in messages if m.get("sender_type") == "USER"), "Bài toán")
        return _fallback_flashcard(problem_text=first_user_msg)

    genai.configure(api_key=key)
    # Đồng bộ model qua biến môi trường GEMINI_MODEL
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    formatted_chat = _format_chat_for_flashcard(messages)

    prompt = f"""
Hãy đúc kết đoạn hội thoại giải toán dưới đây thành một Thẻ Flashcard ôn tập thông minh:

─── ĐOẠN ĐỐI THOẠI BÀI TOÁN ───
{formatted_chat}

─── YÊU CẦU ĐỊNH DẠNG JSON ĐẦU RA ───
Chỉ trả về JSON thuần túy theo cấu trúc:
{{
  "problem_statement": "Đề bài toán đầy đủ kèm LaTeX",
  "key_takeaway": "1-2 câu bí kíp/công thức cốt lõi dễ nhớ nhất",
  "final_answer": "Kết quả cuối cùng ngắn gọn chính xác",
  "topic_tag": "Tên dạng toán ngắn gọn"
}}
"""

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=FLASHCARD_EXTRACTION_SYSTEM_INSTRUCTION,
            generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        result_dict = json.loads(raw_text)

        # 🛡️ Validate qua Pydantic v2
        validated = FlashcardContent.model_validate(result_dict)
        return validated

    except Exception as e:
        print(f"[Cảnh báo Flashcard Extraction] Lỗi khi gọi Gemini: {e}")
        first_user_msg = next((m.get("content", "") for m in messages if m.get("sender_type") == "USER"), "Bài toán")
        return _fallback_flashcard(problem_text=first_user_msg, reason=str(e))


def _fallback_flashcard(problem_text: str, reason: str = "") -> FlashcardContent:
    """Hàm dự phòng an toàn khi mất mạng hoặc quota Gemini gặp sự cố."""
    return FlashcardContent(
        problem_statement=problem_text,
        key_takeaway="Đọc kỹ đề bài, tóm tắt các đại lượng đã biết và áp dụng đúng công thức tương ứng.",
        final_answer="Đã hoàn thành",
        topic_tag="Toán tổng hợp",
        is_fallback=True
    )