import json
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

import models
from router import agent_router
from chat_utils import get_recent_chat_context
from agents.orchestrator import _agent
from sqlalchemy.sql import func
from routers.metrics import update_session_active_interval

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


def save_orchestrator_log(
    db: Session,
    user_query: str,
    target_agent: str,
    reason: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    notify_parent: bool = False,
):
    """Lưu lịch sử quyết định của Orchestrator vào DB (chạy background)."""
    try:
        new_log = models.OrchestratorLog(
            user_query=user_query,
            target_agent=target_agent,
            reason=reason,
            session_id=session_id,
            user_id=user_id,
            notify_parent=notify_parent,
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving orchestrator log: {e}")


def save_audit_feedback_log(
    db: Optional[Session] = None,
    user_query: str = "",
    predicted_agent: str = "",
    suggested_agent: str = "",
):
    """
    US 10.4 (Task T10.4.2):
    Ghi nhận câu hỏi bị phân luồng sai vào bảng audit_feedback_logs ở trạng thái PENDING.
    
    Cải tiến kiểm soát chất lượng dữ liệu:
    1. Kiểm tra rỗng và cắt tỉa whitespace.
    2. Chống trùng lặp nhãn ban đầu (Anti-Echo Tagging).
    3. Whitelist 4 nhãn Agent hợp lệ.
    4. Chống spam bản ghi trùng lặp (Deduplication) khi câu hỏi đã có sẵn ở trạng thái PENDING.
    5. An toàn luồng/kết nối DB: Tự động khởi tạo và đóng SessionLocal nếu db=None trong BackgroundTasks.
    """
    if not user_query or not user_query.strip():
        return
        
    clean_query = user_query.strip()
    clean_predicted = predicted_agent.replace("_AGENT", "").strip().upper()
    clean_suggested = suggested_agent.replace("_AGENT", "").strip().upper()

    # 1. Chống Echo Tagging
    if clean_suggested == clean_predicted:
        return

    # 2. Whitelist 4 Agent hợp lệ
    from router import VALID_AUDIT_AGENTS
    if clean_suggested not in VALID_AUDIT_AGENTS:
        return

    should_close = False
    session = db
    if session is None:
        from database import SessionLocal
        session = SessionLocal()
        should_close = True

    try:
        # 3. Chống trùng lặp bản ghi PENDING (Deduplication)
        existing = (
            session.query(models.AuditFeedbackLog)
            .filter(
                models.AuditFeedbackLog.user_query == clean_query,
                models.AuditFeedbackLog.predicted_agent == clean_predicted,
                models.AuditFeedbackLog.suggested_agent == clean_suggested,
                models.AuditFeedbackLog.status == "PENDING",
            )
            .first()
        )
        if existing:
            print(f"[ActiveLearning] [INFO] Đã tồn tại bản ghi PENDING cho câu hỏi: '{clean_query[:35]}...', bỏ qua trùng lặp.")
            return

        feedback_log = models.AuditFeedbackLog(
            user_query=clean_query,
            predicted_agent=clean_predicted,
            suggested_agent=clean_suggested,
            status="PENDING",
        )
        session.add(feedback_log)
        session.commit()
        print(f"[ActiveLearning] [SUCCESS] Đã ghi nhận câu hỏi phân luồng sai vào audit_feedback_logs: '{clean_query[:40]}' ({clean_predicted} -> {clean_suggested})")
    except Exception as e:
        session.rollback()
        print(f"[ActiveLearning] Lỗi lưu audit_feedback_logs: {e}")
    finally:
        if should_close and session is not None:
            session.close()


def update_stats_on_answer(db: Session, session_id: str, answer_status: Optional[str]):
    """
    Cập nhật số lần trả lời sai liên tiếp và số lần hint.
    - "wrong"   → wrong_count += 1, nếu đang ở mode hint thì hint_count += 1
    - "correct" → reset cả hai về 0
    - None      → không thay đổi

    Trả về: (stats, computed_mode)
    - computed_mode là mode đã được tính TRƯỚC KHI tăng hint_count.
      Dùng giá trị này ở tầng ngoài để tránh tính lại 2 lần (bug double-computation).
    """
    stats = get_or_create_session_stats(db, session_id)
    if not answer_status:
        return stats, None

    computed_mode = None
    if answer_status == "wrong":
        stats.consecutive_wrong_count += 1
        # Tính mode TRƯỚC khi tăng hint_count — đây là mode thực sự của lượt này
        computed_mode = get_teaching_mode(stats.consecutive_wrong_count, stats.hint_count)
        if computed_mode == "hint":
            stats.hint_count += 1
        print(
            f"[Stats] Session {session_id}: sai lan {stats.consecutive_wrong_count} "
            f"| hint {stats.hint_count}/{MAX_HINTS} | mode={computed_mode}"
        )
    elif answer_status == "correct":
        print(f"[Stats] Session {session_id}: DUNG → reset wrong={stats.consecutive_wrong_count}, hint={stats.hint_count}")
        stats.consecutive_wrong_count = 0
        stats.hint_count = 0
        computed_mode = "socratic"  # Sau khi đúng luôn reset về socratic

    db.commit()
    db.refresh(stats)
    return stats, computed_mode


def process_query_with_orchestrator(
    user_query: str,
    session_id: str,
    db: Session,
    background_tasks: BackgroundTasks,
    problem_context: Optional[dict] = None,
    answer_status: Optional[str] = None,
    grade_level: Optional[int] = None,  
    attachment_url: Optional[str] = None,  # US 6.4: URL ảnh Cloudinary
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

    session_user_id = None
    if session_id:
        # 1. Lưu tin nhắn của học sinh vào Database
        user_msg = models.Message(session_id=session_id, sender_type="USER", content=user_query, attachment_url=attachment_url)
        db.add(user_msg)
        
        # Cập nhật updated_at của session
        session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session_obj:
            session_obj.updated_at = func.now()
            session_user_id = session_obj.user_id
            
        db.commit()

        # Task #168 & #169: Cập nhật khoảng active khi học sinh gửi tin nhắn
        try:
            update_session_active_interval(db, session_id)
        except Exception:
            pass

        # 2. Cập nhật bộ đếm
        stats, computed_mode = update_stats_on_answer(db, session_id, answer_status)

        # 3. Xác định chế độ dạy học hiện tại
        # Dùng computed_mode từ bên trong hàm update_stats_on_answer (đã tính TRƯỚC khi hint_count tăng)
        # để tránh bug double-computation: nếu tính lại ở đây, hint_count đã bị tăng → sai mode
        if computed_mode is not None:
            teaching_mode = computed_mode
        else:
            teaching_mode = get_teaching_mode(stats.consecutive_wrong_count, stats.hint_count)

        # 4. Lấy lịch sử ngữ cảnh (loại trừ chính tin nhắn vừa lưu để xác định đúng ngữ cảnh trước đó)
        chat_history = get_recent_chat_context(db, session_id, limit=6)
        prev_messages = [
            msg for msg in chat_history 
            if not (msg["role"] == "user" and msg["parts"][0] == user_query)
        ]
        history_text = "\n".join([f"[{msg['role'].upper()}]: {msg['parts'][0]}" for msg in prev_messages])

        # 4b. Lấy toàn bộ các ảnh bài toán mà học sinh đã gửi trong phiên học này (tối đa 3 ảnh gần nhất)
        session_images_query = (
            db.query(models.Message.attachment_url)
            .filter(
                models.Message.session_id == session_id,
                models.Message.sender_type == "USER",
                models.Message.attachment_url.isnot(None),
                models.Message.attachment_url != "",
            )
            .order_by(models.Message.created_at.asc())
            .all()
        )
        session_image_urls = []
        for (img_url,) in session_images_query:
            if img_url and img_url not in session_image_urls:
                session_image_urls.append(img_url)

        if len(session_image_urls) > 3:
            session_image_urls = session_image_urls[-3:]
    else:
        session_image_urls = [attachment_url] if attachment_url else []

    # 5. Phân luồng qua Orchestrator (Trụ 1 - StateMachine)
    result = _agent.route_sync(
        latest_message=user_query,
        history_text=history_text,
        problem_context=problem_context,
        student_grade=grade_level,
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

    # US 8.1: Kiểm tra xem đề bài học sinh vừa gửi có trùng 100% với bài đã giải trước đó không
    is_exact_duplicate = False
    if session_user_id and session_user_id != "guest-user-id":
        try:
            from deduplication import compute_problem_hash, is_likely_problem_text
            if is_likely_problem_text(user_query):
                query_hash = compute_problem_hash(user_query)
                prev_solved = (
                    db.query(models.IndependenceScore)
                    .filter(
                        models.IndependenceScore.student_id == session_user_id,
                        models.IndependenceScore.problem_hash == query_hash,
                    )
                    .first()
                )
                if prev_solved:
                    is_exact_duplicate = True
                    dup_instruction = (
                        "[CHỈ ĐẠO SƯ PHẠM ĐẶC BIỆT - BÀI TOÁN ĐÃ TỪNG HOÀN THÀNH TRƯỚC ĐÓ]:\n"
                        "Học sinh đang gửi lại một bài toán mà em đã từng giải đúng và hoàn thành trước đó!\n"
                        "YÊU CẦU BẮT BUỘC:\n"
                        "1. Hãy MỞ ĐẦU câu trả lời bằng một lời khen và câu nhắc nhở nhẹ nhàng, ấm áp: "
                        "'Thầy thấy bài toán này em đã từng giải rất tốt rồi đó! Lần này em muốn tự luyện tập lại để ôn tập, hay muốn thầy ra một bài toán nâng cao hơn để thử sức nhé?'.\n"
                        "2. Sau đó nếu học sinh vẫn muốn giải bài này, hãy dẫn dắt Socratic như bình thường."
                    )
                    enriched_task_description = f"{dup_instruction}\n\n{enriched_task_description}"
        except Exception as e:
            print(f"[Deduplication Check Error] {e}")

    emotion_flag = result.get("emotion_flag", "GUIDING")
    print(f"[Orchestrator] {target_agent} | mode={teaching_mode} | wrong={stats.consecutive_wrong_count if stats else 0} | emotion={emotion_flag} | session_images={len(session_image_urls)}")

    # Lưu log ngầm (US 8.1 - T8.7: kèm session_id, user_id, notify_parent)
    # Chỉ cảnh báo phụ huynh khi thực sự có vi phạm thô tục, xúc phạm hoặc vô lễ (emotion_flag == WARNING hoặc lý do có profan/toxic/disrespect)
    # Tuyệt đối KHÔNG báo phụ huynh khi chỉ là chào hỏi (greeting) hay trò chuyện ngoài lề (off-topic)
    is_greeting_or_offtopic = (
        emotion_flag == "GUIDING"
        or (reason and any(k in reason.lower() for k in ("greeting", "off-topic", "ngoài lề", "chào hỏi")))
    )
    is_safety_violation = (
        not is_greeting_or_offtopic
        and (
            emotion_flag == "WARNING"
            or (reason and any(k in reason.lower() for k in ("profan", "toxic", "violation", "disrespect", "vô lễ", "chửi", "hú", "shouting")))
        )
    )
    background_tasks.add_task(
        save_orchestrator_log,
        db,
        user_query,
        target_agent,
        reason,
        session_id,
        session_user_id,
        is_safety_violation,
    )

    # Yield event orchestrator (kèm stats, teaching_mode và emotion_flag để FE debug)
    decision = {
        "target_agent": target_agent,
        "reason": reason,
        "teaching_mode": teaching_mode,
        "emotion_flag": emotion_flag,
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

    # Gọi AI stream với enriched_task_description và bộ sưu tập ảnh phiên học
    full_reply = ""
    meta = {"has_comprehension": False, "suggested_agent": None}
    for chunk in agent_router(
        target_agent,
        enriched_task_description,
        history_text,
        user_query,
        expected_answer,
        grade_level=grade_level,
        attachment_url=attachment_url,
        meta=meta,
        session_image_urls=session_image_urls,
    ):
        full_reply += chunk
        yield f"event: message\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"

    # US 10.4 (Task T10.4.2): Bóc tách thẻ ẩn khỏi phản hồi trước khi lưu DB
    from router import extract_audit_tag
    clean_reply, extracted_agent = extract_audit_tag(full_reply)
    suggested_agent = meta.get("suggested_agent") or extracted_agent

    # Lưu phản hồi AI sạch vào DB Message (Học sinh & Phụ huynh không thấy thẻ ẩn)
    if clean_reply and session_id:
        ai_msg = models.Message(session_id=session_id, sender_type="AGENT_TUTOR", content=clean_reply)
        db.add(ai_msg)
        
        # Cập nhật updated_at của session
        session_obj = db.query(models.Session).filter(models.Session.id == session_id).first()
        if session_obj:
            session_obj.updated_at = func.now()
            
        db.commit()

        # Task #168: Cập nhật mốc kết thúc câu trả lời AI vào khoảng active
        try:
            update_session_active_interval(db, session_id)
        except Exception:
            pass

    # BẢO VỆ CHỐNG FALSE POSITIVE (CHÀO HỎI & NGOÀI LỀ):
    # Câu chào hỏi / xã giao thuộc trách nhiệm của SAFETY theo kiến trúc hệ thống.
    if is_greeting_or_offtopic and suggested_agent in ('SCAFFOLDING', 'SCAFFOLDING_AGENT'):
        suggested_agent = None

    # US 10.4 (Task T10.4.2): Nếu phát hiện phân luồng sai -> Ghi nhận vào audit_feedback_logs
    if suggested_agent:
        if background_tasks:
            background_tasks.add_task(
                save_audit_feedback_log,
                None,  # Để None để Background Task tự mở SessionLocal riêng, tránh lỗi closed session của FastAPI
                user_query,
                target_agent,
                suggested_agent,
            )
        else:
            save_audit_feedback_log(db, user_query, target_agent, suggested_agent)

    # Nếu Gemini nhận diện học sinh đã giải đúng bài toán:
    # 1. Chuyển emotion_flag thành CORRECT để con cú vỗ tay/vui vẻ
    # 2. Reset bộ đếm số lần sai trong session stats
    is_gemini_comprehension = meta.get("has_comprehension", False)
    if is_gemini_comprehension:
        answer_status = "correct"
        emotion_flag = "CORRECT"
        if stats:
            stats.consecutive_wrong_count = 0
            stats.hint_count = 0
            db.commit()
            print(f"[Comprehension Trigger] Gemini xác nhận hoàn thành bài toán -> Reset stats cho session {session_id}")

    # Trigger hỏi "Đã hiểu / Chưa hiểu" khi:
    # - Gemini phát hiện hoàn thành bài toán (is_gemini_comprehension), HOẶC
    # - Học sinh trả lời đúng (answer_status="correct"), HOẶC
    # - Hệ thống vừa reveal đáp án (teaching_mode="reveal")
    should_ask_comprehension = is_gemini_comprehension or (answer_status == "correct") or (teaching_mode == "reveal")
    if should_ask_comprehension:
        comprehension_event = {
            "trigger": "correct_answer" if (answer_status == "correct" or is_gemini_comprehension) else "auto_reveal",
            "message": "Hoi hoc sinh da hieu chua",
            "stats": {
                "consecutive_wrong_count": stats.consecutive_wrong_count if stats else 0,
                "hint_count": stats.hint_count if stats else 0,
                "not_understood_count": stats.not_understood_count if stats else 0,
            }
        }
        yield f"event: ask_comprehension\ndata: {json.dumps(comprehension_event, ensure_ascii=False)}\n\n"

    # Gửi emotion về FE để con cú thay đổi cử động
    EMOTION_MAP = {
        "CORRECT":  "correct",
        "WRONG":    "incorrect",
        "GUIDING":  "suggesting",
        "WARNING":  "incorrect",   # Cú lắc đầu khi học sinh dùng ngôn ngữ không phù hợp
    }
    owl_emotion = EMOTION_MAP.get(emotion_flag, "suggesting")
    print(f"[🦉 Owl] emotion_flag={emotion_flag} → owl_emotion={owl_emotion}")
    yield f"event: done\ndata: {json.dumps({'emotion': owl_emotion}, ensure_ascii=False)}\n\n"


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
        # Task #160 (US 6.1): Kích hoạt tính điểm tự lực và lưu kết quả vào DB
        from routers.independence import save_independence_score
        independence_record = save_independence_score(db=db, session_id=session_id)
        print(f"[Stats] Session {session_id}: DA HIEU -> Independence Score: {independence_record.score} ({independence_record.evaluation})")
        result = {
            "message": "Hoc sinh da hieu bai!",
            "independence": {
                "id": independence_record.id,
                "score": independence_record.score,
                "hints_used": independence_record.hints_used,
                "not_understood_count": independence_record.not_understood_count,
                "evaluation": independence_record.evaluation,
            },
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
