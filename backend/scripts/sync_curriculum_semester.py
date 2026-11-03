"""
SocraticKid Backend — US 9.3 (Task T9.12)
Script đồng bộ nhãn semester (1 | 2) giữa Neon DB (curriculum_topics) và grade_curriculum.json.

Cách chạy:
    cd d:\Document\Capstone\backend
    $env:PYTHONIOENCODING="utf-8"; python scripts/sync_curriculum_semester.py
"""

import sys
import os
import re
import json
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
import models


def sync_db_and_json():
    print("=" * 65)
    print("SocraticKid — Đồng Bộ Nhóm Học Kỳ (Task T9.12 - US 9.3)")
    print("=" * 65)

    db = SessionLocal()
    try:
        # 1. Cập nhật và chuẩn hóa semester trong bảng curriculum_topics (sửa lỗi Lớp 5)
        print("\n[1/3] Chuẩn hóa cột 'semester' trong Neon DB theo phân phối Bộ GD&ĐT...")
        topics = db.query(models.CurriculumTopic).all()
        updated_db_count = 0

        for t in topics:
            norm_ch = unicodedata.normalize('NFC', t.chapter_name or "")
            ch_lower = norm_ch.lower()
            correct_sem = 1

            if "cuối năm" in ch_lower or "học kì 2" in ch_lower or "học kỳ 2" in ch_lower:
                correct_sem = 2
            else:
                m = re.search(r"(?:Chương|Chủ đề)\s*(\d+)", norm_ch, re.IGNORECASE)
                if m:
                    num = int(m.group(1))
                    if t.grade == 4 and num >= 8:
                        correct_sem = 2
                    elif t.grade == 5 and num >= 7:
                        correct_sem = 2
                    elif t.grade >= 6 and num >= 6:
                        correct_sem = 2

            if t.semester != correct_sem:
                t.semester = correct_sem
                updated_db_count += 1

        db.commit()
        print(f"  [OK] Đã hiệu chỉnh {updated_db_count} bản ghi trong Neon DB (chuẩn hóa NFC).")

        # 2. Xây dựng từ điển tra cứu nhanh từ DB: (grade, clean_topic_nfc) -> semester
        db_map = {}
        for t in db.query(models.CurriculumTopic).all():
            clean_name = re.sub(
                r"^(?:Giáo án\s+Toán\s+\d+\s+)?(?:Bài\s*\d+:\s*)?",
                "",
                t.topic_name,
                flags=re.IGNORECASE
            ).strip()
            key = (t.grade, unicodedata.normalize('NFC', clean_name.lower()))
            db_map[key] = t.semester

        # 3. Đọc và nâng cấp file grade_curriculum.json
        print("\n[2/3] Cập nhật cấu trúc 'grade_curriculum.json' sang dạng phân nhóm {'1': [...], '2': [...] }...")
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents", "grade_curriculum.json")

        if not os.path.exists(json_path):
            print(f"  [LỖI] Không tìm thấy file: {json_path}")
            return

        with open(json_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        new_curriculum = {}
        for g_str in sorted(raw_data.keys(), key=lambda x: int(x)):
            g_int = int(g_str)
            raw_val = raw_data[g_str]
            new_curriculum[g_str] = {"1": [], "2": []}

            # Lấy danh sách bài gốc (hỗ trợ cả dạng list cũ hoặc dict mới)
            topic_list = []
            if isinstance(raw_val, list):
                for it in raw_val:
                    t_title = it.get("topic") if isinstance(it, dict) else str(it)
                    topic_list.append(t_title)
            elif isinstance(raw_val, dict):
                topic_list = raw_val.get("1", []) + raw_val.get("2", [])

            for title in topic_list:
                norm_title = unicodedata.normalize('NFC', title.strip())
                lookup_key = (g_int, norm_title.lower())

                # Tìm học kì khớp chính xác hoặc mờ trong DB
                sem = db_map.get(lookup_key)
                if sem is None:
                    for (dg, dt), s in db_map.items():
                        if dg == g_int and (norm_title.lower() in dt or dt in norm_title.lower()):
                            sem = s
                            break

                # Fallback an toàn nếu không thấy trong DB
                if sem not in (1, 2):
                    sem = 1

                sem_key = str(sem)
                if norm_title not in new_curriculum[g_str][sem_key]:
                    new_curriculum[g_str][sem_key].append(norm_title)

        # Ghi lại ra file JSON định dạng thụt lề 2 spaces
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(new_curriculum, f, ensure_ascii=False, indent=2)

        print(f"  [OK] Đã ghi thành công cấu trúc mới vào: {json_path}")

        # 4. Thống kê tổng kết
        print("\n[3/3] Thống kê phân bổ học kì theo từng khối lớp:")
        for g_str in new_curriculum:
            s1_list = new_curriculum[g_str]["1"]
            s2_list = new_curriculum[g_str]["2"]
            print(f"  • Lớp {g_str}: Tổng {len(s1_list) + len(s2_list):2d} bài | Học kỳ 1: {len(s1_list):2d} bài | Học kỳ 2: {len(s2_list):2d} bài")

        print("\n" + "=" * 65)
        print("✅ [HOÀN TẤT] Đồng bộ dataset grade_curriculum.json thành công 100%!")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    sync_db_and_json()

