import os
import pathlib
from dotenv import load_dotenv

_env_path = pathlib.Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_env_path)
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

import re
import json
import itertools
import threading
import google.generativeai as genai
from agents.reviewer import LocalReviewerAgent
from agents.agent_prompts import _get_grade_context
import io
from typing import Optional
import httpx
from PIL import Image

# US 10.2 (T10.2.2): Import telemetry wrappers để thu thập token và TTFT
from middleware.gemini_telemetry import (
    stream_with_telemetry,
    generate_with_telemetry,
    _is_429_exception,
    extract_finish_reason,
)
from middleware.telemetry_middleware import push_failover_event

# Tên model đang dùng thực tế — đồng bộ với bảng giá trong gemini_telemetry.py
_ACTIVE_MODEL_NAME = "gemini-3.5-flash-lite"
_ROTATION_LITE_MODELS: tuple[str, str] = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite")
_FORBIDDEN_BACKUP_MODELS: set[str] = {"gemini-3.6-flash", "gemini-3.8-flash"}
_ROTATION_COUNTER = itertools.count()
_ROTATION_LOCK = threading.Lock()
_DEFAULT_MAX_OUTPUT_TOKENS = 1024
_MIN_CHAT_MAX_OUTPUT_TOKENS = 1024

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

4. PHƯƠNG PHÁP SOCRATIC DỄ HIỂU & BÁM SÁT BÀI TOÁN:
   - Không giải hộ hay đưa đáp số cuối cùng trước khi học sinh tự tìm ra. Chỉ dẫn dắt từng bước nhỏ (1 bước mỗi lượt) và đặt DUY NHẤT 1 câu hỏi gợi mở rõ ràng ở cuối.
   - BÁM SÁT ĐỀ BÀI CỤ THỂ: Thao tác trực tiếp trên số liệu của bài toán học sinh đang hỏi, không khảo sát lý thuyết lan man (VD: có delta cụ thể thì tính delta bài đó, không liệt kê trường hợp lý thuyết).
   - ĐƠN GIẢN HÓA NGÔN NGỮ THEO LỚP (LỚP 4–9):
     * Lớp 4–5 (Tiểu học): Dùng từ gần gũi ("số hạng chưa biết", "thừa số chưa biết", "số bị chia/số chia"). Viết phép nhân với chữ là `3 \times x`. Viết số hàng nghìn liền nhau (`34500`) hoặc cách khoảng trắng (`34 500`), TUYỆT ĐỐI KHÔNG dùng dấu phẩy phân cách hàng nghìn (`34,500`). TUYỆT ĐỐI KHÔNG dùng dấu `\Leftrightarrow`, KHÔNG nói "phương trình", "nghiệm", "hạng tử tự do", "cô lập ẩn", "chuyển vế đổi dấu", "ƯCLN" cho phép chia đơn giản (VD: 10/5 chỉ là 10 : 5).
     * Lớp 6–7: Diễn đạt tự nhiên, trình bày xuống dòng thẳng dấu `=`; TUYỆT ĐỐI KHÔNG dùng dấu `\Leftrightarrow` (kể cả trong Mẫu trình bày vào vở); tránh thuật ngữ nặng nề ("cô lập hạng tử", "số hạng tự do").
     * Lớp 8–9: Dùng thuật ngữ và ký hiệu chuẩn THCS (`\Leftrightarrow`, ĐKXĐ, nghiệm, tập nghiệm, chứng minh).
   - NGUYÊN TẮC ĐIỀN KHUYẾT SOCRATIC KHÔNG NÓI LỘ:
     * Với bài cần trình bày, kèm KHUNG TRÌNH BÀY NGẮN có ô trống `\square` bọc trong `$...$` hoặc `$$...$$` (chỉ mở 1 bước hiện tại; Lớp 4–5 tối đa 1–2 ô `\square` mỗi lượt — VD quy đồng nhiều phân số chỉ chừa đúng 1 ô trống như `$$\frac{5}{6} + \frac{3}{8} - \frac{1}{4} = \frac{\square}{24} + \frac{9}{24} - \frac{6}{24}$$` hoặc hỏi mẫu chung trước `$$\text{Mẫu chung} = \square$$`, TUYỆT ĐỐI KHÔNG đặt 3 ô `\square` cùng lúc; không đặt chữ tiếng Việt dài bên trong `$...$`). TUYỆT ĐỐI KHÔNG viết biểu thức đồng nhất vô nghĩa (VD: `$$\sqrt{x}-1 = \sqrt{x}-1$$`); phần nào giữ nguyên chỉ nhắc ngắn bằng lời, chỉ đưa vào `$$...$$` đúng phần chứa `\square`.
     * TUYỆT ĐỐI KHÔNG nói lộ dấu (`+` hay `-`), phép tính (`nhân` hay `chia`) hay quy tắc biến đổi cần điền! CẤM dùng các cụm như "đổi dấu thành -4", "lấy tích chia cho thừa số đã biết", "lấy thương nhân với số chia", "lấy ... chia cho ...", "lấy ... nhân với ..." khi đang gợi mở hoặc sửa lỗi (kể cả bài phần trăm hay tần số tương đối: KHÔNG viết "lấy A chia cho B rồi nhân 100%", hãy viết thẳng khung biểu thức có `\square` như `$$\frac{12}{25} \times 100\% = \square\%$$` hoặc `$$80 \ \square \ 25\%$$`)! Hãy hỏi để học sinh tự suy nghĩ cách tìm giá trị ở ô `\square` (VD lượt 1 bài `3x + 4 = 16`: hỏi khi đưa 4 sang vế phải thì số 4 thay đổi thế nào kèm `$$3x = 16 \ \square \ 4$$`; lượt 2 tương tự để học sinh tự nhận ra phép tính ở `$$x = 12 \ \square \ 3$$`).
   - KHUNG TRÌNH BÀY CHUẨN 4 DẠNG TOÁN:
     * Tìm x / Phương trình: Xuống dòng thẳng dấu `=` (Lớp 4–7) hoặc `\Leftrightarrow` (Lớp 8–9).
     * Tính giá trị / Phân số / Căn thức / Đổi đơn vị: Nối chuỗi dấu `=` từng bước (`= ...`) hoặc khung đổi đơn vị kèm `\square` cho phần đang tính (VD: `$$1\text{ tấn} = \square\text{ kg}$$`).
     * Toán có lời văn: Bố cục ngắn `Lời giải:` -> `Phép tính: ... = \square (đơn vị)`.
     * Hình học: Lớp 4–6 dùng `Lời giải - Phép tính` hoặc khung so sánh/đếm góc có `\square`; Lớp 7–9 dùng `Xét ... có: ... \Rightarrow ...`.
   - MẪU TRÌNH BÀY VÀO VỞ: Khi học sinh giải ĐÚNG bước cuối (hoặc ở chế độ giải chi tiết), tóm tắt ngắn **Mẫu trình bày hoàn chỉnh** (2–4 dòng chuẩn cấp lớp) trước khi chốt.
   - CHỐNG LẶP & ĐỔI BÀI: Nếu học sinh nói "chưa học", "không biết", "bí" -> hạ thấp độ khó (chia nhỏ phép tính/ví dụ gần gũi), TUYỆT ĐỐI KHÔNG lặp lại câu hỏi cũ. Nếu học sinh đổi bài/gửi ảnh mới -> chuyển ngay sang bài mới.

5. ĐỘ DÀI & CÁCH VIẾT:
   - Ngắn gọn, ấm áp: phần lời dẫn 2–4 câu ngắn (tối đa 5 câu nếu bài vượt cấp hoặc cần giải thích ngắn khái niệm mới; tổng dưới 140 từ, trừ khi chốt mẫu vở/giải mẫu) + tách riêng khung trình bày có `\square` nếu cần. Gộp khen và nhắc cấp lớp (nếu có) thành 1 câu ngắn, và chỉ kết thúc bằng DUY NHẤT 1 câu hỏi khớp trực tiếp với ô `\square`.
   - TUYỆT ĐỐI KHÔNG mở đầu bằng "Dạ", "Dạ được", "Vâng ạ", "Thưa em"; KHÔNG tự xưng "học sinh" ở ngôi thứ ba; luôn xưng "thầy", gọi "em". KHÔNG đặt dấu chấm `.` ngay sau biểu thức trung gian `= số` (VD không viết `3x = 12.`).

