import urllib.request
import urllib.error
import json
import os
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
URL = "http://127.0.0.1:8000/api/protected"

def make_request(token=None):
    req = urllib.request.Request(URL)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    
    try:
        response = urllib.request.urlopen(req)
        body = response.read().decode('utf-8')
        return response.status, json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        return e.code, json.loads(body)
    except Exception as e:
        return 0, str(e)

print("--- BẮT ĐẦU TEST ---")

# 1. Không có Token
print("\n[Test 1] Không gửi Token:")
status, data = make_request(token=None)
print(f"Status Code: {status}")
print(f"Response: {data}")

# 2. Token sai phiên bản (ví dụ: version 0.9)
print("\n[Test 2] Gửi Token sai phiên bản (version = 0.9):")
token_invalid_version = jwt.encode({"sub": "user_123", "version": "0.9"}, SECRET_KEY, algorithm=ALGORITHM)
status, data = make_request(token=token_invalid_version)
print(f"Status Code: {status}")
print(f"Response: {data}")

# 3. Token hợp lệ (version 1.0)
print("\n[Test 3] Gửi Token hợp lệ (version = 1.0):")
token_valid = jwt.encode({"sub": "user_123", "version": "1.0", "name": "Nguyễn Văn A"}, SECRET_KEY, algorithm=ALGORITHM)
status, data = make_request(token=token_valid)
print(f"Status Code: {status}")
print(f"Response: {data}")

print("\n--- KẾT THÚC TEST ---")
