"""
US 8.2: Test suite cho:
1. Sổ tay Playlist (YouTube-style):
   - CRUD bookmark_playlists
   - Lưu bài toán kèm tên học sinh đặt (title) & gắn vào playlists
   - Lọc bài toán theo playlist_id
2. Bảng xếp hạng chuỗi ngày học (Streak Leaderboard):
   - API GET /metrics/streak-leaderboard
   - Lọc theo khối lớp (Lớp 4 - 9) & Toàn server
   - Bảo vệ riêng tư (chỉ hiện display_name, avatar, grade, streak_days, rank)

Chạy:
    $env:PYTHONIOENCODING="utf-8"; python test/test_playlist_and_streak_leaderboard.py
"""
import sys
import os
import uuid
from datetime import datetime, date, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import models
import schemas
from database import SessionLocal
from routers import bookmarks as bookmarks_router
from routers import metrics as metrics_router


def make_id() -> str:
    return uuid.uuid4().hex


def get_db():
    return SessionLocal()


def _cleanup(db, student_ids: list[str]):
    for sid in student_ids:
        # Xóa bookmark_playlist_items
        db.query(models.BookmarkPlaylistItem).filter(
            models.BookmarkPlaylistItem.playlist_id.in_(
                db.query(models.BookmarkPlaylist.id).filter(models.BookmarkPlaylist.student_id == sid)
            )
        ).delete(synchronize_session=False)

        # Xóa bookmark_playlists
        db.query(models.BookmarkPlaylist).filter(models.BookmarkPlaylist.student_id == sid).delete()

        # Xóa problem_bookmarks
        db.query(models.ProblemBookmark).filter(models.ProblemBookmark.student_id == sid).delete()

        # Xóa metrics & sessions
        db.query(models.IndependenceScore).filter(models.IndependenceScore.student_id == sid).delete()
        db.query(models.SessionActiveInterval).filter(models.SessionActiveInterval.user_id == sid).delete()
        db.query(models.Message).filter(
            models.Message.session_id.in_(
                db.query(models.Session.id).filter(models.Session.user_id == sid)
            )
        ).delete(synchronize_session=False)
        db.query(models.Session).filter(models.Session.user_id == sid).delete()
        db.query(models.User).filter(models.User.id == sid).delete()
    db.commit()


