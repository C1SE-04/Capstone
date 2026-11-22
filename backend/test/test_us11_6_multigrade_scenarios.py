"""
US 11.6: Bộ Kiểm Thử Tự Động Toàn Diện Luồng Socratic Bridge ("Bài A-B-C-D")
Bao phủ toàn bộ Khối Lớp 5 -> 9, mỗi lớp gồm cả 2 Học kỳ (HK1 và HK2),
mỗi kỳ gồm 2 bài học cách xa nhau.
Mỗi bài test thực hiện đúng chuẩn 3 LƯỢT HỘI THOẠI ĐẦY ĐỦ (3 Requests -> 3 Responses):
- Lượt 1: Học sinh than chưa học bài C -> Hệ thống hỏi thăm dò (Probe) có tag <!-- PROBE_PENDING -->
- Lượt 2: Học sinh phản hồi tiến độ (B < C, E > C, hoặc cô bỏ qua bài) -> Hệ thống điều phối Kịch bản tương ứng
- Lượt 3: Học sinh trả lời bước 1 / gợi nhớ -> Hệ thống dẫn dắt tiếp bước 2, đảm bảo KHÔNG lặp lại câu hỏi thăm dò.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import _agent


def execute_3_turn_socratic_bridge(
    grade: int,
    semester: int,
    topic_c_name: str,
    req_1_student: str,
    req_2_student: str,
    expected_scenario: str,  # "SCENARIO_B_NEW" | "SCENARIO_A_OLD" | "SCENARIO_B_SKIPPED"
    req_3_student: str,
    step1_guidance_text: str,
):
    """
    Helper thực thi chu trình 3 lượt tương tác hoàn chỉnh:
    Turn 1 (Req 1 -> Res 1) -> Turn 2 (Req 2 -> Res 2) -> Turn 3 (Req 3 -> Res 3).
    """
    # ── LƯỢT 1: Học sinh gửi câu hỏi và than chưa học bài C ──
    res_1 = _agent.route_sync(req_1_student, student_grade=grade)
    assert res_1["selected_agent"] == "SCAFFOLDING", f"Lớp {grade} HK{semester}: Lượt 1 phải chọn SCAFFOLDING"
    assert "PROBE_PENDING" in res_1["task_description"], f"Lớp {grade} HK{semester}: Lượt 1 phải yêu cầu gắn PROBE_PENDING"

    # Mô phỏng phản hồi 1 của hệ thống (AI gửi câu hỏi thăm dò mở kèm tên bài C)
    res_1_simulated = (
        f"Hiện tại trên trường em đã học đến bài nào rồi, bài {topic_c_name} này em đã học qua chưa? <!-- PROBE_PENDING -->"
    )

    # ── LƯỢT 2: Học sinh trả lời câu hỏi thăm dò về tiến độ ──
    h_turn_2 = f"[USER]: {req_1_student}\n[AGENT]: {res_1_simulated}\n"
    res_2 = _agent.route_sync(req_2_student, history_text=h_turn_2, student_grade=grade)
    assert res_2["selected_agent"] == "SCAFFOLDING", f"Lớp {grade} HK{semester}: Lượt 2 phải tiếp tục SCAFFOLDING"
    assert "US 11.6 CURRICULUM ORDER" in res_2["task_description"], f"Lớp {grade} HK{semester}: Lượt 2 phải inject thứ tự bài"

    # Kiểm tra kịch bản phân nhánh sư phạm
    if expected_scenario in ("SCENARIO_B_NEW", "SCENARIO_B_SKIPPED"):
        assert "KỊCH BẢN B" in res_2["task_description"], f"Lớp {grade} HK{semester}: Phải áp dụng Kịch bản B"
        if expected_scenario == "SCENARIO_B_SKIPPED":
            assert "bình thường nhé" in res_2["task_description"] or "Đôi khi thầy cô" in res_2["task_description"]
    elif expected_scenario == "SCENARIO_A_OLD":
        assert "KỊCH BẢN A" in res_2["task_description"], f"Lớp {grade} HK{semester}: Phải áp dụng Kịch bản A"

    # Mô phỏng phản hồi 2 của hệ thống (AI hướng dẫn bước 1 theo kịch bản)
    res_2_simulated = step1_guidance_text

    # ── LƯỢT 3: Học sinh trả lời bước 1 / nhớ lại kiến thức cũ ──
    h_turn_3 = (
        f"[USER]: {req_1_student}\n"
        f"[AGENT]: {res_1_simulated}\n"
        f"[USER]: {req_2_student}\n"
        f"[AGENT]: {res_2_simulated}\n"
    )
    res_3 = _agent.route_sync(req_3_student, history_text=h_turn_3, student_grade=grade)
    assert res_3["selected_agent"] in ("SCAFFOLDING", "MISCONCEPTION", "KNOWLEDGE_TRACING"), f"Lớp {grade} HK{semester}: Lượt 3 phải điều phối sư phạm"
    # Kiểm tra điều kiện chống lặp: Lượt 3 tuyệt đối KHÔNG hỏi lại câu thăm dò
    assert "<!-- PROBE_PENDING -->" not in res_3.get("task_description", "")
    assert "DỪNG LẠI Ở CÂU HỎI THĂM DÒ" not in res_3.get("task_description", "")


# =========================================================================
# KHỐI LỚP 5: HK1 & HK2 (4 test cases)
# =========================================================================

def test_grade_5_hk1_lesson_1_learn_new():
    """Lớp 5 HK1 - Bài 1: 'Khái niệm số thập phân' (học sinh mới học bài 'Cộng trừ phân số' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=5,
        semester=1,
        topic_c_name="Khái niệm số thập phân",
        req_1_student="Thầy ơi bài khái niệm số thập phân này em chưa học bao giờ ạ",
        req_2_student="Dạ trên trường em mới học đến cộng trừ hai phân số khác mẫu thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ phân số một phần mười viết thành 0.1 phải không thầy?",
        step1_guidance_text="Không sao em nhé, số thập phân rất dễ hiểu! Em thử xem phân số 1/10 có thể viết thành dạng nào nhé.",
    )


