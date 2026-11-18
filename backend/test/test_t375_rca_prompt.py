# backend/test/test_t375_rca_prompt.py
import pytest
from agents.rca_prompt import (
    RCA_SYSTEM_INSTRUCTION,
    RCA_FEW_SHOT_EXAMPLES,
    GEMINI_RCA_GENERATION_CONFIG,
    _mask_sensitive_payload,
    format_rca_prompt,
    parse_rca_output,
)
from schemas import AiDiagnosisData


def test_rca_system_instruction_contains_core_rules():
    """Kiểm tra System Instruction có đủ các quy tắc then chốt."""
    assert "Senior Site Reliability Engineer" in RCA_SYSTEM_INSTRUCTION
    assert "CRASH_500" in RCA_SYSTEM_INSTRUCTION
    assert "USER_REPORT" in RCA_SYSTEM_INSTRUCTION
    assert "ANTI-HALLUCINATION" in RCA_SYSTEM_INSTRUCTION
    assert "root_cause" in RCA_SYSTEM_INSTRUCTION
    assert "resolution_summary" in RCA_SYSTEM_INSTRUCTION
    assert "code_patch" in RCA_SYSTEM_INSTRUCTION
    assert "TIẾNG VIỆT" in RCA_SYSTEM_INSTRUCTION


def test_rca_generation_config():
    """Kiểm tra cấu hình tham số sinh của Gemini."""
    assert GEMINI_RCA_GENERATION_CONFIG["temperature"] == 0.2
    assert GEMINI_RCA_GENERATION_CONFIG["response_mime_type"] == "application/json"


def test_mask_sensitive_payload():
    """Kiểm tra tính năng bảo mật lọc bỏ mật khẩu và token trong payload."""
    raw_payload = '{"username": "admin", "password": "supersecretpassword123", "token": "xyz_jwt_token"}'
    masked = _mask_sensitive_payload(raw_payload)

    assert "supersecretpassword123" not in masked
    assert "xyz_jwt_token" not in masked
    assert '"password": "***MASKED***"' in masked


def test_format_rca_prompt_crash_500():
    """Kiểm tra format prompt với lỗi CRASH_500 có stack trace."""
    error_data = {
        "error_type": "CRASH_500",
        "error_code": "ERR_TEST_001",
        "severity": "CRITICAL",
        "endpoint": "POST /api/chat",
        "message": "KeyError: 'user_id'",
        "stack_trace": "File 'main.py', line 12, in handle_chat",
        "request_payload": '{"message": "hello", "password": "mypassword"}',
        "user_email": "student@socratickid.vn",
    }
    prompt = format_rca_prompt(error_data)

    assert "ERR_TEST_001" in prompt
    assert "CRASH_500" in prompt
    assert "KeyError: 'user_id'" in prompt
    assert "File 'main.py', line 12" in prompt
    assert "student@socratickid.vn" in prompt
    assert "mypassword" not in prompt  # Đã được che giấu


def test_format_rca_prompt_truncation():
    """Kiểm tra cắt tỉa stack trace quá dài chống tràn token."""
    long_stack = "Line in stack trace\n" * 500  # Rất dài
    error_data = {
        "error_type": "CRASH_500",
        "error_code": "ERR_LONG",
        "stack_trace": long_stack,
    }
    prompt = format_rca_prompt(error_data, max_stack_chars=200)

    assert "đã được cắt ngắn để tối ưu token" in prompt


def test_format_rca_prompt_user_report():
    """Kiểm tra format prompt với phản ánh của học sinh (không có stack trace)."""
    error_data = {
        "error_type": "USER_REPORT",
        "error_code": "UR_LAG_002",
        "severity": "WARNING",
        "endpoint": "POST /api/errors/report-user-issue",
        "message": "[Báo lỗi học sinh] Đơ lag khi giải toán",
        "stack_trace": None,
        "request_payload": '{"device": "iPad"}',
        "user_email": "be_nam@gmail.com",
    }
    prompt = format_rca_prompt(error_data)

    assert "UR_LAG_002" in prompt
    assert "USER_REPORT" in prompt
    assert "(Không có stack trace)" in prompt
    assert "iPad" in prompt


def test_parse_rca_output_plain_json():
    """Kiểm tra parse phản hồi JSON chuẩn từ AI."""
    raw_ai_response = """
    {
      "root_cause": "Thiếu kiểm tra khóa session_id trong từ điển phiên làm việc",
      "resolution_summary": "Sử dụng session.get('session_id') thay vì truy cập trực tiếp bằng ngoặc vuông",
      "fix_steps": [
        "Mở file backend/routers/chat.py",
        "Sửa câu lệnh lấy khóa từ điển"
      ],
      "code_patch": "session_id = data.get('session_id')",
      "file_path": "backend/routers/chat.py",
      "line_number": "88",
      "confidence_score": 0.95,
      "model_used": "gemini-3.5-flash"
    }
    """
    result = parse_rca_output(raw_ai_response)

    assert isinstance(result, AiDiagnosisData)
    assert result.line_number == 88  # Ép kiểu thành công từ string "88"
    assert result.file_path == "backend/routers/chat.py"
    assert result.confidence_score == 0.95
    assert "Thiếu kiểm tra khóa session_id" in result.root_cause


def test_parse_rca_output_markdown_wrapped_json():
    """Kiểm tra parse khi AI vô tình bọc trong ```json ... ```."""
    raw_markdown = """
    ```json
    {
      "root_cause": "Timeout kết nối mạng",
      "resolution_summary": "Tăng timeout client",
      "fix_steps": ["Cấu hình timeout 60s"],
      "code_patch": null,
      "file_path": "null",
      "line_number": null,
      "confidence_score": 0.8,
      "model_used": "gemini-3.5-flash"
    }
    ```
    """
    result = parse_rca_output(raw_markdown)

    assert isinstance(result, AiDiagnosisData)
    assert result.root_cause == "Timeout kết nối mạng"
    assert result.code_patch is None
    assert result.file_path is None  # Đã chuyển "null" string thành None chuẩn


def test_parse_rca_output_corrupted_fallback():
    """Kiểm tra cơ chế tự phục hồi (Self-healing Fallback) khi AI trả về lỗi cú pháp."""
    corrupted_output = "Xin lỗi, tôi không thể phân tích vì thiếu stack trace {abc"
    result = parse_rca_output(corrupted_output)

    assert isinstance(result, AiDiagnosisData)
    assert "không thể phân tích cú pháp JSON" in result.root_cause
    assert result.confidence_score == 0.5
