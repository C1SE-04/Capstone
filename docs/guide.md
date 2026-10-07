# 📘 Hướng Dẫn Thực Hiện Task: `[AI] Sửa agent_prompts.py – Nhận tham số grade_level, chèn vào prompt`

> **Sprint 5 – US 5.1: Chọn Lớp Học Sinh & AI Thích Nghi Theo Lớp**
> **Người thực hiện:** [Thông] – AI Engineer
> **Task:** T5.9
> **Ước tính thời gian:** 4 giờ

---

## 1. 🔍 Phân Tích Nhiệm Vụ

### Task này làm gì?

Hiện tại, AI trả lời học sinh mà **không biết học sinh đang học lớp mấy**. Toàn bộ prompt trong `agent_prompts.py` chỉ nói chung chung "học sinh lớp 4–9". Nhiệm vụ này yêu cầu:

> **Cho `agent_prompts.py` biết `grade_level` của học sinh để tự động chèn vào prompt: "Học sinh đang học Lớp X. Các kiến thức em đã học bao gồm: [danh sách tích lũy từ lớp 4 đến lớp X]."**

### Vấn đề hiện tại

Mở `agent_prompts.py` (dòng 51–58), hàm `build_specialized_agent_prompt` hiện tại **không có tham số `grade_level`**:

```python
# ⚠️ HIỆN TẠI: không biết grade_level
def build_specialized_agent_prompt(
    agent_role: str,
    task_description: str,
    history: list[dict],
    latest_message: str,
    reject_reason: Optional[str] = None,
    problem_context: Optional[dict] = None,
) -> str:
```

Và trong `orchestrator_bridge.py` (dòng 206), `agent_router` được gọi cũng không truyền `grade_level`:

```python
# ⚠️ HIỆN TẠI: không có grade_level
for chunk in agent_router(target_agent, enriched_task_description, history_text, user_query, expected_answer):
```

Hệ quả: **AI không biết học sinh lớp 7 đã học gì, nên không thể đánh giá "Em chưa học phân số" là đúng hay sai**.

### Những gì cần làm

| # | Việc cần làm | File |
|---|---|---|
| 1 | Tạo `grade_curriculum.json` – danh sách kiến thức tích lũy theo lớp 4–9 | `backend/agents/grade_curriculum.json` |
| 2 | Thêm hàm `_get_grade_context()` và tham số `grade_level` vào hàm chính | `backend/agents/agent_prompts.py` |
| 3 | Sửa `router.py` – thêm `grade_level`, chèn grade context vào prompt | `backend/router.py` |
| 4 | Sửa `orchestrator_bridge.py` – nhận và truyền `grade_level` xuống | `backend/orchestrator_bridge.py` |
| 5 | Sửa `main.py` – nhận `grade_level` từ request body | `backend/main.py` hoặc `schemas.py` |

> **Lưu ý:** Không cần sửa Frontend. Phần FE truyền `grade_level` là task của Thống/Bảo (T5.4 + T5.7). Task T5.9 chỉ làm phần AI/BE.

---

## 2. 🌿 Đặt Tên Branch

```bash
git checkout dev
git pull origin dev
git checkout -b feat/us5.1-grade-level-prompt
```

> `feat/` = tính năng mới, `us5.1` = User Story 5.1, `grade-level-prompt` = mô tả ngắn.

---

## 3. 🏗️ Phân Tích Code Hiện Tại

### Luồng hiện tại (không có grade_level)

```
POST /chat/orchestrator
   ↓ main.py
   ↓ process_query_with_orchestrator()   [orchestrator_bridge.py, dòng 107]
   ↓ agent_router()                      [router.py, dòng 38]
   ↓ Prompt gửi Gemini (không biết lớp)
```

### Luồng SAU khi sửa

```
POST /chat/orchestrator  { grade_level: 7 }
   ↓ main.py  →  parse grade_level=7
   ↓ process_query_with_orchestrator(grade_level=7)
   ↓ agent_router(grade_level=7)
   ↓ _get_grade_context(7)  →  danh sách kiến thức lớp 4–7
   ↓ Prompt chèn: "Học sinh đang học Lớp 7. Đã học: [...]"
   ↓ Gemini biết đủ ngữ cảnh để phản hồi phù hợp
```

### Kiến trúc file quan trọng cần nắm

