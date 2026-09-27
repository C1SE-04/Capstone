from typing import Optional

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
        "dùng từ ngữ thiếu tôn trọng (ê, mày, tao...) hoặc nội dung không phù hợp lứa tuổi. "
        "Nhắc nhở thái độ nếu cần, từ chối nhẹ nhàng và hướng về bài học."
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
            "• Đặt 1–2 câu hỏi ngắn để kiểm tra xem học sinh đã hiểu khái niệm nền tảng chưa.\n"
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
            "• Chỉ hỏi 1 câu hỏi tại một thời điểm, không hỏi nhiều câu cùng lúc.\n"
            "• Nếu học sinh bí hoàn toàn, thu hẹp câu hỏi xuống mức đơn giản hơn."
        ),
        "SAFETY": (
            "• NẾU học sinh dùng từ ngữ thiếu tôn trọng (ê, mày, tao, chửi thề...): BẮT BUỘC nhắc nhở cách xưng hô (gọi 'thầy', xưng 'em') một cách nghiêm túc nhưng nhẹ nhàng trước khi đáp ứng yêu cầu. TUYỆT ĐỐI KHÔNG xin lỗi.\n"
            "• NẾU là câu hỏi ngoài lề: Từ chối nhẹ nhàng, không phán xét, không giải thích dài dòng.\n"
            "• Luôn hướng học sinh trở về bài học hiện tại một cách tự nhiên.\n"
            "• Giữ tông thân thiện; nhưng nếu cần nhắc nhở thái độ thì phải kiên quyết."
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

    return f"""{_JSON_RULE}

Bạn là {agent_role} AGENT của SocraticKid — gia sư AI cho học sinh lớp 4–9 Việt Nam.
Vai trò của bạn: {role_description}
{reject_section}{problem_section}
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
• 📐 ĐỊNH DẠNG CÔNG THỨC TOÁN HỌC (LaTeX chuẩn):
  - Khi viết công thức, biến số, phân số, phương trình hoặc bất phương trình, BẮT BUỘC dùng ký hiệu LaTeX kẹp giữa dấu $:
    Ví dụ: $x \\geq 2$, $\\frac{{1}}{{2}}$, $2x + 3 = 7$, $\\sqrt{{x - 2}}$.
  - Với công thức dài hoặc đặt riêng trên một dòng, dùng $$...$$ (ví dụ: $$x \\geq 2$$).
  - TUYỆT ĐỐI KHÔNG dùng \\( ... \\) hay \\[ ... \\] dạng thô nếu không cần thiết.
  - ⚠️ JSON ESCAPE QUAN TRỌNG: Khi viết LaTeX trong JSON string, dấu \\ phải được viết là \\\\ (double backslash).
    VÍ DỤ ĐÚNG trong JSON: "draft_response": "Em thử tính $\\\\frac{{1}}{{2}}$ nhé?"
    VÍ DỤ SAI trong JSON: "draft_response": "Em thử tính $\\frac{{1}}{{2}}$ nhé?" (sẽ gây lỗi parse)

• ⚠️ NGUYÊN TẮC QUY ĐỒNG PHÂN SỐ (TOÁN LỚP 4–9):
  - BẮT BUỘC hướng dẫn học sinh tìm MẪU SỐ CHUNG NHỎ NHẤT (BCNN).
  - Nếu học sinh lấy tích hai mẫu (ví dụ: mẫu 8 và 6 học sinh chọn 8 × 6 = 48 thay vì 24):
    ❌ TUYỆT ĐỐI KHÔNG khen "hoàn toàn đúng" rồi tiếp tục hướng dẫn giải bài với mẫu 48!
    ✅ ĐÚNG: Ghi nhận nhưng gợi mở tìm BCNN:
       "Lấy 8 nhân 6 bằng 48 đúng là một mẫu chung, nhưng 48 đã là số nhỏ nhất cùng chia hết cho 8 và 6 chưa? Em thử tìm xem có số nào nhỏ hơn 48 mà cũng chia hết cho cả 8 và 6 không nhé?"


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



