"""
US 11.6 & US 9.3: BỘ 30 TEST CASES KIỂM THỬ SÂU TOÀN DIỆN VỀ HÀM Ý 'CHƯA HỌC / LẠ LÃM'
Mở rộng chuỗi đối thoại Socratic từ 3 đến 5 lượt (Requests <-> Responses).

Bộ test này bao quát:
- Phần 1 (10 tests): Các tình huống ngoại lệ, biểu đạt lạ lẫm, mới toanh, teencode Gen Z,
                     ẩn ý chưa từng gặp, thầy cô lướt qua hoặc bỏ qua bài (3 lượt).
- Phần 2 (10 tests): Chuỗi đối thoại sâu 4 LƯỢT (4 Requests <-> 4 Responses)
                     từ Lớp 5 đến Lớp 9 (HK1 & HK2) cho cả Kịch bản A (quên bài) và B (chưa học).
- Phần 3 (10 tests): Chuỗi đối thoại sâu 5 LƯỢT (5 Requests <-> 5 Responses)
                     kiểm tra toàn diện: Than lạ -> Thăm dò -> Phân loại Socratic ->
                     Làm bước 1 -> Gợi ý bước 2 -> Chốt đáp án & Củng cố.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import _agent, _detect_uncovered_claim


# ==============================================================================
# TEST RUNNER HELPERS (3 LƯỢT, 4 LƯỢT, 5 LƯỢT)
# ==============================================================================

def execute_3_turn_scenario(
    grade: int,
    topic_c_name: str,
    req_1_student: str,
    req_2_student: str,
    expected_scenario: str,  # "SCENARIO_B_NEW" | "SCENARIO_A_OLD" | "SCENARIO_B_SKIPPED"
    req_3_student: str,
    step1_guidance_text: str,
):
    """Thực thi chuỗi 3 lượt tương tác."""
    # Lượt 1: Than lạ / chưa học
    assert _detect_uncovered_claim(req_1_student), f"Phải nhận diện được hàm ý chưa học/lạ lẫm: '{req_1_student}'"
    res_1 = _agent.route_sync(req_1_student, student_grade=grade)
    assert res_1["selected_agent"] == "SCAFFOLDING", "Lượt 1 phải route SCAFFOLDING"
    assert "PROBE_PENDING" in res_1["task_description"], "Lượt 1 phải yêu cầu PROBE_PENDING"

    res_1_sim = f"Hiện tại trên trường em đã học đến bài nào rồi, bài {topic_c_name} này em đã học qua chưa? <!-- PROBE_PENDING -->"

    # Lượt 2: Phản hồi tiến độ
    h_2 = f"[USER]: {req_1_student}\n[AGENT]: {res_1_sim}\n"
    res_2 = _agent.route_sync(req_2_student, history_text=h_2, student_grade=grade)
    assert res_2["selected_agent"] == "SCAFFOLDING", "Lượt 2 phải tiếp tục SCAFFOLDING"
    assert "US 11.6 CURRICULUM ORDER" in res_2["task_description"], "Lượt 2 phải inject thứ tự curriculum"

    if expected_scenario in ("SCENARIO_B_NEW", "SCENARIO_B_SKIPPED"):
        assert "KỊCH BẢN B" in res_2["task_description"]
        if expected_scenario == "SCENARIO_B_SKIPPED":
            assert any(w in res_2["task_description"] for w in ("bình thường nhé", "Đôi khi thầy cô", "lướt qua"))
    elif expected_scenario == "SCENARIO_A_OLD":
        assert "KỊCH BẢN A" in res_2["task_description"]

    # Lượt 3: Học sinh thực hiện bước 1
    res_2_sim = step1_guidance_text
    h_3 = h_2 + f"[USER]: {req_2_student}\n[AGENT]: {res_2_sim}\n"
    res_3 = _agent.route_sync(req_3_student, history_text=h_3, student_grade=grade)
    assert res_3["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING")
    assert "<!-- PROBE_PENDING -->" not in res_3["task_description"]


def execute_4_turn_scenario(
    grade: int,
    topic_c_name: str,
    req_1_student: str,
    req_2_student: str,
    expected_scenario: str,
    res_2_step1_ai: str,
    req_3_student: str,
    res_3_step2_ai: str,
    req_4_student: str,
):
    """Thực thi chuỗi 4 lượt tương tác hoàn chỉnh."""
    # Turn 1
    assert _detect_uncovered_claim(req_1_student), f"Lượt 1: Phải bắt được hàm ý chưa học: '{req_1_student}'"
    res_1 = _agent.route_sync(req_1_student, student_grade=grade)
    assert res_1["selected_agent"] == "SCAFFOLDING"
    assert "PROBE_PENDING" in res_1["task_description"]

    res_1_sim = f"Hiện tại trên trường em đã học đến bài nào rồi, bài {topic_c_name} này em đã học qua chưa? <!-- PROBE_PENDING -->"

    # Turn 2
    h_2 = f"[USER]: {req_1_student}\n[AGENT]: {res_1_sim}\n"
    res_2 = _agent.route_sync(req_2_student, history_text=h_2, student_grade=grade)
    assert res_2["selected_agent"] == "SCAFFOLDING"
    assert "US 11.6 CURRICULUM ORDER" in res_2["task_description"]
    if expected_scenario == "SCENARIO_B_NEW":
        assert "KỊCH BẢN B" in res_2["task_description"]
    elif expected_scenario == "SCENARIO_A_OLD":
        assert "KỊCH BẢN A" in res_2["task_description"]

    # Turn 3
    h_3 = h_2 + f"[USER]: {req_2_student}\n[AGENT]: {res_2_step1_ai}\n"
    res_3 = _agent.route_sync(req_3_student, history_text=h_3, student_grade=grade)
    assert res_3["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING")
    assert "<!-- PROBE_PENDING -->" not in res_3["task_description"]

    # Turn 4
    h_4 = h_3 + f"[USER]: {req_3_student}\n[AGENT]: {res_3_step2_ai}\n"
    res_4 = _agent.route_sync(req_4_student, history_text=h_4, student_grade=grade)
    assert res_4["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING")
    assert "<!-- PROBE_PENDING -->" not in res_4["task_description"]


def execute_5_turn_scenario(
    grade: int,
    topic_c_name: str,
    req_1_student: str,
    req_2_student: str,
    expected_scenario: str,
    res_2_step1_ai: str,
    req_3_student: str,
    res_3_step2_ai: str,
    req_4_student: str,
    res_4_step3_ai: str,
    req_5_student: str,
):
    """Thực thi chuỗi 5 lượt tương tác trọn vẹn."""
    # Turn 1
    assert _detect_uncovered_claim(req_1_student), f"Lượt 1: Phải bắt được hàm ý chưa học: '{req_1_student}'"
    res_1 = _agent.route_sync(req_1_student, student_grade=grade)
    assert res_1["selected_agent"] == "SCAFFOLDING"
    assert "PROBE_PENDING" in res_1["task_description"]

    res_1_sim = f"Hiện tại trên trường em đã học đến bài nào rồi, bài {topic_c_name} này em đã học qua chưa? <!-- PROBE_PENDING -->"

    # Turn 2
    h_2 = f"[USER]: {req_1_student}\n[AGENT]: {res_1_sim}\n"
    res_2 = _agent.route_sync(req_2_student, history_text=h_2, student_grade=grade)
    assert res_2["selected_agent"] == "SCAFFOLDING"
    assert "US 11.6 CURRICULUM ORDER" in res_2["task_description"]
    if expected_scenario in ("SCENARIO_B_NEW", "SCENARIO_B_SKIPPED"):
        assert "KỊCH BẢN B" in res_2["task_description"]
    elif expected_scenario == "SCENARIO_A_OLD":
        assert "KỊCH BẢN A" in res_2["task_description"]

    # Turn 3
    h_3 = h_2 + f"[USER]: {req_2_student}\n[AGENT]: {res_2_step1_ai}\n"
    res_3 = _agent.route_sync(req_3_student, history_text=h_3, student_grade=grade)
    assert res_3["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING")
    assert "<!-- PROBE_PENDING -->" not in res_3["task_description"]

    # Turn 4
    h_4 = h_3 + f"[USER]: {req_3_student}\n[AGENT]: {res_3_step2_ai}\n"
    res_4 = _agent.route_sync(req_4_student, history_text=h_4, student_grade=grade)
    assert res_4["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING")
    assert "<!-- PROBE_PENDING -->" not in res_4["task_description"]

    # Turn 5
    h_5 = h_4 + f"[USER]: {req_4_student}\n[AGENT]: {res_4_step3_ai}\n"
    res_5 = _agent.route_sync(req_5_student, history_text=h_5, student_grade=grade)
    assert res_5["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING", "SAFETY")
    assert "<!-- PROBE_PENDING -->" not in res_5["task_description"]


# ==============================================================================
# PHẦN 1: 10 TEST CASES - SẮC THÁI BIỂU ĐẠT ĐẶC BIỆT / TEENCODE / BỠ NGỠ (3 LƯỢT)
# ==============================================================================

def test_edge_01_strange_slang_grade5():
    """Case 1: 'lạ hoắc à thầy' - Lớp 5 HK1 Hỗn số."""
    execute_3_turn_scenario(
        grade=5,
        topic_c_name="Hỗn số",
        req_1_student="Bài hỗn số này lạ hoắc à thầy, em không biết làm sao",
        req_2_student="Dạ trường em mới học bài Phân số thập phân thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Phần nguyên là 2 còn phần phân số là 3/4 đúng không thầy",
        step1_guidance_text="Hỗn số gồm phần nguyên và phần phân số. Ví dụ 2 và 3/4 thì phần nguyên là mấy em?",
    )


def test_edge_02_brand_new_grade6():
    """Case 2: 'mới toanh em chưa thấy bao giờ' - Lớp 6 HK1 Ước chung lớn nhất."""
    execute_3_turn_scenario(
        grade=6,
        topic_c_name="Ước chung - Ước chung lớn nhất",
        req_1_student="Dạng toán ước chung lớn nhất này mới toanh em chưa thấy bao giờ luôn á thầy",
        req_2_student="Ở trường em mới học đến Phép nhân và phép chia số tự nhiên",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Các ước của 6 là 1, 2, 3, 6 ạ",
        step1_guidance_text="Không sao nhé! Đầu tiên em liệt kê các số mà 6 chia hết giúp thầy nào.",
    )


def test_edge_03_strange_ears_grade7():
    """Case 3: 'nghe lạ tai ghê á' - Lớp 7 HK1 Số vô tỉ. Căn bậc hai số học."""
    execute_3_turn_scenario(
        grade=7,
        topic_c_name="Số vô tỉ. Căn bậc hai số học",
        req_1_student="Số vô tỉ với căn bậc hai số học này nghe lạ tai ghê á thầy",
        req_2_student="Trường em mới học tới Lũy thừa của số hữu tỉ thôi",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ là 3 bình phương bằng 9 ạ",
        step1_guidance_text="Thầy giải thích từ từ nhé: Căn bậc hai số học của 9 là số dương mà bình phương lên bằng 9. Số nào bình phương bằng 9 em nhỉ?",
    )


def test_edge_04_strange_eyes_grade8():
    """Case 4: 'nhìn lạ mắt quá thầy ơi' - Lớp 8 HK2 Hình chóp tam giác đều."""
    execute_3_turn_scenario(
        grade=8,
        topic_c_name="Hình chóp tam giác đều",
        req_1_student="Hình chóp tam giác đều nhìn lạ mắt quá thầy ơi",
        req_2_student="Ở lớp em mới học bài Phương trình bậc nhất một ẩn thôi",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Mặt đáy là tam giác đều đúng không thầy",
        step1_guidance_text="Hình chóp tam giác đều có mặt đáy là hình gì đặc biệt em nhỉ?",
    )


def test_edge_05_unseen_before_grade9():
    """Case 5: 'quái lạ sao em chưa từng gặp' - Lớp 9 HK1 Căn bậc ba."""
    execute_3_turn_scenario(
        grade=9,
        topic_c_name="Căn bậc ba và căn thức bậc ba",
        req_1_student="Quái lạ sao em chưa từng gặp căn bậc ba dạng này bao giờ",
        req_2_student="Ở trường em mới học đến Căn bậc hai và căn thức bậc hai thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="2 mũ 3 bằng 8 ạ",
        step1_guidance_text="Tương tự như căn bậc hai, căn bậc ba của 8 là số mà khi mũ 3 lên bằng 8. Số nào mũ 3 bằng 8 em?",
    )


def test_edge_06_teencode_chx_bh_grade6():
    """Case 6: 'chx bh thấy... lun á thầy' - Lớp 6 HK1 Bội chung nhỏ nhất."""
    execute_3_turn_scenario(
        grade=6,
        topic_c_name="Bội chung - Bội chung nhỏ nhất",
        req_1_student="chx bh thấy bài bội chung nhỏ nhất lun á thầy",
        req_2_student="trường em mới học tới Thứ tự thực hiện các phép tính",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Bội của 4 là 0, 4, 8, 12 đúng không ạ",
        step1_guidance_text="Thầy chỉ cách dễ hiểu nhất nha. Em hãy kể 3 số lớn hơn 0 chia hết cho 4 xem nào.",
    )


def test_edge_07_first_time_ever_grade7():
    """Case 7: 'lần đầu tiên trong đời em mới thấy' - Lớp 7 HK1 Hai tam giác bằng nhau."""
    execute_3_turn_scenario(
        grade=7,
        topic_c_name="Hai tam giác bằng nhau",
        req_1_student="Lần đầu tiên trong đời em mới thấy bài chứng minh hai tam giác bằng nhau này á",
        req_2_student="Ở trường em mới học tới Số thực thôi thầy",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ có cạnh AB bằng cạnh A'B' ạ",
        step1_guidance_text="Đừng lo nhé! Em quan sát đề bài xem có những cạnh nào của hai tam giác có độ dài bằng nhau?",
    )


def test_edge_08_teacher_skipped_fast_grade8():
    """Case 8: 'cô lướt qua bài... em chả kịp học' - Lớp 8 HK1 Định lí Thalès."""
    execute_3_turn_scenario(
        grade=8,
        topic_c_name="Định lí Thalès trong tam giác",
        req_1_student="Ở lớp cô lướt qua bài định lí thalès trong tam giác rồi em chả kịp học",
        req_2_student="Cô em không dạy bài đó nhảy cóc sang hình học khác luôn",
        expected_scenario="SCENARIO_B_SKIPPED",
        req_3_student="Dạ đường thẳng d song song với cạnh BC ạ",
        step1_guidance_text="Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé! Định lí Thalès bắt đầu từ một đường thẳng song song với một cạnh của tam giác. Đề bài cho đường thẳng nào song song em?",
    )


def test_edge_09_teacher_no_teach_grade9():
    """Case 9: 'bài này cô em không dạy' - Lớp 9 HK1 Tỉ số lượng giác."""
    execute_3_turn_scenario(
        grade=9,
        topic_c_name="Tỉ số lượng giác của góc nhọn",
        req_1_student="Bài tỉ số lượng giác của góc nhọn này cô em không dạy",
        req_2_student="Cô bỏ qua bài này chuyển sang hình tròn luôn thầy",
        expected_scenario="SCENARIO_B_SKIPPED",
        req_3_student="Sin bằng đối chia huyền phải không thầy",
        step1_guidance_text="Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé! Trong tam giác vuông, sin của một góc nhọn bằng cạnh đối chia cho cạnh nào?",
    )


def test_edge_10_teencode_e_chx_gap_bh_grade5():
    """Case 10: 'e chx gặp bh bài diện tích hình thang này' - Lớp 5 HK1 Diện tích hình thang."""
    execute_3_turn_scenario(
        grade=5,
        topic_c_name="Hình thang. Diện tích hình thang",
        req_1_student="e chx gặp bh bài diện tích hình thang này",
        req_2_student="em mới học tới bài Phép nhân số thập phân thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Đáy lớn là 8, đáy bé là 5 thì tổng hai đáy là 13 ạ",
        step1_guidance_text="Hình thang có hai đáy song song. Muốn tính diện tích, bước 1 em cộng độ dài đáy lớn và đáy bé lại trước nhé. Tổng bằng bao nhiêu em?",
    )


# ==============================================================================
# PHẦN 2: 10 TEST CASES - CHUỖI ĐỐI THOẠI SÂU 4 LƯỢT (4 REQUESTS <-> 4 RESPONSES)
# ==============================================================================

def test_deep_4turn_11_grade5_hk1_divide_decimals():
    """Case 11: Lớp 5 HK1 Phép chia số thập phân (Trường học đến Nhân số thập phân -> Chưa học)."""
    execute_4_turn_scenario(
        grade=5,
        topic_c_name="Phép chia số thập phân",
        req_1_student="Bài chia 14,4 : 1,2 này em chưa học cách chia dấu phẩy thầy ơi",
        req_2_student="Trên trường em mới học đến Phép nhân số thập phân thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Vì em chưa học chia số thập phân nên thầy hướng dẫn từ từ nhé. Bước 1: Số chia 1,2 có 1 chữ số sau dấu phẩy, vậy ta dời dấu phẩy của cả hai số sang phải 1 chữ số thành phép chia nào?",
        req_3_student="Dạ thành 144 chia cho 12 đúng không thầy",
        res_3_step2_ai="Chính xác luôn! Giờ phép chia trở thành chia hai số tự nhiên quen thuộc. Em tính giúp thầy 144 : 12 bằng mấy nhé.",
        req_4_student="144 chia 12 bằng 12 thầy ơi!",
    )


def test_deep_4turn_12_grade5_hk1_percent_ratio():
    """Case 12: Lớp 5 HK1 Tỉ số phần trăm (Trường học đến Quãng đường chuyển động đều -> Đã học nhưng quên)."""
    execute_4_turn_scenario(
        grade=5,
        topic_c_name="Tìm hai số khi biết hiệu và tỉ số của hai số đó",
        req_1_student="Dạng toán tìm hai số khi biết hiệu và tỉ số này lạ lẫm quá em không nhớ",
        req_2_student="Ở trường em học đến Quãng đường, thời gian của một chuyển động đều rồi ạ",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Quãng đường thời gian rồi thì trong chương trình HK1 lớp 5, em đã học bài Tìm hai số khi biết hiệu và tỉ số rồi. Có lẽ em quên nên thầy nhắc lại: Bước 1 tìm hiệu số phần bằng nhau nhé. Đề cho tỉ số 3/5 thì hiệu số phần là mấy?",
        req_3_student="Dạ lấy 5 trừ 3 là bằng 2 phần ạ",
        res_3_step2_ai="Đúng rồi! Đề cho hiệu hai số là 10, vậy giá trị 1 phần là bao nhiêu em tính giúp thầy?",
        req_4_student="Lấy 10 chia 2 là 5, vậy 1 phần là 5 thầy ơi",
    )


def test_deep_4turn_13_grade6_hk1_subtract_integers():
    """Case 13: Lớp 6 HK1 Phép trừ số nguyên (Trường mới học Lũy thừa -> Chưa học tới)."""
    execute_4_turn_scenario(
        grade=6,
        topic_c_name="Phép cộng và phép trừ số nguyên",
        req_1_student="Phép tính 5 - 9 này ra số âm lạ quá, em chưa được học số âm",
        req_2_student="Ở trường em mới học đến Lũy thừa với số mũ tự nhiên thôi",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Vì em chưa học số nguyên nên thầy giải thích bằng hình ảnh nhé: Em có 5 nghìn mà mua cây bút 9 nghìn thì em còn thiếu người bán mấy nghìn?",
        req_3_student="Dạ em thiếu 4 nghìn ạ",
        res_3_step2_ai="Đúng rồi! Trong toán học, số tiền thiếu 4 nghìn được biểu diễn bằng số nguyên âm mang dấu trừ đằng trước. Vậy 5 - 9 bằng bao nhiêu em?",
        req_4_student="Dạ bằng âm 4, viết là -4 đúng không thầy",
    )


def test_deep_4turn_14_grade6_hk1_divisibility_rules():
    """Case 14: Lớp 6 HK1 Dấu hiệu chia hết (Trường đã học đến Số nguyên tố -> Đã học nhưng quên)."""
    execute_4_turn_scenario(
        grade=6,
        topic_c_name="Dấu hiệu chia hết",
        req_1_student="Sao bài xét số 234 có chia hết cho 9 này lạ hoắc vậy thầy",
        req_2_student="Trên trường em đã học tới bài Số nguyên tố rồi thầy ơi",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Số nguyên tố rồi thì với chương trình HK1 lớp 6, em đã học Dấu hiệu chia hết rồi. Có lẽ em đã quên nên thầy nhắc lại: Một số chia hết cho 9 khi tổng các chữ số của nó chia hết cho 9. Em tính tổng các chữ số của 234 xem bằng mấy?",
        req_3_student="2 + 3 + 4 = 9 thầy ơi",
        res_3_step2_ai="Rất tốt! Vậy số 9 có chia hết cho 9 không, và kết luận số 234 có chia hết cho 9 không em?",
        req_4_student="9 chia hết cho 9 nên 234 chắc chắn chia hết cho 9 ạ",
    )


def test_deep_4turn_15_grade7_hk1_square_root():
    """Case 15: Lớp 7 HK1 Căn bậc hai số học (Trường mới học Phép tính số hữu tỉ -> Chưa học)."""
    execute_4_turn_scenario(
        grade=7,
        topic_c_name="Số vô tỉ. Căn bậc hai số học",
        req_1_student="Dấu căn bậc hai này mới toanh em chưa thấy bao giờ",
        req_2_student="Ở trường em mới học đến Cộng, trừ, nhân, chia số hữu tỉ thôi",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Thầy giảng từ nền tảng nhé: Căn bậc hai số học của a là một số không âm x sao cho x bình phương bằng a. Với căn 16, số dương nào bình phương lên bằng 16 em?",
        req_3_student="Dạ 4 bình phương là 16 ạ",
        res_3_step2_ai="Chính xác! Vậy căn bậc hai số học của 16 chính là 4. Tương tự, căn bậc hai số học của 25 là mấy em nhỉ?",
        req_4_student="Dạ bằng 5 vì 5 bình phương bằng 25 thầy ơi",
    )


def test_deep_4turn_16_grade7_hk2_inverse_proportion():
    """Case 16: Lớp 7 HK2 Đại lượng tỉ lệ nghịch (Trường học đến Biểu thức đại số -> Đã học nhưng quên)."""
    execute_4_turn_scenario(
        grade=7,
        topic_c_name="Đại lượng tỉ lệ nghịch",
        req_1_student="Đại lượng tỉ lệ nghịch này nghe lạ tai ghê, em không biết làm",
        req_2_student="Ở trường em học đến Biểu thức đại số rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Biểu thức đại số rồi thì trong chương trình HK2 lớp 7, em đã học bài Đại lượng tỉ lệ nghịch rồi. Có lẽ em quên nên thầy nhắc lại: Hai đại lượng tỉ lệ nghịch khi tích x nhân y bằng hệ số a không đổi. Đề cho x = 2 thì y = 6, vậy hệ số a là mấy?",
        req_3_student="a = 2 x 6 = 12 ạ",
        res_3_step2_ai="Đúng rồi! Khi x = 4 thì y bằng bao nhiêu để 4 nhân y = 12 em?",
        req_4_student="y = 12 / 4 = 3 thầy ơi",
    )


def test_deep_4turn_17_grade8_hk1_factorization():
    """Case 17: Lớp 8 HK1 Phân tích đa thức thành nhân tử (Trường mới học Nhân đa thức -> Chưa học)."""
    execute_4_turn_scenario(
        grade=8,
        topic_c_name="Phân tích đa thức thành nhân tử",
        req_1_student="Bài phân tích đa thức thành nhân tử 2x^2 + 4x này em chưa từng gặp",
        req_2_student="Ở lớp em mới học Phép nhân đa thức thôi thầy",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Không sao nhé! Phân tích thành nhân tử ngược lại với nhân phân phối. Em nhìn xem giữa 2x^2 và 4x có chung thừa số nào?",
        req_3_student="Dạ có chung số 2 và chữ x ạ, tức là chung 2x",
        res_3_step2_ai="Rất giỏi! Giờ ta đặt 2x ra ngoài ngoặc: 2x*(...). Bên trong ngoặc còn lại gì em?",
        req_4_student="Bên trong ngoặc còn lại x + 2, thành 2x(x + 2) đúng không thầy",
    )


def test_deep_4turn_18_grade8_hk1_rhombus_square():
    """Case 18: Lớp 8 HK1 Hình thoi và hình vuông (Trường học đến Định lí Thalès -> Đã học nhưng quên)."""
    execute_4_turn_scenario(
        grade=8,
        topic_c_name="Hình thoi và hình vuông",
        req_1_student="Tính chất hai đường chéo hình thoi này lạ hoắc à thầy",
        req_2_student="Trên trường em đang học bài Định lí Thalès trong tam giác rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Định lí Thalès rồi thì trong chương trình HK1 lớp 8, em đã học bài Hình thoi và hình vuông rồi. Có lẽ em quên nên thầy nhắc lại: Hai đường chéo của hình thoi vuông góc với nhau và cắt nhau tại trung điểm mỗi đường. Vậy góc giữa hai đường chéo bằng bao nhiêu độ em?",
        req_3_student="Dạ bằng 90 độ vì vuông góc ạ",
        res_3_step2_ai="Chính xác! Giờ tam giác tạo bởi nửa hai đường chéo là tam giác vuông. Cạnh huyền chính là cạnh hình thoi. Em nhớ định lý nào để tính cạnh huyền không?",
        req_4_student="Dạ định lý Pytago thầy ơi!",
    )


def test_deep_4turn_19_grade9_hk1_simplify_roots():
    """Case 19: Lớp 9 HK1 Rút gọn căn thức bậc hai (Trường mới học Phương trình bậc nhất hai ẩn -> Chưa học)."""
    execute_4_turn_scenario(
        grade=9,
        topic_c_name="Biến đổi đơn giản và rút gọn biểu thức chứa căn thức bậc hai",
        req_1_student="Biểu thức căn thức phức tạp này mới toanh em chưa thấy bao giờ",
        req_2_student="Ở trường em mới học Khái niệm phương trình và hệ hai phương trình bậc nhất hai ẩn thôi",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Thầy hướng dẫn từng bước nhỏ nhé. Với biểu thức căn của (x - 3)^2, công thức cơ bản là căn(A^2) = |A|. Em hãy viết lại biểu thức dưới dạng giá trị tuyệt đối giúp thầy nào.",
        req_3_student="Dạ thành trị tuyệt đối của x - 3, tức là |x - 3| ạ",
        res_3_step2_ai="Đúng rồi! Đề bài cho điều kiện x >= 3, vậy biểu thức x - 3 mang dấu dương hay âm, và |x - 3| phá dấu ra bằng gì em?",
        req_4_student="Vì x >= 3 nên x - 3 >= 0, vậy |x - 3| bằng chính nó là x - 3 thầy ơi",
    )


def test_deep_4turn_20_grade9_hk1_linear_system():
    """Case 20: Lớp 9 HK1 Giải hệ phương trình (Trường học đến Giải bài toán lập hệ -> Đã học nhưng quên)."""
    execute_4_turn_scenario(
        grade=9,
        topic_c_name="Giải hệ hai phương trình bậc nhất hai ẩn",
        req_1_student="Cách giải hệ phương trình bằng phương pháp cộng đại số này lạ quá em quên mất",
        req_2_student="Ở lớp em học đến Giải bài toán bằng cách lập hệ phương trình rồi ạ",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Giải bài toán bằng cách lập hệ phương trình rồi thì trong chương trình HK1 lớp 9, em đã học bài Giải hệ hai phương trình rồi. Có lẽ em quên nên thầy nhắc lại: Phương pháp cộng đại số là cộng hoặc trừ từng vế hai phương trình để triệt tiêu một ẩn. Với hệ: x + y = 5 và x - y = 1, nếu cộng hai vế lại ta được gì em?",
        req_3_student="y với -y hết, x + x thành 2x = 6 ạ",
        res_3_step2_ai="Rất chính xác! 2x = 6 thì x bằng bao nhiêu, và thế vào phương trình đầu tìm y giúp thầy nhé.",
        req_4_student="x = 3, thế vào x + y = 5 thì y = 2 thầy ơi",
    )


# ==============================================================================
# PHẦN 3: 10 TEST CASES - CHUỖI ĐỐI THOẠI SÂU 5 LƯỢT (5 REQUESTS <-> 5 RESPONSES)
# ==============================================================================

def test_deep_5turn_21_grade5_hk2_cube_surface():
    """Case 21: Lớp 5 HK2 Diện tích xung quanh hình lập phương (Chưa học -> 5 lượt hoàn chỉnh)."""
    execute_5_turn_scenario(
        grade=5,
        topic_c_name="Diện tích xung quanh và diện tích toàn phần của hình lập phương",
        req_1_student="Bài hình lập phương này lạ hoắc à thầy",
        req_2_student="Ở lớp em mới học bài Xăng-ti-mét khối thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Vì em chưa học tới bài này nên thầy giải thích từ từ nhé. Hình lập phương có 6 mặt là các hình vuông bằng nhau. Diện tích xung quanh là diện tích 4 mặt bên. Diện tích 1 mặt hình vuông cạnh a là gì em?",
        req_3_student="Dạ diện tích 1 mặt là a nhân a ạ",
        res_3_step2_ai="Chính xác! Vậy diện tích xung quanh gồm 4 mặt thì ta lấy diện tích 1 mặt nhân mấy?",
        req_4_student="Dạ nhân 4 đúng không thầy",
        res_4_step3_ai="Rất giỏi! Giờ với hình lập phương cạnh 3 cm, em tính diện tích 1 mặt rồi nhân 4 giúp thầy nhé.",
        req_5_student="3 x 3 = 9, rồi 9 x 4 = 36 cm vuông thầy ơi",
    )


def test_deep_5turn_22_grade5_hk2_speed_motion():
    """Case 22: Lớp 5 HK2 Vận tốc chuyển động đều (Đã học nhưng quên -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=5,
        topic_c_name="Vận tốc của một chuyển động đều",
        req_1_student="Công thức tính vận tốc này lạ lẫm quá em chưa nhớ",
        req_2_student="Ở trường em học đến Biểu đồ hình quạt tròn rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Biểu đồ hình quạt tròn rồi thì trong chương trình HK2 lớp 5, em đã học bài Vận tốc rồi. Có lẽ em quên nên thầy nhắc lại: Muốn tính vận tốc ta lấy quãng đường chia cho thời gian: v = s : t. Đề bài cho quãng đường s là bao nhiêu km em?",
        req_3_student="Quãng đường s = 120 km ạ",
        res_3_step2_ai="Đúng rồi! Và ô tô đi hết thời gian t là 2 giờ. Em thay số vào công thức v = s : t xem vận tốc bằng bao nhiêu?",
        req_4_student="120 chia cho 2 bằng 60 ạ",
        res_4_step3_ai="Tuyệt vời! Vậy vận tốc của ô tô là 60 kèm theo đơn vị đo là gì em nhỉ?",
        req_5_student="Dạ đơn vị là km/h, vận tốc là 60 km/h thầy ơi",
    )


