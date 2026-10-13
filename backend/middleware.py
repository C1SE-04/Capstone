import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt, JWTError
from dotenv import load_dotenv

import auth

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", getattr(auth, "SECRET_KEY", "06KARAOKE-10-OTOKE"))
ALGORITHM = getattr(auth, "ALGORITHM", os.getenv("ALGORITHM", "HS256"))


class ChatSessionVersionMiddleware(BaseHTTPMiddleware):
    """
    US 6.2 - Task T6.11: Middleware API /chat
    Kiểm tra session_version trong JWT token với DB NeonDB.
    Nếu học sinh đổi lớp ở tab khác -> session_version trong DB tăng lên.
    Mỗi request chat gửi từ tab cũ có session_version lệch với DB ->
    Trả mã 401 kèm body { "error": "SESSION_STALE" }.
    Frontend sẽ bắt cờ này để tự gọi update() của NextAuth refresh session mà không đăng xuất.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Chỉ kiểm tra đối với các API thuộc luồng chat (/chat, /chat/orchestrator, /chat/comprehension, v.v.)
        if path == "/chat" or path.startswith("/chat/"):
            # Bỏ qua CORS preflight
            if request.method == "OPTIONS":
                return await call_next(request)

            auth_header = request.headers.get("Authorization")

            # Nếu có Authorization header (học sinh đăng nhập)
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()
                try:
                    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                    user_id = payload.get("sub")
                    token_version = payload.get("session_version")

                    if user_id:
                        from database import SessionLocal
                        import models

                        db = SessionLocal()
                        try:
                            user = db.query(models.User).filter(models.User.id == str(user_id)).first()
                            if user:
                                db_version = getattr(user, "session_version", 1) or 1
                                # Nếu token không có session_version hoặc bị lệch với DB -> SESSION_STALE
                                if token_version is None or int(token_version) != int(db_version):
                                    return JSONResponse(
                                        status_code=401,
                                        content={"error": "SESSION_STALE"}
                                    )
                        finally:
                            db.close()

                    # Lưu payload vào request.state để route handler có thể dùng nếu cần
                    request.state.user = payload

                except JWTError:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Unauthorized: Token không hợp lệ hoặc đã hết hạn"}
                    )

        # Cho phép request đi tiếp nếu token hợp lệ hoặc nếu là guest (không có Authorization header)
        response = await call_next(request)
        return response


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

            # Task T6.11: Kiểm tra session_version nếu là route chat
            path = request.url.path
            if path == "/chat" or path.startswith("/chat/"):
                token_session_version = payload.get("session_version")
                user_id = payload.get("sub")
                if user_id:
                    from database import SessionLocal
                    import models
                    db = SessionLocal()
                    try:
                        user = db.query(models.User).filter(models.User.id == str(user_id)).first()
                        if user:
                            db_version = getattr(user, "session_version", 1) or 1
                            if token_session_version is None or int(token_session_version) != int(db_version):
                                return JSONResponse(
                                    status_code=401,
                                    content={"error": "SESSION_STALE"}
                                )
                    finally:
                        db.close()
                
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
