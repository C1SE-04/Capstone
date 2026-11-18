"""
US 11.3 - Task T376: ErrorDiagnosisService (Dịch Vụ Trợ Lý AI Chẩn Đoán Lỗi Hệ Thống)
====================================================================================
Dịch vụ điều phối kết nối Gemini API để thực hiện Root Cause Analysis (RCA):
  - Tích hợp Dynamic Model Selection qua SystemConfigService (Ưu tiên gemini-3.5-flash).
  - Kiểm soát Timeout nghiêm ngặt bằng ThreadPoolExecutor chống treo luồng worker.
  - Tự động nhận diện lỗi xác thực (401/403) để ngắt sớm, không lãng phí thời gian retry.
  - Tự động chuyển mạch Failover sang backup_model (gemini-3.5-flash-lite) khi lỗi 429/503.
  - Graceful Fallback: Chẩn đoán cục bộ (Local Heuristic Rule) khi mất mạng/hết quota hoàn toàn.
  - Đảm bảo 100% không văng exception làm chết tiến trình backend.
"""

import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Dict, Any, Optional, Union
from sqlalchemy.orm import Session
import google.generativeai as genai

from schemas import AiDiagnosisData
from agents.rca_prompt import (
    RCA_SYSTEM_INSTRUCTION,
    GEMINI_RCA_GENERATION_CONFIG,
    format_rca_prompt,
    parse_rca_output,
)
from services.system_config_service import get_system_settings

logger = logging.getLogger("error_diagnosis_service")


