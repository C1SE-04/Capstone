"""
File: backend/test/test_us11_1_rate_limiting.py
Mô tả: Bộ kiểm thử tự động toàn diện cho US 11.1 (Rate Limiting & Socratic Cool-Down)
Tasks:
  - Task #357 (T11.1.0): Service lõi RateLimiterService (Sliding Window Log & RFC Headers)
  - Task #358 (T11.1.1): Tích hợp Dynamic Rate Limit học sinh trên router chat (/chat/orchestrator)
  - Task #359 (T11.1.2): Cài đặt quy tắc sư phạm Socratic Cool-Down (>= 5s)
"""

import time
import uuid
import random
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from database import get_db, SessionLocal
import models
import auth
from services.rate_limiter_service import RateLimiterService


@pytest.fixture(autouse=True)
def clean_limiter_state():
    """Reset RAM state trước mỗi test case."""
    RateLimiterService.reset_in_memory_state()
    yield
    RateLimiterService.reset_in_memory_state()


# ==============================================================================
# 1. UNIT TESTS CHO LÕI RATELIMITERSERVICE (TASK #357)
# ==============================================================================

@pytest.mark.anyio
async def test_sliding_window_allow_and_block():
    """Kiểm tra logic sliding window: cho qua khi dưới limit, chặn khi vượt limit."""
    mock_redis = MagicMock()
    pipe_mock = MagicMock()
    mock_redis.pipeline.return_value = pipe_mock

    # Lần 1: Cửa sổ rỗng (count = 0) -> Cho qua
    pipe_mock.execute = AsyncMock(side_effect=[
        [0, 0, []],  # zremrangebyscore, zcard, zrange
        [True, True] # zadd, expire
    ])

    allowed, info = await RateLimiterService.check_sliding_window(
        redis_client=mock_redis,
        key="test:student:usr-1:chat",
        limit=3,
        window_seconds=60,
    )
    assert allowed is True
    assert info["remaining"] == 2
    assert info["retry_after"] == 0

    # Lần 2: Đã đạt limit (count = 3) -> Chặn
    now_ms = time.time() * 1000
    pipe_mock.execute = AsyncMock(side_effect=[
        [0, 3, [("entry1", now_ms - 20000)]],  # current_count = 3, oldest_score = now - 20s
    ])

    allowed2, info2 = await RateLimiterService.check_sliding_window(
        redis_client=mock_redis,
        key="test:student:usr-1:chat",
        limit=3,
        window_seconds=60,
    )
    assert allowed2 is False
    assert info2["remaining"] == 0
    assert info2["retry_after"] > 0
    assert info2["retry_after"] <= 60


def test_rfc_headers_generation():
    """Kiểm tra hàm sinh 4 HTTP headers tuân thủ RFC 6585 và chuẩn công nghiệp."""
    headers = RateLimiterService.build_rate_limit_headers(
        limit=30,
        remaining=0,
        retry_after=15,
        reset_at=1731765400,
    )
    assert headers["Retry-After"] == "15"
    assert headers["X-RateLimit-Limit"] == "30"
    assert headers["X-RateLimit-Remaining"] == "0"
    assert headers["X-RateLimit-Reset"] == "1731765400"


@pytest.mark.anyio
async def test_controlled_fail_open_in_memory():
    """Kiểm tra cơ chế Controlled Fail-Open: Khi Redis lỗi, RAM limiter tự động kích hoạt."""
    broken_redis = AsyncMock()
    broken_redis.pipeline.side_effect = RuntimeError("Redis connection lost")

    key = f"test:failopen:{uuid.uuid4().hex}"
    # Gửi 2 request với limit = 2
    ok1, info1 = await RateLimiterService.check_sliding_window(broken_redis, key, limit=2, window_seconds=10)
    assert ok1 is True
    assert info1.get("fallback_mode") is True

    ok2, info2 = await RateLimiterService.check_sliding_window(broken_redis, key, limit=2, window_seconds=10)
    assert ok2 is True

    # Request thứ 3 vượt limit = 2 -> Bị RAM limiter chặn lại
    ok3, info3 = await RateLimiterService.check_sliding_window(broken_redis, key, limit=2, window_seconds=10)
    assert ok3 is False
    assert info3["retry_after"] > 0


