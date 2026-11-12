"""
US 10.4 - Task T10.4.3:
Bộ kiểm thử Hàm reload_model() (Atomic Swap), Out-of-process File Watcher,
Pipeline Validation, I/O Throttling & Thread-Safety.

Chạy:
    python -m pytest backend/test/test_orchestrator_reload_model.py -v
"""

import os
import sys
import time
import threading
import pathlib
import pytest
import joblib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent, _agent


def test_initial_model_loaded():
    """Kiểm tra mô hình mặc định được nạp thành công khi khởi tạo OrchestratorAgent."""
    agent = OrchestratorAgent()
    assert agent._local_model is not None, "Mô hình _local_model phải được nạp thành công"
    assert agent._last_loaded_mtime > 0, "Thời gian _last_loaded_mtime phải lớn hơn 0"
    assert agent._model_path.exists(), f"File mô hình {agent._model_path} phải tồn tại"


def test_manual_reload_model_success():
    """Kiểm tra gọi trực tiếp reload_model() thực hiện nạp lại và trả về True."""
    agent = OrchestratorAgent()
    old_mtime = agent._last_loaded_mtime

    # Gọi reload_model
    success = agent.reload_model(force=True)
    assert success is True
    assert agent._local_model is not None
    assert agent._last_loaded_mtime >= old_mtime


def test_atomic_swap_preserves_old_model_on_corrupt_file(tmp_path):
    """
    Kiểm tra tính nguyên tử (Atomic Swap):
    Nếu file mô hình mới bị hỏng (corrupt), reload_model() bắt lỗi an toàn
    và GIỮ NGUYÊN mô hình cũ đang chạy trên RAM, không làm sập server.
    """
    agent = OrchestratorAgent()
    original_model = agent._local_model
    original_path = agent._model_path

    # Tạo một file giả mạo bị hỏng nội dung
    corrupt_file = tmp_path / "corrupt_orchestrator.pkl"
    corrupt_file.write_bytes(b"INVALID_CORRUPT_PICKLE_DATA_12345" * 30)

    try:
        # Trỏ tạm thời vào file hỏng
        agent._model_path = corrupt_file
        success = agent.reload_model(force=True)

        assert success is False, "Nạp file hỏng phải trả về False"
        # Bảo toàn con trỏ mô hình cũ trên RAM
        assert agent._local_model is original_model, "Mô hình cũ trên RAM phải được bảo toàn nguyên vẹn"
    finally:
        agent._model_path = original_path


def test_reload_graceful_when_file_not_found(tmp_path):
    """Kiểm tra xử lý an toàn khi file mô hình không tồn tại (không văng exception)."""
    agent = OrchestratorAgent()
    original_model = agent._local_model
    original_path = agent._model_path

    non_existent_file = tmp_path / "not_found.pkl"
    try:
        agent._model_path = non_existent_file
        success = agent.reload_model(force=True)
        assert success is False
        assert agent._local_model is original_model
    finally:
        agent._model_path = original_path


def test_pipeline_validation_rejects_invalid_interface(tmp_path):
    """Kiểm tra Pipeline Validation: Nếu đối tượng không có predict_proba hoặc classes_ thì từ chối nạp."""
    agent = OrchestratorAgent()
    original_model = agent._local_model
    original_path = agent._model_path

    # Dump một object dictionary bình thường thay vì pipeline scikit-learn
    invalid_file = tmp_path / "invalid_obj.pkl"
    joblib.dump({"message": "I am not a scikit-learn model"}, invalid_file)

    try:
        agent._model_path = invalid_file
        success = agent.reload_model(force=True)
        assert success is False, "Phải từ chối đối tượng không có predict_proba"
        assert agent._local_model is original_model, "Phải giữ nguyên mô hình cũ trên RAM"
    finally:
        agent._model_path = original_path


