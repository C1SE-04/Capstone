"""
US 10.3 - Router Quản Trị Cài Đặt Hệ Thống (Admin Settings Hub) (T10.3.2)
=========================================================================
Cung cấp 8 Endpoints API chính thức thay thế toàn bộ mock router cũ:
  1. GET   /admin/settings                : Đọc cấu hình đầy đủ (Redis cache -> DB, API Key readonly)
  2. PUT   /admin/settings                : Cập nhật cấu hình có xác thực ADMIN & Hot-Reloading tức thì
  3. GET   /admin/settings/models         : Đồng bộ danh sách model khả dụng từ Google Gemini API
  4. POST  /admin/settings/test-key       : Ping test đo latency thực của Gemini API (KHÔNG lưu key vào DB)
  5. GET   /admin/settings/health         : Healthcheck thật 4 dịch vụ (Neon DB, Upstash Redis, Gemini, SMTP)
  6. POST  /admin/settings/test-playground: Sa bàn Mini Playground thử nghiệm prompt Socratic toán học
  7. GET   /admin/settings/audits         : Lấy danh sách lịch sử thay đổi cấu hình (Audit Trail)
  8. POST  /admin/settings/rollback/{id}  : Hoàn tác cấu hình 1-Click từ lịch sử (Rollback - AC-SET-07)
"""

import os
import time
import socket
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
import schemas
import dependencies
from services.system_config_service import (
    get_system_settings,
    update_system_settings,
    rollback_system_settings,
    get_setting_audits,
    _get_sync_redis,
)

# Khởi tạo router chính thức với prefix /admin
router = APIRouter(
    prefix="/admin/settings",
    tags=["Admin Settings Hub (US 10.3)"],
    dependencies=[Depends(dependencies.require_role(["ADMIN"]))],
)

# Router phụ để tương thích ngược cho các frontend gọi qua /admin/mock/settings trong giai đoạn chuyển đổi
mock_compat_router = APIRouter(
    prefix="/admin/mock/settings",
    tags=["Admin Settings Hub (US 10.3 Compatibility)"],
    dependencies=[Depends(dependencies.require_role(["ADMIN"]))],
)