# ==============================================================================
# 2. UNIT TESTS CHO QUY TẮC SƯ PHẠM SOCRATIC COOL-DOWN (TASK #359)
# ==============================================================================

@pytest.mark.anyio
async def test_socratic_cooldown_logic():
    """Kiểm tra quy tắc Cool-down: Chặn nếu gửi dồn dập < 5s, cho phép nếu >= 5s."""
    mock_redis = AsyncMock()
    session_id = f"test-sess-{uuid.uuid4().hex[:8]}"

    # Trường hợp 1: Câu hỏi đầu tiên (chưa có completion nào) -> Cho qua
    mock_redis.get.return_value = None
    is_cool, retry, delta = await RateLimiterService.check_socratic_cooldown(
        mock_redis, session_id, cooldown_seconds=5.0
    )
    assert is_cool is True
    assert retry == 0

    # Trường hợp 2: AI vừa hoàn tất cách đây 1.5 giây -> Bị chặn
    now = time.time()
    mock_redis.get.return_value = str(now - 1.5)
    is_cool2, retry2, delta2 = await RateLimiterService.check_socratic_cooldown(
        mock_redis, session_id, cooldown_seconds=5.0
    )
    assert is_cool2 is False
    assert retry2 >= 3  # Cần đợi khoảng 4s nữa
    assert delta2 < 5.0

    # Trường hợp 3: Đã trôi qua 5.5 giây -> Cho phép gửi tiếp
    mock_redis.get.return_value = str(now - 5.5)
    is_cool3, retry3, delta3 = await RateLimiterService.check_socratic_cooldown(
        mock_redis, session_id, cooldown_seconds=5.0
    )
    assert is_cool3 is True
    assert retry3 == 0


# ==============================================================================
# 3. INTEGRATION TESTS CHO ROUTER POST /chat/orchestrator (TASK #358 & #359)
# ==============================================================================

@pytest.fixture
def test_student_and_session():
    """Khởi tạo phiên học test trong database kết nối với user có sẵn."""
    db = SessionLocal()
    session_id = f"sess-test-{uuid.uuid4().hex[:8]}"

    # Đảm bảo guest-user-id đã có sẵn trong DB
    guest = db.query(models.User).filter(models.User.id == "guest-user-id").first()
    if not guest:
        guest = models.User(
            id="guest-user-id",
            email="guest@socratickid.local",
            username="guest",
            hashed_password="guest",
            role="GUEST"
        )
        db.add(guest)
        db.commit()

    session = models.Session(
        id=session_id,
        user_id="guest-user-id",
        title="Phiên kiểm thử Rate Limit",
    )
    db.add(session)
    db.commit()
    db.close()

    yield {"user_id": "guest-user-id", "session_id": session_id}

    # Dọn dẹp sau test
    db = SessionLocal()
    db.query(models.Session).filter(models.Session.id == session_id).delete()
    db.commit()
    db.close()


