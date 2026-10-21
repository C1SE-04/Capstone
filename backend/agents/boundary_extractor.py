from typing import List, Dict, Any, Optional
import os
import json
import google.generativeai as genai
from schemas import ProblemBoundaryResult, BoundaryMessageItem

# ========================================================
# 1. SYSTEM INSTRUCTION SƯ PHẠM CHO BOUNDARY EXTRACTION
# ========================================================
BOUNDARY_EXTRACTION_SYSTEM_INSTRUCTION = """
Bạn là một Trợ lý AI Phân Tích Dữ Liệu Hội Thoại Sư Phạm chuyên nghiệp của hệ thống SocraticKid.
Nhiệm vụ của bạn là: Đọc một chuỗi các tin nhắn đối thoại giữa Học sinh (USER) và Gia sư AI (AGENT_TUTOR) trong một phiên học, sau đó XÁC ĐỊNH CHÍNH XÁC RANH GIỚI CỦA BÀI TOÁN VỪA HOÀN THÀNH.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC QUY TẮC PHÂN TÍCH SAU:
1. NGUYÊN TẮC BÀI TOÁN VỪA HOÀN THÀNH (TARGET PROBLEM):
   - Bài toán cần trích xuất LUÔN LUÔN là bài toán được hoàn thành ở cuối chuỗi tin nhắn (ngay trước khi học sinh bấm "Đã hiểu" hoặc kết thúc phiên).
   - Hãy tìm tin nhắn bắt đầu thực sự của bài toán này (nơi học sinh đưa ra đề bài mới, câu hỏi toán học mới hoặc ảnh bài tập mới).

2. PHÁT HIỆN BÀI CŨ BỊ BỎ DỞ (ABANDONED PROBLEMS / TOPIC SWITCH):
   - Nếu trong phiên chat, học sinh từng hỏi một bài toán khác trước đó nhưng bỏ ngang giữa chừng (ví dụ: than "khó quá bỏ qua", hoặc đột ngột chuyển sang hỏi đề bài khác hoàn toàn):
     + Đặt cờ: `has_abandoned_problem = true`
     + Tóm tắt ngắn bài bị bỏ dở trong `abandoned_problem_summary`.
     + ĐIỀU QUAN TRỌNG NHẤT: Ranh giới `boundary_start_index` PHẢI bắt đầu từ bài toán mới, TUYỆT ĐỐI KHÔNG được chứa các tin nhắn của bài toán cũ đã bị bỏ dở!

3. LOẠI BỎ TIN NHẮN RÁC / CHÀO HỎI PHIẾM:
   - Các tin nhắn như "Chào thầy", "Thầy ơi", "Thời tiết hôm nay đẹp quá"... ở đầu phiên KHÔNG ĐƯỢC tính là điểm bắt đầu ranh giới. Ranh giới chỉ tính từ câu hỏi toán học thực sự.

4. TRÍCH XUẤT ĐỀ BÀI (extracted_problem):
   - Đề bài phải được làm sạch, giữ nguyên số liệu và công thức LaTeX ($...$ hoặc $$...$$).
   - Nếu học sinh gửi ảnh kèm lời nhắn ngắn (ví dụ: "Thầy xem ảnh giúp em"), hãy đọc ngữ cảnh gia sư đối thoại để viết lại đề bài toán rõ ràng trong `extracted_problem`.

5. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - Trả về JSON thuần túy (Plain JSON).
   - TUYỆT ĐỐI KHÔNG bọc trong ```json ... ``` hoặc ký tự ngoài JSON.
"""

def _format_conversation_for_gemini(messages: List[Dict[str, Any]]) -> str:
    """Format danh sách tin nhắn thành văn bản đánh số index rõ ràng cho Gemini phân tích."""
    lines = []
    for idx, msg in enumerate(messages):
        sender = msg.get("sender_type", "USER")
        content = msg.get("content", "").strip()
        attachment = msg.get("attachment_url")
        attach_str = f" [Có đính kèm ảnh: {attachment}]" if attachment else ""
        lines.append(f"[{idx}] {sender}: {content}{attach_str}")
    return "\n".join(lines)


