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
    """Trả về True nếu học sinh biện hộ rằng chưa học/chưa được dạy chủ đề nào đó."""
    # Công thức: (Từ phủ định) + (từ đệm tùy chọn) + (học/dạy/thấy/gặp/nghe)
    pattern = r"(chưa|chx|không|ko|k|hk)\s+(được\s+|đc\s+|dc\s+|từng\s+|bao giờ\s+|bao h\s+|cs\s+|có\s+)?(hc|học|dạy|nghe|biết tới|bt tới|bt|biết)|(lần đầu|mới|ms).{0,10}(gặp|thấy|nghe)|(chưa|chx)\s+quen"
    # Cộng thêm các cụm từ viết tắt quá dị của Gen Z mà Regex khó gom nhóm
    gen_z_slang = ("e ch hc", "chưa hỉu", "chx hỉu")
    msg_lower = message.lower()
    if re.search(pattern, msg_lower) or any(s in msg_lower for s in gen_z_slang):
        return True
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
            "dạy đến bài này chưa",
            "dạy đến bài",
            "học tới bài này chưa",
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
                f"TUYỆT ĐỐI KHÔNG HỎI LẠI câu 'Ở trường thầy cô đã dạy đến chưa' hay câu hỏi mùa hè lần thứ 2!\n"
                f"2. BẮT BUỘC tiếp tục dẫn dắt Socratic theo KỊCH BẢN B: Hãy hạ thấp rào cản thêm một nấc nữa, "
                f"tuyệt đối KHÔNG lặp lại câu hỏi toán học vừa hỏi ở lượt trước. "
                f"Hãy chia nhỏ bước giải hơn nữa hoặc gợi ý một phép tính nhẩm cực kỳ đơn giản để học sinh tự tin trả lời."
            )

        # US 9.3 (Task T9.11 & T9.13): Đưa dòng thời gian và Kịch bản thăm dò Socratic chuyên sâu vào task_description
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
            return (
                f"HỌC SINH TUYÊN BỐ CHƯA HỌC: '{message[:80]}'.\n"
                f"[{timeline_label}] CHƯƠNG TRÌNH LỚP {curr_grade}:\n"
                f"- HK1: [{hk1_str}]\n"
                f"- HK2: [{hk2_str}]\n\n"
                f"CHỈ ĐẠO SƯ PHẠM BẮT BUỘC (SOCRATIC PROBE GUIDELINES):\n"
                f"{scenario_guide}\n\n"
                f"NGUYÊN TẮC QUAN TRỌNG: Nếu rơi vào trường hợp cần hỏi thăm dò tiến độ trường học hoặc kỳ nghỉ hè, "
                f"BẠN PHẢI DỪNG LẠI Ở CÂU HỎI THĂM DÒ VÀ GẮN THẺ ẨN <!-- PROBE_PENDING --> (HOẶC [PROBE_PENDING]) Ở CUỐI CÂU TRẢ LỜI, "
                f"TUYỆT ĐỐI KHÔNG GIẢI BÀI HOẶC ĐẶT PHÉP TÍNH TOÁN NGAY TRONG LƯỢT NÀY!"
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
                f"{'Bài: ' + problem_text[:60] + '. ' if problem_text else ''}"
                "Dùng câu hỏi Socratic để học sinh tự tìm ra bước tính sai. "
                "Tuyệt đối không tiết lộ đáp án đúng."
            )
        return (
            f"Học sinh đang hiểu sai hoặc tính sai: '{message[:60]}'. "
            "Xác định chính xác bước sai và đặt câu hỏi gợi mở để học sinh tự phát hiện lỗi."
        )
    # SCAFFOLDING (default)
    if problem_text:
        return (
            f"Học sinh cần hỗ trợ bài: '{problem_text[:70]}'. "
            "Dùng phương pháp Socratic: đặt câu hỏi gợi mở cho bước tiếp theo, "
            "tuyệt đối không giải hộ toàn bộ bài."
        )
    return (
        "Học sinh cần được dẫn dắt từng bước. "
        "Dùng phương pháp Socratic: hỏi về bước học sinh vừa làm, "
        "rồi đặt câu hỏi cho bước tiếp theo. Không giải hộ."
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
        "dạy đến bài này chưa",
        "dạy đến bài",
        "học tới bài này chưa",
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
        "đm", "dcm", "dm", "vcl", "vl", "đĩ", "cặc", "lồn","chó chết", "ngu ngốc", "chết đi", "cút đi", "mẹ mày","thằng chó", "địt", 
        "mẹ kiếp", "đệt", "đệch", "đậu má", "dmm", "dkm", "đkm", "đklm", "loz", "lòn", "cẹc", "buồi", "dái", "clgt", "cc", "qq", "ml",
         "sml", "vml", "cđm", "vkl","đụ mẹ", "đụ má", "đĩ mẹ", "đù má", "đù mẹ", "đụ", "cút", "biến", "xéo", "cái đệt",
        "địt mẹ", "địt con mẹ", "địt cụ", "địt mợ", "địt tổ sư", "địt mả bố","địt mẹ mày", "đụ mẹ mày", "đm mày", "đm nó", "địt con lồn mẹ", 
        "đcmm", "dcmm", "con đĩ mẹ","vãi", "vãi lồn", "vãi cả lồn", "vãi lìn", "vãi lon", "vãi l","vãi đái", "vãi nhái", "vãi chưởng", "vãi nồi",
        "cái lồn gì thế", "cái lồn gì vậy", "cái lồn", "mặt lồn", "hãm lồn", "xạo lồn", "con lồn", "thằng lồn", "sấp mặt lồn",
        "con cặc", "cục cặc", "cái cặc", "đầu cặc", "cái quần què", "quần què","phò", "điếm", "cave", "đĩ điếm", "gái điếm", "con đĩ",
        "nứng", "nứng lồn", "nứng sảng", "chịch", "xoạc", "bú cu", "bú lồn", "liếm lồn","súc vật", "súc sinh", "óc chó", "óc lợn", "ngu học", 
        "ngu như bò", "ngu lồn", "khốn nạn", "khốn kiếp", "chó má",  "đĩ chó", "đĩ ngựa", "đĩ thoã",
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
        "em nhân chéo",
        "em tính nhầm", "em cộng nhầm", "em nhân nhầm",
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
            r"^(?:thầy ơi\s+|thầy\s+|thưa thầy\s+|bạn ơi\s+|tính\s+|em muốn tính\s+|cho em hỏi\s+|giúp em\s+|phép tính\s+|phép tính này\s+)?"
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
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip() if text else ""

    @staticmethod
    def _extract_fraction(text: str) -> Tuple[Optional[Fraction], Optional[str]]:
        """Trích xuất số/phân số từ văn bản, bỏ qua 'câu 1', 'bài 2'."""
        s = re.sub(r"\b(câu|bài|trang|đề)\s*\d+\b", "", text, flags=re.IGNORECASE)
        s = s.replace(",", ".")
        matches = list(re.finditer(r"-?\d+(?:/\d+|\.\d+)?", s))
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
        Hỗ trợ: 3x3+5, (2+3)*4, 2^3, 1/2+1/3, v.v.
        """
        expr = re.sub(r"(\d)\s*x\s*(\d)", r"\1*\2", text, flags=re.IGNORECASE)
        expr = expr.replace("^", "**")
        m = re.search(r"[\d\s\+\-\*\/\(\)\*\.]+", expr)
        if not m:
            return None
        try:
            result = sympy.sympify(m.group(0).strip())
            return Fraction(result.p, result.q) if hasattr(result, "p") else Fraction(float(result))
        except Exception:
            return None

    @staticmethod
    def _solve_simple_linear_equation(raw_eq: str) -> Optional[Tuple[str, Fraction, str]]:
        """
        Giải phương trình bậc nhất một ẩn đơn giản (ví dụ: '2x + 3 = 5', '2x = 2', '3y - 9 = 0').
        Trả về: (tên biến, nghiệm Fraction, phương trình chuẩn).
        """
        try:
            if "=" not in raw_eq:
                return None
            lhs_str, rhs_str = raw_eq.split("=", 1)
            # Thêm dấu nhân giữa số và biến chữ cái: 2x -> 2*x
            lhs_norm = re.sub(r"(\d)\s*([a-zA-Z])", r"\1*\2", lhs_str)
            rhs_norm = re.sub(r"(\d)\s*([a-zA-Z])", r"\1*\2", rhs_str)

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
    ) -> Optional[RoutingResult]:
        """
        Trụ cột 1 — Kiểm tra học sinh giải phương trình tuyến tính từ ngữ cảnh:
        Ví dụ: Trong lịch sử có phương trình '2x + 3 = 5' (nghiệm đúng x = 1).
        Học sinh nhắn: 'à là qua thành -3, đáp án x = 2'.
        Nhận diện nghiệm sai (x = 2 != 1) -> Route MISCONCEPTION (emotion_flag='WRONG')
        kèm phân tích sư phạm: chuyển vế đúng nhưng kết luận sai nghiệm do quên chia hệ số.
        Nếu nghiệm đúng (x = 1 == 1) -> Route SCAFFOLDING (emotion_flag='CORRECT').
        """
        if not history_text and not problem_context:
            return None

        # Tập hợp văn bản để tìm phương trình gốc đang thảo luận
        context_sources = []
        if problem_context:
            for k in ("problem_text", "problem", "title", "content"):
                val = problem_context.get(k)
                if val and isinstance(val, str):
                    context_sources.append(val)
        if history_text:
            context_sources.append(history_text)

        search_corpus = "\n".join(context_sources)
        if not search_corpus.strip():
            return None

        # Regex tìm các biểu thức phương trình dạng có dấu '='
        eq_pattern = re.compile(
            r"(\b\d*\.?\d*\s*[a-zA-Z]\s*(?:[\+\-\*\/]\s*\d+\.?\d*)?\s*=\s*[+-]?\s*[\d\.\s\+\-\*\/]+)",
            re.IGNORECASE,
        )
        eq_matches = eq_pattern.findall(search_corpus)
        if not eq_matches:
            return None

        solved_target = None
        for raw in reversed(eq_matches):
            res = self._solve_simple_linear_equation(raw)
            if res:
                v_name, sol, eq_clean = res
                # Ưu tiên phương trình có chứa phép tính hoặc hệ số (ví dụ 2x + 3 = 5, 2x = 2)
                # thay vì phép gán tầm thường x = 2
                is_trivial_assign = bool(re.match(rf"^{v_name}\s*=\s*-?\d+$", eq_clean.strip(), re.IGNORECASE))
                if not is_trivial_assign or not solved_target:
                    solved_target = res
                    if re.search(r"[\+\-\*\/]", eq_clean) or re.search(r"\d+[a-zA-Z]", eq_clean):
                        break

        if not solved_target:
            return None

        var_name, true_sol, eq_str = solved_target

        # Tìm xem học sinh có đưa ra đề xuất nghiệm trong tin nhắn hiện tại không
        ans_pattern = re.compile(
            rf"(?:(?:đáp án|dap an|nghiệm|nghiem|kết quả|ket qua|tính ra|tinh ra|ra)\s*(?:là|la\s*)?)?{var_name}\s*=\s*(-?\d+(?:\.\d+)?(?:/\d+)?)|\b(?:đáp án|dap an|nghiệm|nghiem|kết quả|ket qua)\s*(?:là|la\s*)?(-?\d+(?:\.\d+)?(?:/\d+)?)",
            re.IGNORECASE,
        )
        m = ans_pattern.search(original_message)
        if not m:
            return None

        cand_str = m.group(1) or m.group(2)
        if not cand_str:
            return None

        try:
            cand_frac, _ = self._extract_fraction(cand_str)
        except Exception:
            return None

        if cand_frac is None:
            return None

        # So khớp nghiệm
        if cand_frac == true_sol:
            # Học sinh đoán đúng nghiệm!
            task = (
                f"Học sinh đã giải đúng phương trình '{eq_str}' và tìm ra {var_name} = {cand_str} (nghiệm đúng: {true_sol}). "
                "Bạn là THẦY GIÁO: Khen ngợi học sinh đã giải chính xác phương trình, ghi nhận sự nỗ lực và chốt bài toán bằng cách gắn tag [COMPREHENSION_CHECK]."
            )
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=task,
                routing_scratchpad=f"[Trụ1] Linear equation CORRECT: {eq_str} -> {var_name}={true_sol}",
                emotion_flag="CORRECT",
            )
        else:
            # Học sinh đoán sai nghiệm!
            has_transpose_step = any(s in original_message.lower() for s in (
                "chuyển vế", "chuyen ve", "qua thành", "qua thanh", "đổi dấu", "doi dau",
                "-3", "- 3", "= 2", "=2"
            ))

            pedagogical_analysis = ""
            if has_transpose_step:
                pedagogical_analysis = (
                    f"Phân tích sư phạm: Học sinh đã thực hiện bước chuyển vế đúng nhưng ở bước cuối kết luận {var_name} = {cand_str} là SAI "
                    f"(do quên chia cho hệ số của {var_name}, nghiệm đúng phải là {var_name} = {true_sol})."
                )
            else:
                pedagogical_analysis = (
                    f"Phân tích sư phạm: Học sinh đưa ra kết quả {var_name} = {cand_str} là SAI "
                    f"(nghiệm đúng của phương trình '{eq_str}' phải là {var_name} = {true_sol})."
                )

            task = (
                f"Học sinh đang giải phương trình '{eq_str}'. {pedagogical_analysis} "
                "Bạn là THẦY GIÁO, điều phối sư phạm Socratic BẮT BUỘC: "
                "1. Nếu học sinh có bước chuyển vế đúng, hãy khen ngợi bước đó. "
                f"2. Nhẹ nhàng chỉ ra rằng kết quả {var_name} = {cand_str} chưa chính xác, yêu cầu học sinh quan sát lại hệ số của {var_name}. "
                "3. Đặt câu hỏi Socratic gợi mở bước chia cuối cùng để học sinh tự tính lại. "
                f"4. TUYỆT ĐỐI KHÔNG khen 'đáp án {var_name} = {cand_str} là hoàn toàn đúng'. "
                "5. TUYỆT ĐỐI KHÔNG gắn tag [COMPREHENSION_CHECK]."
            )
            return RoutingResult(
                selected_agent="MISCONCEPTION",
                task_description=task,
                routing_scratchpad=f"[Trụ1] Linear equation mismatch: {eq_str} -> true {var_name}={true_sol}, student guessed {cand_str}",
                emotion_flag="WRONG",
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
        if raw in ("*", "x", "×", "nhân với", "nhân"):
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
        m = self._minimal_arithmetic_re.match(text_clean)
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
        if self._profanity_re.search(text_clean):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message, safety_subtype="DISRESPECT"),
                routing_scratchpad="[Trụ1] Profanity / Disrespect detected.",
                emotion_flag="WARNING",
            )

        # 1.1b Shouting / Gibberish / Hú hét cộc lốc
        is_shouting_msg = (
            any(s == text_clean or text_clean.startswith(s + " ") or text_clean.endswith(" " + s) for s in self.SHOUTING_SIGNALS)
            or bool(self._shouting_re.match(text_clean))
        )
        if is_shouting_msg and self._no_study_intent(text_clean):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message, safety_subtype="SHOUTING"),
                routing_scratchpad=f"[Trụ1] Shouting / improper exclamation detected: '{text_clean[:40]}'",
                emotion_flag="WARNING",
            )

        # 1.2 Off-topic tuyệt đối
        if any(s in text_clean for s in self.OFFTOPIC_SIGNALS):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message),
                routing_scratchpad=f"[Trụ1] Off-topic signal: '{text_clean[:40]}'",
                emotion_flag="WARNING",
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

        # 1.3c [Task T9.14 & T9.15]: Nhận diện học sinh phản hồi sau câu hỏi thăm dò (Follow-up Turn & Safe Fallback)
        probe_type = _detect_probe_in_history(history_text)
        if probe_type:
            reply_intent = _classify_probe_reply(text_clean)
            praise_summer = "Nếu học sinh xác nhận đang tự học trước trong kỳ nghỉ hè, hãy bắt đầu bằng một lời khen ngợi tinh thần tự giác của em! " if probe_type == "SUMMER_PROBE" else ""
            summer_unclear_note = " (LƯU Ý MÙA HÈ - AC 9.3.7: Học sinh có tâm lý xả hơi hè, tuyệt đối không gặng hỏi hay truy cứu, hãy động viên ấm áp và giảng giải từng bước nhỏ từ gốc rễ theo Kịch bản B)." if probe_type == "SUMMER_PROBE" else ""
            
            guide_instruction = (
                f"HỌC SINH ĐANG PHẢN HỒI CÂU HỎI THĂM DÒ TIẾN ĐỘ ({probe_type}): '{original_message[:80]}'.\n"
                f"BẠN LÀ THẦY GIÁO SOCRATIC. Hãy đọc hiểu câu trả lời thực tế của học sinh trong ngữ cảnh hội thoại để rẽ nhánh sư phạm chuẩn xác nhất:\n\n"
                f"1. NẾU HỌC SINH CHƯA HỌC TỚI / HỌC TRƯỚC BÀI MỚI (chưa học, cô chưa dạy, mới học tới bài trước, hoặc tự học trước hè):\n"
                f"   -> BẮT BUỘC ÁP DỤNG KỊCH BẢN B (DẪN DẮT TỪ GỐC RỄ):\n"
                f"   - Coi học sinh là 'tờ giấy trắng', tuyệt đối không ép học sinh phải nhớ công thức mới.\n"
                f"   - {praise_summer}Giải thích từ nền tảng đơn giản nhất, chia nhỏ bài toán và đặt một câu hỏi gợi mở nhẹ nhàng.\n\n"
                f"2. NẾU HỌC SINH ĐÃ HỌC RỒI NHƯNG QUÊN / ÔN LẠI BÀI CŨ (đã học trên lớp, lâu ngày không làm nên quên, xả hơi hè quên):\n"
                f"   -> BẮT BUỘC ÁP DỤNG KỊCH BẢN A (GỢI NHỚ KIẾN THỨC CŨ):\n"
                f"   - Đồng cảm nhẹ nhàng (quên là bình thường sau một thời gian), KHÔNG giảng lại từ đầu.\n"
                f"   - Nhắc lại tên công thức hoặc quy tắc tổng quát, gợi mở để học sinh tự nhớ lại.\n\n"
                f"3. NẾU HỌC SINH NÓI LẤP LỬNG / BÍ BÀI / KHÔNG BIẾT ('em ko bt', 'bí quá'):\n"
                f"   -> Áp dụng Kịch bản B (hướng dẫn kiên nhẫn từ bước đơn giản nhất, không truy cứu hay phán xét).{summer_unclear_note}"
            )
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=guide_instruction,
                routing_scratchpad=f"[Trụ1] Follow-up Probe -> Socratic Decision Framework ({probe_type}) [{reply_intent}]",
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
        # 1.4 Câu hỏi lý thuyết "X là gì?" / "thế nào là X"
        if self._theory_re.search(text_clean) or any(s in text_clean for s in self.THEORY_SIGNALS):
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

        # 1.5 Tín hiệu lỗi sai rõ ràng
        if any(s in text_clean for s in self.MISCONCEPTION_SIGNALS):
            return RoutingResult(
                selected_agent="MISCONCEPTION",
                task_description=_build_task_description("MISCONCEPTION", original_message, problem_context),
                routing_scratchpad=f"[Trụ1] Explicit misconception signal: '{text_clean[:40]}'",
                emotion_flag="WRONG",
            )

        # 1.6 Tín hiệu cầu cứu / cần gợi ý
        if any(s in text_clean for s in self.HELP_SIGNALS):
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=_build_task_description("SCAFFOLDING", original_message, problem_context),
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
        eq_route = self._check_linear_equation_progress(original_message, history_text, problem_context)
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
            correct_frac, correct_raw = self._extract_fraction(str(correct_solution))
            if correct_frac is not None:
                # FIX #2: Nếu câu học sinh chứa từ phủ định / không hiểu
                # thì KHÔNG so khớp toán học — tránh trích số từ "bài 3", "câu 2" nhầm thành đáp án
                _negation_signals = (
                    "không hiểu", "ko hiểu", "k hiểu", "chưa hiểu",
                    "không biết", "ko biết", "k biết",
                    "sai rồi", "em sai", "mình sai",
                    "không làm được", "ko làm được",
                    "chưa làm", "chưa ra", "không ra",
                    "bài này", "câu này", "đề này",
                )
                _has_negation = any(s in text_clean for s in _negation_signals)
                if _has_negation:
                    return None  # Bỏ qua so khớp toán học, xuống Trụ 2

                _has_operator = bool(re.search(r"[\+\-\*\/\^\(\)x]", original_message, re.IGNORECASE))
                if _has_operator:
                    student_frac = self._eval_math_expr(original_message)
                    student_raw = original_message[:30] if student_frac is not None else None
                    if student_frac is None:
                        student_frac, student_raw = self._extract_fraction(original_message)
                else:
                    student_frac, student_raw = self._extract_fraction(original_message)

                if student_frac is not None:
                    if student_frac == correct_frac:
                        return RoutingResult(
                            selected_agent="SCAFFOLDING",
                            task_description=_build_task_description(
                                "SCAFFOLDING", original_message, problem_context
                            ) + f" (Học sinh tính đúng: {student_raw} ✓)",
                            routing_scratchpad=f"[Trụ1] Math match CORRECT: {student_raw} == {correct_raw}",
                            emotion_flag="CORRECT",
                        )
                    else:
                        return RoutingResult(
                            selected_agent="MISCONCEPTION",
                            task_description=_build_task_description(
                                "MISCONCEPTION", original_message, problem_context,
                                student_ans=student_raw, expected_ans=correct_raw,
                            ),
                            routing_scratchpad=f"[Trụ1] Math mismatch: {student_raw} != {correct_raw}",
                            emotion_flag="WRONG",
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
            # Nếu ML đoán SAFETY nhưng câu không chứa bất kỳ từ cấm, hú hét hay ngoài lề thực sự,
            # mà lại có tín hiệu học tập hoặc toán học -> BÁC BỎ SAFETY!
            if predicted == "SAFETY":
                has_profanity = bool(self._profanity_re.search(text))
                has_shouting = (
                    any(s == text or text.startswith(s + " ") or text.endswith(" " + s) for s in self.SHOUTING_SIGNALS)
                    or bool(self._shouting_re.match(text))
                )
                has_offtopic = any(s in text for s in self.OFFTOPIC_SIGNALS)

                has_math_tokens = bool(re.search(r"[\d\+\-\*\/\=]|tìm x|đáp án|kết quả|\bx\b|\by\b", text, re.IGNORECASE))
                has_study_signal = any(s in text for s in self.STUDY_SIGNALS)

                if not (has_profanity or has_shouting or has_offtopic) and (has_math_tokens or has_study_signal):
                    print(f"[ML-Router] Chặn False Positive SAFETY cho câu có tín hiệu học tập/toán học: '{text}' → Bác bỏ SAFETY")
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

        # Ưu tiên An toàn ngôn từ (SAFETY): Kể cả tin nhắn đầu tiên, nếu vi phạm thì phải chuyển SAFETY ngay
        if ml_res is not None and ml_res.get("selected_agent") in ("SAFETY", "SAFETY_AGENT"):
            return ml_res

        # Phễu "Bắt đầu phiên học mới"
        is_empty_history = (
            not history_text.strip()
            or history_text.strip() == "(Đây là tin nhắn đầu tiên trong phiên này)"
        )
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
        if (
            "Math mismatch" in routing_scratchpad
            or "math mismatch" in routing_scratchpad
            or any(kw in msg_lower for kw in _explicit_wrong_keywords)
        ):
            return "WRONG"
        # ────────────────────────────────────────────────────────────────────

        if agent == "SAFETY":
            return "WARNING"
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