def test_chat_orchestrator_student_rate_limit_enforced(test_student_and_session):
    """
    T11.1.1 Integration Test:
    Học sinh gửi câu hỏi đến /chat/orchestrator.
    Khi cấu hình student_rate_limit = 2:
    - 2 câu đầu thành công (200).
    - Câu thứ 3 bị chặn với HTTP 429 và lý do STUDENT_LIMIT.
    """
    client = TestClient(app)
    session_id = test_student_and_session["session_id"]
    user_id = test_student_and_session["user_id"]

    # Mock generator AI trả về nhanh
    def _mock_ai_stream(*args, **kwargs):
        yield "event: message\ndata: {\"text\": \"Chào em!\"}\n\n"
        yield "event: done\ndata: {}\n\n"

    # Giả lập cấu hình student_rate_limit = 2
    mock_settings = {
        "student_rate_limit": 2,
        "global_gemini_rpm_limit": 100,
    }

    student_counter = 0

    async def fake_check_sliding_window(redis_client, key, limit, window_seconds=60):
        nonlocal student_counter
        if "ratelimit:student" in key:
            student_counter += 1
            if student_counter > limit:
                return False, {
                    "allowed": False,
                    "current_count": student_counter,
                    "remaining": 0,
                    "retry_after": 20,
                    "reset_at": int(time.time() + 20),
                }
            return True, {
                "allowed": True,
                "current_count": student_counter,
                "remaining": limit - student_counter,
                "retry_after": 0,
                "reset_at": int(time.time() + 60),
            }
        # Cho phép các key khác (như global) đi qua
        return True, {
            "allowed": True,
            "current_count": 1,
            "remaining": limit - 1,
            "retry_after": 0,
            "reset_at": int(time.time() + 60),
        }

    with patch("orchestrator_bridge.process_query_with_orchestrator", side_effect=_mock_ai_stream):
        with patch("routers.chat.system_config_service.get_system_settings", return_value=mock_settings):
            with patch.object(RateLimiterService, "check_socratic_cooldown", return_value=(True, 0, 999.0)):
                with patch.object(RateLimiterService, "check_sliding_window", side_effect=fake_check_sliding_window):
                    # Request 1: Thành công (200)
                    res1 = client.post("/chat/orchestrator", json={"session_id": session_id, "prompt": "1 + 1 = ?"})
                    assert res1.status_code == 200

                    # Request 2: Thành công (200)
                    res2 = client.post("/chat/orchestrator", json={"session_id": session_id, "prompt": "2 + 2 = ?"})
                    assert res2.status_code == 200

                    # Request 3: Vượt quá student_rate_limit = 2 -> Chặn với mã 429!
                    res3 = client.post("/chat/orchestrator", json={"session_id": session_id, "prompt": "3 + 3 = ?"})
                    assert res3.status_code == 429
                    body3 = res3.json()
                    assert body3["detail"]["error"] == "rate_limit_exceeded"
                    assert body3["detail"]["reason"] == "STUDENT_LIMIT"
                    assert body3["detail"]["limit"] == 2
                    assert res3.headers.get("Retry-After") is not None
                    assert res3.headers.get("X-RateLimit-Limit") == "2"


def test_chat_orchestrator_socratic_cooldown_enforced(test_student_and_session):
    """
    T11.1.2 Integration Test:
    Học sinh gửi câu hỏi tiếp theo trong vòng < 5 giây sau khi AI trả lời xong.
    Hệ thống chặn lại với HTTP 429 và reason SOCRATIC_COOL_DOWN.
    """
    client = TestClient(app)
    session_id = test_student_and_session["session_id"]

    # Giả lập câu trả lời AI vừa kết thúc cách đây 1 giây
    RateLimiterService.record_ai_completion_sync(session_id)

    mock_settings = {"student_rate_limit": 30, "global_gemini_rpm_limit": 100}
    with patch("services.system_config_service.get_system_settings", return_value=mock_settings):
        # Học sinh gửi câu hỏi ngay sau 0.2s -> Bị chặn bởi Socratic Cool-Down!
        res = client.post("/chat/orchestrator", json={"session_id": session_id, "prompt": "Câu hỏi gửi quá nhanh"})
        assert res.status_code == 429
        data = res.json()
        assert data["detail"]["error"] == "rate_limit_exceeded"
        assert data["detail"]["reason"] == "SOCRATIC_COOL_DOWN"
        assert "5 giây" in data["detail"]["message"]
        assert int(res.headers.get("Retry-After", "0")) > 0


# ==============================================================================
# 4. UNIT & INTEGRATION TESTS CHO ANTI-BRUTE-FORCE LOGIN (TASK #360)
# ==============================================================================

@pytest.fixture
def test_auth_user():
    """Tạo user kiểm thử đăng nhập trong database."""
    db = SessionLocal()
    user_id = f"user-brute-{uuid.uuid4().hex[:6]}"
    username = f"brute_target_{uuid.uuid4().hex[:6]}"
    password = "SuperSecretPassword123"

    user = models.User(
        id=user_id,
        email=f"{username}@socratickid.local",
        username=username,
        hashed_password=auth.hash_password(password),
        role="STUDENT"
    )
    db.add(user)
    db.commit()
    db.close()

    RateLimiterService.reset_in_memory_state()

    yield {"user_id": user_id, "username": username, "password": password}

    # Dọn dẹp sau test
    db = SessionLocal()
    db.query(models.User).filter(models.User.id == user_id).delete()
    db.commit()
    db.close()
    RateLimiterService.reset_in_memory_state()


