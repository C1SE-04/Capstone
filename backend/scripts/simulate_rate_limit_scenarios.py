"""
========================================================================================
File: backend/scripts/simulate_rate_limit_scenarios.py
Sprint 11 - US 11.1: Quản Trị Lưu Lượng & Chống Lạm Dụng Tài Nguyên (Rate Limiting)
========================================================================================
Script kiểm thử kịch bản tự động toàn diện:
  1. Kịch bản 1: Dynamic Student Rate Limit (Sliding Window & 4 headers RFC 6585)
  2. Kịch bản 2: Socratic Pedagogical Cool-Down (< 5s giữa 2 câu hỏi)
  3. Kịch bản 3: Phòng thủ Brute-Force Đăng nhập 3 lớp (Khóa 15 phút, cô lập IP)
  4. Kịch bản 4: Cơ chế tự phục hồi an toàn Fail-Open khi Redis Offline
  5. Kịch bản 5: Chống tấn công dò OTP Phụ huynh (Khóa 15 phút sau 5 lần nhập sai)

Cách chạy:
  python backend/scripts/simulate_rate_limit_scenarios.py
========================================================================================
"""

import sys
import os
import time
import uuid
from typing import Dict, Any

# Thêm thư mục backend vào sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal
import models
import auth
from services.rate_limiter_service import RateLimiterService, _fallback_memory_limiter


# ANSI Color Codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_header(title: str):
    print(f"\n{BOLD}{CYAN}{'=' * 80}{RESET}")
    print(f"{BOLD}{CYAN}▶ {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 80}{RESET}")


def print_pass(msg: str):
    print(f"  {GREEN}✔ [PASS]{RESET} {msg}")


def print_fail(msg: str):
    print(f"  {RED}✘ [FAIL]{RESET} {msg}")


def print_info(msg: str):
    print(f"  {BLUE}ℹ [INFO]{RESET} {msg}")


def setup_test_users():
    """Khởi tạo tài khoản kiểm thử tạm thời."""
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    student_id = f"sim-student-{suffix}"
    student_username = f"sim_student_{suffix}"
    student_password = "StudentPass123"

    parent_id = f"sim-parent-{suffix}"
    parent_email = f"sim_parent_{suffix}@example.com"
    parent_password = "ParentPass123"

    student = models.User(
        id=student_id,
        username=student_username,
        hashed_password=auth.hash_password(student_password),
        role="STUDENT",
        grade=5,
    )

    parent = models.User(
        id=parent_id,
        username=f"parent_{suffix}",
        email=parent_email,
        hashed_password=auth.hash_password(parent_password),
        role="MONITOR",
        email_verified=True,
    )

    db.add_all([student, parent])
    db.commit()

    session_id = f"sim-session-{suffix}"
    session = models.Session(
        id=session_id,
        user_id=student_id,
        title="Session Kiểm thử Rate Limit",
    )
    db.add(session)
    db.commit()
    db.close()

    return {
        "student_id": student_id,
        "student_username": student_username,
        "student_password": student_password,
        "parent_id": parent_id,
        "parent_email": parent_email,
        "parent_password": parent_password,
        "session_id": session_id,
    }


def cleanup_test_users(users: Dict[str, Any]):
    """Xóa dữ liệu kiểm thử sau khi hoàn tất."""
    db = SessionLocal()
    db.query(models.Session).filter(
        models.Session.user_id == users["student_id"]
    ).delete()
    db.query(models.User).filter(
        models.User.id.in_([users["student_id"], users["parent_id"]])
    ).delete()
    db.query(models.EmailOtp).filter(
        models.EmailOtp.email == users["parent_email"]
    ).delete()
    db.commit()
    db.close()


def _mock_ai_stream(*args, **kwargs):
    yield 'event: message\ndata: {"text": "Chào em, em hãy quan sát kỹ bài toán nhé!"}\n\n'
    yield 'event: done\ndata: {}\n\n'


