"""
========================================================================================
File: backend/test/test_us11_5_contact_hub.py
Sprint 11 - US 11.5: Feedback & Contact Hub (Trang Liên Hệ & Đóng Góp Ý Kiến)
========================================================================================
Kiểm thử tự động toàn diện:
  1. POST /api/contact/submit: Tiếp nhận biểu mẫu, lưu DB contact_requests
  2. Bắn Webhook tự động tới Discord / Telegram, phân loại tag Dev vs PM
  3. Inline & Backend Validation: Họ tên, Email, Content (5-500 ký tự)
  4. POST /api/contact/upload-attachment: Chặn file sai định dạng, chặn file > 5MB
  5. GET & PATCH /api/contact/requests: Quản trị viên duyệt và cập nhật trạng thái
========================================================================================
"""

import io
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import SessionLocal
import models
import auth
from services.webhook_service import get_sent_webhooks, clear_sent_webhooks, resolve_team_tag


@pytest.fixture(autouse=True)
def clean_webhook_logs():
    clear_sent_webhooks()
    yield
    clear_sent_webhooks()


@pytest.fixture
def test_admin_user():
    """Tạo user Quản trị viên phục vụ kiểm thử API Admin Contact."""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    admin_id = f"test-admin-{suffix}"
    admin_user = models.User(
        id=admin_id,
        username=f"admin_{suffix}",
        email=f"admin_{suffix}@socratickid.edu.vn",
        hashed_password=auth.hash_password("AdminPass123"),
        role="ADMIN",
    )
    db.add(admin_user)
    db.commit()
    db.close()

    token = auth.create_access_token({"sub": admin_id, "role": "ADMIN", "session_version": 1})
    yield {"admin_id": admin_id, "token": token}

    db = SessionLocal()
    db.query(models.User).filter_by(id=admin_id).delete()
    db.commit()
    db.close()