6. ĐÁNH GIÁ HOÀN THÀNH BÀI TOÁN (COMPREHENSION TRIGGER):
   - Khi học sinh đã trả lời ĐÚNG đáp án cuối cùng của bài toán (kể cả viết gọn, phân số `\frac{a}{b}`, số tuần hoàn `0,(5)`, đơn vị `2 giờ 35 phút`, `15,4 kg`, hoặc đáp án trắc nghiệm A/B/C/D), HOẶC khi bạn vừa trình bày xong toàn bộ lời giải chi tiết ở chế độ giải bài:
     -> BẮT BUỘC kèm Mẫu trình bày hoàn chỉnh và chèn tag [COMPREHENSION_CHECK] vào CUỐI câu trả lời (trước thẻ ẩn nếu có).
   - Khi bài toán chưa giải xong hoặc bạn vẫn đang đặt câu hỏi gợi mở tiếp theo:
     -> TUYỆT ĐỐI KHÔNG chèn tag [COMPREHENSION_CHECK].

7. KIỂM TRA TÍNH ĐÚNG ĐẮN TOÁN HỌC (FACT-CHECK BẮT BUỘC):
   - Tự giải nhẩm bài toán trước khi trả lời.
   - ĐỘC LẬP VỚI NHÃN PHÂN LUỒNG: Dù vai trò được giao là MISCONCEPTION hay SCAFFOLDING, nếu học sinh đã ra ĐÚNG đáp án cuối cùng -> công nhận ĐÚNG ngay, trình bày Mẫu hoàn chỉnh và gắn [COMPREHENSION_CHECK]; TUYỆT ĐỐI KHÔNG bắt tính lại phép tính đã đúng!
   - Ngược lại, nếu học sinh tính SAI -> TUYỆT ĐỐI KHÔNG dùng từ "hoàn toàn đúng", "chính xác", "chuẩn rồi". Hãy ghi nhận nhẹ nhàng ("Em làm đúng phần ... rồi, nhưng ở phần ... em kiểm tra lại nhé") và chỉ vào đúng bước/ô sai để em tự sửa, KHÔNG gắn [COMPREHENSION_CHECK].

8. CƠ CHẾ THẨM ĐỊNH NGẦM 2 LỚP & GIAO THỨC THẺ ẨN (SELF-REFLECTIVE HIDDEN TAG PROTOCOL - US 10.4):
   [LỚP SƯ PHẠM (CHÍNH - GỬI HỌC SINH)]:
   - Bạn là Thầy giáo mẫu mực, giảng dạy ấm áp, kiên nhẫn.
   - TUYỆT ĐỐI KHÔNG nhắc đến các thuật ngữ kỹ thuật hệ thống, AI, mô hình máy học, phân luồng hay tên Agent (như 'Orchestrator', 'Routing', 'Agent', 'Scaffolding', 'Misconception', 'Safety') trong lời giảng gửi cho học sinh.

   [LỚP THẨM ĐỊNH NGẦM (PHỤ - CHỈ DÙNG THẺ ẨN)]:
   - Hệ thống cung cấp cho bạn vai trò chuyên môn hiện tại được phân luồng: {target_agent}.
   - Bạn có nhiệm vụ ngầm đối chiếu câu nói vừa rồi của học sinh với vai trò chuyên môn này:
     * Nếu học sinh hiểu sai bản chất/ngộ nhận toán học (ví dụ: 'nhân 2 phân số là nhân chéo', '2 âm nhân nhau ra âm') nhưng bị gán vai trò SCAFFOLDING -> Đính kèm ở DÒNG CUỐI CÙNG: <!-- AUDIT_AGENT: MISCONCEPTION -->
     * Nếu học sinh hỏi định nghĩa, lý thuyết, khái niệm (ví dụ: 'số hữu tỉ là gì ạ', 'định nghĩa hàm số') nhưng bị gán vai trò SCAFFOLDING -> Đính kèm ở DÒNG CUỐI CÙNG: <!-- AUDIT_AGENT: KNOWLEDGE_TRACING -->
     * Nếu học sinh xúc phạm, chửi thề, quấy rối, vô lễ nhưng bị gán học tập -> Đính kèm ở DÒNG CUỐI CÙNG: <!-- AUDIT_AGENT: SAFETY -->
     * Nếu học sinh đang THỰC SỰ HỎI BÀI TOÁN HOẶC ĐANG TÍNH TOÁN GIẢI TOÁN nhưng bị gán nhầm sang SAFETY hoặc MISCONCEPTION -> Đính kèm ở DÒNG CUỐI CÙNG: <!-- AUDIT_AGENT: SCAFFOLDING -->
   - NGUYÊN TẮC BẤT DI BẤT DỊCH CỦA THẺ ẨN (CHỐNG BẮT SAI & FALSE POSITIVE):
     * VAI TRÒ SAFETY BAO GỒM CẢ CHÀO HỎI & NGOÀI LỀ: Khi học sinh CHÀO HỎI ('chào thầy', 'em chào thầy', 'hello', 'hi', 'thầy ơi', 'tạm biệt') hoặc trò chuyện ngoài bài học: Vai trò SAFETY là HOÀN TOÀN CHUẨN XÁC theo thiết kế hệ thống! TUYỆT ĐỐI KHÔNG coi đây là lỗi và TUYỆT ĐỐI KHÔNG gắn thẻ <!-- AUDIT_AGENT: SCAFFOLDING -->!
     * Nếu phân luồng đã CHUẨN XÁC: TUYỆT ĐỐI KHÔNG đính kèm bất kỳ thẻ ẩn nào.
     * TUYỆT ĐỐI KHÔNG gắn thẻ trùng với vai trò hiện tại (ví dụ: nếu vai trò hiện tại đã là SCAFFOLDING thì tuyệt đối không gắn thẻ SCAFFOLDING).
     * BẢO VỆ CÂU TRẢ LỜI NGẮN TRONG HỘI THOẠI: Khi học sinh trả lời ngắn gọn (như 'dạ', 'vâng', 'là 6', 'bằng 3', 'em chưa hiểu', 'tiếp theo làm gì') để đáp lại câu hỏi của Thầy: Đây là sự tiếp nối hoàn toàn tự nhiên của vai trò SCAFFOLDING, TUYỆT ĐỐI KHÔNG coi là sai lệch và TUYỆT ĐỐI KHÔNG gắn thẻ ẩn!
     * DANH MỤC AGENT HỢP LỆ DUY NHẤT: Bắt buộc chỉ được chọn 1 trong 4 nhãn chính xác: MISCONCEPTION, KNOWLEDGE_TRACING, SAFETY, SCAFFOLDING. Tuyệt đối không tự sáng tạo tên nhãn khác (như MATH, TUTOR, FOLLOWUP...).
     * Thẻ ẩn BẮT BUỘC phải đặt ở dòng cuối cùng riêng biệt của câu trả lời, cú pháp chính xác: <!-- AUDIT_AGENT: <AGENT_NAME> -->
     * TUYỆT ĐỐI KHÔNG giải thích lý do hay bình luận gì thêm cạnh thẻ ẩn (để tiết kiệm token và giữ tốc độ streaming).
