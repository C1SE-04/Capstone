import os
import re
import json
import google.generativeai as genai
from agents.reviewer import LocalReviewerAgent
from agents.agent_prompts import _get_grade_context
import io
from typing import Optional
import httpx
from PIL import Image

# US 10.2 (T10.2.2): Import telemetry wrappers để thu thập token và TTFT
from middleware.gemini_telemetry import stream_with_telemetry, generate_with_telemetry, _is_429_exception
from middleware.telemetry_middleware import push_failover_event

# Tên model đang dùng thực tế — đồng bộ với bảng giá trong gemini_telemetry.py
_ACTIVE_MODEL_NAME = "gemini-3.5-flash-lite"

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

4. PHƯƠNG PHÁP SOCRATIC & BÁM SÁT BÀI TOÁN:
   - Khi hướng dẫn học tập, không giải hộ hay đưa đáp án ngay. Hãy đặt câu hỏi gợi mở từng bước nhỏ để học sinh tự suy nghĩ.
   - BÁM SÁT ĐỀ BÀI CỤ THỂ: Hướng dẫn học sinh thao tác trên chính số liệu và dữ kiện của BÀI TOÁN ĐANG HỎI. TUYỆT ĐỐI KHÔNG đi lan man khảo sát lý thuyết toàn diện ngoài lề (ví dụ: bài toán có delta cụ thể thì hướng dẫn tính delta của bài đó, không bắt học sinh khảo sát các trường hợp lý thuyết delta > 0, = 0, < 0).
   - Nếu học sinh nói không có máy tính hoặc tính nhẩm khó: Hãy hướng dẫn học sinh đặt phép tính số học đơn giản dựa trên hệ số của bài để tự tính nhẩm từng bước.

5. ĐỘ DÀI:
   - Ngắn gọn, chuẩn mực, từ 2 đến 4 câu.

6. ĐÁNH GIÁ HOÀN THÀNH BÀI TOÁN (COMPREHENSION TRIGGER):
   - Khi học sinh đã trả lời ĐÚNG đáp án cuối cùng của bài toán (ví dụ: chọn đúng đáp án trắc nghiệm A/B/C/D, hoặc tính ra kết quả số cuối cùng đúng), HOẶC khi bạn vừa trình bày xong toàn bộ lời giải chi tiết cho bài toán (ở chế độ giải bài):
     -> BẮT BUỘC chèn thêm tag đặc biệt [COMPREHENSION_CHECK] vào CUỐI CÙNG của câu trả lời.
   - Khi học sinh mới trả lời một câu hỏi gợi mở trung gian, định nghĩa khái niệm, hoặc bài toán chưa giải xong, hoặc bạn vẫn đang đặt câu hỏi tiếp theo cho học sinh:
     -> TUYỆT ĐỐI KHÔNG chèn tag [COMPREHENSION_CHECK].