- **`orchestrator_bridge.py`** – Điểm trung tâm, gọi `agent_router`. Đây là nơi đầu tiên nhận `grade_level` từ API.
- **`router.py`** – Gọi Gemini. Là nơi `base_prompt` được tạo ra – cần chèn `grade_context` vào đây.
- **`agent_prompts.py`** – Chứa `build_specialized_agent_prompt`. Cần thêm `grade_level` làm tham số và hàm `_get_grade_context()`.

---

## 4. 📋 Chuẩn Bị: Tạo `grade_curriculum.json`

**Tạo file mới:** `backend/agents/grade_curriculum.json`

**Nguyên tắc tích lũy:** Lớp 7 biết hết kiến thức lớp 4 + 5 + 6 + 7. Lớp 9 biết hết từ lớp 4 đến lớp 9.

```json
{
  "4": [
    "So tu nhien, so chan, so le",
    "Phep cong, tru, nhan, chia so co nhieu chu so",
    "Phan so: khai niem, so sanh, rut gon",
    "Cong, tru phan so cung mau va khac mau",
    "Nhan, chia phan so",
    "Dien tich, chu vi hinh chu nhat, hinh vuong",
    "Goc nhon, goc tu, goc vuong",
    "Don vi do do dai, dien tich, khoi luong, thoi gian"
  ],
  "5": [
    "So thap phan: doc, viet, so sanh",
    "Cong, tru, nhan, chia so thap phan",
    "Ti so phan tram",
    "Dien tich hinh tam giac, hinh thang",
    "The tich hinh hop chu nhat",
    "So nguyen to va hop so"
  ],
  "6": [
    "Uoc va boi, UCLN, BCNN",
    "So nguyen am",
    "Phep tinh voi so nguyen",
    "Phan so mo rong sang so nguyen",
    "Ti le thuc",
    "Hinh hoc: duong thang, goc, tam giac, tu giac",
    "Thong ke co ban: bieu do cot, tan so"
  ],
  "7": [
    "So huu ti va cac phep tinh",
    "Ti le thuan va ti le nghich",
    "Ham so va do thi (khai niem co ban)",
    "Phuong trinh bac nhat mot an",
    "Tam giac bang nhau (3 truong hop)",
    "Tam giac can, tam giac deu",
    "Tu giac: hinh thang, hinh binh hanh",
    "Thong ke: so trung binh cong, so trung vi"
  ],
  "8": [
    "Phep nhan, chia da thuc",
    "Hang dang thuc dang nho (7 hang dang thuc)",
    "Phan thuc dai so",
    "Phuong trinh bac nhat hai an",
    "He phuong trinh bac nhat hai an",
    "Tu giac: hinh chu nhat, hinh thoi, hinh vuong",
    "Dien tich cac hinh phang",
    "Dinh ly Pythagore"
  ],
  "9": [
    "Can bac hai va can thuc bac hai",
    "Ham so bac nhat y = ax + b",
    "Phuong trinh bac hai mot an",
    "He thuc Vi-et",
    "Ham so bac hai (khai niem)",
    "Duong tron: tiep tuyen, day cung, goc noi tiep",
    "Tam giac dong dang",
    "Ti so luong giac trong tam giac vuong",
    "The tich hinh tru, hinh non, hinh cau"
  ]
}
```

> **Lưu ý về encoding:** File JSON dùng tiếng Việt không dấu để tránh vấn đề encoding trên Windows. Thông có thể tự thêm dấu vào sau khi tạo file trên máy của mình.

---

## 5. ✍️ Code Cần Viết

### 5.1. Thêm hàm `_get_grade_context()` vào `agent_prompts.py`

**Mở file:** `backend/agents/agent_prompts.py`

**Thêm import và hàm mới vào đầu file** (ngay sau dòng `from typing import Optional`):

