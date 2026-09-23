import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timedelta, timezone

# Import middleware và các cấu hình JWT từ hệ thống
from middleware import JWTMiddleware, SECRET_KEY, ALGORITHM

# ==========================================
# THIẾT LẬP APP ẢO ĐỂ TEST MIDDLEWARE
# ==========================================
app = FastAPI()
# Gắn JWTMiddleware vào app ảo này để kiểm tra luồng chặn
app.add_middleware(JWTMiddleware)

# Tạo một route cần bảo mật (bắt buộc phải có token hợp lệ)
@app.get("/protected")
async def protected_route():
    return {"message": "Success"}

# Tạo một route công khai (không cần token, đã được khai báo trong public_paths của middleware)
@app.get("/health")
async def public_route():
    return {"status": "ok"}

# Khởi tạo TestClient để gửi các request giả lập
client = TestClient(app)

# ==========================================
# CÁC KỊCH BẢN KIỂM THỬ (TEST CASES)
# ==========================================

# 1. Kịch bản: Token hoàn toàn hợp lệ
def test_valid_token():
    # Tạo payload với thời gian hết hạn (exp) là 15 phút trong tương lai
    payload = {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Gửi request kèm token đúng chuẩn Bearer
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    
    # Kỳ vọng: HTTP 200 OK và lấy được data thành công
    assert response.status_code == 200
    assert response.json() == {"message": "Success"}

# 2. Kịch bản: Token đã hết hạn
def test_expired_token():
    # Tạo payload với thời gian hết hạn (exp) là 15 phút trong quá khứ
    payload = {"sub": "user123", "exp": datetime.now(timezone.utc) - timedelta(minutes=15)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    
    # Kỳ vọng: HTTP 401 Unauthorized do token không còn giá trị
    assert response.status_code == 401
    assert "Unauthorized:" in response.json()["detail"]

# 3. Kịch bản: Token bị sai chữ ký (Signature)
def test_invalid_signature_token():
    payload = {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    # Mã hóa token bằng một SECRET_KEY sai ("wrong-secret")
    token = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)
    
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    
    # Kỳ vọng: HTTP 401 Unauthorized do chữ ký không khớp với hệ thống
    assert response.status_code == 401
    assert "Unauthorized:" in response.json()["detail"]

# 4. Kịch bản: Truy cập route công khai không cần token
def test_public_route_no_token():
    # Gửi request đến /health mà không truyền header Authorization
    response = client.get("/health")
    
    # Kỳ vọng: HTTP 200 OK vì /health nằm trong danh sách public_paths
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# 5. Kịch bản: Không gửi header Authorization khi truy cập route bảo mật
def test_missing_auth_header():
    # Hoàn toàn không đính kèm header nào
    response = client.get("/protected")
    
    # Kỳ vọng: HTTP 401 Unauthorized vì thiếu token
    assert response.status_code == 401
    assert "Thiếu hoặc sai định dạng token" in response.json()["detail"]

# 6. Kịch bản: Header Authorization bị sai định dạng chữ "Bearer"
def test_invalid_auth_header_format():
    payload = {"sub": "user123", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    # Truyền "Token " thay vì "Bearer " theo đúng chuẩn
    response = client.get("/protected", headers={"Authorization": f"Token {token}"})
    
    # Kỳ vọng: HTTP 401 Unauthorized vì định dạng bắt buộc là "Bearer "
    assert response.status_code == 401
    assert "Thiếu hoặc sai định dạng token" in response.json()["detail"]

# 7. Kịch bản: Phiên bản của Token (version) không đúng quy định
def test_wrong_token_version():
    # Tạo payload có chứa trường "version" khác "1.0"
    payload = {
        "sub": "user123", 
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "version": "2.0"
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    
    # Kỳ vọng: HTTP 401 Unauthorized vì hệ thống chỉ chấp nhận version 1.0 (hoặc không có version)
    assert response.status_code == 401
    assert "Phiên bản mã thông báo không đạt chuẩn" in response.json()["detail"]
