import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from agents.reviewer import LocalReviewerAgent

def test_reviewer_allows_confirmation_when_student_answered():
    reviewer = LocalReviewerAgent()
    
    # Kịch bản trong thực tế của người dùng:
    # Học sinh vừa trả lời: "1 ạ"
    # AI phản hồi khen ngợi và xác nhận kết quả:
    student_query = "1 ạ"
    ai_response = "Thầy rất khen ngợi em vì đã tính ra kết quả rất chính xác! Phân số 4/4 rút gọn thành 1. Kết quả cuối cùng là 1."
    
    res = reviewer.review(
        student_question=student_query,
        expected_answer="",
        scaffolding_response=ai_response,
        has_comprehension=True,
    )
    
    print("[TEST 1] Review result:", res)
    assert res["is_approved"] is True, f"Bị từ chối vô lý: {res['feedback']}"
    assert "học sinh đã trả lời" in res["reasoning"].lower() or "hoàn thành bài toán" in res["reasoning"].lower()
    print("[PASS TEST 1] Reviewer cho phép AI xác nhận và khen ngợi khi học sinh vừa trả lời đúng!")


def test_reviewer_blocks_premature_answer_leak():
    reviewer = LocalReviewerAgent()
    
    # Kịch bản học sinh chưa giải mà AI đã đọc kết quả:
    student_query = "3/4 + 1/4 = bao nhiêu ạ?"
    ai_response = "Kết quả của phép tính này là 1 nhé em."
    
    res = reviewer.review(
        student_question=student_query,
        expected_answer="",
        scaffolding_response=ai_response,
        has_comprehension=False,
    )
    
    print("[TEST 2] Review result:", res)
    assert res["is_approved"] is False, "Reviewer phải chặn khi AI đọc kết quả sớm!"
    assert ("đọc thẳng kết quả" in res["feedback"] or "chốt đáp án" in res["feedback"])
    print("[PASS TEST 2] Reviewer vẫn chặn nghiêm ngặt khi AI có ý định giải bài hộ / đọc trước đáp án!")


if __name__ == "__main__":
    test_reviewer_allows_confirmation_when_student_answered()
    test_reviewer_blocks_premature_answer_leak()
    print("\n=> TẤT CẢ TEST ĐÃ HOÀN TOÀN CHÍNH XÁC!")