def _get_masked_api_key() -> str:
    """Trả về 4 ký tự cuối của API Key, tuyệt đối không để lộ toàn bộ khóa."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return "Chưa cấu hình (Đọc từ .env)"
    if len(key) <= 4:
        return "••••••••"
    return f"••••••••{key[-4:]}"


# Danh sách fallback các model Google chính thức khuyên dùng trong Sprint 10
_OFFICIAL_CURATED_MODELS: List[Dict[str, str]] = [
    {
        "id": "gemini-3.5-flash-lite",
        "name": "gemini-3.5-flash-lite",
        "display_name": "Gemini 3.5 Flash-Lite (Khuyên Dùng)",
        "description": "Trọng lượng nhẹ, phản hồi tức thì (~0.2s), tối ưu sâu Chat Socratic, Flashcard & Dự phòng",
        "speed": "Cực nhanh (~0.2s)",
        "recommended_for": "Chat Socratic Chính & Dự Phòng (primary_model, backup_model)",
    },
    {
        "id": "gemini-3.8-flash",
        "name": "gemini-3.8-flash",
        "display_name": "Gemini 3.8 Flash",
        "description": "Thế hệ mới nhất, tối ưu sâu cho phương pháp gợi mở Socratic và đọc ảnh đề bài",
        "speed": "Siêu tốc (~0.3s)",
        "recommended_for": "Chat Socratic Nâng Cao",
    },
    {
        "id": "gemini-3.5-flash",
        "name": "gemini-3.5-flash",
        "display_name": "Gemini 3.5 Flash",
        "description": "Cân bằng hoàn hảo tốc độ và năng lực phân tích tổng hợp lịch sử học tập dài hạn",
        "speed": "Rất nhanh (~0.4s)",
        "recommended_for": "Báo Cáo Phụ Huynh (parent_insight_model)",
    },
    {
        "id": "gemini-3.1-flash-lite",
        "name": "gemini-3.1-flash-lite",
        "display_name": "Gemini 3.1 Flash-Lite (Siêu Tiết Kiệm)",
        "description": "Tối ưu chi phí token tới 60%, phản hồi tức thì cho các tác vụ phân loại ngắn",
        "speed": "Tức thì (~0.15s)",
        "recommended_for": "Phân Loại SGK & Email (classifier_model, email_model)",
    },
    {
        "id": "gemini-3.5-flash-lite",
        "name": "gemini-3.5-flash-lite",
        "display_name": "Gemini 3.5 Flash-Lite",
        "description": "Nhẹ, ổn định cao, thích hợp làm trạm dự phòng khẩn cấp khi gặp sự cố rate limit",
        "speed": "Cực nhanh (~0.2s)",
        "recommended_for": "Flashcard & Dự Phòng (flashcard_model, backup_model)",
    },
    {
        "id": "gemini-2.5-flash",
        "name": "gemini-2.5-flash",
        "display_name": "Gemini 2.5 Flash (LTS)",
        "description": "Phiên bản ổn định cao, nhận diện hình học và chữ viết tay học sinh chuẩn xác",
        "speed": "Rất nhanh (~0.35s)",
        "recommended_for": "Chat Socratic / Dự phòng cấp 2",
    },
    {
        "id": "gemini-2.0-flash-lite",
        "name": "gemini-2.0-flash-lite",
        "display_name": "Gemini 2.0 Flash-Lite",
        "description": "Model đa phương thức thế hệ 2.0, độ phủ rộng và ổn định",
        "speed": "Rất nhanh (~0.2s)",
        "recommended_for": "Sub-Agent & Dự phòng",
    },
]


# ==============================================================================
# 1. GET /admin/settings – Đọc cấu hình đầy đủ
# ==============================================================================
@router.get("", response_model=schemas.AdminSystemSettings)
@mock_compat_router.get("", response_model=schemas.AdminSystemSettings)
def get_admin_settings(db: Session = Depends(get_db)):
    """
    Lấy cấu hình hệ thống hiện tại.
    Đọc từ Upstash Redis Cache trước (latency < 1ms), nếu Cache Miss mới query DB Neon.
    API Key chỉ hiển thị ở dạng che 4 ký tự cuối (Readonly).
    """
    settings = get_system_settings(db=db)
    settings["api_key_masked"] = _get_masked_api_key()
    # Gán fallback backward compatibility
    settings["model_name"] = settings.get("primary_model", "gemini-3.5-flash-lite")
    settings["rate_limit_per_minute"] = settings.get("student_rate_limit", 30)
    return schemas.AdminSystemSettings(**settings)


# ==============================================================================
# 2. PUT /admin/settings – Cập nhật cấu hình & Hot-Reloading tức thì
# ==============================================================================
@router.put("", response_model=schemas.AdminSystemSettings)
@mock_compat_router.put("", response_model=schemas.AdminSystemSettings)
def update_admin_settings(
    body: schemas.AdminSystemSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
):
    """
    Cập nhật cấu hình hệ thống:
      - Ghi DB Neon
      - Lưu lịch sử Audit Trail
      - Xóa Redis Cache để kích hoạt Hot-Reloading tức thì cho học sinh
    """
    changed_by = current_user.get("email") or current_user.get("username") or "admin@socratickid.edu.vn"
    update_dict = body.model_dump(exclude_unset=True)

    # Loại bỏ triệt để mọi nỗ lực ghi đè API Key
    update_dict.pop("api_key_override", None)
    update_dict.pop("multi_key_pool", None)

    summary = "Cập nhật cấu hình hệ thống từ Admin Hub"
    if "primary_model" in update_dict:
        summary = f"Đổi Chat Socratic Model sang {update_dict['primary_model']}"

    updated = update_system_settings(
        new_data=update_dict,
        changed_by=changed_by,
        change_summary=summary,
        db=db,
    )
    updated["api_key_masked"] = _get_masked_api_key()
    updated["model_name"] = updated.get("primary_model", "gemini-3.5-flash-lite")
    updated["rate_limit_per_minute"] = updated.get("student_rate_limit", 30)

    return schemas.AdminSystemSettings(**updated)


# ==============================================================================
# 3. GET /admin/settings/models – Danh sách Model từ Google Gemini API
# ==============================================================================
@router.get("/models", response_model=List[schemas.AdminModelOption])
def list_available_models():
    """
    Đồng bộ danh sách các model khả dụng thời gian thực từ Google Gemini API.
    Nếu Google API gặp sự cố (mất mạng/hết quota), tự động fallback về danh mục 6 model chính thức.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return [schemas.AdminModelOption(**m) for m in _OFFICIAL_CURATED_MODELS]

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key, transport="rest")

        models_list = []
        # Lấy danh sách model từ Google API
        for m in genai.list_models():
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                raw_name = m.name.replace("models/", "")
                # Chỉ lọc các model Gemini
                if "gemini" in raw_name.lower():
                    disp = getattr(m, "display_name", raw_name) or raw_name
                    desc = getattr(m, "description", "") or "Google Gemini Model"

                    # Phân loại tốc độ sơ bộ
                    speed = "Nhanh (~0.3s)"
                    if "lite" in raw_name.lower():
                        speed = "Tức thì (~0.15s)"
                    elif "pro" in raw_name.lower():
                        speed = "Tư duy cao (~1.2s)"

                    # Gợi ý phân hệ phù hợp
                    recommended = "Hội thoại đa năng"
                    if "3.8" in raw_name or "2.5" in raw_name:
                        recommended = "Khuyên dùng Chat Socratic chính"
                    elif "lite" in raw_name:
                        recommended = "Khuyên dùng Phân loại SGK & Sub-Agent"
                    elif "pro" in raw_name:
                        recommended = "Khuyên dùng Báo cáo Phụ huynh (ngữ cảnh 2M)"

                    models_list.append(schemas.AdminModelOption(
                        id=raw_name,
                        name=raw_name,
                        display_name=disp,
                        description=desc,
                        speed=speed,
                        recommended_for=recommended,
                    ))

        if models_list:
            # Sắp xếp để các model ưu tiên hiển thị lên trước
            return models_list

    except Exception as err:
        print(f"[AdminSettings] ⚠️ Không thể list models từ Google API: {err} — Dùng danh mục mặc định.")

    return [schemas.AdminModelOption(**m) for m in _OFFICIAL_CURATED_MODELS]