def _create_student(db, email_prefix: str, grade: int = 5) -> models.User:
    user = models.User(
        id=make_id(),
        email=f"{email_prefix}_{make_id()[:6]}@socratic.edu.vn",
        hashed_password="hash",
        role="STUDENT",
        grade=grade,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_session_with_message(db, user_id: str, content: str = "Tìm x biết 2x + 5 = 15") -> models.Session:
    sess = models.Session(id=make_id(), user_id=user_id, title="Phiên giải toán")
    db.add(sess)
    db.flush()

    msg = models.Message(
        id=make_id(),
        session_id=sess.id,
        sender_type="USER",
        content=content,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db.add(msg)
    db.commit()
    db.refresh(sess)
    return sess


# ==============================================================================
# TESTS
# ==============================================================================

def test_auto_create_default_playlist():
    """TEST 1: Tự động khởi tạo playlist mặc định '⭐ Yêu thích' khi học sinh truy cập lần đầu."""
    db = get_db()
    s = _create_student(db, "student_default_pl")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        playlists = bookmarks_router.list_playlists(current_user=user_dict, db=db)

        assert len(playlists) >= 1
        default_pl = next((p for p in playlists if p.is_default), None)
        assert default_pl is not None
        assert "Yêu thích" in default_pl.name
        assert default_pl.item_count == 0
        print("[PASS] Test 1: Tự động khởi tạo playlist mặc định '⭐ Yêu thích' thành công.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_create_and_manage_playlist():
    """TEST 2: Học sinh tạo playlist mới và cập nhật tên, màu sắc."""
    db = get_db()
    s = _create_student(db, "student_manage_pl")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}

        # Tạo mới playlist "Ôn thi HK1"
        create_body = schemas.PlaylistCreate(
            name="Ôn thi HK1",
            description="Các bài toán hình học khó",
            color="#EF4444",
        )
        new_pl = bookmarks_router.create_playlist(body=create_body, current_user=user_dict, db=db)
        assert new_pl.name == "Ôn thi HK1"
        assert new_pl.description == "Các bài toán hình học khó"
        assert new_pl.color == "#EF4444"
        assert new_pl.item_count == 0

        # Cập nhật playlist
        update_body = schemas.PlaylistUpdate(
            name="Ôn thi HK1 - Hình Học",
            color="#3B82F6",
        )
        updated_pl = bookmarks_router.update_playlist(
            playlist_id=new_pl.id,
            body=update_body,
            current_user=user_dict,
            db=db,
        )
        assert updated_pl.name == "Ôn thi HK1 - Hình Học"
        assert updated_pl.color == "#3B82F6"

        print("[PASS] Test 2: Tạo và cập nhật thông tin Playlist thành công.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_bookmark_with_custom_title_and_playlist():
    """TEST 3: Lưu bài toán kèm Tên bài học sinh tự đặt và gắn vào Playlist."""
    db = get_db()
    s = _create_student(db, "student_title_bm")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        sess = _create_session_with_message(db, s.id, "Một hình chữ nhật có chu vi 40cm...")

        # Tạo playlist
        pl = bookmarks_router.create_playlist(
            body=schemas.PlaylistCreate(name="Toán Chu Vi Diện Tích"),
            current_user=user_dict,
            db=db,
        )

        # Lưu bookmark kèm title và playlist_ids
        custom_title = "Bài toán chu vi hình chữ nhật lớp 5"
        bm_resp = bookmarks_router.create_bookmark(
            body=schemas.BookmarkCreate(
                session_id=sess.id,
                title=custom_title,
                note="Nhớ công thức: (dài + rộng) * 2",
                playlist_ids=[pl.id],
            ),
            current_user=user_dict,
            db=db,
        )

        assert bm_resp.title == custom_title
        assert pl.id in bm_resp.playlist_ids

        # Kiểm tra chi tiết bookmark
        get_resp = bookmarks_router.get_bookmark(bookmark_id=bm_resp.id, current_user=user_dict, db=db)
        assert get_resp.title == custom_title
        assert pl.id in get_resp.playlist_ids

        # Kiểm tra item_count trong playlist
        pl_detail = bookmarks_router.get_playlist_detail(playlist_id=pl.id, current_user=user_dict, db=db)
        assert pl_detail.item_count == 1
        assert len(pl_detail.items) == 1
        assert pl_detail.items[0].title == custom_title

        print("[PASS] Test 3: Lưu bài toán kèm Tên bài học sinh đặt & gắn vào Playlist thành công.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_create_playlist_with_initial_bookmark():
    """TEST 4: Nút '+ Tạo danh sách mới' trong Popup: Tự động lưu luôn bài toán vào playlist mới tạo."""
    db = get_db()
    s = _create_student(db, "student_popup_new_pl")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        sess = _create_session_with_message(db, s.id, "Tính diện tích hình thang")

        # Lưu bookmark trước
        bm = bookmarks_router.create_bookmark(
            body=schemas.BookmarkCreate(
                session_id=sess.id,
                title="Diện tích hình thang",
            ),
            current_user=user_dict,
            db=db,
        )

        # Tạo playlist mới kèm initial_bookmark_id (hành vi khi bấm Lưu ở Popup Sổ tay)
        new_pl = bookmarks_router.create_playlist(
            body=schemas.PlaylistCreate(
                name="Hình thang nâng cao",
                initial_bookmark_id=bm.id,
            ),
            current_user=user_dict,
            db=db,
        )

        assert new_pl.item_count == 1

        # Kiểm tra playlist detail
        pl_detail = bookmarks_router.get_playlist_detail(playlist_id=new_pl.id, current_user=user_dict, db=db)
        assert len(pl_detail.items) == 1
        assert pl_detail.items[0].id == bm.id

        print("[PASS] Test 4: Tạo playlist mới kèm initial_bookmark_id lưu bài toán ngay lập tức thành công.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_filter_bookmarks_by_playlist():
    """TEST 5: Lọc danh sách bài toán Sổ Tay theo playlist_id (Sidebar Sổ tay)."""
    db = get_db()
    s = _create_student(db, "student_filter_pl")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        sess1 = _create_session_with_message(db, s.id, "Đề bài số 1: Phân số thập phân")
        sess2 = _create_session_with_message(db, s.id, "Đề bài số 2: Tỉ số phần trăm")

        pl_phan_so = bookmarks_router.create_playlist(
            body=schemas.PlaylistCreate(name="Phân số"),
            current_user=user_dict,
            db=db,
        )

        # bm1 thuộc pl_phan_so, bm2 không thuộc
        bm1 = bookmarks_router.create_bookmark(
            body=schemas.BookmarkCreate(
                session_id=sess1.id,
                title="Bài phân số thập phân",
                playlist_ids=[pl_phan_so.id],
            ),
            current_user=user_dict,
            db=db,
        )

        bm2 = bookmarks_router.create_bookmark(
            body=schemas.BookmarkCreate(
                session_id=sess2.id,
                title="Bài tỉ số phần trăm",
            ),
            current_user=user_dict,
            db=db,
        )

        # Lọc theo pl_phan_so: chỉ ra bm1
        filtered = bookmarks_router.list_bookmarks(
            playlist_id=pl_phan_so.id,
            current_user=user_dict,
            db=db,
        )
        assert len(filtered) == 1
        assert filtered[0].id == bm1.id

        # Không lọc playlist (Tất cả bài toán): ra cả 2
        all_bm = bookmarks_router.list_bookmarks(
            playlist_id=None,
            current_user=user_dict,
            db=db,
        )
        assert len(all_bm) >= 2

        print("[PASS] Test 5: Lọc Sổ Tay theo Playlist ID hoạt động chính xác.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_update_bookmark_title_and_playlist_sync():
    """TEST 6: Cập nhật tiêu đề bài toán và đồng bộ danh sách playlist (checkbox popup)."""
    db = get_db()
    s = _create_student(db, "student_sync_pl")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        sess = _create_session_with_message(db, s.id, "Đề bài đại số")

        pl_a = bookmarks_router.create_playlist(body=schemas.PlaylistCreate(name="Danh sách A"), current_user=user_dict, db=db)
        pl_b = bookmarks_router.create_playlist(body=schemas.PlaylistCreate(name="Danh sách B"), current_user=user_dict, db=db)

        # Tạo bookmark chỉ gắn pl_a
        bm = bookmarks_router.create_bookmark(
            body=schemas.BookmarkCreate(session_id=sess.id, title="Tiêu đề cũ", playlist_ids=[pl_a.id]),
            current_user=user_dict,
            db=db,
        )
        assert pl_a.id in bm.playlist_ids
        assert pl_b.id not in bm.playlist_ids

        # Học sinh sửa lại tiêu đề và đổi checkbox: uncheck A, check B
        updated_bm = bookmarks_router.update_bookmark(
            bookmark_id=bm.id,
            body=schemas.BookmarkUpdate(
                title="Tiêu đề mới do con đặt",
                playlist_ids=[pl_b.id],
            ),
            current_user=user_dict,
            db=db,
        )
        assert updated_bm.title == "Tiêu đề mới do con đặt"
        assert pl_b.id in updated_bm.playlist_ids
        assert pl_a.id not in updated_bm.playlist_ids

        print("[PASS] Test 6: Cập nhật tiêu đề bài và đồng bộ checkbox playlist thành công.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_delete_playlist_preserves_bookmarks():
    """TEST 7: Xóa danh sách phát thì bài toán gốc trong Sổ Tay vẫn được giữ nguyên."""
    db = get_db()
    s = _create_student(db, "student_del_pl")
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        sess = _create_session_with_message(db, s.id, "Bài toán hình học")

        pl = bookmarks_router.create_playlist(body=schemas.PlaylistCreate(name="Sẽ bị xóa"), current_user=user_dict, db=db)
        bm = bookmarks_router.create_bookmark(
            body=schemas.BookmarkCreate(session_id=sess.id, title="Bài toán bền vững", playlist_ids=[pl.id]),
            current_user=user_dict,
            db=db,
        )

        # Xóa playlist
        bookmarks_router.delete_playlist(playlist_id=pl.id, current_user=user_dict, db=db)

        # Kiểm tra bài toán vẫn còn nguyên trong Sổ Tay
        check_bm = bookmarks_router.get_bookmark(bookmark_id=bm.id, current_user=user_dict, db=db)
        assert check_bm is not None
        assert check_bm.title == "Bài toán bền vững"
        assert pl.id not in check_bm.playlist_ids

        print("[PASS] Test 7: Xóa playlist bảo toàn bài toán gốc trong Sổ Tay thành công.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def test_streak_leaderboard_all_and_grade():
    """TEST 8 & 9: Bảng xếp hạng Streak Toàn Server & Lọc theo Khối Lớp (Lớp 4 - 9)."""
    db = get_db()
    today = date.today()

    # Tạo 4 học sinh:
    # s1: Lớp 5, streak 3 ngày (hôm nay, hôm qua, 2 ngày trước) -> max_streak = 3
    # s2: Lớp 5, streak 1 ngày (hôm nay) -> max_streak = 1
    # s3: Lớp 6, streak 5 ngày (hôm nay và 4 ngày liên tiếp trước) -> max_streak = 5
    # s4: Lớp 5, kỷ lục 7 ngày trong quá khứ, hiện tại streak = 0 -> max_streak = 7
    s1 = _create_student(db, "student_streak_s1", grade=5)
    s2 = _create_student(db, "student_streak_s2", grade=5)
    s3 = _create_student(db, "student_streak_s3", grade=6)
    s4 = _create_student(db, "student_streak_s4", grade=5)

    try:
        sess1 = _create_session_with_message(db, s1.id, "Bài của s1")
        sess2 = _create_session_with_message(db, s2.id, "Bài của s2")
        sess3 = _create_session_with_message(db, s3.id, "Bài của s3")
        sess4 = _create_session_with_message(db, s4.id, "Bài của s4")
        # Đặt sess4 về quá khứ 15 ngày để s4 không có hoạt động hôm nay (streak_days = 0)
        sess4.created_at = datetime.now(timezone.utc) - timedelta(days=15)
        db.query(models.Message).filter(models.Message.session_id == sess4.id).update(
            {"created_at": datetime.now(timezone.utc) - timedelta(days=15)}
        )
        db.commit()

        # Ghi nhận ngày học cho s1: 3 ngày liên tiếp
        for d_offset in [0, 1, 2]:
            dt = datetime.combine(today - timedelta(days=d_offset), datetime.min.time(), tzinfo=timezone.utc)
            db.add(models.SessionActiveInterval(
                id=make_id(),
                session_id=sess1.id,
                user_id=s1.id,
                start_time=dt,
                end_time=dt,
                active_seconds=300,
            ))

        # Ghi nhận ngày học cho s2: 1 ngày (hôm nay)
        dt2 = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        db.add(models.SessionActiveInterval(
            id=make_id(),
            session_id=sess2.id,
            user_id=s2.id,
            start_time=dt2,
            end_time=dt2,
            active_seconds=300,
        ))

        # Ghi nhận ngày học cho s3: 5 ngày liên tiếp
        for d_offset in [0, 1, 2, 3, 4]:
            dt3 = datetime.combine(today - timedelta(days=d_offset), datetime.min.time(), tzinfo=timezone.utc)
            db.add(models.SessionActiveInterval(
                id=make_id(),
                session_id=sess3.id,
                user_id=s3.id,
                start_time=dt3,
                end_time=dt3,
                active_seconds=500,
            ))

        # Ghi nhận ngày học cho s4: 7 ngày liên tiếp trong quá khứ (cách đây 10 -> 16 ngày, hiện tại streak = 0)
        for d_offset in range(10, 17):
            dt4 = datetime.combine(today - timedelta(days=d_offset), datetime.min.time(), tzinfo=timezone.utc)
            db.add(models.SessionActiveInterval(
                id=make_id(),
                session_id=sess4.id,
                user_id=s4.id,
                start_time=dt4,
                end_time=dt4,
                active_seconds=400,
            ))
        db.commit()

        # TEST TOÀN SERVER (grade=None) với s1 là current_user
        user_s1 = {"id": s1.id, "email": s1.email, "role": s1.role}
        board_all = metrics_router.get_streak_leaderboard(grade=None, limit=20, current_user=user_s1, db=db)

        assert board_all.scope == "ALL"
        assert board_all.grade is None
        assert board_all.total_participants >= 4

        # Tìm các bạn này trong leaderboard
        entry_s4 = next(item for item in board_all.leaderboard if item.student_id == s4.id)
        entry_s3 = next(item for item in board_all.leaderboard if item.student_id == s3.id)
        entry_s1 = next(item for item in board_all.leaderboard if item.student_id == s1.id)
        entry_s2 = next(item for item in board_all.leaderboard if item.student_id == s2.id)

        assert entry_s4.max_streak == 7
        assert entry_s4.streak_days == 0

        assert entry_s3.max_streak == 5
        assert entry_s3.streak_days == 5

        assert entry_s1.max_streak == 3
        assert entry_s1.streak_days == 3

        assert entry_s2.max_streak == 1
        assert entry_s2.streak_days == 1

        # Xếp hạng theo KỶ LỤC: s4 (7) > s3 (5) > s1 (3) > s2 (1)
        # s4 dù streak hiện tại = 0 nhưng kỷ lục = 7 nên phải đứng trên s3 (5) và s1 (3)
        assert entry_s4.rank < entry_s3.rank < entry_s1.rank < entry_s2.rank

        # current_user_entry phải là của s1
        assert board_all.current_user_entry is not None
        assert board_all.current_user_entry.student_id == s1.id
        assert board_all.current_user_entry.is_current_user is True
        assert board_all.current_user_entry.streak_days == 3
        assert board_all.current_user_entry.max_streak == 3

        print("[PASS] Test 8: Bảng xếp hạng Streak sắp xếp theo KỶ LỤC (max_streak) chính xác.")

        # TEST LỌC THEO KHỐI LỚP: grade=5
        board_g5 = metrics_router.get_streak_leaderboard(grade=5, limit=20, current_user=user_s1, db=db)
        assert board_g5.scope == "GRADE_5"
        assert board_g5.grade == 5

        # Chỉ có học sinh lớp 5
        for item in board_g5.leaderboard:
            assert item.grade == 5

        g5_ids = [item.student_id for item in board_g5.leaderboard]
        assert s1.id in g5_ids
        assert s2.id in g5_ids
        assert s4.id in g5_ids
        assert s3.id not in g5_ids  # s3 là lớp 6 nên không xuất hiện

        print("[PASS] Test 9: Lọc Bảng xếp hạng Streak theo Khối Lớp (Lớp 5) chuẩn xác.")

    finally:
        _cleanup(db, [s1.id, s2.id, s3.id, s4.id])
        db.close()


def test_streak_leaderboard_privacy():
    """TEST 10: Bảo vệ quyền riêng tư trên Bảng xếp hạng: Chỉ hiển thị display_name, avatar, grade, streak_days, rank."""
    db = get_db()
    s = _create_student(db, "nguyen_hoang_nam", grade=7)
    try:
        user_dict = {"id": s.id, "email": s.email, "role": s.role}
        resp = metrics_router.get_streak_leaderboard(grade=7, limit=10, current_user=user_dict, db=db)

        my_item = next(item for item in resp.leaderboard if item.student_id == s.id)

        # Kiểm tra display_name: không lộ tên miền email
        assert "@" not in my_item.display_name
        assert my_item.display_name.startswith("nguyen_hoang_nam")

        # Kiểm tra avatar được sinh an toàn
        assert my_item.avatar is not None
        assert "dicebear" in my_item.avatar

        # Kiểm tra không có thuộc tính nhạy cảm như hashed_password, refresh_token
        d = my_item.model_dump()
        assert "hashed_password" not in d
        assert "email" not in d
        assert "phone" not in d

        print("[PASS] Test 10: Bảo vệ quyền riêng tư trên Bảng xếp hạng hoàn hảo.")
    finally:
        _cleanup(db, [s.id])
        db.close()


def run_all_tests():
    print("=" * 60)
    print("BAT DAU KIEM TRA TOAN BO TEST SUITE US 8.2")
    print("=" * 60)
    tests = [
        test_auto_create_default_playlist,
        test_create_and_manage_playlist,
        test_bookmark_with_custom_title_and_playlist,
        test_create_playlist_with_initial_bookmark,
        test_filter_bookmarks_by_playlist,
        test_update_bookmark_title_and_playlist_sync,
        test_delete_playlist_preserves_bookmarks,
        test_streak_leaderboard_all_and_grade,
        test_streak_leaderboard_privacy,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Ket qua: {passed}/{len(tests)} PASSED | {failed} FAILED")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
