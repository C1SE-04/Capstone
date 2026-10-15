import sys
import os
import uuid
from datetime import datetime, timedelta, timezone, date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
import dependencies
import models
from database import SessionLocal
from routers.metrics import update_session_active_interval

client = TestClient(app)

TEST_STUDENT_ID = "test-student-active-metrics"


def mock_get_current_user():
    return {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}


app.dependency_overrides[dependencies.get_current_user] = mock_get_current_user


def setup_test_data(db):
    # Dọn dẹp dữ liệu cũ của test student
    db.query(models.SessionActiveInterval).filter(
        models.SessionActiveInterval.user_id == TEST_STUDENT_ID
    ).delete()
    db.query(models.Session).filter(models.Session.user_id == TEST_STUDENT_ID).delete()
    db.query(models.User).filter(models.User.id == TEST_STUDENT_ID).delete()
    db.commit()

    user = models.User(
        id=TEST_STUDENT_ID,
        email="test_active@socratickid.local",
        hashed_password="hash",
        role="STUDENT",
        grade=5,
    )
    db.add(user)
    db.commit()


def test_restart_metric_endpoint():
    print("\n--- TEST: POST /metrics/restart (Task #169) ---")
    db = SessionLocal()
    try:
        setup_test_data(db)

        # 1. Gọi /metrics/restart khi chưa có session
        res = client.post(
            "/metrics/restart",
            json={
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                "restart_time": datetime.now(timezone.utc).isoformat(),
                "session_id": None,
            },
        )
        assert res.status_code == 200, f"Status code: {res.status_code}, {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["session_id"] is not None
        assert data["interval_id"] is not None
        assert data["active_seconds"] == 0

        created_session_id = data["session_id"]

        # Kiểm tra trong DB có bản ghi session_active_intervals
        interval = (
            db.query(models.SessionActiveInterval)
            .filter(models.SessionActiveInterval.id == data["interval_id"])
            .first()
        )
        assert interval is not None
        assert interval.session_id == created_session_id
        assert interval.user_id == TEST_STUDENT_ID
        print("[OK] Created first active interval on /metrics/restart without session_id")

        # 2. Gọi lại /metrics/restart với session_id cụ thể
        res2 = client.post(
            "/metrics/restart",
            json={
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                "restart_time": datetime.now(timezone.utc).isoformat(),
                "session_id": created_session_id,
            },
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["success"] is True
        assert data2["interval_id"] != data["interval_id"]
        print("[OK] Created subsequent active interval with explicit session_id")
    finally:
        db.close()


def test_active_interval_update_and_idle_detection():
    print("\n--- TEST: Active Interval Update & Idle Detection Logic ---")
    db = SessionLocal()
    try:
        setup_test_data(db)

        # Tạo 1 session
        sess = models.Session(id=uuid.uuid4().hex, user_id=TEST_STUDENT_ID, title="Test Chat")
        db.add(sess)
        db.commit()

        t0 = datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc)
        # Bắt đầu active lúc t0
        int1 = update_session_active_interval(db, sess.id, timestamp=t0)
        assert int1 is not None
        assert int1.active_seconds == 0

        # Tương tác tiếp lúc t0 + 2 phút (gap = 120s <= 600s)
        t1 = t0 + timedelta(minutes=2)
        int2 = update_session_active_interval(db, sess.id, timestamp=t1)
        assert int2.id == int1.id  # Vẫn là interval cũ
        assert int2.active_seconds == 120
        print("[OK] Extended active interval within 10 minutes (gap = 2m, active = 120s)")

        # Tương tác tiếp lúc t0 + 5 phút (gap = 3m <= 600s)
        t2 = t0 + timedelta(minutes=5)
        int3 = update_session_active_interval(db, sess.id, timestamp=t2)
        assert int3.id == int1.id
        assert int3.active_seconds == 300  # 5 phút
        print("[OK] Extended active interval to 5m (active = 300s)")

        # Học sinh IDLE: 15 phút sau mới tương tác lại (gap = 15m > 10m idle threshold)
        t3 = t2 + timedelta(minutes=15)
        int4 = update_session_active_interval(db, sess.id, timestamp=t3)
        assert int4.id != int1.id  # Đã mở một interval mới!
        assert int4.active_seconds == 0

        # Kiểm tra interval cũ vẫn giữ nguyên 300s, không bị cộng 15 phút idle
        db.refresh(int1)
        assert int1.active_seconds == 300
        print("[OK] Idle detected (> 10m). Old interval locked at 300s, new interval created at 0s")
    finally:
        db.close()


def test_metrics_study_time_excludes_idle():
    print("\n--- TEST: GET /metrics/study-time excludes idle (Task #168, AC2) ---")
    db = SessionLocal()
    try:
        setup_test_data(db)

        # Mô phỏng AC2:
        # - Học sinh vào chat, idle 10 phút.
        # - Bấm "Đang học" lúc restart_t.
        # - Tương tác 5 phút (300 active_seconds).
        sess = models.Session(id=uuid.uuid4().hex, user_id=TEST_STUDENT_ID, title="AC2 Session")
        db.add(sess)
        db.commit()

        # Tạo interval 5 phút học sau khi restart vào ngày hôm nay
        today_date = date.today()
        restart_t = datetime.combine(today_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=14)
        active_end_t = restart_t + timedelta(minutes=5)

        interval = models.SessionActiveInterval(
            session_id=sess.id,
            user_id=TEST_STUDENT_ID,
            start_time=restart_t,
            end_time=active_end_t,
            active_seconds=300,  # Đúng 5 phút (300s)
        )
        db.add(interval)
        db.commit()

        # Gọi API /metrics/study-time
        res = client.get(f"/metrics/study-time?student_id={TEST_STUDENT_ID}&mode=weekly")
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "weekly"

        today_metric = next((d for d in data["data"] if d["date"] == str(today_date)), None)
        assert today_metric is not None
        assert today_metric["minutes"] == 5, f"Expected 5 minutes, got {today_metric['minutes']}"
        assert data["total_minutes"] == 5
        print(f"[OK] AC2 verified! Parent dashboard records exactly {today_metric['minutes']} minutes (excluding idle)!")

        # Kiểm tra alias /metrics
        res_alias = client.get(f"/metrics?student_id={TEST_STUDENT_ID}&mode=weekly")
        assert res_alias.status_code == 200
        assert res_alias.json()["total_minutes"] == 5
        print("[OK] Alias GET /metrics works identically")

        # Kiểm tra mode monthly
        res_monthly = client.get(f"/metrics/study-time?student_id={TEST_STUDENT_ID}&mode=monthly")
        assert res_monthly.status_code == 200
        assert res_monthly.json()["total_minutes"] == 5
        print("[OK] Mode monthly sums active minutes accurately")
    finally:
        # Dọn dẹp dữ liệu test
        db.query(models.SessionActiveInterval).filter(
            models.SessionActiveInterval.user_id == TEST_STUDENT_ID
        ).delete()
        db.query(models.Session).filter(models.Session.user_id == TEST_STUDENT_ID).delete()
        db.query(models.User).filter(models.User.id == TEST_STUDENT_ID).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_restart_metric_endpoint()
    test_active_interval_update_and_idle_detection()
    test_metrics_study_time_excludes_idle()
    print("\nALL IDLE & ACTIVE METRICS TESTS PASSED!")
