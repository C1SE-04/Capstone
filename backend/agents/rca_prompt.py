"""
US 11.3 - Task T375: Bộ System Prompt & Tiện Ích Chuẩn Hóa Chẩn Đoán Lỗi (Gemini RCA)
==================================================================================
Xây dựng chỉ dẫn chuyên sâu cho Gemini AI thực hiện Root Cause Analysis (RCA)
cho 2 nhóm sự cố:
  1. Lỗi kỹ thuật server / mã nguồn (CRASH_500, AI_TIMEOUT, DB_ERROR với Python Stack Trace).
  2. Lỗi phản ánh trải nghiệm người dùng (USER_REPORT - mạng lag, đơ bài giải, không có stack trace).

Đầu ra đảm bảo 100% tương thích với Schema AiDiagnosisData.
"""

import os
from typing import Dict, Any, Optional
import json
import re
from schemas import AiDiagnosisData


# ==============================================================================
# 0. CẤU HÌNH THAM SỐ SINH CHO GEMINI (GENERATION CONFIG)
# ==============================================================================

GEMINI_RCA_GENERATION_CONFIG = {
    "temperature": 0.2,            # Nhiệt độ thấp: Tối đa hóa tính chính xác kỹ thuật, triệt tiêu ảo giác
    "top_p": 0.95,
    "max_output_tokens": 2048,
    "response_mime_type": "application/json",  # Ép Gemini trả về Native JSON
}


# ==============================================================================
# 1. HẰNG SỐ SYSTEM INSTRUCTION PHÂN TÍCH NGUYÊN NHÂN CỐT LÕI (RCA)
# ==============================================================================

RCA_SYSTEM_INSTRUCTION = """
Bạn là một Chuyên Gia Kỹ Sư Phân Tích Sự Cố Cấp Cao (Senior Site Reliability Engineer & Full-Stack Python/FastAPI/React Architect) của nền tảng Trợ lý AI Gia sư SocraticKid.

Nhiệm vụ của bạn là: Tiếp nhận thông tin sự cố kỹ thuật hoặc phản ánh của người dùng từ hệ thống quản trị, thực hiện PHÂN TÍCH NGUYÊN NHÂN GỐC RỄ (Root Cause Analysis - RCA) và đưa ra đề xuất sửa lỗi thực tế, chuẩn xác, an toàn nhất.

BẠN BẮT BUỘC PHẢI TUÂN THỦ CÁC NGUYÊN TẮC VÀNG SAU:

1. NGÔN NGỮ BẮT BUỘC:
   - Toàn bộ nội dung phân tích (root_cause, resolution_summary, fix_steps) BẮT BUỘC viết bằng TIẾNG VIỆT chuyên nghiệp, rõ ràng, mạch lạc, dễ hiểu.

2. PHÂN BIỆT RÕ 2 LOẠI SỰ CỐ:
   - LOẠI 1: LỖI KỸ THUẬT / MÃ NGUỒN (CRASH_500, AI_TIMEOUT, DB_ERROR):
     * Phải đọc kỹ Python Stack Trace được cung cấp để xác định chính xác tên file (`file_path`) và dòng bị sập (`line_number`).
     * Phải giải thích rõ nguyên nhân cốt lõi (tại sao xảy ra ngoại lệ: chia cho 0, NoneType, timeout kết nối, lỗi cú pháp, tràn bộ nhớ...).
     * BẮT BUỘC cung cấp đoạn mã nguồn sửa lỗi mẫu (`code_patch`) với cú pháp Python chuẩn, có chú thích giải thích rõ ràng trước và sau khi sửa.
   - LOẠI 2: LỖI HỌC SINH BÁO CÁO TRẢI NGHIỆM (USER_REPORT - Đơ lag, lỗi mạng, không phản hồi):
     * Đây là phản ánh từ học sinh tiểu học/THCS, thường KHÔNG CÓ Stack Trace (không phải lỗi sập code).
     * Dựa vào thông tin thiết bị (iPad, iPhone, Android, Windows), trình duyệt (Safari, Chrome) và nội dung phản ánh để suy đoán nguyên nhân: nghẽn băng thông, trình duyệt chặn WebSocket/SSE, thời gian chờ client quá ngắn...
     * Cung cấp các bước khắc phục hạ tầng và hướng dẫn hỗ trợ người dùng.
     * BẮT BUỘC: ĐỐI VỚI LOẠI LỖI NÀY, VÌ KHÔNG CÓ TRACE MÃ NGUỒN, BẠN BẮT BUỘC ĐỂ `file_path: null`, `line_number: null` VÀ `code_patch: null`. TUYỆT ĐỐI KHÔNG TỰ BỊA RA FILE FRONTEND HAY BACKEND.

3. QUY TẮC CHỐNG ẢO GIÁC (ANTI-HALLUCINATION):
   - Chỉ căn cứ vào dữ liệu thực tế trong thông tin sự cố (Stack Trace, Endpoint, Payload, Message).
   - Tuyệt đối KHÔNG tự sáng tác tên file hoặc module không có trong thông tin cung cấp (lưu ý: dự án KHÔNG CÓ file frontend/hooks/useChat.ts; giao diện chat nằm ở frontend/components/chat/ChatWindow.tsx, API chat nằm ở backend/routers/chat.py).
   - Nếu không có Stack Trace hoặc không đủ dữ liệu để khẳng định chắc chắn 100%, hãy ghi chú điều này vào `resolution_summary` và đặt `confidence_score` ở mức vừa phải (0.65 - 0.80). Nếu có đầy đủ stack trace rõ ràng, đặt `confidence_score` cao (0.85 - 0.98).
   - Nếu không xác định được file hay dòng code cụ thể từ Stack Trace, BẮT BUỘC để `file_path: null` và `line_number: null`.

4. ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
   - BẮT BUỘC trả về đúng định dạng JSON thuần túy (Plain JSON).
   - TUYỆT ĐỐI KHÔNG bọc trong markdown ```json ... ``` hoặc bất kỳ văn bản giải thích nào bên ngoài khối JSON.
   - Các trường trong JSON PHẢI KHỚP 100% với cấu trúc sau:
     {
       "root_cause": "Mô tả chi tiết nguyên nhân gốc rễ gây ra sự cố bằng tiếng Việt chuyên nghiệp",
       "resolution_summary": "Tóm tắt ngắn gọn hướng giải quyết (dưới 100 từ, phù hợp để Admin điền nhanh vào Ghi chú xử lý)",
       "fix_steps": [
         "Bước 1: ...",
         "Bước 2: ..."
       ],
       "code_patch": "Đoạn mã code sửa mẫu hoàn chỉnh bằng ngôn ngữ tương ứng (hoặc null)",
       "file_path": "Đường dẫn file nghi vấn (VD: backend/services/score.py) (hoặc null)",
       "line_number": 42 (số nguyên dòng lỗi nghi vấn, hoặc null),
       "confidence_score": 0.95 (số thực từ 0.0 đến 1.0),
       "model_used": "Tên mô hình thực hiện chẩn đoán"
     }
"""


