import json
from unittest.mock import MagicMock, patch
import pytest

from router import agent_router
import orchestrator_bridge


def test_router_strips_comprehension_tag_and_sets_meta():
    """Kiểm tra router bóc tách thẻ [COMPREHENSION_CHECK] và cập nhật meta."""
    mock_response = MagicMock()
    mock_response.text = "Chính xác! Đáp án C là đơn thức duy nhất. [COMPREHENSION_CHECK]"

    with patch("router.genai.GenerativeModel") as mock_model_cls, \
         patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_instance

        meta = {"has_comprehension": False}
        stream_chunks = list(
            agent_router(
                target_agent="SCAFFOLDING_AGENT",
                task_description="Hướng dẫn học sinh",
                history_text="",
                user_query="c",
                meta=meta,
            )
        )

        full_streamed_text = "".join(stream_chunks)

        # 1. Thẻ [COMPREHENSION_CHECK] đã được bóc tách sạch sẽ khỏi văn bản hiển thị
        assert "[COMPREHENSION_CHECK]" not in full_streamed_text
        assert "Chính xác! Đáp án C là đơn thức duy nhất." in full_streamed_text

        # 2. Meta object ghi nhận has_comprehension = True
        assert meta["has_comprehension"] is True


def test_router_does_not_trigger_comprehension_when_response_ends_with_question():
    """Kiểm tra router KHÔNG trigger comprehension khi câu trả lời của AI kết thúc bằng dấu '?' (vẫn đang hỏi học sinh)."""
    mock_response = MagicMock()
    # Dù có từ 'Rất chính xác' và từ 'kết quả' nhưng kết thúc bằng câu hỏi 'không?' -> không được trigger
    mock_response.text = (
        "Rất chính xác, khi Delta > 0 thì phương trình có 2 nghiệm phân biệt. "
        "Thế còn trường hợp Delta = 0 và Delta < 0, phương trình sẽ có kết quả như thế nào, em có nhớ không?"
    )

    with patch("router.genai.GenerativeModel") as mock_model_cls, \
         patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_instance

        meta = {"has_comprehension": False}
        stream_chunks = list(
            agent_router(
                target_agent="SCAFFOLDING_AGENT",
                task_description="Hướng dẫn học sinh",
                history_text="",
                user_query="b^2 - 4ac",
                meta=meta,
            )
        )

        assert meta["has_comprehension"] is False


def test_orchestrator_bridge_emits_ask_comprehension_when_gemini_detects():
    """Kiểm tra orchestrator_bridge phát event ask_comprehension khi Gemini phát hiện."""
    db_mock = MagicMock()
    bg_tasks_mock = MagicMock()

    # Mock SessionStats
    mock_stats = MagicMock()
    mock_stats.consecutive_wrong_count = 2
    mock_stats.hint_count = 1
    mock_stats.not_understood_count = 0

    with patch("orchestrator_bridge.get_or_create_session_stats", return_value=mock_stats), \
         patch("orchestrator_bridge.update_stats_on_answer", return_value=(mock_stats, "socratic")), \
         patch("orchestrator_bridge.get_recent_chat_context", return_value=[]), \
         patch("orchestrator_bridge.update_session_active_interval"), \
         patch("orchestrator_bridge._agent.route_sync", return_value={
             "selected_agent": "SCAFFOLDING_AGENT",
             "routing_scratchpad": "test",
             "task_description": "test task",
             "emotion_flag": "GUIDING",
         }), \
         patch("orchestrator_bridge.agent_router") as mock_router:

        # Giả lập router trả về chữ và set meta["has_comprehension"] = True
        def fake_agent_router(*args, **kwargs):
            meta = kwargs.get("meta")
            if meta is not None:
                meta["has_comprehension"] = True
            yield "Chính xác! "
            yield "Đáp án C đúng rồi."

        mock_router.side_effect = fake_agent_router

        events = list(
            orchestrator_bridge.process_query_with_orchestrator(
                user_query="c",
                session_id="session-123",
                db=db_mock,
                background_tasks=bg_tasks_mock,
            )
        )

        all_events_text = "".join(events)

        # 1. Bắt buộc phải có event ask_comprehension
        assert "event: ask_comprehension" in all_events_text

        # 2. Con cú phải có emotion là correct
        assert '"emotion": "correct"' in all_events_text

        # 3. Session stats phải được reset về 0
        assert mock_stats.consecutive_wrong_count == 0
        assert mock_stats.hint_count == 0


def test_linear_equation_misconception_routing():
    """Kiểm tra Orchestrator nhận diện đúng học sinh đoán sai nghiệm phương trình tuyến tính."""
    from agents.orchestrator import _agent
    hist = "Thầy: Để tìm x trong phương trình 2x + 3 = 5, bước đầu tiên em chuyển +3 sang vế phải thì đổi dấu thế nào?"
    msg = "à là qua thành -3, đáp án x = 2"
    result = _agent.route_sync(latest_message=msg, history_text=hist)

    assert result["selected_agent"] == "MISCONCEPTION"
    assert result["emotion_flag"] == "WRONG"
    assert "2x + 3 = 5" in result["task_description"]
    assert "TUYỆT ĐỐI KHÔNG khen" in result["task_description"]


def test_router_blocks_comprehension_for_misconception_agent():
    """Kiểm tra router chặn comprehension check khi target_agent là MISCONCEPTION_AGENT."""
    mock_response = MagicMock()
    mock_response.text = "Em chuyển vế đúng nhưng đáp án x = 2 là sai rồi nhé. [COMPREHENSION_CHECK]"

    with patch("router.genai.GenerativeModel") as mock_model_cls, \
         patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
        mock_instance = MagicMock()
        mock_instance.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_instance

        meta = {"has_comprehension": False}
        stream_chunks = list(
            agent_router(
                target_agent="MISCONCEPTION_AGENT",
                task_description="Hướng dẫn sửa sai",
                history_text="",
                user_query="à là qua thành -3, đáp án x = 2",
                meta=meta,
            )
        )

        # Tag bị bóc tách nhưng meta["has_comprehension"] phải là False
        assert meta["has_comprehension"] is False


def test_reviewer_rejects_false_praise_when_student_submits_wrong_answer():
    """Kiểm tra Reviewer từ chối khi AI khen 'hoàn toàn đúng' cho đáp án sai của học sinh."""
    from agents.reviewer import LocalReviewerAgent
    reviewer = LocalReviewerAgent()

    # Bài toán đáp án đúng là '1', học sinh nộp 'x = 2', AI khen 'hoàn toàn đúng'
    review = reviewer.review(
        student_question="à là qua thành -3, đáp án x = 2",
        expected_answer="1",
        scaffolding_response="Em làm hoàn toàn đúng rồi đó!",
        has_comprehension=False,
    )

    assert review["is_approved"] is False
    assert "False Praise" in review["reasoning"] or "chưa đưa ra đáp án đúng" in review["feedback"]

