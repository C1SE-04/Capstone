import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Bỏ qua kiểm tra JWT đối với các route công khai
        public_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in public_paths:
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Thiếu hoặc sai định dạng token"}
            )
            
        token = auth_header.split(" ")[1]
        
        try:
            # Giải mã token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Kiểm tra phiên bản mã thông báo
            # Logic: Nếu có trường 'version' trong payload và không phải là '1.0' -> Lỗi 401
            token_version = payload.get("version")
            if token_version and token_version != "1.0":
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Phiên bản mã thông báo không đạt chuẩn"}
                )
                
            # Lưu payload vào request.state để các route khác có thể sử dụng (ví dụ: request.state.user)
            request.state.user = payload
            
        except JWTError as e:
            # Bắt lỗi token không hợp lệ, sai chữ ký, hoặc đã hết hạn
            return JSONResponse(
                status_code=401,
                content={"detail": f"Unauthorized: Mã thông báo không hợp lệ - {str(e)}"}
            )
            
        # Tiếp tục xử lý request nếu token hợp lệ
        response = await call_next(request)
        return response
