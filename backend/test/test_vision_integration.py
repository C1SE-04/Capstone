"""
Unit & Integration Test: Tích hợp Gemini Vision xử lý ảnh Cloudinary URL
Chạy: python -m unittest backend/test/test_vision_integration.py -v
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from PIL import Image

# Thêm thư mục backend vào sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Cấu hình UTF-8 cho Windows console tránh lỗi UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from router import agent_router, load_image_from_url, SOCRATIC_VISION_INSTRUCTION


class TestGeminiVisionIntegration(unittest.TestCase):

    def setUp(self):
        """Giả lập GEMINI_API_KEY để test chạy độc lập không phụ thuộc file .env."""
        self._orig_key = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "fake-key-for-unit-test"

    def tearDown(self):
        if self._orig_key is not None:
            os.environ["GEMINI_API_KEY"] = self._orig_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)

    def test_load_image_from_url_invalid(self):
        """Hàm load ảnh trả về None an toàn khi URL rỗng hoặc sai định dạng."""
        self.assertIsNone(load_image_from_url(None))
        self.assertIsNone(load_image_from_url(""))
        self.assertIsNone(load_image_from_url("not_a_valid_url"))

    @patch("httpx.Client.get")
    def test_load_image_from_url_success(self, mock_get):
        """Hàm load ảnh tải bytes từ URL và chuyển thành PIL Image hợp lệ."""
        import io
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        
        mock_resp = MagicMock()
        mock_resp.content = img_bytes.getvalue()
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        result = load_image_from_url("https://res.cloudinary.com/demo/image/upload/math.png")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Image.Image)

    def test_vision_instruction_contains_core_pedagogy(self):
        """Prompt Socratic Vision bắt buộc phải chứa các nguyên tắc chống lộ đáp án."""
        self.assertIn("ĐỌC VÀ TRÍCH XUẤT ĐỀ BÀI", SOCRATIC_VISION_INSTRUCTION)
        self.assertIn("LaTeX chuẩn", SOCRATIC_VISION_INSTRUCTION)
        self.assertIn("TUYỆT ĐỐI KHÔNG GIẢI RA ĐÁP ÁN", SOCRATIC_VISION_INSTRUCTION)
        self.assertIn("GỢI MỞ BƯỚC ĐẦU TIÊN", SOCRATIC_VISION_INSTRUCTION)

    @patch("router.load_image_from_url")
    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_agent_router_with_attachment_url_multimodal(self, mock_generate, mock_load_img):
        """Khi có attachment_url, agent_router phải truyền [image, prompt] vào model."""
        fake_img = Image.new("RGB", (50, 50), color=(255, 255, 255))
        mock_load_img.return_value = fake_img
        
        mock_response = MagicMock()
        mock_response.text = "Chào em! Thầy thấy bài toán trong ảnh là $2x + 4 = 10$. Bước đầu tiên em sẽ làm gì với số 4 nhỉ?"
        mock_generate.return_value = mock_response

        # Gọi generator
        chunks = list(agent_router(
            target_agent="SCAFFOLDING_AGENT",
            task_description="Hướng dẫn gợi mở",
            history_text="",
            user_query="Thầy xem ảnh giúp em với",
            attachment_url="https://res.cloudinary.com/demo/image/upload/sample.jpg"
        ))

        # Kiểm tra payload gọi model là list chứa [fake_img, prompt_text]
        mock_generate.assert_called()
        call_args = mock_generate.call_args[0][0]
        self.assertIsInstance(call_args, list)
        self.assertEqual(call_args[0], fake_img)
        self.assertIn("SOCRATIC VISION", call_args[1])
        self.assertGreater(len(chunks), 0)

    @patch("google.generativeai.GenerativeModel.generate_content")
    def test_agent_router_without_attachment_url_backward_compatible(self, mock_generate):
        """Khi KHÔNG có attachment_url, agent_router phải truyền prompt text thuần túy."""
        mock_response = MagicMock()
        mock_response.text = "Chào em! Để tính phép cộng phân số, em hãy quy đồng mẫu số nhé."
        mock_generate.return_value = mock_response

        chunks = list(agent_router(
            target_agent="SCAFFOLDING_AGENT",
            task_description="Hướng dẫn gợi mở",
            history_text="",
            user_query="1/2 + 1/3 tính sao thầy?",
            attachment_url=None
        ))

        mock_generate.assert_called()
        call_args = mock_generate.call_args[0][0]
        # Không được là list chứa ảnh, mà là chuỗi prompt text
        self.assertIsInstance(call_args, str)
        self.assertNotIn("HƯỚNG DẪN XỬ LÝ ẢNH BÀI TOÁN TỪ CLOUDINARY", call_args)
        self.assertGreater(len(chunks), 0)


if __name__ == "__main__":
    unittest.main()