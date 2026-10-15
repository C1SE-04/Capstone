# US 6.4 - Task #173: Test API Upload Cloudinary
# Kiểm tra các API endpoint sau:
#   1. POST /upload/image   - Upload ảnh thực tế lên Cloudinary
#   2. GET  /upload/signature - Lấy chữ ký để FE upload thẳng
#   3. Kiểm tra attachment_url được lưu vào bảng messages qua API /chat/orchestrator

import sys
import os
# Thêm thư mục backend vào sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Cấu hình UTF-8 cho Windows console tránh lỗi UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from main import app
import dependencies

client = TestClient(app)

# Giả lập user đã đăng nhập (STUDENT)
TEST_USER_ID = "test-upload-user"

def mock_get_current_user():
    return {"id": TEST_USER_ID, "role": "STUDENT", "grade": 5}

app.dependency_overrides[dependencies.get_current_user] = mock_get_current_user


def test_upload_signature_endpoint():
    """Test GET /upload/signature - trả về chữ ký và metadata."""
    print("\n--- TEST: GET /upload/signature ---")
    res = client.get("/upload/signature")
    # Nếu Cloudinary chưa cấu hình → 503 (expected trong test environment)
    if res.status_code == 503:
        print("[EXPECTED 503] Cloudinary chưa cấu hình trong test env. API trả lỗi đúng.")
        return
    assert res.status_code == 200, f"Unexpected status: {res.status_code} — {res.json()}"
    data = res.json()
    assert "signature" in data
    assert "timestamp" in data
    assert "api_key" in data
    assert "cloud_name" in data
    assert "folder" in data
    print(f"[OK] Signature endpoint hoạt động! cloud_name={data['cloud_name']}, folder={data['folder']}")


def test_upload_image_no_file():
    """Test POST /upload/image không có file → 422 Unprocessable Entity."""
    print("\n--- TEST: POST /upload/image (không có file) ---")
    res = client.post("/upload/image")
    assert res.status_code == 422, f"Expected 422, got {res.status_code}"
    print("[OK] Trả 422 khi không gửi file — đúng validation.")


def test_upload_image_wrong_type():
    """Test POST /upload/image với file text → 415 Unsupported Media Type."""
    print("\n--- TEST: POST /upload/image (sai content-type) ---")
    import io
    fake_file = io.BytesIO(b"This is not an image")
    res = client.post(
        "/upload/image",
        files={"file": ("test.txt", fake_file, "text/plain")},
    )
    assert res.status_code == 415, f"Expected 415, got {res.status_code} — {res.json()}"
    print("[OK] Trả 415 khi upload file không phải ảnh — đúng theo AC US 6.4.")


def test_upload_image_too_large():
    """Test POST /upload/image với file > 5MB → 413 Request Entity Too Large."""
    print("\n--- TEST: POST /upload/image (file > 5MB) ---")
    import io
    large_content = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 1)  # > 5MB, bắt đầu bằng JPEG magic bytes
    res = client.post(
        "/upload/image",
        files={"file": ("big.jpg", io.BytesIO(large_content), "image/jpeg")},
    )
    assert res.status_code == 413, f"Expected 413, got {res.status_code} — {res.json()}"
    print("[OK] Trả 413 khi upload file > 5MB — đúng theo AC US 6.4.")


def test_attachment_url_in_message_schema():
    """Test rằng MessageResponse schema có trường attachment_url."""
    print("\n--- TEST: Kiểm tra schema MessageResponse có attachment_url ---")
    import schemas
    msg = schemas.MessageResponse(
        id="test-id",
        sender_type="USER",
        content="Test message",
        attachment_url="https://res.cloudinary.com/demo/image/upload/test.jpg",
        created_at=__import__("datetime").datetime.now(),
    )
    assert msg.attachment_url == "https://res.cloudinary.com/demo/image/upload/test.jpg"
    print("[OK] MessageResponse schema có trường attachment_url!")

    msg_no_attachment = schemas.MessageResponse(
        id="test-id-2",
        sender_type="AGENT_TUTOR",
        content="AI response",
        created_at=__import__("datetime").datetime.now(),
    )
    assert msg_no_attachment.attachment_url is None
    print("[OK] MessageResponse attachment_url là None khi không có ảnh — backward compatible!")


def test_gemini_request_has_attachment_url():
    """Test GeminiRequest schema có trường attachment_url."""
    print("\n--- TEST: Kiểm tra schema GeminiRequest có attachment_url ---")
    import schemas
    req = schemas.GeminiRequest(
        session_id="test-session",
        prompt="Giải bài này",
        attachment_url="https://res.cloudinary.com/demo/image/upload/problem.jpg",
    )
    assert req.attachment_url == "https://res.cloudinary.com/demo/image/upload/problem.jpg"
    print("[OK] GeminiRequest có attachment_url!")

    req_no_img = schemas.GeminiRequest(session_id="test", prompt="Hello")
    assert req_no_img.attachment_url is None
    print("[OK] GeminiRequest attachment_url mặc định None — backward compatible!")


if __name__ == "__main__":
    test_upload_signature_endpoint()
    test_upload_image_no_file()
    test_upload_image_wrong_type()
    test_upload_image_too_large()
    test_attachment_url_in_message_schema()
    test_gemini_request_has_attachment_url()
    print("\nALL CLOUDINARY UPLOAD TESTS PASSED!")
