# SETUP.md

# Hướng dẫn cài đặt môi trường phát triển

Tài liệu này hướng dẫn từng bước cài đặt môi trường làm việc cho dự án. Sau khi hoàn thành, máy tính của bạn cần đáp ứng các yêu cầu sau:

## Mục tiêu hoàn thành

* Đã cài đặt **Node.js v22.x**
* Đã cài đặt **Python 3.11.x**
* Đã cài đặt **Visual Studio Code (VS Code)**
* Đã cài đặt đầy đủ các Extensions bắt buộc:

  * ESLint
  * Prettier
  * Python
  * Prisma

## Yêu cầu hệ điều hành

Hỗ trợ:

* Windows 10 / 11

---

# Bước 1: Cài đặt Node.js v22

## 1.1 Tải Node.js

Truy cập trang chính thức:

https://nodejs.org

Tải phiên bản:

**v22.23.2 LTS with npm** 

> Không sử dụng các bản có nhãn EOL (End of life) mà chỉ tải các bản LTS (Long Term Support).

---

## 1.2 Kiểm tra cài đặt

Mở Terminal hoặc Command Prompt và chạy:
**Lưu ý:** chỉ gõ các lệnh nằm trong khối lệnh bash (ví dụ: node -v, không copy cả khối)

```bash
node -v
```

Kết quả mong muốn:

```bash
v22.x.x
```

Ví dụ:

```bash
v22.18.0
```

Tiếp tục kiểm tra npm:

```bash
npm -v
```

Ví dụ:

```bash
10.x.x
```

**Nếu xuất hiện số phiên bản nghĩa là cài đặt thành công.**

---

# Bước 2: Cài đặt Python 3.11

## 2.1 Tải Python

Truy cập:

https://www.python.org/downloads/

Tải phiên bản:

**Python 3.11.x**

> Không sử dụng Python 3.12 hoặc Python 3.13 nếu dự án yêu cầu Python 3.11.

---

## 2.2 Lưu ý quan trọng khi cài trên Windows

Khi mở trình cài đặt Python:

✅ Chọn:

```text
Add Python to PATH
```

sau đó nhấn:

```text
Install Now
```

---

## 2.3 Kiểm tra cài đặt

Mở Terminal hoặc Command Prompt:

```bash
python --version
```

Kết quả mong muốn:

```bash
Python 3.11.x
```

Ví dụ:

```bash
Python 3.11.9
```

Nếu lệnh trên không hoạt động, thử:

```bash
python3 --version
```

---

# Bước 3: Cài đặt Visual Studio Code

## 3.1 Tải VS Code

Truy cập:

https://code.visualstudio.com

Tải phiên bản phù hợp với hệ điều hành của bạn.

---

## 3.2 Kiểm tra

Sau khi cài đặt:

* Mở VS Code thành công
* Có thể mở thư mục dự án

---

# Bước 4: Cài đặt Extensions bắt buộc

Mở VS Code.

Chọn:

```text
Extensions
```

hoặc nhấn:

```text
Ctrl + Shift + X
```

Tìm kiếm và cài đặt các extension sau.

---

## 4.1 ESLint

Tên Extension:

```text
ESLint
```

Nhà phát triển:

```text
Microsoft
```

Mục đích:

* Kiểm tra lỗi JavaScript/TypeScript
* Hỗ trợ coding standards

---

## 4.2 Prettier

Tên Extension:

```text
Prettier - Code formatter
```

Nhà phát triển:

```text
Prettier
```

Mục đích:

* Tự động format code
* Đồng bộ coding style trong nhóm

---

## 4.3 Python

Tên Extension:

```text
Python
```

Nhà phát triển:

```text
Microsoft
```

Mục đích:

* Hỗ trợ Python
* Debug
* IntelliSense
* Virtual Environment

---

## 4.4 Prisma

Tên Extension:

```text
Prisma
```

Nhà phát triển:

```text
Prisma
```

Mục đích:

* Hỗ trợ Prisma Schema
* Syntax Highlighting
* Auto-completion

---

# Bước 5: Xác nhận môi trường

Sau khi hoàn thành, chạy các lệnh sau.

## Kiểm tra Node.js

```bash
node -v
```

Kết quả:

```bash
v22.x.x
```

---

## Kiểm tra npm

```bash
npm -v
```

Kết quả:

```bash
10.x.x
```

---

## Kiểm tra Python

```bash
python --version
```

Kết quả:

```bash
Python 3.11.x
```

---

# Checklist hoàn thành

* [ ] Đã cài đặt Node.js v22
* [ ] Lệnh `node -v` trả về `v22.x.x`
* [ ] Đã cài đặt Python 3.11
* [ ] Lệnh `python --version` trả về `Python 3.11.x`
* [ ] Đã cài đặt VS Code
* [ ] Đã cài đặt ESLint
* [ ] Đã cài đặt Prettier
* [ ] Đã cài đặt Python Extension
* [ ] Đã cài đặt Prisma Extension

---

# Tiêu chí nghiệm thu

Mỗi thành viên trong nhóm được xem là hoàn thành bước thiết lập môi trường khi:

1. Chạy lệnh:

```bash
node -v
```

trả về:

```bash
v22.x.x
```

2. Chạy lệnh:

```bash
python --version
```

trả về:

```bash
Python 3.11.x
```

3. Mở được VS Code.

4. Đã cài đặt đầy đủ các Extensions:

* ESLint
* Prettier
* Python
* Prisma

5. Không xuất hiện lỗi liên quan đến PATH của Node.js hoặc Python.