def test_deep_5turn_23_grade6_hk2_fraction_operations():
    """Case 23: Lớp 6 HK2 Phép nhân và chia phân số (Chưa học -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=6,
        topic_c_name="Phép nhân và phép chia phân số",
        req_1_student="Phép chia hai phân số 2/3 chia 4/5 này mới toanh em chưa thấy",
        req_2_student="Ở trường em mới học bài Mở rộng phân số thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Thầy hướng dẫn cách làm cực dễ nhé: Muốn chia cho một phân số, ta lấy phân số thứ nhất nhân với phân số nghịch đảo của phân số thứ hai. Phân số nghịch đảo của 4/5 là gì em?",
        req_3_student="Nghịch đảo là đảo ngược tử và mẫu thành 5/4 phải không thầy",
        res_3_step2_ai="Chuẩn luôn! Vậy phép chia 2/3 : 4/5 trở thành phép nhân 2/3 x 5/4. Khi nhân hai phân số, ta lấy tử nhân tử, mẫu nhân mẫu. Tử số mới là bao nhiêu?",
        req_4_student="2 nhân 5 là 10, mẫu là 3 nhân 4 là 12, thành 10/12 ạ",
        res_4_step3_ai="Rất tốt! Giờ em rút gọn phân số 10/12 cho 2 giúp thầy để được phân số tối giản nhé.",
        req_5_student="10 chia 2 được 5, 12 chia 2 được 6, kết quả tối giản là 5/6 thầy ơi",
    )


def test_deep_5turn_24_grade6_hk2_double_bar_chart():
    """Case 24: Lớp 6 HK2 Biểu đồ cột kép (Cô bỏ qua bài -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=6,
        topic_c_name="Biểu đồ cột kép",
        req_1_student="Biểu đồ cột kép này cô em bỏ qua không dạy trên lớp",
        req_2_student="Cô nhảy cóc bài này chuyển sang học xác suất luôn thầy",
        expected_scenario="SCENARIO_B_SKIPPED",
        res_2_step1_ai="Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé! Biểu đồ cột kép dùng để so sánh hai nhóm dữ liệu cạnh nhau (ví dụ số học sinh nam và nữ). Cột màu xanh biểu thị gì trên biểu đồ em nhìn giúp thầy?",
        req_3_student="Cột xanh là số học sinh Giỏi còn cột cam là học sinh Khá ạ",
        res_3_step2_ai="Đúng rồi! Giờ đề bài hỏi lớp 6A có bao nhiêu học sinh Giỏi, em nhìn cột màu xanh của lớp 6A chỉ vào vạch số mấy?",
        req_4_student="Chỉ vào vạch số 15 ạ",
        res_4_step3_ai="Chính xác! Vậy lớp 6A có 15 bạn học sinh Giỏi. Cách đọc thật đơn giản đúng không em?",
        req_5_student="Dạ đọc biểu đồ cột kép cũng dễ hiểu ghê thầy ơi, em cảm ơn thầy",
    )