7. KIỂM TRA TÍNH ĐÚNG ĐẮN TOÁN HỌC (FACT-CHECK BẮT BUỘC):
   - Trước khi công nhận học sinh đúng, BẮT BUỘC phải tự kiểm tra lại các bước tính và nghiệm của bài toán.
   - TUYỆT ĐỐI KHÔNG khen 'hoàn toàn đúng', 'chính xác', 'chuẩn rồi' nếu học sinh tính sai kết quả (ví dụ: phương trình 2x + 3 = 5 mà học sinh bảo x = 2 là SAI, nghiệm đúng phải là x = 1).
   - Nếu học sinh mới làm đúng một phần (ví dụ chuyển vế đúng) nhưng kết luận sai nghiệm: Hãy khen bước làm đúng, nhưng chỉ rõ nghiệm cuối chưa đúng và yêu cầu học sinh làm lại bước cuối.
   - TUYỆT ĐỐI KHÔNG gắn thẻ [COMPREHENSION_CHECK] khi học sinh chưa tìm ra nghiệm đúng.

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
     * Nếu học sinh chỉ cần hướng dẫn từng bước bình thường nhưng bị gán nhầm sang SAFETY hoặc MISCONCEPTION -> Đính kèm ở DÒNG CUỐI CÙNG: <!-- AUDIT_AGENT: SCAFFOLDING -->
   - NGUYÊN TẮC BẤT DI BẤT DỊCH CỦA THẺ ẨN (CHỐNG BẮT SAI & FALSE POSITIVE):
     * Nếu phân luồng đã CHUẨN XÁC: TUYỆT ĐỐI KHÔNG đính kèm bất kỳ thẻ ẩn nào.
     * TUYỆT ĐỐI KHÔNG gắn thẻ trùng với vai trò hiện tại (ví dụ: nếu vai trò hiện tại đã là SCAFFOLDING thì tuyệt đối không gắn thẻ SCAFFOLDING).
     * BẢO VỆ CÂU TRẢ LỜI NGẮN TRONG HỘI THOẠI: Khi học sinh trả lời ngắn gọn (như 'dạ', 'vâng', 'là 6', 'bằng 3', 'em chưa hiểu', 'tiếp theo làm gì') để đáp lại câu hỏi của Thầy: Đây là sự tiếp nối hoàn toàn tự nhiên của vai trò SCAFFOLDING, TUYỆT ĐỐI KHÔNG coi là sai lệch và TUYỆT ĐỐI KHÔNG gắn thẻ ẩn!
     * DANH MỤC AGENT HỢP LỆ DUY NHẤT: Bắt buộc chỉ được chọn 1 trong 4 nhãn chính xác: MISCONCEPTION, KNOWLEDGE_TRACING, SAFETY, SCAFFOLDING. Tuyệt đối không tự sáng tạo tên nhãn khác (như MATH, TUTOR, FOLLOWUP...).
     * Thẻ ẩn BẮT BUỘC phải đặt ở dòng cuối cùng riêng biệt của câu trả lời, cú pháp chính xác: <!-- AUDIT_AGENT: <AGENT_NAME> -->
     * TUYỆT ĐỐI KHÔNG giải thích lý do hay bình luận gì thêm cạnh thẻ ẩn (để tiết kiệm token và giữ tốc độ streaming).
