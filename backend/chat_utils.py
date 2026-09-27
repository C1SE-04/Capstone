from sqlalchemy.orm import Session
import models

def get_recent_chat_context(db: Session, session_id: str, limit: int = 5) -> list[dict]:
    """
    Lấy n tin nhắn gần nhất của một phòng chat, đảo ngược theo thứ tự thời gian
    và format lại cho đúng chuẩn mảng JSON của Gemini.
    """
    # 1. Truy vấn n tin nhắn mới nhất
    messages = (
        db.query(models.Message)
        .filter(models.Message.session_id == session_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()
    )
    
    # 2. Đảo ngược lại (cũ -> mới) để đọc theo mạch thời gian
    messages.reverse()
    
    # 3. Format lại thành mảng cho Gemini
    formatted_context = []
    for msg in messages:
        # Nếu là USER thì role là user, nếu là AGENT thì role là model
        role = "user" if msg.sender_type == "USER" else "model"
        formatted_context.append({
            "role": role,
            "parts": [msg.content]
        })
        
    return formatted_context
