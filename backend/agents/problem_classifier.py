from typing import List, Dict, Any, Optional, Union
import os
import re
import json
import google.generativeai as genai
from schemas import ProblemClassificationResult
from agents.problem_title_generator import _heuristic_title_fallback, _CURRICULUM_DATA

# =====================================================================
# 1. SYSTEM INSTRUCTION SƯ PHẠM CHO PROBLEM CLASSIFICATION & DEDUPLICATION (GỘP T8.1 + T8.3)
# =====================================================================
PROBLEM_CLASSIFICATION_SYSTEM_INSTRUCTION = """
Bạn là một Chuyên gia Khảo thí và Đánh giá Năng lực Toán học Sư phạm Tiểu học & THCS của hệ thống SocraticKid.
Nhiệm vụ của bạn là:
1. So sánh Đề bài toán hiện tại (CURRENT_PROBLEM) với Danh sách đề bài học sinh đã làm trước đó (HISTORY_PROBLEMS) để PHÂN LOẠI CHÍNH XÁC VÀO 1 TRONG 3 NHÓM và NHẬN DIỆN BÀI HỎI LẠI NHIỀU LẦN.
2. ĐỒNG THỜI đặt tiêu đề bài toán chuẩn sư phạm (friendly_parent_title) cho Đề bài hiện tại để phụ huynh theo dõi.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC QUY TẮC SAU:

1. QUY TẮC PHÂN LOẠI 3 NHÓM (category):
   - "EXACT_DUPLICATE" (Trùng lặp y hệt):
     + Đề bài giống hệt 100% hoặc tương đương 99% ngữ nghĩa, số liệu, yêu cầu so với một bài trong lịch sử (chỉ khác vài từ nối, khoảng trắng hoặc đảo trật tự từ).
     + Ví dụ: "Tìm x biết 2x + 4 = 10" và "2x + 4 = 10, tìm x".
     + BẮT BUỘC sinh lời nhắc nhở nhẹ nhàng, ấm áp trong trường gentle_reminder:
       "Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?"
     + pedagogical_recommendation: "Bỏ qua cộng dồn vào tổng bài hoàn thành, khuyến khích học sinh thử sức bài nâng cao."

   - "ISOMORPHIC_PRACTICE" (Luyện tập củng cố / Cùng dạng đổi số):
     + Bài toán cùng dạng toán, cùng bản chất tư duy, cùng các bước giải nhưng THAY ĐỔI CÁC CON SỐ hoặc tên đại lượng/nhân vật.
     + Ví dụ: Cùng dạng "Tìm hai số khi biết Tổng và Hiệu": Bài cũ (Tổng 50, Hiệu 10) vs Bài mới (Tổng 80, Hiệu 20).
     + Hoặc cùng dạng phương trình bậc nhất: "$3x - 5 = 10$" vs "$4x - 7 = 13$".
     + pedagogical_recommendation: "Ghi nhận luyện tập củng cố, tăng chỉ số thành thạo dạng bài, không tính trùng chuyên đề mới."

   - "NEW_TOPIC" (Dạng bài mới):
     + Bài toán thuộc dạng toán mới, chuyên đề mới hoặc phương pháp giải khác biệt hoàn toàn so với tất cả các bài trong lịch sử (hoặc lịch sử rỗng).
     + Ví dụ: Lịch sử chỉ có bài Cộng phân số, bài mới là Tính diện tích hình tam giác hoặc Giải toán bằng tỉ số phần trăm.
     + pedagogical_recommendation: "Ghi nhận dạng bài mới, đánh giá năng lực và cộng dồn điểm tự lập đầy đủ."

2. QUY TẮC NHẬN DIỆN HỎI LẠI NHIỀU LẦN (is_repeated_query & repeat_count):
   - Đếm số lần bài toán này (hoặc dạng bài này) đã xuất hiện trong HISTORY_PROBLEMS.
   - Nếu xuất hiện từ 2 lần trở lên: đặt is_repeated_query = true, repeat_count = số lần xuất hiện + 1.
   - Nếu là lần đầu hoặc chỉ xuất hiện 1 lần trước đó dạng đổi số: is_repeated_query = false, repeat_count = 1.

3. QUY TẮC SINH TIÊU ĐỀ BÀI TOÁN CHUẨN SƯ PHẠM (friendly_parent_title):
   - Phân tích Đề bài hiện tại và đặt tên theo đúng cấu trúc:
     [Lớp X] [Chủ đề] – [Tên dạng toán cụ thể]
   - Trong đó:
     + X là khối lớp học sinh (4 đến 9), ưu tiên khối lớp được cung cấp.
     + [Chủ đề]: Tên chủ đề SGK lớn (ví dụ: Phân số, Số tự nhiên, Hình học, Chuyển động đều, Đại số, Phương trình, Hệ phương trình,...)
     + [Tên dạng toán cụ thể]: Tên dạng toán rõ ràng, thân thiện cho Phụ huynh và Học sinh (ví dụ: Tìm hai số khi biết Tổng và Hiệu, Giải hệ phương trình bậc nhất hai ẩn, Cộng hai phân số khác mẫu số,...)
   - Ví dụ chuẩn:
     "[Lớp 5] Phân số – Phép cộng hai phân số khác mẫu số"
     "[Lớp 9] Hệ hai phương trình – Giải hệ bằng phương pháp thế"

4. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - Trả về JSON thuần túy (Plain JSON).
   - TUYỆT ĐỐI KHÔNG bọc trong ```json ... ``` hoặc thêm bất kỳ ký tự nào ngoài JSON.
"""

