# =============================================================================
# SocraticKid Backend — Curriculum Crawler (Task T8.24 - US 8.4)
#
# Tự động cào mục lục chuyên đề Toán lớp 4–9 từ VietJack.
# Bộ sách: Kết Nối Tri Thức (chương trình SGK mới).
#
# Cách chạy thủ công để kiểm tra output:
#   cd d:\Document\Capstone\backend
#   python -m agents.curriculum_crawler
# =============================================================================

import json
import logging
import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ─── Cấu hình ────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 15     # Timeout mỗi request (giây)
MAX_RETRIES = 3          # Số lần retry khi request thất bại
CRAWL_DELAY = 1.5        # Nghỉ giữa các lớp để tránh rate-limit VietJack

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "vi-VN,vi;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# URL trang mục lục VietJack theo từng lớp (đã kiểm tra thực tế)
VIETJACK_URLS: dict[int, str] = {
    4: "https://vietjack.com/giao-an-toan-4/index.jsp",
    5: "https://vietjack.com/giao-an-toan-5/index.jsp",
    6: "https://vietjack.com/giao-an-toan-6/index.jsp",
    7: "https://vietjack.com/giao-an-toan-7/index.jsp",
    8: "https://vietjack.com/giao-an-toan-8/index.jsp",
    9: "https://vietjack.com/giao-an-toan-9/index.jsp",
}

# Từ khoá nhận dạng bộ sách "Kết Nối Tri Thức" (bộ sách đầu tiên ta cần lấy)
BOOK_KEYWORDS = ("kết nối tri thức", "ket noi tri thuc", "kntt")


# ─── Hàm tiện ích ────────────────────────────────────────────────────────────

def _fetch_html(url: str) -> Optional[str]:
    """
    Tải toàn bộ nội dung HTML từ URL với cơ chế thử lại (retry) tối đa 3 lần.
    Trả về chuỗi HTML (str) nếu thành công, hoặc None nếu thất bại.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.exceptions.Timeout:
            logger.warning(f"[Crawler] Quá thời gian chờ (Timeout): {url} (lần {attempt}/{MAX_RETRIES})")
        except requests.exceptions.ConnectionError:
            logger.warning(f"[Crawler] Lỗi kết nối mạng: {url} (lần {attempt}/{MAX_RETRIES})")
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[Crawler] Lỗi mã HTTP {e.response.status_code}: {url}")
            if e.response.status_code == 404:
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"[Crawler] Lỗi không xác định: {url} — {e} (lần {attempt}/{MAX_RETRIES})")

        if attempt < MAX_RETRIES:
            time.sleep(CRAWL_DELAY * attempt)

    logger.error(f"[Crawler] Thất bại hoàn toàn sau {MAX_RETRIES} lần thử: {url}")
    return None


def _is_book_heading(tag) -> bool:
    """Kiểm tra một thẻ h3 có phải là tiêu đề bộ sách chính (không có class) không."""
    if tag.name != "h3":
        return False
    classes = tag.get("class", [])
    return len(classes) == 0 or classes == []


def _is_target_book(text: str) -> bool:
    """Kiểm tra tên bộ sách có phải là Kết Nối Tri Thức không."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in BOOK_KEYWORDS)


# ─── Hàm bóc tách dữ liệu ────────────────────────────────────────────────────

