from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, dependencies
from database import get_db

router = APIRouter(tags=["Sessions"])

@router.post("/sessions", response_model=schemas.SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: schemas.SessionCreate,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Tạo một phòng chat (Session) mới cho người dùng đang đăng nhập.
    Quản trị viên (ADMIN) không được phép tham gia chat.
    """
    if current_user.get("role") == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản Quản trị viên không thể tham gia phiên chat học sinh."
        )
    new_session = models.Session(
        user_id=current_user["id"],
        title=session_data.title
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Task #168 & #169: Khởi tạo khoảng active ban đầu cho session mới
    from datetime import datetime, timezone
    now_utc = datetime.now(timezone.utc)
    initial_interval = models.SessionActiveInterval(
        session_id=new_session.id,
        user_id=current_user["id"],
        start_time=now_utc,
        end_time=now_utc,
        active_seconds=0,
    )
    db.add(initial_interval)
    db.commit()

    return new_session


@router.get("/sessions", response_model=list[schemas.SessionResponse])
def get_user_sessions(
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách tất cả phòng chat (Session) của người dùng đang đăng nhập,
    sắp xếp theo thời gian cập nhật mới nhất. Quản trị viên không có session chat.
    """
    if current_user.get("role") == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản Quản trị viên không có phiên chat học sinh."
        )

    from sqlalchemy.orm import joinedload
    sessions = db.query(models.Session).options(
        joinedload(models.Session.messages)
    ).filter(
        models.Session.user_id == current_user["id"]
    ).order_by(models.Session.updated_at.desc()).all()
    
    return sessions


@router.get("/sessions/{session_id}", response_model=schemas.SessionResponse)
def get_session_detail(
    session_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy chi tiết một phòng chat (Session) kèm danh sách tin nhắn.
    Dùng cho tính năng Xem lại đoạn chat trong Sổ tay bài toán và Dashboard.
    """
    from sqlalchemy.orm import joinedload
    session = db.query(models.Session).options(
        joinedload(models.Session.messages)
    ).filter(
        models.Session.id == session_id
    ).first()

    if not session:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng chat.")

    user_id = current_user["id"]
    role = current_user.get("role")
    if session.user_id != user_id:
        if role in ("PARENT", "MONITOR"):
            link = db.query(models.ParentStudentLink).filter(
                models.ParentStudentLink.parent_id == user_id,
                models.ParentStudentLink.student_id == session.user_id,
            ).first()
            if not link:
                from fastapi import HTTPException
                raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập phòng chat này.")
        else:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập phòng chat này.")

    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: str,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Xóa một phòng chat (Session) và toàn bộ tin nhắn bên trong.
    """
    if current_user.get("role") == "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản Quản trị viên không thể thao tác trên phiên chat."
        )

    session = db.query(models.Session).filter(
        models.Session.id == session_id,
        models.Session.user_id == current_user["id"]
    ).first()
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng chat hoặc không có quyền truy cập.")
        
    # Xóa các bản ghi liên quan trước khi xóa session để tránh lỗi ForeignKey / NotNullViolation
    db.query(models.SessionActiveInterval).filter(models.SessionActiveInterval.session_id == session.id).delete()
    db.query(models.IndependenceScore).filter(models.IndependenceScore.session_id == session.id).delete()
    db.query(models.SessionStats).filter(models.SessionStats.session_id == session.id).delete()
    db.query(models.Message).filter(models.Message.session_id == session.id).delete()

    db.delete(session)
    db.commit()
    return None