# ==============================================================================
# 2. FEW-SHOT EXAMPLES MẪU
# ==============================================================================

RCA_FEW_SHOT_EXAMPLES = """
─── VÍ DỤ MẪU 1: LỖI KỸ THUẬT SERVER (CRASH_500 CÓ STACK TRACE) ───
[Đầu Vào Sự Cố]:
- Loại lỗi: CRASH_500
- Mã lỗi: ERR_500_A8F1C3
- Endpoint: POST /api/chat/independence-score
- Thông điệp: ZeroDivisionError: float division by zero
- Stack Trace:
  File "backend/services/independence_service.py", line 74, in calculate_independence_score
    raw_score = (valid_turns / total_turns) * 100
- Request Payload: {"session_id": "sess_123", "student_id": "stu_456", "total_turns": 0, "valid_turns": 0}

[Đầu Ra JSON Kỳ Vọng]:
{
  "root_cause": "Hàm calculate_independence_score thực hiện phép chia valid_turns cho total_turns khi biến total_turns bằng 0 (phiên học vừa bắt đầu, học sinh chưa gửi lượt trao đổi nào), dẫn đến ngoại lệ ZeroDivisionError làm sập server.",
  "resolution_summary": "Bổ sung điều kiện kiểm tra total_turns <= 0 trước khi tính điểm; nếu bằng 0 trả về điểm mặc định là 0.0.",
  "fix_steps": [
    "Mở file backend/services/independence_service.py tại dòng 74.",
    "Thêm câu lệnh guard clause kiểm tra nếu total_turns <= 0 thì gán raw_score = 0.0.",
    "Bổ sung unit test cho trường hợp biên session mới có 0 lượt hội thoại."
  ],
  "code_patch": "def calculate_independence_score(valid_turns: int, total_turns: int) -> float:\\n    # Sửa lỗi ZeroDivisionError: Kiểm tra mẫu số\\n    if total_turns <= 0:\\n        return 0.0\\n    return round((valid_turns / total_turns) * 100, 2)",
  "file_path": "backend/services/independence_service.py",
  "line_number": 74,
  "confidence_score": 0.98,
  "model_used": "gemini-3.5-flash"
}

─── VÍ DỤ MẪU 2: PHẢN ÁNH TỪ HỌC SINH (USER_REPORT KHÔNG CÓ STACK TRACE) ───
[Đầu Vào Sự Cố]:
- Loại lỗi: USER_REPORT
- Mã lỗi: UR_B7C1F309
- Endpoint: POST /api/errors/report-user-issue
- Thông điệp: [Báo lỗi học sinh] Đơ lag / Lỗi mạng - AI phản hồi rất chậm, chờ mãi không thấy gợi ý tiếp theo
- Stack Trace: None
- Request Payload: {"issue_type": "LAG", "student_grade": 5, "device_info": "iPad Air (Safari 16.4)", "network": "Wifi gia đình", "last_problem": "Tìm x: 2x + 5 = 15"}

[Đầu Ra JSON Kỳ Vọng]:
{
  "root_cause": "Học sinh sử dụng trình duyệt Safari trên thiết bị iPad gặp độ trễ mạng khi nhận luồng Server-Sent Events (SSE) hoặc API Gemini đang quá tải xử lý bài toán dài, dẫn đến giao diện không nhận được tín hiệu giữ kết nối (heartbeat) và rơi vào trạng thái chờ vô hạn.",
  "resolution_summary": "Tăng timeout client trên thiết bị iOS lên 60 giây, bổ sung ping định kỳ 15 giây giữ kết nối cho luồng chat và hiển thị thông báo kết nối lại thân thiện cho bé.",
  "fix_steps": [
    "Kiểm tra cấu hình SSE/Streaming trong API chat, bổ sung comment ping định kỳ mỗi 15 giây.",
    "Cập nhật Frontend chat client tự động nhận diện mất kết nối và hiển thị nút 'Thử gửi lại'.",
    "Gửi phản hồi chăm sóc phụ huynh/học sinh qua email thông báo hệ thống đã ghi nhận và tối ưu đường truyền."
  ],
  "code_patch": null,
  "file_path": null,
  "line_number": null,
  "confidence_score": 0.80,
  "model_used": "gemini-3.5-flash"
}
"""


