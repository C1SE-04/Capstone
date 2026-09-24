import json
import re
import pathlib
from fractions import Fraction
from typing import Any, Optional, Tuple, TypedDict

import sympy
import joblib


class RoutingResult(TypedDict):
    """Cấu trúc dữ liệu kết quả phân luồng của Orchestrator."""
    selected_agent: str      # "SCAFFOLDING" | "MISCONCEPTION" | "KNOWLEDGE_TRACING" | "SAFETY"
    task_description: str    # Chỉ đạo cụ thể cho agent tiếp theo (< 3 câu)
    routing_scratchpad: str  # Ghi chú suy luận nội bộ

def _build_task_description(
    agent: str,
    message: str,
    problem_context: Optional[dict] = None,
    student_ans: Optional[str] = None,
    expected_ans: Optional[str] = None,
    safety_subtype: Optional[str] = None,
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
        "ê", "mày", "tao", "mầy", "thằng kia", "con kia", "bot ngu", "thằng bot", "con bot", "ông già", "bà già", "chúng mày", "bọn mày", "thằng này", "con này"
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
        "hệ số góc", "cắt nhau", "trùng nhau", "khoảng cách", "số chính phương", "vế trái", "vế phải"
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
        "cho em ví dụ", "ví dụ đi", "ví dụ thế nào", "ví dụ cụ thể",
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

        # Load Local ML Model (Trụ 2)
        self._local_model = None
        _model_path = pathlib.Path(__file__).parent / "local_orchestrator.pkl"
        if _model_path.exists():
            try:
                self._local_model = joblib.load(_model_path)
                print(f"[OrchestratorAgent] [OK] Local ML Model loaded ({_model_path.stat().st_size // 1024}KB)")
            except Exception as e:
                print(f"[OrchestratorAgent] [WARN] Khong load duoc ML Model: {e}")
        else:
            print(f"[OrchestratorAgent] [WARN] ML Model khong co — chay train_local_model.py truoc.")

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
                task_description=_build_task_description("SCAFFOLDING", original_message, problem_context),
                routing_scratchpad=f"[Trụ3 - StateMachine]: Bài toán đang mở → SCAFFOLDING.",
            )

        # 3.2 Kế thừa agent cuối từ lịch sử hội thoại
        last_agent = self._last_agent_from_history(history_text)
        if last_agent and last_agent in ("MISCONCEPTION", "KNOWLEDGE_TRACING"):
            return RoutingResult(
                selected_agent=last_agent,
                task_description=_build_task_description(last_agent, original_message, problem_context),
                routing_scratchpad=f"[Trụ3 - StateMachine]: Tiếp tục ngữ cảnh '{last_agent}' từ lịch sử.",
            )

        # 3.3 Mặc định an toàn
        return RoutingResult(
            selected_agent="SCAFFOLDING",
            task_description=_build_task_description("SCAFFOLDING", original_message, problem_context),
            routing_scratchpad=f"[Trụ3 - StateMachine]: Mặc định SCAFFOLDING.",
        )

    def _structural_route(
        self,
        text_clean: str,
        original_message: str,
        problem_context: Optional[dict],
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
            )

        # 1.2 Off-topic tuyệt đối
        if any(s in text_clean for s in self.OFFTOPIC_SIGNALS):
            return RoutingResult(
                selected_agent="SAFETY",
                task_description=_build_task_description("SAFETY", original_message),
                routing_scratchpad=f"[Trụ1] Off-topic signal: '{text_clean[:40]}'",
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
            )

        # 1.4 Câu hỏi lý thuyết "X là gì?" / "thế nào là X"
        if self._theory_re.search(text_clean) or any(s in text_clean for s in self.THEORY_SIGNALS):
            return RoutingResult(
                selected_agent="KNOWLEDGE_TRACING",
                task_description=_build_task_description("KNOWLEDGE_TRACING", original_message, problem_context),
                routing_scratchpad=f"[Trụ1] Theory question pattern: '{text_clean[:40]}'",
            )

        # 1.5 Tín hiệu lỗi sai rõ ràng
        if any(s in text_clean for s in self.MISCONCEPTION_SIGNALS):
            return RoutingResult(
                selected_agent="MISCONCEPTION",
                task_description=_build_task_description("MISCONCEPTION", original_message, problem_context),
                routing_scratchpad=f"[Trụ1] Explicit misconception signal: '{text_clean[:40]}'",
            )

        # 1.6 Tín hiệu cầu cứu / cần gợi ý
        if any(s in text_clean for s in self.HELP_SIGNALS):
            return RoutingResult(
                selected_agent="SCAFFOLDING",
                task_description=_build_task_description("SCAFFOLDING", original_message, problem_context),
                routing_scratchpad=f"[Trụ1] Help signal: '{text_clean[:40]}'",
            )

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
                        )
                    else:
                        return RoutingResult(
                            selected_agent="MISCONCEPTION",
                            task_description=_build_task_description(
                                "MISCONCEPTION", original_message, problem_context,
                                student_ans=student_raw, expected_ans=correct_raw,
                            ),
                            routing_scratchpad=f"[Trụ1] Math mismatch: {student_raw} != {correct_raw}",
                        )

        return None  # Không khớp → chuyển Trụ cột 2

    def _ml_route(self, text: str, problem_context: Optional[dict] = None) -> Optional[RoutingResult]:
        """
        Trụ cột 2 — Phân loại intent bằng Local ML Model (TF-IDF + Logistic Regression).
        Threshold: 60%.
        """
        if self._local_model is None:
            return None
        try:
            proba = self._local_model.predict_proba([text])[0]
            max_prob = float(proba.max())
            predicted = self._local_model.classes_[proba.argmax()]

            if max_prob < self.ML_CONFIDENCE_THRESHOLD:
                print(f"[ML-Router] Phân vân: {predicted} ({max_prob:.1%}) < {self.ML_CONFIDENCE_THRESHOLD:.0%} → Trụ cột 3")
                return None

            task = _build_task_description(predicted, text, problem_context)
            print(f"[ML-Router ⚡] {predicted} ({max_prob:.1%})")
            return RoutingResult(
                selected_agent=predicted,
                task_description=task,
                routing_scratchpad=f"[Trụ2 - ML Semantic Router]: {predicted} ({max_prob:.1%})",
            )
        except Exception as e:
            print(f"[ML-Router] Lỗi: {e}")
            return None
    async def route(
        self,
        latest_message: str,
        history_text: str = "",
        problem_context: Optional[dict] = None,
    ) -> RoutingResult:
        """Phân luồng tin nhắn học sinh — 100% cục bộ, không gọi API nào."""
        text_clean = self._normalize(latest_message)

        # Trụ cột 1
        result = self._structural_route(text_clean, latest_message, problem_context)
        if result is not None:
            return result

        # Phễu "Bắt đầu phiên học mới"
        is_empty_history = (
            not history_text.strip()
            or history_text.strip() == "(Đây là tin nhắn đầu tiên trong phiên này)"
        )
        if is_empty_history:
            student_val, _ = self._extract_fraction(text_clean)
            if student_val is None:
                return RoutingResult(
                    selected_agent="SCAFFOLDING",
                    task_description=_build_task_description("SCAFFOLDING", latest_message, problem_context),
                    routing_scratchpad="[Trụ1] Phiên học mới (lịch sử rỗng).",
                )

        # Trụ cột 2
        result = self._ml_route(text_clean, problem_context)
        if result is not None:
            return result

        # Trụ cột 3
        return self._state_machine_route(text_clean, history_text, problem_context, latest_message)

    def route_sync(
        self,
        latest_message: str,
        history_text: str = "",
        problem_context: Optional[dict] = None,
    ) -> RoutingResult:
        """Phiên bản đồng bộ (sync) của route() — dùng trong context non-async."""
        text_clean = self._normalize(latest_message)

        result = self._structural_route(text_clean, latest_message, problem_context)
        if result is not None:
            return result

        is_empty_history = (
            not history_text.strip()
            or history_text.strip() == "(Đây là tin nhắn đầu tiên trong phiên này)"
        )
        if is_empty_history:
            student_val, _ = self._extract_fraction(text_clean)
            if student_val is None:
                return RoutingResult(
                    selected_agent="SCAFFOLDING",
                    task_description=_build_task_description("SCAFFOLDING", latest_message, problem_context),
                    routing_scratchpad="[Trụ1] Phiên học mới (lịch sử rỗng).",
                )

        result = self._ml_route(text_clean, problem_context)
        if result is not None:
            return result

        # Trụ cột 3
        return self._state_machine_route(text_clean, history_text, problem_context, latest_message)
    
_agent = OrchestratorAgent()
