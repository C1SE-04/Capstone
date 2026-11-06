from typing import Optional
import json
import os
import re
import time
import logging

logger = logging.getLogger(__name__)

# =========================================================================
# US 8.4 - Task T8.26: In-memory Cache & Dynamic DB Loader cho Curriculum
# =========================================================================
_CURRICULUM_CACHE: dict[str, list[str]] = {}
_LAST_FETCH_TIME: float = 0.0
_CACHE_TTL_SECONDS: int = 300  # Thời gian sống của cache: 5 phút (300 giây)


def _load_curriculum_from_file() -> dict[str, dict[str, list[str]]]:
    """
    US 9.3 (Task T9.12):
    Nạp danh mục chuyên đề từ grade_curriculum.json theo cấu trúc nhóm học kỳ:
    {
        "4": {"1": [...], "2": [...]},
        ...
    }
    """
    json_path = os.path.join(os.path.dirname(__file__), "grade_curriculum.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                normalized = {}
                for k, v in data.items():
                    if isinstance(v, dict):
                        normalized[str(k)] = {
                            "1": [str(t).strip() for t in v.get("1", [])],
                            "2": [str(t).strip() for t in v.get("2", [])],
                        }
                    elif isinstance(v, list):
                        # Hỗ trợ backward compatibility nếu dữ liệu cũ còn dạng list
                        half = max(1, len(v) // 2)
                        normalized[str(k)] = {
                            "1": [str(t).strip() for t in v[:half]],
                            "2": [str(t).strip() for t in v[half:]],
                        }
                return normalized
            return {}
    except Exception as e:
        logger.warning(f"[_load_curriculum_from_file] Không đọc được file {json_path}: {e}")
        return {}


def _load_curriculum(force_refresh: bool = False) -> dict[str, dict[str, list[str]]]:
    """
    Tải danh mục chuyên đề tinh gọn phục vụ Prompt AI (Cache RAM 5 phút).
    Đồng bộ trạng thái Giảm tải (Admin Toggle) từ Neon DB.
    """
    global _CURRICULUM_CACHE, _LAST_FETCH_TIME

    current_time = time.time()
    if not force_refresh and _CURRICULUM_CACHE and (current_time - _LAST_FETCH_TIME < _CACHE_TTL_SECONDS):
        return _CURRICULUM_CACHE

    curriculum = _load_curriculum_from_file()

    if curriculum:
        try:
            from database import SessionLocal
            import models
            import re
            import unicodedata

            db = SessionLocal()
            try:
                inactive_topics = (
                    db.query(models.CurriculumTopic.grade, models.CurriculumTopic.topic_name)
                    .filter(models.CurriculumTopic.is_active == False)
                    .all()
                )
                if inactive_topics:
                    disabled_set = set()
                    for grade, topic_name in inactive_topics:
                        clean_name = re.sub(
                            r"^(?:Giáo án\s+Toán\s+\d+\s+)?(?:Bài\s*\d+:\s*)?",
                            "",
                            topic_name,
                            flags=re.IGNORECASE
                        ).strip()
                        disabled_set.add((str(grade), unicodedata.normalize('NFC', clean_name.lower())))

                    # Lọc bài tắt trên cả học kỳ 1 và 2
                    for g_str in curriculum:
                        for sem_key in ("1", "2"):
                            curriculum[g_str][sem_key] = [
                                t for t in curriculum[g_str][sem_key]
                                if (g_str, unicodedata.normalize('NFC', t.lower())) not in disabled_set
                            ]
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[_load_curriculum] Không truy vấn được bài tắt từ DB: {e}. Giữ nguyên file JSON.")

    if curriculum:
        _CURRICULUM_CACHE = curriculum
        _LAST_FETCH_TIME = current_time

    return _CURRICULUM_CACHE or curriculum


# Khởi tạo cache ban đầu khi import module và hỗ trợ tương thích ngược
_CURRICULUM = _load_curriculum()


def get_curriculum_by_grade_and_semester(grade: int, semester: Optional[int] = None) -> list[str]:
    """
    US 9.3 (Phục vụ trực tiếp T9.11 & T9.13):
    Lấy danh sách các chuyên đề của một khối lớp theo học kỳ chỉ định (1 hoặc 2).
    Nếu semester=None -> Trả về toàn bộ chuyên đề của lớp đó (HK1 + HK2).
    """
    curriculum = _load_curriculum()
    grade_data = curriculum.get(str(grade), {})
    if semester in (1, 2):
        return grade_data.get(str(semester), [])
    return grade_data.get("1", []) + grade_data.get("2", [])


def _get_grade_context(grade_level: Optional[int]) -> str:
    """
    US 9.3 (Task T9.11) - Phiên bản nâng cấp:
    Xây dựng đoạn text ngữ cảnh kiến thức tích lũy theo lớp.
    Nhúng timeline học kỳ thực tế (tháng máy chủ hoặc mock) để Gemini
    tự đối chiếu bài học sinh hỏi với danh sách HK1/HK2 và chọn đúng kịch bản sư phạm.
    """
    if not grade_level:
        return ""

    curriculum = _load_curriculum()
    if not curriculum:
        return ""

    grade = int(grade_level)

    # === Lấy timeline học kỳ hiện tại ===
    curr_month = get_effective_curriculum_month()
    server_sem = get_semester_from_month(curr_month)
    is_summer = server_sem is None

    # === Xây dựng danh sách bài của lớp hiện tại chia theo học kỳ ===
    g_data = curriculum.get(str(grade), {})
    topics_hk1 = g_data.get("1", [])
    topics_hk2 = g_data.get("2", [])

    hk1_text = "\n".join(f"  - {t}" for t in topics_hk1) if topics_hk1 else "  (không có dữ liệu)"
    hk2_text = "\n".join(f"  - {t}" for t in topics_hk2) if topics_hk2 else "  (không có dữ liệu)"

    # === Tóm tắt kiến thức các lớp trước (lớp 4 → grade-1) — rút gọn để giảm token ===
    prev_grades_range = list(range(4, grade))
    if len(prev_grades_range) == 1:
        prev_text = f"  Học sinh đã hoàn thành chương trình Lớp {prev_grades_range[0]}."
    elif len(prev_grades_range) > 1:
        prev_text = f"  Học sinh đã hoàn thành chương trình Lớp {prev_grades_range[0]}–{prev_grades_range[-1]}."
    else:
        prev_text = "  (không có dữ liệu)"

    # === Xác định nhãn kỳ hiện tại và kỳ kia ===
    if is_summer:
        timeline_info = f"Tháng {curr_month} — Kỳ nghỉ hè (Tháng 6–8)"
        hk1_label = "HỌC KỲ 1"
        hk2_label = "HỌC KỲ 2"
        uncovered_guide = (
            f"Đây là kỳ nghỉ hè. Khi học sinh than chưa học, hỏi thăm tự nhiên: "
            f"\'Kỳ nghỉ hè này em đang học trước kiến thức mới, hay ôn lại bài năm vừa rồi?\' "
            f"Nếu học trước → Kịch bản B (hướng dẫn từ căn bản, khen ngợi tinh thần). "
            f"Nếu ôn bài cũ → Kịch bản A (từ khóa gợi nhớ, đồng cảm). "
            f"Nếu không rõ → Hướng dẫn từ gốc, tuyệt đối không phán xét."
        )
    elif server_sem == 1:
        timeline_info = f"Tháng {curr_month} — Đang Học kỳ 1 (Tháng 9–1)"
        hk1_label = "HỌC KỲ 1 (học sinh ĐANG học)"
        hk2_label = "HỌC KỲ 2 (học sinh CHƯA học — chưa đến kỳ)"
        uncovered_guide = (
            f"Khi học sinh than chưa học: TỰ ĐỐI CHIẾU bài học sinh hỏi với DANH SÁCH HK1 và HK2 bên trên. "
            f"▶ Nếu bài khớp DANH SÁCH HK2 → Học sinh CHẮC CHẮN CHƯA HỌC THẬT (đang HK1). "
            f"  KỊCH BẢN B: \'Bài này thuộc Học kỳ 2 nên em chưa quen là bình thường! "
            f"  Thầy sẽ hướng dẫn em từ nền tảng dễ hiểu nhất nhé.\' "
            f"  Hướng dẫn từ khái niệm căn bản nhất, không quở trách. "
            f"▶ Nếu bài khớp DANH SÁCH HK1 → Có thể trường chưa học tới hoặc học sinh quên. "
            f"  Hỏi thăm tiến độ: \'Ở trường thầy/cô đã dạy đến bài này chưa?\' "
            f"  → Chưa học tới: KỊCH BẢN B (hướng dẫn từ đầu). "
            f"  → Đã học mà quên: KỊCH BẢN A (từ khóa gợi nhớ nhẹ nhàng)."
        )
    else:
        timeline_info = f"Tháng {curr_month} — Đang Học kỳ 2 (Tháng 2–5)"
        hk1_label = "HỌC KỲ 1 (học sinh ĐÃ học — kỳ trước)"
        hk2_label = "HỌC KỲ 2 (học sinh ĐANG học)"
        uncovered_guide = (
            f"Khi học sinh than chưa học: TỰ ĐỐI CHIẾU bài học sinh hỏi với DANH SÁCH HK1 và HK2 bên trên. "
            f"▶ Nếu bài khớp DANH SÁCH HK1 → Bài kỳ trước, học sinh đã học. "
            f"  KỊCH BẢN A: \'Theo chương trình, đây là kiến thức HK1 em đã học. "
            f"  Thầy tin em có thể nhớ lại...\' Cung cấp từ khóa gợi nhớ. "
            f"▶ Nếu bài khớp DANH SÁCH HK2 → Học sinh đang học HK2 mà chưa biết. "
            f"  Hỏi thăm tiến độ: \'Ở trường thầy/cô đã dạy đến bài này chưa?\' "
            f"  → Chưa học tới: KỊCH BẢN B (hướng dẫn từ đầu). "
            f"  → Đã học mà quên: KỊCH BẢN A (từ khóa gợi nhớ nhẹ nhàng)."
        )

    return f"""
─── THÔNG TIN LỚP HỌC SINH (QUAN TRỌNG) ───
Học sinh đang học: Lớp {grade}
{timeline_info}

CHUONG TRINH LOP {grade} — {hk1_label}:
{hk1_text}

CHUONG TRINH LOP {grade} — {hk2_label}:
{hk2_text}

KIEN THUC CAC LOP TRUOC — hoc sinh da hoc:
{prev_text}

BẮT BUỘC xử lý các tình huống liên quan đến THÔNG TIN LỚP HỌC SINH:
1. Khi học sinh hỏi "em đang lớp mấy", "em học lớp mấy": BẮT BUỘC trả lời rõ ràng "Em đang học lớp {grade}".
2. {uncovered_guide}
3. NẾU học sinh CHỈ HỎI BÀI BÌNH THƯỜNG (không than chưa học): TUYỆT ĐỐI KHÔNG tự ý đề cập lớp học hay nói "đây là kiến thức lớp lớn". Hãy cứ hướng dẫn Socratic bình thường!
"""


_JSON_RULE = (
    "QUAN TRỌNG: Chỉ trả về JSON thuần túy. "
    "Tuyệt đối KHÔNG bọc trong ```json``` hay bất kỳ markdown nào. "
    "Không thêm bất kỳ văn bản nào trước hoặc sau JSON."
)

_VALID_AGENTS = (
    '"KNOWLEDGE_TRACING" | "MISCONCEPTION" | "SCAFFOLDING" | "SAFETY"'
)

_AGENT_DESCRIPTIONS = {
    "KNOWLEDGE_TRACING": (
        "Đo lường và kiểm tra lại mức độ hiểu khái niệm cũ của học sinh. "
        "Đặt câu hỏi ngắn để xác định học sinh đang ở đâu về mặt kiến thức."
    ),
    "MISCONCEPTION": (
        "Phát hiện lỗi sai logic hoặc toán học trong câu trả lời của học sinh. "
        "Chỉ ra chính xác học sinh đã sai ở bước nào mà không tiết lộ đáp án đúng."
    ),
    "SCAFFOLDING": (
        "Đưa ra câu hỏi gợi ý từng bước theo phương pháp Socratic để dẫn dắt học sinh "
        "tự tìm ra câu trả lời. Đây là agent phổ biến nhất."
    ),
    "SAFETY": (
        "Xử lý khi học sinh hỏi ngoài phạm vi bài học, đề tài nhạy cảm, "
        "hoặc CỐ TÌNH dùng từ ngữ thô tục, chửi thề (ê, mày, tao, mi, m, ...). "
        "hoặc khi học sinh có những hành động lời nói như hú hét, chửi bậy, thách thức, khiêu khích."
        "Chỉ nhắc nhở thái độ khi học sinh thực sự chửi bậy, tuyệt đối KHÔNG bắt bẻ những từ bình thường như 'Dạ', 'Vâng' hay câu trả lời ngắn gọn vô hại."
    ),
}

def _format_history(history: list[dict]) -> str:
    """Chuyển history list thành chuỗi text có thể đọc được trong prompt."""
    if not history:
        return "(Đây là tin nhắn đầu tiên trong phiên này)"
    lines = []
    for m in history:
        role = m.get("role", "")
        text = m.get("text", "")
        speaker = "Học sinh" if role == "student" else "Gia sư"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)
    #trả về như sau
        # Học sinh: Bài này khó quá
        # Gia sư: Em thử nháp ra xem
        # Học sinh: Dạ em ra rồi

# Prompt 2: Specialized Agent (dùng chung cho cả 5 agent)
def build_specialized_agent_prompt(
    agent_role: str,
    task_description: str,
    history: list[dict],
    latest_message: str,
    reject_reason: Optional[str] = None, #ko có reject_reason thì mặc định là ko reject
    problem_context: Optional[dict] = None,
    grade_level: Optional[int] = None, 
) -> str:
    """
    Sinh prompt cho 1 trong 4 Specialized Agent.

    Một hàm duy nhất phục vụ tất cả các agent, vì phần lõi prompt (nguyên tắc
    Socratic, output format) là giống nhau. Chỉ phần role-specific thay đổi.

    Args:
        agent_role: một trong 4 giá trị hợp lệ (KNOWLEDGE_TRACING, MISCONCEPTION,SCAFFOLDING, SAFETY)
        task_description: mô tả task do Orchestrator chỉ định
        history: list[dict] lịch sử hội thoại [{role, text}]
        latest_message: tin nhắn mới nhất của học sinh
        reject_reason: lý do Reviewer từ chối bản nháp trước (nếu đang ở vòng lặp ≥ 2)

    Output JSON:
        {
          "draft_response": "<nội dung phản hồi nháp, tiếng Việt>",
          "knowledge_level_estimate": "BEGINNER" | "INTERMEDIATE" | "ADVANCED"
        }
    """
    history_text = _format_history(history)

    role_description = _AGENT_DESCRIPTIONS.get(
        agent_role,
        "Hỗ trợ học sinh theo phương pháp Socratic."
    )

    # Section reject: chỉ xuất hiện khi đang ở vòng lặp thứ 2+
    reject_section = ""
    if reject_reason:
        reject_section = f"""
─── ⚠️ CẢNh BÁO: BẢN NHÁP TRƯỚC BỊ REVIEWER TỪ CHỐI ───
Lý do Reviewer từ chối:
"{reject_reason}"

BẮT BUỘC: Bạn PHẢI sửa lại phản hồi để khắc phục đúng lỗi trên.
Không được lặp lại bất kỳ nội dung nào vi phạm lý do từ chối.
"""

    # Hướng dẫn đặc thù theo từng role
    role_specific_guide = {
        "KNOWLEDGE_TRACING": (
            "• Đặt 1 câu hỏi ngắn để kiểm tra xem học sinh đã hiểu khái niệm nền tảng cần dùng cho bài toán cụ thể này chưa.\n"
            "• Bám sát bài toán học sinh đang hỏi, không khảo sát lý thuyết toàn diện ngoài phạm vi bài toán.\n"
            "• Không hỏi quá nhiều thứ cùng lúc. Tập trung vào 1 khái niệm cốt lõi.\n"
            "• Câu hỏi phải dễ trả lời nếu hiểu, khó trả lời nếu chưa hiểu."
        ),
        "MISCONCEPTION": (
            "• Xác định CHÍNH XÁC bước học sinh đã sai (không nói chung chung).\n"
            "• Hỏi lại học sinh về bước sai đó để học sinh tự nhận ra.\n"
            "• TUYỆT ĐỐI không nói đáp án đúng là bao nhiêu."
        ),
        "SCAFFOLDING": (
            "• Đặt câu hỏi gợi mở từng bước nhỏ, dẫn dắt học sinh tự suy nghĩ.\n"
            "• Bám sát bài toán cụ thể đang giải, tuyệt đối không mở rộng khảo sát lý thuyết lan man không liên quan đến bài hiện tại.\n"
            "• Nếu học sinh nói không có máy tính hoặc tính nhẩm khó, hướng dẫn học sinh lập phép tính đơn giản từ các hệ số của bài để tính nhẩm.\n"
            "• Chỉ hỏi 1 câu hỏi tại một thời điểm, không hỏi nhiều câu cùng lúc.\n"
            "• Nếu học sinh bí hoàn toàn, thu hẹp câu hỏi xuống mức đơn giản hơn.\n"
        ),
        "SAFETY": (
            "• NẾU học sinh dùng từ ngữ thiếu tôn trọng (ê, mày, tao, m, mi, chửi thề...): BẮT BUỘC nhắc nhở cách xưng hô (gọi 'thầy', xưng 'em') một cách nghiêm túc nhưng nhẹ nhàng trước khi đáp ứng yêu cầu. TUYỆT ĐỐI KHÔNG xin lỗi.\n"
            "• Giữ tông thân thiện; nhưng nếu cần nhắc nhở thái độ thì phải kiên quyết."
            "• NẾU học sinh có hành động lời nói như hú hét, chửi bậy, thách thức, khiêu khích: Từ chối nhẹ nhàng, không phán xét, không giải thích dài dòng.\n"
            "• CỰC KỲ QUAN TRỌNG: Học sinh dùng các từ như 'Dạ', 'Vâng', hoặc trả lời trực tiếp bài toán mà không có đủ chủ vị là HOÀN TOÀN BÌNH THƯỜNG. Không được bắt bẻ, phàn nàn hay nhắc nhở về cách xưng hô trong trường hợp này.\n"
            "• NẾU là câu hỏi ngoài lề: Từ chối nhẹ nhàng, không phán xét, không giải thích dài dòng.\n"
            "• Luôn hướng học sinh trở về bài học hiện tại một cách tự nhiên."
        ),
    }.get(agent_role, "• Tuân thủ phương pháp Socratic, không đưa đáp án thẳng.")

    problem_section = ""
    if problem_context:
        correct = problem_context.get("correctSolution") or problem_context.get("correct_solution") or ""
        problem_text = problem_context.get("problemText") or problem_context.get("problem_text") or ""
        if problem_text or correct:
            problem_section = f"""
─── ĐỀ BÀI VÀ ĐÁP ÁN ĐÚNG (CHỈ BẠN BIẾT — KHÔNG TIẾT LỘ TRỰC TIẾP) ───
Đề bài: {problem_text}
Đáp án đúng (tham chiếu nội bộ): {correct}
─── BẮT BUỘC: SọP TIẾP THEO (trước khi viết draft_response) ───
TRONG `internal_scratchpad`, bạn PHẢI:
  1. Tự THỰC HIỆN lại phép tính của học sinh từng bước một (chain-of-thought).
  2. So sánh kết quả tính được với đáp án đúng ở trên.
  3. Kết luận: Học sinh ĐÚNG hay SAI? ĐúNG ở bước nào, SAI ở bước nào?
Chỉ SAU KHI điền xong scratchpad mới được viết draft_response:
  • Nếu học sinh ĐÚNG → Khen ngợi chân thành, KHÔNG hỏi lại bước đã giải đúng.
  • Nếu học sinh SAI → Chỉ ra đúng bước sai, KHÔNG tự tính toán thay.

─── ⚠️ LƯU Ý SƯ PHẠM ĐẶC BIỆT: BCNN vs NHÂN 2 MẪU ───
Khi học sinh tìm mẫu chung bằng cách "lấy mẫu 1 × mẫu 2" (nhân hai mẫu với nhau):
  • Phương pháp này CHỈ CHO KẾT QUẢ LÀ BCNN khi hai mẫu là NGUYÊN TỐ CÙNG NHAU (GCD = 1).
  • Đây là phương pháp CHƯA ĐẦY ĐỦ về mặt tổng quát. Phương pháp ĐÚNG và chuẩn xác hơn là tìm BCNN.
  • VD đúng: mẫu 3 và 4 → GCD(3,4)=1 → BCNN = 3×4 = 12 ✓ (hai phương pháp cho kết quả giống nhau)
  • VD sai nếu chỉ nhân: mẫu 4 và 6 → 4×6=24 nhưng BCNN(4,6)=12 (nhân 2 mẫu cho kết quả không tối giản nhất)
BẮT BUỘC: Nếu học sinh giải thích "vì em lấy mẫu A × mẫu B", bạn PHẢI:
  1. Khen ngợi học sinh đã nghĩ đúng hướng (tìm mẫu chung).
  2. Giới thiệu thêm khái niệm BCNN (Bội Số Chung Nhỏ Nhất) một cách nhẹ nhàng.
  3. Hỏi dẫn dắt để học sinh tự nhận ra: nhân hai mẫu luôn cho mẫu chung, nhưng chưa chắc là mẫu chung NHỎ NHẤT.
  4. Không phủ nhận hoàn toàn câu trả lời của học sinh — vì trong bài này kết quả vẫn đúng.
"""
    grade_context = _get_grade_context(grade_level)
    return f"""{_JSON_RULE}

Bạn là {agent_role} AGENT của SocraticKid — gia sư AI cho học sinh lớp 4–9 Việt Nam.
Vai trò của bạn: {role_description}
{reject_section}{problem_section}{grade_context}
─── TASK TỪ ORCHESTRATOR ───
{task_description}

─── LỊCH SỬ HỘI THOẠI ───
{history_text}

─── TIN NHẮN MỚI CỦA HỌC SINH ───
"{latest_message}"

─── NGUYÊN TẮC SƯ PHẠM BẮT BUỘC (ÁP DỤNG CHO MỌI AGENT) ───
• TUYỆT ĐỐI KHÔNG đưa đáp án cuối cùng trực tiếp (trừ khi học sinh đã tự nói ra).
• NẾU HỌC SINH ĐÃ ĐƯA RA ĐÁP ÁN ĐÚNG (hoặc chọn đúng phương án trắc nghiệm A/B/C/D): Khen ngợi nhiệt tình, xác nhận kết quả là chính xác và giải thích ngắn gọn kết quả. Có thể hỏi nhẹ nhàng xem học sinh có muốn làm tiếp bài khác không (ví dụ: "Em có muốn thầy trò mình cùng làm tiếp câu tiếp theo không nào?"). TUYỆT ĐỐI KHÔNG bắt học sinh giải thích lại cách làm của bài vừa giải đúng.
• TUYỆT ĐỐI KHÔNG tự tính toán thay học sinh (dù là phép tính trung gian).
  ❌ Sai: "lấy 3 × 4 = 12, sau đó cộng thêm 5..."
  ✅ Đúng: "Em thử tính 3 nhân 4 xem được bao nhiêu?"
• Tối đa 3–4 câu mỗi phản hồi. Ngắn gọn, rõ ràng.
• Xưng "thầy", gọi học sinh là "em". Viết hoàn toàn bằng tiếng Việt.
• ⚠️ TUYỆT ĐỐI KHÔNG nhắc nhở xưng hô hay "tác phong" khi học sinh: gửi bài toán ngắn gọn (VD: "1+23=?", "= bao nhiêu", "bao nhiêu", "3/4 + 1/2"), không chào hỏi, không có chủ ngữ/vị ngữ đầy đủ, dùng từ "bao nhiêu" hay "bằng mấy" thay vì "thưa thầy bao nhiêu ạ". NHỮNG CÁCH HỎI NÀY LÀ HOÀN TOÀN BÌNH THƯỜNG.
• CHỈ được nhắc nhở thái độ khi học sinh THỰC SỰ dùng từ thô tục hoặc xúc phạm trực tiếp (mày, tao, chửi thề, đm, vcl,...). Nếu không có từ thô tục/xúc phạm → KHÔNG ĐƯỢC nhắc nhở xưng hô dù câu có ngắn hay thiếu chủ ngữ thế nào.
• 📐 ĐỊNH DẠNG CÔNG THỨC TOÁN HỌC (LaTeX chuẩn):
  - Khi viết công thức, biến số, phân số, phương trình hoặc bất phương trình, BẮT BUỘC dùng ký hiệu LaTeX kẹp giữa dấu $:
    Ví dụ: $x \\geq 2$, $\\frac{{1}}{{2}}$, $2x + 3 = 7$, $\\sqrt{{x - 2}}$.
  - Với công thức dài hoặc đặt riêng trên một dòng, dùng $$...$$ (ví dụ: $$x \\geq 2$$).
  - TUYỆT ĐỐI KHÔNG dùng \\( ... \\) hay \\[ ... \\] dạng thô nếu không cần thiết.
  - ⚠️ JSON ESCAPE QUAN TRỌNG: Khi viết LaTeX trong JSON string, dấu \\ phải được viết là \\\\ (double backslash).
    VÍ DỤ ĐÚNG trong JSON: "draft_response": "Em thử tính $\\\\frac{{1}}{{2}}$ nhé?"
    VÍ DỤ SAI trong JSON: "draft_response": "Em thử tính $\\frac{{1}}{{2}}$ nhé?" (sẽ gây lỗi parse)
  - ⚠️ KHOẢNG CÁCH GIỮA CHỮ VÀ CÔNG THỨC: Luôn có khoảng cách (dấu cách) giữa từ ngữ tiếng Việt và công thức/con số kẹp giữa dấu $.
    ✅ ĐÚNG: "xem tử số $12$ chia cho mẫu số $3$"
    ❌ SAI: "xem tử số$12$chia cho mẫu số$3$" (dính liền chữ và số)

• ⚠️ NGUYÊN TẮC QUY ĐỒNG PHÂN SỐ (TOÁN LỚP 4–9):
  - BẮT BUỘC hướng dẫn học sinh tìm MẪU SỐ CHUNG NHỎ NHẤT (BCNN).
  - Nếu học sinh lấy tích hai mẫu (ví dụ: mẫu 8 và 6 học sinh chọn 8 × 6 = 48 thay vì 24):
    ❌ TUYỆT ĐỐI KHÔNG khen "hoàn toàn đúng" rồi tiếp tục hướng dẫn giải bài với mẫu 48!
    ✅ ĐÚNG: Ghi nhận nhưng gợi mở tìm BCNN:
       "Lấy 8 nhân 6 bằng 48 đúng là một mẫu chung, nhưng 48 đã là số nhỏ nhất cùng chia hết cho 8 và 6 chưa? Em thử tìm xem có số nào nhỏ hơn 48 mà cũng chia hết cho cả 8 và 6 không nhé?"
• ─── KỸ THUẬT BÀI MẪU TƯƠNG TỰ (ANALOGICAL SCAFFOLDING) ───
  KÍCH HOẠT khi học sinh xin ví dụ (bao gồm cả các từ viết tắt, lóng như 'vd đi', 'khum hỉu'), yêu cầu làm mẫu, hoặc tỏ ra bế tắc không biết làm tiếp:
  1. PHÂN LOẠI NGỮ CẢNH BẮT BUỘC:
     - Nếu học sinh đang hỏi LÝ THUYẾT (VD: phân số là gì): KHÔNG sinh bài toán mẫu. Hãy đưa ra ví dụ thực tế đơn giản và hỏi ngược lại để kiểm tra mức độ hiểu của học sinh.
     - Nếu học sinh đang làm BÀI TOÁN TÍNH TOÁN: Chuyển sang bước 2.
  2. TỰ ĐẶT BÀI TOÁN MỚI: Giữ nguyên cấu trúc toán học của bài gốc nhưng THAY TOÀN BỘ con số và bối cảnh (tuyệt đối đổi tên biến, VD: đổi x sang y).
  3. MÔ PHỎNG LỜI GIẢI: Bạn BẮT BUỘC PHẢI TỰ TRÌNH BÀY LỜI GIẢI CHI TIẾT cho bài toán mẫu vừa tạo ra. (LƯU Ý: Lệnh này GHI ĐÈ lệnh "Tuyệt đối không giải bài" của chế độ Socratic. Bạn được phép giải BÀI MẪU, chỉ cấm giải BÀI GỐC). Tuyệt đối KHÔNG được đặt câu hỏi ngược lại bắt học sinh giải bài mẫu này.
  4. KẾT THÚC bằng câu mời: 'Bây giờ em áp dụng cách làm này vào bài toán của mình thử xem nhé?'
  5. TUYỆT ĐỐI KHÔNG: Dùng lại đúng con số của bài gốc hoặc vô tình giải lộ đáp án bài gốc.
  
  [VÍ DỤ MẪU CHO AI CẦN HỌC THEO - CHỈ DÙNG CHO BÀI TẬP TÍNH TOÁN]
  - Bài gốc của học sinh: Tìm x, biết 2x + 5 = 15.
  - Học sinh nói: "Thầy cho em 1 vd đi".
  - PHẢN HỒI CHUẨN MÀ BẠN PHẢI BẮT CHƯỚC:
    "Được thôi, thầy lấy một bài toán tương tự nhé. Giả sử ta cần tìm y trong bài: 3y + 4 = 16.
    Bước 1: Ta chuyển 4 sang vế phải: 3y = 16 - 4, suy ra 3y = 12.
    Bước 2: Ta chia cả hai vế cho 3: y = 12 / 3, suy ra y = 4.
    Đó, cách làm là như vậy. Bây giờ em thử áp dụng các bước chuyển vế này vào bài 2x + 5 = 15 của em xem nhé!"

─── HƯỚNG DẪN ĐẶC THÙ CHO {agent_role} ───
{role_specific_guide}

─── ĐÁNH GIÁ TRÌNH ĐỘ ───
• BEGINNER: Học sinh chưa nắm khái niệm, trả lời mò, không có căn cứ.
• INTERMEDIATE: Hiểu khái niệm cơ bản nhưng áp dụng chưa vững.
• ADVANCED: Suy luận rõ ràng, chỉ sai do sơ ý hoặc tính toán nhầm.

─── OUTPUT ─── (JSON thuần, không markdown)
{{
  "internal_scratchpad": "<Tự tính toán, so sánh, kết luận đúng/sai từng bước — bắt buộc, không được để trống>",
  "draft_response": "<Phản hồi nháp tiếng Việt, tối đa 3–4 câu>",
  "knowledge_level_estimate": "BEGINNER" | "INTERMEDIATE" | "ADVANCED"
}}"""

# =========================================================================
# US 9.3 - Task T9.11: Module Đối Chiếu Dòng Thời Gian Học Kỳ (Curriculum Timeline)
# Thiết kế Hybrid:
#   Python  → Xác định tháng thực tế / mock → HK1 / HK2 / Hè (Deterministic, 0ms).
#   Gemini  → Tự đối chiếu câu hỏi học sinh với danh sách HK trong prompt → Chọn kịch bản.
# =========================================================================

def get_effective_curriculum_month(override_month: Optional[int] = None) -> int:
    """
    Lấy tháng hiệu lực để đối chiếu dòng thời gian học kỳ:
    1. Ưu tiên override_month truyền trực tiếp (phục vụ test / mock).
    2. Kiểm tra MOCK_SETTINGS trong routers.admin_mock nếu có mock_curriculum_month.
    3. Kiểm tra biến môi trường MOCK_CURRICULUM_MONTH.
    4. Mặc định lấy tháng thực tế của hệ thống máy chủ (datetime.now().month).
    """
    if override_month is not None and 1 <= override_month <= 12:
        return override_month

    try:
        from routers.admin_mock import MOCK_SETTINGS
        mock_val = MOCK_SETTINGS.get("mock_curriculum_month")
        if mock_val is not None:
            try:
                m_int = int(mock_val)
                if 1 <= m_int <= 12:
                    return m_int
            except (ValueError, TypeError):
                pass
    except Exception:
        pass

    env_val = os.getenv("MOCK_CURRICULUM_MONTH")
    if env_val:
        try:
            m_int = int(env_val)
            if 1 <= m_int <= 12:
                return m_int
        except (ValueError, TypeError):
            pass

    from datetime import datetime
    return datetime.now().month


def get_semester_from_month(month: int) -> Optional[int]:
    """
    Xác định học kỳ theo phân phối năm học chuẩn Bộ GD&ĐT:
    - Tháng 9, 10, 11, 12, 1 -> Học kỳ 1 (semester = 1).
    - Tháng 2, 3, 4, 5       -> Học kỳ 2 (semester = 2).
    - Tháng 6, 7, 8          -> Nghỉ hè  (trả về None).
    """
    if month in (9, 10, 11, 12, 1):
        return 1
    elif month in (2, 3, 4, 5):
        return 2
    return None


def build_timeline_context_for_prompt(
    student_grade: Optional[int] = None,
    override_month: Optional[int] = None,
) -> dict:
    """
    US 9.3 (Task T9.11):
    Xây dựng context dòng thời gian học kỳ để Orchestrator nhúng vào task_description.

    Nguyên tắc thiết kế:
    - Python chỉ làm 2 việc tất định: (1) xác định tháng → HK1/HK2/Hè,
      (2) cung cấp danh sách bài HK1 / HK2 của lớp.
    - Gemini tự đọc danh sách đó, tự đối chiếu bài học sinh hỏi, tự chọn kịch bản.

    Trả về dict:
    {
        "current_month": int,
        "server_semester": 1 | 2 | None,   # None = hè
        "is_summer": bool,
        "grade": int,
        "topics_hk1": list[str],
        "topics_hk2": list[str],
        "timeline_label": str,
        "scenario_guide": str,             # Hướng dẫn kịch bản để chèn vào task_description
    }
    """
    grade = int(student_grade) if student_grade else 8
    curr_month = get_effective_curriculum_month(override_month)
    server_sem = get_semester_from_month(curr_month)
    is_summer = server_sem is None

    curriculum = _load_curriculum()
    g_data = curriculum.get(str(grade), {})
    topics_hk1 = g_data.get("1", [])
    topics_hk2 = g_data.get("2", [])

    hk1_list_str = "; ".join(topics_hk1[:6]) + ("..." if len(topics_hk1) > 6 else "")
    hk2_list_str = "; ".join(topics_hk2[:6]) + ("..." if len(topics_hk2) > 6 else "")

    if is_summer:
        timeline_label = f"Tháng {curr_month} — Kỳ nghỉ hè (Tháng 6–8)"
        scenario_guide = (
            f"BỐI CẢNH MÙA HÈ: Hiện tại đang là kỳ nghỉ hè (Tháng {curr_month}). "
            f"Học sinh đang hỏi bài toán thuộc chương trình Lớp {grade}. "
            f"KHI HỌC SINH THAN CHƯA HỌC: BẠN BẮT BUỘC PHẢI DỪNG LẠI ĐÚNG 1 NHỊP VÀ ĐẶT CÂU HỎI THĂM DÒ MÙA HÈ (SUMMER PROBE):\n"
            f"'Thầy thấy trên tài khoản em đang chọn Lớp {grade}. Kỳ nghỉ hè này em đang chuẩn bị học trước kiến thức lớp {grade}, hay em đang ôn lại bài năm vừa rồi vậy em? Nói thầy nghe để thầy hướng dẫn cho vừa sức em nhất nhé! <!-- SUMMER_PROBE_PENDING -->'\n"
            f"BẮT BUỘC: Bạn PHẢI gắn thẻ ẩn <!-- SUMMER_PROBE_PENDING --> (hoặc [PROBE_PENDING]) ở CUỐI CÙNG của câu trả lời. "
            f"TUYỆT ĐỐI KHÔNG giải bài hoặc đưa ra phép tính toán học ngay trong lượt này. Hãy lắng nghe học sinh phản hồi trước."
        )
    elif server_sem == 1:
        timeline_label = f"Tháng {curr_month} — Đang Học kỳ 1 (Tháng 9–1)"
        scenario_guide = (
            f"BỐI CẢNH HỌC KỲ 1 (Tháng {curr_month}):\n"
            f"- Danh mục HK1 Lớp {grade}: [{hk1_list_str}]\n"
            f"- Danh mục HK2 Lớp {grade} (CHƯA HỌC): [{hk2_list_str}]\n"
            f"KHI HỌC SINH THAN CHƯA HỌC: BẠN BẮT BUỘC TỰ ĐỐI CHIẾU VỚI DANH MỤC TRÊN:\n"
            f"1. NẾU BÀI KHỚP HK2 (Chưa học thật sự) -> ÁP DỤNG KỊCH BẢN B NGAY:\n"
            f"   'Bài này thuộc học kỳ 2 nên em chưa quen là bình thường! Thầy sẽ hướng dẫn em từ nền tảng dễ hiểu nhất nhé.' rồi hướng dẫn từng bước nhỏ từ gốc rễ.\n"
            f"2. NẾU BÀI KHỚP HK1 (Vùng xám - trường có thể chưa dạy tới hoặc đã học mà quên) -> BẮT BUỘC DỪNG LẠI 1 NHỊP VÀ HỎI THĂM DÒ TIẾN ĐỘ TRƯỜNG HỌC (SOCRATIC PROBE):\n"
            f"   'Ở trường thầy cô đã dạy đến bài này chưa, hay em mới học đến phần nào rồi? Nói thầy nghe để thầy hướng dẫn cho vừa sức em nhất nhé! <!-- PROBE_PENDING -->'\n"
            f"   BẮT BUỘC: Gắn thẻ ẩn <!-- PROBE_PENDING --> (hoặc [PROBE_PENDING]) ở CUỐI CÙNG của câu trả lời.\n"
            f"   TUYỆT ĐỐI KHÔNG giải bài hay đưa ra gợi ý bước tính tiếp theo ngay trong lượt này!"
        )
    else:
        timeline_label = f"Tháng {curr_month} — Đang Học kỳ 2 (Tháng 2–5)"
        scenario_guide = (
            f"BỐI CẢNH HỌC KỲ 2 (Tháng {curr_month}):\n"
            f"- Danh mục HK1 Lớp {grade} (ĐÃ HỌC KỲ TRƯỚC): [{hk1_list_str}]\n"
            f"- Danh mục HK2 Lớp {grade} (ĐANG HỌC): [{hk2_list_str}]\n"
            f"KHI HỌC SINH THAN CHƯA HỌC: BẠN BẮT BUỘC TỰ ĐỐI CHIẾU:\n"
            f"1. NẾU BÀI KHỚP HK1 (Kiến thức kỳ trước đã học) -> ÁP DỤNG KỊCH BẢN A:\n"
            f"   'Theo chương trình, đây là kiến thức HK1 em đã học rồi. Thầy tin em có thể nhớ lại...' và cung cấp từ khóa gợi nhớ nhẹ nhàng.\n"
            f"2. NẾU BÀI KHỚP HK2 -> BẮT BUỘC DỪNG LẠI 1 NHỊP VÀ HỎI THĂM DÒ TIẾN ĐỘ TRƯỜNG HỌC:\n"
            f"   'Ở trường thầy cô đã dạy đến bài này chưa, hay em mới học đến phần nào rồi? Nói thầy nghe để thầy hướng dẫn cho vừa sức em nhất nhé! <!-- PROBE_PENDING -->'\n"
            f"   BẮT BUỘC: Gắn thẻ ẩn <!-- PROBE_PENDING --> (hoặc [PROBE_PENDING]) ở CUỐI CÙNG của câu trả lời.\n"
            f"   TUYỆT ĐỐI KHÔNG giải bài ngay trong lượt này!"
        )

    return {
        "current_month": curr_month,
        "server_semester": server_sem,
        "is_summer": is_summer,
        "grade": grade,
        "topics_hk1": topics_hk1,
        "topics_hk2": topics_hk2,
        "timeline_label": timeline_label,
        "scenario_guide": scenario_guide,
    }