# ==============================================================================
# 3. TIỆN ÍCH LỌC BẢO MẬT & CẮT TỈA AN TOÀN (SANITIZATION & TRUNCATION)
# ==============================================================================

def _mask_sensitive_payload(payload_str: str) -> str:
    """Che giấu các trường nhạy cảm (password, token, otp) trong payload trước khi gửi cho AI."""
    if not payload_str:
        return ""
    # Mask password, secret, token, otp
    masked = re.sub(
        r'("(?:password|token|access_token|secret|otp|otp_code)"\s*:\s*)"[^"]+"',
        r'\1"***MASKED***"',
        payload_str,
        flags=re.IGNORECASE,
    )
    return masked


# ==============================================================================
# 4. HÀM CHUẨN HÓA DỮ LIỆU ĐẦU VÀO THÀNH PROMPT
# ==============================================================================

def format_rca_prompt(error_data: Dict[str, Any], max_stack_chars: int = 3500, max_payload_chars: int = 1500) -> str:
    """
    Biến đổi dữ liệu của 1 sự cố hệ thống thành chuỗi Prompt ngữ cảnh chi tiết cho Gemini.
    Bao gồm lọc bảo mật và cắt tỉa độ dài an toàn chống tràn token.
    """
    error_type = error_data.get("error_type", "UNKNOWN")
    error_code = error_data.get("error_code", "N/A")
    severity = error_data.get("severity", "WARNING")
    endpoint = error_data.get("endpoint") or "(Không xác định)"
    message = error_data.get("message", "(Không có thông điệp lỗi)")
    user_email = error_data.get("user_email") or "(Ẩn danh)"

    # Cắt tỉa Stack Trace an toàn nếu quá dài
    raw_stack = error_data.get("stack_trace") or ""
    if raw_stack and len(raw_stack) > max_stack_chars:
        stack_trace = raw_stack[:max_stack_chars] + "\n... [Stack trace đã được cắt ngắn để tối ưu token] ..."
    else:
        stack_trace = raw_stack or "(Không có stack trace)"

    # Lọc bảo mật và cắt tỉa Payload
    raw_payload = error_data.get("request_payload") or ""
    masked_payload = _mask_sensitive_payload(raw_payload)
    if masked_payload and len(masked_payload) > max_payload_chars:
        request_payload = masked_payload[:max_payload_chars] + " ... [Payload đã được cắt ngắn] ..."
    else:
        request_payload = masked_payload or "(Không có dữ liệu gửi lên)"

    prompt = f"""
Hãy phân tích sự cố hệ thống dưới đây và xuất ra kết quả CHẨN ĐOÁN NGUYÊN NHÂN CỐT LÕI (RCA) theo đúng định dạng JSON thuần túy đã quy định.

─── THÔNG TIN SỰ CỐ CẦN PHÂN TÍCH ───
- Mã định danh lỗi: {error_code}
- Phân loại sự cố: {error_type}
- Mức độ nghiêm trọng: {severity}
- API Endpoint gặp lỗi: {endpoint}
- Người dùng liên quan: {user_email}
- Tóm tắt thông điệp lỗi: {message}

─── STACK TRACE CHI TIẾT ───
{stack_trace}

─── DỮ LIỆU GỬI LÊN (REQUEST PAYLOAD) ───
{request_payload}

BẮT ĐẦU PHÂN TÍCH VÀ XUẤT RA JSON:
"""
    return prompt.strip()