"""

# ==============================================================================
# US 10.4 (Task T10.4.2): GIAO THỨC BÓC TÁCH THẺ ẨN (HIDDEN TAG PARSER)
# ==============================================================================
AUDIT_REGEX = re.compile(r"<!--\s*AUDIT_AGENT\s*:\s*([A-Z_]+)\s*-->", re.IGNORECASE)
VALID_AUDIT_AGENTS = {"MISCONCEPTION", "KNOWLEDGE_TRACING", "SAFETY", "SCAFFOLDING"}

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


def sanitize_stream_chunks(chunk_iterator):
    """
    US 10.4: Bộ lọc chống rò rỉ thẻ ẩn và tag comprehension khi streaming.
    Sử dụng kỹ thuật Lookahead Holding Buffer để ngăn chặn việc các thẻ bị cắt đôi/cắt ba
    giữa các chunk (Chunk Boundary Fragmentation) hiển thị lên màn hình học sinh ([AC-AL-01]).
    """
    buffer = ""
    for chunk in chunk_iterator:
        buffer += chunk
        
        # Liên tục loại bỏ các tag hoàn chỉnh đã xuất hiện trong buffer
        buffer = AUDIT_REGEX.sub("", buffer)
        buffer = buffer.replace("[COMPREHENSION_CHECK]", "").replace("COMPREHENSION_CHECK", "")
        
        # Kiểm tra xem cuối buffer có dấu hiệu mở thẻ chưa đóng không:
        # Thẻ ẩn: bắt đầu bằng '<' (tối đa ~55 ký tự)
        # Thẻ comp: bắt đầu bằng '[' (tối đa ~25 ký tự)
        last_lt = buffer.rfind("<")
        last_lb = buffer.rfind("[")
        
        hold_pos = len(buffer)
        if last_lt != -1 and (len(buffer) - last_lt) <= 55:
            hold_pos = min(hold_pos, last_lt)
        if last_lb != -1 and (len(buffer) - last_lb) <= 25:
            hold_pos = min(hold_pos, last_lb)
            
        safe_to_yield = buffer[:hold_pos]
        buffer = buffer[hold_pos:]
        
        if safe_to_yield:
            yield safe_to_yield
            
    # Khi stream kết thúc, xử lý và xả nốt phần buffer còn lại
    if buffer:
        final_clean = AUDIT_REGEX.sub("", buffer)
        final_clean = final_clean.replace("[COMPREHENSION_CHECK]", "").replace("COMPREHENSION_CHECK", "").strip()
        if final_clean:
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
        
    genai.configure(api_key=api_key)

    # US 10.3 (Task T10.3.3): Đọc cấu hình động từ SystemConfigService (Redis Cache -> Neon DB)
    active_model = _ACTIVE_MODEL_NAME
    backup_model = os.getenv("GEMINI_BACKUP_MODEL", "gemini-3.5-flash-lite")
    active_temperature = 0.35
    active_top_p = 0.90
    active_max_tokens = 512
    try:
        from services.system_config_service import get_system_settings
        sys_config = get_system_settings()
        active_model = sys_config.get("primary_model") or os.getenv("GEMINI_CHAT_MODEL") or _ACTIVE_MODEL_NAME
        backup_model = sys_config.get("backup_model") or os.getenv("GEMINI_BACKUP_MODEL", "gemini-3.5-flash-lite")
        active_temperature = float(sys_config.get("temperature", 0.35))
        active_top_p = float(sys_config.get("top_p", 0.90))
        active_max_tokens = int(sys_config.get("max_output_tokens", 512))
    except Exception as err:
        print(f"[Router] Cảnh báo đọc SystemConfig: {err} — Dùng fallback.")
        active_model = os.getenv("GEMINI_CHAT_MODEL") or _ACTIVE_MODEL_NAME

    if meta is not None:
        meta["model_used"] = active_model

    def _build_gemini_model(model_name_str: str):
        return genai.GenerativeModel(
            model_name=model_name_str,
            system_instruction=TEACHER_SYSTEM_INSTRUCTION,
            generation_config=genai.GenerationConfig(
                temperature=active_temperature,
                top_p=active_top_p,
                max_output_tokens=active_max_tokens,
            )
        )

    model = _build_gemini_model(active_model)
    current_agent_label = "Chat"
    # US 10.4: Chuẩn hóa tên Agent để đối chiếu chuẩn xác với 4 nhãn cốt lõi
    clean_target_agent = target_agent.replace("_AGENT", "").strip().upper()

    grade_context = _get_grade_context(grade_level)
    base_prompt = f"""
    {grade_context}
Vai trò chuyên môn hiện tại: {clean_target_agent}.
Chỉ đạo sư phạm từ Orchestrator: {task_description}

--- LỊCH SỬ TRÒ CHUYỆN ---
{history_text}

--- HỌC SINH VỪA NÓI ---
{user_query}

--- QUY TẮC PHẢN HỒI 2 TẦNG (US 10.4 ACTIVE LEARNING) ---
1. TẦNG SƯ PHẠM (GỬI HỌC SINH):
   - Bạn là THẦY GIÁO, xưng "thầy" gọi "em", TUYỆT ĐỐI KHÔNG xưng "Dạ".
   - Giảng giải Socratic gợi mở, bám sát số liệu bài toán học sinh đang hỏi, trả lời ngắn gọn (2-4 câu).
   - TUYỆT ĐỐI KHÔNG nhắc đến các thuật ngữ kỹ thuật: 'Orchestrator', 'Routing', 'Agent', 'target_agent', 'Scaffolding', 'Misconception' trong lời thoại gửi học sinh.
