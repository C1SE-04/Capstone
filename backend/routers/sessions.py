from fastapi import APIRouter, Depends, status
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
    """
    new_session = models.Session(
        user_id=current_user["id"],
        title=session_data.title
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.get("/sessions", response_model=list[schemas.SessionResponse])
def get_user_sessions(
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách tất cả phòng chat (Session) của người dùng đang đăng nhập,
    sắp xếp theo thời gian cập nhật mới nhất.
    """
    from sqlalchemy.orm import joinedload
    sessions = db.query(models.Session).options(
        joinedload(models.Session.messages)
    ).filter(
        models.Session.user_id == current_user["id"]
    ).order_by(models.Session.updated_at.desc()).all()
    
    return sessions
