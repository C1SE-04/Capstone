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


# ==============================================================================
# US 9.5 (Task T9.17): Middleware Tự Động Bắt Unhandled Exceptions & Ghi System Errors
# ==============================================================================

import uuid
import json
import re
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Any, Union, Optional
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import HTTPException as FastAPIHTTPException

SENSITIVE_FIELD_NAMES = {
    "password", "old_password", "new_password", "hashed_password",
    "token", "access_token", "refresh_token", "otp", "otp_code",
    "secret", "api_key", "credentials"
}


def mask_sensitive_payload(raw: Union[dict, list, str, Any]) -> str:
    """
    Lọc bỏ (mask) các trường nhạy cảm trong request_payload trước khi lưu DB
    theo đúng yêu cầu bảo mật của US 9.5.
    """
    def _mask_obj(obj: Any) -> Any:
        if isinstance(obj, dict):
            masked = {}
            for k, v in obj.items():
                if isinstance(k, str) and k.lower() in SENSITIVE_FIELD_NAMES:
                    masked[k] = "***MASKED***"
                elif isinstance(v, (dict, list)):
                    masked[k] = _mask_obj(v)
                else:
                    masked[k] = v
            return masked
        elif isinstance(obj, list):
            return [_mask_obj(item) for item in obj]
        return obj

    if isinstance(raw, (dict, list)):
        return json.dumps(_mask_obj(raw), ensure_ascii=False)

    if isinstance(raw, (str, bytes)):
        text_val = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        text_val = text_val.strip()
        if not text_val:
            return ""
        # Thử parse JSON
        try:
            parsed = json.loads(text_val)
            return json.dumps(_mask_obj(parsed), ensure_ascii=False)
        except Exception:
            # Fallback regex mask chuỗi thông thường (VD: form-urlencoded hay query string)
            masked_str = re.sub(
                r'((?:password|token|otp|secret)=)[^&\s]+',
                r'\g<1>***MASKED***',
                text_val,
                flags=re.IGNORECASE
            )
            return masked_str

    return str(raw)


