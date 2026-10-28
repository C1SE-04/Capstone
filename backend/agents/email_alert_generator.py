from typing import Dict, Any, List, Optional
import os
import re
import json
import google.generativeai as genai
from schemas import (
    AcademicAlertGenerateRequest,
    AcademicAlertEmailResult,
    SafetyAlertGenerateRequest,
    SafetyAlertEmailResult,
)
from agents.orchestrator import OrchestratorAgent
# =====================================================================
# 1. BỘ LỌC KIỂM DUYỆT TỪ NGỮ THÔ TỤC (TÁI SỬ DỤNG TỪ ORCHESTRATOR)
# =====================================================================

# Danh sách đại từ xưng hô thiếu tôn trọng / vô lễ (giữ nguyên không che mờ bằng dấu *
# để phụ huynh đọc hiểu rõ ngữ cảnh con xưng hô cộc lốc như thế nào)
_DISRESPECT_WORDS = {
    "mày", "tao", "mầy", "thằng kia", "con kia", "bot ngu", "thằng bot", "m", "mi"
    "con bot", "ông già", "bà già", "chúng mày", "bọn mày", "thằng này", "con này"
}

# Lọc riêng tập hợp các từ ngữ thô tục / tục tĩu thực sự từ OrchestratorAgent.PROFANITY_LIST
# Bỏ qua các đại từ xưng hô để tránh che mờ nhầm 'mày' thành 'm**' làm phụ huynh hiểu lầm
_PURE_PROFANITY_LIST = [
    w.strip().lower() for w in OrchestratorAgent.PROFANITY_LIST 
    if w.strip().lower() not in _DISRESPECT_WORDS
]

# Sắp xếp từ dài nhất lên trước để ưu tiên match cụm từ dài trước (VD: 'địt con mẹ' trước 'địt')
_PURE_PROFANITY_SORTED = sorted(list(set(_PURE_PROFANITY_LIST)), key=len, reverse=True)


def _collapse_repeated_chars(text: str) -> str:
    """Rút gọn các ký tự lặp kéo dài do học sinh gõ khi ức chế (VD: 'vclllll' -> 'vcl', 'đmmmmm' -> 'đm')."""
    return re.sub(r"(.)\1{2,}", r"\1\1", text)


def censor_sensitive_words(text: str) -> str:
    """
    Che mờ các từ ngữ thô tục, chửi thề trong văn bản dựa trên kho PROFANITY_LIST chuẩn của hệ thống.
    Ví dụ: 'địt' -> 'đ**', 'vcl' -> 'v**', 'mẹ kiếp' -> 'm** k***'.
    Đảm bảo nội dung gửi qua email phụ huynh luôn sạch sẽ, nhân văn và đồng bộ với Orchestrator.
    """
    if not text:
        return ""
    
    censored = text
    
    # 1. Duyệt qua kho từ thô tục chuẩn của Orchestrator (đã sort dài trước ngắn)
    for word in _PURE_PROFANITY_SORTED:
        # Match nguyên từ hoặc cụm từ (hỗ trợ cả trường hợp kéo dài ký tự cuối)
        escaped_word = re.escape(word)
        pattern = rf"\b{escaped_word}+\b"
        
        def _mask_match(match):
            m = match.group(0)
            parts = m.split()
            masked_parts = []
            for p in parts:
                if len(p) <= 2:
                    masked_parts.append(p[0] + "*")
                else:
                    masked_parts.append(p[0] + "*" * (len(p) - 1))
            return " ".join(masked_parts)
            
        censored = re.sub(pattern, _mask_match, censored, flags=re.IGNORECASE | re.UNICODE)
        
    return censored


# =====================================================================
# 2. SYSTEM INSTRUCTIONS SƯ PHẠM CHO 2 LOẠI EMAIL ALERT
# =====================================================================