def _parse_curriculum(html: str, grade: int) -> list[dict]:
    """
    Bóc tách danh sách chuyên đề/bài học từ HTML trang VietJack.
    Chỉ lấy đúng các bài thuộc bộ sách 'Kết Nối Tri Thức'.

    Cấu trúc mỗi dict trả về:
    {
        "grade": 6,
        "chapter": "Chương 1: Tập hợp các số tự nhiên",
        "topic_name": "Bài 1: Tập hợp",
        "order_index": 1,
        "source_url": "https://vietjack.com/giao-an-toan-6/bai-1-tap-hop-kntt.jsp"
    }
    """
    soup = BeautifulSoup(html, "html.parser")
    col_main = soup.find("div", class_="col-md-7")
    if not col_main:
        col_main = soup.find("div", class_="middle-col") or soup.body
        if not col_main:
            logger.warning(f"[Crawler] Lớp {grade}: Không tìm thấy vùng nội dung chính.")
            return []

    topics: list[dict] = []
    order_index = 0
    current_chapter = f"Toán {grade}"
    in_target_book = False  # Đã vào đúng bộ sách chưa
    book_count = 0           # Đếm số bộ sách đã gặp

    # Duyệt các phần tử con trực tiếp của col-md-7 theo thứ tự DOM
    for element in col_main.children:
        if not hasattr(element, "name") or element.name is None:
            continue

        # ── TẦNG 1: Nhận diện Tiêu đề Bộ sách lớn ────────────────────────────
        if _is_book_heading(element):
            book_name = element.get_text().strip()
            book_count += 1

            if book_count == 1 and _is_target_book(book_name):
                in_target_book = True
                logger.info(f"[Crawler] Lớp {grade}: Bắt đầu cào bộ sách '{book_name}'")
            elif book_count > 1 and in_target_book:
                logger.info(
                    f"[Crawler] Lớp {grade}: Gặp bộ sách mới '{book_name[:50]}' -> Dừng cào."
                )
                break
            continue

        if not in_target_book:
            continue

        # ── TẦNG 2 & 3: Bóc tách Chương và Bài học từ thẻ div.row.vj__list ────
        if element.name == "div" and "vj__list" in element.get("class", []):
            # Mỗi block có 2 cột col-md-6.
            # Trong 1 cột có thể có nhiều cặp (h3, ul) liên tiếp nhau
            # (ví dụ Lớp 4 cột 2 có cả Chủ đề 9 và Chủ đề 10).
            # Duyệt theo thứ tự tất cả thẻ h3 và ul bên trong cột:
            for col in element.find_all("div", class_="col-md-6", recursive=False):
                for item in col.find_all(["h3", "ul"]):
                    if item.name == "h3":
                        current_chapter = item.get_text().strip()
                        order_index = 0  # Reset thứ tự khi sang chương/chủ đề mới
                    elif item.name == "ul" and "list" in item.get("class", []):
                        for li in item.find_all("li"):
                            a_tag = li.find("a", href=True)
                            if not a_tag:
                                continue

                            topic_name = a_tag.get_text().strip()
                            href = a_tag.get("href", "")

                            # Bỏ qua link rỗng hoặc quá ngắn
                            if not topic_name or len(topic_name) < 3:
                                continue

                            # Chuyển relative URL thành absolute URL
                            if href.startswith("../"):
                                href = "https://vietjack.com/" + href[3:]
                            elif href.startswith("/"):
                                href = "https://vietjack.com" + href

                            order_index += 1
                            topics.append(
                                {
                                    "grade": grade,
                                    "chapter": current_chapter,
                                    "topic_name": topic_name,
                                    "order_index": order_index,
                                    "source_url": href,
                                }
                            )

    logger.info(
        f"[Crawler] Lớp {grade}: Bóc tách được {len(topics)} bài học "
        f"từ {len(set(t['chapter'] for t in topics))} chương/chủ đề."
    )
    return topics


# ─── Hàm công khai ───────────────────────────────────────────────────────────

def fetch_grade_curriculum(grade: int) -> list[dict]:
    """
    Cào và bóc tách mục lục Toán cho 1 khối lớp cụ thể từ VietJack.

    Tham số:
        grade (int): Khối lớp cần cào (chỉ chấp nhận từ 4 đến 9).

    Trả về:
        list[dict]: Danh sách các bài học của lớp đó (hoặc [] nếu có lỗi).
    """
    if grade not in VIETJACK_URLS:
        logger.error(f"[Crawler] Khối lớp {grade} không được hỗ trợ. Chỉ hỗ trợ lớp 4-9.")
        return []

    url = VIETJACK_URLS[grade]
    logger.info(f"[Crawler] Bắt đầu cào mục lục Toán lớp {grade} từ: {url}")

    html = _fetch_html(url)
    if not html:
        logger.error(f"[Crawler] Không tải được HTML lớp {grade}. Bỏ qua lớp này.")
        return []

    topics = _parse_curriculum(html, grade)

    if not topics:
        logger.warning(
            f"[Crawler] Lớp {grade}: Không bóc tách được bài học nào! "
            "Có thể VietJack đã thay đổi cấu trúc web, cần kiểm tra lại selector."
        )

    return topics