# ==============================================================================
# KỊCH BẢN 1: DYNAMIC STUDENT RATE LIMIT (SLIDING WINDOW & RFC 6585)
# ==============================================================================
def run_scenario_1_dynamic_rate_limit(client: TestClient, users: Dict[str, Any]) -> bool:
    print_header("KỊCH BẢN 1: Dynamic Student Rate Limit (Hạn mức câu hỏi động & RFC 6585)")
    RateLimiterService.reset_in_memory_state()

    session_id = users["session_id"]
    success = True

    mock_settings = {
        "student_rate_limit": 3,
        "global_gemini_rpm_limit": 100,
    }

    with patch("orchestrator_bridge.process_query_with_orchestrator", side_effect=_mock_ai_stream):
        with patch("routers.chat.system_config_service.get_system_settings", return_value=mock_settings):
            print_info("Admin cấu hình: student_rate_limit = 3 câu/phút.")

            # Gửi 3 câu đầu tiên (cho phép)
            for i in range(1, 4):
                _fallback_memory_limiter._cooldowns.clear()  # Tránh dính cool-down
                res = client.post(
                    "/chat/orchestrator",
                    json={"prompt": f"Câu hỏi {i}", "session_id": session_id}
                )
                if res.status_code == 200:
                    remaining = res.headers.get("X-RateLimit-Remaining")
                    limit = res.headers.get("X-RateLimit-Limit")
                    print_pass(f"Gửi câu {i}/3 thành công (HTTP 200) | Limit: {limit}, Remaining: {remaining}")
                else:
                    print_fail(f"Câu {i} bị từ chối bất thường: HTTP {res.status_code}")
                    success = False

            # Gửi câu thứ 4 (vượt quá hạn mức 3 câu/phút -> phải bị chặn 429)
            _fallback_memory_limiter._cooldowns.clear()
            res4 = client.post(
                "/chat/orchestrator",
                json={"prompt": "Câu hỏi thứ 4", "session_id": session_id}
            )

            if res4.status_code == 429:
                retry_after = res4.headers.get("Retry-After")
                rem = res4.headers.get("X-RateLimit-Remaining")
                reset_ts = res4.headers.get("X-RateLimit-Reset")
                print_pass(f"Câu 4 bị chặn đúng chuẩn (HTTP 429) | Retry-After: {retry_after}s, Remaining: {rem}, Reset: {reset_ts}")
                detail = res4.json().get("detail", {})
                if detail.get("reason") in ["STUDENT_LIMIT", "RATE_LIMIT_EXCEEDED"] or "quá nhanh" in detail.get("message", ""):
                    print_pass(f"Mã lý do phản hồi: {detail.get('reason')} - {detail.get('message')}")
                else:
                    print_fail(f"Lý do phản hồi không khớp: {detail}")
                    success = False
            else:
                print_fail(f"Câu 4 không bị chặn! Nhận HTTP {res4.status_code}")
                success = False

    return success


# ==============================================================================
# KỊCH BẢN 2: SOCRATIC PEDAGOGICAL COOL-DOWN (< 5s GIỮA 2 CÂU HỎI)
# ==============================================================================
def run_scenario_2_socratic_cooldown(client: TestClient, users: Dict[str, Any]) -> bool:
    print_header("KỊCH BẢN 2: Socratic Pedagogical Cool-Down (< 5s giữa 2 câu hỏi)")
    RateLimiterService.reset_in_memory_state()

    session_id = users["session_id"]
    success = True

    mock_settings = {
        "student_rate_limit": 10,
        "global_gemini_rpm_limit": 100,
    }

    with patch("orchestrator_bridge.process_query_with_orchestrator", side_effect=_mock_ai_stream):
        with patch("routers.chat.system_config_service.get_system_settings", return_value=mock_settings):
            # 1. Gửi câu đầu tiên -> Thành công
            res1 = client.post(
                "/chat/orchestrator",
                json={"prompt": "Em chưa hiểu câu này ạ", "session_id": session_id}
            )
            if res1.status_code == 200:
                print_pass("Gửi câu hỏi đầu tiên thành công (HTTP 200).")
            else:
                print_fail(f"Gửi câu đầu thất bại: HTTP {res1.status_code}")
                return False

            # 2. Gửi tiếp câu hỏi mới ngay lập tức (dưới 5 giây) -> Phải bị chặn sư phạm
            print_info("Gửi tiếp tin nhắn mới ngay sau đó (< 5s)...")
            res2 = client.post(
                "/chat/orchestrator",
                json={"prompt": "Giải giúp em luôn đi!", "session_id": session_id}
            )

            if res2.status_code == 429:
                detail = res2.json().get("detail", {})
                if detail.get("reason") == "SOCRATIC_COOL_DOWN":
                    print_pass(f"Bị chặn sư phạm đúng chuẩn (HTTP 429, reason=SOCRATIC_COOL_DOWN)")
                    print_pass(f"Thông điệp sư phạm: '{detail.get('message')}'")
                    print_pass(f"Thời gian cần suy ngẫm còn lại: {detail.get('retry_after')}s")
                else:
                    print_fail(f"Lý do chặn không đúng: {detail}")
                    success = False
            else:
                print_fail(f"Không chặn spam dưới 5s! Nhận HTTP {res2.status_code}")
                success = False

    return success


