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
