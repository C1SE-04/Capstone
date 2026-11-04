# test/test_us95_system_errors.py
"""
US 9.5: Trung Tâm Quản Trị Báo Lỗi & Sự Cố Hệ Thống (Incident Hub)
=============================================================================
Kiểm thử toàn diện:
  1. POST /api/errors/report-user-issue:
     - Học sinh báo lỗi AI (AC 9.5.1): Thành công trả về "Cảm ơn em đã gửi phản hồi!",
       nhãn INFO, mã lỗi UR_..., lưu đúng User ID.
     - Debounce chống spam: Bấm liên tiếp trong 30s trả về 429 Too Many Requests.
  2. Middleware tự động bắt Unhandled Exceptions (T9.17):
     - Bắt Crash 500: lưu CRASH_500, nhãn CRITICAL, lưu stack trace.
     - Bắt Timeout: lưu AI_TIMEOUT, nhãn WARNING.
     - Bỏ qua các mã 4xx (400, 404, 422): không ghi nhận vào DB.
     - Bảo mật payload: Tự động mask password, token, otp thành ***MASKED***.
  3. GET /admin/errors (AC 9.5.2 & AC 9.5.3):
     - Chặn quyền học sinh / non-admin (403 Forbidden).
     - Admin xem danh sách sự cố sắp xếp mới nhất lên đầu.
     - Lọc theo status (OPEN, RESOLVED), error_type, severity.
     - Tìm kiếm theo User ID hoặc Email học sinh (AC 9.5.3).
  4. GET /admin/errors/{error_id} (AC 9.5.5 - Drawer trượt):
     - Trả về chi tiết User context, request payload và Full Stack Trace.
  5. PATCH /admin/errors/{error_id}/resolve (AC 9.5.6):
     - Chuyển trạng thái sang RESOLVED ngay lập tức, lưu resolved_by và resolved_at.
"""

import os
import sys
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
import auth
import models
from database import SessionLocal
from middleware import mask_sensitive_payload

client = TestClient(app)

ADMIN_USER_ID = "c8bb335bcbe24b859d10d740afbacaf4"
STUDENT_USER_ID = f"test_student_{uuid.uuid4().hex[:6]}"
STUDENT_EMAIL = f"student_{uuid.uuid4().hex[:6]}@socratickid.edu.vn"

ADMIN_TOKEN = auth.create_access_token({
    "sub": ADMIN_USER_ID,
    "email": "admin@socratickid.edu.vn",
    "role": "ADMIN",
    "session_version": 1,
})

STUDENT_TOKEN = auth.create_access_token({
    "sub": STUDENT_USER_ID,
    "email": STUDENT_EMAIL,
    "role": "STUDENT",
    "session_version": 1,
})

ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
STUDENT_HEADERS = {"Authorization": f"Bearer {STUDENT_TOKEN}"}


@pytest.fixture(scope="module", autouse=True)
def setup_test_users():
    """Tạo user thử nghiệm trong DB nếu chưa có để kiểm thử outerjoin user."""
    db = SessionLocal()
    try:
        student = db.query(models.User).filter(models.User.id == STUDENT_USER_ID).first()
        if not student:
            student = models.User(
                id=STUDENT_USER_ID,
                username=f"hs_{uuid.uuid4().hex[:8]}",
                email=STUDENT_EMAIL,
                hashed_password="hashed_pw_test",
                role="STUDENT",
                grade=5,
            )
            db.add(student)
            db.commit()
    finally:
        db.close()


class TestSensitivePayloadMasking:
    """Kiểm tra chức năng lọc bỏ thông tin nhạy cảm trước khi lưu DB."""

    def test_mask_json_dict(self):
        payload = {
            "username": "superkid",
            "password": "SecretPassword123!",
            "token": "secret_jwt_token",
            "otp_code": "123456",
            "other_info": "safe data"
        }
        masked = mask_sensitive_payload(payload)
        assert "SecretPassword123!" not in masked
        assert "secret_jwt_token" not in masked
        assert "123456" not in masked
        assert "***MASKED***" in masked
        assert "superkid" in masked
        assert "safe data" in masked

    def test_mask_raw_string(self):
        raw = "username=test&password=SecretPassWord123&otp=999888"
        masked = mask_sensitive_payload(raw)
        assert "SecretPassWord123" not in masked
        assert "999888" not in masked
        assert "***MASKED***" in masked