def test_grade_5_hk1_lesson_2_forgot_old():
    """Lớp 5 HK1 - Bài 2: 'Hình tam giác. Diện tích hình tam giác' (học sinh học đến 'Thể tích hình hộp chữ nhật' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=5,
        semester=1,
        topic_c_name="Diện tích hình tam giác",
        req_1_student="Bài tính diện tích hình tam giác này hình như em chưa học thầy ơi",
        req_2_student="Dạ trên trường em học đến bài thể tích hình hộp chữ nhật rồi ạ",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="A em nhớ rồi, lấy độ dài đáy nhân với chiều cao rồi chia cho 2 đúng không thầy?",
        step1_guidance_text="Hiện tại nếu em đã học đến thể tích hình hộp chữ nhật rồi thì em đã học bài diện tích hình tam giác rồi. Có lẽ em quên nên thầy nhắc lại nhé: Muốn tính diện tích tam giác ta lấy đáy nhân chiều cao chia 2.",
    )


def test_grade_5_hk2_lesson_1_learn_new():
    """Lớp 5 HK2 - Bài 1: 'Tìm giá trị phần trăm của một số' (học sinh mới học 'Tỉ số phần trăm' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=5,
        semester=2,
        topic_c_name="Tìm giá trị phần trăm của một số",
        req_1_student="Thầy ơi bài tìm giá trị phần trăm của một số em chưa học",
        req_2_student="Trên lớp em mới học bài tỉ số phần trăm đầu tiên thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ muốn tìm 20% của 100 thì em lấy 100 nhân 20 rồi chia 100 được 20 phải không thầy?",
        step1_guidance_text="Để thầy chỉ em từ từ nhé! Giả sử em có 100 cái kẹo, 20% số kẹo đó sẽ là bao nhiêu cái nhỉ?",
    )


