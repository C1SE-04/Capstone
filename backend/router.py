import os
import json
import google.generativeai as genai
from agents.reviewer import LocalReviewerAgent
from agents.agent_prompts import _get_grade_context
import io
from typing import Optional
import httpx
from PIL import Image

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
"""

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
    model = genai.GenerativeModel(
        model_name="gemini-3.5-flash-lite",
        system_instruction=TEACHER_SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            temperature=0.3,
            top_p=0.9,
            max_output_tokens=1024,
        )
    )
    grade_context = _get_grade_context(grade_level)
    base_prompt = f"""
    {grade_context}
Vai trò chuyên môn hiện tại: {target_agent}.
Chỉ đạo sư phạm từ Orchestrator: {task_description}

--- LỊCH SỬ TRÒ CHUYỆN ---
{history_text}

--- HỌC SINH VỪA NÓI ---
{user_query}

NHẮC LẠI NGUYÊN TẮC:
- Bạn là THẦY GIÁO, xưng "thầy" gọi "em", TUYỆT ĐỐI KHÔNG xưng "Dạ".
- Chỉ nhắc nhở thái độ khi học sinh dùng từ XÚC PHẠM THỰC SỰ (mày, tao, chửi thề) — câu ngắn, không chào hỏi, không có chủ ngữ là BÌNH THƯỜNG, không nhắc.
- Bám sát số liệu bài toán học sinh đang hỏi, không hỏi lý thuyết lan man các trường hợp không liên quan đến bài hiện tại.
- Trả lời ngắn gọn, chuẩn mực (2-4 câu).
- ĐÁNH GIÁ HOÀN THÀNH BÀI TOÁN (COMPREHENSION CHECK):
  + Nếu học sinh vừa trả lời ĐÚNG đáp án cuối cùng của bài toán (ví dụ: chọn đúng đáp án trắc nghiệm A/B/C/D, hoặc tính ra kết quả cuối cùng đúng), HOẶC bạn vừa hoàn thành giải thích toàn bộ bài toán cho học sinh (ở chế độ Reveal):
    -> BẮT BUỘC gắn tag [COMPREHENSION_CHECK] ở CUỐI CÙNG của câu trả lời.
  + Nếu bài toán CHƯA XONG (học sinh mới trả lời một câu hỏi phụ, định nghĩa trung gian, hoặc bạn vẫn đang tiếp tục đặt câu hỏi cho học sinh):
    -> TUYỆT ĐỐI KHÔNG gắn tag [COMPREHENSION_CHECK].
- FACT-CHECK TOÁN HỌC: Bắt buộc nhẩm lại các bước tính của học sinh trước khi phản hồi. Tuyệt đối không khen 'hoàn toàn đúng', 'chính xác' nếu kết quả sai (như x = 2 cho phương trình 2x + 3 = 5).
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

    reviewer = LocalReviewerAgent()
    max_retries = 2
    current_attempt = 0
    final_text = ""
    prompt = base_prompt
    is_comprehension_detected = False

    while current_attempt <= max_retries:
        print("=== PROMPT CHUẨN BỊ GỬI AI ===")
        print(prompt)
        print("================================")
        
        try:
            # Lấy toàn bộ văn bản để Reviewer có thể đánh giá (không stream trực tiếp)
            call_payload = [*loaded_images, prompt] if loaded_images else prompt
            response = model.generate_content(call_payload, stream=False)
            generated_text = response.text or ""
            
            # 1. Bóc tách tag [COMPREHENSION_CHECK] do Gemini phát hiện
            has_comp_tag = (
                "[COMPREHENSION_CHECK]" in generated_text
                or "COMPREHENSION_CHECK" in generated_text
            )
            cleaned_text = (
                generated_text.replace("[COMPREHENSION_CHECK]", "")
                .replace("COMPREHENSION_CHECK", "")
                .strip()
            )

            # 2. Cơ chế nhận diện hoàn thành bài toán (Comprehension Trigger)
            # Kiểm tra xem câu trả lời có đang kết thúc bằng một câu hỏi gợi mở tiếp theo hay không.
            # Nếu câu kết thúc bằng dấu '?', AI vẫn đang hỏi dở học sinh -> TUYỆT ĐỐI KHÔNG kích hoạt comprehension check!
            ends_with_question = cleaned_text.strip().rstrip("*_~` \t\r\n").endswith("?")

            # TUYỆT ĐỐI KHÔNG kích hoạt comprehension check khi:
            # - Đang phân luồng MISCONCEPTION hoặc SAFETY (học sinh đang hiểu sai hoặc vi phạm ngoài lề)
            # - Hoặc câu trả lời kết thúc bằng câu hỏi '?'
            is_misconception_or_safety = target_agent in (
                "MISCONCEPTION_AGENT", "SAFETY_AGENT", "MISCONCEPTION", "SAFETY"
            )

            praise_markers = ("chính xác", "hoàn toàn đúng", "đúng rồi", "rất tốt", "xuất sắc", "chuẩn rồi", "chúc mừng em", "khen ngợi", "rất giỏi")
            is_praise = any(p in cleaned_text.lower() for p in praise_markers)
            conclusive_keywords = ("đáp án", "kết quả", "chọn đúng", "đáp án a", "đáp án b", "đáp án c", "đáp án d", "nghiệm của phương trình", "nghiệm là", "vô nghiệm")
            has_conclusive_markers = any(k in cleaned_text.lower() for k in conclusive_keywords)

            # Chỉ kích hoạt khi bài toán đã kết luận, KHÔNG ở mode sửa sai/safety và KHÔNG kết thúc bằng câu hỏi gợi mở
            attempt_has_comprehension = False
            if not ends_with_question and not is_misconception_or_safety:
                if has_comp_tag or (is_praise and has_conclusive_markers):
                    attempt_has_comprehension = True

            # Kiểm duyệt gắt gao với cả SCAFFOLDING_AGENT và MISCONCEPTION_AGENT
            if target_agent in ("SCAFFOLDING_AGENT", "MISCONCEPTION_AGENT"):
                review_result = reviewer.review(
                    user_query,
                    expected_answer,
                    cleaned_text,
                    has_comprehension=attempt_has_comprehension,
                )
                if not review_result["is_approved"]:
                    current_attempt += 1
                    print(f"[Reviewer Agent 🛑] Từ chối (Lần {current_attempt}/{max_retries}): {review_result['feedback']}")
                    print(f"[Reviewer Agent 🛑] Lý do: {review_result['reasoning']}")
                    
                    # Nạp lại lời mắng vào prompt để ép AI phải sửa lỗi
                    prompt += f"\n\n[HỆ THỐNG KIỂM DUYỆT CẢNH BÁO]: Câu trả lời vừa rồi của bạn bị TỪ CHỐI vì lý do: {review_result['feedback']}. \nHãy sinh lại câu trả lời khác và TUYỆT ĐỐI KHÔNG vi phạm lỗi này nữa."
                    final_text = cleaned_text  # Backup lỡ như hết số lần thử vẫn ngu
                    continue
            
            # Nếu pass qua được Reviewer hoặc không phải Scaffolding thì chốt đáp án
            final_text = cleaned_text
            is_comprehension_detected = attempt_has_comprehension
            break
            
        except Exception as e:
            yield f" [Lỗi khi gọi AI: {str(e)}]"
            return

    # Lưu kết quả phát hiện comprehension vào meta object
    if meta is not None:
        meta["has_comprehension"] = is_comprehension_detected

    # Sau khi chốt được văn bản xịn, chẻ nhỏ ra để giả lập luồng Stream trả về Frontend cho mượt
    words = final_text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")

