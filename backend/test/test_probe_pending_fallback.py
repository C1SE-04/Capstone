import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import (
    _has_probe_already_completed,
    _build_task_description,
    _detect_probe_in_history,
    _agent,
)

def test_has_probe_already_completed():
    # Trường hợp 1: Chưa từng hỏi thăm dò
    hist_1 = "[USER]: 2 + 2 = mấy\n[AGENT]: Bằng 4 em nhé"
    assert _has_probe_already_completed(hist_1) is False

    # Trường hợp 2: AI mới hỏi thăm dò, học sinh chưa kịp trả lời
    hist_2 = "[USER]: em chưa học\n[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa?"
    assert _has_probe_already_completed(hist_2) is False

    # Trường hợp 3: AI đã hỏi thăm dò VÀ học sinh đã trả lời sau đó
    hist_3 = (
        "[USER]: em chưa học\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa, hay em mới học đến phần nào rồi?\n"
        "[USER]: dạ chưa cô mới dạy bài trước thôi\n"
        "[AGENT]: Vậy thầy sẽ hướng dẫn từ từ nhé!"
    )
    assert _has_probe_already_completed(hist_3) is True

    # Trường hợp 4: AI hỏi thăm dò dạng nhiều dòng (multi-line) và học sinh đã phản hồi
    hist_multiline = (
        "[USER]: bài này em chưa học\n"
        "[AGENT]: Thầy chào em nhé!\n"
        "Ở trường thầy cô đã dạy đến bài này chưa hay em mới học đến phần nào rồi?\n"
        "[USER]: dạ em chưa học tới ạ\n"
        "[AGENT]: Được rồi, vậy mình cùng tìm hiểu từ đầu nha!"
    )
    assert _has_probe_already_completed(hist_multiline) is True

    # Trường hợp 5: Thăm dò mùa hè đã hoàn tất
    hist_summer = (
        "[USER]: 3/4 + 45/2 tính sao thầy\n"
        "[AGENT]: Bây giờ đang là kỳ nghỉ hè, em đang chuẩn bị học trước kiến thức hay ôn lại bài năm vừa rồi thế?\n"
        "[USER]: em tự học trước ạ\n"
        "[AGENT]: Tinh thần tự giác của em rất tốt! Thầy sẽ hướng dẫn từ bước cơ bản nhất nhé."
    )
    assert _has_probe_already_completed(hist_summer) is True

def test_no_repeat_probe_in_task_description():
    """Kiểm tra task_description không chứa câu hỏi thăm dò nếu probe đã hoàn tất."""
    hist = (
        "[USER]: em chưa học\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa?\n"
        "[USER]: dạ chưa ạ\n"
        "[AGENT]: Thầy hướng dẫn từ đầu nhé! Số nào chia hết cho 4 và 2?"
    )
    task_desc = _build_task_description("SCAFFOLDING", "em chưa học cái này", history_text=hist, student_grade=7)
    assert "TUYỆT ĐỐI KHÔNG HỎI LẠI" in task_desc
    assert "Ở trường thầy cô đã dạy đến bài này chưa" not in task_desc
    assert "Hạ thấp rào cản thêm một nấc" in task_desc or "hạ thấp rào cản thêm một nấc" in task_desc

def test_routing_with_probe_already_completed():
    """Kiểm tra route_sync điều phối SCAFFOLDING với chỉ đạo chống lặp lại thăm dò."""
    hist = (
        "[USER]: em chưa học\n"
        "[AGENT]: Ở trường thầy cô đã dạy đến bài này chưa?\n"
        "[USER]: dạ chưa cô mới dạy bài trước thôi\n"
        "[AGENT]: Vậy thầy hướng dẫn nhé! Số nào chia hết cho 4 và 2?"
    )
    res = _agent.route_sync("em vẫn chưa học bài này thầy ơi", history_text=hist, student_grade=7)
    assert res["selected_agent"] == "SCAFFOLDING"
    assert "TUYỆT ĐỐI KHÔNG HỎI LẠI" in res["task_description"]
    assert "KỊCH BẢN B" in res["task_description"]