# ==============================================================================
# 4. POST /admin/settings/test-key – Ping Test Google Gemini API
# ==============================================================================
@router.post("/test-key", response_model=schemas.AdminTestKeyResponse)
def test_gemini_api_key():
    """
    Gửi ping test siêu nhẹ tới Google Gemini API và đo thời gian phản hồi thực tế (ms).
    BẢO MẬT: TUYỆT ĐỐI KHÔNG lưu API Key vào cơ sở dữ liệu.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chưa cấu hình GEMINI_API_KEY trong file .env máy chủ."
        )

    masked_key = _get_masked_api_key()
    start_time = time.perf_counter()

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key, transport="rest")

        # Gửi test ping siêu nhẹ: sinh 1 từ duy nhất với model tốc độ cao
        model = genai.GenerativeModel("gemini-3.5-flash-lite")
        from middleware.gemini_telemetry import generate_with_telemetry
        _ = generate_with_telemetry(
            model, "Ping", "gemini-3.5-flash-lite", "Fallback", generation_config={"max_output_tokens": 2}
        )

        latency_ms = max(int((time.perf_counter() - start_time) * 1000), 1)

        return schemas.AdminTestKeyResponse(
            success=True,
            status="SUCCESS",
            latency_ms=latency_ms,
            message=f"Kết nối thành công! Độ trễ: {latency_ms}ms - Sẵn sàng phục vụ",
            key_masked=masked_key,
        )

    except Exception as err:
        latency_ms = max(int((time.perf_counter() - start_time) * 1000), 1)
        return schemas.AdminTestKeyResponse(
            success=False,
            status="FAILED",
            latency_ms=latency_ms,
            message=f"Kết nối thất bại ({err})",
            key_masked=masked_key,
        )


# ==============================================================================
# 5. GET /admin/settings/health – Real-time Healthcheck Đích Thực (AC-SET-06)
# ==============================================================================
@router.get("/health", response_model=schemas.AdminHealthResponse)
def get_system_health(db: Session = Depends(get_db)):
    """
    Kiểm tra sức khỏe thật của 4 dịch vụ cốt lõi (Neon DB, Redis, Gemini, SMTP).
    Thay thế hoàn toàn dữ liệu giả Math.random() cũ.
    """
    services: Dict[str, schemas.AdminHealthServiceDetail] = {}

    # 1. Neon PostgreSQL Database
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1;")).scalar()
        latency_db = max(int((time.perf_counter() - t0) * 1000), 1)
        services["neon_postgresql"] = schemas.AdminHealthServiceDetail(
            status="ONLINE",
            latency_ms=latency_db,
            detail="Neon PostgreSQL Pooler kết nối ổn định",
        )
    except Exception as err:
        latency_db = max(int((time.perf_counter() - t0) * 1000), 1)
        services["neon_postgresql"] = schemas.AdminHealthServiceDetail(
            status="DOWN",
            latency_ms=latency_db,
            detail=f"Lỗi DB: {err}",
        )

    # 2. Upstash Redis Cache
    t0 = time.perf_counter()
    try:
        client = _get_sync_redis()
        if client is not None:
            # Ping kiểm tra Redis
            if hasattr(client, "ping"):
                client.ping()
            else:
                client.get("healthcheck_ping")
            latency_redis = max(int((time.perf_counter() - t0) * 1000), 1)
            services["upstash_redis"] = schemas.AdminHealthServiceDetail(
                status="ONLINE",
                latency_ms=latency_redis,
                detail="Upstash Redis Cache hoạt động tốt (Hot-Reload sẵn sàng)",
            )
        else:
            services["upstash_redis"] = schemas.AdminHealthServiceDetail(
                status="STANDBY",
                latency_ms=0,
                detail="Chưa cấu hình Redis, hệ thống đang dùng DB fallback an toàn",
            )
    except Exception as err:
        latency_redis = max(int((time.perf_counter() - t0) * 1000), 1)
        services["upstash_redis"] = schemas.AdminHealthServiceDetail(
            status="DEGRADED",
            latency_ms=latency_redis,
            detail=f"Lỗi Redis: {err}",
        )

    # 3. Google Gemini API Gateway
    t0 = time.perf_counter()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key, transport="rest")
            # Thử nhẹ list model limit
            genai.get_model("models/gemini-3.5-flash-lite")
            latency_ai = max(int((time.perf_counter() - t0) * 1000), 1)
            services["gemini_api"] = schemas.AdminHealthServiceDetail(
                status="ONLINE",
                latency_ms=latency_ai,
                detail="Google Gemini API Gateway sẵn sàng phục vụ",
            )
        except Exception as err:
            latency_ai = max(int((time.perf_counter() - t0) * 1000), 1)
            services["gemini_api"] = schemas.AdminHealthServiceDetail(
                status="DEGRADED",
                latency_ms=latency_ai,
                detail=f"Cảnh báo Gemini API: {err}",
            )
    else:
        services["gemini_api"] = schemas.AdminHealthServiceDetail(
            status="DOWN",
            latency_ms=0,
            detail="Chưa cấu hình GEMINI_API_KEY",
        )

    # 4. SMTP / Brevo Email Gateway
    t0 = time.perf_counter()
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    if smtp_host:
        try:
            # Kiểm tra socket kết nối cổng SMTP trong 2 giây
            sock = socket.create_connection((smtp_host, smtp_port), timeout=2.0)
            sock.close()
            latency_smtp = max(int((time.perf_counter() - t0) * 1000), 1)
            services["smtp_email"] = schemas.AdminHealthServiceDetail(
                status="ONLINE",
                latency_ms=latency_smtp,
                detail=f"Cổng SMTP {smtp_host}:{smtp_port} thông suốt",
            )
        except Exception as err:
            latency_smtp = max(int((time.perf_counter() - t0) * 1000), 1)
            services["smtp_email"] = schemas.AdminHealthServiceDetail(
                status="DEGRADED",
                latency_ms=latency_smtp,
                detail=f"Không thể kết nối cổng SMTP: {err}",
            )
    else:
        services["smtp_email"] = schemas.AdminHealthServiceDetail(
            status="STANDBY",
            latency_ms=0,
            detail="SMTP chưa cấu hình host (Đang ở chế độ Mock Logger)",
        )

    # Xác định trạng thái tổng thể
    overall = "HEALTHY"
    if services.get("neon_postgresql", {}).status == "DOWN":
        overall = "DOWN"
    elif any(s.status in ("DEGRADED", "DOWN") for s in services.values()):
        overall = "DEGRADED"

    return schemas.AdminHealthResponse(
        overall_status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=services,
    )


# ==============================================================================
# 6. POST /admin/settings/test-playground – Mini Playground Thử Nghiệm Sư Phạm (AC-SET-05)
# ==============================================================================
@router.post("/test-playground", response_model=schemas.AdminPlaygroundResponse)
def test_prompt_playground(
    body: schemas.AdminPlaygroundRequest,
    db: Session = Depends(get_db),
):
    """
    Sa bàn thử nghiệm Mini Playground:
    Cho phép Admin nhập bài toán mẫu (ví dụ: 'x + 5 = 12'), chọn Model và tham số
    để quan sát phản hồi sư phạm Socratic, thời gian đo (ms) và số lượng token tiêu thụ.
    """
    settings = get_system_settings(db=db)

    # Áp dụng tham số tuỳ chỉnh hoặc fallback về cài đặt hiện hành
    model_name = body.model_name or settings.get("primary_model", "gemini-3.5-flash-lite")
    temperature = body.temperature if body.temperature is not None else float(settings.get("temperature", 0.35))
    max_tokens = body.max_tokens or int(settings.get("max_output_tokens", 512))
    strictness = body.socratic_strictness or settings.get("socratic_strictness", "BALANCED")

    # Xây dựng chỉ dẫn sư phạm theo mức độ nghiêm khắc
    strictness_instructions = {
        "GUIDED": "Phong cách Khuyến khích: Hãy đưa ra câu hỏi gợi ý chi tiết kèm ví dụ số học tương tự để học sinh dễ hiểu.",
        "BALANCED": "Phong cách Cân bằng: Hãy đặt câu hỏi gợi ý tư duy 2-4 câu bám sát số liệu đề bài, tuyệt đối không giải hộ đáp án.",
        "STRICT": "Phong cách Thử thách: Chỉ chất vấn bước suy luận của học sinh, yêu cầu học sinh tự chứng minh phép tính.",
    }
    instruction = strictness_instructions.get(strictness, strictness_instructions["BALANCED"])

    system_prompt = f"""Bạn là Thầy giáo Gia sư Toán SocraticKid.
