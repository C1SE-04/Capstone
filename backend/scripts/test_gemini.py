import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
import google.generativeai as genai

# Nạp biến môi trường từ .env
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Lỗi: Không tìm thấy GEMINI_API_KEY trong biến môi trường.")
    exit(1)

# Cấu hình API Key
genai.configure(api_key=api_key)

# Khởi tạo model (sử dụng model có sẵn từ danh sách bạn vừa test)
model = genai.GenerativeModel('gemini-3.1-flash-lite')

prompt = """
Hãy tạo thông tin ngẫu nhiên về một học sinh. Trả về kết quả dưới định dạng JSON với cấu trúc sau:
{
    "name": "string",
    "genre": "string",
    "price": "number"
}
"""

def test_json_generation():
    print("Đang gửi yêu cầu tới Gemini...")
    try:
        # Ép model trả về kết quả dưới dạng JSON
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
        )
        
        print("\n=== RAW RESPONSE (Dạng chuỗi trả về) ===")
        print(response.text)
        
        print("\n=== PARSED JSON (Parse thành Python Dict) ===")
        # Kiểm tra xem có parse được thành JSON chuẩn không
        data = json.loads(response.text)
        print(json.dumps(data, indent=4, ensure_ascii=False))
        
        print("\nTHÀNH CÔNG: Đã trả về và parse được JSON chuẩn xác!")

    except json.JSONDecodeError:
        print("\nTHẤT BẠI: Kết quả trả về không phải là một chuỗi JSON hợp lệ.")
    except Exception as e:
        print(f"\nCÓ LỖI XẢY RA: {e}")

if __name__ == "__main__":
    test_json_generation()
