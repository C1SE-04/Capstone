"""
Unit & Integration Test cho Task T374 (US 11.3):
==================================================
Kiểm thử cấu trúc dữ liệu, ORM Model, Pydantic Schema, Router Mapping,
và khả năng xử lý ngoại lệ bao quát cho 2 cột mới:
  - ai_diagnosis (JSONB)
  - ai_diagnosed_at (TIMESTAMPTZ)
"""

import pytest
import json
from datetime import datetime, timezone
import models
import schemas
from routers.admin_errors import _map_system_error_response


def test_t374_model_attributes_exist():
    """Kiểm tra ORM model SystemError có đầy đủ 2 thuộc tính mới và Index."""
    assert hasattr(models.SystemError, "ai_diagnosis"), "SystemError thiếu thuộc tính ai_diagnosis"
    assert hasattr(models.SystemError, "ai_diagnosed_at"), "SystemError thiếu thuộc tính ai_diagnosed_at"
    assert models.SystemError.ai_diagnosed_at.index is True, "Cột ai_diagnosed_at phải có index=True"


def test_t374_schema_serialization_dict():
    """Kiểm tra Pydantic Schema tự động chuẩn hóa dictionary thành AiDiagnosisData."""
    now = datetime.now(timezone.utc)
    diagnosis_dict = {
        "root_cause": "ZeroDivisionError in calculate_score",
        "resolution_summary": "Thêm kiểm tra mẫu số khác 0 trước khi chia",
        "fix_steps": ["Kiểm tra denominator > 0", "Gán điểm 0 nếu mẫu số = 0"],
        "code_patch": "if total == 0: return 0",
        "file_path": "backend/services/score.py",
        "line_number": 42,
        "confidence_score": 0.95,
        "model_used": "gemini-3.5-flash",
    }

    item = schemas.SystemErrorItemResponse(
        id="test-err-001",
        error_code="ERR_500_TEST",
        error_type="CRASH_500",
        severity="CRITICAL",
        message="ZeroDivisionError",
        status="OPEN",
        created_at=now,
        ai_diagnosis=diagnosis_dict,
        ai_diagnosed_at=now,
    )

    assert item.ai_diagnosis is not None
    # Pydantic v2 chuẩn hóa thành AiDiagnosisData typed object
    assert item.ai_diagnosis.root_cause == "ZeroDivisionError in calculate_score"
    assert item.ai_diagnosis.line_number == 42
    assert item.ai_diagnosis.confidence_score == 0.95
    assert item.ai_diagnosed_at == now

    # Khi xuất ra JSON payload (API Response)
    dumped = item.model_dump()
    assert dumped["ai_diagnosis"]["root_cause"] == "ZeroDivisionError in calculate_score"


def test_t374_schema_serialization_typed_model():
    """Kiểm tra Schema hỗ trợ trực tiếp typed model AiDiagnosisData."""
    now = datetime.now(timezone.utc)
    diag_model = schemas.AiDiagnosisData(
        root_cause="Database connection timeout",
        resolution_summary="Tăng pool size và timeout connection",
        fix_steps=["Mở database.py", "Sửa pool_pre_ping=True"],
        code_patch="create_engine(..., pool_pre_ping=True)",
        file_path="backend/database.py",
        line_number=18,
        confidence_score=0.9,
        model_used="gemini-3.5-flash",
    )

    item = schemas.SystemErrorItemResponse(
        id="test-err-002",
        error_code="ERR_DB_TIMEOUT",
        error_type="CRASH_500",
        severity="CRITICAL",
        message="OperationalError",
        status="OPEN",
        created_at=now,
        ai_diagnosis=diag_model,
        ai_diagnosed_at=now,
    )

    assert item.ai_diagnosis.root_cause == "Database connection timeout"
    assert item.ai_diagnosis.confidence_score == 0.9


def test_t374_edge_case_legacy_null_record():
    """Kiểm tra bản ghi cũ (legacy record) chưa có chẩn đoán (NULL) không bị crash."""
    now = datetime.now(timezone.utc)
    item = schemas.SystemErrorItemResponse(
        id="test-legacy-003",
        error_code="ERR_OLD",
        error_type="USER_REPORT",
        severity="INFO",
        message="Báo lỗi từ học sinh cũ",
        status="RESOLVED",
        created_at=now,
        ai_diagnosis=None,
        ai_diagnosed_at=None,
    )

    assert item.ai_diagnosis is None
    assert item.ai_diagnosed_at is None


def test_t374_edge_case_raw_json_string_auto_parse():
    """
    Kiểm tra ngoại lệ: Nếu ai_diagnosis bị lưu thành JSON string thô
    thì field_validator sẽ tự động deserialize thành typed object.
    """
    now = datetime.now(timezone.utc)
    raw_json = json.dumps({"root_cause": "Network packet loss", "resolution_summary": "Thêm retry backoff"})

    item = schemas.SystemErrorItemResponse(
        id="test-raw-004",
        error_code="ERR_NET",
        error_type="AI_TIMEOUT",
        severity="WARNING",
        message="Timeout",
        status="OPEN",
        created_at=now,
        ai_diagnosis=raw_json,
        ai_diagnosed_at=now,
    )

    assert item.ai_diagnosis is not None
    assert item.ai_diagnosis.root_cause == "Network packet loss"
    assert item.ai_diagnosis.resolution_summary == "Thêm retry backoff"


def test_t374_edge_case_corrupted_raw_string():
    """Kiểm tra ngoại lệ: Chuỗi text thô / không phải JSON được đưa an toàn vào root_cause."""
    now = datetime.now(timezone.utc)
    item = schemas.SystemErrorItemResponse(
        id="test-corrupted-005",
        error_code="ERR_CORRUPT",
        error_type="CRASH_500",
        severity="WARNING",
        message="Corrupted string test",
        status="OPEN",
        created_at=now,
        ai_diagnosis="chuỗi text mô tả lỗi thô từ log bên ngoài",
        ai_diagnosed_at=now,
    )

    assert item.ai_diagnosis is not None
    assert "Raw analysis: chuỗi text mô tả lỗi thô" in item.ai_diagnosis.root_cause


def test_t374_router_mapping():
    """Kiểm tra hàm _map_system_error_response trong router admin_errors map đúng 2 trường mới."""
    now = datetime.now(timezone.utc)
    mock_record = models.SystemError(
        id="mock-err-006",
        error_code="ERR_ROUTER_TEST",
        error_type="CRASH_500",
        severity="CRITICAL",
        message="Test Router Mapping",
        status="OPEN",
        created_at=now,
        ai_diagnosis={"root_cause": "Map test passed", "resolution_summary": "Done"},
        ai_diagnosed_at=now,
    )

    mapped = _map_system_error_response(mock_record)

    assert mapped.id == "mock-err-006"
    assert mapped.ai_diagnosis is not None
    assert mapped.ai_diagnosis.root_cause == "Map test passed"
    assert mapped.ai_diagnosis.resolution_summary == "Done"
    assert mapped.ai_diagnosed_at == now