```python
import json
import os

def _load_curriculum() -> dict:
    """Tai grade_curriculum.json mot lan khi khoi dong module."""
    json_path = os.path.join(os.path.dirname(__file__), "grade_curriculum.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Cache curriculum khi module duoc load (khong doc file nhieu lan)
_CURRICULUM = _load_curriculum()


def _get_grade_context(grade_level: Optional[int]) -> str:
    """
    Xây dựng đoạn text ngữ cảnh kiến thức tích lũy theo lớp.

    Nguyên tắc tích lũy: Lớp 7 biết hết kiến thức lớp 4 + 5 + 6 + 7.
    Nếu grade_level=None → trả về chuỗi rỗng (không ảnh hưởng prompt).
    """
    if not grade_level or not _CURRICULUM:
        return ""

    grade = int(grade_level)
    all_topics = []
    for lvl in range(4, grade + 1):
        for topic in _CURRICULUM.get(str(lvl), []):
            all_topics.append(f"  - [Lớp {lvl}] {topic}")

    if not all_topics:
        return ""

    topics_text = "\n".join(all_topics)

    return f"""
─── THÔNG TIN LỚP HỌC SINH (QUAN TRỌNG) ───
Học sinh đang học: Lớp {grade}
Các kiến thức đã được học (tích lũy từ lớp 4 đến lớp {grade}):
{topics_text}

BẮT BUỘC khi học sinh nói "em chưa học" hoặc tỏ ra không hiểu:
- Nếu kiến thức thuộc danh sách trên: Học sinh đã học rồi. Nhẹ nhàng nhắc: "Theo chương trình, đây là kiến thức lớp X mà em đã học. Thầy tin em có thể nhớ lại...".
- Nếu KHÔNG thuộc danh sách (vượt cấp): Rất bình thường. An ủi: "Đây là kiến thức lớp cao hơn, em chưa học là hoàn toàn bình thường. Thầy sẽ giải thích thật đơn giản để em hiểu nhé...". Sau đó VẪN tiếp tục hướng dẫn học sinh giải quyết bài toán đó.
"""
```

---

### 5.2. Sửa `build_specialized_agent_prompt` trong `agent_prompts.py`

**Tìm hàm `build_specialized_agent_prompt` (dòng 51). Thêm tham số `grade_level`:**

```python
# TRUOC KHI SUA:
def build_specialized_agent_prompt(
    agent_role: str,
    task_description: str,
    history: list[dict],
    latest_message: str,
    reject_reason: Optional[str] = None,
    problem_context: Optional[dict] = None,
) -> str:

# SAU KHI SUA:
def build_specialized_agent_prompt(
    agent_role: str,
    task_description: str,
    history: list[dict],
    latest_message: str,
    reject_reason: Optional[str] = None,
    problem_context: Optional[dict] = None,
    grade_level: Optional[int] = None,   # THEM DONG NAY
) -> str:
```

**Thêm dòng này ngay trước câu lệnh `return f"""` ở cuối hàm:**

```python
grade_context = _get_grade_context(grade_level)   # THEM DONG NAY
```

**Tìm trong chuỗi `return f"""`, tìm đoạn `{reject_section}{problem_section}` và sửa:**

```python
# TRUOC KHI SUA:
{reject_section}{problem_section}
─── TASK TU ORCHESTRATOR ───

# SAU KHI SUA (them {grade_context}):
{reject_section}{problem_section}{grade_context}
─── TASK TU ORCHESTRATOR ───
```

> **Lý do:** Khi `grade_level=None` thì `grade_context=""` → prompt không thay đổi gì. Backward compatible hoàn toàn.

---

### 5.3. Sửa `router.py`

**Mở file:** `backend/router.py`

**Bước 1 – Thêm import ở đầu file:**

```python
from agents.agent_prompts import _get_grade_context
```

**Bước 2 – Sửa chữ ký hàm `agent_router` (dòng 38):**

```python
# TRUOC:
def agent_router(target_agent: str, task_description: str, history_text: str, user_query: str, expected_answer: str = ""):

# SAU:
def agent_router(target_agent: str, task_description: str, history_text: str, user_query: str, expected_answer: str = "", grade_level: int = None):
```

**Bước 3 – Tìm biến `base_prompt` (dòng 55), thêm `grade_context` vào đầu prompt:**

