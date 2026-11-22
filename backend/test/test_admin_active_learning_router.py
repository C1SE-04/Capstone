"""
US 10.4 - Task T10.4.4:
Bộ kiểm thử tự động cho Router Active Learning & Endpoint Tái huấn luyện mô hình.
Chạy:
    python -m pytest backend/test/test_admin_active_learning_router.py -v
"""

import os
import sys
import unittest
import tempfile
import pathlib
from unittest.mock import patch, MagicMock
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base
from models import AuditFeedbackLog
import schemas
from routers.admin_active_learning import (
    approve_and_retrain,
    list_feedback_logs,
    reject_feedbacks,
    get_active_learning_stats,
    update_feedback_item,
    delete_feedback_item,
    _retrain_lock,
)


class TestAdminActiveLearningRouter(unittest.TestCase):
    """Kiểm thử trực tiếp logic nghiệp vụ của các endpoint trong admin_active_learning.py."""

    def setUp(self):
        # Database SQLite in-memory độc lập
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine, tables=[AuditFeedbackLog.__table__])
        self.db = self.SessionLocal()

        # Tạo file dataset CSV tạm thời cô lập hoàn toàn, không chạm vào file thật của dự án
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.temp_csv = pathlib.Path(self.tmp_dir.name) / "intent_data.csv"
        self.initial_content = "text,label\nchào thầy,SAFETY\nphân số là gì,KNOWLEDGE_TRACING\n"
        self.temp_csv.write_text(self.initial_content, encoding="utf-8")
        self.patcher_data_path = patch("routers.admin_active_learning.DATA_PATH", self.temp_csv)
        self.patcher_data_path.start()

    def tearDown(self):
        self.patcher_data_path.stop()
        self.tmp_dir.cleanup()
        self.db.close()
        Base.metadata.drop_all(bind=self.engine, tables=[AuditFeedbackLog.__table__])

    def test_01_retrain_empty_feedback_ids(self):
        """1. Kiểm tra gửi danh sách feedback_ids rỗng báo lỗi 400 Bad Request."""
        payload = schemas.RetrainRequest(feedback_ids=[])
        with self.assertRaises(Exception) as ctx:
            approve_and_retrain(payload=payload, db=self.db)
        self.assertIn("không được để trống", str(ctx.exception.detail))

    def test_02_retrain_nonexistent_or_not_pending_ids(self):
        """2. Kiểm tra gửi ID không tồn tại hoặc không ở trạng thái PENDING báo lỗi 400."""
        # Thêm 1 bản ghi đã duyệt sẵn
        log_approved = AuditFeedbackLog(
            user_query="câu đã duyệt",
            predicted_agent="SCAFFOLDING",
            suggested_agent="MISCONCEPTION",
            status="APPROVED",
        )
        self.db.add(log_approved)
        self.db.commit()

        payload = schemas.RetrainRequest(feedback_ids=[999, log_approved.id])
        with self.assertRaises(Exception) as ctx:
            approve_and_retrain(payload=payload, db=self.db)
        self.assertIn("Không tìm thấy bản ghi chờ duyệt", str(ctx.exception.detail))

    @patch("routers.admin_active_learning._agent.reload_model", return_value=True)
    @patch("routers.admin_active_learning.build_pipeline")
    @patch("routers.admin_active_learning.joblib.dump")
    @patch("routers.admin_active_learning.pd.read_csv")
    @patch("routers.admin_active_learning.pd.DataFrame.to_csv")
    def test_03_retrain_success_pipeline(self, mock_to_csv, mock_read_csv, mock_dump, mock_pipeline, mock_reload):
        """3. Kiểm tra chu trình tái huấn luyện trọn gói thành công."""
        # Chuẩn bị dữ liệu mẫu PENDING
        log1 = AuditFeedbackLog(
            user_query="nhân 2 phân số là nhân chéo hả thầy",
            predicted_agent="SCAFFOLDING",
            suggested_agent="MISCONCEPTION",
            status="PENDING",
        )
        log2 = AuditFeedbackLog(
            user_query="định nghĩa số hữu tỉ là gì",
            predicted_agent="SCAFFOLDING",
            suggested_agent="KNOWLEDGE_TRACING",
            status="PENDING",
        )
        self.db.add_all([log1, log2])
        self.db.commit()

        # Mock dữ liệu huấn luyện bằng DataFrame thật (có ít nhất 2 nhãn khác nhau)
        mock_read_csv.return_value = pd.DataFrame([
            {"text": "nhân 2 phân số là nhân chéo hả thầy", "label": "MISCONCEPTION"},
            {"text": "định nghĩa số hữu tỉ là gì", "label": "KNOWLEDGE_TRACING"},
            {"text": "chào thầy ạ", "label": "SAFETY"},
        ])

        mock_pipe_instance = MagicMock()
        mock_pipeline.return_value = mock_pipe_instance

        # Gọi endpoint
        payload = schemas.RetrainRequest(feedback_ids=[log1.id, log2.id])
        res = approve_and_retrain(payload=payload, db=self.db)

        # Kiểm tra phản hồi
        self.assertTrue(res.success)
        self.assertEqual(res.retrained_count, 2)
        self.assertIn("tái huấn luyện mô hình và nạp RAM thành công", res.message)

        # Kiểm tra trạng thái trong DB được chuyển sang APPROVED
        self.db.refresh(log1)
        self.db.refresh(log2)
        self.assertEqual(log1.status, "APPROVED")
        self.assertEqual(log2.status, "APPROVED")

        # Kiểm tra các hàm huấn luyện và hot-reload được gọi
        self.assertTrue(mock_pipe_instance.fit.called)
        self.assertTrue(mock_reload.called)

    def test_04_list_feedback_logs(self):
        """4. Kiểm tra lấy danh sách feedback logs và lọc theo status PENDING."""
        log1 = AuditFeedbackLog(user_query="q1", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        log2 = AuditFeedbackLog(user_query="q2", predicted_agent="SCAFFOLDING", suggested_agent="SAFETY", status="APPROVED")
        self.db.add_all([log1, log2])
        self.db.commit()

        res_pending = list_feedback_logs(status_filter="PENDING", limit=10, offset=0, db=self.db)
        self.assertEqual(res_pending.total, 1)
        self.assertEqual(res_pending.pending_count, 1)
        self.assertEqual(res_pending.items[0].user_query, "q1")

        res_all = list_feedback_logs(status_filter="ALL", limit=10, offset=0, db=self.db)
        self.assertEqual(res_all.total, 2)

    def test_05_reject_feedback_logs(self):
        """5. Kiểm tra từ chối mẫu câu lỗi và chuyển trạng thái sang REJECTED."""
        log1 = AuditFeedbackLog(user_query="spam teencode", predicted_agent="SCAFFOLDING", suggested_agent="SAFETY", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        payload = schemas.RejectFeedbacksRequest(feedback_ids=[log1.id])
        res = reject_feedbacks(payload=payload, db=self.db)

        self.assertTrue(res.success)
        self.assertEqual(res.rejected_count, 1)

        self.db.refresh(log1)
        self.assertEqual(log1.status, "REJECTED")

    @patch("routers.admin_active_learning.pd.read_csv", side_effect=Exception("Lỗi đọc dữ liệu huấn luyện"))
    @patch("routers.admin_active_learning.pd.DataFrame.to_csv")
    def test_06_retrain_rollback_on_training_failure(self, mock_to_csv, mock_read_csv):
        """6. Kiểm tra an toàn dữ liệu: Rollback DB nếu xảy ra lỗi trong quá trình train."""
        log1 = AuditFeedbackLog(user_query="câu thử lỗi", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        payload = schemas.RetrainRequest(feedback_ids=[log1.id])
        with self.assertRaises(Exception) as ctx:
            approve_and_retrain(payload=payload, db=self.db)

        self.assertIn("Quá trình tái huấn luyện mô hình gặp sự cố", str(ctx.exception.detail))

        # Xác nhận DB được rollback an toàn, trạng thái vẫn được bảo toàn là PENDING
        self.db.refresh(log1)
        self.assertEqual(log1.status, "PENDING")

    def test_07_concurrent_retrain_conflict(self):
        """7. Kiểm tra chống xung đột tiến trình: Nếu đang có retrain chạy, request kế tiếp nhận 409 Conflict."""
        # Giả lập lock đang bị chiếm giữ bởi tiến trình khác
        _retrain_lock.acquire(blocking=False)
        try:
            payload = schemas.RetrainRequest(feedback_ids=[1])
            with self.assertRaises(Exception) as ctx:
                approve_and_retrain(payload=payload, db=self.db)
            self.assertEqual(ctx.exception.status_code, 409)
            self.assertIn("Hệ thống đang thực hiện một tiến trình tái huấn luyện", ctx.exception.detail)
        finally:
            _retrain_lock.release()

    @patch("routers.admin_active_learning.pd.read_csv")
    @patch("routers.admin_active_learning.pd.DataFrame.to_csv")
    def test_08_retrain_with_single_intent_validation(self, mock_to_csv, mock_read_csv):
        """8. Kiểm tra validation: Dữ liệu huấn luyện chỉ có 1 nhãn duy nhất bị từ chối an toàn."""
        log1 = AuditFeedbackLog(user_query="q1", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        # Mock dữ liệu chỉ có 1 nhãn duy nhất
        mock_read_csv.return_value = pd.DataFrame([
            {"text": "câu 1", "label": "MISCONCEPTION"},
            {"text": "câu 2", "label": "MISCONCEPTION"},
        ])

        payload = schemas.RetrainRequest(feedback_ids=[log1.id])
        with self.assertRaises(Exception) as ctx:
            approve_and_retrain(payload=payload, db=self.db)

        self.assertIn("tối thiểu 2 nhãn intent khác nhau", str(ctx.exception.detail))
        self.db.refresh(log1)
        self.assertEqual(log1.status, "PENDING")

    @patch("routers.admin_active_learning.pd.read_csv", side_effect=Exception("Lỗi ép buộc trong quá trình fit mô hình"))
    def test_09_csv_truncation_rollback_with_temp_file(self, mock_read_csv):
        """9. Kiểm tra file CSV được truncate đúng kích thước ban đầu nếu quá trình train bị lỗi."""
        orig_size = self.temp_csv.stat().st_size

        log1 = AuditFeedbackLog(
            user_query="câu cần thử rollback file",
            predicted_agent="SCAFFOLDING",
            suggested_agent="MISCONCEPTION",
            status="PENDING",
        )
        self.db.add(log1)
        self.db.commit()

        payload = schemas.RetrainRequest(feedback_ids=[log1.id])
        with self.assertRaises(Exception):
            approve_and_retrain(payload=payload, db=self.db)

        # Xác nhận kích thước file CSV và nội dung được truncate về đúng ban đầu
        self.assertEqual(self.temp_csv.stat().st_size, orig_size)
        self.assertEqual(self.temp_csv.read_text(encoding="utf-8"), self.initial_content)

    def test_10_get_active_learning_stats(self):
        """10. Kiểm tra endpoint GET /stats trả về đầy đủ các chỉ số thống kê."""
        log1 = AuditFeedbackLog(user_query="q1", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        log2 = AuditFeedbackLog(user_query="q2", predicted_agent="SCAFFOLDING", suggested_agent="SAFETY", status="APPROVED")
        log3 = AuditFeedbackLog(user_query="q3", predicted_agent="SCAFFOLDING", suggested_agent="SAFETY", status="REJECTED")
        self.db.add_all([log1, log2, log3])
        self.db.commit()

        stats = get_active_learning_stats(db=self.db)
        self.assertTrue(stats.success)
        self.assertEqual(stats.total_feedbacks, 3)
        self.assertEqual(stats.pending_count, 1)
        self.assertEqual(stats.approved_count, 1)
        self.assertEqual(stats.rejected_count, 1)
        self.assertEqual(stats.total_training_samples, 2)  # Trong self.temp_csv có 2 dòng
        self.assertIn("SAFETY", stats.intents_distribution)

    def test_11_search_and_filter_feedbacks(self):
        """11. Kiểm tra tìm kiếm từ khóa và lọc theo agent trong GET /feedbacks."""
        log1 = AuditFeedbackLog(user_query="nhân hai phân số khó quá", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        log2 = AuditFeedbackLog(user_query="định nghĩa số tự nhiên", predicted_agent="SCAFFOLDING", suggested_agent="KNOWLEDGE_TRACING", status="PENDING")
        self.db.add_all([log1, log2])
        self.db.commit()

        # Tìm kiếm theo từ khóa "phân số"
        res_search = list_feedback_logs(status_filter="PENDING", search="phân số", db=self.db)
        self.assertEqual(res_search.total, 1)
        self.assertEqual(res_search.items[0].id, log1.id)

        # Lọc theo agent
        res_agent = list_feedback_logs(status_filter="PENDING", agent_filter="KNOWLEDGE_TRACING", db=self.db)
        self.assertEqual(res_agent.total, 1)
        self.assertEqual(res_agent.items[0].id, log2.id)

    def test_12_update_feedback_item_success(self):
        """12. Kiểm tra hiệu chỉnh câu hỏi và nhãn đề xuất (PUT /feedbacks/{id})."""
        log1 = AuditFeedbackLog(user_query="câu sai chính tả", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        payload = schemas.UpdateFeedbackRequest(
            user_query="câu đã sửa chuẩn tiếng Việt",
            suggested_agent="SAFETY",
        )
        updated = update_feedback_item(feedback_id=log1.id, payload=payload, db=self.db)
        self.assertEqual(updated.user_query, "câu đã sửa chuẩn tiếng Việt")
        self.assertEqual(updated.suggested_agent, "SAFETY")

        self.db.refresh(log1)
        self.assertEqual(log1.user_query, "câu đã sửa chuẩn tiếng Việt")
        self.assertEqual(log1.suggested_agent, "SAFETY")

    def test_13_update_feedback_item_invalid_agent(self):
        """13. Kiểm tra sửa nhãn không hợp lệ báo lỗi 400."""
        log1 = AuditFeedbackLog(user_query="câu 1", predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        payload = schemas.UpdateFeedbackRequest(suggested_agent="INVALID_AGENT_XYZ")
        with self.assertRaises(Exception) as ctx:
            update_feedback_item(feedback_id=log1.id, payload=payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("không hợp lệ", ctx.exception.detail)

    def test_14_update_feedback_item_not_found(self):
        """14. Kiểm tra sửa bản ghi không tồn tại báo lỗi 404."""
        payload = schemas.UpdateFeedbackRequest(suggested_agent="SAFETY")
        with self.assertRaises(Exception) as ctx:
            update_feedback_item(feedback_id=99999, payload=payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_15_delete_feedback_item_success_and_not_found(self):
        """15. Kiểm tra xóa bản ghi DELETE /feedbacks/{id}."""
        log1 = AuditFeedbackLog(user_query="câu rác", predicted_agent="SCAFFOLDING", suggested_agent="SAFETY", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        res = delete_feedback_item(feedback_id=log1.id, db=self.db)
        self.assertTrue(res.success)
        self.assertEqual(res.deleted_id, log1.id)

        # Kiểm tra không còn tồn tại trong DB
        check_item = self.db.query(AuditFeedbackLog).filter(AuditFeedbackLog.id == log1.id).first()
        self.assertIsNone(check_item)

        # Xóa lại lần nữa -> 404
        with self.assertRaises(Exception) as ctx:
            delete_feedback_item(feedback_id=log1.id, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("routers.admin_active_learning._agent.reload_model", return_value=True)
    @patch("routers.admin_active_learning.build_pipeline")
    @patch("routers.admin_active_learning.joblib.dump")
    @patch("routers.admin_active_learning.pd.read_csv")
    def test_16_retrain_query_length_clamping(self, mock_read_csv, mock_dump, mock_pipeline, mock_reload):
        """16. Kiểm tra câu hỏi quá dài (>1000 ký tự) được tự động cắt ngắn an toàn khi nạp huấn luyện."""
        huge_query = "toán học " * 200  # ~1600 ký tự
        log1 = AuditFeedbackLog(user_query=huge_query, predicted_agent="SCAFFOLDING", suggested_agent="MISCONCEPTION", status="PENDING")
        self.db.add(log1)
        self.db.commit()

        mock_read_csv.return_value = pd.DataFrame([
            {"text": "câu 1", "label": "MISCONCEPTION"},
            {"text": "câu 2", "label": "SAFETY"},
        ])
        mock_pipe_instance = MagicMock()
        mock_pipeline.return_value = mock_pipe_instance

        payload = schemas.RetrainRequest(feedback_ids=[log1.id])
        res = approve_and_retrain(payload=payload, db=self.db)
        self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