def test_deep_5turn_25_grade7_hk2_polynomial_root():
    """Case 25: Lớp 7 HK2 Đa thức một biến (Chưa học -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=7,
        topic_c_name="Đa thức một biến",
        req_1_student="Khái niệm nghiệm của đa thức một biến này nghe lạ tai ghê á",
        req_2_student="Ở trường em mới học bài Tỉ lệ thức thôi thầy ơi",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Thầy giải thích từ gốc rễ nhé: Nghiệm của đa thức P(x) là giá trị của x làm cho P(x) = 0. Cho đa thức P(x) = 2x - 6, để tìm nghiệm ta cho biểu thức nào bằng 0 em?",
        req_3_student="Dạ cho 2x - 6 = 0 ạ",
        res_3_step2_ai="Đúng rồi! Giờ em chuyển số -6 sang vế phải thì 2x bằng mấy?",
        req_4_student="2x = 6 ạ",
        res_4_step3_ai="Rất tốt! Vậy x bằng bao nhiêu để 2 nhân x bằng 6?",
        req_5_student="x = 6 / 2 = 3, vậy x = 3 là nghiệm của đa thức thầy ơi",
    )


def test_deep_5turn_26_grade7_hk2_triangle_sides():
    """Case 26: Lớp 7 HK2 Quan hệ giữa ba cạnh tam giác (Đã học nhưng quên -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=7,
        topic_c_name="Quan hệ giữa ba cạnh của một tam giác",
        req_1_student="Bất đẳng thức ba cạnh tam giác này lạ hoắc à, em quên mất tiêu",
        req_2_student="Ở trường em học đến Hình lăng trụ đứng tam giác rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Hình lăng trụ đứng rồi thì trong chương trình HK2 lớp 7, em đã học bài Quan hệ ba cạnh tam giác rồi. Có lẽ em quên nên thầy nhắc lại: Trong một tam giác, tổng độ dài hai cạnh bất kỳ luôn lớn hơn cạnh còn lại. Đề cho ba đoạn thẳng 2 cm, 3 cm, 6 cm, tổng hai cạnh ngắn là mấy?",
        req_3_student="2 + 3 = 5 cm ạ",
        res_3_step2_ai="Đúng rồi! Giờ em so sánh tổng 5 cm này với cạnh thứ ba dài 6 cm xem nó lớn hơn hay bé hơn?",
        req_4_student="5 bé hơn 6 cm ạ",
        res_4_step3_ai="Chính xác! Vì tổng hai cạnh nhỏ hơn cạnh thứ ba nên ba đoạn thẳng này có ghép thành tam giác được không em?",
        req_5_student="Dạ không ghép thành tam giác được vì vi phạm bất đẳng thức tam giác thầy ơi",
    )