def run_crawler(grades: list[int] | None = None) -> list[dict]:
    """
    Cào toàn bộ mục lục chuyên đề Toán từ VietJack cho danh sách các khối lớp chỉ định.
    (Hàm này được Thống gọi trực tiếp từ API Backend ở Task T8.25).

    Tham số:
        grades: Danh sách khối lớp cần cào. Mặc định là [4, 5, 6, 7, 8, 9].

    Trả về:
        list[dict]: Tổng hợp tất cả bài học đã bóc tách từ các lớp cào thành công.
    """
    if grades is None:
        grades = [4, 5, 6, 7, 8, 9]

    all_topics: list[dict] = []
    failed_grades: list[int] = []
    start_time = time.time()

    logger.info(f"[Crawler] Bắt đầu tiến trình cào VietJack cho các lớp: {grades}")

    for i, grade in enumerate(grades):
        topics = fetch_grade_curriculum(grade)

        if topics:
            all_topics.extend(topics)
        else:
            failed_grades.append(grade)

        if i < len(grades) - 1:
            time.sleep(CRAWL_DELAY)

    elapsed = time.time() - start_time
    success_grades = [g for g in grades if g not in failed_grades]

    logger.info(
        f"[Crawler] Hoàn tất! "
        f"Tổng cộng: {len(all_topics)} bài học | "
        f"Thành công: {len(success_grades)} lớp {success_grades} | "
        f"Thất bại: {len(failed_grades)} lớp {failed_grades} | "
        f"Tổng thời gian: {elapsed:.1f} giây"
    )

    if failed_grades:
        logger.warning(
            f"[Crawler] Các lớp sau không cào được: {failed_grades}. "
            "Dữ liệu cũ trong Database của các lớp này sẽ được giữ nguyên."
        )

    return all_topics


# ─── Các hàm biến đổi dữ liệu (Data Transformation) ─────────────────────────

def transform_for_db_sync(
    raw_topics: list[dict],
    school_year: str = "2024-2025",
) -> list[dict]:
    """
    Biến đổi dữ liệu thô từ crawler thành cấu trúc bản ghi chuẩn để nạp vào
    bảng 'curriculum_topics' trên Neon DB (phục vụ Task T8.25 của Thống).

    Tự động chuẩn hóa:
      - Cắt bỏ tiền tố rác ở tên chương (ví dụ 'Giáo án Toán 7 Chương 1...' -> 'Chương 1...').
      - Xác định học kì 1 hay 2 (semester) dựa trên số thứ tự Chủ đề / Chương theo SGK.
      - Bổ sung các trường bắt buộc của DB: 'book_series', 'school_year', 'is_active'.
    """
    transformed = []
    for item in raw_topics:
        grade = item["grade"]
        ch = item["chapter"]

        # 1. Làm sạch tên chương & bài học: cắt bỏ tiền tố "Giáo án Toán X" nếu có
        clean_chapter = re.sub(r"^Giáo án\s+Toán\s+\d+\s*", "", ch, flags=re.IGNORECASE).strip()
        clean_topic = re.sub(r"^Giáo án\s+Toán\s+\d+\s*", "", item["topic_name"], flags=re.IGNORECASE).strip()

        # 2. Xác định học kì (semester = 1 hoặc 2) theo phân phối chuẩn Bộ GD&ĐT
        #    - Tiểu học (lớp 4-5): Lớp 4 (CĐ 1-7 là HK1, CĐ 8-13 là HK2); Lớp 5 (CĐ 1-6 là HK1, CĐ 7-12 là HK2).
        #    - THCS (lớp 6-9): Chương 1-5 là HK1, Chương 6-10 là HK2.
        sem = 1
        ch_lower = clean_chapter.lower()
        if "cuối năm" in ch_lower or "học kì 2" in ch_lower or "học kỳ 2" in ch_lower:
            sem = 2
        else:
            match = re.search(r"(?:Chương|Chủ đề)\s*(\d+)", clean_chapter, re.IGNORECASE)
            if match:
                num = int(match.group(1))
                if grade == 4 and num >= 8:
                    sem = 2
                elif grade == 5 and num >= 7:
                    sem = 2
                elif grade >= 6 and num >= 6:
                    sem = 2

        transformed.append({
            "grade": grade,
            "book_series": "Kết nối tri thức",
            "semester": sem,
            "chapter_name": clean_chapter,
            "topic_name": clean_topic,
            "order_index": item["order_index"],
            "school_year": school_year,
            "is_active": True,
            "source_url": item["source_url"],
        })

    return transformed