def extract_problem_boundary(
    messages: List[Dict[str, Any]],
    api_key: Optional[str] = None,
) -> ProblemBoundaryResult:
    """
    Hàm phân tích ranh giới bài toán sử dụng Gemini API.
    Nếu có lỗi hoặc không có API key, tự động dùng Heuristic Fallback thông minh.
    """
    if not messages:
        return ProblemBoundaryResult(
            extracted_problem="Không có dữ liệu bài toán",
            boundary_start_index=0,
            boundary_end_index=0,
            filtered_messages=[],
            has_abandoned_problem=False,
            is_fallback=True
        )

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _heuristic_boundary_fallback(messages, reason="Không tìm thấy GEMINI_API_KEY")

    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    
    formatted_convo = _format_conversation_for_gemini(messages)
    
    prompt = f"""
Hãy phân tích lịch sử đối thoại dưới đây và xác định ranh giới của bài toán vừa hoàn thành:

─── LỊCH SỬ ĐỐI THOẠI TRONG PHIÊN ───
{formatted_convo}

─── YÊU CẦU ĐỊNH DẠNG JSON ĐẦU RA ───
Chỉ trả về JSON thuần túy theo cấu trúc:
{{
  "extracted_problem": "Nội dung đề bài hoàn chỉnh của bài toán vừa giải xong (chứa LaTeX nếu có)",
  "boundary_start_index": <số nguyên index của tin nhắn bắt đầu bài toán này>,
  "boundary_end_index": <số nguyên index của tin nhắn kết thúc bài toán này>,
  "has_abandoned_problem": <true nếu học sinh từng bỏ dở bài khác trước đó, false nếu không>,
  "abandoned_problem_summary": <chuỗi tóm tắt bài bị bỏ dở hoặc null nếu không có>
}}
"""

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=BOUNDARY_EXTRACTION_SYSTEM_INSTRUCTION,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        result_dict = json.loads(raw_text)

        start_idx = max(0, min(result_dict.get("boundary_start_index", 0), len(messages) - 1))
        end_idx = max(start_idx, min(result_dict.get("boundary_end_index", len(messages) - 1), len(messages) - 1))

        # Cắt đúng danh sách tin nhắn nằm trong ranh giới
        filtered = []
        for i in range(start_idx, end_idx + 1):
            m = messages[i]
            filtered.append(
                BoundaryMessageItem(
                    index=i,
                    sender_type=m.get("sender_type", "USER"),
                    content=m.get("content", ""),
                    attachment_url=m.get("attachment_url"),
                    created_at=str(m.get("created_at", ""))
                )
            )

        return ProblemBoundaryResult(
            extracted_problem=result_dict.get("extracted_problem", messages[start_idx].get("content", "")),
            boundary_start_index=start_idx,
            boundary_end_index=end_idx,
            filtered_messages=filtered,
            has_abandoned_problem=bool(result_dict.get("has_abandoned_problem", False)),
            abandoned_problem_summary=result_dict.get("abandoned_problem_summary"),
            is_fallback=False
        )

    except Exception as e:
        print(f"[Cảnh báo Boundary Extraction] Lỗi khi gọi Gemini: {e}")
        return _heuristic_boundary_fallback(messages, reason=str(e))


def _heuristic_boundary_fallback(messages: List[Dict[str, Any]], reason: str = "") -> ProblemBoundaryResult:
    """
    Thuật toán Heuristic dự phòng khi không thể gọi Gemini API:
    Quét ngược từ cuối danh sách tin nhắn lên để tìm tin nhắn đề bài gần nhất.
    Phát hiện các từ khóa đổi đề như 'bài khác', 'không làm nữa', 'thôi', 'đổi bài'.
    """
    total = len(messages)
    start_idx = 0
    has_abandoned = False
    abandoned_summary = None

    # Tìm kiếm ngược từ tin nhắn cuối cùng lên
    switch_keywords = ["bài khác", "không làm nữa", "đổi bài", "thôi bài này", "bỏ qua bài này", "làm bài này đi"]
    
    for i in range(total - 1, -1, -1):
        msg = messages[i]
        content_lower = msg.get("content", "").lower()
        
        # Nếu gặp tin nhắn học sinh xin đổi bài
        if msg.get("sender_type") == "USER" and any(k in content_lower for k in switch_keywords):
            start_idx = i
            has_abandoned = True
            abandoned_summary = "Học sinh chủ động đổi bài giữa chừng trong phiên học."
            break

    # Nếu không thấy từ khóa đổi bài, tìm tin nhắn USER đầu tiên có nội dung toán học hoặc có ảnh
    if start_idx == 0:
        for i, msg in enumerate(messages):
            if msg.get("sender_type") == "USER":
                content = msg.get("content", "").strip()
                # Bỏ qua các câu chào cụt
                if content.lower() in ["chào thầy", "chào thầy ạ", "thầy ơi", "alo", "hi thầy", "hello"]:
                    continue
                start_idx = i
                break

    end_idx = total - 1
    extracted = messages[start_idx].get("content", "Bài toán") if total > 0 else ""

    filtered = []
    for i in range(start_idx, end_idx + 1):
        m = messages[i]
        filtered.append(
            BoundaryMessageItem(
                index=i,
                sender_type=m.get("sender_type", "USER"),
                content=m.get("content", ""),
                attachment_url=m.get("attachment_url"),
                created_at=str(m.get("created_at", ""))
            )
        )

    return ProblemBoundaryResult(
        extracted_problem=extracted,
        boundary_start_index=start_idx,
        boundary_end_index=end_idx,
        filtered_messages=filtered,
        has_abandoned_problem=has_abandoned,
        abandoned_problem_summary=abandoned_summary,
        is_fallback=True
    )