def test_summer_probe_fallback_unclear():
    """Kiểm tra phản hồi lấp lửng trong mùa hè fallback về Kịch bản B theo AC 9.3.7."""
    hist = (
        "[USER]: 3/4 + 45/2 tính sao thầy\n"
        "[AGENT]: Bây giờ đang là kỳ nghỉ hè, em đang chuẩn bị học trước kiến thức hay ôn lại bài năm vừa rồi thế?"
    )
    res = _agent.route_sync("em ko bt", history_text=hist, student_grade=7)
    assert res["selected_agent"] == "SCAFFOLDING"
    assert "Kịch bản B" in res["task_description"] or "KỊCH BẢN B" in res["task_description"]
    assert "AC 9.3.7" in res["task_description"] or "xả hơi hè" in res["task_description"]

def test_probe_tag_recognition_paraphrased():
    """
    Kiểm tra nhận diện Thẻ ẩn [PROBE_PENDING] / <!-- PROBE_PENDING -->:
    Dù Gemini paraphrase câu hỏi bằng từ ngữ hoàn toàn khác (không chứa từ 'thầy cô' hay 'ở trường'),
    hệ thống vẫn nhận diện chính xác 100% nhờ giao thức thẻ ẩn.
    """
    # 1. Thẻ ẩn dạng HTML comment <!-- PROBE_PENDING -->
    hist_html_comment = (
        "[USER]: bài này em chưa học\n"
        "[AGENT]: Thầy tò mò một xíu là bài này lớp mình đã đi qua chưa ta? <!-- PROBE_PENDING -->"
    )
    assert _detect_probe_in_history(hist_html_comment) == "SCHOOL_PROBE"

    # 2. Thẻ ẩn mùa hè <!-- SUMMER_PROBE_PENDING -->
    hist_summer_tag = (
        "[USER]: bài này khó quá\n"
        "[AGENT]: Đang dịp nghỉ ngơi xả hơi, em tự tìm hiểu trước hay xem lại kiến thức vậy nè? <!-- SUMMER_PROBE_PENDING -->"
    )
    assert _detect_probe_in_history(hist_summer_tag) == "SUMMER_PROBE"

    # 3. Thẻ ẩn vuông [PROBE_PENDING]
    hist_bracket_tag = (
        "[USER]: phân số này em chưa hiểu\n"
        "[AGENT]: Dạng toán này mới toanh với em hay em từng tiếp cận rồi? [PROBE_PENDING]"
    )
    assert _detect_probe_in_history(hist_bracket_tag) == "SCHOOL_PROBE"

def test_probe_tag_prevents_repeat_probe():
    """
    Kiểm tra Thẻ ẩn ngăn chặn tuyệt đối hỏi lặp lại thăm dò ở các lượt sau,
    ngay cả khi câu hỏi gốc của AI được paraphrase hoàn toàn.
    """
    hist = (
        "[USER]: bài này em chưa học\n"
        "[AGENT]: Dạng toán này mới toanh với em hay em từng tiếp cận rồi? <!-- PROBE_PENDING -->\n"
        "[USER]: dạ mới toanh luôn thầy\n"
        "[AGENT]: Thầy hiểu rồi! Thầy sẽ hướng dẫn từng bước nhỏ nhé. Đầu tiên số 6 chia cho 2 được mấy?"
    )
    # Xác định probe đã hoàn tất nhờ có thẻ ẩn trong lịch sử và đã có tin nhắn trả lời
    assert _has_probe_already_completed(hist) is True

    # Khi học sinh tiếp tục bối rối than chưa học
    res = _agent.route_sync("bước này em cũng chưa học thầy ơi", history_text=hist, student_grade=7)
    assert res["selected_agent"] == "SCAFFOLDING"
    assert "TUYỆT ĐỐI KHÔNG HỎI LẠI" in res["task_description"]