"""

# ==============================================================================
# US 10.4 & US 8.1: GIAO THỨC BÓC TÁCH THẺ ẨN (HIDDEN TAG PARSER)
# ==============================================================================
AUDIT_REGEX = re.compile(r"<!--\s*AUDIT_AGENT\s*:\s*([A-Z_]+)\s*-->", re.IGNORECASE)
VALID_AUDIT_AGENTS = {"MISCONCEPTION", "KNOWLEDGE_TRACING", "SAFETY", "SCAFFOLDING"}

# Giao thức thẩm định xác nhận an toàn ngôn từ kép (Double-Check Safety Confirmation Tag)
SAFETY_CONFIRM_REGEX = re.compile(
    r"<!--\s*SAFETY_CONFIRM\s*:\s*(YES|NO)(?:\s*\|\s*REASON\s*:\s*([^>]+?))?\s*-->",
    re.IGNORECASE
)

def extract_audit_tag(text: str) -> tuple[str, Optional[str]]:
    """
    Bóc tách thẻ ẩn <!-- AUDIT_AGENT: <AGENT> --> khỏi chuỗi văn bản phản hồi.
    Lấy thẻ xuất hiện cuối cùng (theo đúng chuẩn dòng cuối) và xóa toàn bộ thẻ ẩn.
    
    Returns:
        tuple (clean_text, suggested_agent):
        - clean_text: Văn bản đã được lọc sạch hoàn toàn thẻ ẩn, sẵn sàng gửi học sinh.
        - suggested_agent: Tên Agent viết hoa chuẩn (MISCONCEPTION, KNOWLEDGE_TRACING, SAFETY, SCAFFOLDING)
                           hoặc None nếu không có thẻ ẩn / thẻ không hợp lệ.
    """
    if not text:
        return "", None
        
    matches = list(AUDIT_REGEX.finditer(text))
    if not matches:
        return text.strip(), None

    last_match = matches[-1]
    raw_agent = last_match.group(1).strip().upper().replace("_AGENT", "")
    suggested_agent = raw_agent if raw_agent in VALID_AUDIT_AGENTS else None

    # Làm sạch toàn bộ thẻ ẩn khỏi văn bản
    clean_text = AUDIT_REGEX.sub("", text).strip()
    return clean_text, suggested_agent


def extract_safety_confirm_tag(text: str) -> tuple[str, Optional[bool], Optional[str]]:
    """
    Bóc tách thẻ ẩn <!-- SAFETY_CONFIRM: YES|NO | REASON: ... --> do Gemini sinh ra.
    
    Returns:
        tuple (clean_text, is_violation, reason):
        - clean_text: Văn bản đã làm sạch thẻ SAFETY_CONFIRM.
        - is_violation: True nếu Gemini xác nhận YES (thực sự vi phạm),
                        False nếu Gemini xác nhận NO (vô hại / bị bạn bắt nạt / trích dẫn),
                        None nếu không tìm thấy thẻ ẩn này.
        - reason: Lý do vi phạm cụ thể do Gemini trích xuất (nếu có).
    """
    if not text:
        return "", None, None

    matches = list(SAFETY_CONFIRM_REGEX.finditer(text))
    if not matches:
        return text.strip(), None, None

    last_match = matches[-1]
    status_str = last_match.group(1).strip().upper()
    reason_str = (last_match.group(2) or "").strip()

    is_violation = True if status_str == "YES" else False
    clean_text = SAFETY_CONFIRM_REGEX.sub("", text).strip()
    return clean_text, is_violation, reason_str if reason_str else None


def sanitize_stream_chunks(chunk_iterator):
    """
    US 10.4 & US 11.6 & US 8.1: Bộ lọc chống rò rỉ thẻ ẩn và tag comprehension khi streaming.
    Sử dụng kỹ thuật Dynamic Lookahead Holding Buffer để ngăn chặn việc các thẻ bị cắt đôi/cắt ba
    giữa các chunk (Chunk Boundary Fragmentation) hiển thị lên màn hình học sinh ([AC-AL-01]).
    Bảo vệ triệt để: <!-- AUDIT_AGENT:... -->, <!-- SAFETY_CONFIRM:... -->, <!-- PROBE_PENDING -->, v.v.
    Đảm bảo 100% không rò rỉ dù thẻ có dài bất kỳ (200-500+ ký tự) hoặc stream bị đứt quãng.
    """
    buffer = ""
    for chunk in chunk_iterator:
        buffer += chunk
        
        # 1. Liên tục loại bỏ các tag hoàn chỉnh đã xuất hiện trong buffer
        buffer = AUDIT_REGEX.sub("", buffer)
        buffer = SAFETY_CONFIRM_REGEX.sub("", buffer)
        buffer = re.sub(r"<!--[\s\S]*?-->", "", buffer)
        buffer = re.sub(r"\[(?:SUMMER_)?PROBE_PENDING\]", "", buffer, flags=re.IGNORECASE)
        buffer = buffer.replace("[COMPREHENSION_CHECK]", "").replace("COMPREHENSION_CHECK", "")
        
        # 2. Xác định điểm an toàn để xả (yield):
        hold_pos = len(buffer)
        
        # Nếu buffer chứa '<!--' mà chưa gặp '-->' -> Chắc chắn giữ lại từ '<!--' bất kể độ dài
        open_comment_idx = buffer.rfind("<!--")
        if open_comment_idx != -1:
            hold_pos = min(hold_pos, open_comment_idx)
        else:
            # Nếu chưa đủ 4 ký tự '<!--', kiểm tra xem đuôi buffer có dở dang '<', '<!', '<!-' không
            for prefix_len in (3, 2, 1):
                if len(buffer) >= prefix_len:
                    tail = buffer[-prefix_len:]
                    if "<!--".startswith(tail):
                        hold_pos = min(hold_pos, len(buffer) - prefix_len)
                        break
                        
        # Kiểm tra thẻ ngoặc vuông '[' dở dang (chỉ giữ nếu khớp tiền tố của thẻ hệ thống)
        open_bracket_idx = buffer.rfind("[")
        if open_bracket_idx != -1:
            after_bracket = buffer[open_bracket_idx:].upper()
            bracket_prefixes = ("[COMPREHENSION", "[PROBE", "[SUMMER_PROBE")
            if any(p.startswith(after_bracket) or after_bracket.startswith(p) for p in bracket_prefixes):
                hold_pos = min(hold_pos, open_bracket_idx)
                
        safe_to_yield = buffer[:hold_pos]
        buffer = buffer[hold_pos:]
        
        if safe_to_yield:
            yield safe_to_yield
            
    # Khi stream kết thúc, xử lý và xả nốt phần buffer còn lại
    if buffer:
        final_clean = AUDIT_REGEX.sub("", buffer)
        final_clean = SAFETY_CONFIRM_REGEX.sub("", final_clean)
        final_clean = re.sub(r"<!--[\s\S]*?-->", "", final_clean)
        # Loại bỏ triệt để thẻ dở dang chưa kịp đóng do đứt cáp/timeout
        final_clean = re.sub(r"<!--[\s\S]*$", "", final_clean)
        final_clean = re.sub(r"\[(?:SUMMER_)?PROBE_PENDING\]", "", final_clean, flags=re.IGNORECASE)
        final_clean = re.sub(r"\[(?:COMPREHENSION_CHECK|SUMMER_PROBE_PENDING|PROBE_PENDING)[^\]]*$", "", final_clean, flags=re.IGNORECASE)
        final_clean = final_clean.replace("[COMPREHENSION_CHECK]", "").replace("COMPREHENSION_CHECK", "").rstrip()
        if final_clean.strip():
            yield final_clean


_IMAGE_MEMORY_CACHE: dict[str, Image.Image] = {}

def load_image_from_url(url: Optional[str], timeout: float = 10.0) -> Optional[Image.Image]:
    """
    Tải ảnh từ Cloudinary HTTPS URL và chuyển thành đối tượng PIL.Image.
    Áp dụng In-Memory Cache: Nếu URL đã tải một lần, các lần sau lấy trực tiếp từ RAM (0ms).
    Xử lý lỗi an toàn: timeout hoặc lỗi HTTP sẽ trả về None thay vì làm sập server.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return None
    if url in _IMAGE_MEMORY_CACHE:
        return _IMAGE_MEMORY_CACHE[url]
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))
            _IMAGE_MEMORY_CACHE[url] = img
            return img
    except Exception as e:
        print(f"[Cảnh báo Vision] Không thể tải ảnh từ Cloudinary ({url}): {e}")
        return None
# ==========================================
# CHỈ DẪN HỆ THỐNG XỬ LÝ ẢNH BÀI TOÁN (SOCRATIC VISION)
# ==========================================
SOCRATIC_VISION_INSTRUCTION = """
--- HƯỚNG DẪN XỬ LÝ ẢNH BÀI TOÁN TỪ CLOUDINARY (SOCRATIC VISION) ---
Học sinh vừa gửi một bức ảnh bài toán kèm lời nhắn. BẠN BẮT BUỘC PHẢI THỰC HIỆN:
1. ĐỌC VÀ TRÍCH XUẤT ĐỀ BÀI:
   - Hãy quan sát thật kỹ các con số, hình vẽ và công thức toán trong ảnh.
   - Viết lại đề bài rõ ràng ở đầu phản hồi bằng công thức LaTeX chuẩn ($...$ hoặc $$...$$) để học sinh xác nhận bạn đã đọc đúng đề.
2. TUYỆT ĐỐI KHÔNG GIẢI RA ĐÁP ÁN:
   - Nghiêm cấm đưa ra kết quả cuối cùng hoặc tự thực hiện các phép tính thay học sinh.
3. GỢI MỞ BƯỚC ĐẦU TIÊN (SOCRATIC HOOK):
   - Đặt DUY NHẤT 01 câu hỏi gợi mở đơn giản nhất dẫn dắt học sinh thực hiện bước đầu tiên.
4. XỬ LÝ ẢNH MỜ / KHÔNG HỢP LỆ:
   - Nếu ảnh quá mờ hoặc mất góc: Lịch sự nhờ học sinh chụp lại rõ nét hơn.
   - Nếu ảnh không phải bài toán: Nhẹ nhàng từ chối và nhắc học sinh gửi ảnh bài tập toán.
"""
    
