"""
T10.2.11 — Async Load Simulation Script: Mô Phỏng 20 Học Sinh Chat Đồng Thời
=============================================================================
Mục đích:
  1. Giả lập 20 học sinh đồng thời gửi câu hỏi Toán qua `POST /chat/orchestrator` (`asyncio` + `httpx`).
  2. Gửi kèm request sai schema (`422` -> `4xx`) để kiểm chứng ghi nhận lỗi Client (AC-KPI-03).
  3. Đo độ trễ thực tế của từng học sinh (End-to-End, P50, P95, P99, TTFT chunk đầu).
  4. Truy vấn `GET /admin/kpi/overview` và `GET /admin/kpi/throughput?range=1h` trước và sau tải
     để chứng minh Dashboard nhảy số real-time (RPM & Total Requests) không cần chờ batch 60 giây.

Cách sử dụng:
  - Chế độ In-Process (tự test trực tiếp FastAPI app với ASGI transport + mock Gemini stream):
      .\venv\Scripts\python.exe scripts/simulate_20_students_load_test.py --in-process

  - Chế độ Live Server (khi Backend server đang chạy ở localhost:8000):
      .\venv\Scripts\python.exe scripts/simulate_20_students_load_test.py --base-url http://127.0.0.1:8000 --admin-token <JWT>
"""

import argparse
import asyncio
import json
import math
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import httpx

# Đảm bảo import được các module trong backend/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


MATH_QUESTIONS = [
    "Giải phương trình bậc nhất 2x + 5 = 15 giúp em với ạ.",
    "Làm sao tìm ước chung lớn nhất của 24 và 36 ạ?",
    "Một hình chữ nhật có chu vi 48cm, chiều dài hơn chiều rộng 4cm. Tính diện tích?",
    "Tính giá trị biểu thức A = 3*(x - 2) + 4 tại x = 5.",
    "Em chưa hiểu cách quy đồng mẫu số hai phân số 3/4 và 5/6.",
    "Chứng minh tổng ba góc trong một tam giác bằng 180 độ như thế nào ạ?",
    "Tìm x biết x/3 = 12/9.",
    "Giải bất phương trình 3x - 7 > 2 giúp em với.",
    "Cách phân tích đa thức x^2 - 9 thành nhân tử là gì ạ?",
    "Một ô tô đi quãng đường 120km trong 2.5 giờ, tính vận tốc trung bình.",
    "Tính chu vi hình tròn có bán kính r = 7cm.",
    "Định lý Pytago áp dụng cho loại tam giác nào ạ?",
    "Tìm hai số biết tổng bằng 35 và hiệu bằng 9.",
    "Số nguyên tố nhỏ nhất là số nào và vì sao 1 không phải số nguyên tố?",
    "Tính diện tích hình thang có đáy lớn 10cm, đáy nhỏ 6cm, chiều cao 5cm.",
    "Giải hệ phương trình x + y = 10 và x - y = 2.",
    "Làm sao rút gọn phân số 36/48 về tối giản?",
    "Tính căn bậc hai số học của 144 giúp em với.",
    "Tam giác cân có một góc ở đáy bằng 50 độ thì góc ở đỉnh bằng bao nhiêu?",
    "Nếu tăng cạnh hình vuông lên 2 lần thì diện tích tăng mấy lần ạ?",
]


@dataclass
class StudentRunResult:
    student_index: int
    status_code: int
    e2e_ms: float
    ttft_ms: Optional[float]
    error: Optional[str] = None


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return round(ordered[idx], 1)