# ==============================================================================
# 5. HÀM PARSER & VALIDATOR BÓC TÁCH KẾT QUẢ AI SANG SCHEMA
# ==============================================================================

def parse_rca_output(raw_output: str, model_used: str = "gemini-3.5-flash") -> AiDiagnosisData:
    """
    Bóc tách phản hồi văn bản từ Gemini AI thành đối tượng Schema AiDiagnosisData.
    Xử lý an toàn:
      - Tự động gỡ bỏ markdown block ```json ... ``` nếu có.
      - Tự phục hồi an toàn (Self-healing Fallback) khi JSON bị lỗi cú pháp, không làm chết ứng dụng.
    """
    cleaned = raw_output.strip()

    # 1. Gỡ bỏ markdown code block nếu Gemini bọc ngoài
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    # 2. Tìm khối JSON đầu tiên nếu có văn bản râu ria
    json_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if json_match:
        cleaned = json_match.group(1).strip()

    # 3. Tiến hành parse JSON
    try:
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("Parsed JSON is not a dictionary")

        # Đảm bảo có model_used
        if not data.get("model_used"):
            data["model_used"] = model_used

        # Chống ảo giác: nếu không có file_path hoặc rỗng -> gán None
        if data.get("file_path") in ["", "None", "null", "N/A"]:
            data["file_path"] = None

        if data.get("line_number") in ["", "None", "null", "N/A", 0]:
            data["line_number"] = None
        elif isinstance(data.get("line_number"), str):
            try:
                data["line_number"] = int(data["line_number"])
            except ValueError:
                data["line_number"] = None

        # BỘ LỌC XÁC THỰC ĐƯỜNG DẪN THỰC TẾ (Path Verification & Anti-Hallucination Guard)
        # Chỉ giữ lại file_path nếu tệp đó thực sự tồn tại trong cây thư mục dự án
        if data.get("file_path"):
            fp = str(data["file_path"]).strip().replace("\\", "/")
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            full_path = os.path.join(project_root, fp)
            if not os.path.exists(full_path):
                # Thử tìm tương đối trong backend hoặc frontend
                backend_path = os.path.join(project_root, "backend", fp)
                frontend_path = os.path.join(project_root, "frontend", fp)
                if os.path.exists(backend_path):
                    data["file_path"] = os.path.relpath(backend_path, project_root).replace("\\", "/")
                elif os.path.exists(frontend_path):
                    data["file_path"] = os.path.relpath(frontend_path, project_root).replace("\\", "/")
                else:
                    # File hoàn toàn không tồn tại trong repository -> AI ảo giác -> Triệt tiêu!
                    data["file_path"] = None
                    data["line_number"] = None

        return AiDiagnosisData.model_validate(data)

    except Exception as exc:
        # Cơ chế Fallback tự phục hồi an toàn: không crash hệ thống
        return AiDiagnosisData(
            root_cause=f"AI đã tạo kết quả nhưng không thể phân tích cú pháp JSON: {str(exc)}",
            resolution_summary=f"Phản hồi thô từ AI: {raw_output[:200]}...",
            fix_steps=["Kiểm tra lại format phản hồi của mô hình AI.", "Thử phân tích lại bằng nút Phân tích AI."],
            code_patch=None,
            file_path=None,
            line_number=None,
            confidence_score=0.5,
            model_used=model_used,
        )
