from typing import Dict, Any, List, Optional
import os
import json
import google.generativeai as genai
from schemas import AiInsightReportResponse

# ==========================================
# 1. HẰNG SỐ SYSTEM INSTRUCTION SƯ PHẠM
# ==========================================
PARENT_INSIGHTS_SYSTEM_INSTRUCTION = """
Bạn là một Chuyên gia Cố vấn Sư phạm Toán học giàu kinh nghiệm, tận tâm và thấu hiểu tâm lý lứa tuổi học sinh từ Lớp 4 đến Lớp 9 tại Việt Nam.
Nhiệm vụ của bạn là: Đọc bảng dữ liệu thống kê quá trình học tập thực tế của học sinh (gồm tổng số bài đã giải, các dạng toán đã làm, điểm tự lực và tần suất xin trợ giúp) để viết một "BÁO CÁO NHẬN XÉT SƯ PHẠM" gửi riêng cho Phụ huynh học sinh.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC NGUYÊN TẮC VÀNG SAU ĐÂY:
1. TÔN TRỌNG SỰ THỰC DỮ LIỆU:
   - Dựa hoàn toàn vào các con số trong bản thống kê được cung cấp. Tuyệt đối không bịa đặt hoặc suy diễn vượt ngoài dữ liệu.
   - Nếu học sinh giải tốt (điểm tự lực cao >= 80, ít dùng gợi ý): Khen ngợi rõ ràng tư duy độc lập và sự tự giác của con.
   - Nếu học sinh gặp khó khăn (điểm tự lực thấp < 60, nhiều lần bấm 'Chưa hiểu', cần nhiều gợi ý): Nhẹ nhàng chỉ ra chính xác dạng toán con đang lúng túng, không chỉ trích, không tạo cảm giác tiêu cực hay áp lực cho phụ huynh.

2. NGUYÊN TẮC PHẢN HỒI SƯ PHẠM (SANDWICH FEEDBACK):
   - Luôn ghi nhận điểm tích cực/sự kiên trì của con trước (Strengths).
   - Tiếp theo phân tích khúc mắc tư duy cụ thể cần tháo gỡ (Weak Points).
   - Kết thúc bằng lời khuyên hành động cụ thể, dễ áp dụng tại nhà cho cha mẹ (Recommendations).

3. LỜI KHUYÊN DÀNH CHO PHỤ HUYNH PHẢI CỤ THỂ & THỰC TẾ:
   - KHÔNG đưa ra lời khuyên sáo rỗng như: "Hãy cho con làm thêm nhiều bài tập", "Cần cố gắng hơn".
   - PHẢI đưa ra chỉ dẫn hành động gắn với dạng toán thực tế. Ví dụ: "Khi con làm dạng toán Tìm hai số khi biết Tổng và Hiệu, cha mẹ hãy gợi ý con vẽ sơ đồ đoạn thẳng ra giấy nháp trước khi làm phép tính", hoặc "Hãy khuyến khích con đọc to đề bài 2 lần để gạch chân từ khóa quan trọng".

4. PHONG CÁCH DIỄN ĐẠT:
   - Ấm áp, tôn trọng, mang tính xây dựng, đáng tin cậy như một người thầy tâm huyết đang trò chuyện cùng phụ huynh.
   - Xưng hô chuẩn mực: "con", "em", "phụ huynh", "cha mẹ".
   - TUYỆT ĐỐI KHÔNG sử dụng thuật ngữ kỹ thuật AI (như 'Prompt', 'Token', 'Model', 'Penalty', 'Database').

5. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - Bắt buộc trả về đúng định dạng JSON thuần túy (Plain JSON).
   - TUYỆT ĐỐI KHÔNG bọc trong ```json ... ``` hoặc bất kỳ ký tự nào bên ngoài JSON.
"""

# ==========================================
# 2. HÀM CHUẨN HÓA DỮ LIỆU ĐẦU VÀO (HELPER)
# ==========================================
def format_parent_insights_prompt(
    student_name: str,
    grade_level: int,
    period_description: str,
    total_problems_completed: int,
    average_independence_score: float,
    total_hints_used: int,
    total_not_understood_count: int,
    topic_breakdown: List[Dict[str, Any]],
) -> str:
    """
    Biến đổi dữ liệu thống kê từ Backend thành chuỗi Prompt ngữ cảnh chi tiết cho Gemini.
    """
    topics_str_list = []
    for t in topic_breakdown:
        topic_name = t.get("topic_name", "Toán tổng hợp")
        solved = t.get("problems_solved", 0)
        avg_score = t.get("avg_independence", 0)
        hints = t.get("hints_used", 0)
        not_understood = t.get("not_understood", 0)
        topics_str_list.append(
            f"  - Dạng toán '{topic_name}': Đã hoàn thành {solved} bài | Điểm tự lập TB: {avg_score}/100 | Số gợi ý đã dùng: {hints} | Bấm 'Chưa hiểu': {not_understood} lần"
        )
    topics_formatted = "\n".join(topics_str_list) if topics_str_list else "  - (Chưa có dữ liệu chi tiết theo từng chuyên đề)"

    prompt = f"""
Hãy phân tích dữ liệu học tập dưới đây và xuất ra BÁO CÁO NHẬN XÉT SƯ PHẠM cho phụ huynh học sinh.

─── DỮ LIỆU THỐNG KÊ HỌC TẬP ───
• Tên học sinh: {student_name}
• Khối lớp hiện tại: Lớp {grade_level}
• Khoảng thời gian đánh giá: {period_description}
• Tổng số bài toán đã giải hoàn thành: {total_problems_completed} bài
• Điểm Tự Lực (Independence Score) trung bình toàn đợt: {average_independence_score:.1f} / 100
• Tổng số gợi ý (hints) con đã dùng: {total_hints_used} lần
• Tổng số lần con bấm 'Chưa hiểu' khi gặp khó: {total_not_understood_count} lần

─── CHI TIẾT THEO TỪNG DẠNG TOÁN ───
{topics_formatted}

─── YÊU CẦU ĐỊNH DẠNG JSON ĐẦU RA ───
Chỉ trả về JSON thuần túy theo cấu trúc chính xác sau:
{{
  "summary": "Chuỗi văn bản (2-3 câu) tóm tắt tổng thể phong độ học tập, tinh thần tự giác và mức độ tiến bộ của con trong kỳ học vừa qua.",
  "strengths": [
    "Điểm mạnh thứ nhất (cụ thể dạng toán con làm chủ tốt nhất hoặc thái độ kiên trì giải quyết)",
    "Điểm mạnh thứ hai (khả năng tư duy độc lập hoặc mức độ thành thạo)"
  ],
  "weak_points": [
    "Khó khăn cụ thể thứ nhất (dạng toán con còn lúng túng hoặc bước suy luận con hay gặp trở ngại)",
    "Khó khăn cụ thể thứ hai (nếu có, dựa vào số gợi ý hoặc tần suất bấm Chưa hiểu)"
  ],
  "recommendations": [
    "Lời khuyên sư phạm cụ thể 1: Cha mẹ nên hỏi hoặc cùng con làm gì tại nhà để củng cố dạng bài yếu",
    "Lời khuyên sư phạm cụ thể 2: Cách khích lệ tinh thần tự giác để con tiếp tục phát huy điểm mạnh"
  ],
  "mastery_assessment": "Tự lập xuất sắc | Tự lập tốt | Đang tiến bộ | Cần thêm hỗ trợ sư phạm"
}}
"""
    return prompt.strip()


