# backend/test/test_t376_error_diagnosis_service.py
import pytest
from unittest.mock import patch, MagicMock
from concurrent.futures import TimeoutError as FutureTimeoutError
from services.error_diagnosis_service import ErrorDiagnosisService
from schemas import AiDiagnosisData


def test_service_initialization():
    """Kiểm tra khởi tạo ErrorDiagnosisService đọc đúng model từ config."""
    service = ErrorDiagnosisService(db=None)
    assert service.primary_model == "gemini-3.5-flash"
    assert service.backup_model == "gemini-3.5-flash-lite"


def test_service_extract_error_dict_none():
    """Kiểm tra xử lý an toàn khi đầu vào error_input là None."""
    service = ErrorDiagnosisService(db=None)
    extracted = service._extract_error_dict(None)
    assert extracted["id"] == "unknown"
    assert extracted["error_code"] == "ERR_UNKNOWN"
    assert extracted["message"] == "Không có thông tin sự cố"


def test_service_diagnose_success_mocked():
    """Kiểm tra luồng chẩn đoán thành công khi Gemini trả về kết quả."""
    service = ErrorDiagnosisService(db=None)
    mock_json = """
    {
      "root_cause": "Lỗi chia cho 0 trong hàm tính điểm",
      "resolution_summary": "Thêm kiểm tra mẫu số khác 0",
      "fix_steps": ["Kiểm tra denominator > 0"],
      "code_patch": "if denom == 0: return 0",
      "file_path": "backend/services/score.py",
      "line_number": 42,
      "confidence_score": 0.95,
      "model_used": "gemini-3.5-flash"
    }
    """

    with patch.object(service, "_call_gemini_raw", return_value=mock_json):
        result = service.diagnose_error({
            "error_type": "CRASH_500",
            "message": "ZeroDivisionError: float division by zero",
            "stack_trace": "File 'backend/services/score.py', line 42",
        })

        assert isinstance(result, AiDiagnosisData)
        assert result.root_cause == "Lỗi chia cho 0 trong hàm tính điểm"
        assert result.line_number == 42
        assert result.model_used == "gemini-3.5-flash"


def test_service_timeout_failover_to_backup():
    """Kiểm tra khi Primary Model bị Timeout -> tự động chuyển mạch sang Backup Model."""
    service = ErrorDiagnosisService(db=None)
    backup_mock_json = """
    {
      "root_cause": "Chẩn đoán thành công bởi Backup Model",
      "resolution_summary": "Xử lý bằng trạm dự phòng",
      "fix_steps": ["Xem lại code"],
      "code_patch": null,
      "file_path": null,
      "line_number": null,
      "confidence_score": 0.8,
      "model_used": "gemini-3.5-flash-lite"
    }
    """

    def mock_call(model_name, prompt, timeout_seconds):
        if model_name == "gemini-3.5-flash":
            raise FutureTimeoutError("Primary model timed out")
        return backup_mock_json

    with patch.object(service, "_call_gemini_raw", side_effect=mock_call):
        result = service.diagnose_error({
            "error_type": "CRASH_500",
            "message": "Timeout test",
        })

        assert isinstance(result, AiDiagnosisData)
        assert result.root_cause == "Chẩn đoán thành công bởi Backup Model"
        assert result.model_used == "gemini-3.5-flash-lite"


def test_service_auth_error_skip_backup():
    """Kiểm tra khi gặp lỗi xác thực 401/Unauthenticated -> ngắt ngay, không gọi backup lãng phí thời gian."""
    service = ErrorDiagnosisService(db=None)
    mock_call = MagicMock(side_effect=Exception("401 Unauthenticated: API_KEY_INVALID"))

    with patch.object(service, "_call_gemini_raw", mock_call):
        result = service.diagnose_error({
            "error_type": "CRASH_500",
            "message": "Crash message",
        })

        # Chỉ được gọi 1 lần (cho primary), không gọi backup
        assert mock_call.call_count == 1
        assert result.model_used == "local-heuristic-fallback"
        assert "không hợp lệ" in result.root_cause


def test_service_graceful_fallback_when_both_fail():
    """Kiểm tra khi cả 2 model đều gặp sự cố -> Kích hoạt Local Heuristic Fallback an toàn."""
    service = ErrorDiagnosisService(db=None)

    with patch.object(service, "_call_gemini_raw", side_effect=Exception("API Down")):
        result = service.diagnose_error({
            "error_type": "CRASH_500",
            "message": "OperationalError: connection to server lost",
            "stack_trace": 'File "backend/database.py", line 18, in connect',
            "endpoint": "POST /api/chat",
        })

        assert isinstance(result, AiDiagnosisData)
        assert result.model_used == "local-heuristic-fallback"
        assert result.file_path == "backend/database.py"
        assert result.line_number == 18
        assert "OperationalError" in result.root_cause


def test_service_graceful_fallback_user_report():
    """Kiểm tra Local Fallback cho trường hợp học sinh báo lỗi mạng/lag."""
    service = ErrorDiagnosisService(db=None)

    with patch.object(service, "_call_gemini_raw", side_effect=Exception("API Down")):
        result = service.diagnose_error({
            "error_type": "USER_REPORT",
            "message": "[Báo lỗi học sinh] Đơ lag khi giải toán",
            "stack_trace": None,
        })

        assert isinstance(result, AiDiagnosisData)
        assert result.model_used == "local-heuristic-fallback"
        assert "trải nghiệm" in result.root_cause
        assert result.code_patch is None
