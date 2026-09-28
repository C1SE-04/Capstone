import json
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

import models
from router import agent_router
from chat_utils import get_recent_chat_context
from agents.orchestrator import _agent

# ==========================================
# CẤU HÌNH NGƯỠNG HINT (Task #107)
# ==========================================
# Sau bao nhiêu lần sai liên tiếp thì bắt đầu cho hint thay vì hỏi Socratic
WRONG_BEFORE_HINT = 3
# Tổng số hint tối đa trước khi hệ thống tự đưa đáp án luôn
MAX_HINTS = 2
# Tổng ngưỡng: WRONG_BEFORE_HINT + MAX_HINTS = số lần sai để lộ đáp án
# VD: 3 sai → hint 1, 4 sai → hint 2, 5 sai → lộ đáp án


def get_teaching_mode(consecutive_wrong: int, hint_count: int) -> str:
    """
    Xác định chế độ dạy học dựa trên số lần sai và số hint đã cho.
    Returns:
        "socratic"  - hỏi gợi mở Socratic (0 đến WRONG_BEFORE_HINT-1 lần sai)
        "hint"      - đưa ra gợi ý trực tiếp (WRONG_BEFORE_HINT đến MAX_HINTS lần)
        "reveal"    - tiết lộ đáp án (đã hết hint)
    """
    if consecutive_wrong < WRONG_BEFORE_HINT:
        return "socratic"
    elif hint_count < MAX_HINTS:
        return "hint"
    else:
        return "reveal"


def build_teaching_instruction(mode: str, consecutive_wrong: int, hint_count: int) -> str:
    """
    Xây dựng chỉ đạo sư phạm phù hợp với chế độ dạy học hiện tại.
    Instruction này sẽ được nhồi vào task_description gửi cho AI.
    """
    if mode == "socratic":
        return (
            f"[Chế độ Socratic - Sai {consecutive_wrong} lần] "
            "Tiếp tục đặt câu hỏi gợi mở, TUYỆT ĐỐI không đưa đáp án. "
            "Câu hỏi phải nhỏ hơn, cụ thể hơn bước trước."
        )
    elif mode == "hint":
        return (
            f"[Chế độ Hint #{hint_count + 1}/{MAX_HINTS} - Sai {consecutive_wrong} lần] "
            "Học sinh đã sai nhiều lần. Thầy hãy đưa ra MỘT GỢI Ý CỤ THỂ (hint), "
            "tiết lộ một phần nhỏ của bước giải mà không nói thẳng đáp án. "
            "Ví dụ: 'Thầy gợi ý: hãy thử chia cả 2 vế cho 2 xem sao em.' "
            "Ngắn gọn, 1-2 câu."
        )
    else:  # reveal
        return (
            f"[Chế độ Tiết lộ đáp án - Sai {consecutive_wrong} lần, đã cho {hint_count} hint] "
            "Học sinh đã sai quá nhiều lần và đã nhận đủ hint. "
            "Thầy hãy GIẢI THÍCH TOÀN BỘ bài toán từng bước một cách rõ ràng, "
            "kết thúc bằng câu hỏi 'Em có hiểu cách làm này chưa?' "
            "KHÔNG hỏi Socratic nữa, giải thẳng."
        )


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