class TestReportUserIssue:
    """AC 9.5.1: Học sinh bấm cờ 🚩 báo lỗi bài toán/AI."""

    def test_01_student_can_report_issue(self):
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        res = client.post(
            "/api/errors/report-user-issue",
            headers=STUDENT_HEADERS,
            json={
                "reason": "AI giải sai bước 2",
                "detail": "Đáp án 2 + 2 = 5 là sai",
                "message_id": msg_id,
                "session_id": "sess_123",
                "endpoint": "/chat",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["success"] is True
        assert data["message"] == "Cảm ơn em đã gửi phản hồi!"
        assert data["error_code"].startswith("UR_")
        assert "error_id" in data

        # Kiểm tra bản ghi trong DB
        db = SessionLocal()
        try:
            record = db.query(models.SystemError).filter(models.SystemError.id == data["error_id"]).first()
            assert record is not None
            assert record.error_type == "USER_REPORT"
            assert record.severity == "INFO"
            assert record.user_id == STUDENT_USER_ID
            assert record.user_email == STUDENT_EMAIL
            assert record.status == "OPEN"
        finally:
            db.close()

    def test_02_debounce_blocks_duplicate_report(self):
        """Bấm nút gửi lại ngay lập tức -> 429 Too Many Requests chống spam."""
        msg_id = f"msg_spam_{uuid.uuid4().hex[:8]}"
        # Lần 1: Thành công
        res1 = client.post(
            "/api/errors/report-user-issue",
            headers=STUDENT_HEADERS,
            json={
                "reason": "AI bị đơ",
                "message_id": msg_id,
            },
        )
        assert res1.status_code == 201

        # Lần 2: Gửi lại ngay -> Bị chặn 429
        res2 = client.post(
            "/api/errors/report-user-issue",
            headers=STUDENT_HEADERS,
            json={
                "reason": "AI bị đơ",
                "message_id": msg_id,
            },
        )
        assert res2.status_code == 429
        assert "chờ" in res2.json()["detail"].lower() or "đã ghi nhận" in res2.json()["detail"].lower()


class TestSystemErrorMiddleware:
    """T9.17 & AC 9.5.4: Middleware tự động bắt unhandled exceptions."""

    def test_01_crash_500_captured_with_critical_severity(self):
        """Tạo route giả lập crash 500 để test middleware bắt tự động."""
        from fastapi import APIRouter
        dummy_router = APIRouter()

        @dummy_router.post("/test-system-crash")
        def crash_route(payload: dict):
            raise ZeroDivisionError("Lỗi chia cho 0 giả lập")

        app.include_router(dummy_router)

        secret_payload = {
            "password": "MySuperSecretPassword",
            "number": 0,
        }

        res = client.post("/test-system-crash", headers=STUDENT_HEADERS, json=secret_payload)
        assert res.status_code == 500
        data = res.json()
        assert "error_code" in data
        assert data["error_code"].startswith("ERR_500_")
        assert data["error_type"] == "CRASH_500"

        # Kiểm tra trong DB
        db = SessionLocal()
        try:
            record = db.query(models.SystemError).filter(models.SystemError.error_code == data["error_code"]).first()
            assert record is not None
            assert record.error_type == "CRASH_500"
            assert record.severity == "CRITICAL"
            assert "ZeroDivisionError" in record.stack_trace
            # Đảm bảo password đã được mask
            assert "MySuperSecretPassword" not in (record.request_payload or "")
            assert "***MASKED***" in (record.request_payload or "")
            assert record.user_id == STUDENT_USER_ID
        finally:
            db.close()

    def test_02_timeout_captured_with_warning_severity(self):
        """Giả lập lỗi Timeout -> Lưu AI_TIMEOUT nhãn WARNING."""
        from fastapi import APIRouter
        dummy_router = APIRouter()

        @dummy_router.get("/test-system-timeout")
        def timeout_route():
            raise TimeoutError("Gemini API call timed out after 30 seconds")

        app.include_router(dummy_router)

        res = client.get("/test-system-timeout", headers=STUDENT_HEADERS)
        assert res.status_code == 500
        data = res.json()
        assert data["error_code"].startswith("ERR_TIMEOUT_")
        assert data["error_type"] == "AI_TIMEOUT"

        db = SessionLocal()
        try:
            record = db.query(models.SystemError).filter(models.SystemError.error_code == data["error_code"]).first()
            assert record is not None
            assert record.error_type == "AI_TIMEOUT"
            assert record.severity == "WARNING"
        finally:
            db.close()

    def test_03_client_4xx_not_logged_as_system_error(self):
        """Lỗi 404 / 422 từ client không được coi là crash hệ thống."""
        res = client.get("/non-existent-route-404-test-xyz")
        assert res.status_code == 404

        # Không tạo record lỗi
        db = SessionLocal()
        try:
            record = db.query(models.SystemError).filter(
                models.SystemError.endpoint.contains("non-existent-route-404-test-xyz")
            ).first()
            assert record is None
        finally:
            db.close()


class TestAdminErrorsManagementAPI:
    """AC 9.5.2, 9.5.3, 9.5.5, 9.5.6: API Quản trị sự cố."""

    def test_01_rbac_student_forbidden(self):
        """Học sinh không có quyền xem trang quản trị lỗi (403 Forbidden)."""
        res = client.get("/admin/errors", headers=STUDENT_HEADERS)
        assert res.status_code == 403

    def test_02_admin_list_errors_pagination_and_sorting(self):
        """AC 9.5.2: Admin xem danh sách sự cố, mới nhất lên đầu bảng."""
        res = client.get("/admin/errors?page=1&limit=10", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        if len(data["items"]) >= 2:
            # Sắp xếp giảm dần theo created_at
            t1 = datetime.fromisoformat(data["items"][0]["created_at"])
            t2 = datetime.fromisoformat(data["items"][1]["created_at"])
            assert t1 >= t2

    def test_03_admin_filter_by_status_and_type(self):
        """Lọc danh sách theo status và error_type."""
        res = client.get("/admin/errors?status=OPEN&error_type=USER_REPORT", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        for item in data["items"]:
            assert item["status"] == "OPEN"
            assert item["error_type"] == "USER_REPORT"

    def test_04_admin_search_by_user_id_or_email(self):
        """AC 9.5.3: Nhập User ID hoặc Email vào thanh tìm kiếm -> Lọc ra đúng tài khoản đó."""
        res = client.get(f"/admin/errors?search={STUDENT_USER_ID}", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert STUDENT_USER_ID in (item["user_id"] or "")

    def test_05_admin_drawer_detail(self):
        """AC 9.5.5: Bấm vào dòng lỗi -> Xem chi tiết Full Stack Trace, endpoint, request_payload."""
        # Lấy 1 bản ghi có sẵn
        list_res = client.get("/admin/errors?limit=1", headers=ADMIN_HEADERS)
        items = list_res.json()["items"]
        assert len(items) > 0
        error_id = items[0]["id"]

        detail_res = client.get(f"/admin/errors/{error_id}", headers=ADMIN_HEADERS)
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == error_id
        assert "endpoint" in detail
        assert "severity" in detail
        assert "status" in detail

    def test_06_admin_resolve_error(self):
        """AC 9.5.6: Bấm Đánh dấu đã xử lý -> Tag trạng thái đổi sang RESOLVED."""
        # Tạo 1 sự cố mới để test resolve
        db = SessionLocal()
        error_id = f"test_err_{uuid.uuid4().hex[:8]}"
        try:
            err = models.SystemError(
                id=error_id,
                error_code=f"ERR_TEST_{uuid.uuid4().hex[:6].upper()}",
                error_type="CRASH_500",
                severity="CRITICAL",
                message="Lỗi thử nghiệm resolve",
                stack_trace="Traceback (most recent call last): ...",
                endpoint="GET /test",
                status="OPEN",
            )
            db.add(err)
            db.commit()
        finally:
            db.close()

        # Gọi API resolve
        res = client.patch(
            f"/admin/errors/{error_id}/resolve",
            headers=ADMIN_HEADERS,
            json={"resolved_note": "Đã sửa xong lỗi phân chia 0."},
        )
        assert res.status_code == 200
        resolved_data = res.json()
        assert resolved_data["status"] == "RESOLVED"
        assert resolved_data["resolved_by"] == ADMIN_USER_ID
        assert resolved_data["resolved_at"] is not None
        assert resolved_data["resolved_note"] == "Đã sửa xong lỗi phân chia 0."

        # Kiểm tra lại qua GET
        get_res = client.get(f"/admin/errors/{error_id}", headers=ADMIN_HEADERS)
        assert get_res.json()["status"] == "RESOLVED"