def test_deep_5turn_27_grade8_hk2_first_degree_equation():
    """Case 27: Lớp 8 HK2 Phương trình bậc nhất một ẩn (Chưa học -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=8,
        topic_c_name="Phương trình bậc nhất một ẩn",
        req_1_student="Phương trình bậc nhất một ẩn ax + b = 0 này mới toanh em chưa từng học",
        req_2_student="Ở trường em mới học bài Phân thức đại số thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Không sao nhé, phương trình bậc nhất rất giống bài tìm x hồi lớp 6. Với phương trình 3x - 12 = 0, bước 1 em chuyển -12 sang vế phải đổi dấu thành gì?",
        req_3_student="Chuyển vế thành 3x = 12 ạ",
        res_3_step2_ai="Rất chính xác! Giờ muốn tìm x, em lấy 12 chia cho mấy?",
        req_4_student="Lấy 12 chia 3 được x = 4 ạ",
        res_4_step3_ai="Rất giỏi! Giờ em thử thay x = 4 ngược lại vào 3x - 12 xem có đúng bằng 0 không nào.",
        req_5_student="3 nhân 4 là 12, trừ 12 bằng 0 chuẩn luôn thầy ơi",
    )


def test_deep_5turn_28_grade8_hk2_pythagoras_similarity():
    """Case 28: Lớp 8 HK2 Định lí Pythagore và ứng dụng (Cô lướt qua bài -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=8,
        topic_c_name="Định lí Pythagore và ứng dụng",
        req_1_student="Định lí pythagore này cô em lướt qua trên lớp em không hiểu",
        req_2_student="Thầy cô bỏ qua bài định lí pythagore nhảy sang tam giác đồng dạng luôn",
        expected_scenario="SCENARIO_B_SKIPPED",
        res_2_step1_ai="Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé! Định lí Pythagore phát biểu: Trong tam giác vuông, bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông: a^2 + b^2 = c^2. Cho hai cạnh góc vuông là 3 và 4, 3 bình phương cộng 4 bình phương bằng bao nhiêu em?",
        req_3_student="3^2 = 9, 4^2 = 16, 9 + 16 = 25 ạ",
        res_3_step2_ai="Đúng rồi! Cạnh huyền bình phương bằng 25, vậy cạnh huyền c bằng bao nhiêu?",
        req_4_student="Căn 25 là bằng 5 ạ",
        res_4_step3_ai="Tuyệt vời! Vậy bộ ba cạnh 3, 4, 5 là bộ ba Pythagore kinh điển. Em thấy định lý này dễ nhớ không?",
        req_5_student="Dạ rất dễ nhớ thầy ạ, em hiểu rõ bản chất rồi",
    )


