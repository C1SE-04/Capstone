import json
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

import models
from router import agent_router
from chat_utils import get_recent_chat_context
from agents.orchestrator import _agent


def save_orchestrator_log(db: Session, user_query: str, target_agent: str, reason: str):
    """Lưu lịch sử quyết định của Orchestrator vào DB (chạy background)."""
    try:
        new_log = models.OrchestratorLog(
            user_query=user_query,
            target_agent=target_agent,
            reason=reason
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving orchestrator log: {e}")


def process_query_with_orchestrator(
    user_query: str,
    session_id: str,
    db: Session,
    background_tasks: BackgroundTasks,
    problem_context: Optional[dict] = None,
):
    """
    Wrapper nối OrchestratorAgent với FastAPI.
    - Ghi nhận tin nhắn vào DB
    - Lấy lịch sử chat
    - Gọi route_sync() để phân luồng (0 API call).
    - Lưu log vào DB (BackgroundTask).
    - Gọi agent_router để sinh văn bản (stream).
    """
    # 1. Lưu tin nhắn của học sinh vào Database
    user_msg = models.Message(session_id=session_id, sender_type="USER", content=user_query)
    db.add(user_msg)
    db.commit()

    # 2. Lấy 5 tin nhắn ngữ cảnh (bao gồm cả tin nhắn vừa lưu)
    chat_history = get_recent_chat_context(db, session_id, limit=5)

    # Format lịch sử thành chuỗi văn bản cho AI dễ đọc
    history_text = "\n".join([f"[{msg['role'].upper()}]: {msg['parts'][0]}" for msg in chat_history])

    result = _agent.route_sync(
        latest_message=user_query,
        history_text=history_text,
        problem_context=problem_context,
    )

    # Map: "SAFETY" → "SAFETY_AGENT" (giữ tương thích với router cũ của Capstone)
    selected = result["selected_agent"]
    target_agent = selected if selected.endswith("_AGENT") else selected + "_AGENT"
    reason = result["routing_scratchpad"]
    task_description = result.get("task_description", "")

    print(f"[Orchestrator ⚡] {target_agent} | {reason}")

    # Lưu log ngầm
    background_tasks.add_task(save_orchestrator_log, db, user_query, target_agent, reason)

    # Yield quyết định của Orchestrator
    decision = {"target_agent": target_agent, "reason": reason, "debug_context": history_text}
    yield f"event: orchestrator\ndata: {json.dumps(decision, ensure_ascii=False)}\n\n"

    # Đưa sang router để sinh văn bản (stream)
    full_reply = ""
    for chunk in agent_router(target_agent, task_description, history_text, user_query):
        full_reply += chunk
        chunk_data = {"text": chunk}
        yield f"event: message\ndata: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

    # Lưu tin nhắn trả lời của AI vào Database
    if full_reply:
        ai_msg = models.Message(session_id=session_id, sender_type="AGENT_TUTOR", content=full_reply)
        db.add(ai_msg)
        db.commit()

    # Đánh dấu kết thúc
    yield "event: done\ndata: {}\n\n"
