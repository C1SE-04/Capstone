from typing import Optional, Dict, List
import os
import re
import json
import unicodedata
import google.generativeai as genai
from schemas import ProblemTitleResult

# =====================================================================
# 1. TẬN DỤNG GRADE_CURRICULUM.JSON CHO TOÀN BỘ HỆ THỐNG
# =====================================================================
def _load_curriculum_catalog() -> Dict[str, List[str]]:
    """Đọc dữ liệu chuẩn từ grade_curriculum.json một lần khi khởi động module."""
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(cur_dir, "grade_curriculum.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Cảnh báo] Không thể đọc grade_curriculum.json: {e}")
        return {}

_CURRICULUM_DATA = _load_curriculum_catalog()


def _strip_accents(text: str) -> str:
    """Chuyển chuỗi tiếng Việt có dấu thành không dấu chữ thường để so khớp siêu tốc."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', text)
    no_accent = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return no_accent.replace("đ", "d").replace("Đ", "D").lower().strip()


# Bảng chuẩn hóa chủ đề tiếng Việt có dấu từ grade_curriculum.json
_TOPIC_CANONICAL_MAP = {
    "toan co loi van": "Toán có lời văn",
    "toan chuyen dong deu": "Chuyển động đều",
    "chuyen dong deu": "Chuyển động đều",
    "tinh chu vi va dien tich": "Hình học",
    "hinh phang": "Hình học",
    "hinh khoi": "Hình học",
    "hinh hoc truc quan": "Hình học",
    "goc va don vi do goc": "Hình học",
    "goc o vi tri dac biet": "Hình học",
    "mo dau ve duong tron": "Hình học",
    "hinh hop chu nhat, hinh lap phuong": "Hình học",
    "hinh lang tru dung tam giac": "Hình học",
    "hinh lang tru dung tu giac": "Hình học",
    "truong hop bang nhau thu nhat cua tam giac": "Hình học",
    "truong hop bang nhau thu hai cua tam giac": "Hình học",
    "truong hop bang nhau thu ba cua tam giac": "Hình học",
    "phan so": "Phân số",
    "tinh chat co ban cua phan so": "Phân số",
    "so thap phan": "Số thập phân",
    "ti so phan tram": "Tỉ số phần trăm",
    "so tu nhien": "Số tự nhiên",
    "dau hieu chia het": "Số tự nhiên",
    "bieu thuc chua chu": "Đại số",
    "hang dang thuc": "Đại số",
    "thong ke": "Thống kê",
    "xac suat": "Xác suất",
    "xac suat thuc nghiem": "Xác suất",
    "dai luong khoi luong": "Đại lượng và Đo lường",
    "dai luong thoi gian": "Đại lượng và Đo lường",
    "don vi do thoi gian": "Đại lượng và Đo lường",
    "dai luong dien tich": "Đại lượng và Đo lường",
    "don vi do dien tich": "Đại lượng và Đo lường",
    "don vi do the tich": "Đại lượng và Đo lường",
}


def _make_title_result(clean_text: str, grade: int, topic: str, subtopic: str) -> ProblemTitleResult:
    """Đóng gói ProblemTitleResult theo đúng định dạng chuẩn."""
    g = max(4, min(9, grade))
    title = f"[Lớp {g}] {topic} – {subtopic}"
    short_summary = (clean_text[:60] + "...") if len(clean_text) > 60 else (clean_text or subtopic)
    return ProblemTitleResult(
        friendly_parent_title=title,
        grade=g,
        topic=topic,
        subtopic_type=subtopic,
        short_summary=short_summary,
        is_fallback=True,
    )


# =====================================================================
# 2. THUẬT TOÁN FALLBACK TỰ ĐỘNG KHỚP VỚI GRADE_CURRICULUM.JSON
# =====================================================================
def _heuristic_title_fallback(problem_text: str, grade: Optional[int] = None) -> ProblemTitleResult:
    """
    Thuật toán Fallback nhận diện chuyên đề & dạng toán chuẩn sư phạm:
    - Nhận diện nhanh các dạng bài toán kinh điển của SGK Tiểu học & THCS.
    - Quét kho chuyên đề từ grade_curriculum.json để gán khối lớp và chủ đề phù hợp.
    - Đảm bảo đầu ra có dấu tiếng Việt chuẩn và tuân thủ quy tắc: [Lớp X] [Chủ đề] – [Dạng toán].
    """
    clean_text = (problem_text or "").strip()
    lower = clean_text.lower()
    norm_problem = _strip_accents(clean_text)

    # 1. Phát hiện nhanh các dạng toán kinh điển bằng từ khóa đặc trưng sư phạm
    if any(k in lower for k in ["vận tốc", "quãng đường", "km/h", "ngược chiều", "cùng chiều", "khởi hành"]):
        g = grade or 5
        topic = "Chuyển động đều"
        subtopic = "Bài toán hai chuyển động" if ("ngược chiều" in lower or "cùng chiều" in lower) else "Tính vận tốc quãng đường thời gian"
        return _make_title_result(clean_text, g, topic, subtopic)

    if any(k in lower for k in ["tổng và hiệu", "tổng là", "hiệu là"]):
        g = grade or 4
        topic = "Toán có lời văn"
        subtopic = "Tìm hai số khi biết tổng và hiệu"
        return _make_title_result(clean_text, g, topic, subtopic)

    if any(k in lower for k in ["tổng và tỉ", "hiệu và tỉ"]):
        g = grade or 4
        topic = "Toán có lời văn"
        subtopic = "Tìm hai số khi biết tổng và tỉ số" if "tổng" in lower else "Tìm hai số khi biết hiệu và tỉ số"
        return _make_title_result(clean_text, g, topic, subtopic)

    if any(k in lower for k in ["diện tích", "chu vi", "hình chữ nhật", "hình vuông", "hình tam giác", "hình thang", "hình thoi", "hình tròn"]):
        g = grade or 4
        topic = "Hình học"
        if "hình chữ nhật" in lower:
            subtopic = "Chu vi và diện tích hình chữ nhật" if ("diện tích" in lower or "chu vi" in lower) else "Hình chữ nhật"
        elif "hình vuông" in lower:
            subtopic = "Chu vi và diện tích hình vuông" if ("diện tích" in lower or "chu vi" in lower) else "Hình vuông"
        elif "hình tam giác" in lower:
            subtopic = "Diện tích hình tam giác"
        elif "hình thang" in lower:
            subtopic = "Diện tích hình thang"
        elif "hình tròn" in lower:
            subtopic = "Chu vi và diện tích hình tròn"
        else:
            subtopic = "Tính chu vi và diện tích"
        return _make_title_result(clean_text, g, topic, subtopic)

    if any(k in lower for k in ["phương trình bậc hai", "hệ phương trình", "bất phương trình", "căn bậc hai", "x^2"]):
        g = grade or 9
        topic = "Đại số"
        if "phương trình bậc hai" in lower or "x^2" in lower:
            subtopic = "Phương trình bậc hai một ẩn"
        elif "hệ phương trình" in lower:
            subtopic = "Giải hệ phương trình bậc nhất hai ẩn"
        elif "bất phương trình" in lower:
            subtopic = "Bất phương trình bậc nhất"
        else:
            subtopic = "Giải phương trình"
        return _make_title_result(clean_text, g, topic, subtopic)

    if any(k in lower for k in ["tỉ số phần trăm", "%", "lãi suất"]):
        g = grade or 5
        topic = "Tỉ số phần trăm"
        subtopic = "Giải bài toán về tỉ số phần trăm"
        return _make_title_result(clean_text, g, topic, subtopic)

    if any(k in lower for k in ["phân số", "quy đồng", "tử số", "mẫu số"]):
        g = grade or 4
        topic = "Phân số"
        subtopic = "Tìm phân số của một số" if "phần" in lower else "Các phép tính với phân số"
        return _make_title_result(clean_text, g, topic, subtopic)

    # 2. Quét kho chuyên đề từ grade_curriculum.json nếu chưa khớp các nhóm trên
    problem_words = set(re.findall(r"\b\w+\b", norm_problem))
    best_grade = grade or 5
    best_topic = "Toán trọng tâm"
    best_subtopic = "Luyện tập bài toán"
    max_score = 0

    grades_to_scan = [str(grade)] if (grade and str(grade) in _CURRICULUM_DATA) else list(_CURRICULUM_DATA.keys())

    for g_str in grades_to_scan:
        try:
            g_int = int(g_str)
        except ValueError:
            continue
        topics = _CURRICULUM_DATA.get(g_str, [])
        for item in topics:
            norm_item = _strip_accents(item)
            item_words = set(re.findall(r"\b\w+\b", norm_item))
            
            overlap = problem_words.intersection(item_words)
            meaningful_overlap = [w for w in overlap if len(w) > 2 and w not in ["bai", "toan", "cac", "mot", "hai", "khi", "biet"]]
            score = len(meaningful_overlap)

            if grade and g_int == grade:
                score += 1

            if score > max_score:
                max_score = score
                best_grade = g_int
                
                # Bóc tách chủ đề và dạng toán theo cấu trúc dấu ':' trong grade_curriculum.json
                if ":" in item:
                    parts = item.split(":", 1)
                    raw_p0 = parts[0].strip().lower()
                    best_topic = _TOPIC_CANONICAL_MAP.get(raw_p0, parts[0].strip().capitalize())
                    best_subtopic = parts[1].strip().capitalize()
                else:
                    norm_item_lower = norm_item.lower()
                    if any(k in norm_item_lower for k in ["phuong trinh", "he phuong trinh", "bat phuong trinh", "can bac"]):
                        best_topic = "Đại số"
                    elif any(k in norm_item_lower for k in ["hinh", "tam giac", "duong tron", "goc"]):
                        best_topic = "Hình học"
                    else:
                        best_topic = "Toán trọng tâm"
                    best_subtopic = item.strip().capitalize()

    # 3. Trích xuất câu hỏi hành động nếu không khớp chuyên đề nào
    if max_score == 0:
        action_match = re.search(r"\b(tính|tìm|giải|chứng minh)\s+([^.?!,;\n]{4,35})", clean_text, re.IGNORECASE)
        if action_match:
            verb = action_match.group(1).capitalize()
            target = action_match.group(2).strip()
            best_topic = "Toán tư duy"
            best_subtopic = f"{verb} {target}"
            best_grade = grade or 5
        else:
            best_topic = "Toán tổng hợp"
            best_subtopic = "Luyện tập bài toán"
            best_grade = grade or 5

    return _make_title_result(clean_text, best_grade, best_topic, best_subtopic)


# =====================================================================
# 3. HÀM CHÍNH GỌI GEMINI KÈM NGỮ CẢNH GRADE_CURRICULUM
# =====================================================================
def generate_friendly_problem_title(
    problem_text: str,
    grade: Optional[int] = None,
    api_key: Optional[str] = None
) -> ProblemTitleResult:
    """
    Gọi Gemini API để tự động sinh tên bài toán mặc định (friendly_parent_title)
    theo cấu trúc chuẩn sư phạm: [Lớp X] [Chủ đề] – [Tên dạng toán].
    Nạp sẵn danh mục chuyên đề từ grade_curriculum.json vào ngữ cảnh để AI bám sát SGK.
    Nếu có lỗi hoặc chưa cấu hình API key, tự động dùng Heuristic Fallback an toàn.
    """
    if not problem_text or not problem_text.strip():
        return _heuristic_title_fallback("Bài toán tổng hợp", grade=grade)

    clean_problem = problem_text.strip()
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        return _heuristic_title_fallback(clean_problem, grade=grade)

    # Lấy danh mục chuyên đề từ grade_curriculum.json để làm context tham chiếu cho Gemini
    curriculum_hint = ""
    target_grade_str = str(grade) if (grade and str(grade) in _CURRICULUM_DATA) else "5"
    if target_grade_str in _CURRICULUM_DATA:
        sample_topics = _CURRICULUM_DATA[target_grade_str][:15]
        curriculum_hint = f"Các chuyên đề SGK Lớp {target_grade_str} tham chiếu:\n" + "\n".join([f"- {t}" for t in sample_topics])

    prompt = f"""