def test_deep_5turn_29_grade9_hk2_quadratic_equation():
    """Case 29: Lớp 9 HK2 Phương trình bậc hai một ẩn (Chưa học -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=9,
        topic_c_name="Phương trình bậc hai một ẩn",
        req_1_student="Công thức nghiệm delta của phương trình bậc hai này mới toanh em chưa thấy bao giờ",
        req_2_student="Ở trường em mới học Hàm số y = ax2 thôi thầy ơi",
        expected_scenario="SCENARIO_B_NEW",
        res_2_step1_ai="Thầy hướng dẫn từng bước tính delta nhé: Phương trình ax^2 + bx + c = 0 có biệt thức Delta = b^2 - 4ac. Với phương trình x^2 - 4x + 3 = 0, em xác định giúp thầy hệ số a, b, c là gì?",
        req_3_student="a = 1, b = -4, c = 3 đúng không thầy",
        res_3_step2_ai="Chính xác! Giờ em thay vào công thức Delta = (-4)^2 - 4*1*3 xem bằng mấy?",
        req_4_student="(-4)^2 là 16, trừ đi 12 thì Delta = 4 ạ",
        res_4_step3_ai="Rất tốt! Vì Delta = 4 > 0 nên phương trình có hai nghiệm phân biệt. Căn bậc hai của Delta là căn 4 bằng mấy em?",
        req_5_student="Căn 4 bằng 2, vậy x1 = (4 + 2)/2 = 3 và x2 = (4 - 2)/2 = 1 thầy ơi",
    )


def test_deep_5turn_30_grade9_hk2_inscribed_angle():
    """Case 30: Lớp 9 HK2 Góc nội tiếp (Đã học nhưng quên -> 5 lượt)."""
    execute_5_turn_scenario(
        grade=9,
        topic_c_name="Góc nội tiếp",
        req_1_student="Mối quan hệ giữa góc nội tiếp và góc ở tâm này lạ quá em quên mất",
        req_2_student="Ở trường em học đến Đa giác đều rồi thầy ơi",
        expected_scenario="SCENARIO_A_OLD",
        res_2_step1_ai="Hiện tại nếu em đã học đến Đa giác đều rồi thì trong chương trình HK2 lớp 9, em đã học bài Góc nội tiếp rồi. Có lẽ em quên nên thầy nhắc lại: Góc nội tiếp bằng nửa số đo của góc ở tâm cùng chắn một cung. Nếu góc ở tâm chắn cung AB có số đo là 80 độ thì góc nội tiếp chắn cung AB bằng bao nhiêu độ em?",
        req_3_student="Dạ lấy 80 chia 2 là bằng 40 độ ạ",
        res_3_step2_ai="Đúng rồi! Và số đo của cung bị chắn AB chính bằng số đo góc ở tâm, tức là 80 độ. Vậy góc nội tiếp bằng bao nhiêu lần số đo cung bị chắn?",
        req_4_student="Dạ góc nội tiếp bằng một nửa số đo cung bị chắn ạ",
        res_4_step3_ai="Chính xác hoàn toàn! Em đã nhớ lại định lý rất nhanh. Thầy chúc mừng em nhé!",
        req_5_student="Dạ em nhớ lại rồi, em cảm ơn thầy nhiều ạ",
    )
