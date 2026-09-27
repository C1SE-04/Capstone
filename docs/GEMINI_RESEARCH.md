# Nghiên cứu: Google Gemini API - Structured Outputs & Streaming

## 1. Structured Outputs (Đầu ra dạng JSON)

Gemini API cho phép ép buộc mô hình trả về dữ liệu tuân thủ một định dạng JSON Schema nhất định. Điều này rất hữu ích cho các Agent (như Orchestrator, Knowledge, Misconception, Scaffolding, Safety) để dễ dàng bóc tách dữ liệu.

- Sử dụng thư viện `pydantic` để định nghĩa cấu trúc dữ liệu (`BaseModel`). 
- Truyền JSON schema vào tham số `response_format` trong `client.interactions.create()`.
- Định dạng yêu cầu: `mime_type: "application/json"`.

### Cấu trúc Code:
```python
from google import genai
from pydantic import BaseModel, Field
# pydantic dùng để kiểm tra dữ liệu đầu ra từ gemini API
# BaseModel là lớp cơ sở của Pydantic, giúp Tự động kiểm tra và báo lỗi dữ liệu (age='muoi_tam' -> báo lỗi), Tự động ép kiểu thông minh (age='18' -> ép kiểu thành int 18)
# 1. Định nghĩa Schema bằng Pydantic
class ResponseSchema(BaseModel):
    answer: str = Field(description="Câu trả lời của AI") #định hướng cho AI biết cần trả về dữ liệu j vào đây 
    thought_process: str = Field(description="Luồng suy nghĩ ngầm của AI")

# 2. Khởi tạo Client
client = genai.Client()

# 3. Gọi API với response_format
interaction = client.interactions.create(
    model="gemini-3.7-flash",
    input="Giải thích phương trình bậc 2",
    response_format={
        "type": "text",
        "mime_type": "application/json",
        "schema": ResponseSchema.model_json_schema() #.model_json_schema():  nó là một phương thức của BaseModel, dùng để chuyển đổi định nghĩa lớp Pydantic (cấu trúc dữ liệu) sang một định dạng JSON Schema chuẩn. JSON Schema này sau đó được truyền cho mô hình Gemini để mô hình biết chính xác cấu trúc đầu ra mong muốn là gì.  
    }
)

# 4. Parse dữ liệu trả về
result = ResponseSchema.model_validate_json(interaction.output_text)
print(result.answer)
```

## 2. Streaming (Trả về dữ liệu theo luồng)

Thay vì chờ mô hình sinh xong toàn bộ câu trả lời (có thể mất nhiều giây), cơ chế Streaming cho phép nhận dữ liệu từng phần (chunk) ngay khi mô hình đang sinh. Trải nghiệm người dùng sẽ mượt mà hơn.

- Bật cờ `stream=True` trong `client.interactions.create()`.
- Hàm gọi sẽ trả về một Iterable stream.
- Lặp qua các event, kiểm tra `event.event_type == "step.delta"` và `event.delta.type == "text"` để lấy text.

### Cấu trúc Code:
```python
from google import genai

client = genai.Client()

stream = client.interactions.create(
    model="gemini-3.7-flash",
    input="Kể một câu chuyện ngắn về toán học.",
    stream=True #nghĩ từ nào, trả về từ đó
)

for event in stream:
    # Bắt các sự kiện chữ đang được sinh ra
    if event.event_type == "step.delta": #nếu có chữ mới trả về
        if event.delta.type == "text" and getattr(event.delta, "text", None): #kiểm tra xem chữ mới trả về(không phải là hình ảnh)
            print(event.delta.text, end="", flush=True) #end="" là ko tự động xuống dòng, flush=True là in ra ngay
            
    # Bắt sự kiện hoàn thành
    elif event.event_type == "interaction.completed": #khi gemini trả xong
        print(f"\n[Hoàn tất - Tổng tokens: {event.interaction.usage.total_tokens}]")
```

## 3. Kết hợp Streaming và Structured Outputs

Đặc biệt, Interactions API hỗ trợ kết hợp cả Stream và JSON Schema. Các chunk stream trả về sẽ là các phần JSON không hoàn chỉnh, khi ghép lại sẽ được chuỗi JSON chuẩn.

### Code mẫu Python hoàn chỉnh chạy được:

```python
import os
from google import genai
from pydantic import BaseModel, Field

# Yêu cầu cài đặt SDK: pip install google-genai
# Đảm bảo đã set biến môi trường GEMINI_API_KEY

class TutorResponse(BaseModel):
    thought_process: str = Field(description="Nháp ngầm cách giải bài toán")
    student_response: str = Field(description="Câu hỏi gợi ý lại cho học sinh theo phương pháp Socratic, không được đưa ra đáp án cuối cùng.")

def test_gemini_streaming_json():
    client = genai.Client()
    
    prompt = """
    Học sinh: Làm sao để giải phương trình x^2 - 4 = 0?
    AI Gia sư (chỉ gợi ý, không giải hộ):
    """

    print("Đang gọi AI...\n")
    stream = client.interactions.create(
        model="gemini-3.7-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": TutorResponse.model_json_schema()
        },
        stream=True
    )
    
    full_json = ""
    for event in stream:
        if event.event_type == "step.delta":
            if event.delta.type == "text" and getattr(event.delta, "text", None):
                chunk = event.delta.text
                print(chunk, end="", flush=True)
                full_json += chunk
                
    print("\n\n--- KẾT QUẢ ĐÃ PARSE THÀNH OBJECT ---")
    try:
        final_obj = TutorResponse.model_validate_json(full_json)
        print("Nháp ngầm:", final_obj.thought_process)
        print("Phản hồi học sinh:", final_obj.student_response)
    except Exception as e:
        print("Lỗi parse JSON:", e)

if __name__ == "__main__":
    test_gemini_streaming_json()
```