def export_to_curriculum_json(
    raw_topics: list[dict],
    save_path: Optional[str] = None,
) -> dict[str, list[str]]:
    """
    Biến đổi 424 bài học thô thành cấu trúc phân tầng {'4': [...], '5': [...]}
    tương thích chuẩn với file 'grade_curriculum.json' (phục vụ Task T8.26 cho AI Prompts).

    Tự động tối ưu:
      - Cắt bỏ tiền tố 'Bài X: ' để chỉ giữ lại khái niệm / tên dạng toán cốt lõi.
      - Lọc bỏ các bài chung chung không mang ngữ nghĩa toán học ('Luyện tập chung', 'Ôn tập chung'...).
      - Tùy chọn lưu thẳng ra file JSON nếu truyền 'save_path'.
    """
    result: dict[str, list[str]] = {str(g): [] for g in range(4, 10)}
    ignore_keywords = (
        "luyện tập chung",
        "ôn tập chung",
        "ôn tập cuối năm",
        "bài tập cuối chương",
        "bài tập cuối",
    )

    for item in raw_topics:
        g_str = str(item["grade"])
        topic = item["topic_name"].strip()
        topic_lower = topic.lower()

        # Bỏ qua bài luyện tập chung không có tên kiến thức cụ thể
        if any(ign in topic_lower for ign in ignore_keywords):
            continue

        # Cắt bỏ tiền tố "Giáo án Toán X" và "Bài X: " (ví dụ: "Bài 10: Số nguyên tố" -> "Số nguyên tố")
        clean_topic = re.sub(r"^(?:Giáo án\s+Toán\s+\d+\s+)?(?:Bài\s*\d+:\s*)?", "", topic, flags=re.IGNORECASE).strip()

        if clean_topic and clean_topic not in result[g_str]:
            result[g_str].append(clean_topic)

    # Nếu có đường dẫn file lưu, xuất ra file JSON UTF-8
    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[Crawler] Đã xuất thành công dữ liệu vào: {save_path}")

    return result


# ─── Khối Chạy Kiểm Tra Trực Tiếp Khi Thực Thi File Này ──────────────────────
if __name__ == "__main__":
    import sys
    import io
    from collections import Counter

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    print("=" * 65)
    print("SocraticKid — Curriculum Crawler (Task T8.24 - US 8.4)")
    print("Đang cào mục lục Toán lớp 4-9 từ VietJack...")
    print("=" * 65)

    # TEST NHANH: Cào thử nghiệm Lớp 4
    print("\n[TEST NHANH] Cào thử lớp 4:")
    sample = fetch_grade_curriculum(4)
    if sample:
        chapters = set(t["chapter"] for t in sample)
        print(f"  ✅ Thành công: Lấy được {len(sample)} bài học, thuộc {len(chapters)} chủ đề.")
        print(f"  Bài 1: {sample[0]['topic_name']}")
        print(f"  Bài cuối: {sample[-1]['topic_name']}")
    else:
        print("  ❌ Thất bại: Không lấy được lớp 4.")
        sys.exit(1)

    # FULL TEST: Cào toàn bộ 6 lớp
    print("\n[FULL TEST] Cào toàn bộ 6 khối lớp (4 -> 9)... Vui lòng đợi:")
    all_data = run_crawler()

    print(f"\n{'='*65}")
    print(f"✅ TỔNG KẾT: Đã bóc tách được {len(all_data)} bài học chuẩn!")

    by_grade = Counter(t["grade"] for t in all_data)
    for g in sorted(by_grade):
        print(f"  • Lớp {g}: {by_grade[g]} bài học")

    # TEST BIẾN ĐỔI 1: Database format (Thống T8.25)
    db_records = transform_for_db_sync(all_data)
    print(f"\n[BIẾN ĐỔI 1] Đã tạo {len(db_records)} bản ghi DB (mẫu bài đầu Lớp 7 đã làm sạch tên chương):")
    g7_sample = next((r for r in db_records if r["grade"] == 7), None)
    if g7_sample:
        print(f"  {g7_sample}")

    # TEST BIẾN ĐỔI 2: Xuất và cập nhật trực tiếp file grade_curriculum.json (cho T8.26)
    import os
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grade_curriculum.json")
    ai_curriculum = export_to_curriculum_json(all_data, save_path=json_path)
    total_ai_topics = sum(len(v) for v in ai_curriculum.values())
    print(f"\n[BIẾN ĐỔI 2] Đã xuất và cập nhật {total_ai_topics} dạng toán thuần túy vào: {json_path}")
    for g in sorted(ai_curriculum.keys()):
        print(f"  • Lớp {g}: {len(ai_curriculum[g])} dạng toán (mẫu: {ai_curriculum[g][:2]}...)")
