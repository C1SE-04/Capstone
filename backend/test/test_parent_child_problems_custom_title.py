# US 8.1 - Task T8.4: Tests cho bảng independence_scores và API /parent/child-problems
# Nghiệp vụ:
# 1. Nếu bài đó học sinh CÓ lưu vào sổ tay & tự gõ tên riêng (VD: "Toán tuổi mẹ con khó nhằn"):
#    -> Hiển thị đúng tên con tự đặt trên màn hình phụ huynh (tôn trọng cảm xúc và tư duy của con).
# 2. Nếu bài đó học sinh KHÔNG bấm lưu vào sổ tay (hoặc có lưu nhưng để trống tên):
#    -> Tự động dùng tên chuẩn sư phạm do AI sinh ra (friendly_parent_title) để hiển thị cho phụ huynh.
# 3. Đồng bộ custom_title vào bảng independence_scores khi lưu / sửa bookmark.

import sys
import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import dependencies
import models
from database import SessionLocal

client = TestClient(app)

TEST_STUDENT_ID = "test-stu-custom-title-81"
TEST_PARENT_ID  = "test-par-custom-title-81"

current_mock_user: dict = {"id": TEST_PARENT_ID, "role": "MONITOR"}

def mock_user():
    return current_mock_user

@pytest.fixture(autouse=True)
def override_user():
    app.dependency_overrides[dependencies.get_current_user] = mock_user
    yield
    app.dependency_overrides.pop(dependencies.get_current_user, None)