def test_grade_5_hk2_lesson_2_forgot_old():
    """Lớp 5 HK2 - Bài 2: 'Mét khối' (học sinh học đến 'Vận tốc chuyển động đều' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=5,
        semester=2,
        topic_c_name="Mét khối",
        req_1_student="Bài mét khối này em chưa được học bao giờ",
        req_2_student="Ở lớp em học đến bài toán vận tốc quãng đường rồi thầy ơi",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ 1 mét khối bằng 1000 đề-xi-mét khối em nhớ ra rồi ạ",
        step1_guidance_text="Hiện tại nếu em đã học đến vận tốc rồi thì em đã học bài mét khối rồi. Em nhớ lại xem 1 mét khối gấp bao nhiêu lần 1 đề-xi-mét khối nhé?",
    )


# =========================================================================
# KHỐI LỚP 6: HK1 & HK2 (4 test cases)
# =========================================================================

def test_grade_6_hk1_lesson_1_learn_new():
    """Lớp 6 HK1 - Bài 1: 'Số nguyên tố' (học sinh mới học 'Lũy thừa với số mũ tự nhiên' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=6,
        semester=1,
        topic_c_name="Số nguyên tố",
        req_1_student="Em chưa học bài số nguyên tố này thầy ơi",
        req_2_student="Dạ trên trường em mới học đến bài lũy thừa thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ số nguyên tố là số chỉ có hai ước là 1 và chính nó phải không thầy?",
        step1_guidance_text="Thầy sẽ giảng từ nền tảng nhé! Em thử xem các số tự nhiên lớn hơn 1 nào chỉ chia hết cho 1 và chính nó nào.",
    )


def test_grade_6_hk1_lesson_2_forgot_old():
    """Lớp 6 HK1 - Bài 2: 'Phép nhân số nguyên' (học sinh học đến 'Cộng trừ phân số' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=6,
        semester=1,
        topic_c_name="Phép nhân số nguyên",
        req_1_student="Hình như em chưa học phép nhân số nguyên âm thầy ơi",
        req_2_student="Ở lớp em học qua bài cộng trừ phân số rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ âm nhân âm ra dương, ví dụ âm hai nhân âm ba bằng sáu đúng không thầy?",
        step1_guidance_text="Hiện tại nếu em đã học đến cộng trừ phân số thì em đã học bài nhân số nguyên rồi. Có lẽ em quên quy tắc nhân hai số nguyên cùng dấu âm, thầy nhắc lại nhé!",
    )


def test_grade_6_hk2_lesson_1_learn_new():
    """Lớp 6 HK2 - Bài 1: 'Bài toán về tỉ số phần trăm' (học sinh mới học 'Mở rộng phân số' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=6,
        semester=2,
        topic_c_name="Một số bài toán về tỉ số và tỉ số phần trăm",
        req_1_student="Bài toán tỉ số phần trăm lớp 6 này em chưa học tới",
        req_2_student="Trên lớp em mới học mở rộng phân số bằng nhau thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ tỉ số của hai số a và b là a chia cho b đúng không thầy?",
        step1_guidance_text="Đừng lo em nhé, tỉ số thực chất là phép chia giữa hai đại lượng. Em thử tìm tỉ số của 3 và 5 xem nào.",
    )


def test_grade_6_hk2_lesson_2_teacher_skipped():
    """Lớp 6 HK2 - Bài 2: 'Số đo góc' (cô bảo giảm tải không dạy -> Teacher skipped)."""
    execute_3_turn_socratic_bridge(
        grade=6,
        semester=2,
        topic_c_name="Số đo góc",
        req_1_student="Thầy ơi bài số đo góc này em chưa được học",
        req_2_student="Cô em bảo bài này giảm tải không dạy, cô nhảy cóc qua bài khác luôn",
        expected_scenario="SCENARIO_B_SKIPPED",
        req_3_student="Dạ góc bẹt có số đo bằng 180 độ phải không thầy?",
        step1_guidance_text="Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé! Thầy sẽ hướng dẫn em cách đọc số đo góc bằng thước đo độ thật dễ hiểu.",
    )