async def _simulate_one_student(
    client: httpx.AsyncClient,
    idx: int,
    student_headers: Dict[str, str],
    endpoint: str,
    session_id: str,
) -> StudentRunResult:
    """Mô phỏng 1 học sinh gửi câu hỏi Toán và đọc luồng phản hồi SSE."""
    question = MATH_QUESTIONS[idx % len(MATH_QUESTIONS)]
    payload = {
        "session_id": session_id,
        "prompt": question,
        "grade_level": 4 + (idx % 6),
    }

    t_start = time.perf_counter()
    ttft_ms: Optional[float] = None
    try:
        async with client.stream("POST", endpoint, json=payload, headers=student_headers) as resp:
            async for chunk in resp.aiter_bytes():
                if chunk and ttft_ms is None:
                    ttft_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
            e2e_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
            if ttft_ms is None:
                ttft_ms = e2e_ms
            return StudentRunResult(
                student_index=idx + 1,
                status_code=resp.status_code,
                e2e_ms=e2e_ms,
                ttft_ms=ttft_ms,
            )
    except Exception as exc:
        e2e_ms = round((time.perf_counter() - t_start) * 1000.0, 1)
        return StudentRunResult(
            student_index=idx + 1,
            status_code=500,
            e2e_ms=e2e_ms,
            ttft_ms=None,
            error=str(exc),
        )


async def _send_invalid_4xx_probe(
    client: httpx.AsyncClient,
    student_headers: Dict[str, str],
    endpoint: str,
) -> int:
    """Gửi payload thiếu field bắt buộc để kiểm tra ghi nhận HTTP 422 (Client Error)."""
    try:
        res = await client.post(endpoint, json={"invalid_field": True}, headers=student_headers)
        return res.status_code
    except Exception:
        return 0