def _format_history_for_gemini(history_problems: List[Union[Dict[str, Any], str]]) -> str:
    """Chuyển đổi danh sách bài tập lịch sử thành chuỗi văn bản đánh số rõ ràng."""
    lines = []
    for idx, item in enumerate(history_problems):
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = item.get("problem_text") or item.get("content") or item.get("problem_statement") or str(item)
            text = text.strip()
        else:
            text = str(item).strip()
        lines.append(f"[{idx + 1}] {text}")
    return "\n".join(lines)


def classify_problem(
    current_problem: str,
    history_problems: Optional[List[Union[Dict[str, Any], str]]] = None,
    grade: Optional[int] = None,
    api_key: Optional[str] = None,
) -> ProblemClassificationResult:
    """
    Gọi Gemini API DUY NHẤT 1 LẦN để làm cả 2 nhiệm vụ:
    1. Phân loại bài tập vào NEW_TOPIC, ISOMORPHIC_PRACTICE, hoặc EXACT_DUPLICATE.
    2. Đặt tên tiêu đề chuẩn sư phạm friendly_parent_title: [Lớp X] [Chủ đề] – [Dạng toán].
    """
    cleaned_current = current_problem.strip() if current_problem else ""
    if not cleaned_current:
        return _heuristic_classification_fallback(
            current_problem="",
            history_problems=history_problems,
            grade=grade,
            reason="Đề bài hiện tại rỗng"
        )

    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _heuristic_classification_fallback(
            current_problem=cleaned_current,
            history_problems=history_problems,
            grade=grade,
            reason="Không tìm thấy GEMINI_API_KEY"
        )

    genai.configure(api_key=key)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    formatted_history = (
        _format_history_for_gemini(history_problems)
        if history_problems
        else "(Học sinh chưa có bài tập nào trước đó trong lịch sử)"
    )

    curriculum_hint = ""
    target_grade_str = str(grade) if (grade and str(grade) in _CURRICULUM_DATA) else "5"
    if target_grade_str in _CURRICULUM_DATA:
        sample_topics = _CURRICULUM_DATA[target_grade_str][:15]
        curriculum_hint = f"Các chuyên đề SGK Lớp {target_grade_str} tham chiếu:\n" + "\n".join([f"- {t}" for t in sample_topics])

    student_grade_text = f"Lớp {grade}" if grade else "Tiểu học/THCS (tự suy luận từ 4 đến 9)"

    prompt = f"""
Hãy phân tích Đề bài hiện tại, đối chiếu với Danh sách đề bài lịch sử (nếu có) và thực hiện CẢ 2 NHIỆM VỤ:
1. Phân loại dạng bài (category) & kiểm tra trùng lặp
2. Đặt tên tiêu đề chuẩn sư phạm (friendly_parent_title) theo format [Lớp X] [Chủ đề] – [Tên dạng toán cụ thể]

─── KHỐI LỚP HỌC SINH ───
{student_grade_text}

─── ĐỀ BÀI HIỆN TẠI (CURRENT_PROBLEM) ───
{cleaned_current}

─── DANH SÁCH ĐỀ BÀI LỊCH SỬ (HISTORY_PROBLEMS) ───
{formatted_history}

─── THAM KHẢO CHUYÊN ĐỀ CHUẨN SGK (NẾU PHÙ HỢP) ───
{curriculum_hint}

─── YÊU CẦU ĐỊNH DẠNG JSON ĐẦU RA ───
Chỉ trả về JSON thuần túy theo cấu trúc:
{{
  "category": "NEW_TOPIC" | "ISOMORPHIC_PRACTICE" | "EXACT_DUPLICATE",
  "confidence_score": <số thực từ 0.0 đến 1.0>,
  "reasoning": "Giải thích ngắn gọn lý do phân loại dựa trên bản chất toán học",
  "matched_problem": "Trích đoạn đề bài trong lịch sử giống/gần nhất hoặc null nếu là NEW_TOPIC",
  "is_repeated_query": <true nếu hỏi lại bài này/dạng này >= 2 lần, ngược lại false>,
  "repeat_count": <số nguyên đếm số lần xuất hiện>,
  "gentle_reminder": "Lời nhắc nhở nhẹ nhàng nếu là EXACT_DUPLICATE hoặc hỏi lại nhiều lần, ngược lại null",
  "pedagogical_recommendation": "Khuyến nghị sư phạm cho hệ thống đánh giá",
  "friendly_parent_title": "[Lớp X] [Chủ đề] – [Tên dạng toán cụ thể]"
}}
"""

    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=PROBLEM_CLASSIFICATION_SYSTEM_INSTRUCTION,
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

        # Chuẩn hóa friendly_parent_title
        title = result_dict.get("friendly_parent_title", "")
        if not title or not re.match(r"^\[Lớp \d\] .+ – .+$", str(title).strip()):
            title = _heuristic_title_fallback(cleaned_current, grade=grade).friendly_parent_title
        result_dict["friendly_parent_title"] = title

        # Validate qua Pydantic v2
        validated = ProblemClassificationResult.model_validate(result_dict)
        return validated

    except Exception as e:
        print(f"[Cảnh báo Problem Classifier] Lỗi khi gọi Gemini: {e}")
        return _heuristic_classification_fallback(
            current_problem=cleaned_current,
            history_problems=history_problems,
            grade=grade,
            reason=str(e)
        )