# =========================================================================
# KHỐI LỚP 7: HK1 & HK2 (4 test cases)
# =========================================================================

def test_grade_7_hk1_lesson_1_learn_new():
    """Lớp 7 HK1 - Bài 1: 'Số vô tỉ. Căn bậc hai số học' (học sinh mới học 'Cộng trừ nhân chia số hữu tỉ' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=7,
        semester=1,
        topic_c_name="Số vô tỉ. Căn bậc hai số học",
        req_1_student="Em chưa học căn bậc hai số học thầy ơi",
        req_2_student="Trên trường em mới học cộng trừ số hữu tỉ thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ căn bậc hai số học của 9 là 3 vì 3 bình phương bằng 9 đúng không thầy?",
        step1_guidance_text="Rất dễ hiểu em nhé! Căn bậc hai số học của một số không âm a là số x không âm sao cho x bình phương bằng a. Em thử tìm số nào bình phương bằng 9 nhé.",
    )


def test_grade_7_hk1_lesson_2_forgot_old():
    """Lớp 7 HK1 - Bài 2: 'Tổng các góc trong một tam giác' (học sinh học đến 'Tam giác cân' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=7,
        semester=1,
        topic_c_name="Tổng các góc trong một tam giác",
        req_1_student="Bài tổng các góc trong một tam giác em chưa học",
        req_2_student="Dạ ở trường em học đến bài tam giác cân rồi ạ",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ tổng ba góc của một tam giác luôn bằng 180 độ em nhớ ra rồi ạ",
        step1_guidance_text="Hiện tại nếu em đã học đến tam giác cân rồi thì em đã học bài tổng ba góc rồi. Có lẽ em quên nên thầy nhắc lại: Tổng ba góc trong một tam giác luôn bằng 180 độ nhé!",
    )


def test_grade_7_hk2_lesson_1_learn_new():
    """Lớp 7 HK2 - Bài 1: 'Đa thức một biến' (học sinh mới học 'Tỉ lệ thức' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=7,
        semester=2,
        topic_c_name="Đa thức một biến",
        req_1_student="Em chưa học bài đa thức một biến thầy ơi",
        req_2_student="Trên lớp em mới học xong bài tỉ lệ thức thôi thầy",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ đa thức một biến là tổng của những đơn thức của cùng một biến phải không thầy?",
        step1_guidance_text="Thầy sẽ giảng từ khái niệm cơ bản nhất nhé! Đa thức một biến là tổng của các đơn thức cùng chứa một biến x. Ví dụ như 2x^2 + 3x - 1.",
    )


def test_grade_7_hk2_lesson_2_forgot_old():
    """Lớp 7 HK2 - Bài 2: 'Quan hệ giữa ba cạnh của một tam giác' (học sinh học đến 'Hình lăng trụ đứng' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=7,
        semester=2,
        topic_c_name="Quan hệ giữa ba cạnh của một tam giác",
        req_1_student="Bất đẳng thức ba cạnh tam giác em chưa học thầy ơi",
        req_2_student="Trường em học sang phần hình lăng trụ đứng tam giác rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ trong một tam giác, độ dài một cạnh luôn nhỏ hơn tổng hai cạnh còn lại đúng không thầy?",
        step1_guidance_text="Hiện tại nếu em đã học đến hình lăng trụ đứng thì em đã học quan hệ ba cạnh tam giác rồi. Có lẽ em quên: trong tam giác, tổng hai cạnh luôn lớn hơn cạnh thứ ba nhé!",
    )