2. TẦNG THẨM ĐỊNH NGẦM (GIAO THỨC THẺ ẨN AUDIT_AGENT):
   - Quan sát câu nói vừa rồi của học sinh: '{user_query}'.
   - Đối chiếu với vai trò chuyên môn hiện tại: '{clean_target_agent}'.
   - Nếu bạn phát hiện phân luồng SAI:
     * Học sinh hiểu sai kiến thức/ngộ nhận toán học nhưng vai trò là SCAFFOLDING -> Đính kèm ở dòng CUỐI CÙNG: <!-- AUDIT_AGENT: MISCONCEPTION -->
     * Học sinh hỏi khái niệm/định nghĩa lý thuyết nhưng vai trò là SCAFFOLDING -> Đính kèm ở dòng CUỐI CÙNG: <!-- AUDIT_AGENT: KNOWLEDGE_TRACING -->
     * Học sinh vi phạm thái độ, xưng hô mày tao, chửi thề nhưng vai trò là học tập -> Đính kèm ở dòng CUỐI CÙNG: <!-- AUDIT_AGENT: SAFETY -->
     * Học sinh học tập bình thường nhưng vai trò là MISCONCEPTION/SAFETY -> Đính kèm ở dòng CUỐI CÙNG: <!-- AUDIT_AGENT: SCAFFOLDING -->
   - NGUYÊN TẮC CHỐNG BẮT SAI & FALSE POSITIVE:
     * Nếu phân luồng ĐÃ CHUẨN XÁC: TUYỆT ĐỐI KHÔNG gắn thẻ này!
     * TUYỆT ĐỐI KHÔNG gắn thẻ trùng với vai trò hiện tại (ví dụ: vai trò là '{clean_target_agent}' thì không được gắn <!-- AUDIT_AGENT: {clean_target_agent} -->).
     * BẢO VỆ CÂU TRẢ LỜI NGẮN: Khi học sinh đáp lời ngắn gọn (như 'dạ', 'vâng', 'là 6', 'bằng 3', 'em chưa hiểu', 'tiếp theo làm gì'): Đây là sự tiếp nối hoàn toàn bình thường của SCAFFOLDING, TUYỆT ĐỐI KHÔNG gắn thẻ ẩn!
     * DANH MỤC HỢP LỆ DUY NHẤT: Chỉ chọn 1 trong 4 nhãn (MISCONCEPTION, KNOWLEDGE_TRACING, SAFETY, SCAFFOLDING).
- ĐÁNH GIÁ HOÀN THÀNH BÀI TOÁN (COMPREHENSION CHECK):
  + Nếu học sinh vừa trả lời ĐÚNG đáp án cuối cùng của bài toán: BẮT BUỘC gắn tag [COMPREHENSION_CHECK] ngay sau câu kết luận (trước thẻ AUDIT_AGENT nếu có).
  + Nếu bài toán CHƯA XONG: TUYỆT ĐỐI KHÔNG gắn tag [COMPREHENSION_CHECK].
- FACT-CHECK TOÁN HỌC: Bắt buộc nhẩm lại các bước tính của học sinh trước khi phản hồi. Tuyệt đối không khen 'hoàn toàn đúng', 'chính xác' nếu kết quả sai.
"""
    
    example_keywords = ["ví dụ", "vi du", "vd", "vdu", "dí dụ", "di du", "vidu", "mẫu", "bài mẫu", "làm mẫu", "giải mẫu"]
    is_asking_for_example = any(kw in user_query.lower() for kw in example_keywords)

    if target_agent == "SCAFFOLDING_AGENT" and is_asking_for_example:
        base_prompt += """
