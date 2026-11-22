from typing import Optional
import re
import hashlib
import models
from sqlalchemy.orm import Session
from sqlalchemy import desc
from schemas import ProblemClassificationResult
from agents.problem_classifier import classify_problem


def compute_problem_hash(problem_text: str) -> str:
    """
    Chuẩn hóa nội dung đề bài và tính mã băm SHA-256 (64 ký tự hex):
    - Đưa về chữ thường (lowercase)
    - Loại bỏ dấu câu cơ bản và khoảng trắng thừa
    - Đảm bảo 2 bài toán giống nhau về câu chữ dù khác khoảng trắng vẫn ra cùng 1 hash.
    """
    if not problem_text:
        return ""
    lower = problem_text.lower().strip()
    # Loại bỏ dấu câu thông thường nhưng giữ lại các ký hiệu số và phép toán cơ bản
    cleaned = re.sub(r"[.,:;!?'\"()[\]{}]", " ", lower)
    normalized = " ".join(cleaned.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


MATH_KEYWORDS_PATTERN = re.compile(
    r"\b(tính|tìm|giải|chứng minh|cho|biết|tam giác|hình|phương trình|phân số|số học sinh|vận tốc|quãng đường|diện tích|chu vi|bán kính|đoạn thẳng|góc)\b",
    re.IGNORECASE,
)

GREETING_PATTERN = re.compile(
    r"^(dạ\s+)?(em\s+)?(chào|alo|hi|hello|thầy|cô|ơi|bạn|ad|giúp em|cho em hỏi)\b",
    re.IGNORECASE,
)


def is_likely_problem_text(content: str) -> bool:
    """
    Xác định tin nhắn có phải là đề bài toán hay không:
    - Loại bỏ câu chào hỏi, xã giao mở đầu (dựa vào cấu trúc ngữ pháp và độ dài, không hardcode danh sách tĩnh).
    - Nhận diện tín hiệu toán học: chứa số, ký hiệu toán tử, ký tự LaTeX hoặc các thuật ngữ toán học.
    """
    if not content:
        return False
    text = content.strip()
    words = text.split()
    if not words:
        return False

    has_digits = bool(re.search(r"\d", text))
    has_math_symbols = bool(re.search(r"[+\-*/=<>%$^/\\_]", text))
    has_math_keywords = bool(MATH_KEYWORDS_PATTERN.search(text))
    is_math_related = has_digits or has_math_symbols or has_math_keywords

    # 1. Có dấu hiệu toán học rõ ràng và độ dài hợp lý
    if is_math_related and len(words) >= 2:
        return True

    # 2. Câu chào hỏi/xã giao mở đầu không kèm nội dung toán học
    if GREETING_PATTERN.match(text) and not is_math_related:
        return False

    # 3. Tin nhắn hội thoại ngắn (< 4 từ) không có bất kỳ yếu tố toán học nào (ví dụ: "vâng ạ", "ok thầy")
    if len(words) < 4 and not is_math_related:
        return False

    # 4. Tin nhắn mô tả tự luận dài (>= 4 từ)
    return len(words) >= 4


def extract_session_problem_text(db: Session, session_id: str) -> str:
    """
    Trích xuất đề bài toán của phiên học:
    1. Quét danh sách tin nhắn USER theo thứ tự thời gian.
    2. Chọn tin nhắn đầu tiên thỏa mãn đặc trưng đề bài toán (bỏ qua câu chào, hội thoại ngắn).
    3. Nếu không tìm thấy, fallback sang tiêu đề session (nếu có ý nghĩa).
    4. Fallback cuối cùng là nội dung tin nhắn USER đầu tiên bất kỳ hoặc 'Bài toán'.
    """
    user_msgs = (
        db.query(models.Message)
        .filter(
            models.Message.session_id == session_id,
            models.Message.sender_type == "USER"
        )
        .order_by(models.Message.created_at.asc())
        .limit(10)
        .all()
    )

    for msg in user_msgs:
        content = (msg.content or "").strip()
        if is_likely_problem_text(content):
            return content

    # Fallback 1: Tiêu đề session nếu không phải tiêu đề mặc định
    session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
    if session_obj and session_obj.title:
        title = session_obj.title.strip()
        if title and title.lower() not in ["phòng chat mới", "cuộc trò chuyện mới", "new chat"]:
            return title

    # Fallback 2: Tin nhắn USER đầu tiên (nếu có)
    for msg in user_msgs:
        if msg.content and msg.content.strip():
            return msg.content.strip()

    return "Bài toán"


def check_problem_deduplication(
    db: Session,
    student_id: str,
    current_problem: str,
    grade: Optional[int] = None,
    limit_history: int = 15,
) -> ProblemClassificationResult:
    """
    Quy trình kiểm tra Deduplication & Sinh tên bài toán 2 tầng (Gộp T8.1 + T8.3):
    1. Fast-Path: So sánh SHA-256 hash với các bài học sinh đã làm trước đó trong DB.
       Nếu trùng khớp 100% -> Tái sử dụng friendly_parent_title đã có, trả về EXACT_DUPLICATE ngay lập tức (0 token Gemini).
    2. Slow-Path: Nếu không trùng hash trực tiếp, lấy top 15 bài đã giải gần nhất của học sinh
       và gọi Gemini classify_problem(...) DUY NHẤT 1 LẦN để vừa phân loại NEW_TOPIC / ISOMORPHIC_PRACTICE
       vừa sinh friendly_parent_title chuẩn SGK.
    """
    from agents.problem_title_generator import _heuristic_title_fallback

    if not current_problem:
        fallback_title = _heuristic_title_fallback("Bài toán", grade=grade).friendly_parent_title
        return ProblemClassificationResult(
            category="NEW_TOPIC",
            confidence_score=1.0,
            reasoning="Đề bài hiện tại rỗng.",
            is_repeated_query=False,
            repeat_count=1,
            pedagogical_recommendation="Ghi nhận dạng bài mới.",
            friendly_parent_title=fallback_title,
            is_fallback=True
        )

    current_hash = compute_problem_hash(current_problem)

    # ─── TẦNG 1: FAST-PATH HASH CHECK TRONG DB ───────────────────────────
    exact_match = (
        db.query(models.IndependenceScore)
        .filter(
            models.IndependenceScore.student_id == student_id,
            models.IndependenceScore.problem_hash == current_hash
        )
        .first()
    )

    if exact_match:
        # Đếm tổng số lần đã làm bài này
        dup_count = (
            db.query(models.IndependenceScore)
            .filter(
                models.IndependenceScore.student_id == student_id,
                models.IndependenceScore.problem_hash == current_hash
            )
            .count()
        )
        # Tái sử dụng friendly_parent_title đã lưu trong bản ghi trước (0 token Gemini)
        cached_title = exact_match.friendly_parent_title
        if not cached_title:
            cached_title = _heuristic_title_fallback(
                exact_match.problem_text or current_problem,
                grade=grade
            ).friendly_parent_title

        return ProblemClassificationResult(
            category="EXACT_DUPLICATE",
            confidence_score=1.0,
            reasoning="Đề bài trùng khớp 100% mã hash SHA-256 với bài toán đã hoàn thành trước đó.",
            matched_problem=exact_match.problem_text or current_problem,
            is_repeated_query=True,
            repeat_count=dup_count + 1,
            gentle_reminder="Thầy thấy em đã giải rất tốt bài này rồi. Em có muốn thử sức bài nâng cao hơn không?",
            pedagogical_recommendation="Bỏ qua cộng dồn vào tổng bài hoàn thành, khuyến khích học sinh thử sức bài nâng cao.",
            friendly_parent_title=cached_title,
            is_fallback=False
        )

    # ─── TẦNG 2: AI SEMANTIC CHECK (GỌI GEMINI GỘP 1 LẦN DUY NHẤT) ─────────
    # Lấy danh sách tối đa N bài tập học sinh đã hoàn thành gần nhất
    recent_records = (
        db.query(models.IndependenceScore)
        .filter(
            models.IndependenceScore.student_id == student_id,
            models.IndependenceScore.problem_text.isnot(None)
        )
        .order_by(desc(models.IndependenceScore.created_at))
        .limit(limit_history)
        .all()
    )

    history_texts = [r.problem_text for r in recent_records if r.problem_text]

    # Gọi hàm AI classify_problem (1 lần duy nhất cho cả deduplication + friendly_parent_title)
    ai_result = classify_problem(
        current_problem=current_problem,
        history_problems=history_texts,
        grade=grade
    )

    return ai_result