# =========================================================================
# KHỐI LỚP 8: HK1 & HK2 (4 test cases)
# =========================================================================

def test_grade_8_hk1_lesson_1_learn_new():
    """Lớp 8 HK1 - Bài 1: 'Phân tích đa thức thành nhân tử' (học sinh mới học 'Cộng trừ đa thức' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=8,
        semester=1,
        topic_c_name="Phân tích đa thức thành nhân tử",
        req_1_student="Thầy ơi bài phân tích đa thức thành nhân tử em chưa học",
        req_2_student="Dạ trên lớp em mới học cộng trừ đa thức thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ đặt nhân tử chung ra ngoài trước, ví dụ 2x + 4 thì đặt 2 ra ngoài phải không thầy?",
        step1_guidance_text="Thầy sẽ hướng dẫn phương pháp đầu tiên rất trực quan là đặt nhân tử chung nhé! Với biểu thức 2x + 4, em thấy cả hai số hạng cùng chia hết cho mấy nào?",
    )


def test_grade_8_hk1_lesson_2_forgot_old():
    """Lớp 8 HK1 - Bài 2: 'Định lí Thalès trong tam giác' (học sinh học đến 'Phân tích số liệu thống kê' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=8,
        semester=1,
        topic_c_name="Định lí Thalès trong tam giác",
        req_1_student="Bài định lí Thalès này em chưa học bao giờ thầy ơi",
        req_2_student="Dạ trên lớp em học đến phần phân tích số liệu thống kê rồi thầy",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ nếu một đường thẳng song song với một cạnh của tam giác thì định ra trên hai cạnh kia những đoạn thẳng tương ứng tỉ lệ đúng không thầy?",
        step1_guidance_text="Hiện tại nếu em đã học đến thống kê cuối HK1 thì em đã học định lí Thalès rồi. Em nhớ lại xem: khi có đường thẳng song song một cạnh thì các đoạn thẳng trên hai cạnh bên có tỉ lệ như thế nào?",
    )


def test_grade_8_hk2_lesson_1_learn_new():
    """Lớp 8 HK2 - Bài 1: 'Phương trình bậc nhất một ẩn' (học sinh mới học 'Phân thức đại số' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=8,
        semester=2,
        topic_c_name="Phương trình bậc nhất một ẩn",
        req_1_student="Em chưa học phương trình bậc nhất một ẩn thầy ơi",
        req_2_student="Dạ trường em mới học bài phân thức đại số thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ ta chuyển vế hạng tử tự do rồi đổi dấu, sau đó chia cho hệ số của x phải không thầy?",
        step1_guidance_text="Phương trình bậc nhất một ẩn có dạng ax + b = 0 với a khác 0. Em hãy thử chuyển số hạng b sang vế phải và đổi dấu xem nào.",
    )


def test_grade_8_hk2_lesson_2_teacher_skipped():
    """Lớp 8 HK2 - Bài 2: 'Định lí Pythagore và ứng dụng' (cô lướt qua bài không dạy -> Teacher skipped)."""
    execute_3_turn_socratic_bridge(
        grade=8,
        semester=2,
        topic_c_name="Định lí Pythagore và ứng dụng",
        req_1_student="Em chưa học bài định lí Pythagore này bao giờ",
        req_2_student="Cô em lướt qua bài này luôn không dạy thầy ơi",
        expected_scenario="SCENARIO_B_SKIPPED",
        req_3_student="Dạ bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông phải không thầy?",
        step1_guidance_text="Đôi khi thầy cô lướt qua bài này nên em chưa học là bình thường nhé! Định lí Pythagore chỉ áp dụng cho tam giác vuông: bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông.",
    )


# =========================================================================
# KHỐI LỚP 9: HK1 & HK2 (4 test cases)
# =========================================================================

def test_grade_9_hk1_lesson_1_learn_new():
    """Lớp 9 HK1 - Bài 1: 'Biến đổi đơn giản và rút gọn căn thức' (học sinh mới học 'Giải hệ hai phương trình' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=9,
        semester=1,
        topic_c_name="Biến đổi đơn giản và rút gọn biểu thức chứa căn thức bậc hai",
        req_1_student="Em chưa học rút gọn biểu thức chứa căn bậc hai thầy ơi",
        req_2_student="Trên trường em mới học giải hệ hai phương trình thôi thầy",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ đưa thừa số ra ngoài dấu căn, căn của 12 là hai căn ba đúng không thầy?",
        step1_guidance_text="Thầy sẽ chỉ em từng bước nhé! Muốn rút gọn căn 12, em hãy tách 12 = 4 * 3 rồi đưa số 4 ra ngoài căn xem được mấy nhé.",
    )