def test_anti_brute_force_lockout_and_ip_isolation(test_auth_user):
    """
    T11.1.3 Integration Test:
    - Thử sai 5 lần liên tiếp từ IP máy A (192.168.10.1):
      + Lần 1-4: trả về 401 với số lần thử còn lại (4 -> 1).
      + Lần 5: trả về 429 và tạm khóa tài khoản trên IP máy A trong 15 phút.
      + Lần 6: Nhập ĐÚNG mật khẩu trên máy A vẫn bị chặn (429).
    - Nhưng trên máy B (IP khác 192.168.20.2):
      + Nhập ĐÚNG mật khẩu -> Đăng nhập thành công 200 (không bị khóa oan).
    """
    client = TestClient(app)
    username = test_auth_user["username"]
    correct_pwd = test_auth_user["password"]
    wrong_pwd = "IncorrectPassword999"

    ip_a = f"192.168.{random.randint(10, 49)}.{random.randint(1, 250)}"
    ip_b = f"192.168.{random.randint(50, 99)}.{random.randint(1, 250)}"

    # Lần 1 đến 4: Sai mật khẩu -> 401 kèm số lần còn lại
    for attempt in range(1, 5):
        res = client.post(
            "/login",
            data={"username": username, "password": wrong_pwd},
            headers={"X-Real-IP": ip_a}
        )
        assert res.status_code == 401, f"Attempt {attempt} phải trả về 401"
        detail = res.json()["detail"]
        expected_remaining = 5 - attempt
        assert detail["remaining_attempts"] == expected_remaining
        assert f"còn {expected_remaining} lần thử" in detail["message"]

    # Lần 5: Nhập sai mật khẩu lần 5 -> Tạm khóa với HTTP 429
    res5 = client.post(
        "/login",
        data={"username": username, "password": wrong_pwd},
        headers={"X-Real-IP": ip_a}
    )
    assert res5.status_code == 429
    detail5 = res5.json()["detail"]
    assert detail5["error"] == "rate_limit_exceeded"
    assert detail5["reason"] == "AUTH_BRUTE_FORCE"
    assert "tạm thời bị khóa" in detail5["message"]
    assert res5.headers.get("Retry-After") is not None
    assert int(res5.headers.get("Retry-After")) > 0

    # Lần 6 trên máy A: Dù nhập ĐÚNG mật khẩu vẫn bị chặn với mã 429 vì đang trong thời gian khóa
    res6 = client.post(
        "/login",
        data={"username": username, "password": correct_pwd},
        headers={"X-Real-IP": ip_a}
    )
    assert res6.status_code == 429
    detail6 = res6.json()["detail"]
    assert detail6["reason"] == "AUTH_BRUTE_FORCE"

    # Trên máy B (IP khác): Nhập ĐÚNG mật khẩu -> Thành công 200 (Học sinh thật không bị khóa oan!)
    res_b = client.post(
        "/login",
        data={"username": username, "password": correct_pwd},
        headers={"X-Real-IP": ip_b}
    )
    assert res_b.status_code == 200
    token_data = res_b.json()
    assert "access_token" in token_data
    assert token_data["username"] == username


def test_login_success_resets_attempt_count(test_auth_user):
    """
    T11.1.3 Integration Test:
    Đăng nhập sai 2 lần -> Đăng nhập đúng thành công -> Bộ đếm lỗi được xóa về 0.
    """
    client = TestClient(app)
    username = test_auth_user["username"]
    correct_pwd = test_auth_user["password"]
    wrong_pwd = "WrongPassword123"
    client_ip = f"192.168.{random.randint(100, 150)}.{random.randint(1, 250)}"

    # Thử sai 2 lần
    res1 = client.post("/login", data={"username": username, "password": wrong_pwd}, headers={"X-Real-IP": client_ip})
    assert res1.status_code == 401
    assert res1.json()["detail"]["remaining_attempts"] == 4

    res2 = client.post("/login", data={"username": username, "password": wrong_pwd}, headers={"X-Real-IP": client_ip})
    assert res2.status_code == 401
    assert res2.json()["detail"]["remaining_attempts"] == 3

    # Đăng nhập ĐÚNG -> Thành công 200
    res_ok = client.post("/login", data={"username": username, "password": correct_pwd}, headers={"X-Real-IP": client_ip})
    assert res_ok.status_code == 200

    # Thử sai lần nữa -> Bộ đếm đã reset nên remaining_attempts phải quay lại 4 (thay vì 2)
    res_after = client.post("/login", data={"username": username, "password": wrong_pwd}, headers={"X-Real-IP": client_ip})
    assert res_after.status_code == 401
    assert res_after.json()["detail"]["remaining_attempts"] == 4


