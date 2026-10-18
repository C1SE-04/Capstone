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

4. PHƯƠNG PHÁP SOCRATIC:
   - Khi hướng dẫn học tập, không giải hộ hay đưa đáp án ngay. Hãy đặt câu hỏi gợi mở từng bước nhỏ để học sinh tự suy nghĩ.

5. ĐỘ DÀI:
   - Ngắn gọn, chuẩn mực, từ 2 đến 4 câu.

6. ĐÁNH GIÁ HOÀN THÀNH BÀI TOÁN (COMPREHENSION TRIGGER):
   - Khi học sinh đã trả lời ĐÚNG đáp án cuối cùng của bài toán (ví dụ: chọn đúng đáp án trắc nghiệm A/B/C/D, hoặc tính ra kết quả số cuối cùng đúng), HOẶC khi bạn vừa trình bày xong toàn bộ lời giải chi tiết cho bài toán (ở chế độ giải bài):
     -> BẮT BUỘC chèn thêm tag đặc biệt [COMPREHENSION_CHECK] vào CUỐI CÙNG của câu trả lời.
   - Khi học sinh mới trả lời một câu hỏi gợi mở trung gian, định nghĩa khái niệm, hoặc bài toán chưa giải xong:
     -> TUYỆT ĐỐI KHÔNG chèn tag [COMPREHENSION_CHECK].
"""

def load_image_from_url(url: Optional[str], timeout: float = 10.0) -> Optional[Image.Image]:
    """
    Tải ảnh từ Cloudinary HTTPS URL và chuyển thành đối tượng PIL.Image.
    Xử lý lỗi an toàn: timeout hoặc lỗi HTTP sẽ trả về None thay vì làm sập server.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return Image.open(io.BytesIO(resp.content))
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
- Trả lời ngắn gọn, chuẩn mực (2-4 câu).
- ĐÁNH GIÁ HOÀN THÀNH BÀI TOÁN (COMPREHENSION CHECK):
  + Nếu học sinh vừa trả lời ĐÚNG đáp án cuối cùng của bài toán (ví dụ: chọn đúng đáp án trắc nghiệm A/B/C/D, hoặc tính ra kết quả cuối cùng đúng), HOẶC bạn vừa hoàn thành giải thích toàn bộ bài toán cho học sinh (ở chế độ Reveal):
    -> BẮT BUỘC gắn tag [COMPREHENSION_CHECK] ở CUỐI CÙNG của câu trả lời.
  + Nếu bài toán CHƯA XONG (học sinh mới trả lời một câu hỏi phụ, định nghĩa trung gian, hoặc thực hiện một bước nhỏ):
    -> TUYỆT ĐỐI KHÔNG gắn tag [COMPREHENSION_CHECK].
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
    # Tích hợp xử lý ảnh nếu có attachment_url từ Cloudinary
    image_obj = None
    if attachment_url:
        image_obj = load_image_from_url(attachment_url)
        if image_obj:
            base_prompt += f"\n{SOCRATIC_VISION_INSTRUCTION}"
        else:
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
            call_payload = [image_obj, prompt] if image_obj is not None else prompt
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

            # 2. Cơ chế Fallback nhận diện nếu Gemini xác nhận đúng đáp án bài toán
            praise_markers = ("chính xác", "hoàn toàn đúng", "đúng rồi", "rất tốt", "xuất sắc", "chuẩn rồi", "chúc mừng em")
            is_praise = any(p in cleaned_text.lower() for p in praise_markers)
            has_conclusive_done = is_praise and (
                any(k in cleaned_text.lower() for k in ("đáp án", "kết quả", "chọn đúng", "đáp án c", "đáp án a", "đáp án b", "đáp án d"))
                or not cleaned_text.strip().endswith("?")
            )

            if has_comp_tag or has_conclusive_done:
                is_comprehension_detected = True

            # Chỉ kiểm duyệt gắt gao nếu đang đóng vai SCAFFOLDING_AGENT
            if target_agent == "SCAFFOLDING_AGENT":
                review_result = reviewer.review(user_query, expected_answer, cleaned_text)
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