def _prepare_in_process_auth_and_session() -> tuple[Dict[str, str], Dict[str, str], str]:
    """Chuẩn bị JWT Admin/Student và session hợp lệ trong DB local cho --in-process."""
    import auth
    import models
    from database import SessionLocal

    db = SessionLocal()
    try:
        admin_user = db.query(models.User).filter(models.User.role == "ADMIN").first()
        if not admin_user:
            admin_user = models.User(
                username=f"sim_admin_{uuid.uuid4().hex[:6]}",
                email=f"sim_admin_{uuid.uuid4().hex[:6]}@socratickid.test",
                hashed_password="sim-hashed-password",
                role="ADMIN",
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        student_user = db.query(models.User).filter(models.User.role == "STUDENT").first()
        if not student_user:
            student_user = models.User(
                username=f"sim_student_{uuid.uuid4().hex[:6]}",
                email=f"sim_student_{uuid.uuid4().hex[:6]}@socratickid.test",
                hashed_password="sim-hashed-password",
                role="STUDENT",
                grade=7,
            )
            db.add(student_user)
            db.commit()
            db.refresh(student_user)

        sim_session_id = "sim-us10-2-loadtest-session"
        sim_session = db.query(models.Session).filter(models.Session.id == sim_session_id).first()
        if not sim_session:
            sim_session = models.Session(
                id=sim_session_id,
                user_id=student_user.id,
                title="US 10.2 Concurrent Load Test",
            )
            db.add(sim_session)
            db.commit()

        admin_token = auth.create_access_token({"sub": admin_user.username, "role": "ADMIN"})
        student_token = auth.create_access_token({"sub": student_user.username, "role": "STUDENT"})
        return (
            {"Authorization": f"Bearer {admin_token}"},
            {"Authorization": f"Bearer {student_token}"},
            sim_session_id,
        )
    finally:
        db.close()


async def run_load_simulation(
    students: int = 20,
    base_url: str = "http://127.0.0.1:8000",
    endpoint: str = "/chat/orchestrator",
    in_process: bool = False,
    admin_token: str = "",
    student_token: str = "",
    session_id: str = "",
    client_error_probes: int = 2,
) -> bool:
    """Thực thi kịch bản tải đồng thời và xác minh KPI Dashboard nhảy số real-time."""
    print("=" * 72)
    print(f"SOCRATICKID US10.2 LOAD TEST: {students} HOC SINH CHAT DONG THOI")
    print("=" * 72)

    client_kwargs: Dict[str, Any] = {"timeout": 30.0}
    patches = []

    if in_process:
        from main import app
        from workers.telemetry_batch_worker import _accumulator, _live_minute_counters

        # Reset counters cục bộ để thấy rõ mức nhảy số do chính phiên mô phỏng tạo ra
        _accumulator.reset()
        _live_minute_counters.clear()

        admin_headers, student_headers, resolved_session_id = _prepare_in_process_auth_and_session()
        if session_id:
            resolved_session_id = session_id

        transport = httpx.ASGITransport(app=app)
        client_kwargs["transport"] = transport
        client_kwargs["base_url"] = "http://testserver"

        # Mock orchestrator stream generator (sync generator như thực tế StreamingResponse)
        def _fake_orchestrator(*args, **kwargs):
            from middleware.gemini_telemetry import _push_token_event

            time.sleep(0.025)
            _push_token_event(180, 65, "gemini-3.8-flash", "Chat", ttft_ms=25)
            yield f"event: orchestrator\ndata: {json.dumps({'target_agent': 'socratic_tutor', 'teaching_mode': 'socratic'})}\n\n"
            yield f"event: message\ndata: {json.dumps({'text': 'Chào em! Bước đầu tiên em thử chuyển hằng số sang vế phải nhé?'}, ensure_ascii=False)}\n\n"
            yield f"event: done\ndata: {json.dumps({'emotion': 'happy'})}\n\n"

        patches.append(
            patch("orchestrator_bridge.process_query_with_orchestrator", side_effect=_fake_orchestrator)
        )
    else:
        admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        student_headers = (
            {"Authorization": f"Bearer {student_token}"}
            if student_token
            else admin_headers
        )
        client_kwargs["base_url"] = base_url
        resolved_session_id = session_id

    for p in patches:
        p.start()

    try:
        async with httpx.AsyncClient(**client_kwargs) as client:
            if not resolved_session_id:
                # Ở chế độ live server nếu không truyền --session-id, tự tạo 1 session thật
                sess_res = await client.post(
                    "/sessions",
                    json={"title": "US 10.2 Load Test Session"},
                    headers=student_headers,
                )
                if sess_res.status_code in (200, 201):
                    resolved_session_id = sess_res.json().get("id", f"guest-loadtest-{uuid.uuid4().hex[:6]}")
                else:
                    resolved_session_id = f"guest-loadtest-{uuid.uuid4().hex[:6]}"

            # 1. Lấy KPI Overview & Throughput trước mô phỏng
            before_ov_res = await client.get("/admin/kpi/overview", headers=admin_headers)
            before_tp_res = await client.get("/admin/kpi/throughput?range=1h", headers=admin_headers)
            if before_ov_res.status_code != 200 or before_tp_res.status_code != 200:
                print(
                    f"[ERROR] Không thể truy cập Admin KPI endpoints "
                    f"(overview={before_ov_res.status_code}, throughput={before_tp_res.status_code}). "
                    f"Vui lòng truyền --admin-token hợp lệ hoặc dùng --in-process."
                )
                return False

            before_ov = before_ov_res.json()
            before_tp = before_tp_res.json()
            before_reqs = before_ov["throughput"]["total_requests_today"]
            before_rpm = before_ov["throughput"]["rpm_current"]
            before_tp_rpm = before_tp.get("current_rpm", 0)
            before_tokens = before_ov["tokens_and_cost"]["total_tokens_today"]

            print(
                f"[BEFORE] Total Requests Today: {before_reqs} | "
                f"Overview RPM: {before_rpm} | Throughput 1h Live RPM: {before_tp_rpm} | "
                f"Tokens: {before_tokens:,}"
            )

            # 2. Kích hoạt 20 học sinh gửi câu hỏi đồng thời bằng asyncio.gather
            t_batch_start = time.perf_counter()
            student_tasks = [
                _simulate_one_student(client, idx, student_headers, endpoint, resolved_session_id)
                for idx in range(students)
            ]
            error_tasks = [
                _send_invalid_4xx_probe(client, student_headers, endpoint)
                for _ in range(client_error_probes)
            ]
            results_raw = await asyncio.gather(*student_tasks, *error_tasks)
            t_batch_ms = round((time.perf_counter() - t_batch_start) * 1000.0, 1)

            student_results: List[StudentRunResult] = results_raw[:students]
            probe_statuses: List[int] = results_raw[students:]

            if in_process:
                # Chạy chu kỳ drain queue tương đương TelemetryBatchWorker (1s loop khi chạy server thật)
                from middleware.telemetry_middleware import telemetry_queue
                from workers.telemetry_batch_worker import _flush_events

                drained_batch: List[Dict[str, Any]] = []
                while not telemetry_queue.empty():
                    drained_batch.append(telemetry_queue.get_nowait())
                if drained_batch:
                    await _flush_events(None, drained_batch)
            else:
                await asyncio.sleep(1.2)

            # 3. Đọc lại Admin KPI Overview & Throughput sau mô phỏng
            after_ov = (await client.get("/admin/kpi/overview", headers=admin_headers)).json()
            after_tp = (await client.get("/admin/kpi/throughput?range=1h", headers=admin_headers)).json()

            after_reqs = after_ov["throughput"]["total_requests_today"]
            after_rpm = after_ov["throughput"]["rpm_current"]
            after_tp_rpm = after_tp.get("current_rpm", 0)
            after_tokens = after_ov["tokens_and_cost"]["total_tokens_today"]
            after_4xx = after_ov["reliability"].get("status_4xx_count_today", 0)

            latencies = [r.e2e_ms for r in student_results]
            ttfts = [r.ttft_ms for r in student_results if r.ttft_ms is not None]
            ok_count = sum(1 for r in student_results if 200 <= r.status_code < 300)
            err_4xx_count = sum(1 for r in student_results if 400 <= r.status_code < 500) + sum(
                1 for s in probe_statuses if 400 <= s < 500
            )
            err_5xx_count = sum(1 for r in student_results if r.status_code >= 500)

            delta_rpm = after_tp_rpm - before_tp_rpm
            delta_reqs = after_reqs - before_reqs

            print("-" * 72)
            print(f"[BATCH] Hoàn tất {students} luồng chat song song + {client_error_probes} 4xx probes trong {t_batch_ms}ms")
            print(f"  - Thành công (2xx): {ok_count}/{students}")
            print(f"  - Lỗi Client (4xx): {err_4xx_count} (Dashboard recorded 4xx today: {after_4xx})")
            print(f"  - Lỗi Server (5xx): {err_5xx_count}")
            print(
                f"  - Độ trễ E2E: P50={_percentile(latencies, 50)}ms | "
                f"P95={_percentile(latencies, 95)}ms | P99={_percentile(latencies, 99)}ms"
            )
            if ttfts:
                print(f"  - TTFT trung bình: {round(sum(ttfts) / len(ttfts), 1)}ms")
            print("-" * 72)
            print(
                f"[AFTER ] Total Requests Today: {after_reqs} (delta: +{delta_reqs}) | "
                f"Overview RPM: {after_rpm} | Throughput 1h Live RPM: {after_tp_rpm} (delta: +{delta_rpm}) | "
                f"Tokens: {after_tokens:,}"
            )

            passed = ok_count == students and delta_rpm >= students and err_5xx_count == 0
            print(f"[VERDICT] {'PASS - Dashboard nhảy số RPM real-time chính xác!' if passed else 'CHECK NEEDED'}")
            return passed
    finally:
        for p in reversed(patches):
            p.stop()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mô phỏng 20 học sinh chat đồng thời và kiểm tra nhảy số KPI real-time."
    )
    parser.add_argument("--students", type=int, default=20, help="Số học sinh gửi chat đồng thời (mặc định: 20)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="URL Backend FastAPI")
    parser.add_argument("--endpoint", default="/chat/orchestrator", help="Endpoint chat kiểm thử")
    parser.add_argument("--in-process", action="store_true", help="Chạy trực tiếp qua ASGI trong memory không cần server riêng")
    parser.add_argument("--admin-token", default=os.getenv("ADMIN_JWT_TOKEN", ""), help="JWT token Admin")
    parser.add_argument("--student-token", default=os.getenv("STUDENT_JWT_TOKEN", ""), help="JWT token Student")
    parser.add_argument("--session-id", default="", help="Session ID dùng chung (nếu muốn cố định)")
    parser.add_argument("--client-errors", type=int, default=2, help="Số probe lỗi 4xx kèm theo để kiểm tra AC-KPI-03")
    args = parser.parse_args()

    ok = asyncio.run(
        run_load_simulation(
            students=args.students,
            base_url=args.base_url,
            endpoint=args.endpoint,
            in_process=args.in_process,
            admin_token=args.admin_token,
            student_token=args.student_token,
            session_id=args.session_id,
            client_error_probes=args.client_errors,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