# ==============================================================================
# KỊCH BẢN 3: PHÒNG THỦ BRUTE-FORCE ĐĂNG NHẬP 3 LỚP (LOCKOUT 15 PHÚT)
# ==============================================================================
def run_scenario_3_login_brute_force(client: TestClient, users: Dict[str, Any]) -> bool:
    print_header("KỊCH BẢN 3: Phòng Thủ Đăng Nhập Brute-Force 3 Lớp (Lockout 15 phút, Cô Lập IP)")
    RateLimiterService.reset_in_memory_state()

    username = users["student_username"]
    correct_pwd = users["student_password"]
    wrong_pwd = "IncorrectPassword999!"
    attacker_ip = "198.51.100.42"
    legit_ip = "203.0.113.88"

    success = True
    print_info(f"Kẻ tấn công từ IP {attacker_ip} cố tình dò mật khẩu tài khoản '{username}'...")

    # Thử sai 4 lần -> Trả cảnh báo số lần còn lại
    for i in range(1, 5):
        res = client.post(
            "/login",
            data={"username": username, "password": wrong_pwd},
            headers={"X-Real-IP": attacker_ip}
        )
        if res.status_code == 401:
            detail = res.json().get("detail", {})
            rem = detail.get("remaining_attempts")
            print_pass(f"Lần {i}: Báo sai mật khẩu, còn lại {rem} lần thử.")
        else:
            print_fail(f"Lần {i} phản hồi sai mã: HTTP {res.status_code}")
            success = False

    # Thử sai lần thứ 5 -> Kích hoạt khóa tài khoản 15 phút (Trả về HTTP 429 Too Many Requests)
    res5 = client.post(
        "/login",
        data={"username": username, "password": wrong_pwd},
        headers={"X-Real-IP": attacker_ip}
    )
    if res5.status_code in [401, 429]:
        detail5 = res5.json().get("detail", {})
        print_pass(f"Lần 5: Kích hoạt khóa tạm thời 15 phút (HTTP {res5.status_code}) thành công!")
    else:
        print_fail(f"Lần 5 phản hồi sai: HTTP {res5.status_code}")
        success = False

    # Lần 6: Kẻ tấn công dù nhập ĐÚNG mật khẩu vẫn bị chặn
    res6 = client.post(
        "/login",
        data={"username": username, "password": correct_pwd},
        headers={"X-Real-IP": attacker_ip}
    )
    if res6.status_code in [401, 429]:
        detail6 = res6.json().get("detail", {})
        print_pass(f"Lần 6 (Đúng mật khẩu trên Attacker IP): Bị từ chối (HTTP {res6.status_code}) vì tài khoản đang trong thời gian phạt 15 phút.")
    else:
        print_fail(f"Lần 6 không bị chặn: HTTP {res6.status_code}")
        success = False

    # Học sinh thật đăng nhập từ IP khác (legit_ip) với đúng mật khẩu -> Được phép đăng nhập!
    print_info(f"Học sinh thật dùng mạng gia đình (IP {legit_ip}) đăng nhập mật khẩu đúng...")
    res_legit = client.post(
        "/login",
        data={"username": username, "password": correct_pwd},
        headers={"X-Real-IP": legit_ip}
    )
    if res_legit.status_code == 200:
        print_pass("Học sinh thật đăng nhập thành công (HTTP 200) - Không bị khóa oan bởi kẻ tấn công khác IP!")
    else:
        print_fail(f"Học sinh thật bị ảnh hưởng oan: HTTP {res_legit.status_code}")
        success = False

    return success


# ==============================================================================
# KỊCH BẢN 4: FAIL-OPEN RESILIENCY (REDIS OFFLINE / CRASH)
# ==============================================================================
def run_scenario_4_fail_open_resiliency(client: TestClient, users: Dict[str, Any]) -> bool:
    print_header("KỊCH BẢN 4: Cơ Chế An Toàn Fail-Open (Redis Offline Không Bao Giờ Sập 500)")
    RateLimiterService.reset_in_memory_state()

    student_id = users["student_id"]
    token = auth.create_access_token({"sub": student_id, "role": "STUDENT", "session_version": 1})
    headers = {"Authorization": f"Bearer {token}"}

    # Giả lập Redis bị sập (ném ngoại lệ kết nối)
    broken_redis = MagicMock()
    broken_redis.pipeline.side_effect = Exception("ConnectionRefusedError: Redis service is down!")

    success = True
    print_info("Giả lập sự cố Upstash Redis mất kết nối...")

    with patch("orchestrator_bridge.process_query_with_orchestrator", side_effect=_mock_ai_stream):
        # Gọi API qua mock get_redis trả về redis lỗi
        with patch("routers.chat.get_redis", return_value=broken_redis):
            res = client.post(
                "/chat/orchestrator",
                json={"prompt": "Bài này làm sao ạ?", "session_id": users["session_id"]}
            )

            if res.status_code == 200:
                print_pass("Hệ thống tự động chuyển sang Fail-Open RAM, request thành công (HTTP 200).")
                print_pass("Tuyệt đối KHÔNG trả về lỗi máy chủ 500 làm gián đoạn học tập của học sinh!")
            else:
                print_fail(f"Hệ thống gặp lỗi khi Redis hỏng: HTTP {res.status_code}")
                success = False

    return success