ACADEMIC_ALERT_SYSTEM_INSTRUCTION = """
Bạn là Chuyên gia Cố vấn Sư phạm Toán học & Đồng hành Gia đình tại SocraticKid.
Nhiệm vụ của bạn là: Phân tích dữ liệu học tập khi một học sinh (Lớp 4 - Lớp 9) gặp khó khăn liên tiếp (điểm tự lập < 60 trong 3 bài liên tiếp hoặc liên tục bấm Chưa hiểu), và soạn thảo một EMAIL THÔNG BÁO VÀ HƯỚNG DẪN ĐỒNG HÀNH gửi riêng cho Phụ huynh học sinh.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC NGUYÊN TẮC VÀNG SAU ĐÂY:
1. NGUYÊN TẮC PHẢN HỒI SANDWICH FEEDBACK:
   - Khen ngợi nỗ lực (Strengths): Luôn ghi nhận sự kiên trì của con, dám đương đầu với bài khó mà không bỏ cuộc.
   - Phân tích lỗ hổng kiến thức (Learning Gap): Nhẹ nhàng chỉ ra chính xác dạng toán hoặc bước suy luận con đang vướng mắc. Không quy kết con "học kém" hay "chậm hiểu".
   - Giải pháp hành động tại nhà (Actionable Advice): Đưa ra 2-3 lời khuyên rất cụ thể cho cha mẹ (ví dụ: cùng con vẽ sơ đồ đoạn thẳng, nhắc con đọc to đề bài, tạo không khí học thoải mái không la mắng).
2. PHONG THÁI & GIỌNG ĐIỆU:
   - Ấm áp, thấu hiểu, mang tính xây dựng, đáng tin cậy. Tuyệt đối không dùng từ ngữ gây áp lực hay hoang mang cho cha mẹ.
3. GỢI Ý MỞ LỜI (Conversation Opener):
   - Cung cấp một câu nói gợi ý tự nhiên, ấm áp để cha mẹ có thể bắt chuyện với con sau bữa tối mà con không cảm thấy bị kiểm tra hay tra khảo.
4. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - Chỉ trả về JSON thuần túy (Plain JSON), không bọc trong ```json ... ``` hay bất kỳ ghi chú nào bên ngoài.
"""

SAFETY_ALERT_SYSTEM_INSTRUCTION = """
Bạn là Chuyên gia Tâm lý Học đường và Cố vấn Đồng hành Gia đình tại SocraticKid.
Nhiệm vụ của bạn là: Khi hệ thống Safety Agent phát hiện một học sinh (Lớp 4 - Lớp 9) sử dụng từ ngữ thô tục, chửi thề hoặc xưng hô vô lễ trong buổi học với trợ lý gia sư, bạn hãy soạn thảo một EMAIL NHẮC NHỞ TINH TẾ & ĐỊNH HƯỚNG TÂM LÝ gửi riêng cho Phụ huynh.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC NGUYÊN TẮC VÀNG SAU ĐÂY:
1. THẤU HIỂU TÂM LÝ LỨA TUỔI:
   - Lứa tuổi học sinh Lớp 4 đến Lớp 9 (tiền dậy thì và dậy thì) có diễn biến tâm lý nhạy cảm. Việc con bộc phát lời nói thô tục thường xuất phát từ sự bực bội/ức chế khi gặp bài toán quá khó không làm được, hoặc do bắt chước bạn bè/mạng xã hội mà chưa nhận thức hết tính nghiêm trọng.
   - TUYỆT ĐỐI KHÔNG quy kết bản chất đạo đức của con. Không dùng từ ngữ lên án gay gắt.
2. NGUYÊN TẮC BẢO VỆ & CHE MỜ TỪ THÔ (CENSORSHIP):
   - Mọi từ ngữ nhạy cảm trong trích đoạn vi phạm PHẢI ĐƯỢC CHE MỜ bằng ký tự sao (ví dụ: 'đ**', 'v**', 'c**').
3. ĐỊNH HƯỚNG THÁI ĐỘ CHO PHỤ HUYNH:
   - Nhắc nhở cha mẹ giữ bình tĩnh, lắng nghe nguyên nhân cảm xúc phía sau của con trước, không dùng đòn roi hay mắng mỏ nặng lời gây phản tác dụng tâm lý.
4. LỜI KHUYÊN HÀNH ĐỘNG & CÂU MỞ LỜI:
   - 2-3 lời khuyên cụ thể giúp con rèn luyện thói quen kiềm chế cảm xúc tiêu cực và văn hóa ứng xử văn minh.
   - Một câu gợi ý trò chuyện mẫu để cha mẹ dễ dàng khơi chuyện tâm sự với con như một người bạn lớn.
5. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - Chỉ trả về JSON thuần túy (Plain JSON), không bọc trong ```json ... ``` hay bất kỳ ghi chú nào bên ngoài.
"""