```python
# Them dong nay TRUOC khi tao base_prompt:
# (LƯU Ý: Nếu muốn test khi Thống chưa làm xong Backend, hãy sửa tạm thành grade_level = 7 ở đây)
grade_context = _get_grade_context(grade_level)

# Sua base_prompt – them {grade_context} vao dau:
base_prompt = f"""
{grade_context}
Vai tro chuyen mon hien tai: {target_agent}.
Chi dao su pham tu Orchestrator: {task_description}

--- LICH SU TRO CHUYEN ---
{history_text}

--- HOC SINH VUA NOI ---
{user_query}

NHAC LAI NGUYEN TAC:
- Ban la THAY GIAO, xung "thay" goi "em", TUYET DOI KHONG xung "Da".
- Chi nhac nho thai do khi hoc sinh dung tu XUC PHAM THUC SU (may, tao, chui the)
- Tra loi ngan gon, chuan muc (2-4 cau).
"""
```

---

## 6. 🧪 Kiểm Tra Chức Năng (Acceptance Criteria)

Vì Thống đang làm phần nối dữ liệu từ ngoài vào (`main.py` -> `orchestrator_bridge.py`), nên để bạn có thể test độc lập ngay bây giờ, hãy **mở file `router.py`** và gán cứng tạm thời:

```python
def agent_router(...):
    # HARDCODE ĐỂ TEST TRONG LÚC CHỜ THỐNG:
    grade_level = 7 
    # ...
```

Test bằng Postman với kịch bản dưới đây (gọi `POST http://localhost:8000/chat/orchestrator`):

| # | Hành động | Kết quả mong đợi |
|---|---|---|
| **Test 1** | Gửi message: "Em chua hoc phan so" | AI KHÔNG xin lỗi – nhắc "phân số là kiến thức lớp 4 em đã học" |
| **Test 2** | Gửi message: "Em chua hoc phuong trinh bac hai" | AI an ủi "lớp cao hơn... chưa học là bình thường" và vẫn hướng dẫn |
| **Test 3** | Sửa hardcode `grade_level = None` | AI trả lời bình thường, log KHÔNG có section "THÔNG TIN LỚP HỌC SINH" |

### Cách bật server để test

```bash
# Chay backend:
cd d:\Document\Capstone\backend
python -m uvicorn main:app --reload --port 8000

# De debug prompt, them dong print vao router.py truoc khi goi model:
print("=== PROMPT ===")
print(prompt[:2000])  # in 2000 ky tu dau
print("=== END ===")
# XOA DOAN HARDCODE VA PRINT NAY SAU KHI TEST XONG
```

---

## 7. 📁 Tóm Tắt File Cần Tạo / Sửa

```
backend/
├── agents/
│   ├── agent_prompts.py       SUA: them grade_level, them ham _get_grade_context()
│   └── grade_curriculum.json  TAO MOI: kien thuc theo lop
└── router.py                  SUA: them grade_level, chen grade_context vao prompt
```

**Không cần (Phần việc của Thống):**
- Sửa `orchestrator_bridge.py` và `main.py` / `schemas.py` (Thuộc T5.4 của Thống).
- Frontend / Database.

---

## 8. 📤 Tạo Pull Request

```bash
git add backend/agents/agent_prompts.py
git add backend/agents/grade_curriculum.json
git add backend/orchestrator_bridge.py
git add backend/router.py
git add backend/main.py
git commit -m "feat(US5.1-T5.9): Inject grade_level into AI prompt with cumulative curriculum"
git push origin feat/us5.1-grade-level-prompt
```

Lên GitHub tạo PR:
- **Base branch:** `dev`
- **PR title:** `[AI][US5.1-T5.9] Grade-level awareness in agent prompt`
- **Assign reviewer:** Thien (T5.13: Review PR toan bo luong AI)

---

## 9. ⚠️ Phụ Thuộc Cần Biết

| Người | Task | Ảnh hưởng đến T5.9 |
|---|---|---|
| **Thống** | T5.1: Thêm cột `grade_level` vào DB | Không cần đợi – test thủ công Postman với giá trị hardcode |
| **Thống** | T5.4: API login trả về `grade_level` | Cần khi test luồng thật từ FE. Chưa có thì dùng Postman |
| **Bảo** | T5.7: Lưu `grade_level` vào NextAuth | Không cần đợi – test BE độc lập |

> ✅ **Không cần ngồi đợi:** Thông làm phần AI/BE trước, test bằng Postman với `grade_level` hardcode. Khi Thống + Bảo xong thì ráp thật vào là done. Làm song song theo sơ đồ phụ thuộc sprint đã nêu.

---

*Hướng dẫn này thuộc Sprint 5 – SocraticKid Capstone Project.*