def test_dynamic_admin_setting_rate_limit_applied(test_student_and_session):
    """
    US 11.1 - AC1: Kiểm tra cấu hình động student_rate_limit = N từ Admin Settings.
    Nếu Admin đặt student_rate_limit = 3 thì router chat nhận đúng limit=3 và chặn
    ở câu thứ 4 kèm đầy đủ 4 RFC headers.
    """
    client = TestClient(app)
    session_id = test_student_and_session["session_id"]

    def _mock_ai_stream(*args, **kwargs):
        yield "event: message\ndata: {\"text\": \"Chào em!\"}\n\n"
        yield "event: done\ndata: {}\n\n"

    mock_settings = {
        "student_rate_limit": 3,
        "global_gemini_rpm_limit": 100,
    }

    call_count = 0
    passed_limit = None

    async def fake_check_sliding_window(redis_client, key, limit, window_seconds=60):
        nonlocal call_count, passed_limit
        if "ratelimit:student" in key:
            passed_limit = limit
            call_count += 1
            if call_count > limit:
                return False, {
                    "allowed": False,
                    "current_count": call_count,
                    "remaining": 0,
                    "retry_after": 35,
                    "reset_at": int(time.time() + 35),
                }
            return True, {
                "allowed": True,
                "current_count": call_count,
                "remaining": limit - call_count,
                "retry_after": 0,
                "reset_at": int(time.time() + 60),
            }
        return True, {"allowed": True, "current_count": 1, "remaining": 99, "retry_after": 0, "reset_at": int(time.time() + 60)}

    with patch("orchestrator_bridge.process_query_with_orchestrator", side_effect=_mock_ai_stream):
        with patch("routers.chat.system_config_service.get_system_settings", return_value=mock_settings):
            with patch.object(RateLimiterService, "check_socratic_cooldown", return_value=(True, 0, 999.0)):
                with patch.object(RateLimiterService, "check_sliding_window", side_effect=fake_check_sliding_window):
                    # 3 câu đầu hợp lệ
                    for i in range(1, 4):
                        res = client.post("/chat/orchestrator", json={"session_id": session_id, "prompt": f"Câu {i}"})
                        assert res.status_code == 200

                    # Câu 4 -> Bị chặn 429
                    res4 = client.post("/chat/orchestrator", json={"session_id": session_id, "prompt": "Câu 4"})
                    assert res4.status_code == 429
                    assert passed_limit == 3
                    assert res4.headers.get("X-RateLimit-Limit") == "3"
                    assert res4.headers.get("X-RateLimit-Remaining") == "0"
                    assert res4.headers.get("Retry-After") == "35"
                    assert int(res4.headers.get("X-RateLimit-Reset", "0")) > 0


@pytest.mark.anyio
async def test_socratic_cooldown_cross_session_isolation():
    """
    US 11.1 - AC2: Socratic Cool-Down áp dụng theo session_id.
    Session A vừa hoàn thành câu trả lời (AI completion) bị phạt cool-down 5s
    không được làm ảnh hưởng đến Session B.
    """
    mock_redis = None # Test trên in-memory fallback

    # Session A hoàn thành câu trả lời lúc t0
    await RateLimiterService.record_ai_completion(mock_redis, "session-A")

    # Kiểm tra ngay lập tức (< 5s) tại session A -> Bị phạt
    ok_a, retry_a, delta_a = await RateLimiterService.check_socratic_cooldown(mock_redis, "session-A", cooldown_seconds=5)
    assert ok_a is False
    assert retry_a > 0

    # Cùng lúc đó, kiểm tra tại session B -> Không hề bị ảnh hưởng (cho qua)
    ok_b, retry_b, delta_b = await RateLimiterService.check_socratic_cooldown(mock_redis, "session-B", cooldown_seconds=5)
    assert ok_b is True
    assert retry_b == 0