def cleanup_db(db):
    db.rollback()
    ids = [TEST_STUDENT_ID, TEST_PARENT_ID]
    db.query(models.BookmarkPlaylistItem).filter(
        models.BookmarkPlaylistItem.bookmark_id.in_(
            db.query(models.ProblemBookmark.id).filter(models.ProblemBookmark.student_id.in_(ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.ProblemBookmark).filter(models.ProblemBookmark.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.BookmarkPlaylist).filter(models.BookmarkPlaylist.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.Message).filter(
        models.Message.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id.in_(ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.SessionStats).filter(
        models.SessionStats.session_id.in_(
            db.query(models.Session.id).filter(models.Session.user_id.in_(ids))
        )
    ).delete(synchronize_session=False)
    db.query(models.SessionActiveInterval).filter(models.SessionActiveInterval.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.Session).filter(models.Session.user_id.in_(ids)).delete(synchronize_session=False)
    db.query(models.ParentStudentLink).filter(
        (models.ParentStudentLink.parent_id.in_(ids)) |
        (models.ParentStudentLink.student_id.in_(ids))
    ).delete(synchronize_session=False)
    db.query(models.User).filter(models.User.id.in_(ids)).delete(synchronize_session=False)
    db.commit()

def setup_users_and_link(db):
    student = models.User(
        id=TEST_STUDENT_ID,
        email="stu81@test.com",
        hashed_password="x",
        role="STUDENT",
        grade=5,
    )
    parent = models.User(
        id=TEST_PARENT_ID,
        email="par81@test.com",
        hashed_password="x",
        role="MONITOR",
    )
    db.add_all([student, parent])
    db.flush()

    link = models.ParentStudentLink(
        parent_id=TEST_PARENT_ID,
        student_id=TEST_STUDENT_ID,
    )
    db.add(link)
    db.commit()


def test_rule_1_student_bookmarks_with_custom_title():
    """
    Quy tắc 1: Nếu học sinh CÓ lưu vào sổ tay & tự gõ tên riêng (VD: 'Toán tuổi mẹ con khó nhằn'):
    -> API /parent/child-problems trả về đúng tên con tự đặt.
    """
    global current_mock_user
    db = SessionLocal()
    try:
        cleanup_db(db)
        setup_users_and_link(db)

        # Tạo session cho học sinh
        session = models.Session(
            id=uuid.uuid4().hex,
            user_id=TEST_STUDENT_ID,
            title="Phiên học Toán ngày 27/10",
        )
        db.add(session)
        db.commit()

        # Tạo tin nhắn của bài toán
        msg = models.Message(
            id=uuid.uuid4().hex,
            session_id=session.id,
            sender_type="USER",
            content="Hiện nay mẹ hơn con 28 tuổi. Tính tuổi mẹ và con biết tổng số tuổi là 48.",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        db.add(msg)
        db.commit()

        # Lưu điểm tự lực khi hoàn thành bài
        from routers.independence import save_independence_score
        score = save_independence_score(
            db=db,
            session_id=session.id,
            student_id=TEST_STUDENT_ID,
            custom_score=85,
            custom_hints=1,
            custom_not_understood=0,
            problem_text_input="Hiện nay mẹ hơn con 28 tuổi. Tính tuổi mẹ và con biết tổng số tuổi là 48.",
        )

        # Học sinh lưu vào Sổ tay với tên tự đặt: "Toán tuổi mẹ con khó nhằn"
        current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}
        custom_title_text = "Toán tuổi mẹ con khó nhằn"
        bm_resp = client.post("/bookmarks", json={
            "session_id": session.id,
            "title": custom_title_text,
            "note": "Bài này con làm mẹo rất hay!",
        })
        assert bm_resp.status_code == 201, f"Lưu bookmark thất bại: {bm_resp.text}"
        assert bm_resp.json()["title"] == custom_title_text

        # Kiểm tra bảng independence_scores đã đồng bộ custom_title
        db.refresh(score)
        assert score.custom_title == custom_title_text

        # Phụ huynh truy vấn API /parent/child-problems
        current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
        resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]

        # Kiểm tra tiêu đề hiển thị đúng tên con tự đặt
        assert item["problem_title"] == custom_title_text
        assert item["session_title"] == custom_title_text
        # friendly_parent_title chuẩn sư phạm vẫn được bảo toàn
        assert " – " in item["friendly_parent_title"]
        print(f"  [PASS] Rule 1: Phụ huynh thấy đúng tên con tự đặt: '{item['problem_title']}'")

    finally:
        cleanup_db(db)
        db.close()


def test_rule_1_another_custom_title():
    """
    Quy tắc 1: Con tự đặt tên khác: 'Bài hình học thầy Long dặn'.
    -> API hiển thị đúng 'Bài hình học thầy Long dặn'.
    """
    global current_mock_user
    db = SessionLocal()
    try:
        cleanup_db(db)
        setup_users_and_link(db)

        session = models.Session(
            id=uuid.uuid4().hex,
            user_id=TEST_STUDENT_ID,
            title="Phiên học Toán hình",
        )
        db.add(session)
        db.commit()

        msg = models.Message(
            id=uuid.uuid4().hex,
            session_id=session.id,
            sender_type="USER",
            content="Tính chu vi và diện tích hình thang có đáy lớn 12cm, đáy nhỏ 8cm, chiều cao 6cm.",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(msg)
        db.commit()

        from routers.independence import save_independence_score
        score = save_independence_score(
            db=db,
            session_id=session.id,
            student_id=TEST_STUDENT_ID,
            custom_score=90,
            problem_text_input="Tính chu vi và diện tích hình thang có đáy lớn 12cm, đáy nhỏ 8cm, chiều cao 6cm.",
        )

        current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}
        teacher_long_title = "Bài hình học thầy Long dặn"
        bm_resp = client.post("/bookmarks", json={
            "session_id": session.id,
            "title": teacher_long_title,
        })
        assert bm_resp.status_code == 201

        current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
        resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["problem_title"] == teacher_long_title
        assert item["session_title"] == teacher_long_title
        print(f"  [PASS] Rule 1 (2): Tên bài hình học: '{item['problem_title']}'")

    finally:
        cleanup_db(db)
        db.close()


def test_rule_2_student_did_not_bookmark():
    """
    Quy tắc 2: Học sinh KHÔNG bấm lưu vào sổ tay.
    -> Hệ thống tự động dùng tên chuẩn sư phạm do AI sinh ra (friendly_parent_title).
    Ví dụ: [Lớp 5] Chuyển động đều – Bài toán hai chuyển động ngược chiều
    """
    global current_mock_user
    db = SessionLocal()
    try:
        cleanup_db(db)
        setup_users_and_link(db)

        session = models.Session(
            id=uuid.uuid4().hex,
            user_id=TEST_STUDENT_ID,
            title="Toán chuyển động ngược chiều",
        )
        db.add(session)
        db.commit()

        msg = models.Message(
            id=uuid.uuid4().hex,
            session_id=session.id,
            sender_type="USER",
            content="Hai ô tô xuất phát từ A và B đi ngược chiều nhau. Quãng đường AB dài 180km. Vận tốc xe 1 là 40km/h, xe 2 là 50km/h. Hỏi sau bao lâu hai xe gặp nhau?",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        )
        db.add(msg)
        db.commit()

        from routers.independence import save_independence_score
        score = save_independence_score(
            db=db,
            session_id=session.id,
            student_id=TEST_STUDENT_ID,
            custom_score=95,
            problem_text_input="Hai ô tô xuất phát từ A và B đi ngược chiều nhau. Quãng đường AB dài 180km. Vận tốc xe 1 là 40km/h, xe 2 là 50km/h. Hỏi sau bao lâu hai xe gặp nhau?",
        )

        # Học sinh KHÔNG hề lưu vào Sổ tay
        # Phụ huynh truy vấn API
        current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
        resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]

        # custom_title phải là None vì con không đặt
        assert item["custom_title"] is None
        # problem_title và session_title phải là friendly_parent_title chuẩn sư phạm
        assert item["problem_title"] == item["friendly_parent_title"]
        assert item["session_title"] == item["friendly_parent_title"]
        assert "[Lớp 5]" in item["problem_title"]
        assert "Chuyển động đều" in item["problem_title"] or "chuyển động" in item["problem_title"].lower()
        print(f"  [PASS] Rule 2 (Không lưu sổ tay): Hiển thị tên sư phạm AI: '{item['problem_title']}'")

    finally:
        cleanup_db(db)
        db.close()


def test_rule_2_student_bookmarked_with_blank_title():
    """
    Quy tắc 2: Học sinh CÓ lưu vào sổ tay nhưng ĐỂ TRỐNG TÊN (title=None hoặc rỗng).
    -> Hệ thống tự động dùng tên chuẩn sư phạm do AI sinh ra (friendly_parent_title).
    """
    global current_mock_user
    db = SessionLocal()
    try:
        cleanup_db(db)
        setup_users_and_link(db)

        session = models.Session(
            id=uuid.uuid4().hex,
            user_id=TEST_STUDENT_ID,
            title="Toán tìm hai số tổng hiệu",
        )
        db.add(session)
        db.commit()

        msg = models.Message(
            id=uuid.uuid4().hex,
            session_id=session.id,
            sender_type="USER",
            content="Tìm hai số khi biết tổng là 100 và hiệu là 20.",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=8),
        )
        db.add(msg)
        db.commit()

        from routers.independence import save_independence_score
        score = save_independence_score(
            db=db,
            session_id=session.id,
            student_id=TEST_STUDENT_ID,
            custom_score=100,
            problem_text_input="Tìm hai số khi biết tổng là 100 và hiệu là 20.",
        )

        # Học sinh lưu vào Sổ tay nhưng để title là rỗng
        current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 4}
        bm_resp = client.post("/bookmarks", json={
            "session_id": session.id,
            "title": "",
            "note": "Để trống tên",
        })
        assert bm_resp.status_code == 201

        # Phụ huynh truy vấn API /parent/child-problems
        current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
        resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
        assert resp.status_code == 200
        item = resp.json()["items"][0]

        # custom_title phải là None vì con để trống
        assert item["custom_title"] is None
        # problem_title hiển thị tên chuẩn sư phạm
        assert item["problem_title"] == item["friendly_parent_title"]
        assert " – " in item["problem_title"]
        print(f"  [PASS] Rule 2 (Để trống tên): Hiển thị tên sư phạm AI: '{item['problem_title']}'")

    finally:
        cleanup_db(db)
        db.close()