def test_contact_submit_success_and_webhook_pm_tag():
    """
    [AC6]: Gửi form thành công (Góp ý tính năng) -> Lưu DB và bắn Webhook gắn tag PM.
    """
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:6]
    test_email = f"user_{suffix}@gmail.com"

    payload = {
        "fullName": "Nguyễn Văn An",
        "email": test_email,
        "category": "FEATURE_REQUEST",
        "message": "Em muốn hệ thống có thêm tính năng chia sẻ bảng thành tích bài tập cho bố mẹ xem ạ!",
        "attachment_urls": ["https://res.cloudinary.com/demo/image/upload/sample1.png"],
        "recaptcha_score": 0.95,
    }

    res = client.post("/api/contact/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Cảm ơn bạn" in data["message"]
    request_id = data["request_id"]

    # 1. Kiểm tra lưu dữ liệu vào database
    db = SessionLocal()
    saved = db.query(models.ContactRequest).filter_by(id=request_id).first()
    assert saved is not None
    assert saved.full_name == "Nguyễn Văn An"
    assert saved.email == test_email.lower()
    assert saved.topic == "FEATURE"
    assert saved.status == "PENDING"
    assert float(saved.recaptcha_score) == 0.95
    assert len(saved.attachment_urls) == 1
    db.delete(saved)
    db.commit()
    db.close()

    # 2. Kiểm tra bắn Webhook phân loại tag PM
    webhooks = get_sent_webhooks()
    assert len(webhooks) == 1
    wh = webhooks[0]
    assert wh["team"] == "PM"
    assert "ProductManager" in wh["tag_discord"]
    assert "#PM" in wh["tag_telegram"]


def test_contact_submit_bug_report_webhook_dev_tag():
    """
    [AC6]: Gửi form Báo lỗi (BUG_REPORT) -> Tự động bắn Webhook gắn tag Dev (@DevTeam / #Dev).
    """
    client = TestClient(app)
    suffix = uuid.uuid4().hex[:6]
    test_email = f"tester_{suffix}@socratickid.edu.vn"

    payload = {
        "full_name": "Trần Thị Bé",
        "email": test_email,
        "topic": "BUG_REPORT",
        "content": "Em bị lỗi đứng màn hình khi bấm nút xem gợi ý ở câu hỏi số 3 môn Toán lớp 5.",
        "attachment_urls": [],
    }

    res = client.post("/api/contact/submit", json=payload)
    assert res.status_code == 200
    request_id = res.json()["request_id"]

    # Kiểm tra Webhook tag Dev
    webhooks = get_sent_webhooks()
    assert len(webhooks) == 1
    wh = webhooks[0]
    assert wh["team"] == "DEV"
    assert "DevTeam" in wh["tag_discord"]
    assert "#Dev" in wh["tag_telegram"]

    # Dọn dẹp
    db = SessionLocal()
    db.query(models.ContactRequest).filter_by(id=request_id).delete()
    db.commit()
    db.close()


def test_contact_submit_validation_errors():
    """
    [AC3]: Kiểm tra validation:
    - Để trống họ tên -> 400
    - Nội dung < 5 ký tự -> 400
    - Nội dung > 500 ký tự -> 400
    - Email sai cú pháp -> 422
    """
    client = TestClient(app)

    # 1. Để trống họ tên
    r1 = client.post(
        "/api/contact/submit",
        json={"fullName": "", "email": "test@gmail.com", "category": "OTHER", "message": "Nội dung hợp lệ"}
    )
    assert r1.status_code == 400
    assert "họ và tên" in r1.json()["detail"]

    # 2. Nội dung quá ngắn (< 5 ký tự)
    r2 = client.post(
        "/api/contact/submit",
        json={"fullName": "Lê Văn C", "email": "test@gmail.com", "category": "OTHER", "message": "Alo"}
    )
    assert r2.status_code == 400
    assert "ít nhất 5 ký tự" in r2.json()["detail"]

    # 3. Nội dung vượt quá 500 ký tự (0/500 theo AC3)
    long_message = "A" * 501
    r3 = client.post(
        "/api/contact/submit",
        json={"fullName": "Lê Văn C", "email": "test@gmail.com", "category": "OTHER", "message": long_message}
    )
    assert r3.status_code == 400
    assert "vượt quá 500 ký tự" in r3.json()["detail"]

    # 4. Email không hợp lệ
    r4 = client.post(
        "/api/contact/submit",
        json={"fullName": "Lê Văn C", "email": "not-an-email", "category": "OTHER", "message": "Nội dung hợp lệ"}
    )
    assert r4.status_code == 422


def test_contact_upload_attachment_size_and_type_guards():
    """
    [AC4]:
    - Chặn file không phải ảnh (PDF, EXE...) -> HTTP 400
    - Chặn file ảnh vượt quá 5MB -> HTTP 400
    - File hợp lệ -> Thành công HTTP 200
    """
    client = TestClient(app)

    # 1. File không phải ảnh (application/pdf)
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
    r1 = client.post(
        "/api/contact/upload-attachment",
        files={"file": ("document.pdf", fake_pdf, "application/pdf")}
    )
    assert r1.status_code == 400
    assert "không hợp lệ" in r1.json()["detail"]

    # 2. File ảnh quá lớn (> 5MB)
    oversized_bytes = b"0" * (5 * 1024 * 1024 + 100)
    fake_big_img = io.BytesIO(oversized_bytes)
    r2 = client.post(
        "/api/contact/upload-attachment",
        files={"file": ("huge_photo.jpg", fake_big_img, "image/jpeg")}
    )
    assert r2.status_code == 400
    assert "vượt quá giới hạn cho phép (tối đa 5MB)" in r2.json()["detail"]

    # 3. File ảnh hợp lệ (PNG nhỏ)
    valid_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")
    r3 = client.post(
        "/api/contact/upload-attachment",
        files={"file": ("screenshot.png", valid_png, "image/png")}
    )
    assert r3.status_code == 200
    data = r3.json()
    assert data["success"] is True
    assert "http" in data["url"]


def test_admin_get_and_update_contact_request(test_admin_user):
    """
    Kiểm tra quyền quản trị:
    - User thường / Chưa đăng nhập không thể xem danh sách contact (401/403).
    - Admin xem được danh sách và cập nhật trạng thái từ PENDING -> RESOLVED.
    """
    client = TestClient(app)
    admin_token = test_admin_user["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Tạo một phản hồi mẫu trong DB
    db = SessionLocal()
    sample_id = uuid.uuid4().hex
    contact = models.ContactRequest(
        id=sample_id,
        full_name="Người Dùng Thử",
        email="guest_feedback@gmail.com",
        role="GUEST",
        topic="PEDAGOGY",
        content="Cho em hỏi về phương pháp gợi mở của thầy Socratic ạ.",
        status="PENDING",
    )
    db.add(contact)
    db.commit()
    db.close()

    # 2. Người dùng không có quyền truy cập -> Bị chặn 401/403
    r_unauth = client.get("/api/contact/requests")
    assert r_unauth.status_code == 401

    # 3. Admin truy cập -> Thành công 200
    r_admin = client.get("/api/contact/requests", headers=admin_headers)
    assert r_admin.status_code == 200
    items = r_admin.json()
    assert any(item["id"] == sample_id for item in items)

    # 4. Admin cập nhật trạng thái sang RESOLVED
    r_patch = client.patch(
        f"/api/contact/requests/{sample_id}/status",
        json={"status": "RESOLVED"},
        headers=admin_headers
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["status"] == "RESOLVED"

    # Kiểm tra trong DB
    db = SessionLocal()
    updated = db.query(models.ContactRequest).filter_by(id=sample_id).first()
    assert updated.status == "RESOLVED"
    db.delete(updated)
    db.commit()
    db.close()