# =====================================================================
# 3. HÀM FALLBACK AN TOÀN (RULE-BASED)
# =====================================================================

def _fallback_academic_alert(req: AcademicAlertGenerateRequest, reason: str = "") -> AcademicAlertEmailResult:
    """Tạo email cảnh báo học tập mẫu chuẩn mực khi Gemini API gặp sự cố hoặc thiếu API key."""
    topics_text = ", ".join(req.difficult_topics) if req.difficult_topics else "các bài toán tư duy có lời văn"
    return AcademicAlertEmailResult(
        alert_type="ACADEMIC_ALERT",
        email_subject=f"[SocraticKid] Đồng hành cùng bé {req.student_name}: Củng cố bài học môn Toán Lớp {req.grade}",
        student_name=req.student_name,
        grade=req.grade,
        trigger_reason=req.trigger_reason,
        summary=f"Trong các buổi học vừa qua, bé {req.student_name} đã rất kiên trì rèn luyện nhưng đang gặp chút khó khăn ở {topics_text}, với điểm tự lập trung bình đạt {req.average_recent_score:.0f}/100.",
        strengths_observed=f"Bé {req.student_name} có tinh thần tự giác cao, không bỏ cuộc khi gặp bài toán mới và rất tích cực tương tác cùng trợ lý Socratic.",
        learning_gap_analysis=f"Con đang lúng túng ở bước phân tích mối quan hệ giữa các đại lượng trong đề bài và chưa quen với cách biểu diễn dữ kiện bài toán ra nháp.",
        actionable_parent_advice=[
            "Gợi ý con đọc to đề bài 2 lần và dùng bút chì gạch chân dưới các con số quan trọng trước khi giải.",
            "Khuyến khích con vẽ sơ đồ đoạn thẳng hoặc hình minh họa ra giấy nháp để dễ hình dung bài toán.",
            "Dành lời khen ngợi cho sự nỗ lực của con thay vì đặt nặng điểm số, giúp con giữ vững niềm yêu thích môn Toán."
        ],
        suggested_conversation_opener=f"Tối nay bố/mẹ thấy con ngồi học rất tập trung. Có bài toán nào làm con thấy hơi khúc mắc không, kể cho bố/mẹ nghe với nhé!",
        is_fallback=True,
        fallback_reason=reason or "Sử dụng mẫu chuẩn bị sẵn do API chưa phản hồi."
    )