def test_small_file_incomplete_write_rejected(tmp_path):
    """Kiểm tra từ chối file quá nhỏ (< 512 bytes) do đang ghi dở."""
    agent = OrchestratorAgent()
    original_model = agent._local_model
    original_path = agent._model_path

    small_file = tmp_path / "incomplete.pkl"
    small_file.write_bytes(b"PKL_HEADER_ONLY_123")

    try:
        agent._model_path = small_file
        success = agent.reload_model(force=True)
        assert success is False, "Phải từ chối file chưa hoàn chỉnh"
        assert agent._local_model is original_model
    finally:
        agent._model_path = original_path


def test_get_model_info_metadata():
    """Kiểm tra hàm get_model_info() trả về đầy đủ metadata phục vụ API và Dashboard."""
    agent = OrchestratorAgent()
    info = agent.get_model_info()
    assert isinstance(info, dict)
    assert info["is_loaded"] is True
    assert info["file_exists"] is True
    assert info["file_size_kb"] > 0
    assert info["last_loaded_mtime"] > 0
    assert "classes" in info
    assert set(info["classes"]) == {"SAFETY", "SCAFFOLDING", "KNOWLEDGE_TRACING", "MISCONCEPTION"}


def test_double_checked_locking_no_redundant_load():
    """Kiểm tra Double-Checked Lock: Khi force=False và mtime không đổi thì bỏ qua đọc đĩa."""
    agent = OrchestratorAgent()
    current_mtime = agent._last_loaded_mtime

    # Gọi với force=False -> Phải trả về True ngay mà không cần deserialize lại
    success = agent.reload_model(force=False)
    assert success is True
    assert agent._last_loaded_mtime == current_mtime


def test_auto_reload_on_file_mtime_change():
    """
    Kiểm tra cơ chế Out-of-process File Watcher:
    Khi mtime của file mô hình thay đổi (tiến trình ngoài ghi đè),
    lượt gọi _ml_route() kế tiếp tự động phát hiện và nạp lại mô hình.
    """
    agent = OrchestratorAgent()
    initial_mtime = agent._last_loaded_mtime

    # Giả lập tiến trình ngoài chạm vào file (chỉnh mtime tăng lên 5 giây)
    new_mtime = initial_mtime + 5.0
    os.utime(agent._model_path, (new_mtime, new_mtime))

    try:
        # Reset mtime throttle để trigger kiểm tra tức thì trong unit test
        agent._last_mtime_check_time = 0.0

        # Gọi _ml_route -> Phải tự động kích hoạt reload_model
        agent._ml_route("chào thầy ạ")
        assert agent._last_loaded_mtime == pytest.approx(new_mtime, abs=1.0)
    finally:
        # Khôi phục mtime thực tế của file
        current_real_time = time.time()
        os.utime(agent._model_path, (current_real_time, current_real_time))
        agent.reload_model(force=True)


def test_concurrent_reload_thread_safety():
    """
    Kiểm tra Thread-Safety:
    Mô phỏng 10 luồng đồng thời gọi reload_model() và gọi phân loại dự đoán,
    đảm bảo không xảy ra Race Condition hay Crash server.
    """
    agent = OrchestratorAgent()
    errors = []

    def worker_reload():
        try:
            for _ in range(5):
                ok = agent.reload_model(force=True)
                assert ok is True
                time.sleep(0.01)
        except Exception as e:
            errors.append(f"Reload Error: {e}")

    def worker_predict():
        try:
            for _ in range(10):
                res = agent._ml_route("em không hiểu bài toán này")
                assert agent._local_model is not None
                time.sleep(0.005)
        except Exception as e:
            errors.append(f"Predict Error: {e}")

    threads = []
    # 3 worker chạy reload liên tục
    for _ in range(3):
        t = threading.Thread(target=worker_reload)
        threads.append(t)
    # 7 worker chạy predict liên tục
    for _ in range(7):
        t = threading.Thread(target=worker_predict)
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Xảy ra lỗi trong môi trường đa luồng: {errors}"
