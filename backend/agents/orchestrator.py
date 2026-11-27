import json
import os
import time
import re
import pathlib
import threading
from fractions import Fraction
from typing import Any, Optional, Tuple, TypedDict

import sympy
import joblib


class RoutingResult(TypedDict):
    """Cấu trúc dữ liệu kết quả phân luồng của Orchestrator."""
    selected_agent: str      # "SCAFFOLDING" | "MISCONCEPTION" | "KNOWLEDGE_TRACING" | "SAFETY"
    task_description: str    # Chỉ đạo cụ thể cho agent tiếp theo (< 3 câu)
    routing_scratchpad: str  # Ghi chú suy luận nội bộ
    emotion_flag: str

def _detect_uncovered_claim(message: str) -> bool:
    """
    US 11.6: Nhận diện cơ bản các tín hiệu học sinh than chưa học/bỡ ngỡ
    để hỗ trợ phân luồng nhanh trong Orchestrator sang SCAFFOLDING.
    Toàn bộ ngữ nghĩa sâu, sắc thái tinh tế (teencode, ví von, cô bỏ qua...)
    được giao cho Gemini (LLM) tự đọc hiểu trong prompt mà không gò bó vào từ ngữ.
    """
    msg_lower = message.lower().strip()

    # 1. Bảo vệ chống False Positive: học sinh khẳng định 'không lạ', 'quen rồi', 'biết làm', thuật ngữ tiểu học ('chưa biết') hoặc xin ví dụ
    if re.search(r"(không|ko|chẳng|chả)\s+(thấy\s+)?(lạ|bỡ ngỡ)", msg_lower):
        return False
    if re.search(r"(quen\s+lắm|quen\s+rồi|dễ\s+ợt|biết\s+làm\s+rồi)", msg_lower):
        return False
    if re.search(r"\b(ví dụ|bài mẫu|làm mẫu|giải mẫu|cho mẫu)\b", msg_lower):
        return False

    msg_masked = re.sub(
        r"\b(?:thừa số|số hạng|thành phần|số bị trừ|số trừ|số bị chia|số chia|số)\s+chưa biết\b",
        "",
        msg_lower,
    )

    # 2. Nhận diện các tín hiệu chưa học, lạ lẫm hoặc thầy cô bỏ qua bài
    core_pattern = (
        r"(chưa|chx|không|ko|k|hk|ch)\s+.*(học|hc|dạy|nghe|biết|gặp|thấy|nhìn|đụng|va\s*chạm|sờ|tiếp\s*xúc|nhắc|đả\s*động|nói|quen)|"
        r"\b(lạ|mới\s+toanh|mới\s+tinh|lần\s+đầu|quái\s+lạ|bỏ\s+qua|lướt\s+qua|skip|nhảy\s+cóc|giảm\s+tải)\b|"
        r"\b(chx\s+bh|chx\s+từng|e\s+ch\s+hc)\b"
    )
    return bool(re.search(core_pattern, msg_masked))

    return False

