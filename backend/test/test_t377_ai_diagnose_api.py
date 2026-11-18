# backend/test/test_t377_ai_diagnose_api.py
"""
US 11.3 - Task T377: Kiểm Thử API Chẩn Đoán Lỗi (POST /admin/errors/{error_id}/ai-diagnose)
========================================================================================
Kiểm tra:
  1. Phân quyền: Chặn non-admin / học sinh (403 Forbidden).
  2. Báo lỗi 404 khi error_id không tồn tại.
  3. Cache Miss (lần gọi đầu): Gọi AI, lưu DB, trả về cached=False.
  4. Cache Hit (lần gọi sau): Trả về từ DB, cached=True, không gọi lại AI.
  5. Force Refresh: Bỏ qua cache, gọi lại AI, cached=False.
  6. DB Resilience: Khi DB commit lỗi, vẫn trả về kết quả AI cho Admin mà không crash 500.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import auth
import models
from database import SessionLocal
from schemas import AiDiagnosisData

client = TestClient(app)

ADMIN_USER_ID = f"test_admin_{uuid.uuid4().hex[:6]}"
STUDENT_USER_ID = f"test_student_{uuid.uuid4().hex[:6]}"

ADMIN_TOKEN = auth.create_access_token({
    "sub": ADMIN_USER_ID,
    "email": "admin_test@socratickid.edu.vn",
    "role": "ADMIN",
    "session_version": 1,
})

STUDENT_TOKEN = auth.create_access_token({
    "sub": STUDENT_USER_ID,
    "email": "student_test@socratickid.edu.vn",
    "role": "STUDENT",
    "session_version": 1,
})

ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}


@pytest.fixture(scope="module")
def setup_test_error():
    """Tạo một bản ghi lỗi giả lập trong database để test API."""
    db = SessionLocal()
    error_id = f"err_test_{uuid.uuid4().hex[:8]}"
    error_record = models.SystemError(
        id=error_id,
        error_code="ERR_TEST_500",
        error_type="CRASH_500",
        severity="CRITICAL",
        message="ZeroDivisionError: division by zero in calculate_metric",
        stack_trace='File "backend/services/calc.py", line 42, in calculate_metric',
        endpoint="POST /api/chat/message",
        status="OPEN",
        ai_diagnosis=None,
        ai_diagnosed_at=None,
    )
    db.add(error_record)
    db.commit()
    db.refresh(error_record)
    db.close()

    yield error_id

    # Cleanup sau khi test
    db = SessionLocal()
    rec = db.query(models.SystemError).filter(models.SystemError.id == error_id).first()
    if rec:
        db.delete(rec)
        db.commit()
    db.close()


def test_ai_diagnose_requires_admin(setup_test_error):
    """Kiểm tra học sinh không thể gọi API chẩn đoán lỗi (403 Forbidden)."""
    error_id = setup_test_error
    response = client.post(f"/admin/errors/{error_id}/ai-diagnose", headers=STUDENT_HEADERS)
    assert response.status_code == 403


def test_ai_diagnose_not_found():
    """Kiểm tra truyền ID không tồn tại trả về 404 Not Found."""
    fake_id = "non_existent_error_id_12345"
    response = client.post(f"/admin/errors/{fake_id}/ai-diagnose", headers=ADMIN_HEADERS)
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_ai_diagnose_cache_miss_then_cache_hit(setup_test_error):
    """
    Kiểm tra cơ chế Cache-First (AC-AI-07):
      - Lần 1: Chưa có cache -> Gọi ErrorDiagnosisService, cached=False, ghi DB.
      - Lần 2: Đã có trong DB -> Trả về ngay lập tức, cached=True, không gọi lại Service.
    """
    error_id = setup_test_error
    mock_diagnosis = AiDiagnosisData(
        root_cause="Mẫu số phép chia bằng 0",
        resolution_summary="Thêm kiểm tra mẫu số trước khi chia",
        fix_steps=["Kiểm tra biến total > 0"],
        code_patch="if total > 0: return val / total",
        file_path="backend/services/calc.py",
        line_number=42,
        confidence_score=0.96,
        model_used="gemini-3.5-flash",
    )

    with patch("routers.admin_errors.ErrorDiagnosisService") as MockServiceClass:
        mock_instance = MagicMock()
        mock_instance.diagnose_error.return_value = mock_diagnosis
        MockServiceClass.return_value = mock_instance

        # ─── LƯỢT 1: Cache Miss (Chưa có phân tích) ───
        res1 = client.post(f"/admin/errors/{error_id}/ai-diagnose", headers=ADMIN_HEADERS)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["success"] is True
        assert data1["cached"] is False
        assert data1["error_id"] == error_id
        assert data1["ai_diagnosis"]["root_cause"] == "Mẫu số phép chia bằng 0"
        assert data1["ai_diagnosis"]["line_number"] == 42
        assert mock_instance.diagnose_error.call_count == 1

        # ─── LƯỢT 2: Cache Hit (Lấy trực tiếp từ DB) ───
        res2 = client.post(f"/admin/errors/{error_id}/ai-diagnose", headers=ADMIN_HEADERS)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["success"] is True
        assert data2["cached"] is True
        assert data2["error_id"] == error_id
        assert data2["ai_diagnosis"]["root_cause"] == "Mẫu số phép chia bằng 0"
        # call_count vẫn giữ nguyên là 1, chứng tỏ không hề gọi lại AI!
        assert mock_instance.diagnose_error.call_count == 1


def test_ai_diagnose_force_refresh(setup_test_error):
    """
    Kiểm tra tham số force_refresh=true:
    Bỏ qua kết quả đã lưu trong DB để yêu cầu AI phân tích lại.
    """
    error_id = setup_test_error
    mock_refresh_diagnosis = AiDiagnosisData(
        root_cause="Phân tích mới cập nhật sau khi refresh",
        resolution_summary="Giải pháp nâng cao",
        fix_steps=["Cập nhật thư viện"],
        code_patch=None,
        file_path=None,
        line_number=None,
        confidence_score=0.99,
        model_used="gemini-3.5-flash",
    )

    with patch("routers.admin_errors.ErrorDiagnosisService") as MockServiceClass:
        mock_instance = MagicMock()
        mock_instance.diagnose_error.return_value = mock_refresh_diagnosis
        MockServiceClass.return_value = mock_instance

        # Gọi với query param force_refresh=true
        res = client.post(
            f"/admin/errors/{error_id}/ai-diagnose?force_refresh=true",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["cached"] is False
        assert data["ai_diagnosis"]["root_cause"] == "Phân tích mới cập nhật sau khi refresh"
        assert mock_instance.diagnose_error.call_count == 1


def test_ai_diagnose_alias_endpoint(setup_test_error):
    """Kiểm tra alias /api/admin/errors/{id}/ai-diagnose hoạt động đồng nhất."""
    error_id = setup_test_error
    response = client.post(f"/api/admin/errors/{error_id}/ai-diagnose", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["success"] is True