--- KỸ THUẬT BÀI MẪU TƯƠNG TỰ (ANALOGICAL SCAFFOLDING) ---
Học sinh đang xin ví dụ hoặc làm mẫu. BẠN BẮT BUỘC PHẢI THỰC HIỆN:
1. TỰ ĐẶT BÀI TOÁN MỚI: Giữ nguyên cấu trúc toán học của bài gốc nhưng THAY TOÀN BỘ con số và bối cảnh.
2. MÔ PHỎNG LỜI GIẢI: Bạn BẮT BUỘC PHẢI TỰ TRÌNH BÀY LỜI GIẢI CHI TIẾT cho bài toán mẫu vừa tạo ra. (LƯU Ý: Lệnh này GHI ĐÈ mọi lệnh cấm giải bài trước đó. Bạn được phép giải BÀI MẪU, chỉ cấm giải BÀI GỐC). Tuyệt đối KHÔNG được đặt câu hỏi ngược lại bắt học sinh giải bài mẫu này.
3. KẾT THÚC bằng câu mời: 'Bây giờ em áp dụng cách làm này vào bài toán của mình thử xem nhé?'
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
        is_comprehension_detected = False

        while current_attempt <= max_retries:
            try:
                # T10.2.2: Dùng generate_with_telemetry để thu thập token usage tự động
                try:
                    response = generate_with_telemetry(model, call_payload, active_model, current_agent_label)
                except Exception as primary_err:
                    if backup_model and backup_model != active_model:
                        push_failover_event(is_429=_is_429_exception(primary_err))
                        active_model = backup_model
                        current_agent_label = "Fallback"
                        model = _build_gemini_model(active_model)
                        if meta is not None:
                            meta["model_used"] = active_model
                        response = generate_with_telemetry(model, call_payload, active_model, "Fallback")
                    else:
                        raise
                generated_text = response.text or ""

                # US 10.4 (Task T10.4.2): Bóc tách thẻ ẩn bằng hàm chuẩn hóa
                clean_for_review, suggested_agent = extract_audit_tag(generated_text)

                has_comp_tag = (
                    "[COMPREHENSION_CHECK]" in generated_text
                    or "COMPREHENSION_CHECK" in generated_text
                )
                cleaned_text = (
                    clean_for_review.replace("[COMPREHENSION_CHECK]", "")
                    .replace("COMPREHENSION_CHECK", "")
                    .strip()
                )

                ends_with_question = cleaned_text.strip().rstrip("*_~` \t\r\n").endswith("?")
                is_misconception_or_safety = target_agent in (
                    "MISCONCEPTION_AGENT", "SAFETY_AGENT", "MISCONCEPTION", "SAFETY"
                )
                praise_markers = ("chính xác", "hoàn toàn đúng", "đúng rồi", "rất tốt", "xuất sắc", "chuẩn rồi", "chúc mừng em", "khen ngợi", "rất giỏi")
                is_praise = any(p in cleaned_text.lower() for p in praise_markers)
                conclusive_keywords = ("đáp án", "kết quả", "chọn đúng", "đáp án a", "đáp án b", "đáp án c", "đáp án d", "nghiệm của phương trình", "nghiệm là", "vô nghiệm")
                has_conclusive_markers = any(k in cleaned_text.lower() for k in conclusive_keywords)

                attempt_has_comprehension = False
                if not ends_with_question and not is_misconception_or_safety:
                    if has_comp_tag or (is_praise and has_conclusive_markers):
                        attempt_has_comprehension = True

                review_result = reviewer.review(
                    user_query,
                    expected_answer,
                    cleaned_text,
                    has_comprehension=attempt_has_comprehension,
                )
                if not review_result["is_approved"]:
                    current_attempt += 1
                    print(f"[Reviewer] Tu choi lan {current_attempt}: {review_result['feedback']}")
                    call_payload = (
                        [*loaded_images, prompt + f"\n\n[CANH BAO]: Phan hoi bi tu choi vi: {review_result['feedback']}. Hay sinh lai."]
                        if loaded_images
                        else prompt + f"\n\n[CANH BAO]: Phan hoi bi tu choi vi: {review_result['feedback']}. Hay sinh lai."
                    )
                    final_text = cleaned_text
                    continue

                # Lưu nhãn đề xuất vào meta để bên ngoài orchestrator_bridge ghi DB
                if meta is not None:
                    meta["suggested_agent"] = suggested_agent

                # Stream văn bản ĐÃ LÀM SẠCH HOÀN TOÀN ra ngoài (không kèm thẻ ẩn)
                final_text = cleaned_text
                is_comprehension_detected = attempt_has_comprehension
                break

            except Exception as e:
                yield f" [Loi AI: {str(e)}]"
                return

        if meta is not None:
            meta["has_comprehension"] = is_comprehension_detected
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
            # T10.2.2 + T10.4.2: Stream qua telemetry, tự động failover sang backup_model khi lỗi trước chunk đầu,
            # đồng thời lọc thẻ ẩn/comprehension an toàn qua ranh giới chunk bằng sanitize_stream_chunks.
            def _stream_with_failover_and_record():
                nonlocal full_text_buffer, active_model, current_agent_label, model

                def _emit(mdl, mdl_name: str, agent_lbl: str):
                    nonlocal full_text_buffer
                    for chunk_text in stream_with_telemetry(mdl, call_payload, mdl_name, agent_lbl):
                        full_text_buffer += chunk_text
                        yield chunk_text

                try:
                    yield from _emit(model, active_model, current_agent_label)
                except Exception as primary_err:
                    if not full_text_buffer and backup_model and backup_model != active_model:
                        push_failover_event(is_429=_is_429_exception(primary_err))
                        active_model = backup_model
                        current_agent_label = "Fallback"
                        model = _build_gemini_model(active_model)
                        if meta is not None:
                            meta["model_used"] = active_model
                        yield from _emit(model, active_model, "Fallback")
                    else:
                        raise

            for safe_chunk in sanitize_stream_chunks(_stream_with_failover_and_record()):
                if safe_chunk:
                    yield safe_chunk

            # US 10.4 (Task T10.4.2): Trích xuất thẻ ẩn từ buffer sau khi stream xong
            stream_clean_text, stream_suggested_agent = extract_audit_tag(full_text_buffer)
            if meta is not None:
                meta["suggested_agent"] = stream_suggested_agent

            # Phát hiện comprehension sau khi stream xong (dùng text đã loại thẻ ẩn)
            cleaned = (
                stream_clean_text.replace("[COMPREHENSION_CHECK]", "")
                .replace("COMPREHENSION_CHECK", "")
                .strip()
            )
            has_comp_tag = (
                "[COMPREHENSION_CHECK]" in full_text_buffer
                or "COMPREHENSION_CHECK" in full_text_buffer
            )
            ends_with_question = cleaned.strip().rstrip("*_~` \t\r\n").endswith("?")
            is_misconception_or_safety = target_agent in (
                "MISCONCEPTION_AGENT", "SAFETY_AGENT", "MISCONCEPTION", "SAFETY"
            )
            praise_markers = ("chính xác", "hoàn toàn đúng", "đúng rồi", "rất tốt", "xuất sắc", "chuẩn rồi", "chúc mừng em", "khen ngợi", "rất giỏi")
            is_praise = any(p in cleaned.lower() for p in praise_markers)
            conclusive_keywords = ("đáp án", "kết quả", "chọn đúng", "đáp án a", "đáp án b", "đáp án c", "đáp án d", "nghiệm của phương trình", "nghiệm là", "vô nghiệm")
            has_conclusive_markers = any(k in cleaned.lower() for k in conclusive_keywords)

            if not ends_with_question and not is_misconception_or_safety:
                if has_comp_tag or (is_praise and has_conclusive_markers):
                    is_comprehension_detected = True

        except Exception as e:
            yield f" [Loi AI: {str(e)}]"
            return

        if meta is not None:
            meta["has_comprehension"] = is_comprehension_detected