def _fallback_safety_alert(req: SafetyAlertGenerateRequest, reason: str = "") -> SafetyAlertEmailResult:
    """Tạo email cảnh báo ngôn từ mẫu chuẩn mực khi Gemini API gặp sự cố hoặc thiếu API key."""
    censored = censor_sensitive_words(req.original_message)
    return SafetyAlertEmailResult(
        alert_type="SAFETY_ALERT",
        email_subject=f"[SocraticKid] Phối hợp rèn luyện thói quen giao tiếp tích cực cho bé {req.student_name}",
        student_name=req.student_name,
        grade=req.grade,
        violation_category="Ngôn từ chưa phù hợp trong giờ học",
        censored_snippet=censored,
        context_analysis=f"Khi gặp thử thách trong buổi học, bé {req.student_name} có biểu hiện bộc phát cảm xúc nhất thời qua lời nói chưa chuẩn mực. Đây là phản ứng tâm lý thường gặp khi trẻ cảm thấy bế tắc hoặc áp lực trước bài toán khó.",
        tone_guidance_for_parent="Cha mẹ nên tiếp cận bằng sự thấu hiểu và điềm tĩnh, tránh la mắng gay gắt khiến con thu mình hoặc nảy sinh tâm lý chống đối.",
        actionable_parent_advice=[
            "Hỏi thăm xem con có đang cảm thấy mệt mỏi hoặc bực bội với bài toán nào gần đây không.",
            "Nhẹ nhàng giải thích cho con hiểu sự khác biệt giữa việc thể hiện sự khó chịu và việc dùng từ ngữ chưa tôn trọng người đối diện.",
            "Quy ước với con khi cảm thấy quá căng thẳng thì có thể tạm dừng nghỉ ngơi 5 phút uống nước trước khi học tiếp."
        ],
        suggested_conversation_opener=f"Hôm nay ngồi học môn Toán có bài nào làm con thấy bực bội hay đau đầu không? Nếu thấy khó quá thì con cứ nói với bố/mẹ nhé!",
        is_fallback=True,
        fallback_reason=reason or "Sử dụng mẫu chuẩn bị sẵn do API chưa phản hồi."
    )


# =====================================================================
# 4. HÀM GỌI GEMINI SINH EMAIL ALERT
# =====================================================================

def generate_academic_alert_email(
    request_data: AcademicAlertGenerateRequest,
    api_key: Optional[str] = None
) -> AcademicAlertEmailResult:
    """
    Gọi Gemini API để sinh nội dung Email Cảnh Báo Học Tập Yếu chuẩn sư phạm.
    Có cơ chế Fallback tự động khi mất kết nối hoặc API lỗi.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _fallback_academic_alert(request_data, "Thiếu cấu hình GEMINI_API_KEY trong môi trường.")

    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Format danh sách bài toán gần đây
    problems_lines = []
    for idx, p in enumerate(request_data.recent_problems, 1):
        problems_lines.append(
            f"  {idx}. Bài: '{p.problem_title}' | Điểm tự lập: {p.score}/100 | Số gợi ý: {p.hints_used} | Bấm 'Chưa hiểu': {p.not_understood_count} lần"
        )
    problems_block = "\n".join(problems_lines) if problems_lines else "  - (Chưa có danh sách bài cụ thể)"

    prompt = f"""
Hãy phân tích dữ liệu học tập sau đây của học sinh và xuất ra nội dung Email Cảnh Báo Học Tập Yếu gửi Phụ huynh:

── THÔNG TIN HỌC SINH ──
• Tên học sinh: {request_data.student_name}
• Khối lớp: Lớp {request_data.grade}
• Lý do kích hoạt cảnh báo: {request_data.trigger_reason}
• Điểm tự lập trung bình các bài gần đây: {request_data.average_recent_score:.1f}/100
• Các chuyên đề/dạng toán con gặp khó khăn: {', '.join(request_data.difficult_topics) if request_data.difficult_topics else 'Toán tổng hợp'}

── DANH SÁCH BÀI TOÁN GẦN ĐÂY ──
{problems_block}

