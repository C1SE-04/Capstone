from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
import os
from datetime import datetime, timezone

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

# Đường dẫn tới file rubric JSON
RUBRIC_FILE_PATH = os.path.join(os.path.dirname(__file__), "independence_rubric.json")

def load_independence_rubric() -> Dict[str, Any]:
    """
    Đọc file cấu hình barem điểm JSON.
    Nếu không tìm thấy file, trả về cấu hình mặc định an toàn.
    """
    if os.path.exists(RUBRIC_FILE_PATH):
        try:
            with open(RUBRIC_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass #Lỗi thì bỏ qua, dùng cấu hình mặc định
    return {
        "version": "1.0.0",
        "scoring_rules": {
            "base_score": 100,
            "hint_penalty": 5,
            "struggle_penalty": 10,
            "time_penalties": [
                {"threshold_seconds": 1800, "penalty": 10},
                {"threshold_seconds": 900, "penalty": 5},
            ],
            "floor_score": 10,
            "ceiling_score": 100,
        },
        "mastery_levels": [
            {"min_score": 80, "max_score": 100, "label": "Tự lập xuất sắc (ít dùng gợi ý)"},
            {"min_score": 60, "max_score": 79, "label": "Tự lập tốt (dùng 1-2 gợi ý)"},
            {"min_score": 40, "max_score": 59, "label": "Đang tiến bộ (cần một số gợi ý)"},
            {"min_score": 0, "max_score": 39, "label": "Cần thêm hỗ trợ sư phạm"},
        ],
    }


def export_independence_json(
    hints_used: int = 0,
    not_understood_count: int = 0,
    solving_time_seconds: int = 0,
    session_id: Optional[str] = None,
    student_id: Optional[str] = None,
    indent: Optional[int] = None,
) -> str:
    """
    Tính toán và xuất kết quả đánh giá tự lực dưới dạng chuỗi JSON chuẩn hóa.
    Đầu ra tương thích hoàn toàn với schema của Backend API và Frontend.
    """
    eval_result = evaluate_independence(
        hints_used=hints_used,
        not_understood_count=not_understood_count,
        solving_time_seconds=solving_time_seconds,
    )

    data = {
        "session_id": session_id,
        "student_id": student_id,
        "score": eval_result.score,
        "hints_used": eval_result.hints_used,
        "not_understood_count": eval_result.not_understood_count,
        "solving_time_seconds": eval_result.solving_time_seconds,
        "level": eval_result.level,
        "penalties": {
            "hint_penalty": eval_result.hint_penalty,
            "struggle_penalty": eval_result.struggle_penalty,
            "time_penalty": eval_result.time_penalty,
        },
        "quick_answer_warning": eval_result.quick_answer_warning,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    return json.dumps(data, ensure_ascii=False, indent=indent)