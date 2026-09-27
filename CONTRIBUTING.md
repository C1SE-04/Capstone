# Hướng dẫn Đóng góp
---
## 🚀 Bắt Đầu Nhanh

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/Capstone.git
cd Capstone
git remote add upstream https://github.com/C1SE-04/Capstone.git
```

### 2. Tạo Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/ten-tinh-nang
```

### 3. Commit & Push
```bash
git add .
git commit -m "feat: Mô tả ngắn thay đổi"git checkout -b feature/chuc-nang-dang-nhap
git push origin feature/ten-tinh-nang
```

### 4. Tạo Pull Request
- PR hướng tới nhánh `develop` (không phải `main`)
- Mô tả rõ ràng những gì đã thay đổi
- Đợi review từ team

---

## 📝 Tiêu chuẩn Code

### Backend (Python)

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Biến, Hàm | snake_case | `get_session()`, `user_id` |
| Lớp, Model | PascalCase | `ChatSession`, `UserRequest` |
| File | snake_case | `session.py`, `auth.py` |
| Hằng số | UPPER_SNAKE_CASE | `MAX_RETRIES = 3` |

**Bắt buộc:**
- Type hinting: `def get_user(user_id: str) -> dict:`
- Docstring cho function: `"""Lấy thông tin user."""`

```bash
# Format code trước push
black backend/
```

### Frontend (TypeScript/React)

| Đối tượng | Quy ước | Ví dụ |
|---|---|---|
| Component | PascalCase | `ChatBox.tsx` |
| Biến, Hàm | camelCase | `isLoading`, `handleClick()` |
| Type/Interface | PascalCase | `UserProps`, `MessagePayload` |

```bash
# Format code trước push
npm run lint
npm run format
```

---

## 📦 Commit Convention

Sử dụng **Conventional Commits**:

```
<type>: <mô tả ngắn>

<chi tiết (nếu cần)>
```

### Types
- `feat:` - Tính năng mới
- `fix:` - Sửa bug
- `docs:` - Cập nhật tài liệu
- `style:` - Format code
- `refactor:` - Viết lại code
- `test:` - Thêm test
- `chore:` - Update dependencies

### Ví dụ
```
feat: Thêm chức năng pinned session

Học sinh có thể ghim các session quan trọng.
Session ghim hiển thị đầu tiên trong danh sách.

Fixes #42
```

---

## 🧪 Testing

### Backend
```bash
cd backend
pip install pytest
pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm run test
npm run test:watch
```

**Yêu cầu:** Mỗi feature mới phải có test

---

## 📋 Quy Tắc PR

- ✅ Code passes linting & tests
- ✅ Có mô tả rõ ràng
- ✅ 2 approvals trước merge
- ✅ Update documentation nếu cần

---

## 🔧 Cài Đặt Local

### Backend
```powershell
cd backend
python -m venv venv --without-pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Truy cập: http://localhost:3000

---

Cảm ơn đã đóng góp!