def test_update_bookmark_title_syncs_to_parent_api():
    """
    Kiểm tra luồng PATCH /bookmarks/{id}: Học sinh đổi tên bài sau khi lưu.
    -> Màn hình phụ huynh cập nhật đúng tên mới.
    """
    global current_mock_user
    db = SessionLocal()
    try:
        cleanup_db(db)
        setup_users_and_link(db)

        session = models.Session(
            id=uuid.uuid4().hex,
            user_id=TEST_STUDENT_ID,
            title="Phiên làm bài",
        )
        db.add(session)
        db.commit()

        msg = models.Message(
            id=uuid.uuid4().hex,
            session_id=session.id,
            sender_type="USER",
            content="Tìm phân số biết tử số kém mẫu số 5 đơn vị và rút gọn được 2/3.",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        db.add(msg)
        db.commit()

        from routers.independence import save_independence_score
        score = save_independence_score(
            db=db,
            session_id=session.id,
            student_id=TEST_STUDENT_ID,
            custom_score=75,
            problem_text_input="Tìm phân số biết tử số kém mẫu số 5 đơn vị và rút gọn được 2/3.",
        )

        # Ban đầu học sinh để trống tên khi lưu
        current_mock_user = {"id": TEST_STUDENT_ID, "role": "STUDENT", "grade": 5}
        create_resp = client.post("/bookmarks", json={"session_id": session.id})
        bm_id = create_resp.json()["id"]

        # Sau đó học sinh chỉnh sửa tên bài: "Bài phân số hóc búa nhất tuần"
        new_title = "Bài phân số hóc búa nhất tuần"
        patch_resp = client.patch(f"/bookmarks/{bm_id}", json={"title": new_title})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["title"] == new_title

        # Phụ huynh xem lại
        current_mock_user = {"id": TEST_PARENT_ID, "role": "MONITOR"}
        resp = client.get(f"/parent/child-problems?student_id={TEST_STUDENT_ID}")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["problem_title"] == new_title
        assert item["custom_title"] == new_title
        print(f"  [PASS] Patch bookmark: Phụ huynh thấy tên mới '{item['problem_title']}'")

    finally:
        cleanup_db(db)
        db.close()