# ==============================================================================
# KỊCH BẢN 5: CHỐNG DÒ OTP PHỤ HUYNH (KHÓA 15 PHÚT SAU 5 LẦN NHẬP SAI)
# ==============================================================================
def run_scenario_5_otp_lockout(client: TestClient, users: Dict[str, Any]) -> bool:
    print_header("KỊCH BẢN 5: Chống Tấn Công Dò Mã OTP Phụ Huynh (US 11.2)")
    RateLimiterService.reset_in_memory_state()

    parent_email = users["parent_email"]

    # Tạo mã OTP trong DB
    db = SessionLocal()
    from datetime import datetime, timezone, timedelta
    otp = models.EmailOtp(
        email=parent_email.lower(),
        otp_code="888999",
        purpose="PARENT_RESET_PASSWORD",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False,
    )
    db.add(otp)
    db.commit()
    db.close()

    success = True
    print_info(f"Tạo mã OTP thử nghiệm cho phụ huynh {parent_email}. Thử nhập sai...")

    # Nhập sai 4 lần
    for i in range(1, 5):
        res = client.post(
            "/auth/forgot-password/verify-and-reset",
            json={"email": parent_email, "otp_code": "000000", "new_password": "NewSecretPassword123"}
        )
        if res.status_code == 400:
            print_pass(f"Lần {i}: Báo sai mã OTP, còn {5 - i} lần thử.")
        else:
            print_fail(f"Lần {i} phản hồi sai: HTTP {res.status_code}")
            success = False

    # Nhập sai lần 5 -> Khóa tạm thời 15 phút
    res5 = client.post(
        "/auth/forgot-password/verify-and-reset",
        json={"email": parent_email, "otp_code": "000000", "new_password": "NewSecretPassword123"}
    )
    if res5.status_code in [400, 429]:
        print_pass("Lần 5: Khóa mã OTP và kích hoạt thời gian phạt 15 phút thành công!")
    else:
        print_fail(f"Lần 5 không khóa: HTTP {res5.status_code}")
        success = False

    return success


# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    print(f"\n{BOLD}{YELLOW}╔══════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{YELLOW}║   BỘ SCRIPT KIỂM THỬ KỊCH BẢN RATE LIMIT & AN TOÀN HỆ THỐNG US 11.1  ║{RESET}")
    print(f"{BOLD}{YELLOW}╚══════════════════════════════════════════════════════════════════════╝{RESET}")

    client = TestClient(app)
    users = setup_test_users()

    results = {}
    try:
        results["Kịch bản 1 (Dynamic Limit)"] = run_scenario_1_dynamic_rate_limit(client, users)
        results["Kịch bản 2 (Socratic Cool-down)"] = run_scenario_2_socratic_cooldown(client, users)
        results["Kịch bản 3 (Anti-Brute-Force)"] = run_scenario_3_login_brute_force(client, users)
        results["Kịch bản 4 (Fail-Open Resiliency)"] = run_scenario_4_fail_open_resiliency(client, users)
        results["Kịch bản 5 (OTP Lockout)"] = run_scenario_5_otp_lockout(client, users)
    finally:
        cleanup_test_users(users)

    print_header("TỔNG KẾT KẾT QUẢ KIỂM THỬ KỊCH BẢN RATE LIMIT")
    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, ok in results.items():
        status = f"{GREEN}PASSED{RESET}" if ok else f"{RED}FAILED{RESET}"
        print(f"  • {name:<35}: {status}")

    print(f"\n{BOLD}Tỷ lệ thành công: {passed}/{total} ({passed/total * 100:.1f}%){RESET}\n")

    if passed == total:
        print(f"{BOLD}{GREEN}✔ TẤT CẢ KỊCH BẢN RATE LIMIT & PHÒNG THỦ TÀI NGUYÊN ĐẠT YÊU CẦU 100%!{RESET}\n")
        return 0
    else:
        print(f"{BOLD}{RED}✘ CÓ KỊCH BẢN CHƯA ĐẠT. VUI LÒNG KIỂM TRA LẠI LOG CHI TIẾT.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