def extract_user_from_request(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Trích xuất User ID và Email từ request an toàn:
    1. Kiểm tra request.state.user nếu đã qua xác thực.
    2. Bóc tách token từ Authorization header (giải mã an toàn).
    """
    user_state = getattr(request.state, "user", None)
    if isinstance(user_state, dict):
        return (
            str(user_state.get("sub") or user_state.get("id")) if (user_state.get("sub") or user_state.get("id")) else None,
            user_state.get("email")
        )

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            uid = payload.get("sub") or payload.get("id")
            email = payload.get("email")
            return (str(uid) if uid else None, email)
        except Exception:
            pass

    return None, None


class SystemErrorMiddleware(BaseHTTPMiddleware):
    """
    Middleware FastAPI tự động bắt mọi Unhandled Exception (Crash 500, Timeout, SMTP)
    và lưu vết vào bảng system_errors (US 9.5 - T9.17).

    Nguyên tắc hoạt động:
      1. Cho phép request chạy bình thường; bọc try-except toàn diện.
      2. Nếu bắt được lỗi unhandled (hoặc HTTP 500):
         - Xác định loại lỗi: CRASH_500, AI_TIMEOUT, hoặc SMTP_ERROR.
         - Xác định mức độ: CRITICAL (Crash), WARNING (Timeout/SMTP).
         - Trích xuất user context (user_id thực tế hoặc anonymous).
         - Mask dữ liệu nhạy cảm trong request_payload.
         - Ghi vào bảng system_errors an toàn (không làm sập app nếu DB lỗi).
         - Trả về JSON 500 có mã lỗi error_code tra cứu.
      3. Bỏ qua các client error chuẩn (HTTP 4xx như 400, 401, 404, 422).
    """
    async def dispatch(self, request: Request, call_next):
        # Đọc và cache body an toàn để route downstream vẫn nhận được stream
        body_bytes = b""
        try:
            body_bytes = await request.body()
            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request = Request(request.scope, receive=receive)
        except Exception:
            pass

        try:
            response = await call_next(request)
            return response
        except (StarletteHTTPException, FastAPIHTTPException) as http_exc:
            # Nếu là client error (4xx: 400, 401, 403, 404, 422), không tính là crash hệ thống
            if http_exc.status_code < 500:
                raise http_exc

            # Nếu là lỗi máy chủ 500 ném qua HTTPException -> ghi nhận sự cố
            self._log_exception_to_db(request, http_exc, body_bytes)
            raise http_exc
        except Exception as exc:
            # Bắt mọi unhandled exception (Crash 500, Timeout, v.v.)
            error_code, error_type = self._log_exception_to_db(request, exc, body_bytes)

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal Server Error",
                    "error_code": error_code,
                    "error_type": error_type,
                    "message": "Đã xảy ra sự cố hệ thống. Mã lỗi đã được ghi nhận vào Admin Incident Hub để khắc phục.",
                },
            )

    def _log_exception_to_db(self, request: Request, exc: Exception, body_bytes: bytes) -> tuple[str, str]:
        error_id = uuid.uuid4().hex
        exc_str = str(exc)
        exc_name = type(exc).__name__

        # Phân loại lỗi và mức độ nghiêm trọng theo AC 9.5.4
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timeout" in exc_str.lower():
            error_type = "AI_TIMEOUT"
            severity = "WARNING"
            error_code = f"ERR_TIMEOUT_{error_id[:8].upper()}"
            summary_msg = f"AI / Request Timeout: {exc_str or exc_name}"
        elif "smtp" in exc_str.lower() or "mail" in exc_name.lower():
            error_type = "SMTP_ERROR"
            severity = "WARNING"
            error_code = f"ERR_SMTP_{error_id[:8].upper()}"
            summary_msg = f"SMTP Email Error: {exc_str or exc_name}"
        else:
            error_type = "CRASH_500"
            severity = "CRITICAL"
            error_code = f"ERR_500_{error_id[:8].upper()}"
            summary_msg = f"Unhandled Exception ({exc_name}): {exc_str or 'Internal Server Error'}"

        stack_trace = traceback.format_exc()
        endpoint = f"{request.method} {request.url.path}"
        user_id, user_email = extract_user_from_request(request)

        masked_payload_str = None
        if body_bytes:
            try:
                masked_payload_str = mask_sensitive_payload(body_bytes)
            except Exception:
                masked_payload_str = None

        # Ghi DB an toàn tuyệt đối
        try:
            from database import SessionLocal
            import models

            db = SessionLocal()
            try:
                valid_user_id = None
                if user_id:
                    user_exists = db.query(models.User.id).filter(models.User.id == str(user_id)).first()
                    if user_exists:
                        valid_user_id = str(user_id)
                        if not user_email:
                            u_email = db.query(models.User.email).filter(models.User.id == str(user_id)).first()
                            if u_email:
                                user_email = u_email[0]

                record = models.SystemError(
                    id=error_id,
                    error_code=error_code,
                    error_type=error_type,
                    severity=severity,
                    message=summary_msg,
                    stack_trace=stack_trace,
                    endpoint=endpoint,
                    request_payload=masked_payload_str,
                    user_id=valid_user_id,
                    user_email=user_email,
                    status="OPEN",
                )
                db.add(record)
                db.commit()
                print(f"[SystemErrorMiddleware] Đã tự động ghi nhận sự cố {error_code} ({error_type} - {severity}) vào DB.")
            finally:
                db.close()
        except Exception as db_err:
            print(f"[SystemErrorMiddleware] CẢNH BÁO: Lỗi khi lưu sự cố vào DB: {db_err}")

        return error_code, error_type


# ==============================================================================
# US 10.2 (Tasks T10.2.1 - T10.2.2): Telemetry & Observability Exports
# ==============================================================================
from middleware.telemetry_middleware import (
    TelemetryMiddleware,
    telemetry_queue,
    increment_sse_session,
    decrement_sse_session,
    get_active_sse_sessions,
)
from middleware.gemini_telemetry import stream_with_telemetry, generate_with_telemetry



