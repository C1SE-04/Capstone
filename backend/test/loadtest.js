import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  // Kịch bản: Bơm từ từ lên 20 user ảo, giữ nguyên 1 phút rồi giảm dần
  stages: [
    { duration: '30s', target: 20 },
    { duration: '1m', target: 20 },
    { duration: '30s', target: 0 },
  ],
};

export default function () {
  // URL chính xác của API trong backend/routers/chat.py
  const url = 'http://localhost:8000/chat/orchestrator'; 
  
  // Dựa vào schema GeminiRequest, backend yêu cầu 2 trường: session_id và prompt
  const payload = JSON.stringify({
    session_id: "loadtest_session_" + __VU, // __VU là ID của user ảo đang chạy k6
    prompt: "Giải thích cho tôi về định lý pytago",
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      // Nếu API yêu cầu token, bỏ comment dòng dưới và thêm token thật
      // 'Authorization': 'Bearer YOUR_TOKEN_HERE', 
    },
  };

  // Bắn request POST
  const res = http.post(url, payload, params);

  // Kiểm tra kết quả
  check(res, {
    'status is 200': (r) => r.status === 200,
    'no server error': (r) => r.status !== 500,
  });

  // Nghỉ 1s giữa mỗi request để mô phỏng giống user thật hơn
  sleep(1);
}