── YÊU CẦU ĐỊNH DẠNG JSON ĐẦU RA ──
Chỉ xuất ra đúng định dạng JSON thuần túy theo cấu trúc:
{{
  "alert_type": "ACADEMIC_ALERT",
  "email_subject": "Tiêu đề email ấm áp, tinh tế, không gây hoang mang cho cha mẹ",
  "student_name": "{request_data.student_name}",
  "grade": {request_data.grade},
  "trigger_reason": "{request_data.trigger_reason}",
  "summary": "Tóm tắt ngắn gọn tình hình học tập gần đây (2-3 câu)",
  "strengths_observed": "Điểm tích cực về thái độ kiên trì hoặc nỗ lực của con",
  "learning_gap_analysis": "Phân tích cụ thể khúc mắc tư duy hoặc dạng bài con đang vướng",
  "actionable_parent_advice": [
    "Lời khuyên hành động cụ thể 1 tại nhà cho cha mẹ",
    "Lời khuyên hành động cụ thể 2",
    "Lời khuyên hành động cụ thể 3"
  ],
  "suggested_conversation_opener": "Câu gợi ý mở lời nhẹ nhàng để cha mẹ trò chuyện cùng con"
}}
"""

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=ACADEMIC_ALERT_SYSTEM_INSTRUCTION
        )
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.9,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            }
        )
        data = json.loads(response.text.strip())
        data["is_fallback"] = False
        return AcademicAlertEmailResult.model_validate(data)
    except Exception as e:
        return _fallback_academic_alert(request_data, f"Lỗi gọi Gemini API: {str(e)}")


def generate_safety_alert_email(
    request_data: SafetyAlertGenerateRequest,
    api_key: Optional[str] = None
) -> SafetyAlertEmailResult:
    """
    Gọi Gemini API để sinh nội dung Email Cảnh Báo Ngôn Từ Không Phù Hợp.
    Đảm bảo snippet vi phạm được kiểm duyệt che mờ từ thô (Censored / Masked).
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _fallback_safety_alert(request_data, "Thiếu cấu hình GEMINI_API_KEY trong môi trường.")

    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Che mờ từ ngữ thô trước khi đưa vào prompt và schema
    masked_message = censor_sensitive_words(request_data.original_message)

    prompt = f"""
Hãy phân tích sự cố phát ngôn sau đây của học sinh và xuất ra nội dung Email Cảnh Báo Ngôn Từ gửi Phụ huynh:

── THÔNG TIN HỌC SINH & SỰ VIỆC ──
• Tên học sinh: {request_data.student_name}
• Khối lớp: Lớp {request_data.grade}
• Loại vi phạm: {request_data.violation_type}
• Trích đoạn phát ngôn của con (đã che mờ): "{masked_message}"
• Ngữ cảnh bài học/hội thoại trước đó: {request_data.conversation_context or 'Trong lúc đang giải bài tập toán'}
• Thời điểm xảy ra: {request_data.incident_time or 'Hôm nay'}

── YÊU CẦU ĐỊNH DẠNG JSON ĐẦU RA ──
Chỉ xuất ra đúng định dạng JSON thuần túy theo cấu trúc:
{{
  "alert_type": "SAFETY_ALERT",
  "email_subject": "Tiêu đề email trang nhã, tôn trọng, không giật gân",
  "student_name": "{request_data.student_name}",
  "grade": {request_data.grade},
  "violation_category": "Ngôn từ chưa phù hợp trong giờ học",
  "censored_snippet": "{masked_message}",
  "context_analysis": "Phân tích nguyên nhân tâm lý dẫn đến bộc phát cảm xúc của con",
  "tone_guidance_for_parent": "Định hướng thái độ bình tĩnh, lắng nghe, không la mắng cho cha mẹ",
  "actionable_parent_advice": [
    "Lời khuyên hành động 1",
    "Lời khuyên hành động 2",
    "Lời khuyên hành động 3"
  ],
  "suggested_conversation_opener": "Câu mở lời gợi ý gần gũi để cha mẹ trò chuyện cùng con"
}}
"""

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SAFETY_ALERT_SYSTEM_INSTRUCTION
        )
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.9,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            }
        )
        data = json.loads(response.text.strip())
        # Đảm bảo snippet trong output luôn được áp dụng bộ lọc che mờ
        data["censored_snippet"] = censor_sensitive_words(data.get("censored_snippet", masked_message))
        data["is_fallback"] = False
        return SafetyAlertEmailResult.model_validate(data)
    except Exception as e:
        return _fallback_safety_alert(request_data, f"Lỗi gọi Gemini API: {str(e)}")