Hãy phân tích đề bài toán dưới đây và đặt tên bài toán chuẩn sư phạm theo cấu trúc:
[Lớp X] [Chủ đề] – [Tên dạng toán cụ thể]

─── ĐỀ BÀI TOÁN ───
{clean_problem}

─── THAM KHẢO CHUYÊN ĐỀ CHUẨN SGK (NẾU PHÙ HỢP) ───
{curriculum_hint}

─── YÊU CẦU ĐỊNH DẠNG ĐẦU RA JSON THUẦN TÚY ───
Chỉ trả về JSON thuần túy theo cấu trúc:
{{
  "friendly_parent_title": "[Lớp X] [Chủ đề] – [Tên dạng toán]",
  "grade": <số nguyên từ 4 đến 9>,
  "topic": "<Tên chủ đề lớn>",
  "subtopic_type": "<Tên dạng toán cụ thể>",
  "short_summary": "<Tóm tắt đề bài ngắn gọn dưới 15 từ>"
}}
"""

    try:
        genai.configure(api_key=key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
        )

        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Làm sạch markdown nếu có
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        resolved_grade = int(data.get("grade", grade or 5))
        resolved_grade = max(4, min(9, resolved_grade))
        topic = data.get("topic", "Toán trọng tâm").strip()
        subtopic = data.get("subtopic_type", "Luyện tập bài toán").strip()

        # Đảm bảo format chuẩn bắt buộc: [Lớp X] [Chủ đề] – [Dạng toán]
        title = data.get("friendly_parent_title", "").strip()
        if not re.match(r"^\[Lớp \d\] .+ – .+$", title):
            title = f"[Lớp {resolved_grade}] {topic} – {subtopic}"

        return ProblemTitleResult(
            friendly_parent_title=title,
            grade=resolved_grade,
            topic=topic,
            subtopic_type=subtopic,
            short_summary=data.get("short_summary"),
            is_fallback=False
        )

    except Exception as e:
        print(f"[Cảnh báo Problem Title Generator] Lỗi khi gọi Gemini: {e}")
        return _heuristic_title_fallback(clean_problem, grade=grade)