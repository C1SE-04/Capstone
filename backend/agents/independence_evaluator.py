from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class IndependenceEvaluation:
    score: int
    hints_used: int
    not_understood_count: int
    solving_time_seconds: int
    level: str
    hint_penalty: int
    struggle_penalty: int
    time_penalty: int
    quick_answer_warning: bool


def calculate_time_penalty(solving_time_seconds: int) -> int:
    """
    Tính từ lúc hs gửi đề bài, kết thúc khi ấn đã hiểu
    Tính điểm trừ nếu thời gian ngâm bài quá lâu:
    - <= 900s (15 phút): 0đ
    - 901s - 1800s (15 - 30 phút): trừ 5đ
    - > 1800s (> 30 phút): trừ 10đ
    """
    if solving_time_seconds > 1800:
        return 10
    elif solving_time_seconds > 900:
        return 5
    return 0


def classify_mastery_level(score: int) -> str:
    """Phân loại mức độ độc lập theo góc độ sư phạm."""
    if score >= 80:
        return "Tự lập xuất sắc (ít dùng gợi ý)"
    elif score >= 60:
        return "Tự lập tốt (dùng 1-2 gợi ý)"
    elif score >= 40:
        return "Đang tiến bộ (cần một số gợi ý)"
    else:
        return "Cần thêm hỗ trợ sư phạm"


def evaluate_independence(
    hints_used: int = 0,
    not_understood_count: int = 0,
    solving_time_seconds: int = 0,
) -> IndependenceEvaluation:
    """
    Thuật toán ngầm cốt lõi đánh giá điểm tự lực (Independence Score).
    
    Quy tắc barem:
    - Điểm gốc: 100đ
    - Mỗi hint dùng thêm: -5đ
    - Mỗi lần bấm 'Chưa hiểu': -10đ
    - Ngâm bài quá lâu (>15p): -5đ, (>30p): -10đ
    - Điểm sàn: 10đ, Điểm trần: 100đ
    """
    safe_hints = max(0, hints_used)
    safe_not_understood = max(0, not_understood_count)
    safe_time = max(0, solving_time_seconds)
    #Dùng max ở đây để tránh dự liệu âm vào, sẽ chọn 0
    
    hint_penalty = safe_hints * 5
    struggle_penalty = safe_not_understood * 10
    time_penalty = calculate_time_penalty(safe_time)

    total_deduction = hint_penalty + struggle_penalty + time_penalty
    raw_score = 100 - total_deduction

    # Điểm sàn 10đ, trần 100đ
    score = max(10, min(100, raw_score))

    level = classify_mastery_level(score)
    quick_warning = (safe_time < 15 and safe_hints == 0) if safe_time > 0 else False

    return IndependenceEvaluation(
        score=score,
        hints_used=safe_hints,
        not_understood_count=safe_not_understood,
        solving_time_seconds=safe_time,
        level=level,
        hint_penalty=hint_penalty,
        struggle_penalty=struggle_penalty,
        time_penalty=time_penalty,
        quick_answer_warning=quick_warning,
    )


def calculate_independence_score(
    hints_used: int = 0,
    not_understood_count: int = 0,
    solving_time_seconds: int = 0,
) -> Dict[str, Any]:
    """
    Hàm giao diện tiện ích (Helper) trả về dict nhanh cho các module khác.
    """
    res = evaluate_independence(
        hints_used=hints_used,
        not_understood_count=not_understood_count,
        solving_time_seconds=solving_time_seconds,
    )
    return {
        "score": res.score,
        "hints_used": res.hints_used,
        "not_understood_count": res.not_understood_count,
        "solving_time_seconds": res.solving_time_seconds,
        "level": res.level,
        "penalties": {
            "hint_penalty": res.hint_penalty,
            "struggle_penalty": res.struggle_penalty,
            "time_penalty": res.time_penalty,
        },
        "quick_answer_warning": res.quick_answer_warning,
    }