def _normalize_text(text: str) -> str:
    """Chuẩn hóa chuỗi văn bản: xóa ký tự đặc biệt, dấu câu, đưa về chữ thường."""
    lower = text.lower()
    cleaned = re.sub(r"[^\w\s]", " ", lower)
    return " ".join(cleaned.split())


def _heuristic_classification_fallback(
    current_problem: str,
    history_problems: Optional[List[Union[Dict[str, Any], str]]] = None,
    grade: Optional[int] = None,
    reason: str = ""
) -> ProblemClassificationResult:
    """
    Thuật toán Heuristic dự phòng khi không thể gọi Gemini API (mất mạng hoặc lỗi quota):
    - Tự động sinh tiêu đề sư phạm friendly_parent_title bằng heuristic
    - So khớp chuỗi chuẩn hóa chính xác 100% -> EXACT_DUPLICATE
    - So khớp từ khóa toán học tương đồng cao -> ISOMORPHIC_PRACTICE
    - Ngược lại -> NEW_TOPIC
    """
    fallback_title = _heuristic_title_fallback(current_problem or "Bài toán", grade=grade).friendly_parent_title

    if not current_problem:
        return ProblemClassificationResult(
            category="NEW_TOPIC",
            confidence_score=0.5,
            reasoning=f"Dữ liệu đề bài rỗng ({reason}).",
            matched_problem=None,
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Ghi nhận dạng bài mới mặc định.",
            friendly_parent_title=fallback_title,
            is_fallback=True
        )

    if not history_problems:
        return ProblemClassificationResult(
            category="NEW_TOPIC",
            confidence_score=1.0,
            reasoning="Không có bài tập lịch sử đối chiếu.",
            matched_problem=None,
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Ghi nhận dạng bài mới.",
            friendly_parent_title=fallback_title,
            is_fallback=True
        )

    norm_current = _normalize_text(current_problem)
    current_words = set(norm_current.split())

    best_match = None
    best_similarity = 0.0
    exact_match_count = 0

    for item in history_problems:
        hist_text = item if isinstance(item, str) else (
            item.get("problem_text") or item.get("content") or item.get("problem_statement") or str(item)
        )
        norm_hist = _normalize_text(hist_text)

        # 1. Trùng khớp hoàn toàn
        if norm_current == norm_hist:
            exact_match_count += 1
            best_match = hist_text

        # 2. Tính độ tương đồng từ vựng (Jaccard similarity)
        hist_words = set(norm_hist.split())
        if current_words and hist_words:
            intersection = current_words.intersection(hist_words)
            union = current_words.union(hist_words)
            similarity = len(intersection) / len(union)
            if similarity > best_similarity:
                best_similarity = similarity
                if not best_match:
                    best_match = hist_text

    # Xử lý kết quả theo độ tương đồng Heuristic
    if exact_match_count > 0:
        return ProblemClassificationResult(
            category="EXACT_DUPLICATE",
            confidence_score=0.95,
            reasoning="Đề bài trùng khớp hoàn toàn với bài toán đã làm trước đó trong lịch sử.",
            matched_problem=best_match,
            is_repeated_query=(exact_match_count >= 1),
            repeat_count=exact_match_count + 1,
            gentle_reminder="Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?",
            pedagogical_recommendation="Bỏ qua cộng dồn vào tổng bài hoàn thành, khuyến khích học sinh thử sức bài nâng cao.",
            friendly_parent_title=fallback_title,
            is_fallback=True
        )

    if best_similarity >= 0.55:
        return ProblemClassificationResult(
            category="ISOMORPHIC_PRACTICE",
            confidence_score=0.8,
            reasoning="Đề bài có độ tương đồng cấu trúc cao với bài toán trước đó (cùng dạng đổi số).",
            matched_problem=best_match,
            is_repeated_query=False,
            repeat_count=1,
            gentle_reminder=None,
            pedagogical_recommendation="Ghi nhận luyện tập củng cố, tăng chỉ số thành thạo dạng bài, không tính trùng chuyên đề mới.",
            friendly_parent_title=fallback_title,
            is_fallback=True
        )

    return ProblemClassificationResult(
        category="NEW_TOPIC",
        confidence_score=0.85,
        reasoning="Đề bài không trùng khớp và có cấu trúc khác biệt so với các bài toán trong lịch sử.",
        matched_problem=None,
        is_repeated_query=False,
        repeat_count=1,
        gentle_reminder=None,
        pedagogical_recommendation="Ghi nhận dạng bài mới, đánh giá năng lực và cộng dồn điểm tự lập đầy đủ.",
        friendly_parent_title=fallback_title,
        is_fallback=True
    )