# ==========================================
# HÀM HỖ TRỢ ROTATION / COMPREHENSION / MAX_TOKENS
# ==========================================
_NEGATION_CORRECTION_MARKERS = (
    "sai rồi", "chưa đúng", "chưa chính xác", "nhầm rồi", "không đúng",
    "chưa phải", "chưa khớp", "cần sửa lại", "thử tính lại",
    "kiểm tra lại", "làm lại bước", "bị nhầm", "chưa chuẩn",
)
_PRAISE_MARKERS = (
    "chính xác", "hoàn toàn đúng", "đúng rồi", "rất tốt", "xuất sắc",
    "chuẩn rồi", "chúc mừng em", "khen ngợi", "rất giỏi",
)
_CONCLUSIVE_KEYWORDS = (
    "đáp án", "kết quả", "chọn đúng", "đáp án a", "đáp án b",
    "đáp án c", "đáp án d", "nghiệm của phương trình", "nghiệm là", "vô nghiệm",
)
_CLOSING_QUESTION_HINTS = (
    "đã hiểu", "hiểu chưa", "hiểu bài", "rõ chưa", "thắc mắc",
    "bài tiếp", "bài mới", "bài khác", "tiếp tục không", "làm thêm",
)
_EXAMPLE_REQUEST_REGEX = re.compile(
    r"(?<!\w)(ví dụ|vi du|dí dụ|di du|vidu|vd|vdu|bài mẫu|làm mẫu|giải mẫu|cho mẫu|xem mẫu)(?!\w)",
    re.IGNORECASE | re.UNICODE,
)


def _resolve_model_and_fallbacks(sys_config: Optional[dict]) -> tuple[str, list[str]]:
    """
    Xác định primary model và chuỗi failover hợp lệ.
    - Hỗ trợ xoay vòng gemini-3.5-flash-lite <-> gemini-3.1-flash-lite khi bật GEMINI_ROTATE_LITE_MODELS=1
      hoặc sys_config['rotate_lite_models'].
    - Tuyệt đối không đưa gemini-3.6-flash hoặc gemini-3.8-flash vào failover/rotation.
    """
    rotate_env = os.getenv("GEMINI_ROTATE_LITE_MODELS", "").strip().lower() in ("1", "true", "yes")
    rotate_cfg = bool(sys_config and sys_config.get("rotate_lite_models"))

    if rotate_env or rotate_cfg:
        with _ROTATION_LOCK:
            idx = next(_ROTATION_COUNTER) % len(_ROTATION_LITE_MODELS)
        active_model = _ROTATION_LITE_MODELS[idx]
    else:
        active_model = (
            (sys_config.get("primary_model") if sys_config else None)
            or os.getenv("GEMINI_CHAT_MODEL")
            or _ACTIVE_MODEL_NAME
        )

    configured_backup = (
        (sys_config.get("backup_model") if sys_config else None)
        or os.getenv("GEMINI_BACKUP_MODEL")
    )
    candidates: list[str] = []
    if configured_backup and configured_backup not in _FORBIDDEN_BACKUP_MODELS:
        candidates.append(configured_backup)

    if os.getenv("GEMINI_DISABLE_CROSS_FALLBACK", "").strip().lower() in ("1", "true", "yes"):
        fallback_chain = [
            c for c in candidates
            if c and c != active_model and c == configured_backup and c not in _FORBIDDEN_BACKUP_MODELS
        ]
        return active_model, fallback_chain

    if active_model == "gemini-3.5-flash-lite":
        candidates.append("gemini-3.1-flash-lite")
    elif active_model == "gemini-3.1-flash-lite":
        candidates.append("gemini-3.5-flash-lite")
    else:
        candidates.extend(["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"])

    fallback_chain: list[str] = []
    for m_name in candidates:
        if m_name and m_name != active_model and m_name not in _FORBIDDEN_BACKUP_MODELS and m_name not in fallback_chain:
            fallback_chain.append(m_name)
    return active_model, fallback_chain


def _is_transient_gemini_error(err: Exception) -> bool:
    """Nhận diện lỗi mạng/timeout/400-stream hoặc 429 RPM ngắn hạn (không phải hết RPD 500/ngày)."""
    msg = str(err).lower()
    if "limit: 500" in msg or "requestsperday" in msg:
        return False
    return any(tok in msg for tok in (
        "remotedisconnected", "connection aborted", "connectionerror", "newconnectionerror",
        "winerror 10013", "read timed out", "timed out", "timeout",
        "unknown error trying to retrieve streaming response",
        "limit: 15", "resource_exhausted", "429", "503", "500",
    ))


_STUDENT_STATUS_REGEX = re.compile(r"<!--\s*STUDENT_STATUS\s*:\s*(CORRECT|WRONG|GUIDING)\s*-->", re.IGNORECASE)


def _extract_student_status_tag(raw_text: str) -> Optional[str]:
    if not raw_text:
        return None
    matches = list(_STUDENT_STATUS_REGEX.finditer(raw_text))
    if not matches:
        return None
    return matches[-1].group(1).strip().upper()


def _infer_turn_emotion(
    cleaned_text: str,
    initial_emotion: str,
    is_comprehension: bool,
    clean_target_agent: str,
    user_query: str,
    history_text: str,
    raw_text: str = "",
) -> str:
    """Đồng bộ emotion cuối lượt theo thẻ STUDENT_STATUS và kết quả fact-check thực tế trong phản hồi."""
    if clean_target_agent == "SAFETY" or initial_emotion == "WARNING":
        return initial_emotion
    if is_comprehension:
        return "CORRECT"

    user_low = (user_query or "").lower()
    is_asking_example = bool(_EXAMPLE_REQUEST_REGEX.search(user_query or ""))
    if is_asking_example:
        return "GUIDING"

    low = (cleaned_text or "").lower()
    low_masked = re.sub(
        r"(?:đã\s+tự|tự)\s+kiểm tra lại|chỗ nhầm lẫn|(?:em\s+)?đã\s+sửa\s+lại"
        r"|(?:hoặc\s+(?:em\s+)?)?(?:kiểm tra|xem)\s+lại\s+(?:xem\s+)?đề(?:\s+bài)?",
        " ",
        low,
    )
    has_sq = ("\\square" in (cleaned_text or "") or "□" in (cleaned_text or ""))
    has_strict_err = any(m in low_masked for m in (
        "chưa đúng", "chưa chính xác", "chưa chuẩn", "chưa khớp", "sai dấu",
        "nhầm rồi", "quên đổi dấu", "quên ngoặc", "không phải là số nguyên tố",
        "chưa hợp lý", "sai rồi", "chưa tối giản",
        "cần đổi dấu", "phải đổi dấu", "chưa đổi dấu", "không cần cộng",
        "phải được đổi", "em hãy sửa lại", "chứ không phải", "không phải là", "bị ngược",
        "tuy nhiên, em xem lại", "tuy nhiên, em hãy kiểm tra lại", "tuy nhiên em hãy kiểm tra lại",
        "chưa chia hết", "lập phương trình lại",
    )) or (
        any(p in low_masked for p in ("nhưng ở", "tuy nhiên ở", "tuy nhiên, ở", "tuy nhiên,", "tuy nhiên "))
        and any(c in low_masked for c in (
            "kiểm tra lại", "xem lại", "chưa", "em lưu ý", "lưu ý ",
            "sửa lại", "đổi thành", "chứ không phải", "không phải", "khi phía trước",
        ))
    )
    has_err_feedback = has_strict_err or any(m in low_masked for m in (
        "bị nhầm", "nhầm lẫn", "kiểm tra lại", "xem lại", "thử tính lại",
        "chú ý dấu", "lưu ý dấu", "cộng tử", "quên nhân", "quên chia",
    ))
    is_help_only_ask = bool(
        re.search(r"\b(giúp em|hướng dẫn em|chỉ em|cho em hỏi|làm thế nào|làm sao)\b", user_low)
    ) and not re.search(r"\b(em tính được|em ra|đáp án|kết quả|em nghĩ|đúng không|phải không)\b|=", user_low)
    is_first_problem_ask = not (history_text or "").strip() and (
        is_help_only_ask
        or not re.search(r"\b(em tính được|em ra|đáp án|kết quả|em nghĩ|em làm)\b", user_low)
    )

    is_pure_praise_guiding = (
        initial_emotion == "GUIDING"
        and not has_err_feedback
        and any(p in low_masked for p in ("rất khen", "khen ngợi", "rất chính xác", "hoàn toàn đúng", "chính xác rồi", "đúng rồi"))
    )
    tagged_status = _extract_student_status_tag(raw_text)
    if tagged_status == "WRONG" and not is_first_problem_ask and not is_pure_praise_guiding:
        return "WRONG"
    if tagged_status == "CORRECT" and not has_sq and not has_err_feedback and not is_first_problem_ask:
        return "CORRECT"

    if tagged_status == "GUIDING" and initial_emotion != "WRONG" and not has_strict_err:
        return "GUIDING"

    if has_err_feedback and not is_first_problem_ask:
        return "WRONG"

    # CHỈ hạ WRONG -> GUIDING nếu thực sự là lời khen toàn phần không kèm nhắc lỗi (không hạ chỉ vì có \square!)
    if initial_emotion == "WRONG" and tagged_status != "WRONG" and not has_err_feedback and not has_sq:
        if any(p in low for p in ("rất tốt", "đúng rồi", "hoàn toàn đúng", "chính xác", "tuyệt vời")):
            return "GUIDING"

    if initial_emotion == "CORRECT" and has_sq:
        return "GUIDING"
    return initial_emotion


