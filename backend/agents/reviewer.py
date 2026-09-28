import re
from typing import TypedDict

class ReviewResult(TypedDict):
    """Cấu trúc dữ liệu kết quả kiểm duyệt."""
    is_approved: bool
    reasoning: str
    feedback: str

class LocalReviewerAgent:
    MAX_WORD_COUNT: int = 100
    QUESTION_MARK_LOOKBACK_CHARS: int = 80
    # Lớp 0: Bắt Prompt Injection từ học sinh
    PROMPT_INJECTION_PATTERN: re.Pattern = re.compile(
        r"(bỏ\s*qua|ignore|forget|quên\s*đi|xóa\s*đi|ghi\s*đè)\s*"
        r"(quy\s*tắc|hướng\s*dẫn|lệnh|instruction|rule|prompt|câu\s*lệnh)",
        re.IGNORECASE | re.UNICODE,
    )

    # Lớp 2: Lộ đáp án bằng cụm từ chốt kết quả.
    LEAK_PHRASE_PATTERN: re.Pattern = re.compile(
        r"(đáp án|kết quả|số cần tìm)\s*(là|chính là|bằng)\s*",
        re.IGNORECASE | re.UNICODE,
    )

    # Lớp 2: Lộ đáp án bằng số chữ tiếng Việt (VD: "mười lăm đó em")
    NUMBER_WORD_PATTERN: re.Pattern = re.compile(
        r"\b(không|một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|"
        r"mười\s*một|mười\s*hai|mười\s*lăm|hai\s*mươi|"
        r"ba\s*mươi|bốn\s*mươi|năm\s*mươi|một\s*trăm|"
        r"hai\s*trăm|một\s*nghìn)\s*"
        r"(đó\s*em|rồi\s*em|nhé\s*em|thôi\s*em|đấy\s*em|ạ)\s*[.!]",
        re.IGNORECASE | re.UNICODE,
    )

    # Lớp 2: Lộ đáp án qua mã LaTeX (VD: $x = 5$)
    LATEX_LEAK_PATTERN: re.Pattern = re.compile(
        r"\$[^$]*=\s*-?\d+(?:\.\d+)?(?:/\d+)?\s*\$",
        re.UNICODE,
    )

    # Lớp 2: Kết thúc bằng "= <số>"
    _EQUALS_END_PATTERN: re.Pattern = re.compile(
        r"=\s*-?\d+(?:\.\d+)?(?:/\d+)?\s*(?=[.!]|$)",
        re.UNICODE,
    )

    # Lớp 2: Ngoại lệ ví dụ minh họa
    _EXAMPLE_PREFIX_PATTERN: re.Pattern = re.compile(
        r"(ví dụ|vd|chẳng hạn)\s*[:\.]?\s*$",
        re.IGNORECASE | re.UNICODE,
    )

    # Lớp 2: Chấp nhận mẫu số chung chưa tối ưu
    SUBOPTIMAL_DENOMINATOR_PATTERN: re.Pattern = re.compile(
        r"(với|dùng|lấy)\s+mẫu\s+(số\s+)?(chung\s+)?(là\s+)?48|"
        r"48\s+là\s+mẫu\s+(số\s+)?chung\s+(chính xác|hoàn toàn đúng)|"
        r"(hoàn toàn đúng.*?48.*?mẫu\s+(số\s+)?chung)",
        re.IGNORECASE | re.UNICODE,
    )

    # Lớp 3: Từ ngữ chê bai
    NEGATIVE_BLACKLIST: tuple[str, ...] = (
        "sai rồi", "chưa đúng", "kém quá", "dễ thế", "không đúng", "ngốc", "sai hoàn toàn",
    )

    def __init__(self) -> None:
        escaped_blacklist = [re.escape(term) for term in sorted(self.NEGATIVE_BLACKLIST, key=len, reverse=True)]
        self._blacklist_pattern: re.Pattern = re.compile(
            rf"\b({'|'.join(escaped_blacklist)})\b",
            re.IGNORECASE | re.UNICODE,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _response_ends_with_question(self, response: str) -> bool:
        """Kiểm tra có kết thúc bằng câu hỏi THỰC SỰ không, bao gồm bắt câu hỏi giả."""
        has_question = False
        if "?" in response[-self.QUESTION_MARK_LOOKBACK_CHARS:]:
            has_question = True
        elif "?" in response[len(response) // 2:]:
            has_question = True

        if not has_question:
            return False

        # Bắt "câu hỏi giả": câu hỏi ở đầu nhưng chốt đáp án ở cuối
        quarter = len(response) // 4
        question_in_first_quarter = "?" in response[:quarter]
        has_conclusive_ending = bool(re.search(
            r"(là\s+\d+|bằng\s+\d+|= \d+|đó\s+em|rồi\s+đó|vậy\s+nhé)\s*[.!]?\s*$",
            response,
            re.IGNORECASE | re.UNICODE,
        ))
        
        if question_in_first_quarter and has_conclusive_ending:
            return False

        return True

    def _has_conclusive_equals_number(self, response: str) -> bool:
        matches = list(self._EQUALS_END_PATTERN.finditer(response))
        if not matches:
            return False

        for m in matches:
            start, end = m.start(), m.end()
            prefix_window = response[max(0, start - 40):start]
            if self._EXAMPLE_PREFIX_PATTERN.search(prefix_window):
                continue
                
            stripped_after = response[end:].lstrip()
            if stripped_after.startswith("?"):
                continue

            return True
        return False

    def review(
        self,
        student_question: str,
        expected_answer: str,
        scaffolding_response: str,
    ) -> ReviewResult:
        
        clean_question = self._normalize_text(student_question)
        clean_expected = self._normalize_text(expected_answer)
        clean_response = self._normalize_text(scaffolding_response)
        
        response_lower = clean_response.lower()
        expected_lower = clean_expected.lower().strip()
        question_lower = clean_question.lower()

        reasoning_logs: list[str] = []

        # =====================================================================
        # LỚP 0: KIỂM TRA PROMPT INJECTION (Pre-check)
        # =====================================================================
        if self.PROMPT_INJECTION_PATTERN.search(clean_question):
            reasoning_logs.append("[CẢNH BÁO Lớp 0]: Phát hiện Prompt Injection từ học sinh.")
            # Kiểm tra xem AI có bị lừa lộ đáp án không
            if self.LEAK_PHRASE_PATTERN.search(clean_response) or \
               (expected_lower and len(expected_lower) >= 2 and expected_lower in response_lower):
                return {
                    "is_approved": False,
                    "reasoning": " -> ".join(reasoning_logs),
                    "feedback": "Hệ thống phát hiện Prompt Injection. AI đã bị lừa tiết lộ đáp án.",
                }

        # =====================================================================
        # LỚP 1: KIỂM TRA CẤU TRÚC SOCRATIC
        # =====================================================================
        words = clean_response.split()
        if len(words) > self.MAX_WORD_COUNT:
            reasoning_logs.append(f"[FAIL Lớp 1]: Vượt giới hạn ({len(words)}/{self.MAX_WORD_COUNT} từ).")
            return {
                "is_approved": False,
                "reasoning": " -> ".join(reasoning_logs),
                "feedback": "Câu trả lời quá dài, hãy rút gọn dưới 100 từ.",
            }

        ends_with_question = self._response_ends_with_question(clean_response)
        is_praise_correct = any(p in response_lower for p in ("chính xác", "hoàn toàn đúng", "đúng rồi", "xuất sắc", "tuyệt vời", "chuẩn rồi"))
        is_requesting_problem = any(p in response_lower for p in ("gửi đề", "gõ lại đề", "đọc lại đề", "nhập đề", "chưa thấy đề"))

        if not ends_with_question:
            if is_praise_correct:
                reasoning_logs.append("[PASS Lớp 1]: Phản hồi khen ngợi (miễn dấu '?').")
            elif is_requesting_problem:
                reasoning_logs.append("[PASS Lớp 1]: Phản hồi xin đề bài (miễn dấu '?').")
            else:
                reasoning_logs.append("[FAIL Lớp 1]: Không có câu hỏi gợi mở hợp lệ ở cuối hoặc phát hiện câu hỏi giả.")
                return {
                    "is_approved": False,
                    "reasoning": " -> ".join(reasoning_logs),
                    "feedback": "Phải kết thúc bằng một câu hỏi gợi mở, không được chốt đáp án.",
                }
        else:
            reasoning_logs.append("[PASS Lớp 1]: Cấu trúc Socratic hợp lệ.")

        # =====================================================================
        # LỚP 2: KIỂM TRA LỘ ĐÁP ÁN (Answer Leakage Check)
        # =====================================================================
        student_has_answer = bool(expected_lower) and (expected_lower in question_lower)

        if not student_has_answer:
            if expected_lower and len(expected_lower) >= 2 and (expected_lower in response_lower):
                reasoning_logs.append(f"[FAIL Lớp 2]: Phản hồi chứa trực tiếp đáp án '{expected_lower}'.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Đã làm lộ đáp án chính xác."}

            leak_match = self.LEAK_PHRASE_PATTERN.search(clean_response)
            if leak_match and "?" not in clean_response[leak_match.end():]:
                reasoning_logs.append("[FAIL Lớp 2]: Khớp mẫu câu chốt kết quả.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Có dấu hiệu đọc thẳng kết quả."}

            if self._has_conclusive_equals_number(clean_response):
                reasoning_logs.append("[FAIL Lớp 2]: Khớp phép tính chốt '= số'.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Có dấu hiệu giải bài hộ."}

            if self.NUMBER_WORD_PATTERN.search(clean_response):
                reasoning_logs.append("[FAIL Lớp 2]: Lộ đáp án bằng số chữ.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Không dùng chữ để chốt đáp án (VD: mười lăm)."}

            latex_matches = self.LATEX_LEAK_PATTERN.findall(clean_response)
            if latex_matches and not ends_with_question:
                reasoning_logs.append(f"[FAIL Lớp 2]: LaTeX Leak {latex_matches[0]}.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Không viết đáp án số dạng LaTeX."}

        if self.SUBOPTIMAL_DENOMINATOR_PATTERN.search(clean_response):
            reasoning_logs.append("[FAIL Lớp 2]: Chấp nhận mẫu số 48 chưa tối ưu.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Mẫu chung 48 chưa tối ưu. Gợi ý học sinh tìm BCNN 24."}

        reasoning_logs.append("[PASS Lớp 2]: Không phát hiện lộ đáp án.")

        # =====================================================================
        # LỚP 3: KIỂM TRA THÁI ĐỘ
        # =====================================================================
        blacklist_match = self._blacklist_pattern.search(clean_response)
        if blacklist_match:
            reasoning_logs.append(f"[FAIL Lớp 3]: Từ ngữ tiêu cực '{blacklist_match.group(0)}'.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Sử dụng từ ngữ chê bai."}

        reasoning_logs.append("[PASS Lớp 3]: Thái độ sư phạm chuẩn mực.")

        # Hoàn thành
        return {
            "is_approved": True,
            "reasoning": " -> ".join(reasoning_logs),
            "feedback": "Bản nháp phản hồi đạt chuẩn.",
        }
