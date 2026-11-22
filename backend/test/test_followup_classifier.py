"""
US 9.3 - Task T9.14:
Bộ kiểm thử toàn diện Prompt Phân Nhánh Lượt Phản Hồi Kế Tiếp (Follow-up Turn Classifier).
Kiểm thử đa dạng các biến thể câu thoại, tiếng lóng Gen Z, định dạng hội thoại nhiều dòng,
và độ ưu tiên của bộ phân luồng (Safety vs Socratic Scaffolding).

Chạy:
    cd backend
    python -m pytest backend/test/test_followup_classifier.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import (
    _agent,
    _detect_probe_in_history,
    _classify_probe_reply,
)


def test_detect_probe_in_history_variants():
    """Kiểm tra nhận diện câu hỏi thăm dò trong nhiều định dạng hội thoại khác nhau."""
    # 1. Đơn dòng tiêu chuẩn
    h_school_single = (
        "[USER]: em chưa học\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa, hay em mới học đến phần nào rồi?"
    )
    assert _detect_probe_in_history(h_school_single) == "SCHOOL_PROBE"

    # 2. Nhiều dòng có Markdown và định dạng AI thực tế
    h_school_multiline = (
        "[USER]: bài toán này khó quá thầy ơi\n"
        "[AGENT]: Thầy thấy bài này nằm trong chương trình Học kỳ 1 lớp 7.\n\n"
        "Ở trường thầy cô đã dạy đến bài này chưa, hay em mới học đến phần nào rồi? "
        "Nói thầy nghe để thầy hướng dẫn cho vừa sức em nhất nhé!"
    )
    assert _detect_probe_in_history(h_school_multiline) == "SCHOOL_PROBE"

    # 3. Mùa hè với role MODEL (chuẩn Gemini DB)
    h_summer_multiline = (
        "[USER]: bài 3 trang 15 sgk\n"
        "[MODEL]: Chào em, thầy đã nhận được đề bài.\n"
        "Thầy thấy trên tài khoản em đang chọn Lớp 8.\n"
        "Kỳ nghỉ hè này em đang chuẩn bị học trước kiến thức lớp 8, hay em đang ôn lại bài năm vừa rồi vậy em?\n"
        "Nói thầy nghe nhé!"
    )
    assert _detect_probe_in_history(h_summer_multiline) == "SUMMER_PROBE"

    # 4. Role [THẦY] hoặc [ASSISTANT]
    h_thay = (
        "[USER]: em chx học\n"
        "[THẦY]: Ở trường thầy cô đã dạy đến bài lũy thừa này chưa em?"
    )
    assert _detect_probe_in_history(h_thay) == "SCHOOL_PROBE"

    # 5. Hội thoại bình thường (không có probe) -> None
    h_normal = (
        "[USER]: 1 + 1 bằng mấy\n"
        "[AGENT]: 1 + 1 = 2 em nhé!"
    )
    assert _detect_probe_in_history(h_normal) is None

    # 6. Đã qua bước thăm dò: Probe ở lượt trước, lượt gần nhất AI đang giải bài -> None
    h_past_probe = (
        "[USER]: em chưa học\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa em?\n"
        "[USER]: dạ chưa\n"
        "[AGENT]: Được rồi, vậy bước đầu tiên em hãy nhìn vào hai mẫu số nhé!"
    )
    assert _detect_probe_in_history(h_past_probe) is None

    # 7. Lịch sử rỗng -> None
    assert _detect_probe_in_history("") is None
    assert _detect_probe_in_history("   ") is None


def test_classify_probe_reply_learn_new_slang():
    """Kiểm tra nhận diện nhánh Chưa học tới / Tự học trước (LEARN_NEW) với nhiều cách nói và tiếng lóng."""
    learn_new_samples = [
        "dạ chưa",
        "chưa ạ",
        "chưa thầy ơi",
        "dạ chưa cô mới dạy nhân đơn thức thôi",
        "em đang học trước để chuẩn bị năm học mới",
        "chưa học tới thầy ơi",
        "dạ chx học tới",
        "chua hoc thay oi",
        "cô chưa dạy đến bài này",
        "trên lớp mới học bài 1 thôi",
        "em tự học trước hè",
        "em xem trước bài lớp 8",
        "coi trước kiến thức ạ",
        "chưa qua bài này bao giờ",
        "chưa ai dạy em hết trơn",
        "e ms hc toi do",
        "chx tới bài này đâu thầy",
        "dạ bài mới thầy",
        "kiến thức mới em chưa biết",
        "tìm hiểu trước ạ",
        "mới tới bài phân số",
    ]
    for text in learn_new_samples:
        assert _classify_probe_reply(text) == "LEARN_NEW", f"Lỗi nhận diện LEARN_NEW cho câu: '{text}'"


def test_classify_probe_reply_forgot_old_slang():
    """Kiểm tra nhận diện nhánh Đã học mà quên / Ôn tập hè (FORGOT_OLD) với tiếng lóng và biến thể."""
    forgot_old_samples = [
        "dạ rồi",
        "rồi ạ",
        "dạ rồi thầy",
        "cô dạy rồi ạ",
        "thầy dạy rồi mà em quên",
        "đã học trên lớp rồi",
        "học rồi mà em quên sạch mất tiêu",
        "hè xả hơi lâu quá nên em quên rồi thầy",
        "dạ hc r mà quên",
        "dạ em học r",
        "dạ em học rồi",
        "học rồi nhưng mà quên cách làm",
        "em ko nhớ công thức",
        "k nhớ bài này làm sao",
        "em ôn lại bài cũ năm ngoái",
        "em ôn bài cũ",
        "ôn tập hè thầy ơi",
        "nghỉ hè chơi nhiều nên quên r",
        "học xong rồi mà lú quá thầy",
        "học rùi mà quên mất tiu",
        "lâu quá ko đụng tới nên quên",
        "học qua rồi mà lú quá",
    ]
    for text in forgot_old_samples:
        assert _classify_probe_reply(text) == "FORGOT_OLD", f"Lỗi nhận diện FORGOT_OLD cho câu: '{text}'"


def test_classify_probe_reply_unclear():
    """Kiểm tra nhận diện nhánh Lấp lửng / Không rõ ràng (UNCLEAR)."""
    unclear_samples = [
        "em ko bt",
        "k biết",
        "ko bít",
        "bí quá thầy ơi",
        "thầy giảng luôn đi",
        "chịu thua",
        "hổng biết nữa",
        "ko rõ",
        "chịu á",
        "khó hiểu ghê",
    ]
    for text in unclear_samples:
        assert _classify_probe_reply(text) == "UNCLEAR", f"Lỗi nhận diện UNCLEAR cho câu: '{text}'"


def test_orchestrator_followup_routing_all_branches():
    """Kiểm tra toàn diện logic điều phối Orchestrator khi nhận diện câu trả lời sau probe."""
    h_school = (
        "[USER]: em chưa học bài này\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa, hay em mới học đến phần nào rồi?"
    )

    # 1. Học sinh xác nhận chưa học tới -> Gắn nhãn LEARN_NEW và nhúng Khung Socratic Kịch bản B
    res_learn = _agent.route_sync("dạ chx học tới cô mới dạy bài 1 thôi", history_text=h_school)
    assert res_learn["selected_agent"] == "SCAFFOLDING"
    assert "LEARN_NEW" in res_learn["routing_scratchpad"]
    assert "BẮT BUỘC ÁP DỤNG KỊCH BẢN B" in res_learn["task_description"]
    assert "Coi học sinh là 'tờ giấy trắng'" in res_learn["task_description"]

    # 2. Học sinh xác nhận đã học mà quên -> Gắn nhãn FORGOT_OLD và nhúng Khung Socratic Kịch bản A
    res_forgot = _agent.route_sync("dạ học rồi mà em quên sạch công thức", history_text=h_school)
    assert res_forgot["selected_agent"] == "SCAFFOLDING"
    assert "FORGOT_OLD" in res_forgot["routing_scratchpad"]
    assert "BẮT BUỘC ÁP DỤNG KỊCH BẢN A" in res_forgot["task_description"]
    assert "KHÔNG giảng lại từ đầu" in res_forgot["task_description"]

    # 3. Học sinh lấp lửng -> Gắn nhãn UNCLEAR và nhúng Khung Socratic Fallback
    res_unclear = _agent.route_sync("em ko bt thầy ơi", history_text=h_school)
    assert res_unclear["selected_agent"] == "SCAFFOLDING"
    assert "UNCLEAR" in res_unclear["routing_scratchpad"]
    assert "hướng dẫn kiên nhẫn từ bước đơn giản nhất" in res_unclear["task_description"]


def test_orchestrator_summer_probe_followup():
    """Kiểm tra phân nhánh mùa hè: Khen ngợi tự học trước vs Đồng cảm ôn tập hè."""
    h_summer = (
        "[USER]: bài này em chưa học\n"
        "[AGENT]: Thầy thấy trên tài khoản em đang chọn Lớp 8. Kỳ nghỉ hè này em đang chuẩn bị học trước kiến thức lớp 8, hay em đang ôn lại bài năm vừa rồi vậy em?"
    )

    # Hè học trước -> Ghi nhận LEARN_NEW + Khung Socratic có chỉ đạo khen ngợi tự giác
    res_summer_new = _agent.route_sync("em đang học trước để chuẩn bị vào năm học", history_text=h_summer)
    assert res_summer_new["selected_agent"] == "SCAFFOLDING"
    assert "khen ngợi tinh thần tự giác" in res_summer_new["task_description"]
    assert "LEARN_NEW" in res_summer_new["routing_scratchpad"]

    # Hè ôn bài cũ -> Ghi nhận FORGOT_OLD + Khung Socratic Kịch bản A
    res_summer_forgot = _agent.route_sync("hè xả hơi lâu quá nên em quên rồi thầy", history_text=h_summer)
    assert res_summer_forgot["selected_agent"] == "SCAFFOLDING"
    assert "BẮT BUỘC ÁP DỤNG KỊCH BẢN A" in res_summer_forgot["task_description"]
    assert "FORGOT_OLD" in res_summer_forgot["routing_scratchpad"]


def test_safety_priority_over_followup_probe():
    """Kiểm tra nguyên tắc an toàn: Dù đang ở bước probe, nếu học sinh chửi tục/vô lễ vẫn ưu tiên SAFETY."""
    h_school = (
        "[USER]: em chưa học bài này\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa em?"
    )
    # Học sinh chửi bậy hoặc vô lễ
    res_safety = _agent.route_sync("mày nói nhiều quá giải luôn đi", history_text=h_school)
    assert res_safety["selected_agent"] == "SAFETY"
    assert res_safety["emotion_flag"] == "WARNING"