class ErrorDiagnosisService:
    """
    Dịch vụ AI phân tích nguyên nhân gốc rễ và đề xuất giải pháp sửa lỗi.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        # 1. Đọc cấu hình mô hình từ SystemConfigService (Dynamic Hot-Reloading)
        try:
            settings = get_system_settings(db=db)
            # Ưu tiên model thông minh và ít tải nhất (gemini-3.5-flash từ parent_insight_model)
            self.primary_model = settings.get("parent_insight_model") or "gemini-3.5-flash"
            self.backup_model = settings.get("backup_model") or "gemini-3.5-flash-lite"
        except Exception as exc:
            logger.warning(f"Không thể đọc SystemConfigService: {exc}. Dùng cấu hình mặc định.")
            self.primary_model = "gemini-3.5-flash"
            self.backup_model = "gemini-3.5-flash-lite"

        # 2. Khởi tạo Gemini API Client
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _extract_error_dict(self, error_input: Union[Dict[str, Any], Any, None]) -> Dict[str, Any]:
        """Chuẩn hóa đầu vào (dict, ORM SystemError hoặc None) thành dictionary thuần túy an toàn."""
        if not error_input:
            return {
                "id": "unknown",
                "error_code": "ERR_UNKNOWN",
                "error_type": "CRASH_500",
                "severity": "WARNING",
                "message": "Không có thông tin sự cố",
                "stack_trace": None,
                "endpoint": None,
                "request_payload": None,
                "user_email": None,
            }

        if isinstance(error_input, dict):
            return error_input

        # Trích xuất từ ORM SystemError
        return {
            "id": getattr(error_input, "id", "unknown"),
            "error_code": getattr(error_input, "error_code", "N/A"),
            "error_type": getattr(error_input, "error_type", "CRASH_500"),
            "severity": getattr(error_input, "severity", "WARNING"),
            "message": getattr(error_input, "message", ""),
            "stack_trace": getattr(error_input, "stack_trace", None),
            "endpoint": getattr(error_input, "endpoint", None),
            "request_payload": getattr(error_input, "request_payload", None),
            "user_email": getattr(error_input, "user_email", None),
        }

    def _call_gemini_raw(self, model_name: str, prompt: str, timeout_seconds: int) -> str:
        """
        Thực hiện gọi Gemini API đồng bộ bọc trong ThreadPoolExecutor để bắt Timeout chính xác.
        """
        def _invoke():
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=RCA_SYSTEM_INSTRUCTION,
                generation_config=GEMINI_RCA_GENERATION_CONFIG,
            )
            # Thử tận dụng telemetry middleware nếu có
            try:
                from middleware.gemini_telemetry import generate_with_telemetry
                response = generate_with_telemetry(model, prompt, model_name, "Admin-RCA")
            except Exception:
                response = model.generate_content(prompt)

            return response.text if response and hasattr(response, "text") else ""

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_invoke)
            return future.result(timeout=timeout_seconds)

    def _local_heuristic_fallback(self, error_data: Dict[str, Any], reason: str) -> AiDiagnosisData:
        """
        Cơ chế tự phục hồi (Graceful Fallback) khi Gemini bận hoặc mất kết nối:
        Dựa vào phân loại lỗi và thông điệp lỗi để đưa ra chẩn đoán heuristic tức thì.
        """
        error_type = error_data.get("error_type", "CRASH_500")
        message = error_data.get("message", "")
        endpoint = error_data.get("endpoint", "")
        stack = error_data.get("stack_trace", "")

        # Trường hợp 1: Phản ánh từ học sinh (USER_REPORT)
        if error_type == "USER_REPORT":
            return AiDiagnosisData(
                root_cause=f"Học sinh phản ánh sự cố trải nghiệm trên giao diện bài toán. ({reason})",
                resolution_summary="Kiểm tra kết nối mạng của học sinh, phản hồi hướng dẫn bé thử tải lại trang hoặc đổi mạng Wifi.",
                fix_steps=[
                    "Kiểm tra nhật ký phiên chat của học sinh trong Giám Sát Agent.",
                    "Xác nhận tình trạng đường truyền WebSocket/SSE của hệ thống.",
                    "Gửi email chăm sóc phụ huynh nếu bé báo lỗi nhiều lần."
                ],
                code_patch=None,
                file_path=None,
                line_number=None,
                confidence_score=0.6,
                model_used="local-heuristic-fallback",
            )

        # Trường hợp 2: Lỗi sập server (CRASH_500 / AI_TIMEOUT / DB_ERROR)
        exc_match = re.search(r"([A-Za-z_]+Error|Exception):?\s*(.*)", message)
        exc_name = exc_match.group(1) if exc_match else "Lỗi hệ thống không xác định"

        # Trích xuất file và dòng từ stack trace nếu có
        file_match = re.search(r'File "([^"]+)", line (\d+)', stack or "")
        file_path = file_match.group(1) if file_match else None
        line_num = int(file_match.group(2)) if file_match else None

        return AiDiagnosisData(
            root_cause=f"Hệ thống phát sinh ngoại lệ {exc_name} tại endpoint {endpoint}. (Chẩn đoán ngoại tuyến do: {reason})",
            resolution_summary=f"Cần rà soát xử lý ngoại lệ {exc_name} tại vị trí phát sinh lỗi.",
            fix_steps=[
                f"Kiểm tra logic xử lý tại {file_path or 'endpoint ' + str(endpoint)}.",
                "Bổ sung khối try-except để bắt ngoại lệ và trả về mã lỗi thân thiện.",
                "Thử lại tính năng phân tích AI khi đường truyền mạng ổn định."
            ],
            code_patch=None,
            file_path=file_path,
            line_number=line_num,
            confidence_score=0.5,
            model_used="local-heuristic-fallback",
        )

    def diagnose_error(
        self,
        error_input: Union[Dict[str, Any], Any, None],
        timeout_seconds: int = 15,
        force_backup: bool = False,
    ) -> AiDiagnosisData:
        """
        Thực hiện chẩn đoán lỗi hoàn chỉnh với cơ chế chống lỗi 3 tầng:
          1. Gọi Primary Model (gemini-3.5-flash).
          2. Nếu lỗi/timeout -> Chuyển mạch sang Backup Model (gemini-3.5-flash-lite).
          3. Nếu cả 2 đều lỗi -> Kích hoạt Local Heuristic Fallback.
        """
        error_data = self._extract_error_dict(error_input)
        prompt = format_rca_prompt(error_data)

        # Nếu không có API Key -> Chuyển ngay sang Fallback an toàn
        if not self.api_key:
            logger.warning("GEMINI_API_KEY chưa được cấu hình. Sử dụng Local Heuristic Fallback.")
            return self._local_heuristic_fallback(error_data, reason="Chưa cấu hình GEMINI_API_KEY")

        # ─── TẦNG 1: Gọi Primary Model ──────────────────────────────────────
        primary_target = self.backup_model if force_backup else self.primary_model
        is_auth_error = False

        try:
            raw_output = self._call_gemini_raw(primary_target, prompt, timeout_seconds=timeout_seconds)
            if raw_output:
                return parse_rca_output(raw_output, model_used=primary_target)
        except FutureTimeoutError:
            logger.warning(f"Gọi {primary_target} bị quá thời gian ({timeout_seconds}s). Kích hoạt chuyển mạch dự phòng...")
        except Exception as exc:
            err_msg = str(exc)
            # Nhận diện lỗi xác thực (API Key không hợp lệ) -> ngắt ngay, không lãng phí gọi backup
            if any(term in err_msg.lower() for term in ["unauthenticated", "permissiondenied", "api_key_invalid", "401", "403"]):
                logger.error(f"Khóa GEMINI_API_KEY không hợp lệ: {exc}. Chuyển ngay sang Fallback.")
                is_auth_error = True
            else:
                logger.warning(f"Gọi {primary_target} gặp lỗi: {exc}. Kích hoạt chuyển mạch dự phòng...")

        # ─── TẦNG 2: Chuyển mạch sang Backup Model (Bỏ qua nếu lỗi xác thực) ──
        if not is_auth_error and primary_target != self.backup_model:
            try:
                raw_backup = self._call_gemini_raw(self.backup_model, prompt, timeout_seconds=10)
                if raw_backup:
                    return parse_rca_output(raw_backup, model_used=self.backup_model)
            except Exception as exc:
                logger.error(f"Gọi backup_model {self.backup_model} cũng thất bại: {exc}")

        # ─── TẦNG 3: Local Heuristic Fallback An Toàn ────────────────────────
        fallback_reason = "Khóa GEMINI_API_KEY không hợp lệ hoặc bị chặn" if is_auth_error else "Gemini API đang bận hoặc quá thời gian chờ"
        return self._local_heuristic_fallback(error_data, reason=fallback_reason)
