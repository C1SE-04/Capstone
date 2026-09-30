import json
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

import models
from router import agent_router
from chat_utils import get_recent_chat_context
from agents.orchestrator import _agent
from sqlalchemy.sql import func

# Các hằng số cho logic sư phạm
WRONG_BEFORE_HINT = 2 # Nếu sai <= 2 lần thì mode = socratic. Sai > 2 lần thì mode = hint
MAX_HINTS = 2         # Nếu đã gợi ý (hint) quá 2 lần mà vẫn sai thì mode = reveal

def get_or_create_session_stats(db: Session, session_id: str) -> models.SessionStats:
    stats = db.query(models.SessionStats).filter(models.SessionStats.session_id == session_id).first()
    if not stats:
        stats = models.SessionStats(session_id=session_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def get_teaching_mode(consecutive_wrong_count: int, hint_count: int) -> str:
    """
    Quyết định chế độ dạy học dựa trên số lần sai và số lần đã gợi ý.
    - Sai <= 2 lần: Hỏi gợi mở (socratic)
    - Sai > 2 lần và chưa hết gợi ý: Đưa ra gợi ý cụ thể (hint)
    - Đã hết gợi ý: Giải thẳng (reveal)
    """
    if consecutive_wrong_count <= WRONG_BEFORE_HINT:
        return "socratic"
    elif hint_count < MAX_HINTS:
        return "hint"
    else:
        return "reveal"


def build_teaching_instruction(mode: str, wrong_count: int, hint_count: int) -> str:
    """
    Tạo thêm hướng dẫn cho AI dựa trên teaching_mode.
    """
    if mode == "socratic":
        return "[Chế độ: Socratic] Học sinh đang bối rối. Hãy đặt MỘT câu hỏi gợi mở nhỏ để dẫn dắt, TUYỆT ĐỐI không giải bài."
    elif mode == "hint":
        return f"[Chế độ: Hint {hint_count + 1}/{MAX_HINTS}] Học sinh đã sai {wrong_count} lần. Hãy đưa ra gợi ý RÕ RÀNG hơn, cung cấp một phần công thức hoặc bước giải, nhưng vẫn để học sinh tự tính kết quả cuối."
    elif mode == "reveal":
        return f"[Chế độ: Reveal] Học sinh đã bế tắc (sai {wrong_count} lần, dùng hết {MAX_HINTS} gợi ý). Hãy TRÌNH BÀY LỜI GIẢI CHI TIẾT TỪNG BƯỚC cho bài toán này, ĐƯA RA KẾT QUẢ ĐÚNG và kết thúc bằng câu hỏi 'Em đã hiểu rõ từng bước làm này chưa?'"
    return ""


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


def update_stats_on_answer(db: Session, session_id: str, answer_status: Optional[str]) -> models.SessionStats:
    """
    Cập nhật số lần trả lời sai liên tiếp và số lần hint.
    - "wrong"   → wrong_count += 1, nếu đang ở mode hint thì hint_count += 1
    - "correct" → reset cả hai về 0
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
        
        # Cập nhật updated_at của session
        session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session_obj:
            session_obj.updated_at = func.now()
            
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

    # Lấy đáp án kỳ vọng từ problem_context nếu có
    expected_answer = ""
    if problem_context:
        expected_answer = str(problem_context.get("answer", problem_context.get("expected_answer", problem_context.get("correctSolution", problem_context.get("correct_solution", "")))))

    # Gọi AI stream với enriched_task_description
    full_reply = ""
    for chunk in agent_router(target_agent, enriched_task_description, history_text, user_query, expected_answer):
        full_reply += chunk
        yield f"event: message\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

    # Lưu phản hồi AI vào DB
    if full_reply and session_id:
        ai_msg = models.Message(session_id=session_id, sender_type="AGENT_TUTOR", content=full_reply)
        db.add(ai_msg)
        
        # Cập nhật updated_at của session
        session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session_obj:
            session_obj.updated_at = func.now()
            
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
    yield "event: done\ndata: {}\n\n"