def _detect_comprehension(cleaned_text: str, raw_text: str, clean_target_agent: str) -> bool:
    """
    Phát hiện học sinh đã hoàn thành bài toán, tách khỏi nhãn MISCONCEPTION_AGENT.
    - Nếu vẫn còn ô trống điền khuyết (\\square / □) thì chắc chắn CHƯA hoàn thành -> False.
    - Chặn cứng SAFETY và phản hồi mang tính phủ định/sửa sai hoặc câu hỏi gợi bước tiếp theo.
    """
    if clean_target_agent == "SAFETY":
        return False
    if "\\square" in (cleaned_text or "") or "□" in (cleaned_text or ""):
        return False

    cleaned_lower = (cleaned_text or "").lower()
    if any(neg in cleaned_lower for neg in _NEGATION_CORRECTION_MARKERS):
        return False

    has_comp_tag = (
        "[COMPREHENSION_CHECK]" in (raw_text or "")
        or "COMPREHENSION_CHECK" in (raw_text or "")
    )
    stripped_end = (cleaned_text or "").strip().rstrip("*_~` \t\r\n")
    ends_with_question = stripped_end.endswith("?")

    is_praise = any(p in cleaned_lower for p in _PRAISE_MARKERS)
    strict_conclusive_markers = (
        "mẫu trình bày", "trình bày hoàn chỉnh", "ghi vào vở", "hoàn thành",
        "nghiệm của phương trình", "nghiệm là", "vô nghiệm",
        "đáp số", "kết quả cuối", "chọn đúng", "đáp án a", "đáp án b", "đáp án c", "đáp án d",
    )
    has_conclusive = any(k in cleaned_lower for k in strict_conclusive_markers)

    # Nếu còn câu hỏi mở (không phải câu hỏi đóng bài) nằm trong văn bản -> chưa xong bài
    text_no_latex = re.sub(r"\$\$[\s\S]*?\$\$|\$[^$\n]*?\$", " ", cleaned_text or "")
    q_parts = [p.strip() for p in text_no_latex.split("?")[:-1]] if "?" in text_no_latex else []
    for qp in q_parts:
        last_sent = re.split(r"[.!\n]+", qp)[-1].lower()
        if not any(hint in last_sent for hint in _CLOSING_QUESTION_HINTS):
            return False

    if ends_with_question:
        last_sentence = re.split(r"[.!?\n]+", stripped_end[:-1])[-1].lower() if len(stripped_end) > 1 else ""
        if any(hint in last_sentence for hint in _CLOSING_QUESTION_HINTS):
            return bool(has_comp_tag or (is_praise and has_conclusive))
        return False

    if clean_target_agent == "MISCONCEPTION":
        return bool((has_comp_tag or has_conclusive) and is_praise)

    return bool(has_comp_tag or (is_praise and has_conclusive))


def _merge_continuation_text(prefix: str, cont: str) -> str:
    """Ghép phần nối tiếp khi bị cắt MAX_TOKENS và loại bỏ đoạn văn lặp lại nếu Gemini lặp mở đầu."""
    p = (prefix or "").rstrip()
    c = (cont or "").strip()
    if not c:
        return prefix or ""
    if not p:
        return c
    # Loại bỏ các đoạn đầu của continuation đã xuất hiện gần như nguyên văn ở prefix
    kept_paras = []
    seen_p_norm = re.sub(r"\s+", " ", p.lower())
    for para in re.split(r"\n{2,}", c):
        norm_para = re.sub(r"\s+", " ", para.strip().lower())
        if len(norm_para) >= 35 and norm_para[:45] in seen_p_norm:
            continue
        kept_paras.append(para)
    c_clean = "\n\n".join(kept_paras).strip()
    if not c_clean:
        return p
    return p + " " + c_clean