# ==========================================
# 3. HÀM GỌI GEMINI SINH REPORT
# ==========================================
def generate_parent_learning_insights(
    student_name: str,
    grade_level: int,
    period_description: str,
    total_problems_completed: int,
    average_independence_score: float,
    total_hints_used: int,
    total_not_understood_count: int,
    topic_breakdown: List[Dict[str, Any]],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Gọi Google Gemini API để sinh báo cáo nhận xét sư phạm dưới dạng Dict/JSON.
    Hỗ trợ fallback an toàn nếu API lỗi.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _fallback_insights(
            student_name=student_name,
            total_problems=total_problems_completed,
            score=average_independence_score,
            reason="Thiếu GEMINI_API_KEY cấu hình môi trường."
        )

    genai.configure(api_key=key)

    # Sử dụng model gemini-2.5-flash hoặc gemini-3.5-flash-lite có sẵn trong dự án
    # Nhiệt độ thấp (0.25) để báo cáo mang tính sư phạm chuẩn xác, không bịa đặt số liệu
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    generation_config = {
        "temperature": 0.25,
        "top_p": 0.9,
        "max_output_tokens": 1024,
        "response_mime_type": "application/json",
    }

    prompt_content = format_parent_insights_prompt(
        student_name=student_name,
        grade_level=grade_level,
        period_description=period_description,
        total_problems_completed=total_problems_completed,
        average_independence_score=average_independence_score,
        total_hints_used=total_hints_used,
        total_not_understood_count=total_not_understood_count,
        topic_breakdown=topic_breakdown,
    )

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=PARENT_INSIGHTS_SYSTEM_INSTRUCTION,
            generation_config=generation_config,
        )
        response = model.generate_content(prompt_content)
        raw_text = response.text.strip()

        # Dọn dẹp markdown nếu có
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        result_dict = json.loads(raw_text)
        
        # Xác thực cấu trúc dữ liệu trước khi trả về
        validated_report = AiInsightReportResponse.model_validate(result_dict)
        return validated_report.model_dump()
    except Exception as e:
        print(f"[Cảnh báo AI Insights] Lỗi khi gọi Gemini sinh nhận xét sư phạm: {e}")
        fallback_data = _fallback_insights(
            student_name=student_name,
            total_problems=total_problems_completed,
            score=average_independence_score,
            reason=str(e)
        )
        return AiInsightReportResponse.model_validate(fallback_data).model_dump()


def _fallback_insights(student_name: str, total_problems: int, score: float, reason: str = "") -> Dict[str, Any]:
    """Hàm dự phòng (fallback) khi Gemini gặp sự cố mạng hoặc quota."""
    assessment = "Đang tiến bộ"
    if score >= 80:
        assessment = "Tự lập xuất sắc"
    elif score >= 60:
        assessment = "Tự lập tốt"
    elif score < 40:
        assessment = "Cần thêm hỗ trợ sư phạm"

    return {
        "summary": f"Trong đợt học vừa qua, em {student_name} đã nỗ lực hoàn thành {total_problems} bài toán với điểm tự lực trung bình đạt {score:.1f}/100. Em đang duy trì nhịp độ học tập ổn định.",
        "strengths": [
            f"Em {student_name} có thái độ học tập kiên trì và hoàn thành trọn vẹn các bài toán được giao.",
            "Tích cực tương tác với gia sư để từng bước tìm ra lời giải bài tập."
        ],
        "weak_points": [
            "Con còn cần một số gợi ý ở các bước tính toán phức tạp trước khi tự mình chốt đáp số."
        ],
        "recommendations": [
            "Phụ huynh hãy tiếp tục động viên con duy trì thói quen học tập đều đặn mỗi ngày.",
            "Khuyến khích con tự tóm tắt đề bài ra giấy nháp trước khi bắt đầu giải."
        ],
        "mastery_assessment": assessment,
        "is_fallback": True,
        "fallback_reason": reason,
    }