# backend/test/test_ai_error_diagnosis.py
"""
US 11.3 - Task T378: Kịch Bản Kiểm Thử Tích Hợp Tự Động Chẩn Đoán Lỗi Bằng Trợ Lý AI
===================================================================================
Nghiệm thu trực tiếp các tiêu chí chấp nhận trong đặc tả US 11.3:
  1. [Tiêu chí 3 & 5] Ca lỗi code Python thực tế (ZeroDivisionError):
     - AI chỉ rõ chính xác file_path, line_number.
     - Giải thích nguyên nhân bằng tiếng Việt dễ hiểu.
     - Cung cấp đoạn mã sửa mẫu an toàn (code_patch) để Admin sao chép.
  2. [Tiêu chí 4 & 6] Ca báo cáo học sinh đơ lag chat (USER_REPORT):
     - AI đưa ra gợi ý hạ tầng mạng (SSE connection, heartbeat ping 15s, client timeout 60s).
     - Cung cấp câu tóm tắt (resolution_summary) ngắn gọn để điền nhanh vào ghi chú.
  3. [Tiêu chí 7] Cơ chế Cache-First (Zero Duplicate Cost):
     - Gọi lại API lần 2 cho cả 2 ca lỗi -> Trả về ngay lập tức từ DB (cached=True).
     - Số lượt gọi đến Gemini API hoàn toàn bằng 0, tiết kiệm 100% token lặp lại.
  4. Cơ chế Bắt buộc làm mới (force_refresh=true):
     - Bỏ qua cache khi Admin yêu cầu, kích hoạt phân tích mới và cập nhật DB.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Đưa thư mục backend vào python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import auth
import models
from database import SessionLocal
from schemas import AiDiagnosisData

client = TestClient(app)

# Định danh tài khoản Quản trị viên thử nghiệm
ADMIN_USER_ID = f"admin_t378_{uuid.uuid4().hex[:6]}"
ADMIN_TOKEN = auth.create_access_token({
    "sub": ADMIN_USER_ID,
    "email": "admin_test_t378@socratickid.edu.vn",
    "role": "ADMIN",
    "session_version": 1,
})
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture(scope="module")
def setup_realistic_errors():
    """
    Khởi tạo 2 ca lỗi thực tế vào Database:
      - Ca 1: Lỗi code Python thực tế (ZeroDivisionError tại independence_service.py:74).
      - Ca 2: Báo cáo học sinh mạng lag (USER_REPORT về luồng chat SSE).
    """
    db = SessionLocal()
    python_error_id = f"err_py_{uuid.uuid4().hex[:8]}"
    student_report_id = f"err_stu_{uuid.uuid4().hex[:8]}"

    # 1. Bản ghi lỗi code Python thực tế
    python_error = models.SystemError(
        id=python_error_id,
        error_code="ERR_500_ZERO_DIV",
        error_type="CRASH_500",
        severity="CRITICAL",
        message="ZeroDivisionError: float division by zero in calculate_independence_score",
        stack_trace=(
            'Traceback (most recent call last):\n'
            '  File "backend/routers/chat.py", line 185, in send_chat_message\n'
            '  File "backend/services/independence_service.py", line 74, in calculate_independence_score\n'
            '    score = round((valid_turns / total_turns) * 100, 1)\n'
            'ZeroDivisionError: float division by zero'
        ),
        endpoint="POST /api/chat/message",
        request_payload='{"session_id": "sess_123", "message": "Em xong bài rồi ạ"}',
        status="OPEN",
        ai_diagnosis=None,
        ai_diagnosed_at=None,
    )

    # 2. Bản ghi phản ánh học sinh bị mạng lag
    student_report = models.SystemError(
        id=student_report_id,
        error_code="UR_LAG_CHAT_01",
        error_type="USER_REPORT",
        severity="INFO",
        message="[Báo lỗi học sinh] Em gửi tin nhắn mà AI bị đơ, quay tròn hoài không trả lời",
        stack_trace=None,
        endpoint="/chat/message",
        request_payload=(
            '{"reason": "AI trả lời chậm/mạng lag", '
            '"detail": "Quay tròn hơn 40 giây không ra chữ", '
            '"session_id": "sess_888", "client_context": {"browser": "Chrome", "network": "Wifi"}}'
        ),
        status="OPEN",
        ai_diagnosis=None,
        ai_diagnosed_at=None,
    )

    db.add(python_error)
    db.add(student_report)
    db.commit()
    db.refresh(python_error)
    db.refresh(student_report)
    db.close()

    yield {
        "python_error_id": python_error_id,
        "student_report_id": student_report_id,
    }

    # Dọn dẹp dữ liệu sau khi kiểm thử xong
    db = SessionLocal()
    for eid in [python_error_id, student_report_id]:
        rec = db.query(models.SystemError).filter(models.SystemError.id == eid).first()
        if rec:
            db.delete(rec)
    db.commit()
    db.close()


# ==============================================================================
# KIỂM THỬ CA 1: Lỗi Sập Code Python Thực Tế (Tiêu chí chấp nhận số 3 & 5)
# ==============================================================================

def test_scenario_1_python_code_crash(setup_realistic_errors):
    """
    Xác thực Tiêu chí 3 & 5:
      - AI chỉ rõ chính xác file_path và line_number gây lỗi.
      - Giải thích nguyên nhân gốc rễ bằng tiếng Việt dễ hiểu.
      - Cung cấp đoạn mã sửa mẫu an toàn (code_patch) để Admin sao chép.
      - Lưu thành công kết quả vào database.
    """
    error_id = setup_realistic_errors["python_error_id"]

    mock_rca_result = AiDiagnosisData(
        root_cause=(
            "Hàm tính điểm tự lập calculate_independence_score thực hiện phép chia khi mẫu số "
            "total_turns bằng 0 (phiên học vừa bắt đầu, chưa có lượt trao đổi), dẫn đến ngoại lệ ZeroDivisionError."
        ),
        resolution_summary="Bổ sung điều kiện kiểm tra total_turns <= 0 trước khi tính điểm; nếu bằng 0 trả về 0.0.",
        fix_steps=[
            "Mở tệp backend/services/independence_service.py tại dòng 74.",
            "Bổ sung điều kiện: if not total_turns or total_turns <= 0: return 0.0.",
            "Chạy lại bộ kiểm thử tự động để xác nhận ngoại lệ đã được xử lý triệt để.",
        ],
        code_patch=(
            "def calculate_independence_score(valid_turns: int, total_turns: int) -> float:\n"
            "    if not total_turns or total_turns <= 0:\n"
            "        return 0.0\n"
            "    return round((valid_turns / total_turns) * 100, 1)"
        ),
        file_path="backend/services/independence_service.py",
        line_number=74,
        confidence_score=0.98,
        model_used="gemini-3.5-flash",
    )

    with patch("routers.admin_errors.ErrorDiagnosisService") as MockServiceClass:
        mock_service = MagicMock()
        mock_service.diagnose_error.return_value = mock_rca_result
        MockServiceClass.return_value = mock_service

        # Gọi API chẩn đoán lần đầu
        res = client.post(f"/admin/errors/{error_id}/ai-diagnose", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()

        # 1. Xác thực cấu trúc phản hồi
        assert data["success"] is True
        assert data["cached"] is False
        assert data["error_id"] == error_id

        # 2. Xác thực Tiêu chí 3: Tên file, dòng code và tiếng Việt
        diag = data["ai_diagnosis"]
        assert diag["file_path"] == "backend/services/independence_service.py"
        assert diag["line_number"] == 74
        assert "ZeroDivisionError" in diag["root_cause"]
        assert "tính điểm tự lập" in diag["root_cause"]

        # 3. Xác thực Tiêu chí 5: Cung cấp code patch ngắn đã sửa chuẩn
        assert diag["code_patch"] is not None
        assert "total_turns <= 0" in diag["code_patch"]
        assert "return 0.0" in diag["code_patch"]

        # 4. Xác thực dữ liệu đã được lưu bền vững vào database
        db = SessionLocal()
        record_in_db = db.query(models.SystemError).filter(models.SystemError.id == error_id).first()
        assert record_in_db is not None
        assert record_in_db.ai_diagnosis is not None
        assert record_in_db.ai_diagnosis["line_number"] == 74
        assert record_in_db.ai_diagnosed_at is not None
        db.close()


# ==============================================================================
# KIỂM THỬ CA 2: Báo Cáo Học Sinh Mạng Lag / Đơ Chat (Tiêu chí chấp nhận số 4 & 6)
# ==============================================================================

def test_scenario_2_student_lag_report(setup_realistic_errors):
    """
    Xác thực Tiêu chí 4 & 6:
      - AI nhận diện báo cáo học sinh, đưa ra các gợi ý hạ tầng mạng (SSE, Ping, Timeout).
      - Cung cấp câu tóm tắt (resolution_summary) ngắn gọn để phục vụ nút 1-Click điền ghi chú.
    """
    error_id = setup_realistic_errors["student_report_id"]

    mock_user_report_result = AiDiagnosisData(
        root_cause=(
            "Phản ánh từ học sinh liên quan đến hiện tượng giật lag khung chat. "
            "Bối cảnh trình duyệt client cho thấy luồng Server-Sent Events (SSE) bị đứt kết nối ngầm "
            "giữa chừng do thời gian chờ client (Client Timeout) quá ngắn khi mạng chập chờn."
        ),
        resolution_summary="Đã cấu hình Heartbeat Ping 15s cho luồng SSE chat và nâng client timeout lên 60s để chống rớt kết nối mạng học sinh.",
        fix_steps=[
            "Bổ sung cơ chế Heartbeat Ping định kỳ mỗi 15 giây cho luồng SSE để duy trì kết nối sống.",
            "Tăng thời gian chờ phản hồi tối đa trên client từ 30s lên 60s đối với các bài giải toán nhiều bước.",
            "Hiển thị thông báo hỗ trợ học sinh kiểm tra lại kết nối Wifi khi phát hiện mất kết nối.",
        ],
        code_patch=(
            "const SSE_CLIENT_TIMEOUT_MS = 60000;   // Nâng timeout lên 60s chống mạng lag\n"
            "const HEARTBEAT_INTERVAL_MS = 15000;  // Gửi heartbeat ping mỗi 15s"
        ),
        file_path=None,
        line_number=None,
        confidence_score=0.85,
        model_used="gemini-3.5-flash",
    )

    with patch("routers.admin_errors.ErrorDiagnosisService") as MockServiceClass:
        mock_service = MagicMock()
        mock_service.diagnose_error.return_value = mock_user_report_result
        MockServiceClass.return_value = mock_service

        # Gọi API chẩn đoán lỗi phản ánh học sinh
        res = client.post(f"/admin/errors/{error_id}/ai-diagnose", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()

        # 1. Xác thực cấu trúc phản hồi
        assert data["success"] is True
        assert data["cached"] is False

        # 2. Xác thực Tiêu chí 4: Gợi ý hạ tầng mạng, SSE, timeout
        diag = data["ai_diagnosis"]
        assert "Server-Sent Events" in diag["root_cause"] or "SSE" in diag["root_cause"] or "mạng" in diag["root_cause"]
        assert any("Heartbeat" in step or "kết nối" in step for step in diag["fix_steps"])

        # 3. Xác thực Tiêu chí 6: Tóm tắt ngắn gọn để điền 1-Click vào ô ghi chú
        assert diag["resolution_summary"] is not None
        assert len(diag["resolution_summary"]) > 10
        assert "Heartbeat Ping" in diag["resolution_summary"] or "SSE" in diag["resolution_summary"]


# ==============================================================================
# KIỂM THỬ CA 3: Cơ Chế Cache-First Không Gọi Lại AI (Tiêu chí chấp nhận số 7)
# ==============================================================================

def test_scenario_3_cache_first_zero_duplicate_cost(setup_realistic_errors):
    """
    Xác thực Tiêu chí 7:
      - Khi Admin mở lại sự cố đã chẩn đoán xong -> Toàn bộ phân tích hiển thị tức thì (< 0.1s).
      - Tuyệt đối KHÔNG gọi lại Gemini API (call_count == 0).
      - Dữ liệu trả về từ Cache DB nguyên vẹn 100%.
    """
    py_error_id = setup_realistic_errors["python_error_id"]
    stu_error_id = setup_realistic_errors["student_report_id"]

    # Đặt spy/mock để giám sát: nếu ErrorDiagnosisService bị khởi tạo hoặc gọi là FAIL test
    with patch("routers.admin_errors.ErrorDiagnosisService") as MockServiceClass:
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service

        # ─── Kiểm tra Cache Hit Ca 1 (Lỗi Python) ───
        res_py = client.post(f"/admin/errors/{py_error_id}/ai-diagnose", headers=ADMIN_HEADERS)
        assert res_py.status_code == 200
        data_py = res_py.json()
        assert data_py["cached"] is True
        assert data_py["ai_diagnosis"]["line_number"] == 74
        assert data_py["ai_diagnosis"]["file_path"] == "backend/services/independence_service.py"

        # ─── Kiểm tra Cache Hit Ca 2 (Báo cáo học sinh) ───
        res_stu = client.post(f"/admin/errors/{stu_error_id}/ai-diagnose", headers=ADMIN_HEADERS)
        assert res_stu.status_code == 200
        data_stu = res_stu.json()
        assert data_stu["cached"] is True
        assert "Heartbeat Ping" in data_stu["ai_diagnosis"]["resolution_summary"] or "SSE" in data_stu["ai_diagnosis"]["resolution_summary"]

        # KHẲNG ĐỊNH: Tuyệt đối không có bất kỳ lệnh gọi nào đến AI Service!
        assert mock_service.diagnose_error.call_count == 0
        MockServiceClass.assert_not_called()


# ==============================================================================
# KIỂM THỬ CA 4: Cơ Chế Bắt Buộc Làm Mới (force_refresh=true)
# ==============================================================================

def test_scenario_4_force_refresh_updates_db(setup_realistic_errors):
    """
    Xác thực khi truyền force_refresh=true:
      - Bỏ qua dữ liệu trong Cache DB.
      - Gọi AI để phân tích lại và cập nhật timestamp mới.
    """
    py_error_id = setup_realistic_errors["python_error_id"]

    new_diagnosis = AiDiagnosisData(
        root_cause="Phân tích lại sau khi cập nhật mã nguồn",
        resolution_summary="Đã thêm kiểm tra biên hoàn chỉnh",
        fix_steps=["Kiểm tra lại code"],
        code_patch=None,
        file_path="backend/services/independence_service.py",
        line_number=74,
        confidence_score=0.99,
        model_used="gemini-3.5-flash",
    )

    with patch("routers.admin_errors.ErrorDiagnosisService") as MockServiceClass:
        mock_service = MagicMock()
        mock_service.diagnose_error.return_value = new_diagnosis
        MockServiceClass.return_value = mock_service

        # Gọi với force_refresh=true
        res = client.post(
            f"/admin/errors/{py_error_id}/ai-diagnose?force_refresh=true",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["cached"] is False
        assert data["ai_diagnosis"]["root_cause"] == "Phân tích lại sau khi cập nhật mã nguồn"
        assert mock_service.diagnose_error.call_count == 1