def test_grade_9_hk1_lesson_2_forgot_old():
    """Lớp 9 HK1 - Bài 2: 'Tỉ số lượng giác của góc nhọn' (học sinh học đến 'Đường thẳng và đường tròn' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=9,
        semester=1,
        topic_c_name="Tỉ số lượng giác của góc nhọn",
        req_1_student="Em chưa học sin cos tan tỉ số lượng giác",
        req_2_student="Dạ trên lớp em học đến vị trí tương đối của đường thẳng và đường tròn rồi ạ",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ sin đi học bằng đối chia huyền, cos khóc hư bằng kề chia huyền em nhớ bài thơ rồi thầy",
        step1_guidance_text="Hiện tại nếu em đã học đến đường thẳng và đường tròn thì em đã học tỉ số lượng giác rồi. Có lẽ em quên nên thầy nhắc lại: Sin đi học, Cos khóc hư, Tan đoàn kết, Cotang kết đoàn nhé!",
    )


def test_grade_9_hk2_lesson_1_learn_new():
    """Lớp 9 HK2 - Bài 1: 'Định lí Viète và ứng dụng' (học sinh mới học 'Hàm số y = ax2' -> B < C)."""
    execute_3_turn_socratic_bridge(
        grade=9,
        semester=2,
        topic_c_name="Định lí Viète và ứng dụng",
        req_1_student="Em chưa học định lí Vi-et này thầy ơi",
        req_2_student="Trên lớp em mới học hàm số y bằng a x bình phương thôi ạ",
        expected_scenario="SCENARIO_B_NEW",
        req_3_student="Dạ tổng hai nghiệm x1 cộng x2 bằng trừ b chia a, còn tích x1 nhân x2 bằng c chia a phải không thầy?",
        step1_guidance_text="Định lí Viète là công cụ tuyệt vời để tính nhẩm nghiệm phương trình ax^2 + bx + c = 0! Tổng hai nghiệm x1 + x2 = -b/a và tích x1 * x2 = c/a.",
    )


def test_grade_9_hk2_lesson_2_forgot_old():
    """Lớp 9 HK2 - Bài 2: 'Tứ giác nội tiếp' (học sinh học đến 'Hình cầu' -> E > C)."""
    execute_3_turn_socratic_bridge(
        grade=9,
        semester=2,
        topic_c_name="Tứ giác nội tiếp",
        req_1_student="Thầy ơi bài tứ giác nội tiếp em chưa học bao giờ",
        req_2_student="Dạ trường em học đến phần hình trụ hình cầu rồi thầy ơi",
        expected_scenario="SCENARIO_A_OLD",
        req_3_student="Dạ trong một tứ giác nội tiếp, tổng số đo hai góc đối diện luôn bằng 180 độ em nhớ ra rồi ạ!",
        step1_guidance_text="Hiện tại nếu em đã học đến hình cầu ở cuối năm lớp 9 thì em đã học tứ giác nội tiếp rồi. Có lẽ em quên: dấu hiệu quan trọng nhất là tổng hai góc đối diện luôn bằng 180 độ nhé!",
    )