def get_or_create_session_stats(db: Session, session_id: str) -> models.SessionStats:
    """Lấy hoặc tạo mới bộ đếm stats cho session."""
    stats = db.query(models.SessionStats).filter(
        models.SessionStats.session_id == session_id
    ).first()
    if not stats:
        stats = models.SessionStats(session_id=session_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def update_stats_on_answer(db: Session, session_id: str, answer_status: Optional[str]) -> models.SessionStats:
    """
    Cập nhật bộ đếm dựa trên kết quả trả lời của học sinh.
    - "wrong"   → tăng consecutive_wrong_count, tăng hint_count nếu đang ở chế độ hint
    - "correct" → reset consecutive_wrong_count và hint_count về 0
    - None      → không thay đổi
    """
    stats = get_or_create_session_stats(db, session_id)
    if not answer_status:
        return stats

    if answer_status == "wrong":
        stats.consecutive_wrong_count += 1
        # Xác định chế độ trước khi tăng hint_count
        mode = get_teaching_mode(stats.consecutive_wrong_count, stats.hint_count)
        if mode == "hint":
            stats.hint_count += 1
        print(
            f"[Stats] Session {session_id}: sai lan {stats.consecutive_wrong_count} "
            f"| hint {stats.hint_count}/{MAX_HINTS} | mode={mode}"
        )
    elif answer_status == "correct":
        print(f"[Stats] Session {session_id}: DUNG → reset wrong={stats.consecutive_wrong_count}, hint={stats.hint_count}")
        stats.consecutive_wrong_count = 0
        stats.hint_count = 0

    db.commit()
    db.refresh(stats)
    return stats


def process_query_with_orchestrator(
    user_query: str,
    session_id: str,
    db: Session,
    background_tasks: BackgroundTasks,
    problem_context: Optional[dict] = None,
    answer_status: Optional[str] = None,
):
    """
    Wrapper nối OrchestratorAgent với FastAPI.

    Luồng xử lý:
    1. Lưu tin nhắn vào DB.
    2. Cập nhật bộ đếm sai/đúng (Task #106).
    3. Xác định teaching_mode dựa trên bộ đếm (Task #107):
       - socratic: hỏi gợi mở (mặc định)
       - hint: gợi ý cụ thể sau WRONG_BEFORE_HINT lần sai
       - reveal: tiết lộ đáp án sau MAX_HINTS gợi ý
    4. Gọi AI với instruction phù hợp.
    5. Nếu mode="reveal" hoặc answer_status="correct": yield ask_comprehension.
    """
    history_text = ""
    stats = None
    teaching_mode = "socratic"

    if session_id:
        # 1. Lưu tin nhắn của học sinh vào Database
        user_msg = models.Message(session_id=session_id, sender_type="USER", content=user_query)
        db.add(user_msg)
        db.commit()

        # 2. Cập nhật bộ đếm
        stats = update_stats_on_answer(db, session_id, answer_status)

        # 3. Xác định chế độ dạy học hiện tại
        teaching_mode = get_teaching_mode(stats.consecutive_wrong_count, stats.hint_count)

        # 4. Lấy lịch sử ngữ cảnh
        chat_history = get_recent_chat_context(db, session_id, limit=5)
        history_text = "\n".join([f"[{msg['role'].upper()}]: {msg['parts'][0]}" for msg in chat_history])

    # 5. Phân luồng qua Orchestrator (Trụ 1 - StateMachine)
    result = _agent.route_sync(
        latest_message=user_query,
        history_text=history_text,
        problem_context=problem_context,
    )

    selected = result["selected_agent"]
    target_agent = selected if selected.endswith("_AGENT") else selected + "_AGENT"
    reason = result["routing_scratchpad"]
    task_description = result.get("task_description", "")

    # 6. Nhồi thêm chỉ đạo sư phạm vào task_description (Task #107)
    hint_instruction = build_teaching_instruction(
        teaching_mode,
        stats.consecutive_wrong_count if stats else 0,
        stats.hint_count if stats else 0,
    )
    enriched_task_description = f"{hint_instruction}\n\n{task_description}"

    print(f"[Orchestrator] {target_agent} | mode={teaching_mode} | wrong={stats.consecutive_wrong_count if stats else 0}")

    # Lưu log ngầm
    background_tasks.add_task(save_orchestrator_log, db, user_query, target_agent, reason)

    # Yield event orchestrator (kèm stats và teaching_mode để FE debug)
    decision = {
        "target_agent": target_agent,
        "reason": reason,
        "teaching_mode": teaching_mode,
        "stats": {
            "consecutive_wrong_count": stats.consecutive_wrong_count if stats else 0,
            "hint_count": stats.hint_count if stats else 0,
            "not_understood_count": stats.not_understood_count if stats else 0,
        }
    }
    yield f"event: orchestrator\ndata: {json.dumps(decision, ensure_ascii=False)}\n\n"

    # Gọi AI stream với enriched_task_description
    full_reply = ""
    for chunk in agent_router(target_agent, enriched_task_description, history_text, user_query):
        full_reply += chunk
        yield f"event: message\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

    # Lưu phản hồi AI vào DB
    if full_reply and session_id:
        ai_msg = models.Message(session_id=session_id, sender_type="AGENT_TUTOR", content=full_reply)
        db.add(ai_msg)
        db.commit()

    # Trigger hỏi "Đã hiểu / Chưa hiểu" khi:
    # - Học sinh trả lời đúng (answer_status="correct"), HOẶC
    # - Hệ thống vừa reveal đáp án (teaching_mode="reveal")
    should_ask_comprehension = (answer_status == "correct") or (teaching_mode == "reveal")
    if should_ask_comprehension:
        comprehension_event = {
            "trigger": "correct_answer" if answer_status == "correct" else "auto_reveal",
            "message": "Hoi hoc sinh da hieu chua",
            "stats": {
                "consecutive_wrong_count": stats.consecutive_wrong_count if stats else 0,
                "hint_count": stats.hint_count if stats else 0,
                "not_understood_count": stats.not_understood_count if stats else 0,
            }
        }
        yield f"event: ask_comprehension\ndata: {json.dumps(comprehension_event, ensure_ascii=False)}\n\n"

    yield "event: done\ndata: {}\n\n"


def process_comprehension_response(
    session_id: str,
    understood: bool,
    db: Session,
):
    """
    Xử lý khi học sinh bấm 'Đã hiểu' hoặc 'Chưa hiểu' (Task #106).
    - understood=True  → ghi nhận, trả về ack.
    - understood=False → tăng not_understood_count, AI giải thích lại theo cách khác.
    """
    stats = get_or_create_session_stats(db, session_id)

    if understood:
        print(f"[Stats] Session {session_id}: DA HIEU")
        result = {
            "message": "Hoc sinh da hieu bai!",
            "stats": {
                "consecutive_wrong_count": stats.consecutive_wrong_count,
                "hint_count": stats.hint_count,
                "not_understood_count": stats.not_understood_count,
            }
        }
        yield f"event: comprehension_ack\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
    else:
        # Tăng bộ đếm "Chưa hiểu"
        stats.not_understood_count += 1
        db.commit()
        db.refresh(stats)
        print(f"[Stats] Session {session_id}: CHUA HIEU lan {stats.not_understood_count}")

        # Lưu event vào DB để AI biết ngữ cảnh
        system_msg = models.Message(
            session_id=session_id,
            sender_type="SYSTEM",
            content=f"[Hoc sinh bam 'Chua hieu' - lan {stats.not_understood_count}]"
        )
        db.add(system_msg)
        db.commit()

        # Lấy lịch sử và cho AI giải thích lại
        chat_history = get_recent_chat_context(db, session_id, limit=6)
        history_text = "\n".join([f"[{msg['role'].upper()}]: {msg['parts'][0]}" for msg in chat_history])

        not_understood_instruction = (
            f"[Chua hieu lan thu {stats.not_understood_count}] "
            "Hoc sinh van chua hieu. "
            "Thay hay giai thich lai bang cach HOAN TOAN KHAC - "
            "dung vi du thuc te, hinh anh cu the, hoac so sanh de hieu hon. "
            "Tuyet doi khong lap lai cach giai thich cu. "
            "Ket thuc bang cau hoi kiem tra: 'Em co hieu khong?'"
        )

        yield f"event: comprehension_start\ndata: {json.dumps({'not_understood_count': stats.not_understood_count}, ensure_ascii=False)}\n\n"

        full_reply = ""
        for chunk in agent_router("SCAFFOLDING_AGENT", not_understood_instruction, history_text, not_understood_instruction):
            full_reply += chunk
            yield f"event: message\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

        if full_reply:
            ai_msg = models.Message(session_id=session_id, sender_type="AGENT_TUTOR", content=full_reply)
            db.add(ai_msg)
            db.commit()

    yield "event: done\ndata: {}\n\n"