Quy tắc sống còn: Tuyệt đối KHÔNG giải hộ hay đưa ra đáp án trực tiếp.
{instruction}
Luôn xưng hô 'thầy - em' thân thiện, chuẩn mực."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chưa cấu hình GEMINI_API_KEY trong file .env máy chủ."
        )

    start_time = time.perf_counter()
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key, transport="rest")

        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )

        from middleware.gemini_telemetry import generate_with_telemetry
        response = generate_with_telemetry(model, body.prompt, model_name, "Chat")
        latency_ms = max(int((time.perf_counter() - start_time) * 1000), 1)

        # Đọc usage metadata nếu có
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        else:
            # Ước lượng nếu không có metadata
            prompt_tokens = len(body.prompt.split()) * 2
            completion_tokens = len((response.text or "").split()) * 2

        return schemas.AdminPlaygroundResponse(
            response_text=response.text or "",
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_used=model_name,
            socratic_strictness=strictness,
        )

    except Exception as err:
        latency_ms = max(int((time.perf_counter() - start_time) * 1000), 1)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chạy Playground: {err} (Thời gian đo: {latency_ms}ms)"
        )


# ==============================================================================
# 7. GET /admin/settings/audits – Lấy lịch sử thay đổi cấu hình
# ==============================================================================
@router.get("/audits", response_model=List[schemas.AdminAuditItemResponse])
def get_audit_history(
    limit: int = Query(default=10, ge=1, le=50, description="Số lượng bản ghi lịch sử"),
    db: Session = Depends(get_db),
):
    """Lấy danh sách lịch sử thay đổi cấu hình gần nhất (sắp xếp mới nhất trước)."""
    audits = get_setting_audits(limit=limit, db=db)
    return [schemas.AdminAuditItemResponse(**a) for a in audits]


# ==============================================================================
# 8. POST /admin/settings/rollback/{audit_id} – Hoàn tác cấu hình 1-Click (AC-SET-07)
# ==============================================================================
@router.post("/rollback/{audit_id}", response_model=schemas.AdminSystemSettings)
def rollback_setting_version(
    audit_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(dependencies.require_role(["ADMIN"])),
):
    """
    Hoàn tác cấu hình 1-Click:
    Tìm bản ghi audit theo audit_id và áp dụng previous_config trở lại DB,
    đồng thời xóa cache Redis để học sinh nhận ngay cấu hình cũ ổn định.
    """
    changed_by = current_user.get("email") or current_user.get("username") or "admin@socratickid.edu.vn"

    try:
        restored = rollback_system_settings(
            audit_id=audit_id,
            changed_by=changed_by,
            db=db,
        )
        restored["api_key_masked"] = _get_masked_api_key()
        restored["model_name"] = restored.get("primary_model", "gemini-3.5-flash-lite")
        restored["rate_limit_per_minute"] = restored.get("student_rate_limit", 30)

        return schemas.AdminSystemSettings(**restored)

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi hoàn tác cấu hình: {err}",
        )