def _needs_max_tokens_continuation(text: str, check_incomplete_sentence: bool = True) -> bool:
    """Kiểm tra phản hồi chạm MAX_TOKENS có bị cắt ngang (thiếu $, hoặc đứt câu giữa chừng) hay không."""
    if not text or not text.strip():
        return False
    cleaned = AUDIT_REGEX.sub("", text)
    cleaned = SAFETY_CONFIRM_REGEX.sub("", cleaned)
    cleaned = re.sub(r"<!--[\s\S]*?-->", "", cleaned)
    cleaned = re.sub(r"\[(?:SUMMER_)?PROBE_PENDING\]", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("[COMPREHENSION_CHECK]", "").replace("COMPREHENSION_CHECK", "").strip()
    if not cleaned:
        return True
    dbl_cnt = len(re.findall(r"(?<!\\)\$\$", cleaned))
    wo_dbl = re.sub(r"(?<!\\)\$\$", "", cleaned)
    sgl_cnt = len(re.findall(r"(?<!\\)\$", wo_dbl))
    if dbl_cnt % 2 != 0 or sgl_cnt % 2 != 0:
        return True
    if check_incomplete_sentence:
        stripped_end = cleaned.rstrip("*_~` \t\r\n")
        if not stripped_end.endswith((".", "!", "?", "$")):
            return True
    return False


# ==========================================
# HÀM ĐIỀU PHỐI CHÍNH (Router Function) - CÓ TÍCH HỢP REVIEWER TỰ ĐỘNG SỬA LỖI
# ==========================================
def agent_router(
    target_agent: str,
    task_description: str,
    history_text: str,
    user_query: str,
    expected_answer: str = "",
    grade_level: int = None,
    attachment_url: Optional[str] = None,
    meta: Optional[dict] = None,
    session_image_urls: Optional[list[str]] = None,
):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        yield "Lỗi: Chưa cấu hình GEMINI_API_KEY"
        return
        
    genai.configure(api_key=api_key, transport="rest")

    # US 10.3 (Task T10.3.3): Đọc cấu hình động từ SystemConfigService (Redis Cache -> Neon DB)
    sys_config: Optional[dict] = None
    active_temperature = 0.35
    active_top_p = 0.90
    raw_max_tokens = _DEFAULT_MAX_OUTPUT_TOKENS
    try:
        from services.system_config_service import get_system_settings
        sys_config = get_system_settings()
        active_temperature = float(sys_config.get("temperature", 0.35))
        active_top_p = float(sys_config.get("top_p", 0.90))
        raw_max_tokens = int(sys_config.get("max_output_tokens", _DEFAULT_MAX_OUTPUT_TOKENS))
    except Exception as err:
        print(f"[Router] Cảnh báo đọc SystemConfig: {err} — Dùng fallback.")
        sys_config = None

    # Hỗ trợ cả GEMINI_ROTATE_LITE_MODELS và GEMINI_ROTATE_MODELS
    if (
        os.getenv("GEMINI_ROTATE_MODELS", "").strip().lower() in ("1", "true", "yes")
        and not os.getenv("GEMINI_ROTATE_LITE_MODELS")
    ):
        with _ROTATION_LOCK:
            idx = next(_ROTATION_COUNTER) % len(_ROTATION_LITE_MODELS)
        active_model = _ROTATION_LITE_MODELS[idx]
        _, fallback_chain = _resolve_model_and_fallbacks({**(sys_config or {}), "primary_model": active_model, "rotate_lite_models": False})
    else:
        active_model, fallback_chain = _resolve_model_and_fallbacks(sys_config)

    active_max_tokens = max(_MIN_CHAT_MAX_OUTPUT_TOKENS, raw_max_tokens)

    if meta is not None:
        meta["model_used"] = active_model

    print(f"[AI Runtime] Socratic Tutor dispatched with dynamic model: {active_model} | temp={active_temperature} | max_tokens={active_max_tokens}")

    # US 10.4: Chuẩn hóa tên Agent trước khi gắn vào system_instruction
    clean_target_agent = target_agent.replace("_AGENT", "").strip().upper()
    resolved_system_instruction = TEACHER_SYSTEM_INSTRUCTION.replace("{target_agent}", clean_target_agent)

    def _build_gemini_model(model_name_str: str):
        return genai.GenerativeModel(
            model_name=model_name_str,
            system_instruction=resolved_system_instruction,
            generation_config=genai.GenerationConfig(
                temperature=active_temperature,
                top_p=active_top_p,
                max_output_tokens=active_max_tokens,
            )
        )
    model = _build_gemini_model(active_model)
    current_agent_label = "Chat"

    grade_context = _get_grade_context(grade_level)
    base_prompt = f"""
{grade_context}
Vai trò chuyên môn hiện tại: {clean_target_agent}.
Chỉ đạo sư phạm từ Orchestrator: {task_description}

--- LỊCH SỬ TRÒ CHUYỆN ---
{history_text}

--- HỌC SINH VỪA NÓI ---
{user_query}

--- THẨM ĐỊNH AN TOÀN NGÔN TỪ (GIAO THỨC THẺ ẨN SAFETY_CONFIRM) ---
- Đánh giá câu nói của học sinh: '{user_query}' trong ngữ cảnh trò chuyện hiện tại.
- BẮT BUỘC đính kèm thẻ ẩn xác nhận ở dòng CUỐI CÙNG (sau mọi nội dung khác):
  * Nếu học sinh THỰC SỰ có hành vi nói tục, chửi thề, dùng tiếng lóng thô tục, sỉ nhục AI/gia sư, hoặc xưng hô vô lễ thiếu tôn trọng nghiêm trọng:
    <!-- SAFETY_CONFIRM: YES | REASON: <lý do vi phạm cụ thể ngắn gọn> -->
  * Nếu học sinh KHÔNG có hành vi nói tục/xúc phạm (ví dụ: học sinh chỉ đang chào hỏi, hỏi bài toán, cảm thán khó khăn 'bài khoai quá', 'tính toát mồ hôi', hoặc học sinh đang TÂM SỰ việc bị bạn bè ở lớp trêu chọc/bắt nạt, trích dẫn văn bản/đề bài, trêu đùa trong sáng):
    <!-- SAFETY_CONFIRM: NO -->
- NGUYÊN TẮC BẢO VỆ HỌC SINH: Thẻ ẩn này dùng để hệ thống quyết định có gửi email thông báo cho Phụ huynh hay không. Tuyệt đối không quy kết oan khi học sinh chỉ đang tâm sự bị bạn bắt nạt hoặc bộc phát khó khăn bài toán bình thường.
- BẮT BUỘC KHUNG ĐIỀN KHUYẾT: Khi đang gợi mở từng bước (chưa chốt đáp án cuối, không phải lời chào/thăm dò), luôn kèm 1 khung trình bày có `\\square` đặt trong `$...$` hoặc `$$...$$` (VD: `$$1\\text{{ tấn}} = \\square\\text{{ kg}}$$`, `$$x = 48500 \\ \\square \\ 19200$$`, `$$120 + 25 \\times 4 = 120 + \\square$$`).
- ĐÁNH DẤU TRẠNG THÁI BÀI LÀM (THẺ ẨN BẮT BUỘC Ở CUỐI CÙNG): Sau thẻ SAFETY_CONFIRM, gắn 1 thẻ: `<!-- STUDENT_STATUS: CORRECT -->` (nếu em vừa trả lời ĐÚNG đáp án cuối cùng của bài toán), `<!-- STUDENT_STATUS: WRONG -->` (CHỈ dùng khi em vừa tính/biến đổi SAI phép tính hoặc sai bản chất toán học), hoặc `<!-- STUDENT_STATUS: GUIDING -->` (nếu em mới hỏi đề, xin ví dụ, hay đã làm đúng bước trung gian dù còn thiếu bước kế tiếp/cần xét điều kiện thêm).
- Nhắc lại: Tuân thủ đầy đủ quy tắc Sư phạm, Fact-check toán học, [COMPREHENSION_CHECK] và giao thức thẻ ẩn AUDIT_AGENT (đối chiếu '{user_query}' với vai trò '{clean_target_agent}') trong System Instruction.
- Đối chiếu kỹ TỪNG DỮ KIỆN trong đề bài gốc (cẩn thận không nhầm số liệu của đối tượng/lớp thứ hai trong đề với bài ví dụ trước đó).
- Nếu bài toán có điều kiện lọc nghiệm (x nguyên, ĐKXĐ, x > 0...) và học sinh đã tìm đúng các giá trị trung gian (như $x = \frac{3}{2}$ từ $2x - 3 = 0$), TUYỆT ĐỐI KHÔNG nói sai hay bắt tính lại; hãy khen đúng phần giải nghiệm rồi gợi mở kiểm tra điều kiện.
- Nếu chưa hoàn thành bài, BẮT BUỘC viết 1 câu hỏi gợi mở kết thúc bằng dấu `?` Ở SAU khung công thức `$$...$$` (không kết thúc ngang tại `$$...$$`).
"""

    is_asking_for_example = bool(_EXAMPLE_REQUEST_REGEX.search(user_query or ""))

    if clean_target_agent != "SAFETY" and is_asking_for_example:
        base_prompt += """
--- KỸ THUẬT BÀI MẪU TƯƠNG TỰ (ANALOGICAL SCAFFOLDING) ---
Học sinh đang xin ví dụ hoặc làm mẫu. BẠN BẮT BUỘC PHẢI THỰC HIỆN:
1. TỰ ĐẶT BÀI TOÁN MỚI: Giữ nguyên cấu trúc toán học của bài gốc nhưng THAY TOÀN BỘ con số và tên biến (nếu có).
2. MÔ PHỎNG LỜI GIẢI ĐẦY ĐỦ THEO ĐÚNG FORMAT CẤP LỚP: Tự trình bày từng dòng lời giải chi tiết cho bài toán mẫu vừa tạo (Lệnh này GHI ĐÈ lệnh cấm giải bài trước đó — chỉ giải BÀI MẪU, cấm giải BÀI GỐC). Không bắt học sinh giải bài mẫu này.
3. KẾT THÚC bằng câu mời: 'Bây giờ em áp dụng cách trình bày này vào bài toán của mình thử xem nhé?'
"""
    # ── Ký ức thị giác phiên học (Session Image Gallery) ───────────────────
    # Tập hợp danh sách các ảnh bài toán trong phiên học
    active_urls: list[str] = []
    if session_image_urls:
        for u in session_image_urls:
            if u and u not in active_urls:
                active_urls.append(u)
    elif attachment_url and attachment_url not in active_urls:
        active_urls.append(attachment_url)

    loaded_images: list[Image.Image] = []
    for u in active_urls:
        img = load_image_from_url(u)
        if img:
            loaded_images.append(img)

    if len(loaded_images) == 1:
        base_prompt += f"\n{SOCRATIC_VISION_INSTRUCTION}"
        # Nếu câu hiện tại học sinh không gửi lại ảnh mà đang dùng ảnh trước đó của phiên
        if not attachment_url:
            base_prompt += """
\n[LƯU Ý VỀ ĐỀ BÀI ĐÃ GỬI TRƯỚC ĐÓ]: Bức ảnh đính kèm là đề bài mà học sinh đã gửi trong phiên học này.
Học sinh đang hỏi tiếp về nội dung trong ảnh (ví dụ: 'bài 3a', 'câu 2', 'bài hình',...).
BẠN BẮT BUỘC PHẢI:
1. Quan sát kỹ bức ảnh đính kèm để tìm đúng câu hỏi/bài toán mà học sinh đang đề cập.
2. Trích xuất đúng công thức/yêu cầu của câu đó và gợi mở từng bước theo phương pháp Socratic.
3. TUYỆT ĐỐI KHÔNG nói 'Thầy chưa thấy ảnh' hay 'Em hãy gửi lại đề', vì bạn ĐANG CÓ ảnh đề bài của học sinh ngay trước mắt!
"""
    elif len(loaded_images) > 1:
        base_prompt += f"""
--- BỘ SƯU TẬP ẢNH ĐỀ BÀI TRONG PHIÊN HỌC ({len(loaded_images)} ẢNH) ---
Học sinh đã gửi {len(loaded_images)} bức ảnh bài toán trong phiên học này theo thứ tự từ cũ đến mới (Ảnh 1, Ảnh 2,...).
Tất cả các ảnh này đều được đính kèm vào ngữ cảnh của bạn.

HƯỚNG DẪN XỬ LÝ ĐA ẢNH:
1. Học sinh có thể đang hỏi về bức ảnh mới nhất HOẶC bất kỳ bức ảnh nào đã gửi trước đó (ví dụ: 'ảnh đầu tiên', 'ảnh trước', 'ảnh 1', 'ảnh 2', hoặc theo chủ đề bài toán như đại số/hình học).
2. Hãy quan sát toàn bộ các bức ảnh để tìm đúng bài toán mà học sinh đang đề cập:
   - Nếu học sinh nói 'ảnh đầu' hoặc hỏi bài trong bức ảnh đầu tiên: Hãy nhìn vào Ảnh 1.
   - Nếu học sinh hỏi bài trong ảnh gửi sau: Hãy nhìn vào Ảnh tương ứng.
3. Trích xuất đúng công thức/yêu cầu của bài toán đó và đặt câu hỏi gợi mở bước đầu tiên theo phương pháp Socratic.
4. TUYỆT ĐỐI KHÔNG nói 'Thầy chưa thấy ảnh' hay 'Em hãy gửi lại đề', vì bạn ĐANG CÓ toàn bộ các ảnh đề bài của học sinh ngay trước mắt!
"""
    elif attachment_url and not loaded_images:
        base_prompt += "\n[LƯU Ý]: Học sinh có đính kèm ảnh nhưng không tải được từ máy chủ Cloudinary. Hãy nhắc học sinh kiểm tra lại ảnh chụp."

    prompt = base_prompt.encode("utf-16", "surrogatepass").decode("utf-16", errors="replace") if isinstance(base_prompt, str) else base_prompt
    call_payload = [*loaded_images, prompt] if loaded_images else prompt

    # ── Agents cần Reviewer: lấy full text trước, kiểm duyệt, rồi mới stream ──────────────
    needs_review = target_agent in ("SCAFFOLDING_AGENT", "MISCONCEPTION_AGENT")

    if needs_review:
        reviewer = LocalReviewerAgent()
        max_retries = 2
        current_attempt = 0
        final_text = ""
        last_raw_text = ""
        is_comprehension_detected = False
        suggested_agent = None

        require_final_completion = (
            "Học sinh tính đúng:" in task_description
            or "đã giải đúng bài toán" in task_description
        )
        if require_final_completion:
            prompt += (
                "\n[BẮT BUỘC CHỐT HOÀN THÀNH]: Học sinh đã tính ĐÚNG đáp án cuối. "
                "Tuyệt đối KHÔNG hỏi kiểm tra lại hay đặt ô trống \\square; "
                "hãy khen ngợi, viết Mẫu trình bày hoàn chỉnh vào vở và gắn [COMPREHENSION_CHECK] ở cuối."
            )
            call_payload = [*loaded_images, prompt] if loaded_images else prompt

        def _generate_with_failover(payload, tel_meta: dict):
            nonlocal active_model, current_agent_label, model
            import time as _t
            last_err = None
            for retry_idx in range(2):
                try:
                    return generate_with_telemetry(
                        model, payload, active_model, current_agent_label, telemetry_meta=tel_meta
                    )
                except Exception as primary_err:
                    last_err = primary_err
                    if retry_idx < 1 and _is_transient_gemini_error(primary_err):
                        err_low = str(primary_err).lower()
                        delay = 4.5 if ("429" in err_low or "503" in err_low) else 1.5
                        _t.sleep(delay)
                        continue
                    break
            for fb_model in fallback_chain:
                if not fb_model or fb_model == active_model:
                    continue
                for fb_try in range(3):
                    try:
                        if fb_try == 0:
                            push_failover_event(is_429=_is_429_exception(last_err))
                            active_model = fb_model
                            current_agent_label = "Fallback"
                            model = _build_gemini_model(active_model)
                            if meta is not None:
                                meta["model_used"] = active_model
                        return generate_with_telemetry(
                            model, payload, active_model, "Fallback", telemetry_meta=tel_meta
                        )
                    except Exception as fb_err:
                        last_err = fb_err
                        if fb_try < 2 and _is_transient_gemini_error(fb_err):
                            _t.sleep(4.0 * (fb_try + 1))
                            continue
                        break
            raise last_err

        while current_attempt <= max_retries:
            try:
                # T10.2.2: Dùng generate_with_telemetry để thu thập token usage & finish_reason
                tel_meta: dict = {}
                response = _generate_with_failover(call_payload, tel_meta)
                generated_text = getattr(response, "text", None) or ""
                if not isinstance(generated_text, str):
                    generated_text = str(generated_text)

                finish_reason = tel_meta.get("finish_reason")
                if finish_reason is None:
                    finish_reason = extract_finish_reason(response)

                is_max_tokens_cut = (finish_reason == 2)
                if is_max_tokens_cut or _needs_max_tokens_continuation(generated_text, check_incomplete_sentence=False):
                    if is_max_tokens_cut:
                        print(f"[AI Runtime] ⚠️ Non-stream chạm MAX_TOKENS (finish_reason=2) trên {active_model}.")
                        if meta is not None:
                            meta["finish_reason"] = 2
                            meta["truncated"] = True
                    if _needs_max_tokens_continuation(generated_text, check_incomplete_sentence=is_max_tokens_cut):
                        cont_prompt = (
                            f"{prompt}\n\n"
                            f"[PHẦN ĐÃ VIẾT DỞ]:\n{generated_text[-350:]}\n\n"
                            "[YÊU CẦU]: Phần trả lời trên vừa bị ngắt giữa chừng do giới hạn token. "
                            "Hãy viết TIẾP NGAY LẬP TỨC từ chỗ bị cắt (TUYỆT ĐỐI KHÔNG lặp lại đoạn mở đầu hay câu chữ đã viết ở trên) "
                            "và kết thúc trọn vẹn bằng câu hỏi gợi mở + thẻ ẩn bắt buộc."
                        )
                        cont_payload = [*loaded_images, cont_prompt] if loaded_images else cont_prompt
                        try:
                            cont_tel_meta: dict = {}
                            cont_resp = _generate_with_failover(cont_payload, cont_tel_meta)
                            cont_text = getattr(cont_resp, "text", None) or ""
                            if isinstance(cont_text, str) and cont_text.strip():
                                generated_text = _merge_continuation_text(generated_text, cont_text)
                                if meta is not None:
                                    meta["continued_on_max_tokens"] = True
                        except Exception as cont_err:
                            print(f"[AI Runtime] ⚠️ Lỗi khi nối tiếp non-stream: {cont_err}")

                # US 10.4 & US 8.1: Bóc tách thẻ ẩn AUDIT_AGENT, SAFETY_CONFIRM và PROBE_PENDING
                clean_for_review, suggested_agent = extract_audit_tag(generated_text)
                clean_for_review, safety_confirmed, safety_reason = extract_safety_confirm_tag(clean_for_review)
                clean_for_review = re.sub(r"<!--\s*(?:SUMMER_)?PROBE_PENDING\s*-->", "", clean_for_review, flags=re.IGNORECASE)
                clean_for_review = re.sub(r"\[(?:SUMMER_)?PROBE_PENDING\]", "", clean_for_review, flags=re.IGNORECASE)
                clean_for_review = re.sub(r"<!--[\s\S]*?-->", "", clean_for_review)
                if meta is not None:
                    if suggested_agent:
                        meta["suggested_agent"] = suggested_agent
                    if safety_confirmed is not None:
                        meta["safety_confirmed"] = safety_confirmed
                    if safety_reason:
                        meta["safety_reason"] = safety_reason

                cleaned_text = (
                    clean_for_review.replace("[COMPREHENSION_CHECK]", "")
                    .replace("COMPREHENSION_CHECK", "")
                    .strip()
                )

                attempt_has_comprehension = _detect_comprehension(
                    cleaned_text, generated_text, clean_target_agent
                )

                needs_square_step = (
                    not require_final_completion
                    and not is_asking_for_example
                    and clean_target_agent in ("SCAFFOLDING", "MISCONCEPTION")
                    and "PROBE_PENDING" not in task_description
                    and "nộp bài mới" not in task_description.lower()
                    and bool(re.search(r"[\d\+\-\*\/\=\^x√]", user_query or ""))
                )

                review_result = reviewer.review(
                    user_query,
                    expected_answer,
                    cleaned_text,
                    has_comprehension=attempt_has_comprehension,
                    grade_level=grade_level,
                    history_text=history_text,
                    require_final_completion=require_final_completion,
                    require_square_template=needs_square_step,
                    is_wrong_turn=(clean_target_agent == "MISCONCEPTION"),
                )
                if not review_result["is_approved"]:
                    current_attempt += 1
                    print(f"[Reviewer] Tu choi lan {current_attempt}: {review_result['feedback']}")
                    reject_note = (
                        f"\n\n[BẢN NHÁP VỪA BỊ TỪ CHỐI]:\n{cleaned_text[:300]}\n\n"
                        f"[CẢNH BÁO - SỬA NGAY LỖI NÀY]: {review_result['feedback']}\n"
                        "Hãy viết lại câu trả lời HOÀN TOÀN MỚI khắc phục triệt để lỗi trên."
                    )
                    call_payload = (
                        [*loaded_images, prompt + reject_note]
                        if loaded_images
                        else prompt + reject_note
                    )
                    final_text = cleaned_text
                    last_raw_text = generated_text
                    is_comprehension_detected = attempt_has_comprehension
                    continue

                # Lưu nhãn đề xuất vào meta để bên ngoài orchestrator_bridge ghi DB
                if meta is not None:
                    meta["suggested_agent"] = suggested_agent

                # Stream văn bản ĐÃ LÀM SẠCH HOÀN TOÀN ra ngoài (không kèm thẻ ẩn)
                final_text = cleaned_text
                last_raw_text = generated_text
                is_comprehension_detected = attempt_has_comprehension
                break

            except Exception as e:
                yield f" [Loi AI: {str(e)}]"
                return

        if final_text:
            _wo_dbl = re.sub(r"(?<!\\)\$\$", "", final_text)
            if len(re.findall(r"(?<!\\)\$", _wo_dbl)) % 2 != 0:
                _fixed = re.sub(r"(?<!\$)(?<!\\)\$([A-Za-z0-9]+)(?=\s+[^\d\s$])", r"$\1$", final_text, count=1)
                _wo_dbl2 = re.sub(r"(?<!\\)\$\$", "", _fixed)
                if len(re.findall(r"(?<!\\)\$", _wo_dbl2)) % 2 == 0:
                    final_text = _fixed
                else:
                    # Xóa dấu $ lẻ cuối cùng nếu không tự ghép cặp được
                    _idx_last = final_text.rfind("$")
                    if _idx_last != -1 and not (final_text[_idx_last - 1:_idx_last] == "$" or final_text[_idx_last:_idx_last + 2] == "$$"):
                        final_text = final_text[:_idx_last] + final_text[_idx_last + 1:]

        if meta is not None:
            meta["has_comprehension"] = is_comprehension_detected
            init_emo = (
                "WRONG"
                if clean_target_agent == "MISCONCEPTION"
                else ("CORRECT" if require_final_completion else "GUIDING")
            )
            meta["inferred_emotion"] = _infer_turn_emotion(
                final_text, init_emo, is_comprehension_detected,
                clean_target_agent, user_query, history_text, raw_text=last_raw_text,
            )
            if "suggested_agent" not in meta or meta["suggested_agent"] is None:
                meta["suggested_agent"] = suggested_agent

        # Fake-stream word-by-word sau khi đã kiểm duyệt xong
        words = final_text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    else:
        # ── Agents không cần Reviewer: stream trực tiếp từ Gemini → user thấy chữ ngay ──
        is_comprehension_detected = False
        try:
            full_text_buffer = ""
            stream_tel_meta: dict = {}

            # T10.2.2 + T10.4.2: Stream qua telemetry, tự động failover qua fallback_chain khi lỗi trước chunk đầu,
            # đồng thời lọc thẻ ẩn/comprehension an toàn qua ranh giới chunk bằng sanitize_stream_chunks.
            def _stream_with_failover_and_record(payload, tel_meta: dict, allow_nonempty_failover: bool = False):
                nonlocal full_text_buffer, active_model, current_agent_label, model

                def _emit(mdl, mdl_name: str, agent_lbl: str):
                    nonlocal full_text_buffer
                    for chunk_text in stream_with_telemetry(
                        mdl, payload, mdl_name, agent_lbl, telemetry_meta=tel_meta
                    ):
                        full_text_buffer += chunk_text
                        yield chunk_text

                before_len = len(full_text_buffer)
                import time as _t
                last_err = None
                for retry_idx in range(2):
                    try:
                        yield from _emit(model, active_model, current_agent_label)
                        return
                    except Exception as primary_err:
                        last_err = primary_err
                        if len(full_text_buffer) == before_len and retry_idx < 1 and _is_transient_gemini_error(primary_err):
                            # Nếu lỗi 400 streaming, thử fallback gọi non-stream generate_with_telemetry
                            if "streaming response" in str(primary_err).lower():
                                try:
                                    ns_resp = generate_with_telemetry(
                                        model, payload, active_model, current_agent_label, telemetry_meta=tel_meta
                                    )
                                    ns_txt = getattr(ns_resp, "text", None) or ""
                                    if ns_txt:
                                        full_text_buffer += ns_txt
                                        yield ns_txt
                                        return
                                except Exception:
                                    pass
                            delay = 4.0 if "429" in str(primary_err).lower() else 1.5 * (retry_idx + 1)
                            _t.sleep(delay)
                            continue
                        break

                if len(full_text_buffer) == before_len or allow_nonempty_failover:
                    for fb_model in fallback_chain:
                        if not fb_model or fb_model == active_model:
                            continue
                        try:
                            push_failover_event(is_429=_is_429_exception(last_err))
                            active_model = fb_model
                            current_agent_label = "Fallback"
                            model = _build_gemini_model(active_model)
                            if meta is not None:
                                meta["model_used"] = active_model
                            yield from _emit(model, active_model, "Fallback")
                            return
                        except Exception as fb_err:
                            last_err = fb_err
                raise last_err

            emitted_clean = ""
            for safe_chunk in sanitize_stream_chunks(
                _stream_with_failover_and_record(call_payload, stream_tel_meta)
            ):
                if safe_chunk:
                    emitted_clean += safe_chunk
                    yield safe_chunk

            # Nếu stream trả về quá ngắn/cụt bất thường (ví dụ chỉ 1 chữ 'Thầy'), thử nối non-stream 1 lần
            if len(emitted_clean.strip()) < 25 and not emitted_clean.strip().endswith((".", "!", "?")):
                try:
                    cont_prompt_short = (
                        f"{prompt}\n\n[PHẦN ĐÃ VIẾT DỞ]:\n{emitted_clean}\n\n"
                        "[YÊU CẦU]: Hãy viết tiếp ngay phần câu trả lời hoàn chỉnh cho học sinh (không lặp lại chữ đã viết)."
                    )
                    cont_resp_short = generate_with_telemetry(
                        model, cont_prompt_short, active_model, current_agent_label, telemetry_meta={}
                    )
                    cont_txt_short = getattr(cont_resp_short, "text", "") or ""
                    cont_txt_short = AUDIT_REGEX.sub("", SAFETY_CONFIRM_REGEX.sub("", cont_txt_short)).replace("[COMPREHENSION_CHECK]", "").strip()
                    if cont_txt_short:
                        full_text_buffer += " " + cont_txt_short
                        yield " " + cont_txt_short
                except Exception as short_err:
                    print(f"[AI Runtime] ⚠️ Fallback stream ngắn thất bại: {short_err}")

            is_stream_max_tokens = (stream_tel_meta.get("finish_reason") == 2)
            if is_stream_max_tokens or _needs_max_tokens_continuation(full_text_buffer, check_incomplete_sentence=False):
                if is_stream_max_tokens:
                    print(f"[AI Runtime] ⚠️ Stream chạm MAX_TOKENS (finish_reason=2) trên {active_model}.")
                    if meta is not None:
                        meta["finish_reason"] = 2
                        meta["truncated"] = True
                if _needs_max_tokens_continuation(full_text_buffer, check_incomplete_sentence=is_stream_max_tokens):
                    cont_prompt = (
                        f"{prompt}\n\n"
                        f"[PHẦN ĐÃ VIẾT DỞ]:\n{full_text_buffer[-350:]}\n\n"
                        "[YÊU CẦU]: Phần trả lời trên vừa bị ngắt giữa chừng do giới hạn token. "
                        "Hãy viết TIẾP NGAY LẬP TỨC phần còn dang dở (KHÔNG lặp lại chữ đã viết) "
                        "và kết thúc trọn vẹn."
                    )
                    cont_payload = [*loaded_images, cont_prompt] if loaded_images else cont_prompt
                    cont_tel_meta: dict = {}
                    try:
                        cont_had_chunk = False
                        for cont_safe_chunk in sanitize_stream_chunks(
                            _stream_with_failover_and_record(cont_payload, cont_tel_meta)
                        ):
                            if cont_safe_chunk:
                                cont_had_chunk = True
                                yield cont_safe_chunk
                        if cont_had_chunk and meta is not None:
                            meta["continued_on_max_tokens"] = True
                    except Exception as cont_err:
                        print(f"[AI Runtime] ⚠️ Lỗi khi nối tiếp stream: {cont_err}")

            # US 10.4 & US 8.1: Trích xuất thẻ ẩn từ buffer sau khi stream xong
            stream_clean_text, stream_suggested_agent = extract_audit_tag(full_text_buffer)
            stream_clean_text, stream_safety_confirmed, stream_safety_reason = extract_safety_confirm_tag(stream_clean_text)
            if meta is not None:
                meta["suggested_agent"] = stream_suggested_agent
                if stream_safety_confirmed is not None:
                    meta["safety_confirmed"] = stream_safety_confirmed
                if stream_safety_reason:
                    meta["safety_reason"] = stream_safety_reason

            # Phát hiện comprehension sau khi stream xong (dùng text đã loại thẻ ẩn)
            cleaned = (
                stream_clean_text.replace("[COMPREHENSION_CHECK]", "")
                .replace("COMPREHENSION_CHECK", "")
                .strip()
            )
            is_comprehension_detected = _detect_comprehension(
                cleaned, full_text_buffer, clean_target_agent
            )

        except Exception as e:
            yield f" [Loi AI: {str(e)}]"
            return

        if meta is not None:
            meta["has_comprehension"] = is_comprehension_detected
            meta["inferred_emotion"] = _infer_turn_emotion(
                cleaned,
                "GUIDING",
                is_comprehension_detected,
                clean_target_agent,
                user_query,
                history_text,
                raw_text=full_text_buffer,
            )

