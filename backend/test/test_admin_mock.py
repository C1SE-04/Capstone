"""
Test suite cho US 7.3 (Task T7.31) — Router Mock Data /admin/mock/...
Chạy: python test/test_admin_mock.py
hoặc: pytest test/test_admin_mock.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import schemas

client = TestClient(app)


class TestAdminMockRouter(unittest.TestCase):

    def test_01_get_mock_overview_kpis(self):
        """Kiểm tra endpoint /admin/mock/overview trả về 4 thẻ KPI chuẩn xác."""
        res = client.get("/admin/mock/overview")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Kiểm tra cấu trúc response
        self.assertIn("total_users", data)
        self.assertIn("student_dau", data)
        self.assertIn("ai_sessions", data)
        self.assertIn("ai_tokens", data)
        self.assertEqual(data["system_status"], "OPERATIONAL")
        self.assertEqual(data["version"], "v1.4.0")

        # Kiểm tra giá trị các KPI
        self.assertEqual(data["total_users"]["value"], 12480)
        self.assertEqual(data["total_users"]["growth_percent"], 14.2)
        self.assertEqual(data["student_dau"]["value"], 3842)
        self.assertEqual(data["ai_sessions"]["value"], 48920)
        self.assertEqual(data["ai_tokens"]["display_value"], "14.8M")

        # Validate qua Pydantic schema
        schema_obj = schemas.AdminOverviewResponse.model_validate(data)
        self.assertIsNotNone(schema_obj)

    def test_02_get_mock_growth_metrics(self):
        """Kiểm tra số liệu tăng trưởng DAU/MAU (/admin/mock/metrics/growth)."""
        res = client.get("/admin/mock/metrics/growth?days=14")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["period"], "14_days")
        self.assertEqual(len(data["data"]), 14)
        first_item = data["data"][0]
        self.assertIn("date", first_item)
        self.assertIn("dau", first_item)
        self.assertIn("mau", first_item)
        self.assertIn("new_users", first_item)
        self.assertGreater(first_item["dau"], 3000)

        # Validate qua Pydantic schema
        schemas.AdminGrowthResponse.model_validate(data)

    def test_03_get_mock_token_consumption(self):
        """Kiểm tra số liệu tiêu thụ Token AI (/admin/mock/metrics/tokens)."""
        res = client.get("/admin/mock/metrics/tokens?days=14")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["period"], "14_days")
        self.assertGreater(data["total_tokens"], 1000000)
        self.assertGreater(data["total_cost_usd"], 2.0)
        self.assertEqual(len(data["daily_data"]), 14)

        # Validate qua Pydantic schema
        schemas.AdminTokenConsumptionResponse.model_validate(data)

    def test_04_list_mock_users_default(self):
        """Kiểm tra danh sách người dùng mặc định (/admin/mock/users)."""
        res = client.get("/admin/mock/users")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("total", data)
        self.assertIn("items", data)
        self.assertGreaterEqual(data["total"], 4)

        # Kiểm tra cấu trúc từng user item
        item = data["items"][0]
        self.assertIn("id", item)
        self.assertIn("email", item)
        self.assertIn("name", item)
        self.assertIn("role", item)
        self.assertIn("status", item)
        self.assertIn("avg_independence_score", item)
        self.assertIn("streak_days", item)

        # Validate qua Pydantic schema
        schemas.AdminUsersListResponse.model_validate(data)

    def test_05_list_mock_users_with_filters(self):
        """Kiểm tra lọc theo Role, Grade và tìm kiếm keyword."""
        # 1. Lọc Role = STUDENT
        res_student = client.get("/admin/mock/users?role=STUDENT")
        self.assertEqual(res_student.status_code, 200)
        students = res_student.json()["items"]
        for s in students:
            self.assertEqual(s["role"], "STUDENT")
            self.assertIsNotNone(s["grade"])

        # 2. Lọc Grade = 6
        res_grade = client.get("/admin/mock/users?role=STUDENT&grade=6")
        self.assertEqual(res_grade.status_code, 200)
        grade_students = res_grade.json()["items"]
        for s in grade_students:
            self.assertEqual(s["grade"], 6)

        # 3. Tìm kiếm theo tên "Kiệt"
        res_search = client.get("/admin/mock/users?search=Ki%E1%BB%87t")
        self.assertEqual(res_search.status_code, 200)
        search_items = res_search.json()["items"]
        self.assertGreaterEqual(len(search_items), 1)
        self.assertIn("Kiệt", search_items[0]["name"])

    def test_06_get_mock_user_detail(self):
        """Kiểm tra xem chi tiết 1 người dùng theo ID."""
        res = client.get("/admin/mock/users/std_1001")
        self.assertEqual(res.status_code, 200)
        user = res.json()
        self.assertEqual(user["id"], "std_1001")
        self.assertEqual(user["role"], "STUDENT")
        self.assertEqual(user["avg_independence_score"], 85)
        self.assertEqual(user["streak_days"], 7)
        self.assertIsNotNone(user["linked_parent"])
        self.assertEqual(user["linked_parent"]["email"], "hung.nguyen@example.com")

        # Thử tìm user không tồn tại -> 404
        res_404 = client.get("/admin/mock/users/unknown_user_999")
        self.assertEqual(res_404.status_code, 404)

    def test_07_patch_mock_user_status(self):
        """Kiểm tra khóa và mở khóa tài khoản người dùng."""
        # Khóa tài khoản
        res_suspend = client.patch(
            "/admin/mock/users/std_1001/status",
            json={"status": "SUSPENDED", "reason": "Vi phạm điều khoản ngôn từ"}
        )
        self.assertEqual(res_suspend.status_code, 200)
        self.assertEqual(res_suspend.json()["status"], "SUSPENDED")

        # Mở khóa lại
        res_activate = client.patch(
            "/admin/mock/users/std_1001/status",
            json={"status": "ACTIVE"}
        )
        self.assertEqual(res_activate.status_code, 200)
        self.assertEqual(res_activate.json()["status"], "ACTIVE")

    def test_08_get_mock_safety_logs_and_stats(self):
        """Kiểm tra nhật ký vi phạm an toàn và chỉ số thống kê."""
        # 1. Nhật ký
        res_logs = client.get("/admin/mock/safety/logs")
        self.assertEqual(res_logs.status_code, 200)
        logs_data = res_logs.json()
        self.assertGreaterEqual(logs_data["total"], 1)
        schemas.AdminSafetyLogsResponse.model_validate(logs_data)

        # 2. Thống kê
        res_stats = client.get("/admin/mock/safety/stats")
        self.assertEqual(res_stats.status_code, 200)
        stats_data = res_stats.json()
        self.assertEqual(stats_data["comprehension_rate_percent"], 82.4)
        self.assertEqual(stats_data["not_understood_rate_percent"], 17.6)
        self.assertGreaterEqual(len(stats_data["common_difficult_topics"]), 1)
        schemas.AdminSafetyStatsResponse.model_validate(stats_data)

    def test_09_content_topics_crud(self):
        """Kiểm tra danh mục học liệu Toán 4-9 (List, Create, Delete)."""
        # 1. Danh sách chủ đề
        res_list = client.get("/admin/mock/content/topics?grade=5")
        self.assertEqual(res_list.status_code, 200)
        topics = res_list.json()["items"]
        for t in topics:
            self.assertEqual(t["grade"], 5)

        # 2. Thêm chủ đề mới
        new_topic_payload = {
            "grade": 6,
            "title": "Chủ đề thử nghiệm hình học",
            "description": "Mô tả bài học thử nghiệm",
            "problem_count": 10,
            "is_enabled": True
        }
        res_create = client.post("/admin/mock/content/topics", json=new_topic_payload)
        self.assertEqual(res_create.status_code, 201)
        created = res_create.json()
        created_id = created["id"]
        self.assertEqual(created["title"], new_topic_payload["title"])

        # 3. Xóa chủ đề
        res_delete = client.delete(f"/admin/mock/content/topics/{created_id}")
        self.assertEqual(res_delete.status_code, 204)

    def test_10_settings_get_and_update(self):
        """Kiểm tra cấu hình tham số AI hệ thống."""
        # 1. Xem cấu hình hiện tại
        res_get = client.get("/admin/mock/settings")
        self.assertEqual(res_get.status_code, 200)
        settings = res_get.json()
        self.assertEqual(settings["model_name"], "gemini-1.5-flash")
        self.assertEqual(settings["system_version"], "v1.4.0")

        # 2. Cập nhật nhiệt độ temperature
        settings["temperature"] = 0.5
        res_put = client.put("/admin/mock/settings", json=settings)
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["temperature"], 0.5)

        # Revert lại 0.4
        settings["temperature"] = 0.4
        client.put("/admin/mock/settings", json=settings)


if __name__ == "__main__":
    unittest.main()
