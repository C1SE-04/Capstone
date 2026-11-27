import re
from fractions import Fraction
from typing import Optional, TypedDict

class ReviewResult(TypedDict):
    """Cấu trúc dữ liệu kết quả kiểm duyệt."""
    is_approved: bool
    reasoning: str
    feedback: str

class LocalReviewerAgent:
    MAX_WORD_COUNT: int = 195
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

    # Lớp 2: Lộ đáp án qua mã LaTeX (VD: $x = 5$, $x = \frac{5}{2}$)
    LATEX_LEAK_PATTERN: re.Pattern = re.compile(
        r"\$\$?[^$]*=\s*-?(?:\d+(?:\.\d+)?(?:/\d+)?|\\(?:d|t)?frac(?:\{[^{}]+\}\{[^{}]+\}|\s*\d\s*\d))\s*\$\$?",
        re.UNICODE,
    )

    # Lớp 2: Kết thúc bằng "= <số>" hoặc "= \frac{a}{b}"
    _EQUALS_END_PATTERN: re.Pattern = re.compile(
        r"=\s*-?(?:\d+(?:\.\d+)?(?:/\d+)?|\\(?:d|t)?frac(?:\{[^{}]+\}\{[^{}]+\}|\s*\d\s*\d))\s*(?=[.!]|$)",
        re.UNICODE,
    )

    # Nhận diện vế trái có biến phức tạp (đề bài / bước biến đổi chứa ẩn) vs biến đơn (x = 4)
    _EQUATION_WITH_VAR_LHS_PATTERN: re.Pattern = re.compile(
        r"(?:\d+\s*\*?\s*[a-zA-Z]|[a-zA-Z]\s*[\+\-\*/^×:÷]|[+\-]\s*[a-zA-Z]|\\(?:d|t)?frac\{[^}]*[a-zA-Z][^}]*\})",
        re.UNICODE,
    )
    _SINGLE_VAR_EQUALS_PATTERN: re.Pattern = re.compile(
        r"(?:^|[\s\$:,;(\[])([a-zA-Z])\s*=\s*-?(?:\d+(?:\.\d+)?(?:/\d+)?|\\(?:d|t)?frac(?:\{[^{}]+\}\{[^{}]+\}|\s*\d\s*\d))\s*(?=[.!$\s,;?]|$)",
        re.UNICODE,
    )

    # Lớp 2: Ngoại lệ ví dụ minh họa
    _EXAMPLE_PREFIX_PATTERN: re.Pattern = re.compile(
        r"(ví dụ|vd|chẳng hạn)\s*[:\.]?\s*$",
        re.IGNORECASE | re.UNICODE,
    )
    _EXAMPLE_START_PATTERN: re.Pattern = re.compile(
        r"(?<!\w)(ví dụ|vd|chẳng hạn|bài mẫu|bài toán mẫu|tương tự|minh họa)(?!\w)",
        re.IGNORECASE | re.UNICODE,
    )
    _RETURN_TO_ORIGINAL_PATTERN: re.Pattern = re.compile(
        r"(?<!\w)(bài toán của mình|bài của em|áp dụng cách làm này|áp dụng cách trình bày này|quay lại bài)(?!\w)",
        re.IGNORECASE | re.UNICODE,
    )

    # Lớp 2: Chấp nhận mẫu số chung chưa tối ưu
    SUBOPTIMAL_DENOMINATOR_PATTERN: re.Pattern = re.compile(
        r"(với|dùng|lấy|chọn)\s+mẫu\s+(số\s+)?(chung\s+)?(là\s+)?48|"
        r"48\s+là\s+mẫu\s+(số\s+)?chung\s+(chính xác|hoàn toàn đúng|đúng rồi)|"
        r"(hoàn toàn đúng.*?48.*?mẫu\s+(số\s+)?chung)|"
        r"(mẫu\s+(?:số\s+)?chung.*?(?:đúng rồi|hoàn toàn đúng).*?(?:tuy nhiên|nhưng).*?nhỏ nhất)",
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

    @staticmethod
    def _normalize_latex_numbers(text: str) -> str:
        """Chuẩn hóa ký hiệu LaTeX (\frac{a}{b}, \dfrac, \tfrac, \frac52) để đối chiếu Fraction chính xác."""
        if not text:
            return ""
        s = text
        s = re.sub(r"\\[,;!]", " ", s)
        s = re.sub(r"\\(?:left|right)\b", "", s)
        s = re.sub(r"\\(?:d|t)?frac\s*\{\s*([^{}]+?)\s*\}\s*\{\s*([^{}]+?)\s*\}", r"\1/\2", s)
        s = re.sub(r"\\(?:d|t)?frac\s*([0-9])\s*([0-9])", r"\1/\2", s)
        s = s.replace("\\times", "*").replace("\\cdot", "*").replace("\\div", "/")
        s = s.replace("$", " ")
        s = re.sub(r"\s*/\s*", "/", s)
        s = re.sub(r"(^|[=(\[:,;\s])-\s+(?=\d)", r"\1-", s)
        s = re.sub(r"(?<=\d),(?=\d)", ".", s)
        return re.sub(r"\s+", " ", s).strip().lower()

    @staticmethod
    def _normalize_math_tokens(text: str) -> str:
        """Alias giữ tương thích cho _normalize_latex_numbers."""
        return LocalReviewerAgent._normalize_latex_numbers(text)

    @staticmethod
    def _parse_fraction_safe(num_str: str):
        try:
            if not num_str:
                return None
            return Fraction(num_str.strip())
        except Exception:
            return None

    @staticmethod
    def _strip_square_templates(text: str) -> str:
        """Thay thế tạm các công thức $...$ / $$...$$ chứa khung điền khuyết \square / □ để tránh reject oan."""
        if not text:
            return ""
        def _repl(m: re.Match) -> str:
            seg = m.group(0)
            if "\\square" in seg or "□" in seg:
                return "[KHUNG]"
            return seg
        return re.sub(r"\$\$[\s\S]*?\$\$|\$[^$]*?\$", _repl, text)

    def _is_in_example_block(self, text: str, pos: int) -> bool:
        """Kiểm tra vị trí pos có đang nằm trong khối ví dụ tương tự chưa quay lại bài gốc hay không."""
        if not text or pos <= 0:
            return False
        prefix = text[:pos]
        starts = list(self._EXAMPLE_START_PATTERN.finditer(prefix))
        if not starts:
            return False
        last_start = starts[-1].start()
        return not bool(self._RETURN_TO_ORIGINAL_PATTERN.search(prefix[last_start:]))

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
        cleaned_for_check = self._strip_square_templates(response)
        matches = list(self._EQUALS_END_PATTERN.finditer(cleaned_for_check))
        if not matches:
            return False

        ends_with_question = self._response_ends_with_question(response)

        for m in matches:
            start, end = m.start(), m.end()
            prefix_window = cleaned_for_check[max(0, start - 40):start]
            if self._EXAMPLE_PREFIX_PATTERN.search(prefix_window) or self._is_in_example_block(cleaned_for_check, start):
                continue

            stripped_after = cleaned_for_check[end:].lstrip()
            if stripped_after.startswith("?"):
                continue

            clause_match = re.search(r"[^.!?\n;:]*$", cleaned_for_check[:start])
            lhs_clause = clause_match.group(0) if clause_match else ""
            full_clause = lhs_clause + m.group(0)

            if "\\square" in full_clause or "□" in full_clause or "[KHUNG]" in full_clause:
                continue

            # Chặn lộ nghiệm biến đơn (VD: x = 4., x = \frac{5}{2}.) trừ khi nằm trong ví dụ
            if self._SINGLE_VAR_EQUALS_PATTERN.search(full_clause):
                return True

            # Nếu kết thúc có câu hỏi gợi mở, không reject oan nhắc lại đề bài / bước biến đổi còn ẩn ở vế trái
            if ends_with_question and self._EQUATION_WITH_VAR_LHS_PATTERN.search(lhs_clause):
                near_prefix = cleaned_for_check[max(0, start - 35):start].lower()
                if not any(kw in near_prefix for kw in ("đáp án", "kết quả", "nghiệm là", "tìm được")):
                    continue

            return True
        return False

    def review(
        self,
        student_question: str,
        expected_answer: str,
        scaffolding_response: str,
        has_comprehension: bool = False,
        grade_level: Optional[int] = None,
        history_text: str = "",
        require_final_completion: bool = False,
        require_square_template: bool = False,
        is_wrong_turn: bool = False,
    ) -> ReviewResult:
        
        clean_question = self._normalize_text(student_question)
        clean_expected = self._normalize_text(expected_answer)
        clean_response = self._normalize_text(scaffolding_response)
        
        response_lower = clean_response.lower()
        expected_lower = clean_expected.lower().strip()
        question_lower = clean_question.lower()
        question_math_norm = self._normalize_math_tokens(clean_question)
        expected_math_norm = self._normalize_math_tokens(clean_expected)

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
        ends_with_question = self._response_ends_with_question(clean_response)
        is_final_sample = has_comprehension or ("mẫu trình bày" in response_lower and not ends_with_question)
        hint_m_early = re.search(
            r"(?:lấy\s+[^\n.?!]{1,45}\s+(?:chia cho|nhân với)|đổi\s+dấu\s+thành\s*[+\-]?\s*\d+)",
            clean_response,
            re.IGNORECASE,
        )
        if not is_final_sample and hint_m_early:
            reasoning_logs.append(f"[FAIL Lớp 3]: Lộ phép tính/quy tắc '{hint_m_early.group(0)}' trước khi học sinh tự nghĩ.")
            return {
                "is_approved": False,
                "reasoning": " -> ".join(reasoning_logs),
                "feedback": (
                    f"CẤM viết cụm '{hint_m_early.group(0)}' (chứa mẫu bị cấm 'lấy ... chia cho/nhân với' hoặc 'đổi dấu thành ...'). "
                    "Hãy XÓA HẲN cụm từ đó khỏi câu trả lời! Nếu đang tìm x ở a*x = b, viết thẳng: 'Để tìm giá trị ở ô trống, em hãy nghĩ xem cần phép tính gì giữa hai số này: $$x = b \\ \\square \\ a$$'; "
                    "nếu là phần trăm, viết: 'Em hãy đổi phần trăm sang phân số hoặc điền biểu thức: $$\\frac{...}{...} \\times 100\\% = \\square\\%$$'; "
                    "nếu là phép chia đa thức/phân số/số học, viết thẳng phân thức hoặc dấu chia: ví dụ $$\\frac{6x^4}{3x^2} = \\square$$ hoặc $$A : B = \\square$$."
                ),
            }

        dbl_cnt = len(re.findall(r"(?<!\\)\$\$", clean_response))
        wo_dbl = re.sub(r"(?<!\\)\$\$", "", clean_response)
        sgl_cnt = len(re.findall(r"(?<!\\)\$", wo_dbl))
        if dbl_cnt % 2 != 0 or sgl_cnt % 2 != 0:
            reasoning_logs.append("[FAIL Lớp 1]: Dấu $ hoặc $$ trong công thức LaTeX chưa đóng đủ cặp.")
            return {
                "is_approved": False,
                "reasoning": " -> ".join(reasoning_logs),
                "feedback": "Công thức LaTeX bị thiếu dấu $ hoặc $$ đóng ngoặc. Hãy kiểm tra và đóng đủ cặp $...$ / $$...$$ cho mọi công thức.",
            }

        words = clean_response.split()
        if len(words) > self.MAX_WORD_COUNT:
            reasoning_logs.append(f"[FAIL Lớp 1]: Vượt giới hạn ({len(words)}/{self.MAX_WORD_COUNT} từ).")
            return {
                "is_approved": False,
                "reasoning": " -> ".join(reasoning_logs),
                "feedback": f"Câu trả lời quá dài, hãy rút gọn dưới {self.MAX_WORD_COUNT} từ.",
            }

        # Loại trừ ngữ cảnh phủ định/câu hỏi khi kiểm tra khen ("chưa chính xác", "kết quả chính xác là bao nhiêu")
        resp_for_praise_chk = re.sub(
            r"(?:chưa|không|chưa phải là(?:\s+đáp án)?|kết quả)\s+chính xác",
            "",
            response_lower,
        )
        is_praise_correct = any(p in resp_for_praise_chk for p in (
            "chính xác", "hoàn toàn đúng", "đúng rồi", "xuất sắc", "tuyệt vời", 
            "chuẩn rồi", "rất tốt", "rất giỏi", "khen ngợi", "chuẩn xác", "làm tốt lắm"
        ))
        has_square_template = ("\\square" in clean_response or "□" in clean_response)
        is_requesting_problem = any(p in response_lower for p in ("gửi đề", "gõ lại đề", "đọc lại đề", "nhập đề", "chưa thấy đề"))

        if not ends_with_question:
            if is_praise_correct or has_comprehension:
                reasoning_logs.append("[PASS Lớp 1]: Phản hồi khen ngợi / hoàn thành bài toán (miễn dấu '?').")
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
        has_number_in_question = bool(re.search(r"\d+", clean_question))
        has_choice_in_question = bool(re.search(r"\b[a-dA-D]\b", clean_question))
        student_answered = has_number_in_question or has_choice_in_question

        # LỚP 2.0: KIỂM TRA KHEN SAI (False Praise Check)
        # Chỉ chặn khi AI khen khẳng định toàn bộ bài ("hoàn toàn đúng", "chính xác" không có lời nhắc bước tiếp/ô trống)
        numbers_in_student_q = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", question_math_norm)
        student_fracs = {f for s in numbers_in_student_q if (f := self._parse_fraction_safe(s)) is not None}
        expected_frac = self._parse_fraction_safe(expected_math_norm) if expected_math_norm else None
        if expected_frac is None and expected_math_norm:
            exp_nums = re.findall(r"-?\d+(?:\.\d+)?(?:/\d+)?", expected_math_norm)
            if exp_nums:
                expected_frac = self._parse_fraction_safe(exp_nums[-1])

        is_numeric_expected = bool(re.fullmatch(r"-?\d+(?:\.\d+)?(?:/\d+)?", expected_math_norm)) if expected_math_norm else False
        has_correction_or_next_step = has_square_template or any(
            m in response_lower for m in ("tuy nhiên", "nhưng", "kiểm tra lại", "chưa đúng", "chưa chính xác", "bước tiếp")
        )
        strong_false_praise = re.search(
            r"\b(?:hoàn toàn đúng|hoàn toàn chính xác|chuẩn rồi|xuất sắc|đã chính xác(?:\s+rồi)?|rất chính xác(?:\s+rồi)?|là\s+(?:hoàn\s+toàn\s+)?chính\s+xác(?:\s+rồi)?|đúng\s+rồi)\b",
            resp_for_praise_chk,
            re.IGNORECASE,
        )
        has_explicit_err_marker = any(
            m in response_lower for m in ("kiểm tra lại", "xem lại", "chưa đúng", "chưa chính xác", "chưa đúng lắm", "chú ý lại")
        ) or (is_wrong_turn and any(m in response_lower for m in ("tuy nhiên", "nhưng")))

        if not has_comprehension and strong_false_praise and has_explicit_err_marker:
            reasoning_logs.append("[FAIL Lớp 2]: False Praise kèm câu nhắc lỗi.")
            return {
                "is_approved": False,
                "reasoning": " -> ".join(reasoning_logs),
                "feedback": (
                    "Trong câu nhắc sửa lỗi ('kiểm tra lại'/'chưa đúng'), CẤM khen 'hoàn toàn đúng', 'chính xác rồi', 'đúng rồi', 'xuất sắc'. "
                    "Hãy đổi thành 'Em đã thực hiện đúng phần/ý ..., tuy nhiên...'"
                ),
            }
        is_matched = False
        if expected_lower and is_numeric_expected and numbers_in_student_q:
            is_matched = (
                (expected_math_norm in numbers_in_student_q)
                or (expected_lower in numbers_in_student_q)
                or (expected_frac is not None and expected_frac in student_fracs)
            )
            if not is_matched and has_comprehension and not require_final_completion:
                reasoning_logs.append(f"[FAIL Lớp 2]: Chốt hoàn thành sớm khi học sinh chưa ra '{expected_lower}'.")
                return {
                    "is_approved": False,
                    "reasoning": " -> ".join(reasoning_logs),
                    "feedback": (
                        f"Học sinh mới làm bước trung gian và CHƯA tìm ra đáp án cuối ('{expected_lower}'). "
                        "TUYỆT ĐỐI KHÔNG gắn [COMPREHENSION_CHECK] hay viết Mẫu trình bày hoàn chỉnh; hãy đặt câu hỏi gợi mở bước kế tiếp kèm khung \\square."
                    ),
                }
            if not is_matched and (is_wrong_turn or has_explicit_err_marker or (is_praise_correct and not has_correction_or_next_step)) and (
                (is_praise_correct and not has_correction_or_next_step) or strong_false_praise
            ):
                reasoning_logs.append(f"[FAIL Lớp 2]: False Praise! Học sinh nộp {numbers_in_student_q} không khớp expected '{expected_lower}'.")
                return {
                    "is_approved": False,
                    "reasoning": " -> ".join(reasoning_logs),
                    "feedback": (
                        f"Học sinh chưa ra đáp án cuối đúng ('{expected_lower}'). CẤM viết 'hoàn toàn đúng', 'chính xác rồi', 'đúng rồi', 'xuất sắc'. "
                        "Hãy sửa thành 'Em đã thực hiện đúng phần/bước ..., tuy nhiên...'"
                    ),
                }

        student_has_answer = (
            (bool(expected_lower) and (
                expected_lower in question_lower
                or (bool(expected_math_norm) and expected_math_norm in question_math_norm)
                or (expected_frac is not None and expected_frac in student_fracs)
            ))
            or (is_praise_correct and student_answered)
            or has_comprehension
        )

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

            stripped_for_latex = self._strip_square_templates(clean_response)
            for lm in self.LATEX_LEAK_PATTERN.finditer(stripped_for_latex):
                if self._is_in_example_block(stripped_for_latex, lm.start()):
                    continue
                inner_expr = lm.group(0).strip("$").strip()
                is_single_var_sol = bool(self._SINGLE_VAR_EQUALS_PATTERN.match(inner_expr))
                if not ends_with_question or is_single_var_sol:
                    reasoning_logs.append(f"[FAIL Lớp 2]: LaTeX Leak {lm.group(0)}.")
                    return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Không viết đáp án số dạng LaTeX."}
        else:
            reasoning_logs.append("[PASS Lớp 2]: Học sinh đã trả lời hoặc bài toán đã hoàn thành, cho phép AI xác nhận/khen ngợi.")

        if self.SUBOPTIMAL_DENOMINATOR_PATTERN.search(clean_response):
            reasoning_logs.append("[FAIL Lớp 2]: Chấp nhận mẫu số 48 chưa tối ưu.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Mẫu chung 48 chưa tối ưu. Gợi ý học sinh tìm BCNN 24."}

        reasoning_logs.append("[PASS Lớp 2]: Không phát hiện lộ đáp án.")

        # =====================================================================
        # LỚP 3: KIỂM TRA THÁI ĐỘ & XƯNG HÔ THẦY GIÁO & PHÂN TẦNG LỚP
        # =====================================================================
        if re.match(r"^\s*(dạ\b|vâng ạ\b|dạ thưa\b|thưa em\b)", clean_response, re.IGNORECASE):
            reasoning_logs.append("[FAIL Lớp 3]: Thầy giáo không được mở đầu bằng 'Dạ'/'Vâng ạ'/'Thưa em'.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Bạn là THẦY GIÁO, tuyệt đối không mở đầu bằng 'Dạ', 'Vâng ạ' hay 'Thưa em'. Hãy xưng 'Chào em' hoặc bắt đầu bằng 'Thầy...'."}

        if grade_level in (4, 5):
            if re.search(r"\bphương trình\b", clean_response, re.IGNORECASE):
                reasoning_logs.append("[FAIL Lớp 3]: Lớp 4-5 dùng từ 'phương trình'.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Học sinh lớp 4-5 chưa học khái niệm 'phương trình'. Hãy thay bằng 'bài toán tìm x'."}
            if len(re.findall(r"\\square|□", clean_response)) > 2:
                reasoning_logs.append("[FAIL Lớp 3]: Lớp 4-5 quá 2 ô trống \\square.")
                return {
                    "is_approved": False,
                    "reasoning": " -> ".join(reasoning_logs),
                    "feedback": (
                        "Lớp 4-5 chỉ được dùng TỐI ĐA 1-2 ô trống \\square mỗi lượt. "
                        "Nếu quy đồng nhiều phân số, chỉ chừa 1 ô \\square cho tử số đầu tiên (VD: $$\\frac{5}{6}+\\frac{3}{8}-\\frac{1}{4}=\\frac{\\square}{24}+\\frac{9}{24}-\\frac{6}{24}$$) hoặc hỏi mẫu chung: $$\\text{Mẫu chung}=\\square$$. KHÔNG viết 3 ô \\square!"
                    ),
                }

        if require_square_template and not has_comprehension and not is_requesting_problem and "mẫu trình bày" not in response_lower:
            math_blks = re.findall(r"\$\$[\s\S]*?\$\$|\$[^$\n]+?\$", clean_response)
            if not any(("\\square" in mb or "□" in mb) for mb in math_blks):
                reasoning_logs.append("[FAIL Lớp 3]: Thiếu khung \\square trong $...$/$$...$$ khi hướng dẫn bước.")
                return {
                    "is_approved": False,
                    "reasoning": " -> ".join(reasoning_logs),
                    "feedback": "Đang hướng dẫn từng bước/sửa lỗi: BẮT BUỘC phải kèm 1 khung công thức đặt trong $$...$$ có ít nhất 1 ô trống \\square để học sinh tự điền.",
                }

        if grade_level in (4, 5, 6, 7) and ("⇔" in clean_response or "\\Leftrightarrow" in clean_response):
            reasoning_logs.append("[FAIL Lớp 3]: Lớp 4-7 dùng dấu tương đương <=>.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Lớp 4-7 không dùng dấu ⇔ (\\Leftrightarrow), hãy viết xuống dòng thẳng dấu =."}

        # Kiểm tra LaTeX chưa đóng dấu $ / $$
        dbl_cnt = len(re.findall(r"(?<!\\)\$\$", clean_response))
        wo_dbl = re.sub(r"(?<!\\)\$\$", "", clean_response)
        sgl_cnt = len(re.findall(r"(?<!\\)\$", wo_dbl))
        if dbl_cnt % 2 != 0 or sgl_cnt % 2 != 0:
            reasoning_logs.append("[FAIL Lớp 3]: Dấu $ hoặc $$ LaTeX chưa đóng đủ cặp.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Công thức toán bị thiếu dấu đóng $ hoặc $$. Hãy kiểm tra đóng đủ cặp $...$ / $$...$$."}

        # Chống lặp lại câu hỏi thăm dò tiến độ trường học khi lịch sử đã hỏi rồi
        if history_text and any(k in history_text.lower() for k in ("đang học đến bài nào rồi", "đã học qua chưa", "thầy cô đã dạy đến")):
            if any(k in response_lower for k in ("đang học đến bài nào rồi", "đã học qua chưa")):
                reasoning_logs.append("[FAIL Lớp 3]: Lặp lại câu hỏi thăm dò tiến độ trường lớp.")
                return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Đã hỏi tiến độ trường lớp ở lượt trước rồi. Tuyệt đối không hỏi lại; hãy hướng dẫn ngay bước tiếp theo kèm \\square."}

        # Khi Orchestrator đã xác nhận học sinh tính đúng đáp án cuối, không cho bắt tính lại
        if require_final_completion and (has_square_template or any(k in response_lower for k in ("kiểm tra lại", "tính lại", "chưa chính xác"))):
            reasoning_logs.append("[FAIL Lớp 3]: Học sinh đã tính đúng đáp án cuối nhưng AI lại yêu cầu tính lại.")
            return {"is_approved": False, "reasoning": " -> ".join(reasoning_logs), "feedback": "Học sinh đã tính ĐÚNG đáp án cuối. Hãy xác nhận đúng, viết Mẫu trình bày hoàn chỉnh vào vở, KHÔNG đặt ô \\square hay yêu cầu tính lại, và gắn [COMPREHENSION_CHECK]."}

        # Cấm nói lộ phép tính/quy tắc biến đổi khi chưa chốt bài hoàn chỉnh
        is_final_sample = has_comprehension or ("mẫu trình bày" in response_lower and not ends_with_question)
        hint_m = re.search(
            r"(?:lấy\s+[^\n.?!]{1,45}\s+(?:chia cho|nhân với)|đổi\s+dấu\s+thành\s*[+\-]?\s*\d+)",
            clean_response,
            re.IGNORECASE,
        )
        if not is_final_sample and hint_m:
            reasoning_logs.append(f"[FAIL Lớp 3]: Lộ phép tính/quy tắc '{hint_m.group(0)}' trước khi học sinh tự nghĩ.")
            return {
                "is_approved": False,
                "reasoning": " -> ".join(reasoning_logs),
                "feedback": (
                    f"CẤM viết cụm '{hint_m.group(0)}' (chứa mẫu bị cấm 'lấy ... chia cho/nhân với' hoặc 'đổi dấu thành ...'). "
                    "Hãy XÓA HẲN cụm từ đó khỏi câu trả lời! Nếu đang tìm x ở a*x = b, viết thẳng: 'Để tìm giá trị ở ô trống, em hãy nghĩ xem cần phép tính gì giữa hai số này: $$x = b \\ \\square \\ a$$'; "
                    "nếu là phần trăm, viết: 'Em hãy đổi phần trăm sang phân số hoặc điền biểu thức: $$\\frac{...}{...} \\times 100\\% = \\square\\%$$'."
                ),
            }

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