def _normalize_curriculum_text(text: str) -> str:
    """Xóa dấu câu, khoảng trắng thừa để so khớp tên chuyên đề chính xác."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())

def _is_topic_in_active_curriculum(message: str, grade: Optional[int] = None) -> bool:
    """Kiểm tra xem nội dung học sinh đề cập có nằm trong danh mục chuyên đề ĐANG BẬT (active) hay không."""
    try:
        from agents.agent_prompts import _load_curriculum
        curriculum = _load_curriculum()
        if not curriculum:
            return True
        target_grade = int(grade) if grade else 9
        active_topics = []
        for g in range(4, target_grade + 1):
            active_topics.extend(curriculum.get(str(g), []))
        norm_msg = _normalize_curriculum_text(message)
        for topic in active_topics:
            norm_topic = _normalize_curriculum_text(topic)
            if norm_topic and norm_topic in norm_msg:
                return True
        return False
    except Exception:
        return True

def _has_probe_already_completed(history_text: str) -> bool:
    """
    US 9.3 (Task T9.15 - AC 9.3.7 - Tag-based Protocol & Semantic Fallback):
    Kiểm tra xem trong lịch sử phiên chat đã từng diễn ra câu hỏi thăm dò VÀ học sinh đã trả lời chưa.
    - ƯU TIÊN 1: Nhận diện thẻ ẩn [PROBE_PENDING], <!-- PROBE_PENDING --> (chính xác 100%, không phụ thuộc câu chữ).
    - FALLBACK 2: Quét từ khóa/mẫu câu thăm dò truyền thống nếu là tin nhắn cũ chưa có tag.
    Nếu đã hoàn tất, các lượt sau tuyệt đối không hỏi lại câu thăm dò tiến độ trường học/mùa hè nữa.
    """
    if not history_text:
        return False

    blocks = [b.strip() for b in re.split(r'(?im)^(?=\[(?:USER|STUDENT|AGENT|ASSISTANT|MODEL|THẦY)\]|(?:User|Model|Assistant):)', history_text) if b.strip()]
    if not blocks:
        blocks = [l.strip() for l in history_text.split("\n") if l.strip()]

    assistant_prefixes = ("[agent", "[assistant", "[thầy", "[model", "model:", "assistant:")

    # 1. Quét tìm Thẻ ẩn [PROBE_PENDING] / <!-- PROBE_PENDING --> / [SUMMER_PROBE_PENDING]
    probe_tag_signals = ("probe_pending", "socratic_probe", "summer_probe_pending")
    probe_idx = -1
    for i, b in enumerate(blocks):
        b_low = b.lower()
        is_assistant = any(b_low.startswith(p) for p in assistant_prefixes) or ("[agent" in b_low[:15])
        if is_assistant and any(tag in b_low for tag in probe_tag_signals):
            probe_idx = i
            break

    # 2. Fallback đối chiếu từ khóa ngữ nghĩa câu hỏi thăm dò mẫu (nếu AI không có tag)
    if probe_idx == -1:
        probe_signals = (
            "thầy cô đã dạy đến bài",
            "thầy cô đã dạy đến",
            "học đến phần nào rồi",
            "học đến bài nào rồi",
            "đang học đến bài nào",
            "đang học tới bài nào",
            "dạy đến bài này chưa",
            "dạy đến bài",
            "học tới bài này chưa",
            "đã học qua chưa",
            "học qua chưa",
            "thầy cô dạy tới đâu rồi",
            "học trước kiến thức",
            "ôn lại bài năm vừa rồi",
            "chuẩn bị học trước",
            "ôn lại kiến thức cũ",
            "học trước hay ôn lại",
        )
        for i, b in enumerate(blocks):
            b_low = b.lower()
            is_assistant = any(b_low.startswith(p) for p in assistant_prefixes) or ("[agent" in b_low[:15])
            if is_assistant and any(s in b_low for s in probe_signals):
                probe_idx = i
                break

    if probe_idx != -1 and probe_idx < len(blocks) - 1:
        return True

    return False

def _build_task_description(
    agent: str,
    message: str,
    problem_context: Optional[dict] = None,
    student_ans: Optional[str] = None,
    expected_ans: Optional[str] = None,
    safety_subtype: Optional[str] = None,
    student_grade: Optional[int] = None,
    history_text: str = "",
) -> str:
    """
    Tạo task_description có ngữ cảnh bài học và vai trò người thầy.
    """
    problem_text = ""
    if problem_context:
        problem_text = (
            problem_context.get("problemText")
            or problem_context.get("problem_text")
            or ""
        )
    if agent == "SAFETY":
        msg_lower = message.lower()
        # 1. Phát hiện học sinh xưng hô thiếu tôn trọng (mày, tao, thằng, con, bot ngu,...) hoặc chửi thề
        has_disrespect = (
            safety_subtype == "DISRESPECT"
            or any(re.search(rf"\b{re.escape(w)}\b", msg_lower) for w in ("mày", "tao", "mầy", "thằng", "con", "bot ngu", "ông già", "bà già"))
            or any(w in msg_lower for w in ("đm", "vl", "vcl", "chó", "lồn", "cặc", "địt", "đụ", "cút", "mẹ mày"))
        )
        if has_disrespect:
            return (
                f"Học sinh có biểu hiện xưng hô thiếu tôn trọng hoặc vô lễ: '{message[:60]}'. "
                "Bạn là THẦY GIÁO. BẮT BUỘC bạn phải: "
                "1. Nghiêm túc chấn chỉnh và uốn nắn học sinh ngay từ câu đầu tiên: Nhắc học sinh phải xưng hô lễ phép 'thầy - em', tuyệt đối không được xưng 'mày - tao' hay nói chuyện cộc lốc/vô lễ. "
                "2. TUYỆT ĐỐI KHÔNG xưng 'Dạ', không được xin lỗi, không được nịnh nọt học sinh (như khen 'học trò đáng yêu' khi học sinh vừa vô lễ). "
                "3. Yêu cầu học sinh giữ thái độ đúng mực và hỏi học sinh cần hướng dẫn bài toán nào."
            )

        # 2. Phát hiện học sinh hú hét / gọi đùa cộc lốc vô nghĩa ("hú", "la hét", "ú òa", "áaa",...)
        is_shouting = (
            safety_subtype == "SHOUTING"
            or any(s in msg_lower for s in ("hú", "la hét", "hét", "gào", "ú òa", "áaa"))
            or bool(re.match(r"^(h[úu]+|ê+|á+|ủa+|ơ+)$", msg_lower.strip()))
        )
        if is_shouting:
            return (
                f"Học sinh đang hú hét hoặc phát ra tiếng gọi đùa cộc lốc vô nghĩa: '{message[:60]}'. "
                "Bạn là THẦY GIÁO. BẮT BUỘC bạn phải: "
                "1. Nhắc nhở học sinh giữ trật tự và tác phong nghiêm túc: Trong giờ học không được hú hét hay gọi đùa vô nghĩa, cần chào hỏi đàng hoàng, lễ phép. "
                "2. TUYỆT ĐỐI KHÔNG xưng 'Dạ', luôn xưng 'thầy' gọi 'em'. "
                "3. Ân cần hỏi học sinh hôm nay cần thầy hướng dẫn bài toán nào."
            )
        # 3. Off-topic (ngoài lề)
        return (
            f"Học sinh đang giao tiếp ngoài bài học: '{message[:60]}'. "
            "Bạn là THẦY GIÁO (xưng thầy, gọi em, tuyệt đối không xưng 'Dạ'). "
            "Hãy từ chối chuyện ngoài lề một cách nhã nhặn, giữ phong thái người thầy mẫu mực và hướng dẫn học sinh tập trung vào bài học."
        )

    if _detect_uncovered_claim(message):
        # US 9.3 (Task T9.15 - AC 9.3.7): Kiểm tra xem phiên chat này đã từng thăm dò tiến độ chưa
        # Nếu ĐÃ THĂM DÒ XONG -> Tuyệt đối không hỏi lại lần 2
        if history_text and _has_probe_already_completed(history_text):
            return (
                f"HỌC SINH TIẾP TỤC BỐI RỐI HOẶC THAN CHƯA HỌC: '{message[:80]}'.\n"
                f"LƯU Ý QUAN TRỌNG (CHỐNG LẶP LẠI THĂM DÒ - AC 9.3.7):\n"
                f"1. Bạn ĐÃ HỎI thăm dò tiến độ ở lượt trước và học sinh đã trả lời rồi. "
                f"TUYỆT ĐỐI KHÔNG HỎI LẠI câu 'Ở trường thầy cô đã dạy đến chưa' hay 'hiện tại đang học đến bài nào' lần thứ 2!\n"
                f"2. BẮT BUỘC tiếp tục dẫn dắt Socratic theo KỊCH BẢN B: Hãy hạ thấp rào cản thêm một nấc nữa, "
                f"tuyệt đối KHÔNG lặp lại câu hỏi toán học vừa hỏi ở lượt trước, và KÈM 1 khung điền khuyết \\square trong $$...$$ cho bước nhỏ đầu tiên."
            )

        has_concrete_problem = bool(re.search(r"[\d\+\-\*\/\=xXyY]|sqrt|căn|\^", message)) and bool(re.search(r"\d", message))
        # US 9.3 (Task T9.11 & T9.13) + US 11.6 (T401):
        # Đưa dòng thời gian và Kịch bản thăm dò Socratic chuyên sâu vào task_description
        # Probe mới (US 11.6): hỏi cụ thể tên bài học sinh đang học tới + tên bài được hỏi
        curr_grade = student_grade or 7
        try:
            from agents.agent_prompts import build_timeline_context_for_prompt
            tl = build_timeline_context_for_prompt(student_grade=curr_grade)
            timeline_label = tl.get("timeline_label", "")
            scenario_guide = tl.get("scenario_guide", "")
            hk1_topics = tl.get("topics_hk1", [])
            hk2_topics = tl.get("topics_hk2", [])
            hk1_str = "; ".join(hk1_topics[:8]) + ("..." if len(hk1_topics) > 8 else "")
            hk2_str = "; ".join(hk2_topics[:8]) + ("..." if len(hk2_topics) > 8 else "")
            # --- US 11.6: Inject danh sách đầy đủ theo thứ tự vào prompt để Gemini tự so thứ tự ---
            hk1_ordered = "; ".join(f"[{i+1}] {t}" for i, t in enumerate(hk1_topics))
            hk2_ordered = "; ".join(f"[{i+1}] {t}" for i, t in enumerate(hk2_topics))
            concrete_step_note = (
                "\nLƯU Ý ĐỀ BÀI CỤ THỂ: Học sinh đã nêu rõ biểu thức/số liệu cụ thể cần tính. "
                "Thay vì chỉ hỏi tiến độ trường lớp rồi bỏ lửng, hãy đồng cảm ngắn 1 câu rằng chưa quen là bình thường, "
                "sau đó gợi mở NGAY bước 1 thật dễ hiểu kèm 1 khung điền khuyết `\\square` trong `$$...$$` để em bắt đầu làm ngay!"
                if has_concrete_problem
                else (
                    f"NGUYÊN TẮC QUAN TRỌNG: Nếu rơi vào trường hợp cần hỏi thăm dò tiến độ trường học hoặc kỳ nghỉ hè, "
                    f"BẠN PHẢI DỪNG LẠI Ở CÂU HỎI THĂM DÒ VÀ GẮN THẺ ẨN <!-- PROBE_PENDING --> (HOẶC [PROBE_PENDING]) Ở CUỐI CÙNG CÂU TRẢ LỜI, "
                    f"TUYỆT ĐỐI KHÔNG GIẢI BÀI HOẶC ĐẶT PHÉP TÍNH TOÁN NGAY TRONG LƯỢT NÀY!"
                )
            )
            return (
                f"HỌC SINH TUYÊN BỐ CHƯA HỌC: '{message[:80]}'.\n"
                f"[{timeline_label}] CHƯƠNG TRÌNH LỚP {curr_grade}:\n"
                f"- HK1 (thứ tự): {hk1_ordered}\n"
                f"- HK2 (thứ tự): {hk2_ordered}\n\n"
                f"CHỈ ĐẠO SƯ PHẠM BẮT BUỘC (US 11.6 - SOCRATIC BRIDGE PROBE GUIDELINES):\n"
                f"{scenario_guide}\n\n"
                f"=== US 11.6 - CÂU HỎI THĂM DÒ TIẾN ĐỘ NÂNG CAO ===\n"
                f"Khi cần hỏi thăm dò (bài thuộc HK1 vùng xám hoặc HK2 đang học), BẮT BUỘC hỏi theo mẫu:\n"
                f"'Em cho thầy biết trên trường hiện tại em đang học đến bài nào rồi?\n"
                f" Bài [TÊN BÀI HỌC SINH VỪA HỎI] này em đã học qua chưa? <!-- PROBE_PENDING -->'\n"
                f"(Điền tên bài cụ thể mà học sinh đang hỏi vào [TÊN BÀI HỌC SINH VỪA HỎI])\n\n"
                f"=== US 11.6 - XỬ LÝ KHI HỌC SINH TRẢ LỜI THĂM DÒ ===\n"
                f"Khi học sinh trả lời 'học đến bài X' — TỰ ĐỐI CHIẾU với danh sách thứ tự HK1/HK2 bên trên:\n"
                f"● Nếu bài X đứng TRƯỚC bài học sinh hỏi (index X < index bài hỏi)\n"
                f"  → HỌC SINH THỰC SỰ CHƯA HỌC: Dùng Kịch bản B (hướng dẫn từ gốc rễ Socratic).\n"
                f"● Nếu bài X đứng SAU bài học sinh hỏi (index X > index bài hỏi)\n"
                f"  → HỌC SINH ĐÃ HỌC NHƯNG QUÊN: Dùng Kịch bản A với câu mở:\n"
                f"    'Hiện tại nếu em đã học đến [Tên bài X] rồi thì với chương trình HK lớp {curr_grade},\n"
                f"     em đã học [Tên bài được hỏi] rồi. Có lẽ em đã quên nên thầy sẽ nhắc lại cách làm bài này...'\n"
                f"● Nếu học sinh nói 'cô/thầy bỏ qua/không dạy/nhảy cóc/giảm tải'\n"
                f"  → Kịch bản B với lời đồng cảm: 'Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé!'\n\n"
                f"{concrete_step_note}"
            )
        except Exception as e:
            return (
                f"HỌC SINH TUYÊN BỐ CHƯA HỌC: '{message[:80]}'. "
                f"BẮT BUỘC KỊCH BẢN B: 'Vì em đang học lớp {curr_grade} nên chưa quen với kiến thức này là bình thường. "
                f"Thầy sẽ giải thích từ nền tảng đơn giản nhất nhé!' rồi hướng dẫn từng bước Socratic."
            )
    
    if agent == "KNOWLEDGE_TRACING":
        topic = message.replace("là gì", "").replace("thầy ơi", "").replace("vậy thầy", "").strip()
        return (
            f"Học sinh đang hỏi về khái niệm/lý thuyết: '{topic[:50]}'. "
            "Đặt 1-2 câu hỏi ngắn thăm dò để xác định học sinh đang hiểu đến đâu "
            "trước khi giải thích. Không giảng ngay, phải kiểm tra nền tảng trước."
        )
    if agent == "MISCONCEPTION":
        if student_ans and expected_ans:
            return (
                f"Học sinh nộp đáp án '{student_ans}' — chưa chính xác (đáp án đúng: '{expected_ans}'). "
                f"{'Bài: ' + problem_text[:600] + '. ' if problem_text else ''}"
                "Dùng câu hỏi Socratic để học sinh tự tìm ra bước tính sai. "
                "Tuyệt đối không tiết lộ đáp án đúng."
            )
        return (
            f"Học sinh đang hiểu sai hoặc tính sai: '{message[:200]}'. "
            f"{'Bài: ' + problem_text[:600] + '. ' if problem_text else ''}"
            "Xác định chính xác bước sai và đặt câu hỏi gợi mở để học sinh tự phát hiện lỗi."
        )
    # SCAFFOLDING (default)
    if problem_text:
        return (
            f"Học sinh cần hỗ trợ bài: '{problem_text[:600]}'. "
            "Dùng phương pháp Socratic: đặt câu hỏi gợi mở cho bước tiếp theo "
            "(kèm 1 dòng khung trình bày có \\square trong $$...$$ nếu chưa chốt đáp án cuối), "
            "tuyệt đối không giải hộ toàn bộ bài."
        )
    return (
        "Học sinh cần được dẫn dắt từng bước. "
        "Dùng phương pháp Socratic: hỏi về bước học sinh vừa làm, "
        "rồi đặt câu hỏi cho bước tiếp theo (kèm 1 dòng khung \\square trong $$...$$ nếu phù hợp). Không giải hộ."
    )


def _detect_probe_in_history(history_text: str) -> Optional[str]:
    """
    US 9.3 - Task T9.14 & T9.15 (Tag-based Protocol & Semantic Fallback):
    Kiểm tra xem câu nói gần nhất của AI trong lịch sử có phải là câu hỏi thăm dò hay không.
    Hỗ trợ cả tin nhắn đơn dòng và tin nhắn nhiều dòng (multi-line markdown).
    - ƯU TIÊN 1: Nhận diện thẻ ẩn [PROBE_PENDING] / <!-- PROBE_PENDING --> (chính xác 100%).
    - FALLBACK 2: Quét từ khóa/mẫu câu thăm dò nếu tin nhắn không chứa tag.
    Trả về 'SCHOOL_PROBE', 'SUMMER_PROBE' hoặc None.
    """
    if not history_text:
        return None
    
    # 1. Tách lịch sử thành từng khối tin nhắn theo role header (hỗ trợ câu trả lời nhiều dòng)
    blocks = [b.strip() for b in re.split(r'(?im)^(?=\[(?:USER|STUDENT|AGENT|ASSISTANT|MODEL|THẦY)\]|(?:User|Model|Assistant):)', history_text) if b.strip()]
    assistant_prefixes = ("[agent", "[assistant", "[thầy", "[model", "model:", "assistant:")
    assistant_blocks = [
        b for b in blocks 
        if any(b.lower().startswith(p) for p in assistant_prefixes)
    ]
    if not assistant_blocks:
        # Fallback nếu format phẳng không có role header đầy đủ
        lines = [l.strip() for l in history_text.split("\n") if l.strip()]
        assistant_blocks = [
            l for l in lines 
            if any(l.lower().startswith(p) for p in assistant_prefixes)
        ]
    
    if not assistant_blocks:
        return None
    
    last_ai_msg = assistant_blocks[-1].lower()
    
    # 1. Ưu tiên kiểm tra Thẻ ẩn [PROBE_PENDING] / <!-- PROBE_PENDING --> / [SUMMER_PROBE_PENDING]
    has_summer_tag = (
        "summer_probe_pending" in last_ai_msg
        or ("probe_pending" in last_ai_msg and any(w in last_ai_msg for w in ("hè", "nghỉ hè", "summer", "ôn lại bài năm")))
    )
    if has_summer_tag:
        return "SUMMER_PROBE"

    has_school_tag = (
        "probe_pending" in last_ai_msg
        or "socratic_probe" in last_ai_msg
    )
    if has_school_tag:
        return "SCHOOL_PROBE"

    # 2. Fallback đối chiếu từ khóa và mẫu câu ngữ nghĩa
    school_probe_signals = (
        "thầy cô đã dạy đến bài",
        "thầy cô đã dạy đến",
        "học đến phần nào rồi",
        "học đến bài nào rồi",
        "đang học đến bài nào",
        "đang học tới bài nào",
        "dạy đến bài này chưa",
        "dạy đến bài",
        "học tới bài này chưa",
        "đã học qua chưa",
        "học qua chưa",
        "thầy cô dạy tới đâu rồi",
    )
    if any(s in last_ai_msg for s in school_probe_signals):
        return "SCHOOL_PROBE"

    summer_probe_signals = (
        "học trước kiến thức",
        "ôn lại bài năm vừa rồi",
        "chuẩn bị học trước",
        "ôn lại kiến thức cũ",
        "học trước hay ôn lại",
    )
    if any(s in last_ai_msg for s in summer_probe_signals):
        return "SUMMER_PROBE"
    
    return None


def _detect_teacher_skipped_phrase(message: str) -> bool:
    """
    US 11.6 (T400/T401) - Phát hiện học sinh báo giáo viên bỏ qua / không dạy bài đó.
    Ví dụ: "cô em không dạy bài đó", "thầy bỏ qua bài này", "nhảy cóc", "giảm tải"
    """
    msg_lower = message.lower()
    skip_signals = (
        "cô bỏ qua", "thầy bỏ qua", "bỏ qua bài", "nhảy cóc",
        "giảm tải", "không dạy bài", "ko dạy bài", "k dạy bài",
        "cô không dạy", "thầy không dạy", "cô ko dạy", "thầy ko dạy",
        "lướt qua bài", "cô lướt qua", "thầy lướt qua",
        "cô em lướt qua", "thầy em lướt qua", "cô em bỏ qua", "thầy em bỏ qua",
        "cô skip", "thầy skip", "cô em skip", "thầy em skip", "skip bài",
        "cô em không dạy", "cô em ko dạy", "thầy em không dạy",
        "bỏ bài", "cắt bài", "không học bài đó", "ko học bài đó",
        "trường em không học", "trường em ko học",
        "cô hay bỏ", "thầy hay bỏ",
    )
    return any(s in msg_lower for s in skip_signals)


def _detect_semester_for_grade(
    text: str,
    grade: int,
    default_sem: int = 1,
) -> int:
    """
    US 11.6: Tự động xác định học kỳ (1 hoặc 2) của khối lớp dựa trên
    tên bài học xuất hiện trong đoạn hội thoại / đề bài.
    """
    try:
        from agents.agent_prompts import _load_curriculum
        curriculum = _load_curriculum()
        g_data = curriculum.get(str(grade), {})
        text_norm = _normalize_curriculum_text(text)
        # Kiểm tra HK2 trước
        topics_hk2 = g_data.get("2", [])
        for t in topics_hk2:
            t_norm = _normalize_curriculum_text(t)
            if t_norm and len(t_norm) >= 4 and t_norm in text_norm:
                return 2
        # Kiểm tra HK1
        topics_hk1 = g_data.get("1", [])
        for t in topics_hk1:
            t_norm = _normalize_curriculum_text(t)
            if t_norm and len(t_norm) >= 4 and t_norm in text_norm:
                return 1
    except Exception:
        pass
    return default_sem


def _find_best_topic_index(topic_name_mentioned: str, topics: list[str]) -> int:
    """Tìm vị trí phù hợp nhất trong danh sách chuyên đề."""
    norm_mentioned = _normalize_curriculum_text(topic_name_mentioned)
    if not norm_mentioned:
        return -1

    words_mentioned = set(norm_mentioned.split())
    best_idx = -1
    best_score = 0.0

    for i, t in enumerate(topics):
        norm_t = _normalize_curriculum_text(t)
        words_t = set(norm_t.split())

        # Phân biệt ngữ nghĩa toán học: "số nguyên tố" vs "số nguyên" (integers)
        if "tố" in words_t and "tố" not in words_mentioned:
            continue
        if "tố" in words_mentioned and "tố" not in words_t:
            continue

        # 1. Khớp hoàn toàn
        if norm_t == norm_mentioned:
            return i

        score = 0.0
        # 2. Khớp cụm từ chính xác (word boundary substring)
        if re.search(rf"\b{re.escape(norm_mentioned)}\b", norm_t):
            score += 50.0
        elif norm_mentioned in norm_t:
            score += 30.0

        # 3. Điểm giao thoa từ vựng (Token Overlap)
        common = words_mentioned & words_t
        if common:
            overlap_ratio = len(common) / len(words_mentioned)
            score += overlap_ratio * 30.0

        if score > best_score and (score >= 30.0 or len(common) >= min(2, len(words_mentioned))):
            best_score = score
            best_idx = i

    return best_idx


def _get_topic_position_in_curriculum(
    topic_name_mentioned: str,
    grade: int,
    semester: Optional[int] = None,
) -> int:
    """
    US 11.6 (T401): Tìm vị trí (index 0-based) của tên bài học sinh đề cập
    trong danh sách curriculum theo thứ tự (HK1 hoặc HK2).
    Sử dụng thuật toán xếp hạng độ khớp tốt nhất (Best Match Ranking).
    Trả về -1 nếu không tìm thấy.
    """
    try:
        from agents.agent_prompts import _load_curriculum
        curriculum = _load_curriculum()
        g_data = curriculum.get(str(grade), {})
        target_sem = semester if semester in (1, 2) else 1
        topics = g_data.get(str(target_sem), [])
        idx = _find_best_topic_index(topic_name_mentioned, topics)
        if idx != -1:
            return idx
        # Nếu không tìm thấy trong kỳ đã chọn, kiểm tra kỳ còn lại
        other_sem = 2 if target_sem == 1 else 1
        other_topics = g_data.get(str(other_sem), [])
        idx_other = _find_best_topic_index(topic_name_mentioned, other_topics)
        if idx_other != -1:
            return idx_other
        return -1
    except Exception:
        return -1


def _classify_probe_reply_with_curriculum(
    message: str,
    asked_topic: str,
    grade: int,
    semester: int,
) -> str:
    """
    US 11.6 (T401) - Phân loại thông minh phản hồi probe dựa trên vị trí bài trong curriculum.

    So sánh vị trí của bài học sinh nói họ đang học (student_current_topic)
    so với bài được hỏi (asked_topic) trong danh sách curriculum đã sắp xếp theo thứ tự.

    Trả về:
    - 'LEARN_NEW': student_pos < asked_pos → học sinh thực sự chưa học tới bài đó
    - 'FORGOT_OLD': student_pos > asked_pos → học sinh đã học qua bài đó (có thể quên)
    - 'CURRICULUM_SAME': student_pos == asked_pos → đang học đúng bài đó
    - 'UNCLEAR': không xác định được vị trí
    """
    msg_lower = message.lower()

    # Phát hiện câu "cô/thầy bỏ qua" → ưu tiên LEARN_NEW ngay
    if _detect_teacher_skipped_phrase(message):
        return "TEACHER_SKIPPED"

    # Trích xuất tên bài học sinh nhắc tới ("học đến bài lũy thừa", "học tới phân số", ...)
    # Pattern: "học (tới|đến|đến bài|tới bài) <tên bài>"
    student_topic_match = re.search(
        r"(?:học|hc)\s+(?:tới|đến|đến bài|tới bài|đến phần|tới phần)?\s+(?:bài\s+)?(.+?)(?:\s*(?:rồi|r|ạ|á|nhé|thôi|nha|thầy|cô)|$)",
        msg_lower,
        re.IGNORECASE,
    )
    student_topic_raw = student_topic_match.group(1).strip() if student_topic_match else ""

    # Thử tìm thêm nếu học sinh nói "mới học bài X" / "đang học bài X"
    if not student_topic_raw:
        m2 = re.search(
            r"(?:mới học|ms học|đang học|học đến|học tới)\s+(?:bài\s+)?(.+?)(?:\s*(?:rồi|r|ạ|á|nhé|thôi|nha|thầy|cô)|$)",
            msg_lower,
            re.IGNORECASE,
        )
        if m2:
            student_topic_raw = m2.group(1).strip()

    # Nếu không trích được tên bài → fallback sang classify thủ công cũ
    if not student_topic_raw or len(student_topic_raw) < 3:
        return _classify_probe_reply(message)

    asked_pos = _get_topic_position_in_curriculum(asked_topic, grade, semester)
    student_pos = _get_topic_position_in_curriculum(student_topic_raw, grade, semester)

    if asked_pos == -1 or student_pos == -1:
        # Không tìm được vị trí → fallback
        return _classify_probe_reply(message)

    if student_pos < asked_pos:
        return "LEARN_NEW"
    elif student_pos > asked_pos:
        return "FORGOT_OLD"
    else:
        return "CURRICULUM_SAME"


def _classify_probe_reply(message: str) -> str:
    """
    US 9.3 - Task T9.14:
    Phân loại phản hồi của học sinh sau câu hỏi thăm dò:
    - 'LEARN_NEW': Chưa học tới ở trường hoặc đang tự học trước bài mới.
    - 'FORGOT_OLD': Đã học rồi nhưng quên / hè xả hơi / ôn lại bài cũ / cô đã dạy rồi.
    - 'UNCLEAR': Lấp lửng / không rõ ràng / bí quá.
    """
    msg_clean = message.lower().strip()

    # 1. Dấu hiệu ĐÃ HỌC / ĐÃ DẠY / ÔN TẬP CŨ / QUÊN (Ưu tiên kiểm tra trước)
    # Ví dụ: "học rồi", "dạy rồi", "cô dạy rồi", "dạ rồi", "rồi ạ", "ôn bài", "ôn lại", "quên sạch",...
    forgot_signals = (
        "quên", "quen", "học rồi", "hc rồi", "học qua", "hc qua", "dạy rồi", "dạy qua",
        "cô dạy", "thầy dạy", "đã học", "đã dạy", "không nhớ", "ko nhớ", "k nhớ",
        "xả hơi", "ôn lại", "ôn bài", "ôn tập", "bài cũ", "năm ngoái", "lâu quá", "lú quá",
        "rồi mà", "r mà", "chơi nhiều nên quên",
    )
    has_learned_or_forgot = (
        any(s in msg_clean for s in forgot_signals)
        or bool(re.search(r"\b(học|hc|dạy)\s+(r|rồi)\b", msg_clean))
        or bool(re.search(r"^(dạ\s+)?rồi(\s+(ạ|thầy|cô|nè))?$", msg_clean))
        or bool(re.search(r"\b(dạ\s+)?(rồi|r)\s+(ạ|thầy|cô)\b", msg_clean))
        or bool(re.search(r"\bôn\s+(thi|hè|lại|bài|tập)\b", msg_clean))
    )
    if has_learned_or_forgot:
        return "FORGOT_OLD"

    # 2. Dấu hiệu CHƯA HỌC TỚI / HỌC TRƯỚC / BÀI MỚI
    new_signals = (
        "chưa", "chx", "chua", "mới học", "ms học", "ms hc", "mới tới", "ms tới",
        "học trước", "hc trước", "hc trc", "học trc", "tự học", "chuẩn bị", "xem trước",
        "coi trước", "tìm hiểu trước", "chưa tới", "chx tới", "chưa dạy", "chx dạy",
        "bài mới", "kiến thức mới", "chưa học đến", "chưa qua", "chưa ai dạy"
    )
    if any(s in msg_clean for s in new_signals) or bool(re.search(r"\b(bài|học|xem|coi)\s+mới\b", msg_clean)):
        return "LEARN_NEW"

    return "UNCLEAR"


class OrchestratorAgent:
    """
    Orchestrator Agent điều phối câu hỏi học sinh theo KIẾN TRÚC ZERO-API.

    Trụ cột 1 — Structural Pattern Engine : Regex, Ngữ pháp câu, Toán học.
    Trụ cột 2 — ML Semantic Router        : TF-IDF + Logistic Regression.
    Trụ cột 3 — State Machine             : Suy luận từ ngữ cảnh hội thoại.
    """

    # ── Danh sách từ xấu / xúc phạm ─────────────────────────────────────────
    PROFANITY_LIST: tuple = (
        "đm", "dcm", "dm", "vcl", "vl", "đĩ", "cặc", "lồn", "đéo", "đíu", "đếch", "chó chết", "ngu ngốc", "chết đi", "cút đi", "mẹ mày","thằng chó", "địt", 
        "mẹ kiếp", "đệt", "đệch", "đậu má", "dmm", "dkm", "đkm", "đklm", "loz", "lòn", "cẹc", "buồi", "dái", "clgt", "cc", "qq", "ml",
         "sml", "vml", "cđm", "vkl","đụ mẹ", "đụ má", "đĩ mẹ", "đù má", "đù mẹ", "đụ", "cút", "biến đi", "xéo", "cái đệt",
        "địt mẹ", "địt con mẹ", "địt cụ", "địt mợ", "địt tổ sư", "địt mả bố","địt mẹ mày", "đụ mẹ mày", "đm mày", "đm nó", "địt con lồn mẹ", 
        "đcmm", "dcmm", "con đĩ mẹ","vãi", "vãi lồn", "vãi cả lồn", "vãi lìn", "vãi lon", "vãi l","vãi đái", "vãi nhái", "vãi chưởng", "vãi nồi",
        "cái lồn gì thế", "cái lồn gì vậy", "cái lồn", "mặt lồn", "hãm lồn", "xạo lồn", "con lồn", "thằng lồn", "sấp mặt lồn",
        "con cặc", "cục cặc", "cái cặc", "đầu cặc", "cái quần què", "quần què","phò", "điếm", "cave", "đĩ điếm", "gái điếm", "con đĩ",
        "nứng", "nứng lồn", "nứng sảng", "chịch", "xoạc", "bú cu", "bú lồn", "liếm lồn","súc vật", "súc sinh", "óc chó", "óc lợn", "ngu học", 
        "ngu như bò", "ngu như chó", "ngu lồn", "khốn nạn", "khốn kiếp", "chó má",  "đĩ chó", "đĩ ngựa", "đĩ thoã",
        "mày", "tao", "mầy", "thằng kia", "con kia", "bot ngu", "thằng bot", "con bot", "ông già", "bà già", "chúng mày", "bọn mày", "thằng này", "con này",
        "fuck", "fuck you", "fck", "fk", "fucking", "shit", "bitch", "asshole", "dick", "cunt",
        "mặt ghẻ", "óc cứt", "óc bò", "đĩ mẹ", "mẹ mày"
    )

    # ── Danh sách tiếng hú hét, gọi cộc lốc, vô nghĩa, quấy rối ─────────
    SHOUTING_SIGNALS: tuple = (
        "hú", "hú hú", "hú hu", "húu", "húuu", "húuuu", "huuu", "hu", "hú hồn",
        "hét", "la hét", "gào", "gầm", "hú alo", "alo hú",
        "á", "á á", "áaa", "ơ", "ơ kìa", "ủa", "ủa ủa",
        "ú òa", "u oa", "ú oà", "meo meo", "gâu gâu", "quạc quạc",
        "ahihi", "keke", "hơ hơ", "hoho",
    )

    # ── Từ bắt đầu lời chào ────────────────────────────
    GREETING_STARTS: tuple = (
        "chào", "xin chào", "em chào", "dạ chào", "chào thầy", "chào cô", "chào ad", "chào bot", "dạ thầy",
        "chào mọi người", "chào mn", "chào các bạn", "chào buổi sáng", "chào buổi chiều", "chào buổi tối","hi ", "hi\n", "hello", "helo",
        "alo ", "alo\n", "alô", "a lô", "hey ", "yo ", 
        "good morning", "good afternoon", "good evening", "hế lô", "hé lô", "hê lô", "halo", "hê sờ lô", "hê xờ lô",
    )
    GREETING_EXACT: tuple = (
        "hi", "hello", "helo", "alo", "alô", "a lô", "hey", "yo", 
        "chào", "xin chào","hế lô", "hé lô", "hê lô", "halo",
        "chào thầy", "chào cô", "chào ad", "chào bot"
    )

    # ── Tín hiệu "đang hỏi bài học" — nếu có trong câu chào thì KHÔNG route SAFETY ──
    STUDY_SIGNALS: tuple = (
        "bài", "làm sao", "chỉ em", "hướng dẫn", "tính", "giải", "khái niệm", "là gì", 
        "đáp án", "đáp số", "kết quả", "bước", "cách làm", "cách giải", "công thức", 
        "chỉ cách", "giảng lại", "tại sao", "ví dụ", "gợi ý", "chi tiết", "giúp em", 
        "giúp mình", "hỏi", "đề bài", "chứng minh", "tìm x",    
        "số tự nhiên", "lớp triệu", "lớp tỉ", "phép cộng", "phép trừ", "phép nhân", "phép chia",
        "giao hoán", "kết hợp", "chia có dư", "chia hết", "trung bình cộng", "tổng và hiệu",
        "dấu hiệu chia hết", "phân số", "rút gọn", "quy đồng", "tử số", "mẫu số",
        "góc nhọn", "góc tù", "góc bẹt", "vuông góc", "song song", "hình bình hành",
        "hình thoi", "chu vi", "diện tích", "khối lượng", "yến", "tạ", "tấn",       
        "số thập phân", "tỉ số phần trăm", "phần trăm", "lãi", "lỗ", "giảm giá",
        "chuyển động", "vận tốc", "quãng đường", "thời gian", "ngược chiều", "cùng chiều",
        "đuổi kịp", "tam giác", "hình thang", "hình tròn", "hình hộp chữ nhật",
        "hình lập phương", "diện tích xung quanh", "diện tích toàn phần", "thể tích",      
        "tập hợp", "phần tử", "lũy thừa", "số mũ", "cơ số", "số nguyên tố", "hợp số",
        "thừa số", "ước chung", "bội chung", "ucln", "bcnn", "số nguyên", "số âm", "số dương",
        "số đối", "xác suất", "đồng xu", "xúc xắc", "điểm", "đường thẳng", "tia",
        "đoạn thẳng", "số đo góc", "tia phân giác", "tam giác đều", "hình vuông", "lục giác đều",       
        "số hữu tỉ", "tỉ lệ thức", "tỉ lệ thuận", "tỉ lệ nghịch", "số vô tỉ", "căn bậc hai",
        "số thực", "giá trị tuyệt đối", "kề bù", "đối đỉnh", "so le trong", "đồng vị",
        "bằng nhau", "c.c.c", "c.g.c", "g.c.g", "cạnh huyền", "tam giác cân",
        "bất đẳng thức", "đồng quy", "trung tuyến", "trọng tâm", "đường cao", "trung trực",
        "biểu thức đại số", "đơn thức", "đa thức", "hệ số", "nghiệm",      
        "hằng đẳng thức", "bình phương", "lập phương", "nhân tử", "phân thức",
        "quy đồng mẫu thức", "phương trình", "bậc nhất", "ẩn", "năng suất", "hóa học",
        "bất phương trình", "tứ giác", "hình thang cân", "đường trung bình", "hình chữ nhật",
        "thales", "ta-lét", "đồng dạng", "đa giác",        
        "căn thức", "điều kiện xác định", "trục căn", "căn bậc ba", "hàm số",
        "đồng biến", "nghịch biến", "đồ thị", "parabol", "hệ phương trình", "phương pháp thế",
        "cộng đại số", "phương trình bậc hai", "công thức nghiệm", "delta", "vi-ète", "vi-et",
        "trùng phương", "hệ thức lượng", "lượng giác", "sin", "cos", "tan", "cot",
        "đường tròn", "đường kính", "dây cung", "tiếp tuyến", "nội tiếp", "bàng tiếp",
        "góc ở tâm", "cung tròn", "hình quạt", "hình trụ", "hình nón", "hình cầu",
        "pt", "bpt", "hpt", "đkxd", "dkxd", "hđt", "hdt", "đpcm", "dpcm", 
        "gt", "kl", "tbc", "cv", "dt", "tg", "hbh", "hcn", "bt", "pp", 
        "vt", "vp", "oxy", "pi", "x^2", "x^3", "m2", "m3", "cm2", "cm3", 
        "dm2", "dm3", "+", "-", "*", "/", "=", "<", ">", "<=", ">=", "!=", 
        "tính toán", "thực hiện phép tính", "tìm y", "phân tích", "biến đổi", 
        "đơn giản", "lập luận", "suy ra", "định lý", "định lí", "tiên đề", 
        "tính chất", "quy tắc", "nhẩm", "nhân nhẩm", "chia nhẩm", "đặt ẩn phụ", 
        "dạng toán", "toán đố", "bài tập", "đề thi", "đọc số", "viết số", 
        "hỗn số", "phân số thập phân", "chữ số", "hàng đơn vị", "hàng chục", 
        "hàng trăm", "nhóm hạng tử", "tách hạng tử", "khử mẫu", "đưa vào", 
        "đưa ra", "góc ngoài", "tam giác vuông", "tam giác tù", "tam giác nhọn", 
        "hoành độ", "tung độ", "trục tọa độ", "mặt phẳng tọa độ", "gốc tọa độ", 
        "hệ số góc", "cắt nhau", "trùng nhau", "khoảng cách", "số chính phương", "vế trái", "vế phải",
        "dạ", "vâng", "dạ có", "dạ không", "vâng ạ", "dạ hiểu", "dạ vâng", "dạ đúng"
    )

    # ── Tín hiệu ngoài lề (luôn là SAFETY, dù dài bao nhiêu từ) ─────────────
    OFFTOPIC_SIGNALS: tuple = (
        "thầy là ai", "thầy là máy", "thầy là robot", "thầy là bot", "thầy là ai vậy",
        "thầy có thật không", "người thật hay máy", "có phải người thật",
        "trí tuệ nhân tạo", "thầy có cảm xúc không", "thầy biết suy nghĩ không",
        "ai tạo ra thầy", "ai lập trình", "tác giả của thầy", "ai làm ra thầy",
        "thầy dùng chatgpt", "thầy dùng gemini", "thầy dùng gpt",
        "thầy mấy tuổi", "thầy bao nhiêu tuổi",
        "thầy có người yêu chưa", "thầy có vợ chưa",
        "thầy ăn cơm chưa", "nhà thầy ở đâu", "thầy quê ở đâu",
        "chơi game", "liên quân", "free fire", "roblox", "pubg", "minecraft",
        "yêu đương", "tình yêu", "bạn gái", "bạn trai", "thất tình", "crush",
        "nghỉ học", "không muốn học", "học làm gì", "chán học",
        "kể chuyện", "hát đi", "kể chuyện ma", "kể chuyện cười",
        "chơi nối chữ", "đố vui", "tán gẫu", "bạn là ai", "mày là ai", "bot à",
        "là bot hả", "người hay bot",
        "chatgpt", "openai", "claude", "llama", "mã nguồn", "source code",
        "thầy thích gì", "số điện thoại", "sđt", "zalo", "facebook", "fb", 
        "xin infor", "xin info", "in4", "FA à", "ế à", "có bồ chưa",
        "lol", "lmht", "tốc chiến", "genshin", "genshin impact", "valorant", 
        "csgo", "fifa", "fo4", "play together", "leo rank", "đánh rank", "gánh team",
        "xem phim", "nghe nhạc", "idol", "đu idol", "kpop", "bts", "blackpink",
        "anime", "manga", "tiktok", "top top", "tóp tóp", "youtube",
        "hóng biến", "hóng drama", "bóc phốt", "đu trend", "bắt trend",
        "mệt quá", "đau đầu", "buồn ngủ", "ngủ đây", "đi ngủ", "lười học",
        "cúp tiết", "trốn tiết", "bùng học", "cúp học", "ghét học", "áp lực", "stress",
        "đốt trường", "đốt sách", "ghét thầy", "ghét cô", "thi trượt", "rớt môn",
        "cách tỏ tình", "tỏ tình", "cắm sừng", "bị đá", "trà xanh", "chia tay",
        "đơn phương", "tương tư", "làm sao để quên", "thất tình", "thích một người",
        "làm thơ", "rap đi", "hát một bài", "chơi caro", "oẳn tù tì", "kéo búa bao",
        "chửi nhau", "đấm nhau", "solo", "đánh nhau", "cãi nhau", "thách đấu",
        "tâm sự", "buồn quá", "khóc", "chán quá", "vui quá"
    )

    # ── Từ khóa cầu cứu / cần gợi ý (SCAFFOLDING) ────────────────────────────
    HELP_SIGNALS: tuple = (
        "bài này làm sao", "làm sao thầy", "làm thế nào","chỉ em", "chỉ mình", "hướng dẫn",
        "bài này lm sao", "lm sao thầy", "lm thế nào","bí rồi", "chịu rồi", "không biết làm", "ko biết làm",
        "k biết làm", "không biết bắt đầu", "ko biết bắt đầu", "hint thầy", "cho hint", "gợi ý thôi", "1 gợi ý thôi",
        "bí quá", "tắc rồi", "stuck rồi", "em bí", "em tắc","không biết tiếp theo", "ko biết tiếp theo", "k biết tiếp",
        "giúp em", "cứu em", "giúp mình", "giúp e", "cứu e", "bước tiếp theo làm gì", "tiếp theo làm gì",
        "help em", "help mình", "help thầy","gợi ý đi", "cho em gợi ý", "gợi ý nhỏ", "hint đi",
        "bước tiếp làm gì", "tiếp theo lm gì", "làm gì tiếp","lm gì tiếp", "tiếp theo là gì", "next step",
        "cho em ví dụ", "ví dụ đi", "ví dụ thế nào", "ví dụ cụ thể", "cho 1 vd đi", "1 vd đi", "cho vd đi", "vd đi",
        "ví dụ", "vi du", "vd", "vdu", "dí dụ", "di du", "vidu", "mẫu", "bài mẫu", "làm mẫu", "giải mẫu",
        "không hiểu đề", "ko hiểu đề", "k hiểu đề", "chưa làm được", "chưa lm được",
        "bắt đầu từ đâu", "bắt đầu ntn", "bắt đầu từ đâu thầy","em làm vậy đúng k", "em làm vậy đúng ko", "em làm đúng chưa",
        "thầy xem giúp em", "thầy check giúp", "check hộ em", "em làm đến đây rồi", "em mới làm đến đây",
        "ko bt ạ", "ko bt á", "ko biết ạ", "ko biết á","k bt ạ", "k biết ạ", "k biết á", "không bt ạ", "không bt á",
        "chưa bt ạ", "chưa bt á", "chưa biết ạ", "chưa biết á", "em chưa bt", "em ko bt", "em k bt",
        "khó quá", "bó tay", "chịu", "chịu chết", "xin hàng", "tịt ngòi", "nổ não", "lú luôn", "lú rồi", "rối não", "mù tịt", "hoa mắt", 
        "không ra", "tính ko ra", "tính k ra", "giải ko ra", "giải k ra", "chấm hỏi", "xu cà na", "bất lực", "khoai quá", "ảo thật",
        "sos", "ét ô ét", "cứu với", "cứu gấp", "cứu lẹ", "cứu mạng", "giúp vs", "giúp lẹ", "cíu", "cíu e", "cíu em", "cíu vs", "cíu mình", 
        "cíu với", "cứu e vs", "help me", "pls help","hong hiểu", "hong bt", "hong biết", "chả hiểu", "chả biết", "chả bt", 
        "k hỉu", "k hỉu j", "ko hỉu", "ko hỉu gì", "k hỉu gì luôn", "hông hiểu", "hông biết", "hk biết", "hk bt", "khum biết", "khum bt", 
        "khum hỉu", "mù tịt luôn", "chả hiểu đề nói gì", "lag quá", "lag rồi","làm ntn", "lm ntn", "làm ra sao", "lm ra sao", "cách nào", 
        "áp dụng gì", "dùng công thức nào", "dùng ct nào", "dùng hđt nào", "áp dụng định lý nào", "cách làm sao", "cách giải ntn", "phương pháp gì",
        "bước 1 làm gì", "vẽ hình sao", "vẽ hình ntn","xem thử", "ktra giúp", "coi dùm", "ngó qua", "dò giúp", "chữa giúp", 
        "sửa giúp", "sửa lỗi", "sai ở đâu", "sai chỗ nào", "tìm lỗi sai", "chỉ chỗ sai", "lỗi ở đâu", "sao lại sai",
        "như này hả", "như vầy hả", "vầy đúng k", "vậy đúng ko", "đúng ko thầy", "đúng k ạ", "có đúng không", "chuẩn chưa", 
        "ổn không", "vậy hả", "vậy đúng k", "như này đúng chưa", "cần hint", "cho xin hint", "gợi ý xíu", "hé lộ xíu", "mở bài xíu", 
        "hd em vs", "hd e vs", "hd mình", "hướng dẫn với", "hd nhanh", "mớm cho em", "gợi ý nhẹ", "xin 1 gợi ý"
    )

    # ── Tín hiệu hỏi lý thuyết / khái niệm ──────────────────────────────────
    THEORY_SIGNALS: tuple = (
        "là gì", "là cái gì", "là cái nào", "là số nào", "là chỗ nào",
        "thế nào là", "như thế nào là", "ntn là",
        "định nghĩa", "khái niệm", "có nghĩa là gì", "nghĩa là gì",
        "ôn tập", "ôn lại", "nhắc lại", "nhắc em", "nhắc lại đi",
        "em quên", "em ko nhớ", "em k nhớ", "em chưa nhớ",
        "quên mất cách", "quên cách", "không nhớ công thức", "ko nhớ công thức",
        "giải thích lại", "giải thích cho em", "giải thích đi",
        "chưa hiểu khái niệm", "không hiểu khái niệm", "ko hiểu khái niệm",
        "tại sao phải", "tại sao lại", "vì sao phải", "vì sao lại",
        "khác nhau thế nào", "khác nhau ntn", "phân biệt", "so sánh",
        "dùng để làm gì", "có tác dụng gì", "để làm gì", "dùng khi nào",
        "là j vậy", "là j thầy", "là j ạ", "là j á",
        "là cái j", "nghĩa là j", "có nghĩa là j",
        "ntn thầy", "ntn ạ", "ntn á", "cách tính ntn", "cách làm ntn",
        "tử là gì", "mẫu là gì", "tử số là gì", "mẫu số là gì",
        "bcnn là gì", "bcnn là j", "ucln là gì", "ucln là j",
        "công thức là gì", "công thức tính", "cách tính là gì",
        "tính chất", "t/c", "dấu hiệu nhận biết", "dấu hiệu", "định lý", "định lí", 
        "tiên đề", "hệ quả", "quy tắc", "điều kiện", "điều kiện là gì", "đk là gì",
        "đn là gì", "kn là gì", "ct là gì", "cthuc là gì", "vd mẫu", "cho xin vd",
        "nói rõ hơn", "giảng lại", "giảng kỹ hơn", "nói lại xem", "nói dễ hiểu hơn", 
        "giải thích kỹ", "nói tóm lại", "tóm tắt lại", "hiểu đơn giản là", "hiểu nôm na là",
        "ý nghĩa của", "bản chất là", "nguồn gốc", 
        "tại sao ra được", "sao ra đc", "từ đâu ra", "ở đâu ra", "lấy ở đâu", 
        "cơ sở nào", "dựa vào đâu", "nguyên nhân do đâu", "suy ra từ đâu",
        "giống nhau", "giống và khác", "cách nhận biết", "cách nhớ", "mẹo nhớ", 
        "mẹo học thuộc", "dễ nhầm", "hay nhầm", "lưu ý gì", "có chú ý gì không",
        "não cá vàng", "quên sạch", "chữ thầy trả thầy", "lâu quá quên", 
        "lâu ko đụng tới", "rớt chữ", "bay chữ", "lục lại trí nhớ", "gợi nhớ",
        "phát biểu", "định luật", "hệ thức", "đại lượng", "biến số", "hằng số",
        "tập hợp là j", "hàm số là j", "phương trình là j", "đa thức là j", 
        "đơn thức là j", "nghiệm là j", "hệ số là j", "cơ số là j", "số mũ là j",
        "lớp triệu", "lớp tỉ", "tính chất giao hoán", "tc giao hoán", 
        "tính chất kết hợp", "tc kết hợp", "chia có dư", "tổng và hiệu", 
        "dấu hiệu chia hết", "cấu tạo số", "rút gọn phân số", "quy đồng mẫu số",
        "tính lãi", "tính lỗ", "giảm giá", "chuyển động đều", "ngược chiều", 
        "cùng chiều", "đuổi kịp", "diện tích xung quanh", "diện tích toàn phần", 
        "sxq", "stp", "hình hộp chữ nhật", "hình lập phương",
        "tập hợp số", "phần tử của tập hợp", "số nguyên tố", "hợp số", 
        "quy tắc dấu ngoặc", "quy tắc chuyển vế", "chuyển vế đổi dấu", 
        "xác suất thực nghiệm", "tung đồng xu", "gieo xúc xắc",
        "dãy tỉ số bằng nhau", "tỉ lệ thuận", "tỉ lệ nghịch", "số vô tỉ", 
        "căn bậc hai số học", "giá trị tuyệt đối", "trị tuyệt đối",
        "kề bù", "đối đỉnh", "so le trong", "đồng vị", "tia phân giác", 
        "c.c.c", "c.g.c", "g.c.g", "cạnh huyền góc nhọn", "ch-gn", 
        "bất đẳng thức tam giác", "bđt tam giác", "sự đồng quy", 
        "đường trung tuyến", "đường trung trực",
        "đa thức một biến", "nghiệm của đa thức", "hằng đẳng thức đáng nhớ", 
        "hđt đáng nhớ", "bình phương của tổng", "bình phương của hiệu", 
        "hiệu hai bình phương", "lập phương của tổng", "lập phương của hiệu", 
        "tổng hai lập phương", "hiệu hai lập phương",
        "phân tích đa thức thành nhân tử", "đặt nhân tử chung", "nhóm hạng tử", 
        "phân thức đại số", "rút gọn phân thức", "quy đồng mẫu thức", 
        "phương trình bậc nhất", "pt bậc nhất", "phương trình tích", "pt tích", 
        "phương trình chứa ẩn ở mẫu", "toán năng suất", "toán chuyển động", 
        "toán hóa học", "bất phương trình bậc nhất", "bpt bậc nhất",
        "đường trung bình", "hình thang cân", "định lý thalès", "định lí thales", 
        "hệ quả thales", "định lý đảo", "tam giác đồng dạng", "trường hợp đồng dạng",
        "điều kiện xác định", "đkxd", "đưa ra ngoài dấu căn", "đưa vào trong dấu căn", 
        "khử mẫu biểu thức lấy căn", "trục căn thức", "căn bậc ba",
        "hàm số bậc nhất", "sự đồng biến", "sự nghịch biến", "hệ số góc", 
        "phương pháp thế", "phương pháp cộng đại số", "cộng đại số",
        "phương trình bậc hai", "pt bậc hai", "công thức nghiệm", "công thức nghiệm thu gọn", 
        "hệ thức vi-ète", "định lý vi-ét", "nhẩm nghiệm", "phương trình trùng phương", 
        "pt trùng phương", "pt quy về bậc hai",
        "hệ thức lượng", "tỉ số lượng giác", "bảng lượng giác", 
        "tính chất đối xứng", "vị trí tương đối", "tiếp tuyến cắt nhau", 
        "đường tròn nội tiếp", "đường tròn ngoại tiếp", "đường tròn bàng tiếp", 
        "góc ở tâm", "số đo cung", "góc nội tiếp", "góc tạo bởi tia tiếp tuyến và dây cung", 
        "tứ giác nội tiếp", "độ dài đường tròn", "cung tròn", "hình quạt tròn", 
        "hình nón cụt", "mặt cầu", "diện tích mặt cầu", "thể tích hình cầu"
    )

    # ── Mẫu câu lỗi sai rõ ràng (MISCONCEPTION) ──────────────────────────────
    MISCONCEPTION_SIGNALS: tuple = (
        "em nghĩ phải", "em tưởng phải", "em tưởng là",
        "em lấy tử cộng tử mẫu cộng mẫu",
        "em cộng cả tử cả mẫu",
        "em nhân chéo hai phân số", "nhân chéo hai phân số",
        "em tính nhầm", "em cộng nhầm", "em nhân nhầm", "lập nhầm", "chọn nhầm",
        "hình như em sai", "em sai chỗ nào", "chỗ nào em sai",
        "em tưởng âm nhân âm ra âm",
        "em tưởng trừ số âm thì cũng trừ",
        "em tưởng vậy", "em nghĩ vậy mà", "em nghĩ khác",
        "em hiểu nhầm", "em nhớ nhầm", "em học nhầm",
        "hình như sai rồi", "chắc em sai", "em sai r",
        "sai ở đâu", "sai chỗ nào", "em tính sai không",
        "em nhầm", "em lộn", "tính lộn", "bấm lộn", "bấm máy nhầm", "bấm sai", 
        "nhìn nhầm đề", "chép sai đề", "đọc lộn đề", "tính ẩu", "rút gọn ẩu",
        "em ngáo", "ngáo ngang", "lag r", "lag rồi", "ảo ma", 
        "thấy sai sai", "hơi cấn", "cấn cấn", "sao sao á", "kì vậy", "ảo vậy",
        "kết quả vô lý", "thấy vô lý", "ra số âm vô lý", "số lẻ quá", "ra số xấu", 
        "nghiệm xấu quá", "vô nghiệm vô lý",
        "em cứ tưởng", "em cứ ngỡ", "em đinh ninh", "em mặc định", "do em nghĩ", 
        "tại em thấy", "nhìn hình em tưởng", "nhìn hình thấy", "em đo thấy", 
        "em ngộ nhận", "em tự cho là",
        "quên đổi dấu", "lỡ đổi dấu", "quên ngoặc", "thiếu ngoặc", "nhân thiếu",
        "phá ngoặc quên đổi dấu", "trước ngoặc dấu trừ", "chuyển vế không đổi dấu", 
        "chuyển vế quên đổi dấu", "chuyển vế giữ nguyên dấu",
        "âm bình phương ra âm", "âm nhân âm ra âm", "căn số âm", "quên điều kiện", 
        "thiếu đk", "quên đkxd", "thiếu trường hợp", "thiếu nghiệm", "mất nghiệm",
        "triệt tiêu ẩn", "triệt tiêu x", "chia cho ẩn", "chia cho 0", 
        "chia số âm không đổi chiều", "không đổi chiều bpt", "quên đổi chiều",
        "quên quy đồng", "nhân chéo nhầm", "cộng hai mẫu số", "tử cộng tử mẫu cộng mẫu",
        "nhân tử với mẫu", "quy đồng sai", "chưa cùng mẫu mà đã cộng",
        "em dùng lộn công thức", "em nhớ lộn định lý", "nhớ sai công thức", 
        "áp dụng sai", "lộn hằng đẳng thức", "nhầm hđt", "khai triển sai",
        "sao lại ra như vậy", "ủa sao vậy", "sao ra thế được", "sao ko ra", 
        "chỗ này lạ quá", "em làm thế này sao sai", "sai bước nào", "sai ở dòng nào",
        "sao đáp án khác", "ủa sai hả", "hình như sai", "chắc sai r"
    )

    ML_CONFIDENCE_THRESHOLD = 0.60

    def __init__(self, model_name: Optional[str] = None, **kwargs: Any) -> None:
        self.model_name = model_name
        self._minimal_arithmetic_re = re.compile(
            r"^(?:thầy ơi\s+|thầy\s+|thưa thầy\s+|bạn ơi\s+|tính\s+|giải\s+|giải bài\s+|em muốn tính\s+|cho em hỏi\s+|giúp em\s+|phép tính\s+|phép tính này\s+)?"
            r"(\d+(?:\.\d+)?)\s*"
            r"([:\/÷\*x×\+\-]|chia cho|chia|nhân với|nhân|cộng với|cộng|trừ đi|trừ)\s*"
            r"(\d+(?:\.\d+)?)"
            r"(?:\s*(?:=|bằng|\?|là|ra)?\s*(?:\?|mấy|bao nhiêu|la bao nhieu|bao nhiu|j|gì)?)?"
            r"\s*(?:ạ|nhé|nha|hả|ha|à|nhỉ|ơi)?"
            r"\s*[\?!\.]*$",
            re.IGNORECASE | re.UNICODE,
        )
        # Pre-compile regex từ cấm
        escaped = [re.escape(w) for w in self.PROFANITY_LIST]
        self._profanity_re = re.compile(
            rf"\b({'|'.join(escaped)})\b",
            re.IGNORECASE | re.UNICODE,
        )

        # Regex tiếng hú hét, cảm thán quấy rối
        self._shouting_re = re.compile(
            r"^(h[úu]+(\s+h[úu]+)*|ê+|á+|ú\s*òa|ơ+|ủa+)$",
            re.IGNORECASE | re.UNICODE,
        )

        # Regex câu hỏi lý thuyết
        self._theory_re = re.compile(
            r"(.+)\s+(là gì|là cái gì|là j|là cái j|là số gì|là số nào|là cái nào)\s*[?]?$"
            r"|^(thế nào là|ntn là|như thế nào là|định nghĩa|giải thích)\s+.+",
            re.IGNORECASE,
        )

        # Regex trích xuất phương trình đại số (toán học một ẩn, hỗ trợ cả 2 vế có biến)
        # math_chars dùng khoảng trắng ngang [ \t] tránh nhảy dòng; math_var không cắt giữa từ tiếng Việt có dấu
        math_chars = r"[\d\.\+\-\*\/:\^\(\) \t]"
        math_var = r"(?:(?<=\d)[a-zA-Z](?![a-zA-Z_\u00C0-\u1EF9])|(?<![a-zA-Z\d_\u00C0-\u1EF9])[a-zA-Z](?![a-zA-Z_\u00C0-\u1EF9]))"
        math_expr = rf"(?:{math_chars}|{math_var})+"
        self._equation_re = re.compile(
            rf"(?:^|(?<=[\s,:]))("
            rf"{math_expr}"
            rf"="
            rf"{math_expr}"
            rf")",
            re.IGNORECASE,
        )

        # Regex biểu thức toán học
        self._math_expr_re = re.compile(
            r"[\d\s\+\-\*\/\(\)\^\.x]{3,}",
            re.IGNORECASE,
        )

        # US 10.4 (Task T10.4.3): Khởi tạo hạ tầng Hot-Reloading & Atomic Swap cho Local ML Model (Trụ 2)
        self._model_path = pathlib.Path(__file__).parent / "local_orchestrator.pkl"
        self._last_loaded_mtime: float = 0.0
        self._last_mtime_check_time: float = 0.0
        self._mtime_check_interval: float = 1.0  # Giảm 99% system calls I/O
        self._reload_lock = threading.Lock()
        self._local_model = None
        self.reload_model(force=True)

    @classmethod
    def _is_math_measurement_unit(cls, text: str, start: int, end: int, word: str) -> bool:
        """
        Kiểm tra xem từ khớp (dm, ml, cc) có phải là đơn vị đo toán học/dung tích hay không.
        Tránh bắt nhầm các bài toán như: '12 dm', '500 ml', '200 cc', 'tính diện tích theo dm'.
        Tuyệt đối không để 'như cc', 'làm cc gì' bị nhận nhầm là đơn vị toán học!
        """
        w_lower = word.lower()
        if w_lower not in ("dm", "ml", "cc"):
            return False

        # Nếu đứng sau 'như', 'cái', 'làm', 'biết', 'ăn', 'thằng', 'con' -> 100% là chửi tục
        before_match = text[:start].strip().lower()
        if re.search(r"\b(như|cái|làm|biết|ăn|thằng|con)\s*$", before_match):
            return False

        # 1. Liền trước có số hoặc phân số (VD: '12 dm', '12dm', '500 ml', '200 cc', '1/2 dm', '0.5 dm')
        if re.search(r"(\d+(?:[.,]\d+)?|\b\d+/\d+)\s*$", text[:start]):
            return True

        # 2. Liền trước có dấu gạch chéo tỉ lệ / đơn vị kép (VD: 'g/cc', 'kg/cc', 'ml/cc')
        if re.search(r"[/]\s*$", text[:start]):
            return True

        # 3. Liền trước có từ chỉ hướng đổi hoặc câu hỏi đo lường (VD: 'ra dm', 'sang dm', 'bao nhiêu ml', 'mấy dm', 'theo dm', 'sang ml')
        if re.search(r"\b(ra|sang|về|theo|bằng|được|là|đơn vị|bao nhiêu|nhiêu|mấy)\s*$", before_match):
            return True

        # 4. Liền trước là đối tượng hình học (đoạn thẳng DM, đường cao DM, đường thẳng DM, trung tuyến DM, cạnh DM)
        if re.search(r"\b(đoạn thẳng|đường thẳng|đường cao|trung tuyến|cạnh|tia)\s*$", before_match):
            return True

        # 5. Liền sau có số mũ/chỉ số lũy thừa (VD: 'dm^2', 'dm2', 'dm²', 'dm^3', 'dm3', 'dm³', 'ml/phút')
        after = text[end:].lstrip()
        if after.startswith(("^2", "^3", "2", "3", "²", "³", "/")):
            return True

        # 6. Đi cùng các cụm từ chỉ đơn vị đo lường rõ ràng
        unit_phrases = (
            "đơn vị dm", "đơn vị ml", "đơn vị cc",
            "đổi ra dm", "đổi sang dm", "đổi về dm", "theo dm",
            "đổi ra ml", "đổi sang ml", "đổi về ml", "theo ml",
            "đổi ra cc", "đổi sang cc", "đổi về cc", "theo cc",
            "dung tích", "thể tích", "xi lanh", "phân khối", "bình", "bể"
        )
        t_lower = text.lower()
        if any(p in t_lower for p in unit_phrases):
            return True

        return False

    @classmethod
    def _is_compound_word_tao(cls, text: str, start: int, end: int, word: str) -> bool:
        """
        Kiểm tra xem 'tao' có phải là từ ghép 'nhân tạo', 'sáng tạo', 'tạo ra', 'tạo thành' hay không.
        Tránh bắt nhầm khi học sinh gõ tiếng Việt không dấu: 'thay la tri tue nhan tao'.
        """
        if word.lower() != "tao":
            return False
        before = text[:start].strip().lower()
        if re.search(r"\b(nhân|nhan|sáng|sang|cấu|cau|chế|che|đào|dao)\s*$", before):
            return True
        after = text[end:].strip().lower()
        if re.search(r"^(ra|thành|thanh|nên|nen|lập|lap|tác|tac)\b", after):
            return True
        return False

    @classmethod
    def _init_profanity_regexes(cls) -> None:
        """Biên dịch các bộ regex nhận diện thô tục, lách ký tự và xúc phạm."""
        if hasattr(cls, "_profanity_regexes_initialized"):
            return

        escaped = [re.escape(w) for w in cls.PROFANITY_LIST]
        cls._compiled_profanity_re = re.compile(rf"\b({'|'.join(escaped)})\b", re.IGNORECASE | re.UNICODE)

        # Lách ký tự bằng dấu chấm, gạch nối, gạch dưới: d.m, v.l, c.ặ.c, đ.é.o, l.ồ.n, b.u.ồ.i...
        cls._obfuscated_profanity_re = re.compile(
            r"(?i)\b("
            r"d[\.\-_]m(?!\s*=)|v[\.\-_]l|v[\.\-_][ck][\.\-_]l|c[\.\-_]l[\.\-_]m|d[\.\-_]k[\.\-_]m|đ[\.\-_]k[\.\-_]m|đ[\.\-_]c[\.\-_]l[\.\-_]m|"
            r"c[\.\-_]ặ[\.\-_]c|c[\.\-_]a[\.\-_]c|đ[\.\-_]é[\.\-_]o|đ[\.\-_]e[\.\-_]o|l[\.\-_]ồ[\.\-_]n|l[\.\-_]o[\.\-_]n|"
            r"b[\.\-_]u[\.\-_]ồ[\.\-_]i|b[\.\-_]u[\.\-_]o[\.\-_]i|đ[\.\-_]ị[\.\-_]t|đ[\.\-_]i[\.\-_]t|"
            r"đ[\.\-_]ụ(?:\s*|[\.\-_])m[\.\-_]á|đ[\.\-_]ụ(?:\s*|[\.\-_])m[\.\-_]ẹ"
            r")\b"
        )

        # Lách ký tự bằng khoảng trắng cách rời: đ m, d m, v c l, c l m, c ặ c, c a c, l ồ n, l o n, đ é o, đ e o, b u ồ i...
        cls._spaced_profanity_re = re.compile(
            r"(?i)\b("
            r"đ\s+m(?!\s*=)|d\s+m(?!\s*=)|v\s+c\s+l(?:\s+l)*|c\s+l\s+m(?:\s+m)*|c\s+[ặa]\s+c|"
            r"l\s+[ồo]\s+n|đ\s+[éẹeo]\s+o|b\s+u\s+[ồo]\s+i|đ\s+ụ(?:\s+m\s+[áẹ]|\s+(?:má|mẹ))|"
            r"đ\s+k\s+m|v\s+k\s+l|d\s+c\s+m|đ\s+c\s+l\s+m|đ\s+[ịi]\s+t|d\s+i\s+t|"
            r"d\s+a\s+i\s+chứ|s\s+m\s+l|d\s+m\s+m|q\s+q\s+gì"
            r")\b"
        )

        # Ký tự leetspeak, dấu sao, ký hiệu thay thế: d*m, đ*m, v*l, cl*m, c*c, l*n, b*ồi, d!t, đ!t, d@y nhu cc, bot r@c...
        cls._leetspeak_profane_re = re.compile(
            r"(?i)\b("
            r"[dđ]\*+m|v\*+l|cl\*+m|[dđ]\*+o|c\*+c|l\*+n|b\*+[ồo]i|"
            r"d[!1]t|đ[!1]t|d@y\s+nhu\s+cc|bot\s+r@c|r@c\s+ruoi|d0t\s+nhu\s+bo|"
            r"[dđ]\*+k\*+m|[dđ]\.m\.m\.m|v\.c\.l\.l|c\.l\.m\.m"
            r")\b"
        )

        # Tục tĩu gõ KHÔNG DẤU phổ biến: thay lo, thang lo, bot rac, bo di cac, oc cho, me kiep, vai lon, dau buoi, an cac, nung lon, du ma, du me...
        cls._unaccented_profane_re = re.compile(
            r"(?i)\b("
            r"thay\s+lo|thang\s+lo|bot\s+rac|thang\s+bot\s+rac|con\s+bot\s+rac|"
            r"bo\s+di\s+cac|bo\s+di\s+buoi|bo\s+di\s+dai|"
            r"oc\s+cho|oc\s+bo|oc\s+lon|oc\s+cut|oc\s+tom|oc\s+ba\s+dau|oc\s+heo|"
            r"me\s+kiep|vai\s+lon|vai\s+ca\s+lon|vai\s+cac|vai\s+buoi|"
            r"thang\s+lon|con\s+lon|mat\s+lon|ham\s+lon|xao\s+lon|ngu\s+lon|"
            r"dau\s+buoi|bu\s+buoi|an\s+buoi|liem\s+buoi|an\s+cac|bu\s+cu|dau\s+khac|"
            r"nung\s+lon|nung\s+cac|nung\s+sang|"
            r"du\s+ma|du\s+me|dau\s+ma|di\s+me|con\s+di\s+me|"
            r"giang\s+kieu\s+deo\s+gi|day\s+kieu\s+deo\s+gi|deo\s+hieu|deo\s+biet|deo\s+them|"
            r"cut\s+me\s+may|cut\s+me\s+may\s+di|cut\s+di\s+cho\s+ranh|day\s+nhu\s+cc|giai\s+nhu\s+cc"
            r")\b"
        )

        # Kéo dài ký tự: dmmm, vclll, đéooo, cặccc, lồnnn, buồiii, đụuuuuuu, đệchhhh...
        cls._elongated_profanity_re = re.compile(
            r"(?i)\b("
            r"d+m{2,}|d{2,}m+|v+c+l{2,}|v+l{2,}|đ[éẹo]+[eo]{2,}|c[ặặc]+[ac]{2,}|l[ồồn]+[on]{2,}|"
            r"b[uù]+[oòồóô]+[iì]{2,}|bu[ồo]+i{2,}|b[uù]+[oòo]+[iìi]{2,}|đ[ệe]+ch+|đ[ệe]ch{2,}|d[áái]+[ai]{2,}|m[ẹẹ]+[e]*\s+kiếp|"
            r"đ[ụu]{2,}|c+l+m{2,}|v+ã+i+\s+lồn|"
            r"ngu{3,}\s+như\s+(?:chó|bò|lợn)|c+ú+t{2,}\s+(?:mẹ|đi|hộ)"
            r")\b"
        )

        # Cụm từ xúc phạm thầy cô / bot gia sư đặc trưng học sinh & Tiếng Anh toxic
        cls._targeted_insult_re = re.compile(
            r"(?i)\b("
            r"thầy\s+lỏ|thằng\s+lỏ|bot\s+lỏ|con\s+lỏ|dạy\s+lỏ|"
            r"bot\s+rác|thằng\s+bot\s+rác|con\s+bot\s+rác|thợ\s+dạy\s+rác|thằng\s+thợ\s+dạy|"
            r"dạy\s+như\s+cc|dạy\s+làm\s+cc|như\s+hạch\s+dạy|như\s+cc|"
            r"dạy\s+dốt\s+như\s+bò|ngu\s+như\s+bò\s+mà\s+cũng\s+đòi|dốt\s+như\s+chó\s+bày\s+đặt|"
            r"dốt\s+từ\s+trong\s+trứng|dot\s+tu\s+trong\s+trung|"
            r"thằng\s+cha\s+này\s+bị\s+khùng|thằng\s+cha\s+này|bị\s+khùng\s+giải|giải\s+ngu\s+như\s+chó|ngu\s+như\s+chó|"
            r"bố\s+dí\s+cặc|bố\s+dí\s+buồi|bố\s+dí\s+dái|bố\s+éo\s+thèm|bố\s+đéo\s+thèm|"
            r"thầy\s+mõm|thay\s+mom|thợ\s+dạy\s+mõm|tho\s+day\s+mom|bot\s+mõm|bot\s+mom|"
            r"óc\s+tôm|oc\s+tom|óc\s+bã\s+đậu|oc\s+ba\s+dau|óc\s+heo|oc\s+heo|"
            r"bại\s+não|bai\s+nao|mõm\s+chó|mặt\s+phụ\s+khoa|đồ\s+thần\s+kinh|thần\s+kinh\s+giải\s+bậy|biến\s+mẹ\s+đi|"
            r"dumbass|gtfo|kys|motherfuck(?:er|ing)?|screw\s+you|stupid\s+bastard|piece\s+of\s+garbage|idiot\s+teacher|"
            r"suck\s+my\s+dick|eat\s+shit|what\s+the\s+hell\s+giải\s+ngu|"
            r"bullshit|stfu|eat\s+my\s+balls|useless\s+trash|trash\s+bot|shut\s+your\s+face|shut\s+the\s+hell\s+up"
            r")\b"
        )

        cls._profanity_regexes_initialized = True

    @classmethod
    def has_real_profanity(cls, text: str) -> bool:
        """
        Kiểm tra xem văn bản có chứa từ ngữ thô tục / xúc phạm thực sự hay không.
        Tự động loại trừ các đơn vị đo lường toán học (dm, ml, cc) bị trùng ký tự.
        """
        if not text:
            return False

        cls._init_profanity_regexes()

        # 1. Quét từ thô tục gốc
        for m in cls._compiled_profanity_re.finditer(text):
            if cls._is_math_measurement_unit(text, m.start(), m.end(), m.group(0)):
                continue
            if cls._is_compound_word_tao(text, m.start(), m.end(), m.group(0)):
                continue
            return True

        # 2. Quét từ lách ký tự (obfuscated)
        m_obf = cls._obfuscated_profanity_re.search(text)
        if m_obf:
            matched_obf = m_obf.group(0).lower()
            # Ngoại lệ toán học đối với d.m
            if "d.m" in matched_obf or "d-m" in matched_obf or "d_m" in matched_obf:
                t_low = text.lower()
                is_math_dm = (
                    "đoạn thẳng d.m" in t_low
                    or "đoạn thẳng d-m" in t_low
                    or "tích d.m" in t_low
                    or "khoảng cách d.m" in t_low
                    or "d.m =" in t_low
                    or "= d.m" in t_low
                )
                if not is_math_dm:
                    return True
            else:
                return True

        # 3. Quét ký tự kéo dài
        if cls._elongated_profanity_re.search(text):
            return True

        # 4. Quét từ lách bằng khoảng trắng cách rời (spaced letters)
        if cls._spaced_profanity_re.search(text):
            return True

        # 5. Quét leetspeak và ký hiệu thay thế
        if cls._leetspeak_profane_re.search(text):
            return True

        # 6. Quét từ thô tục gõ không dấu
        if cls._unaccented_profane_re.search(text):
            return True

        # 7. Quét xúc phạm gia sư / bot học đường & tiếng Anh toxic
        if cls._targeted_insult_re.search(text):
            return True

        return False

    def reload_model(self, force: bool = True) -> bool:
        """
        US 10.4 (Task T10.4.3): Hot-Reloading mô hình Machine Learning trên RAM (Zero Downtime).
        Sử dụng kỹ thuật Atomic Swap, Double-Checked Lock & Pipeline Validation:
        1. Double-Checked Lock: Nếu force=False, kiểm tra lại mtime bên trong lock để tránh reload lặp.
        2. Kiểm tra kích thước file: st_size >= 512 bytes chống nạp file rỗng đang ghi dở.
        3. Deserialize cách ly: Nạp file mới vào biến tạm (local variable).
        4. Validation & Warm-up: Kiểm tra có predict_proba, classes_ và chạy thử mồi 1 câu.
        5. Atomic Swap: Hoán đổi con trỏ self._local_model tức thì (0.0001ms).
        6. Safe Fallback: Nếu bất kỳ bước nào lỗi, giữ nguyên mô hình cũ trên RAM.
        """
        with self._reload_lock:
            if not self._model_path.exists():
                print(f"[OrchestratorAgent] [WARN] File mô hình không tồn tại: {self._model_path}")
                return False

            try:
                stat_info = self._model_path.stat()
                current_mtime = stat_info.st_mtime

                # Double-Checked Locking khi gọi từ watcher tự động
                if not force and current_mtime <= self._last_loaded_mtime:
                    return True

                # Kiểm tra chống file đang được tạo/ghi dở (0 bytes hoặc quá nhỏ)
                if stat_info.st_size < 512:
                    print(f"[OrchestratorAgent] [WARN] File mô hình quá nhỏ ({stat_info.st_size} bytes), có thể đang ghi dở. Bỏ qua.")
                    return False

                # 1. Nạp vào biến tạm cục bộ (hoàn toàn cách ly, không ảnh hưởng self._local_model đang chạy)
                new_pipeline = joblib.load(self._model_path)

                # 2. Pipeline Validation (Kiểm tra interface chuẩn scikit-learn)
                if not hasattr(new_pipeline, "predict_proba") or not hasattr(new_pipeline, "classes_"):
                    raise ValueError("Mô hình không có phương thức predict_proba hoặc classes_ hợp lệ.")

                # 3. Warm-up Sanity Check (Chạy thử mồi 1 câu xác nhận pipeline hoạt động trơn tru)
                _ = new_pipeline.predict_proba(["kiểm tra khởi động"])[0]

                # 4. Atomic Swap: Hoán đổi tham chiếu bộ nhớ RAM tức thì (0.0001ms)
                self._local_model = new_pipeline
                self._last_loaded_mtime = current_mtime
                classes_str = ", ".join(new_pipeline.classes_)
                print(f"[OrchestratorAgent] [HOT-RELOAD SUCCESS] Đã nạp mô hình mới vào RAM ({stat_info.st_size // 1024}KB, mtime={self._last_loaded_mtime:.2f}, classes=[{classes_str}])")
                return True
            except Exception as e:
                print(f"[OrchestratorAgent] [ERROR] Lỗi khi nạp mô hình (giữ nguyên bản cũ trên RAM): {e}")
                return False

    def get_model_info(self) -> dict:
        """
        US 10.4: Cung cấp thông tin trạng thái mô hình hiện tại phục vụ API Retrain (T10.4.4)
        và Dashboard Giám Sát Agent (T10.4.5).
        """
        file_exists = self._model_path.exists()
        file_size_kb = round(self._model_path.stat().st_size / 1024, 2) if file_exists else 0.0
        classes_list = list(self._local_model.classes_) if (self._local_model and hasattr(self._local_model, "classes_")) else []
        return {
            "is_loaded": self._local_model is not None,
            "model_path": str(self._model_path),
            "file_exists": file_exists,
            "file_size_kb": file_size_kb,
            "last_loaded_mtime": self._last_loaded_mtime,
            "classes": classes_list,
        }

    @staticmethod
    def _normalize_latex_math(text: str) -> str:
        """
        Chuẩn hóa ký hiệu toán LaTeX phổ biến sang biểu thức ASCII/SymPy thống nhất:
        - Loại bỏ \\text{...}, $, $$, \\left, \\right, khoảng trắng mảnh \\, \\; \\!
        - Chuyển \\times, \\cdot, ×, · -> *, \\div, ÷ -> /
        - Chuyển \\frac{a}{b}, \\frac52, \\frac 5 2, \\dfrac, \\tfrac (kể cả âm -\\frac...)
        - Thu gọn dấu trừ đơn ngôi sau khoảng trắng ('- 5/2' -> '-5/2') mà không đụng phép trừ nhị phân ('10 - 5/2').
        """
        if not text:
            return ""
        s = text
        while re.search(r"\\text\s*\{([^{}]*)\}", s):
            s = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", s)
        s = re.sub(r"\\[,;!]", " ", s)
        s = re.sub(r"\\(?:left|right)\b", "", s)
        s = re.sub(r"\$+", " ", s)

        s = re.sub(r"\\(?:times|cdot)\b", " * ", s)
        s = re.sub(r"\\div\b", " / ", s)
        s = s.replace("×", " * ").replace("·", " * ").replace("÷", " / ")

        def _fmt_frac(num: str, den: str) -> str:
            n = num.strip()
            d = den.strip()
            if re.fullmatch(r"-?\d+(?:\.\d+)?", n) and re.fullmatch(r"\d+(?:\.\d+)?", d):
                return f"{n}/{d}"
            return f"({n})/({d})"

        braced_re = re.compile(
            r"\\(?:d|t)?frac\s*\{((?:[^{}]|\{[^{}]*\})+)\}\s*\{((?:[^{}]|\{[^{}]*\})+)\}"
        )
        for _ in range(3):
            new_s = braced_re.sub(lambda m: _fmt_frac(m.group(1), m.group(2)), s)
            if new_s == s:
                break
            s = new_s

        # Hỗn hợp \frac{a}b hoặc \frac a{b}
        s = re.sub(
            r"\\(?:d|t)?frac\s*\{([^{}]+)\}\s*([a-zA-Z\d])",
            lambda m: _fmt_frac(m.group(1), m.group(2)),
            s,
        )
        s = re.sub(
            r"\\(?:d|t)?frac\s*([a-zA-Z\d])\s*\{([^{}]+)\}",
            lambda m: _fmt_frac(m.group(1), m.group(2)),
            s,
        )

        # Dạng không ngoặc nhọn: \frac52 hoặc \frac 5 2 hoặc \frac x 2
        s = re.sub(
            r"\\(?:d|t)?frac\s*([a-zA-Z\d])\s*([a-zA-Z\d])",
            lambda m: _fmt_frac(m.group(1), m.group(2)),
            s,
        )

        # Thu gọn dấu trừ đơn ngôi bị tách khoảng trắng ('- 5/2' -> '-5/2', 'x = - 5/2' -> 'x = -5/2')
        s = re.sub(r"(^|[=(\[:,])\s*-\s+(?=\d)", r"\1-", s)
        s = re.sub(r"(\b(?:là|bằng|ra)\s+)-\s+(?=\d)", r"\1-", s, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def _preprocess_latex_math(text: str) -> str:
        """Alias tương thích ngược cho _normalize_latex_math."""
        return OrchestratorAgent._normalize_latex_math(text)

    @staticmethod
    def _is_explicit_switch_signal(text: str) -> bool:
        """Nhận diện tín hiệu đổi bài/ảnh mới rõ ràng để không lục lại phương trình bài cũ."""
        if not text:
            return False
        t = text.lower().strip()
        if any(kw in t for kw in (
            "đổi bài", "bài khác", "làm bài khác", "sang bài", "chuyển bài",
            "thôi bài này", "bỏ qua bài này", "bỏ bài này", "không làm nữa",
            "ko làm nữa", "bài tiếp theo", "câu khác", "bài mới", "ảnh mới",
        )):
            return True
        if re.search(r"^(?:bài|câu)\s*\d+\s*[:\.]", t) and "=" not in t:
            return True
        if any(k in t for k in (
            "tính chu vi", "tính diện tích", "tính thể tích", "hãy chứng minh",
            "chứng minh rằng", "tính giá trị", "rút gọn biểu thức",
        )) and "=" not in t and not re.search(r"(?:^|\b)(?:là|bằng|ra|được)\s*-?\d", t):
            return True
        return False

    @staticmethod
    def _is_new_problem_switch(text: str) -> bool:
        """Alias giữ tương thích cho _is_explicit_switch_signal."""
        return OrchestratorAgent._is_explicit_switch_signal(text)

    @staticmethod
    def _slice_history_at_problem_boundary(history_text: str) -> str:
        """Cắt lịch sử hội thoại tại ranh giới bài toán mới nhất để tránh kéo phương trình bài cũ."""
        if not history_text:
            return ""
        blocks = [
            b.strip()
            for b in re.split(r"(?im)^(?=\[(?:USER|STUDENT|AGENT|ASSISTANT|MODEL|THẦY)\]|(?:User|Model|Assistant):)", history_text)
            if b.strip()
        ]
        if len(blocks) <= 1:
            if "[NEW_PROBLEM_BOUNDARY]" in history_text:
                return history_text.rsplit("[NEW_PROBLEM_BOUNDARY]", 1)[-1].strip()
            return history_text

        user_prefixes = ("[user", "[student", "user:")
        agent_prefixes = ("[agent", "[assistant", "[model", "[thầy", "model:", "assistant:")
        start_idx = 0
        for i in range(len(blocks) - 1, -1, -1):
            b = blocks[i]
            b_low = b.lower()
            if "[new_problem_boundary]" in b_low:
                start_idx = i
                break
            if any(b_low.startswith(p) for p in agent_prefixes):
                if "[comprehension_check]" in b_low or "mẫu trình bày hoàn chỉnh" in b_low or "chúc mừng em đã hoàn thành" in b_low:
                    start_idx = i + 1
                    break
            elif any(b_low.startswith(p) for p in user_prefixes):
                content = re.sub(r"^\[[^\]]+\]\s*:?\s*|^[a-zA-Z]+:\s*", "", b).strip()
                if OrchestratorAgent._is_explicit_switch_signal(content):
                    start_idx = i
                    break

        if start_idx >= len(blocks):
            return ""
        return "\n".join(blocks[start_idx:])

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip() if text else ""

    @staticmethod
    def _extract_tail_for_eval(text: str) -> str:
        """Ưu tiên trích vế kết luận cuối sau '=', 'kết quả', 'đáp án', 'bằng', 'ra', 'mất', 'là' nếu có số."""
        s = OrchestratorAgent._normalize_latex_math(text)
        if "=" in s:
            eq_tail = s.rsplit("=", 1)[-1].strip()
            m_after = list(re.finditer(r"\b(?:kết quả(?:\s+cuối(?:\s+cùng)?)?|đáp án|bằng|tính được|ra(?:\s+là)?|mất|chọn|nên|vậy|suy ra|(?<!tức\s)là)\b", eq_tail, re.IGNORECASE))
            if m_after:
                cand_after = eq_tail[m_after[-1].end():].strip()
                if re.search(r"\d", cand_after):
                    return cand_after
            if re.search(r"\d", eq_tail):
                return eq_tail
        m_kw = list(re.finditer(r"\b(?:kết quả(?:\s+cuối(?:\s+cùng)?)?|đáp án|bằng|tính được|ra(?:\s+là)?|mất|chọn|(?<!tức\s)là)\b", s, re.IGNORECASE))
        if m_kw:
            tail = s[m_kw[-1].end():].strip()
            if re.search(r"\d", tail):
                return tail
        return s

    @staticmethod
    def _extract_fraction(text: str) -> Tuple[Optional[Fraction], Optional[str]]:
        """Trích xuất số/phân số từ văn bản (hỗ trợ LaTeX \\frac), bỏ qua 'câu 1', 'bài 2'."""
        raw_norm = OrchestratorAgent._normalize_latex_math(text)
        # Chỉ ưu tiên vế kết luận nếu vế đó có số và không chứa biến chữ cái đại số còn dang dở
        tail = OrchestratorAgent._extract_tail_for_eval(raw_norm)
        s = tail if (tail != raw_norm and not re.search(r"(?<![a-zA-Z\u00C0-\u1EF9])[xy](?![a-zA-Z\u00C0-\u1EF9])", tail, re.IGNORECASE)) else raw_norm
        s = re.sub(r"\b(câu|bài|trang|đề)\s*\d+\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(?:m|cm|dm|mm|km)\s*\^?\s*[²³23]\b", " ", s, flags=re.IGNORECASE)
        s = s.replace("²", "").replace("³", "")
        s = re.sub(r"(?<=\d)\s+(?=\d{3}\b)", "", s)
        s = s.replace(",", ".")
        matches = list(re.finditer(r"-?\d+(?:/-?\d+|\.\d+)?", s))
        if not matches:
            return None, None
        cand = next((m.group(0) for m in matches if "/" in m.group(0) or "." in m.group(0)), None)
        if not cand:
            cand = matches[-1].group(0)
        try:
            if "/" in cand:
                n, d = cand.split("/")
                return (Fraction(int(n), int(d)), cand) if int(d) != 0 else (None, None)
            elif "." in cand:
                return Fraction(cand), cand
            else:
                return Fraction(int(cand)), cand
        except Exception:
            return None, None

    @staticmethod
    def _eval_math_expr(text: str) -> Optional[Fraction]:
        """
        Đánh giá biểu thức toán học đơn giản bằng sympy.
        Hỗ trợ LaTeX (\\frac, \\times, \\div, \\cdot), 3x3+5, (2+3)*4, 2^3, 1/2+1/3, câu có chữ mở đầu.
        Tránh đánh giá nhầm số thập phân vô hạn tuần hoàn 0,(5), biểu thức còn biến, hay đơn vị phức hợp.
        """
        s = OrchestratorAgent._normalize_latex_math(text)
        if re.search(r"\d+\s*,\s*\(\d+\)", s):
            return None
        s = OrchestratorAgent._extract_tail_for_eval(s)
        s = re.sub(r"\b(câu|bài|trang|đề)\s*\d+\b", "", s, flags=re.IGNORECASE)
        s = re.sub(r"(?<=\d),(?=\d)", ".", s)
        s = re.sub(r"\b(?:m|cm|dm|mm|km)\s*\^?\s*[²³23]\b", " ", s, flags=re.IGNORECASE)
        s = s.replace("²", "").replace("³", "")
        expr = re.sub(r"(\d)\s*x\s*(\d)", r"\1*\2", s, flags=re.IGNORECASE)
        expr = expr.replace(":", "/").replace("^", "**")
        candidates = [c.strip() for c in re.findall(r"[\d\s\+\-\*\/\(\)\.]+", expr) if re.search(r"\d", c)]
        if not candidates:
            return None
        target_expr = max(candidates, key=len)
        try:
            result = sympy.sympify(target_expr)
            if hasattr(result, "p") and hasattr(result, "q"):
                return Fraction(int(result.p), int(result.q))
            r_exact = sympy.nsimplify(result, rational=True)
            if hasattr(r_exact, "p") and hasattr(r_exact, "q"):
                return Fraction(int(r_exact.p), int(r_exact.q))
            return Fraction(str(round(float(result), 9))).limit_denominator(10000)
        except Exception:
            return None

    @staticmethod
    def _normalize_math_expr(s: str) -> str:
        """
        Chuẩn hóa biểu thức toán học trước khi đưa vào SymPy:
        - Chuẩn hóa LaTeX (\\frac, \\times, \\div, \\cdot)
        - Thêm dấu nhân ngầm: 2x -> 2*x, 2(x+1) -> 2*(x+1), )( -> )*(, )x -> )*x, x( -> x*(
        - Chuyển lũy thừa ^ -> ** và phép chia : -> /
        """
        s = OrchestratorAgent._normalize_latex_math(s)
        s = re.sub(r"(?<=\d),(?=\d)", ".", s)
        s = re.sub(r"(\d)\s*([a-zA-Z])", r"\1*\2", s)
        s = re.sub(r"(\d)\s*\(", r"\1*(", s)
        s = re.sub(r"\)\s*\(", r")*(", s)
        s = re.sub(r"\)\s*([a-zA-Z\d])", r")*\1", s)
        s = re.sub(r"([a-zA-Z])\s*\(", r"\1*(", s)
        s = s.replace("^", "**")
        s = s.replace(":", "/")
        return s

    @staticmethod
    def _clean_extracted_equation(raw: str) -> str:
        """Làm sạch phương trình thô trích xuất từ câu hỏi học sinh (giữ nguyên phép chia 'x : 8 = 15')."""
        raw = raw.strip()
        m_pref = re.match(r"^([a-zA-Z])\s*:\s*(.+)$", raw)
        if m_pref:
            p_var, rest = m_pref.group(1), m_pref.group(2)
            # Xóa nhãn tiền tố ('a: ...', 'tìm x: 48500 - x = 19200') khi phần sau vẫn chứa phương trình có ẩn
            if re.search(rf"(?<![a-zA-Z]){re.escape(p_var)}(?![a-zA-Z])", rest, re.IGNORECASE) or (
                p_var.lower() in ("a", "b", "c", "d") and re.search(r"[a-zA-Z]", rest)
            ):
                raw = rest
        raw = re.sub(r"^[^\d\(\+\-a-zA-Z]+", "", raw)
        raw = re.sub(r"[^\d\)\w]+$", "", raw)
        return raw.strip()

    @staticmethod
    def _solve_simple_linear_equation(raw_eq: str) -> Optional[Tuple[str, Fraction, str]]:
        """
        Giải phương trình bậc nhất một ẩn (ví dụ: '3x + 10 = 25', '2x - 4 = 10', '2(x+1) = 8', 'x/2 + 3 = 7').
        Trả về: (tên biến, nghiệm Fraction, phương trình chuẩn).
        """
        try:
            if "=" not in raw_eq:
                return None
            # Bỏ qua ký hiệu hàm như f(-2) = ... hoặc đơn vị đo 22 m, 2.5 m ở cuối vế
            if re.search(r"\b[a-zA-Z]\s*\(\s*-?\d", raw_eq):
                return None
            if re.search(r"=\s*[\d\.\+\-\*\/\s]+\s+(?:m|cm|dm|mm|km|g|kg|l|ml|s|h|ha)\s*$", raw_eq, re.IGNORECASE):
                return None
            cleaned_units_eq = re.sub(
                r"(?<=\d)\s*(?:m|cm|dm|mm|km|g|kg|l|ml|s|h|ha)\b",
                "",
                raw_eq,
                flags=re.IGNORECASE,
            )
            lhs_str, rhs_str = cleaned_units_eq.split("=", 1)
            lhs_norm = OrchestratorAgent._normalize_math_expr(lhs_str)
            rhs_norm = OrchestratorAgent._normalize_math_expr(rhs_str)

            all_vars = set(re.findall(r"[a-zA-Z]", lhs_norm + rhs_norm))
            if len(all_vars) != 1:
                return None
            var_name = list(all_vars)[0]
            var_sym = sympy.symbols(var_name)

            lhs_expr = sympy.sympify(lhs_norm)
            rhs_expr = sympy.sympify(rhs_norm)

            eq = sympy.Eq(lhs_expr, rhs_expr)
            sols = sympy.solve(eq, var_sym)
            if len(sols) == 1:
                sol = sols[0]
                if hasattr(sol, "p") and hasattr(sol, "q"):
                    return var_name, Fraction(sol.p, sol.q), raw_eq.strip()
                val = float(sol)
                return var_name, Fraction(val).limit_denominator(1000), raw_eq.strip()
        except Exception:
            return None
        return None

    def _check_linear_equation_progress(
        self,
        original_message: str,
        history_text: str = "",
        problem_context: Optional[dict] = None,
        student_grade: Optional[int] = None,
    ) -> Optional[RoutingResult]:
        """
        Trụ cột 1 — Nhận diện bài toán phương trình / tìm x & điều phối Socratic chuẩn xác:
        1. Chuẩn hóa LaTeX (\frac{a}{b}, \frac52) trước khi trích xuất phương trình và nghiệm.
        2. Tránh bám nhầm phương trình cũ trong history nếu học sinh vừa chuyển sang bài/câu khác.
        3. Điều phối SCAFFOLDING với chỉ đạo phân tầng theo cấp lớp (Lớp 4–5 / 6–7 / 8–9) và khung điền khuyết \square không lộ phép tính.
        """
        msg_norm_latex = self._normalize_latex_math(original_message)
        msg_norm_latex = re.sub(r"(?<=\d),(?=\d)", ".", msg_norm_latex)
        # Bỏ qua linear equation parser nếu bài/câu chứa đơn vị thời gian phức hợp (giờ phút, tấn tạ...)
        ctx_blob = " ".join(
            str(problem_context.get(k) or "")
            for k in ("problemText", "problem_text", "problem")
        ) if problem_context else ""
        if re.search(r"\b(?:giờ|phút|giây)\b.*\b(?:phút|giây|giờ)\b|\b(?:tấn|tạ|yến)\b", f"{msg_norm_latex} {ctx_blob}", re.IGNORECASE):
            return None
        # Bỏ qua linear 1-ẩn nếu bài toán có hệ phương trình hoặc nhiều biến độc lập (VD hệ x, y tính T = 3x - y)
        distinct_alg_vars = set(
            re.findall(r"(?<![a-zA-Z\u00C0-\u1EF9])[xyzT](?![a-zA-Z\u00C0-\u1EF9])", f"{msg_norm_latex} {ctx_blob}")
        )
        if len(distinct_alg_vars) > 1 or re.search(r"hệ\s+phương\s+trình", f"{msg_norm_latex} {ctx_blob}", re.IGNORECASE):
            return None
        # Bỏ qua bài có rẽ nhánh nhiều nghiệm ('hoặc', bậc 2 '^2', giá trị tuyệt đối '|...|')
        if "hoặc" in original_message.lower() or re.search(r"\^2|\|[^|]+\|", ctx_blob):
            return None
        # 1. Tìm phương trình gốc & đáp án chuẩn từ problem_context (trừ khi học sinh đang đổi bài mới)
        ctx_target = None
        ctx_sol_frac = None
        ctx_sol_raw = None
        is_switch_sig = self._is_explicit_switch_signal(msg_norm_latex)
        if not is_switch_sig and problem_context:
            raw_ctx_sol = problem_context.get("correctSolution") or problem_context.get("correct_solution")
            if raw_ctx_sol is not None:
                ctx_sol_frac, ctx_sol_raw = self._extract_fraction(str(raw_ctx_sol))
            for k in ("problemText", "problem_text", "problem", "title", "content"):
                val = problem_context.get(k)
                if val and isinstance(val, str):
                    ctx_s = re.sub(r"(?<=\d),(?=\d)", ".", self._normalize_latex_math(val))
                    for raw in reversed(self._equation_re.findall(ctx_s)):
                        res = self._solve_simple_linear_equation(self._clean_extracted_equation(raw))
                        if res and not re.match(rf"^{res[0]}\s*=\s*-?\d+(?:\.\d+)?(?:/\d+)?$", res[2].strip(), re.IGNORECASE):
                            ctx_target = res
                            break
                if ctx_target:
                    break

        # 2. Quét tìm phương trình đại số trong tin nhắn hiện tại
        eq_in_msg = self._equation_re.findall(msg_norm_latex)
        solved_target = None
        eq_source = "msg"

        for raw in reversed(eq_in_msg):
            cleaned = self._clean_extracted_equation(raw)
            res = self._solve_simple_linear_equation(cleaned)
            if res:
                v_name, sol, eq_clean = res
                is_trivial_assign = bool(re.match(rf"^{v_name}\s*=\s*-?\d+(?:\.\d+)?(?:/\d+)?$", eq_clean.strip(), re.IGNORECASE))
                lhs_part, rhs_part = eq_clean.split("=", 1)
                is_student_solve_expr = (
                    lhs_part.strip().lower() == v_name.lower()
                    and not re.search(rf"(?<![a-zA-Z]){re.escape(v_name)}(?![a-zA-Z])", rhs_part, re.IGNORECASE)
                    and bool(history_text.strip() or (problem_context and (problem_context.get("problemText") or problem_context.get("problem_text"))))
                )
                if not is_trivial_assign and not is_student_solve_expr:
                    # Nếu đang trong cùng 1 bài (không đổi bài) và problem_context đã có phương trình gốc cùng ẩn:
                    # kiểm tra xem phương trình biến đổi của học sinh có cùng nghiệm với đề gốc không
                    if ctx_target and (history_text.strip() or ctx_target[0].lower() == v_name.lower()):
                        if sol != ctx_target[1] and v_name.lower() == ctx_target[0].lower():
                            task = (
                                f"Học sinh đang giải bài '{ctx_target[2]}' (đáp án đúng {ctx_target[0]} = {ctx_target[1]}), "
                                f"nhưng viết bước biến đổi '{eq_clean}' (cho ra {sol} != {ctx_target[1]}). "
                                "Bạn là THẦY GIÁO: nhẹ nhàng chỉ ra bước chuyển vế/biến đổi vừa rồi bị sai dấu hoặc sai phép tính, "
                                "đặt câu hỏi gợi mở kèm khung \\square để học sinh tự sửa lại bước đó. KHÔNG nói lộ đáp án và KHÔNG gắn [COMPREHENSION_CHECK]."
                            )
                            return RoutingResult(
                                selected_agent="MISCONCEPTION",
                                task_description=task,
                                routing_scratchpad=f"[Trụ1] Linear step equation mismatch: {eq_clean} (sol={sol}) != {ctx_target[2]} (sol={ctx_target[1]})",
                                emotion_flag="WRONG",
                            )
                        solved_target = ctx_target
                        eq_source = "ctx"
                    elif (
                        not is_switch_sig
                        and ctx_sol_frac is not None
                        and sol != ctx_sol_frac
                        and bool(history_text.strip())
                        and not re.search(r"hệ\s+phương\s+trình|bất\s+phương\s+trình", ctx_blob, re.IGNORECASE)
                        and len(set(re.findall(r"(?<![a-zA-Z\u00C0-\u1EF9])[xyzT](?![a-zA-Z\u00C0-\u1EF9])", msg_norm_latex))) <= 1
                        and self._eval_math_expr(msg_norm_latex) != ctx_sol_frac
                    ):
                        task = (
                            f"Học sinh vừa thiết lập/biến đổi '{eq_clean}' (cho ra {v_name} = {sol}, chưa khớp đáp án đúng {ctx_sol_raw}). "
                            "Bạn là THẦY GIÁO: nhẹ nhàng ghi nhận ý đúng nếu có, chỉ ra chỗ nhầm dấu khi chuyển vế hoặc biểu thức lập chưa chuẩn, "
                            "đặt câu hỏi gợi mở kèm khung \\square để học sinh tự sửa lại bước đó. "
                            "TUYỆT ĐỐI KHÔNG khen 'hoàn toàn đúng'/'chính xác', KHÔNG nói lộ đáp án và KHÔNG gắn [COMPREHENSION_CHECK]."
                        )
                        return RoutingResult(
                            selected_agent="MISCONCEPTION",
                            task_description=task,
                            routing_scratchpad=f"[Trụ1] Linear context solution mismatch: {eq_clean} ({sol}) != ctx_sol ({ctx_sol_frac})",
                            emotion_flag="WRONG",
                        )
                    else:
                        solved_target = res
                    break
                elif not solved_target and not is_student_solve_expr:
                    solved_target = res

        # 3. Nếu tin nhắn hiện tại không chứa phương trình đầy đủ, tìm trong context & history đã cắt ranh giới
        if not solved_target or bool(re.match(rf"^{solved_target[0]}\s*=\s*-?\d+(?:\.\d+)?(?:/\d+)?$", solved_target[2].strip(), re.IGNORECASE)):
            if ctx_target:
                solved_target = ctx_target
                eq_source = "ctx"
            elif not self._is_explicit_switch_signal(msg_norm_latex):
                context_sources = []
                if history_text:
                    scoped_hist = self._slice_history_at_problem_boundary(history_text)
                    if scoped_hist:
                        user_lines = [
                            ln for ln in scoped_hist.splitlines()
                            if ln.strip().upper().startswith("[USER]")
                        ]
                        hist_target = "\n".join(user_lines) if user_lines else scoped_hist
                        hist_s = self._normalize_latex_math(hist_target)
                        context_sources.append(re.sub(r"(?<=\d),(?=\d)", ".", hist_s))

                for src in context_sources:
                    eq_in_ctx = self._equation_re.findall(src)
                    for raw in reversed(eq_in_ctx):
                        cleaned = self._clean_extracted_equation(raw)
                        res = self._solve_simple_linear_equation(cleaned)
                        if res:
                            v_name, sol, eq_clean = res
                            is_trivial_assign = bool(re.match(rf"^{v_name}\s*=\s*-?\d+(?:\.\d+)?(?:/\d+)?$", eq_clean.strip(), re.IGNORECASE))
                            if not is_trivial_assign:
                                solved_target = res
                                eq_source = "ctx"
                                break
                    if eq_source == "ctx":
                        break

        if not solved_target:
            return None

        var_name, true_sol, eq_str = solved_target

        # 4. Kiểm tra xem học sinh có đưa ra đề xuất nghiệm đã tính xong ở cuối không (tránh bắt 7/8 trong 'x = 7/8 - 1/4')
        ans_pattern = re.compile(
            rf"(?:(?:đáp án|dap an|nghiệm|nghiem|kết quả|ket qua|tính ra|tinh ra|ra|được)\s*(?:là|la\s*)?)?(?<![a-zA-Z\d_]){var_name}\s*=\s*(?:(?:[^=?!\n]*=\s*)+)?(-?\d+(?:\.\d+)?(?:/\d+)?)(?!\s*[\+\-\*\/x×÷:])"
            rf"|\b(?:đáp án|dap an|nghiệm|nghiem|kết quả|ket qua)\s*(?:là|la\s*)?(-?\d+(?:\.\d+)?(?:/\d+)?)(?!\s*[\+\-\*\/x×÷:])"
            rf"|(?:^|\b|[\d\)]\s*)(?:bằng|là|ra|được|=)\s*(-?\d+(?:\.\d+)?(?:/\d+)?)\s*(?:giờ|phút|cm|m|kg|ngày|tuổi|bạn|em|quyển)?\s*(?:\([^)]*\))?\s*(?:ạ|nhé|nha|hả|đúng|\?)?[\.\s]*$",
            re.IGNORECASE,
        )

        msg_without_eq = msg_norm_latex.replace(eq_str, " ")
        # Loại bỏ các phương trình bước biến đổi chứa ẩn (VD '6x - 12 = 3', '2x = -3 + 9 = 6', 'x - 4 = 7')
        # để không bắt nhầm vế phải của phương trình bước biến đổi làm đáp án x cuối!
        for raw_step in eq_in_msg:
            cleaned_step = self._clean_extracted_equation(raw_step)
            if "=" in cleaned_step:
                lhs_step = cleaned_step.split("=", 1)[0]
                rhs_step = cleaned_step.split("=", 1)[1]
                is_pure_isolated = bool(re.match(rf"^\s*{re.escape(var_name)}\s*$", lhs_step, re.IGNORECASE)) and not re.search(rf"(?<![a-zA-Z]){re.escape(var_name)}(?![a-zA-Z])", rhs_step, re.IGNORECASE)
                if re.search(rf"(?<![a-zA-Z]){re.escape(var_name)}(?![a-zA-Z])", lhs_step, re.IGNORECASE) and not is_pure_isolated:
                    msg_without_eq = msg_without_eq.replace(raw_step, " ")
        all_ans_matches = list(ans_pattern.finditer(msg_without_eq.strip()))
        m = all_ans_matches[-1] if all_ans_matches else None

        cand_str = None
        if m:
            if m.group(1) or m.group(2) or m.group(3):
                raw_cand = m.group(1) or m.group(2) or m.group(3)
                has_isolated_x_eq = bool(
                    re.search(
                        rf"(?<![\d\*\)\/\.a-zA-Z])\b{re.escape(var_name)}\s*=\s*-?\d+(?:\.\d+)?(?:/\d+)?\s*(?:ạ|nhé|nha|hả|\?|$|,|\.)",
                        msg_norm_latex,
                        re.IGNORECASE,
                    )
                )
                has_non_unit_coeff_lhs = bool(
                    re.search(rf"(?:\d+|\))\s*\*?\s*{re.escape(var_name)}\s*=", msg_norm_latex, re.IGNORECASE)
                )
                is_asking_next_step = bool(
                    re.search(r"\b(tiếp theo|bước đầu|bước tiếp|làm gì|làm sao)\b", msg_without_eq, re.IGNORECASE)
                )
                has_explicit_conclusion_word = bool(
                    re.search(r"\b(nên|suy ra|vậy|kết luận|đáp số|kết quả|chiều rộng|chiều dài)\b", msg_without_eq, re.IGNORECASE)
                )
                if not ((has_non_unit_coeff_lhs or is_asking_next_step) and not has_isolated_x_eq and not m.group(2) and (is_asking_next_step or not (m.group(3) and has_explicit_conclusion_word))):
                    cand_str = raw_cand
        elif eq_source == "msg":
            m_guess = re.search(r"\b(?:ra|được|bằng)\s*(-?\d+(?:\.\d+)?(?:/\d+)?)\s*(?:hả|đúng|ạ|\?)", msg_without_eq, re.IGNORECASE)
            if m_guess:
                cand_str = m_guess.group(1)
        elif eq_source == "ctx" and re.fullmatch(r"\s*-?\d+(?:\.\d+)?(?:/\d+)?\s*(?:ạ|nhé|nha)?\s*", msg_norm_latex, re.IGNORECASE):
            # Học sinh chỉ gõ mỗi số/phân số ở bước cuối hoặc khi bị hỏi (chỉ check nếu có dấu '/' hoặc ngữ cảnh đang ở bước cuối)
            # Lưu ý: ở bước 1 nếu học sinh trả lời số trung gian (vd: "12" trong 3x = 12), không coi nhầm là nghiệm cuối
            if "/" in msg_norm_latex:
                cand_frac_chk = msg_norm_latex.strip().split()[0]
                cand_str = cand_frac_chk

        # A. NẾU HỌC SINH ĐOÁN NGHIỆM:
        if cand_str:
            try:
                cand_frac, _ = self._extract_fraction(cand_str)
            except Exception:
                cand_frac = None

            if cand_frac is not None:
                if cand_frac == true_sol:
                    task = (
                        f"Học sinh đã giải đúng bài toán '{eq_str}' và tìm ra {var_name} = {cand_str} (kết quả đúng: {true_sol}). "
                        "Bạn là THẦY GIÁO: Khen ngợi học sinh đã tìm ra kết quả chính xác, trình bày ngắn gọn Mẫu trình bày hoàn chỉnh vào vở theo đúng cấp lớp, "
                        "và chốt bài bằng cách gắn tag [COMPREHENSION_CHECK]."
                    )
                    return RoutingResult(
                        selected_agent="SCAFFOLDING",
                        task_description=task,
                        routing_scratchpad=f"[Trụ1] Linear equation CORRECT: {eq_str} -> {var_name}={true_sol}",
                        emotion_flag="CORRECT",
                    )
                else:
                    has_transpose_step = any(s in msg_norm_latex.lower() for s in (
                        "chuyển vế", "chuyen ve", "qua thành", "qua thanh", "đổi dấu", "doi dau",
                        "-3", "- 3", "= 2", "=2"
                    ))
                    pedagogical_analysis = (
                        f"Phân tích sư phạm: Học sinh đã làm đúng bước đầu nhưng kết luận cuối {var_name} = {cand_str} chưa chính xác "
                        f"(kết quả đúng phải là {var_name} = {true_sol})."
                        if has_transpose_step else
                        f"Phân tích sư phạm: Học sinh đưa ra kết quả {var_name} = {cand_str} là SAI "
                        f"(kết quả đúng của bài '{eq_str}' phải là {var_name} = {true_sol})."
                    )
                    task = (
                        f"Học sinh đang giải bài '{eq_str}'. {pedagogical_analysis} "
                        "Bạn là THẦY GIÁO, điều phối sư phạm Socratic BẮT BUỘC: "
                        "1. Nếu học sinh có bước làm đúng, hãy khen ngợi bước đó. "
                        f"2. Nhẹ nhàng chỉ ra kết quả {var_name} = {cand_str} chưa khớp, không nói lộ đáp án hay phép tính cần dùng. "
                        "3. Đặt câu hỏi gợi mở kèm khung điền khuyết \\square cho bước đang sai để học sinh tự suy nghĩ tính lại. "
                        f"4. TUYỆT ĐỐI KHÔNG khen 'đáp án {var_name} = {cand_str} là hoàn toàn đúng'. "
                        "5. TUYỆT ĐỐI KHÔNG gắn tag [COMPREHENSION_CHECK]."
                    )
                    return RoutingResult(
                        selected_agent="MISCONCEPTION",
                        task_description=task,
                        routing_scratchpad=f"[Trụ1] Linear equation mismatch: {eq_str} -> true {var_name}={true_sol}, student guessed {cand_str}",
                        emotion_flag="WRONG",
                    )

        # B. NẾU HỌC SINH RA ĐỀ / HỎI BÀI TOÁN TÌM X / PHƯƠNG TRÌNH (Chưa đưa ra nghiệm):
        if student_grade in (4, 5):
            tier_guide = (
                "CẤP LỚP 4–5 (TIỂU HỌC): Gọi là 'tìm x' / 'tìm thành phần chưa biết', viết phép nhân dạng $3 \\times x$. "
                "TUYỆT ĐỐI KHÔNG dùng dấu $\\Leftrightarrow$, KHÔNG nói 'phương trình', 'nghiệm', 'chuyển vế đổi dấu', 'hạng tử tự do'. "
                "Đưa khung trình bày 1 bước với ô trống \\square (VD: $$3 \\times x = 16 \\ \\square \\ 4$$) và hỏi để học sinh tự suy nghĩ phép tính cần điền."
            )
        elif student_grade in (6, 7):
            tier_guide = (
                "CẤP LỚP 6–7: Trình bày xuống dòng thẳng dấu `=` (hạn chế dùng $\\Leftrightarrow$). "
                "KHÔNG dùng thuật ngữ nặng nề ('cô lập hạng tử', 'số hạng tự do'), KHÔNG nói lộ dấu hay phép tính (không bảo 'nhớ đổi dấu thành -4'). "
                "Hỏi số hạng khi đưa sang vế bên kia thay đổi thế nào và kèm khung 1 bước có ô \\square (VD: $$3x = 16 \\ \\square \\ 4$$)."
            )
        else:
            tier_guide = (
                "CẤP LỚP 8–9: Trình bày theo chuẩn THCS (có thể dùng $\\Leftrightarrow$ từng dòng). "
                "KHÔNG nói lộ dấu hay phép tính cần làm; hỏi gợi mở để học sinh tự nhận ra biến đổi ở bước 1 kèm khung điền khuyết 1 bước (VD: $$\\Leftrightarrow 3x = 16 \\ \\square \\ 4$$)."
            )

        task_prompt = (
            f"Học sinh vừa gửi bài tìm {var_name}: '{eq_str}' (Kết quả đúng nội bộ: {var_name} = {true_sol}). "
            "Bạn là THẦY GIÁO SOCRATIC, điều phối giàn giáo dẫn dắt BẮT BUỘC: "
            f"1. TUYỆT ĐỐI KHÔNG giải hộ bài toán, TUYỆT ĐỐI KHÔNG tiết lộ đáp án {var_name} = {true_sol}. "
            "2. TUYỆT ĐỐI KHÔNG nói lộ dấu (+ hay -) hoặc phép tính (cộng/trừ/nhân/chia) của bước biến đổi; phải đặt câu hỏi để học sinh tự tư duy. "
            f"3. {tier_guide}"
        )
        return RoutingResult(
            selected_agent="SCAFFOLDING",
            task_description=task_prompt,
            routing_scratchpad=f"[Trụ1] Linear equation problem prompt: '{eq_str}' (solution: {var_name}={true_sol}) -> Direct Socratic SCAFFOLDING",
            emotion_flag="GUIDING",
        )

    def _no_study_intent(self, text: str) -> bool:
        """Kiểm tra câu không chứa tín hiệu hỏi bài học."""
        return not any(s in text for s in self.STUDY_SIGNALS)

    @staticmethod
    def _last_agent_from_history(history_text: str) -> Optional[str]:
        """
        Trụ cột 3 — Trích xuất agent cuối cùng từ lịch sử hội thoại.
        """
        if not history_text:
            return None

        patterns = [
            r"\[Agent:\s*(MISCONCEPTION|SCAFFOLDING|KNOWLEDGE_TRACING|SAFETY)\]",
            r"agent_role[=:\s]+(MISCONCEPTION|SCAFFOLDING|KNOWLEDGE_TRACING|SAFETY)",
            r"agent[=:\s]+(MISCONCEPTION|SCAFFOLDING|KNOWLEDGE_TRACING|SAFETY)",
            r"\b(MISCONCEPTION|SCAFFOLDING|KNOWLEDGE_TRACING|SAFETY)\b",
        ]
        for p in patterns:
            matches = re.findall(p, history_text, re.IGNORECASE)
            if matches:
                return matches[-1].upper()

        return None

    # ── Tín hiệu tích cực / kết thúc hiểu bài — không báo WRONG dù agent cũ là MISCONCEPTION ──
    POSITIVE_CLOSE_SIGNALS: tuple = (
        "ok em hiểu", "em hiểu rồi", "hiểu rồi thầy", "hiểu rồi ạ", "em hiểu ạ",
        "cảm ơn thầy", "cảm ơn", "cám ơn thầy", "cám ơn", "thank thầy", "thanks thầy",
        "dạ em hiểu", "dạ hiểu", "dạ em biết rồi", "biết rồi thầy",
        "ok thầy", "oke thầy", "được rồi thầy", "rõ rồi thầy",
        "em làm được rồi", "làm được rồi", "giải được rồi",
        "dạ vâng", "vâng ạ", "dạ", "vâng",
    )

    @staticmethod
    def _parse_minimal_operator(raw_op: str) -> Tuple[str, str]:
        """
        Chuẩn hóa toán tử biểu thức tối giản thành mã phép tính (DIV, MUL, ADD, SUB) và ký hiệu toán học chuẩn.
        """
        raw = raw_op.strip().lower()
        if raw in (":", "/", "÷", "chia cho", "chia"):
            return "DIV", ":"
        if raw in ("*", "x", "×", "·", "nhân với", "nhân"):
            return "MUL", "×"
        if raw in ("+", "cộng với", "cộng"):
            return "ADD", "+"
        if raw in ("-", "trừ đi", "trừ"):
            return "SUB", "-"
        return "UNKNOWN", raw

    def _detect_minimal_arithmetic_expr(
        self,
        text_clean: str,
        original_message: str,
    ) -> Optional[RoutingResult]:
        """
        Trụ cột 1 — Nhận diện biểu thức toán học tối giản (Task T8.16 - US 8.2).
        Ví dụ: "4/2", "10:2", "3*5", "12+8", "10:2 = ?", "thầy ơi 4/2 bằng mấy ạ".
        Điều phối trực tiếp sang SCAFFOLDING với chỉ đạo Socratic sư phạm (chia kẹo / đồ vật).
        """
        # Chuẩn hóa biểu thức LaTeX phân số \frac{a}{b} / \frac52 / \times / \div / \cdot / \,
        expr_target = self._normalize_latex_math(text_clean)

        m = self._minimal_arithmetic_re.match(expr_target)
        if not m:
            return None

        a_str, raw_op, b_str = m.group(1), m.group(2), m.group(3)
        op_type, std_op = self._parse_minimal_operator(raw_op)
        if op_type == "UNKNOWN":
            return None

        # Tránh nhận diện nhầm các ngày lễ phổ biến của học sinh Việt Nam khi dùng ký tự / hoặc :
        if raw_op in ("/", ":") and "." not in a_str and "." not in b_str:
            a_int, b_int = int(a_str), int(b_str)
            special_dates = {
                (20, 11), (2, 9), (30, 4), (1, 5), (1, 6),
                (8, 3), (20, 10), (22, 12),
                (19, 5),   # Ngày sinh Bác Hồ
                (26, 3),   # Ngày thành lập Đoàn TNCS
                (10, 3),   # Giỗ Tổ Hùng Vương
                (27, 7),   # Ngày Thương binh Liệt sĩ
                (3, 2),    # Ngày thành lập Đảng
            }
            math_intent_signals = ("=", "tính", "bằng", "mấy", "bao nhiêu", "chia")
            if (a_int, b_int) in special_dates and not any(sig in text_clean for sig in math_intent_signals):
                return None  # Coi là ngày tháng, để các phễu khác xử lý

        # Chuyển đổi giá trị số
        try:
            val_a = float(a_str) if "." in a_str else int(a_str)
            val_b = float(b_str) if "." in b_str else int(b_str)
        except Exception:
            return None

        # Ngoại lệ chia cho 0: Tuyệt đối không gợi mở "chia kẹo cho 0 bạn" (vô lý toán học & sư phạm)
        if op_type == "DIV" and val_b == 0:
            return None  # Để phễu khác / LLM giải thích bản chất phép chia cho 0 không xác định

        # Tính toán giá trị tham chiếu nội bộ (dùng để nhắc AI không được vô tình nói ra đáp án)
        ref_val = ""
        try:
            if op_type == "DIV":
                res = val_a / val_b
                ref_val = f"{int(res)}" if res.is_integer() else f"{res:.2f}"
            elif op_type == "MUL":
                res = val_a * val_b
                ref_val = f"{int(res)}" if res.is_integer() else f"{res:.2f}"
            elif op_type == "ADD":
                res = val_a + val_b
                ref_val = f"{int(res)}" if res.is_integer() else f"{res:.2f}"
            elif op_type == "SUB":
                res = val_a - val_b
                ref_val = f"{int(res)}" if res.is_integer() else f"{res:.2f}"
        except Exception:
            ref_val = ""

        # Xây dựng chỉ đạo sư phạm Socratic đặc thù (chuẩn AC 8.2.7)
        display_expr = f"{a_str} {std_op} {b_str}"
        if op_type == "DIV":
            task_desc = (
                f"Học sinh vừa gửi phép tính chia tối giản: '{display_expr}'. "
                "Bạn là THẦY GIÁO, điều phối Socratic trực tiếp: "
                f"TUYỆT ĐỐI KHÔNG giải bài, TUYỆT ĐỐI KHÔNG nói ra kết quả{' là ' + ref_val if ref_val else ''}. "
                f"BẮT BUỘC gợi mở tư duy cho học sinh bằng hình tượng thực tế gần gũi dạng CHIA KẸO / QUẢ TÁO: "
                f"Đặt câu hỏi gợi mở trực quan (ví dụ: 'Giả sử em có {a_str} cái kẹo và muốn chia đều cho {b_str} bạn, "
                f"vậy mỗi bạn sẽ nhận được mấy cái kẹo nhỉ?'). "
                "Chỉ đặt DUY NHẤT 1 câu hỏi gợi mở ngắn gọn (1-2 câu), ấm áp, khích lệ học sinh tự suy nghĩ."
            )
        elif op_type == "MUL":
            task_desc = (
                f"Học sinh vừa gửi phép tính nhân tối giản: '{display_expr}'. "
                "Bạn là THẦY GIÁO, điều phối Socratic trực tiếp: "
                f"TUYỆT ĐỐI KHÔNG giải bài, TUYỆT ĐỐI KHÔNG nói ra kết quả{' là ' + ref_val if ref_val else ''}. "
                f"BẮT BUỘC gợi mở tư duy cho học sinh bằng hình tượng GOM NHÓM ĐỒ VẬT hoặc PHÉP CỘNG LẶP: "
                f"Đặt câu hỏi gợi mở (ví dụ: 'Giả sử em có {b_str} túi kẹo, mỗi túi có {a_str} viên, "
                f"hoặc số {a_str} được lấy {b_str} lần, em thử tính xem có tất cả bao nhiêu viên kẹo nhé?'). "
                "Chỉ đặt DUY NHẤT 1 câu hỏi gợi mở ngắn gọn (1-2 câu)."
            )
        elif op_type == "ADD":
            task_desc = (
                f"Học sinh vừa gửi phép tính cộng tối giản: '{display_expr}'. "
                "Bạn là THẦY GIÁO, điều phối Socratic trực tiếp: "
                f"TUYỆT ĐỐI KHÔNG giải bài, TUYỆT ĐỐI KHÔNG nói ra kết quả. "
                f"Gợi mở trực quan thêm vào đồ vật (ví dụ: 'Em đang có {a_str} món đồ, có thêm {b_str} món nữa, "
                f"tất cả là bao nhiêu nhỉ?'). Chỉ đặt DUY NHẤT 1 câu hỏi ngắn gọn (1-2 câu)."
            )
        else:  # SUB
            if val_a >= val_b:
                analogy_desc = (
                    f"Gợi mở trực quan bớt đi đồ vật (ví dụ: 'Em có {a_str} cái kẹo, bớt đi {b_str} cái, "
                    f"vậy em còn lại mấy cái kẹo nhỉ?')."
                )
            else:
                analogy_desc = (
                    f"Gợi mở so sánh trực quan giữa số bị trừ {a_str} và số trừ {b_str} "
                    f"(ví dụ: 'Em thử quan sát xem số {a_str} có đủ để bớt đi {b_str} cái kẹo không nhỉ, "
                    f"hay ta cần hình dung bước lùi trên tia số?')."
                )
            task_desc = (
                f"Học sinh vừa gửi phép tính trừ tối giản: '{display_expr}'. "
                "Bạn là THẦY GIÁO, điều phối Socratic trực tiếp: "
                f"TUYỆT ĐỐI KHÔNG giải bài, TUYỆT ĐỐI KHÔNG nói ra kết quả{' là ' + ref_val if ref_val else ''}. "
                f"{analogy_desc} Chỉ đặt DUY NHẤT 1 câu hỏi ngắn gọn (1-2 câu)."
            )

        return RoutingResult(
            selected_agent="SCAFFOLDING",
            task_description=task_desc,
            routing_scratchpad=f"[Trụ1] Minimal math expression detected: '{text_clean}' ({op_type}) -> Direct Socratic dispatch",
            emotion_flag="GUIDING",
        )

    def _state_machine_route(
        self,
        text_clean: str,
        history_text: str,
        problem_context: Optional[dict],
        original_message: str,
    ) -> RoutingResult:
        """
        Trụ cột 3 — Suy luận từ ngữ cảnh bài học, không cần API.
        Đây là tầng cuối cùng, luôn trả về kết quả.
        """
        # 3.1 Bài toán đang mở → SCAFFOLDING
        if problem_context and problem_context.get("correctSolution"):
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=_build_task_description("SCAFFOLDING", original_message, problem_context, history_text=history_text),
                routing_scratchpad=f"[Trụ3 - StateMachine]: Bài toán đang mở → SCAFFOLDING.",
                emotion_flag="GUIDING",
            )

        # 3.2 Kế thừa agent cuối từ lịch sử hội thoại
        last_agent = self._last_agent_from_history(history_text)
        if last_agent and last_agent in ("MISCONCEPTION", "KNOWLEDGE_TRACING"):
            # FIX #1: Nếu tin nhắn hiện tại là lời cảm ơn / đã hiểu rồi
            # thì KHÔNG báo WRONG dù agent cũ là MISCONCEPTION
            is_positive_close = any(s in text_clean for s in self.POSITIVE_CLOSE_SIGNALS)
            if last_agent == "MISCONCEPTION" and is_positive_close:
                return RoutingResult(
                    selected_agent="SCAFFOLDING",
                    task_description=_build_task_description("SCAFFOLDING", original_message, problem_context, history_text=history_text),
                    routing_scratchpad=f"[Trụ3 - StateMachine]: Học sinh đã hiểu sau MISCONCEPTION → SCAFFOLDING khen.",
                    emotion_flag="CORRECT",  # Cú vui vẻ vỗ tay vì học sinh hiểu bài rồi
                )
            return RoutingResult(
                selected_agent=last_agent,
                task_description=_build_task_description(last_agent, original_message, problem_context, history_text=history_text),
                routing_scratchpad=f"[Trụ3 - StateMachine]: Tiếp tục ngữ cảnh '{last_agent}' từ lịch sử.",
                emotion_flag="WRONG" if last_agent == "MISCONCEPTION" else "GUIDING",
            )

        # 3.3 Mặc định an toàn
        return RoutingResult(
            selected_agent="SCAFFOLDING",
            task_description=_build_task_description("SCAFFOLDING", original_message, problem_context, history_text=history_text),
            routing_scratchpad=f"[Trụ3 - StateMachine]: Mặc định SCAFFOLDING.",
            emotion_flag="GUIDING",
        )

    def _structural_route(
        self,
        text_clean: str,
        original_message: str,
        problem_context: Optional[dict],
        history_text: str = "",
        student_grade: Optional[int] = None,
    ) -> Optional[RoutingResult]:
        """
        Trụ cột 1 — Phân luồng bằng quy tắc ngữ pháp và toán học tất định.
        Trả về None nếu không khớp bất kỳ phễu nào.
        """

        # 1.1 Profanity & Disrespect (mày, tao, xúc phạm)
        if self.has_real_profanity(text_clean):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message, safety_subtype="DISRESPECT"),
                routing_scratchpad="[Trụ1] Profanity / Disrespect detected.",
                emotion_flag="WARNING",
            )

        # 1.1b Shouting / Gibberish / Hú hét cộc lốc (không phải vi phạm nghiêm trọng -> emotion_flag='GUIDING')
        is_shouting_msg = (
            any(s == text_clean or text_clean.startswith(s + " ") or text_clean.endswith(" " + s) for s in self.SHOUTING_SIGNALS)
            or bool(self._shouting_re.match(text_clean))
        )
        if is_shouting_msg and self._no_study_intent(text_clean):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message, safety_subtype="SHOUTING"),
                routing_scratchpad=f"[Trụ1] Shouting / improper exclamation detected: '{text_clean[:40]}'",
                emotion_flag="GUIDING",
            )

        # 1.2 Off-topic (chỉ kích hoạt khi không chứa tín hiệu học tập / toán học -> emotion_flag='GUIDING')
        has_offtopic = any(re.search(rf"\b{re.escape(s)}\b", text_clean) for s in self.OFFTOPIC_SIGNALS)
        if has_offtopic and self._no_study_intent(text_clean):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message),
                routing_scratchpad=f"[Trụ1] Off-topic signal: '{text_clean[:40]}'",
                emotion_flag="GUIDING",
            )

        # 1.3 Câu chào hỏi (không kèm nội dung bài học)
        starts_greeting = (
            any(text_clean.startswith(g) for g in self.GREETING_STARTS)
            or text_clean in self.GREETING_EXACT
        )
        if starts_greeting and self._no_study_intent(text_clean):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message),
                routing_scratchpad=f"[Trụ1] Greeting pattern: '{text_clean[:40]}'",
                emotion_flag="GUIDING",
            )

        # 1.3c [Task T9.14 & T9.15 / US 11.6 T401]: Nhận diện học sinh phản hồi sau câu hỏi thăm dò (Follow-up Turn & Safe Fallback)
        probe_type = _detect_probe_in_history(history_text)
        if probe_type:
            curr_grade = student_grade or 7
            try:
                from agents.agent_prompts import get_semester_from_month, get_effective_curriculum_month
                curr_month = get_effective_curriculum_month()
                curr_sem = get_semester_from_month(curr_month)
                base_sem = curr_sem if curr_sem else 1
            except Exception:
                curr_month = 9
                base_sem = 1

            # US 11.6: Tự động xác định học kỳ 1 hay 2 dựa trên bối cảnh bài học đang thảo luận
            context_corpus = original_message + " " + (history_text or "") + (" " + problem_context.get("problem_text", "") if problem_context else "")
            active_sem = _detect_semester_for_grade(context_corpus, curr_grade, default_sem=base_sem) if curr_grade else base_sem

            # US 11.6: Phân loại intent hỗ trợ scratchpad và routing
            if _detect_teacher_skipped_phrase(text_clean):
                reply_intent = "TEACHER_SKIPPED"
            elif student_grade:
                try:
                    reply_intent = _classify_probe_reply_with_curriculum(
                        text_clean, "", student_grade, active_sem
                    )
                except Exception:
                    reply_intent = _classify_probe_reply(text_clean)
            else:
                reply_intent = _classify_probe_reply(text_clean)

            praise_summer = "Nếu học sinh xác nhận đang tự học trước trong kỳ nghỉ hè, hãy bắt đầu bằng một lời khen ngợi tinh thần tự giác của em! " if probe_type == "SUMMER_PROBE" else ""
            summer_unclear_note = " (LƯU Ý MÙA HÈ - AC 9.3.7: Học sinh có tâm lý xả hơi hè, tuyệt đối không gặng hỏi hay truy cứu, hãy động viên ấm áp và giảng giải từng bước nhỏ từ gốc rễ theo Kịch bản B)." if probe_type == "SUMMER_PROBE" else ""

            # US 11.6: Inject danh sách curriculum theo thứ tự để AI tự so sánh vị trí bài
            curriculum_order_note = ""
            if student_grade:
                try:
                    from agents.agent_prompts import _load_curriculum
                    _curriculum = _load_curriculum()
                    _g_data = _curriculum.get(str(student_grade), {})
                    _topics = _g_data.get(str(active_sem), [])
                    if _topics:
                        _ordered = "; ".join(f"[{i+1}] {t}" for i, t in enumerate(_topics))
                        curriculum_order_note = (
                            f"\n\n=== US 11.6 CURRICULUM ORDER (HK{active_sem} Lớp {student_grade}) ===\n"
                            f"Danh sách bài theo thứ tự chương trình (INDEX BÀI TỪ NHỎ ĐẾN LỚN = THỨ TỰ HỌC):\n"
                            f"{_ordered}\n"
                            f"Hãy TỰ SO SÁNH vị trí bài học sinh đang học và bài học sinh hỏi:\n"
                            f"● Bài học sinh đang học [X] < Bài được hỏi [Y] → Học sinh CHƯA HỌC TỚI → BẮT BUỘC ÁP DỤNG KỊCH BẢN B (Coi học sinh là 'tờ giấy trắng').\n"
                            f"● Bài học sinh đang học [X] > Bài được hỏi [Y] → Học sinh ĐÃ HỌC NHƯNG QUÊN → BẮT BUỘC ÁP DỤNG KỊCH BẢN A với câu:\n"
                            f"  'Hiện tại nếu em đã học đến [Tên bài X] rồi thì với chương trình HK{active_sem} lớp {student_grade}, em đã học bài [Tên bài Y] rồi. Có lẽ em đã quên nên thầy sẽ nhắc lại cách làm bài này...'\n"
                            f"● Học sinh nói 'cô/thầy bỏ qua/không dạy/nhảy cóc' → BẮT BUỘC ÁP DỤNG KỊCH BẢN B kèm lời đồng cảm: 'Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé!'"
                        )
                except Exception:
                    curriculum_order_note = ""

            guide_instruction = (
                f"HỌC SINH ĐANG PHẢN HỒI CÂU HỎI THĂM DÒ TIẾN ĐỘ ({probe_type}): '{original_message[:80]}'.\n"
                f"BẠN LÀ THẦY GIÁO SOCRATIC TRÍ TUỆ & THẤU CẢM. Hãy đọc hiểu câu trả lời thực tế của học sinh trong ngữ cảnh hội thoại để rẽ nhánh sư phạm chuẩn xác nhất:\n\n"
                f"1. NẾU HỌC SINH CHƯA HỌC TỚI / HỌC TRƯỚC BÀI MỚI (chưa học, cô chưa dạy, mới học tới bài trước, hoặc tự học trước hè):\n"
                f"   -> BẮT BUỘC ÁP DỤNG KỊCH BẢN B (DẪN DẮT TỪ GỐC RỄ):\n"
                f"   - Coi học sinh là 'tờ giấy trắng', tuyệt đối không ép học sinh phải nhớ công thức mới.\n"
                f"   - {praise_summer}Giải thích từ nền tảng đơn giản nhất, chia nhỏ bài toán và đặt một câu hỏi gợi mở nhẹ nhàng.\n\n"
                f"2. NẾU HỌC SINH ĐÃ HỌC RỒI NHƯNG QUÊN / ÔN LẠI BÀI CŨ (đã học trên lớp, lâu ngày không làm nên quên, xả hơi hè quên):\n"
                f"   -> BẮT BUỘC ÁP DỤNG KỊCH BẢN A (GỢI NHỚ KIẾN THỨC CŨ):\n"
                f"   - Đồng cảm nhẹ nhàng (quên là bình thường sau một thời gian), KHÔNG giảng lại từ đầu.\n"
                f"   - Nhắc lại tên công thức hoặc quy tắc tổng quát, gợi mở để học sinh tự nhớ lại.\n\n"
                f"3. NẾU HỌC SINH NÓI LẤP LỬNG / BÍ BÀI / KHÔNG BIẾT ('em ko bt', 'bí quá'):\n"
                f"   -> Áp dụng Kịch bản B (hướng dẫn kiên nhẫn từ bước đơn giản nhất, không truy cứu hay phán xét).{summer_unclear_note}\n\n"
                f"4. NẾU HỌC SINH BÁO THẦY CÔ BỎ QUA / KHÔNG DẠY / NHẢY CÓC / GIẢM TẢI / LƯỚT QUA BÀI NÀY:\n"
                f"   -> BẮT BUỘC ÁP DỤNG KỊCH BẢN B kèm lời đồng cảm: 'Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé!' rồi hướng dẫn từ nền tảng đơn giản nhất."
                f"{curriculum_order_note}\n"
                f"QUAN TRỌNG: Sau khi giải thích nền tảng, LUÔN kèm 1 khung điền khuyết `\\square` trong `$$...$$` cho bước nhỏ đầu tiên và TUYỆT ĐỐI KHÔNG hỏi lại tiến độ trường lớp."
            )
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=guide_instruction,
                routing_scratchpad=f"[Trụ1] Follow-up Probe -> Socratic Decision Framework ({probe_type}) [{reply_intent}] [US11.6]",
                emotion_flag="GUIDING",
            )

        # 1.3b Học sinh tuyên bố chưa học — KHÔNG route KNOWLEDGE_TRACING, route SCAFFOLDING để xử lý context
        if _detect_uncovered_claim(text_clean):
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=_build_task_description(
                    "SCAFFOLDING", original_message, problem_context,
                    student_grade=student_grade, history_text=history_text
                ),
                routing_scratchpad=f"[Trụ1] Uncovered claim detected: '{text_clean[:40]}'",
                emotion_flag="GUIDING",
            )
        # 1.4 Câu hỏi lý thuyết thuần túy ("X là gì?" / "thế nào là X"), không chặn câu có phép tính/đáp án/xin ví dụ
        _has_calc_or_eq_or_ex = (
            bool(re.search(r"=", original_message))
            or bool(re.search(r"\b(ví dụ|bài mẫu|làm mẫu|cho mẫu|cho xin vd)\b", text_clean, re.IGNORECASE))
            or (
                bool(re.search(r"\d", text_clean))
                and any(w in text_clean for w in (
                    "bằng", "ra ", "suy ra", "vậy", "nên ", "kết quả", "đáp án",
                    "chọn", "tính ", "tìm ", "tưởng", "quên dấu", "thay ", "công thức tính",
                    "tam giác", "không thể", "duy nhất", "đường thẳng",
                ))
            )
        )
        if not _has_calc_or_eq_or_ex and (
            self._theory_re.search(text_clean) or any(s in text_clean for s in self.THEORY_SIGNALS)
        ):
            return RoutingResult(
                selected_agent="KNOWLEDGE_TRACING",
                task_description=_build_task_description("KNOWLEDGE_TRACING", original_message, problem_context),
                routing_scratchpad=f"[Trụ1] Theory question pattern: '{text_clean[:40]}'",
                emotion_flag=OrchestratorAgent._determine_emotion_flag(
                    "KNOWLEDGE_TRACING",
                    f"[Trụ1] Theory question pattern: '{text_clean[:40]}'",
                    original_message,
                ),
            )

        # 1.5 Tín hiệu lỗi sai rõ ràng (trừ khi học sinh đang xin ví dụ mẫu)
        if any(s in text_clean for s in self.MISCONCEPTION_SIGNALS) and not re.search(
            r"\b(ví dụ|bài mẫu|làm mẫu|cho mẫu)\b", text_clean, re.IGNORECASE
        ):
            return RoutingResult(
                selected_agent="MISCONCEPTION",
                task_description=_build_task_description("MISCONCEPTION", original_message, problem_context),
                routing_scratchpad=f"[Trụ1] Explicit misconception signal: '{text_clean[:40]}'",
                emotion_flag="WRONG",
            )

        # 1.6 Tín hiệu cầu cứu / cần gợi ý — nếu có phương trình tìm x kèm theo, ưu tiên kiểm tra tiến độ phương trình trước
        if any(s in text_clean for s in self.HELP_SIGNALS):
            eq_help = self._check_linear_equation_progress(
                original_message, history_text, problem_context, student_grade=student_grade
            )
            if eq_help is not None:
                return eq_help
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=_build_task_description(
                    "SCAFFOLDING", original_message, problem_context,
                    student_grade=student_grade, history_text=history_text,
                ),
                routing_scratchpad=f"[Trụ1] Help signal: '{text_clean[:40]}'",
                emotion_flag="GUIDING",
            )

        # =========================================================================
        # 1.6b Biểu thức toán học tối giản (Task T8.16 - US 8.2)
        # Nhận diện: 4/2, 10:2, 3*5, 12+8... điều phối thẳng SCAFFOLDING (Socratic)
        # =========================================================================
        minimal_math = self._detect_minimal_arithmetic_expr(text_clean, original_message)
        if minimal_math is not None:
            return minimal_math

        # =========================================================================
        # 1.6c Kiểm tra giải phương trình và so khớp nghiệm từ ngữ cảnh (Linear Equation Verifier)
        # Ví dụ: 2x + 3 = 5 (nghiệm x = 1). Học sinh nói x = 2 -> MISCONCEPTION (WRONG)
        # =========================================================================
        eq_route = self._check_linear_equation_progress(
            original_message, history_text, problem_context, student_grade=student_grade
        )
        if eq_route is not None:
            return eq_route

        # 1.7 So khớp Toán học với correctSolution
        correct_solution = None
        if problem_context:
            correct_solution = (
                problem_context.get("correctSolution")
                or problem_context.get("correct_solution")
            )
        if correct_solution:
            sol_raw_17 = str(correct_solution).strip()
            sol_no_units_17 = re.sub(r"\b(?:m|cm|dm|mm|km)\s*\^?\s*[²³23]\b", " ", sol_raw_17, flags=re.IGNORECASE)
            is_algebraic_poly_sol = (
                bool(re.search(r"[xXyYzZ]", sol_no_units_17))
                and not re.match(r"^[a-zA-Z]\s*=\s*-?\d+(?:[.,]\d+)?(?:/\d+)?$", sol_raw_17)
                and any(op in sol_no_units_17 for op in ("+", "-", "*", "^", "/"))
            )
            correct_frac, correct_raw = (
                (None, None) if is_algebraic_poly_sol else self._extract_fraction(sol_raw_17)
            )
            if correct_frac is not None:
                # FIX #2: Nếu câu học sinh chứa từ phủ định / không hiểu HOẶC đang hỏi đề bài (lượt đầu / chưa có dấu hiệu nộp đáp án)
                # thì KHÔNG so khớp toán học — tránh bắt nhầm con số trong đề bài ("472850", "18500 kg") thành đáp án sai!
                _negation_signals = (
                    "không hiểu", "ko hiểu", "k hiểu", "chưa hiểu",
                    "không biết", "ko biết", "k biết",
                    "sai rồi", "em sai", "mình sai",
                    "không làm được", "ko làm được",
                    "chưa làm", "chưa ra", "không ra",
                    "bài này", "câu này", "đề này",
                )
                _has_negation = any(s in text_clean for s in _negation_signals)
                _explicit_answer_claim = bool(
                    re.search(r"\b(?:đáp án|kết quả|em tính được|em tính ra|em ra|tính ra)\b|\bbằng\s+-?\d", text_clean)
                ) or (
                    any(a in text_clean for a in ("đúng không", "phải không"))
                    and bool(history_text.strip() or re.search(r"\b(?:tính ra|được\s+-?\d|kết quả|đáp án)\b|=", text_clean))
                )
                _has_question_ask = any(
                    q in text_clean for q in ("làm sao", "thế nào", "cách làm", "hướng dẫn", "đổi ", "làm tròn", "hỏi ", "phải không thầy", "đúng không thầy")
                ) and not bool(re.search(r"\b(?:em tính được|em tính ra|em ra|đáp án|kết quả)\b", text_clean))
                _is_asking_problem = (
                    (not history_text.strip() and (not _explicit_answer_claim or _has_question_ask))
                    or (_has_question_ask and not _explicit_answer_claim)
                )
                _has_valid_unit_conv = False
                if not _has_negation and "=" in original_message:
                    # 1.7d Kiểm tra sai sót đổi đơn vị trực tiếp (VD: "3 tấn 5 tạ = 3050 kg")
                    _unit_families = {
                        "mass": {"tấn": 1000.0, "tạ": 100.0, "yến": 10.0, "kg": 1.0, "g": 0.001, "gam": 0.001},
                        "length": {"km": 1000.0, "m": 1.0, "dm": 0.1, "cm": 0.01, "mm": 0.001},
                        "time": {"giờ": 3600.0, "phút": 60.0, "giây": 1.0},
                    }
                    _u_pat = r"(?:\d+(?:[.,]\d+)?\s*(?:tấn|tạ|yến|kg|gam|km|dm|cm|mm|m|g|giờ|phút|giây)\b\s*,?\s*)+"
                    for _um in re.finditer(rf"({_u_pat})\s*=\s*({_u_pat})", original_message, re.IGNORECASE):
                        _lhs_s, _rhs_s = _um.group(1), _um.group(2)
                        _tok_re = re.compile(r"(\d+(?:[.,]\d+)?)\s*(tấn|tạ|yến|kg|gam|km|dm|cm|mm|m|g|giờ|phút|giây)\b", re.IGNORECASE)
                        _ltoks = [(float(n.replace(",", ".")), u.lower()) for n, u in _tok_re.findall(_lhs_s)]
                        _rtoks = [(float(n.replace(",", ".")), u.lower()) for n, u in _tok_re.findall(_rhs_s)]
                        for _fam in _unit_families.values():
                            if _ltoks and _rtoks and all(u in _fam for _, u in _ltoks + _rtoks):
                                _lval = sum(v * _fam[u] for v, u in _ltoks)
                                _rval = sum(v * _fam[u] for v, u in _rtoks)
                                if abs(_lval - _rval) > 1e-4:
                                    _r_target_unit = _rtoks[-1][1]
                                    _exp_val = _lval / _fam[_r_target_unit]
                                    _exp_str = f"{int(_exp_val) if _exp_val.is_integer() else round(_exp_val, 4)} {_r_target_unit}"
                                    return RoutingResult(
                                        selected_agent="MISCONCEPTION",
                                        task_description=_build_task_description(
                                            "MISCONCEPTION", original_message, problem_context,
                                            student_ans=_rhs_s.strip(), expected_ans=_exp_str,
                                        ),
                                        routing_scratchpad=f"[Trụ1] Unit conversion mismatch: {_lhs_s.strip()} != {_rhs_s.strip()} (expected {_exp_str})",
                                        emotion_flag="WRONG",
                                    )
                                _has_valid_unit_conv = True
                                break

                if _has_negation or _is_asking_problem:
                    return None  # Bỏ qua so khớp toán học, xuống Trụ 2

                msg_norm_17 = self._normalize_latex_math(original_message)
                _msg_low_17 = msg_norm_17.lower()
                msg_clean_units = re.sub(r"\b(?:m|cm|dm|mm|km)\s*\^?\s*[²³23]\b", " ", msg_norm_17, flags=re.IGNORECASE)
                msg_clean_units = msg_clean_units.replace("²", "").replace("³", "")
                msg_clean_units = re.sub(r"(?<=\d)\s+(?=\d{3}\b)", "", msg_clean_units)

                # Phần biểu thức cuối sau '=', 'ra', 'bằng', 'kết quả', 'mất', 'là' để xem học sinh đã rút gọn xong thành số cuối hay còn phép tính
                rhs_tail = self._extract_tail_for_eval(msg_clean_units)
                _rhs_low_17 = rhs_tail.lower()
                _is_conclusive_avg_formula = bool(
                    "=" not in rhs_tail
                    and not _msg_low_17.rstrip().endswith("?")
                    and re.search(r"\b(?:nên|vậy|suy ra)\b[^.\n]*\btrung bình\b[^.\n]*\blà\b", _msg_low_17)
                )
                _rhs_has_unfinished_ops = (
                    not _is_conclusive_avg_formula
                    and bool(re.search(r"(?:\d|\))\s*(?:[\+\-\*×÷:]|\.(?=\s+\d))\s*(?:\d|\()", rhs_tail))
                )

                # Tách biệt: điều kiện chặn CORRECT (chặt, chỉ chặn khi chính vế kết luận còn dở/bước hỏi)
                # vs điều kiện chặn WRONG mismatch (rộng, tránh bắt nhầm số trung gian ở bài nhiều bước).
                _block_correct_match = (
                    bool(re.search(r"\d+\s*,\s*\(\d+\)", _msg_low_17))
                    or bool(re.search(r"\b\d+\s*(?:giờ|phút)\s+\d+\s*(?:phút|giây)\b|\b\d+\s*(?:tấn|tạ)\s+\d+\s*(?:tạ|yến|kg)\b", _rhs_low_17))
                    or any(w in _msg_low_17 for w in (
                        "đúng chưa", "làm vậy", "tiếp theo", "bước đầu", "giữ nguyên", "vế phải", "vế trái", "lập hệ",
                        "ngày thứ", "1 phần", "giá trị một phần",
                    ))
                    or bool(re.search(r"\b(?:tính được|tính ra|ra là|bằng)\s*[^.\n]+?\bvà\b", _rhs_low_17))
                    or bool(re.search(r"=\s*[^.\n]+?\bvà\b", _rhs_low_17))
                )
                _block_mismatch_wrong = (
                    _block_correct_match
                    or _has_valid_unit_conv
                    or ("√" in original_message or "sqrt" in _msg_low_17)
                    or (
                        not _is_conclusive_avg_formula
                        and any(w in _msg_low_17 for w in (
                            "bước", "nhóm", "rút gọn", "khai triển", "em đổi", "quy đồng", "nhân chéo",
                            "chiều dài", "chiều rộng", "nửa chu vi", "lần lượt", "thể tích", "tổng",
                            "cả ba", "hai đáy", "x1", "x2", "vi-ét", "viète", "tần số", "lời giải",
                            "kết quả thuận lợi", "bcnn", "ưcln", "ucln", "số học sinh", "công việc",
                            "mỗi giờ", "được giảm", "giảm giá", "chiết khấu", "được không",
                        ))
                    )
                    or bool(re.search(r"=\s*[^.\n]+?\bvà\b", _msg_low_17))
                    or _msg_low_17.count("=") >= 2 and "," in _msg_low_17
                )

                _has_operator = bool(re.search(r"[\+\-\*\/\^\(\)x:=]", msg_clean_units, re.IGNORECASE))
                if _has_operator and not _rhs_has_unfinished_ops:
                    student_frac = self._eval_math_expr(msg_clean_units)
                    student_raw = msg_norm_17[:30] if student_frac is not None else None
                    if student_frac is None:
                        student_frac, student_raw = self._extract_fraction(msg_clean_units)
                elif not _rhs_has_unfinished_ops:
                    student_frac, student_raw = self._extract_fraction(msg_clean_units)
                else:
                    student_frac, student_raw = (None, None)

                if student_frac is not None:
                    has_unreduced_sqrt = ("√" in rhs_tail or "sqrt" in _rhs_low_17) and not any(
                        tok in str(correct_solution).lower() for tok in ("√", "sqrt")
                    )
                    if student_frac == correct_frac and not _block_correct_match and not has_unreduced_sqrt:
                        return RoutingResult(
                            selected_agent="SCAFFOLDING",
                            task_description=_build_task_description(
                                "SCAFFOLDING", original_message, problem_context
                            ) + f" (Học sinh tính đúng: {student_raw} ✓)",
                            routing_scratchpad=f"[Trụ1] Math match CORRECT: {student_raw} == {correct_raw}",
                            emotion_flag="CORRECT",
                        )
                    elif student_frac != correct_frac and not _block_mismatch_wrong and not re.search(r"\b[a-zA-Z]\b", msg_clean_units):
                        return RoutingResult(
                            selected_agent="MISCONCEPTION",
                            task_description=_build_task_description(
                                "MISCONCEPTION", original_message, problem_context,
                                student_ans=student_raw, expected_ans=correct_raw,
                            ),
                            routing_scratchpad=f"[Trụ1] Math mismatch: {student_raw} != {correct_raw}",
                            emotion_flag="WRONG",
                        )
            elif history_text.strip():
                # 1.7b Khớp biểu thức đại số / đa thức tương đương qua SymPy (VD: '3x^2 + 2x + 5')
                sol_str = str(correct_solution).strip()
                sol_low = sol_str.lower()
                exp_forms = [
                    str(f).strip().lower()
                    for f in (problem_context.get("expectedAnswerForms") or [])
                    if isinstance(f, str) and len(str(f).strip()) >= 2
                ]
                msg_low_q = original_message.strip().lower()

                if re.search(r"[xXyYzZ]", sol_str) and any(op in sol_str for op in ("+", "-", "*", "^", "/")):
                    try:
                        exp_sym = sympy.sympify(self._normalize_math_expr(sol_str))
                        tail_alg = self._extract_tail_for_eval(original_message)
                        tail_alg = re.sub(r"\s*(?:ạ|nhé|nha|đúng không|phải không|thầy)\s*[\.\?!]*$", "", tail_alg, flags=re.IGNORECASE).strip()
                        if tail_alg and re.search(r"[xXyYzZ]", tail_alg):
                            stu_sym = sympy.sympify(self._normalize_math_expr(tail_alg))
                            if sympy.simplify(stu_sym - exp_sym) == 0:
                                return RoutingResult(
                                    selected_agent="SCAFFOLDING",
                                    task_description=_build_task_description(
                                        "SCAFFOLDING", original_message, problem_context
                                    ) + f" (Học sinh tính đúng: {sol_str} ✓)",
                                    routing_scratchpad=f"[Trụ1] Algebraic match CORRECT: {tail_alg} == {sol_str}",
                                    emotion_flag="CORRECT",
                                )
                    except Exception:
                        pass

                # 1.7c Khớp đáp án định tính (VD: 'Không', 'Có song song', 'a // b', 'Không thể')
                if not msg_low_q.endswith("?"):
                    qual_hit = False
                    if sol_low in ("không", "không thể", "vô nghiệm"):
                        qual_hit = any(len(f) >= 4 and f in msg_low_q for f in exp_forms) or (
                            "không thể" in msg_low_q and any(w in msg_low_q for w in ("nên ", "suy ra", "vậy"))
                        )
                    elif "song song" in sol_low and "song song" in msg_low_q:
                        qual_hit = any(w in msg_low_q for w in ("vì ", "nên ", "do ", "suy ra"))
                    elif "đỉnh" in sol_low and "cạnh" in sol_low:
                        qual_hit = ("đỉnh" in msg_low_q and ("cạnh" in msg_low_q or "tia" in msg_low_q))
                    elif any(len(f) >= 4 and f in msg_low_q for f in exp_forms):
                        qual_hit = True
                    if qual_hit:
                        return RoutingResult(
                            selected_agent="SCAFFOLDING",
                            task_description=_build_task_description(
                                "SCAFFOLDING", original_message, problem_context
                            ) + f" (Học sinh tính đúng: {correct_solution} ✓)",
                            routing_scratchpad=f"[Trụ1] Qualitative match CORRECT: {correct_solution}",
                            emotion_flag="CORRECT",
                        )

        return None  # Không khớp → chuyển Trụ cột 2

    def _ml_route(self, text: str, problem_context: Optional[dict] = None) -> Optional[RoutingResult]:
        """
        Trụ cột 2 — Phân loại intent bằng Local ML Model (TF-IDF + Logistic Regression).
        Threshold: 60%.
        """
        # US 10.4 (Task T10.4.3): Out-of-process File Watcher với I/O Throttling
        # Tự động nạp lại mô hình nếu file trên đĩa được cập nhật từ tiến trình ngoài
        now = time.time()
        if now - self._last_mtime_check_time >= self._mtime_check_interval:
            self._last_mtime_check_time = now
            try:
                if self._model_path.exists():
                    current_mtime = self._model_path.stat().st_mtime
                    if current_mtime > self._last_loaded_mtime:
                        self.reload_model(force=False)
            except Exception as e:
                print(f"[OrchestratorAgent] Cảnh báo kiểm tra mtime mô hình: {e}")

        if self._local_model is None:
            return None
        try:
            proba = self._local_model.predict_proba([text])[0]
            max_prob = float(proba.max())
            predicted = self._local_model.classes_[proba.argmax()]

            safety_threshold = 0.50 if predicted == "SAFETY" else self.ML_CONFIDENCE_THRESHOLD
            if max_prob < safety_threshold:
                print(f"[ML-Router] Phân vân: {predicted} ({max_prob:.1%}) < {safety_threshold:.0%} → Trụ cột 3")
                return None

            # BẢO VỆ CHỐNG FALSE POSITIVE CHO SAFETY:
            if predicted == "SAFETY":
                has_profanity = self.has_real_profanity(text)
                has_shouting = (
                    any(s == text or text.startswith(s + " ") or text.endswith(" " + s) for s in self.SHOUTING_SIGNALS)
                    or bool(self._shouting_re.match(text))
                )
                has_offtopic = any(s in text for s in self.OFFTOPIC_SIGNALS)
                has_greeting = (
                    any(text.startswith(g) for g in self.GREETING_STARTS)
                    or text in self.GREETING_EXACT
                )

                has_math_tokens = bool(re.search(r"[\d\+\-\*\/\=]|tìm x|đáp án|kết quả|\bx\b|\by\b", text, re.IGNORECASE))
                has_study_signal = any(s in text for s in self.STUDY_SIGNALS)

                # 1. Nếu có tín hiệu học tập hoặc toán học mà không có từ cấm thật -> Bác bỏ SAFETY
                if not (has_profanity or has_shouting or has_offtopic) and (has_math_tokens or has_study_signal):
                    print(f"[ML-Router] Chặn False Positive SAFETY cho câu có tín hiệu học tập/toán học: '{text}' → Bác bỏ SAFETY")
                    return None

                # 2. BẢO VỆ MẠNH MẼ: Nếu ML đoán SAFETY nhưng câu hoàn toàn KHÔNG CÓ từ cấm thực sự,
                # không có hú hét, không có ngoài lề, không có chào hỏi (VD: 'mến thầy', 'yêu thầy', các câu khen ngợi ngây thơ...)
                # -> Mô hình TF-IDF đang bị overfit từ khóa 'thầy' -> Bác bỏ SAFETY, chuyển Trụ 3 / SCAFFOLDING!
                if not (has_profanity or has_shouting or has_offtopic or has_greeting):
                    print(f"[ML-Router] Bác bỏ False Positive SAFETY không có căn cứ: '{text}' → Trụ cột 3")
                    return None

            # BẢO VỆ CHỐNG FALSE POSITIVE CHO MISCONCEPTION:
            # Tránh ML Router gán nhầm câu trả lời đúng ("Chu vi bằng (15+10)x2 = 50m", "bằng 50m", "x=10")
            # hoặc đề bài mới ("tính 3x + 10 = 25", "\frac{10}{2} = ?") thành MISCONCEPTION khi không có tín hiệu hiểu sai rõ ràng.
            if predicted == "MISCONCEPTION":
                is_asking_example_only = bool(re.search(r"\b(ví dụ|bài mẫu|làm mẫu|cho mẫu|hay nhầm|hay bị nhầm)\b", text, re.IGNORECASE))
                has_explicit_misconception = (
                    not is_asking_example_only
                    and (
                        any(s in text for s in self.MISCONCEPTION_SIGNALS)
                        or bool(re.search(
                            r"\b(?:tưởng|nhầm|lộn|sai|ngộ nhận|lạ quá|vô lý|cấn|ảo)\b",
                            text,
                            re.IGNORECASE,
                        ))
                    )
                )
                looks_like_neutral_answer_or_prompt = bool(
                    re.search(
                        r"(=|\bbằng\b|\bchu vi\b|\bdiện tích\b|\bthể tích\b|\btỉ số\b|\bxác suất\b|\btrung bình\b|\bđộ dài\b|\bđiểm\b|\bđoạn\b|\btia\b|\bhệ\b|\bđổi\b|\btổng\b|\bhiệu\b|\btính\b|\bgiải\b|\bđáp án\b|\\frac|\bgóc\b|\bđộ\b|\bvì\b|\bnên\b|\bsuy ra\b|\blớn hơn\b|\bnhỏ hơn\b|\btam giác\b|\bhình\b|\bkg\b|\btấn\b|\btạ\b|\bquyển\b|\bbao nhiêu\b|\bthế nào\b|\blàm sao\b|\d+)",
                        text,
                        re.IGNORECASE,
                    )
                )
                if not has_explicit_misconception and (looks_like_neutral_answer_or_prompt or is_asking_example_only):
                    print(f"[ML-Router] Chặn False Positive MISCONCEPTION cho câu trả lời/đề bài trung tính: '{text}' -> Trụ cột 3")
                    return None

            task = _build_task_description(predicted, text, problem_context)
            print(f"[ML-Router] [MATCH] {predicted} ({max_prob:.1%})")
            return RoutingResult(
                selected_agent=predicted,
                task_description=task,
                routing_scratchpad=f"[Trụ2 - ML Semantic Router]: {predicted} ({max_prob:.1%})",
                emotion_flag=OrchestratorAgent._determine_emotion_flag(
                    predicted,
                    f"[Trụ2 - ML Semantic Router]: {predicted} ({max_prob:.1%})",
                    text,
                ),
            )
        except Exception as e:
            print(f"[ML-Router] Error: {e}")
            return None
    
    async def route(
        self,
        latest_message: str,
        history_text: str = "",
        problem_context: Optional[dict] = None,
        student_grade: Optional[int] = None,
    ) -> RoutingResult:
        """Phân luồng tin nhắn học sinh — 100% cục bộ, không gọi API nào."""
        text_clean = self._normalize(latest_message)

        # Trụ cột 1
        result = self._structural_route(
            text_clean, latest_message, problem_context,
            history_text=history_text, student_grade=student_grade
        )
        if result is not None:
            return result

        # Trụ cột 2 - Dự đoán ML trước
        ml_res = self._ml_route(text_clean, problem_context)

        is_empty_history = (
            not history_text.strip()
            or history_text.strip() == "(Đây là tin nhắn đầu tiên trong phiên này)"
        )
        # Ưu tiên An toàn ngôn từ (SAFETY) & Ngộ nhận toán học (MISCONCEPTION) — nhưng KHÔNG bắt nhầm Turn 1 hỏi bài thành MISCONCEPTION
        if ml_res is not None and ml_res.get("selected_agent") in ("SAFETY", "SAFETY_AGENT"):
            return ml_res
        if ml_res is not None and ml_res.get("selected_agent") in ("MISCONCEPTION", "MISCONCEPTION_AGENT"):
            has_wrong_kw = any(s in text_clean for s in self.MISCONCEPTION_SIGNALS) or bool(
                re.search(r"\b(?:tưởng|nhầm|lộn|ngộ nhận|lạ quá|vô lý|cấn)\b", text_clean, re.IGNORECASE)
            )
            if not is_empty_history or has_wrong_kw:
                return ml_res

        # Phễu "Bắt đầu phiên học mới"
        if is_empty_history:
            student_val, _ = self._extract_fraction(text_clean)
            has_math_expr = bool(self._math_expr_re.search(text_clean))
            # Nếu không có phân số VÀ không có biểu thức toán học → SCAFFOLDING ngay
            # Nếu CÓ biểu thức toán (kể cả "3/43 + 32/2 = mấy") → cũng SCAFFOLDING,
            # tránh ML nhầm "mấy" (bao nhiêu) thành "mày" (bất lịch sự).
            if student_val is None or has_math_expr:
                emotion_new = OrchestratorAgent._determine_emotion_flag(
                    "SCAFFOLDING",
                    "[Trụ1] Phiên học mới (lịch sử rỗng, có biểu thức toán học).",
                    latest_message,
                )
                return RoutingResult(
                    selected_agent="SCAFFOLDING",
                    task_description=_build_task_description("SCAFFOLDING", latest_message, problem_context),
                    routing_scratchpad="[Trụ1] Phiên học mới (lịch sử rỗng, có biểu thức toán học).",
                    emotion_flag=emotion_new,
                )

        # Áp dụng kết quả ML nếu không phải phiên học mới
        if ml_res is not None:
            return ml_res

        # Trụ cột 3
        return self._state_machine_route(text_clean, history_text, problem_context, latest_message)
    
    @staticmethod
    def _determine_emotion_flag(
        agent: str,
        routing_scratchpad: str,
        original_message: str,
    ) -> str:
        """
        Xác định cờ cảm xúc dựa trên kết quả phân luồng.
        Mapping:
          SAFETY                                  → "WARNING"
          Bất kỳ agent + keyword hiểu sai rõ ràng → "WRONG"
          MISCONCEPTION (math mismatch)           → "WRONG"
          SCAFFOLDING (math CORRECT)              → "CORRECT"
          KNOWLEDGE_TRACING                       → "GUIDING"
          SCAFFOLDING (mặc định)                  → "GUIDING"
        """
        # ── Kiểm tra keyword hiểu sai — áp dụng cho MỌI agent ──────────────
        # Nếu học sinh tự thú nhận hiểu sai, dù ML Router chọn agent nào
        # (SCAFFOLDING, MISCONCEPTION, ...) cũng đều báo WRONG cho cú lắc đầu
        _explicit_wrong_keywords = (
            "tưởng", "nhầm", "lộn", "sai r", "sai rồi", "ngộ nhận",
            "hiểu sai", "tính sai", "học sai", "nghĩ sai",
            "quên đổi dấu", "quên ngoặc", "không đổi chiều",
            "âm nhân âm ra âm", "âm bình phương ra âm",
            "tử cộng tử mẫu cộng mẫu", "nhân chéo nhầm",
        )
        msg_lower = original_message.lower()
        is_help_or_example_ask = (
            "Help signal" in routing_scratchpad
            or "Uncovered claim" in routing_scratchpad
            or bool(re.search(r"\b(ví dụ|bài mẫu|làm mẫu|cho mẫu|hay nhầm|hay bị nhầm|em chưa quen|em chưa học)\b", msg_lower))
        )
        if (
            "Math mismatch" in routing_scratchpad
            or "math mismatch" in routing_scratchpad
            or (not is_help_or_example_ask and any(kw in msg_lower for kw in _explicit_wrong_keywords))
        ):
            return "WRONG"
        # ────────────────────────────────────────────────────────────────────

        if agent == "SAFETY":
            # Nếu là chào hỏi, ngoài lề, hú hét -> chỉ là hướng dẫn (GUIDING), không cảnh báo (WARNING)
            if any(k in routing_scratchpad.lower() for k in ("greeting", "off-topic", "shouting", "ngoài lề", "chào hỏi")):
                return "GUIDING"
            # Nếu có từ cấm / xúc phạm thực sự -> WARNING
            if OrchestratorAgent.has_real_profanity(original_message):
                return "WARNING"
            if any(k in routing_scratchpad.lower() for k in ("profan", "disrespect", "violation", "vô lễ", "chửi")):
                return "WARNING"
            return "GUIDING"
        if agent == "SCAFFOLDING" and (
            "Math match CORRECT" in routing_scratchpad
            or "Học sinh tính đúng" in routing_scratchpad
        ):
            return "CORRECT"
        return "GUIDING"
    def route_sync(
        self,
        latest_message: str,
        history_text: str = "",
        problem_context: Optional[dict] = None,
        student_grade: Optional[int] = None,
    ) -> RoutingResult:
        """Phiên bản đồng bộ (sync) của route() — dùng trong context non-async."""
        text_clean = self._normalize(latest_message)

        result = self._structural_route(
            text_clean, latest_message, problem_context,
            history_text=history_text, student_grade=student_grade
        )
        if result is not None:
            return result

        # Trụ cột 2 - Dự đoán ML trước
        ml_res = self._ml_route(text_clean, problem_context)
        if ml_res is not None and ml_res.get("selected_agent") in ("SAFETY", "SAFETY_AGENT", "MISCONCEPTION", "MISCONCEPTION_AGENT"):
            return ml_res

        is_empty_history = (
            not history_text.strip()
            or history_text.strip() == "(Đây là tin nhắn đầu tiên trong phiên này)"
        )
        if is_empty_history:
            student_val, _ = self._extract_fraction(text_clean)
            has_math_expr = bool(self._math_expr_re.search(text_clean))
            if student_val is None or has_math_expr:
                emotion_new = OrchestratorAgent._determine_emotion_flag(
                    "SCAFFOLDING",
                    "[Trụ1] Phiên học mới (lịch sử rỗng, có biểu thức toán học).",
                    latest_message,
                )
                return RoutingResult(
                    selected_agent="SCAFFOLDING",
                    task_description=_build_task_description("SCAFFOLDING", latest_message, problem_context),
                    routing_scratchpad="[Trụ1] Phiên học mới (lịch sử rỗng, có biểu thức toán học).",
                    emotion_flag=emotion_new,
                )

        result = self._ml_route(text_clean, problem_context)
        if result is not None:
            return result

        # Trụ cột 3
        return self._state_machine_route(text_clean, history_text, problem_context, latest_message)
    
_agent = OrchestratorAgent()
