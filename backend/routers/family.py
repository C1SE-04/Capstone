from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
import string
import random
from typing import List

from database import get_db
from models import User, ParentStudentLink
import schemas
from dependencies import get_current_user

router = APIRouter(
    prefix="/family",
    tags=["Family"]
)

def generate_pairing_code() -> str:
    """Tạo mã liên kết 6 ký tự ngẫu nhiên (chữ IN HOA và số)"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@router.post("/pairing-code", response_model=schemas.PairingCodeResponse)
def generate_student_pairing_code(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Học sinh (STUDENT) gọi API này để lấy mã Pairing Code.
    Nếu chưa có, tự động tạo mới.
    """
    if current_user.get("role") != "STUDENT":
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể tạo mã liên kết.")
    
    # Lấy object User từ DB
    user_db = db.query(User).filter(User.id == current_user["id"]).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")
        
    if not user_db.pairing_code:
        # Tạo mã mới và đảm bảo không bị trùng lặp
        while True:
            new_code = generate_pairing_code()
            exists = db.query(User).filter(User.pairing_code == new_code).first()
            if not exists:
                break
                
        user_db.pairing_code = new_code
        db.commit()
        db.refresh(user_db)
        
    return {"pairing_code": user_db.pairing_code}

@router.post("/link-student", response_model=schemas.LinkedStudentResponse)
def link_student_to_parent(
    request: schemas.LinkStudentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Phụ huynh (MONITOR) nhập Pairing Code để liên kết với học sinh.
    """
    if current_user.get("role") != "MONITOR":
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới có thể liên kết học sinh.")
        
    # Tìm học sinh bằng pairing code
    student = db.query(User).filter(User.pairing_code == request.pairing_code, User.role == "STUDENT").first()
    if not student:
        raise HTTPException(status_code=404, detail="Mã liên kết không hợp lệ hoặc không tồn tại.")
        
    # Kiểm tra xem đã liên kết chưa
    existing_link = db.query(ParentStudentLink).filter(
        ParentStudentLink.parent_id == current_user["id"],
        ParentStudentLink.student_id == student.id
    ).first()
    
    if existing_link:
        raise HTTPException(status_code=400, detail="Bạn đã liên kết với học sinh này rồi.")
        
    # Tạo liên kết mới
    new_link = ParentStudentLink(
        parent_id=current_user["id"],
        student_id=student.id,
        student_nickname=None # Có thể đặt sau
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    
    return {
        "student_id": student.id,
        "email": student.email,
        "nickname": new_link.student_nickname,
        "created_at": new_link.created_at
    }

@router.get("/students", response_model=List[schemas.LinkedStudentResponse])
def get_linked_students(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Phụ huynh xem danh sách học sinh đang giám sát.
    """
    if current_user.get("role") != "MONITOR":
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới có thể xem danh sách này.")
        
    links = db.query(ParentStudentLink, User).join(
        User, ParentStudentLink.student_id == User.id
    ).filter(ParentStudentLink.parent_id == current_user["id"]).all()
    
    results = []
    for link, student in links:
        results.append({
            "student_id": student.id,
            "email": student.email,
            "nickname": link.student_nickname,
            "created_at": link.created_at
        })
        
    return results

@router.put("/students/{student_id}", response_model=schemas.LinkedStudentResponse)
def update_student_nickname(
    student_id: str,
    request: schemas.UpdateStudentNicknameRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Phụ huynh cập nhật biệt danh cho con"""
    if current_user.get("role") != "MONITOR":
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới có thể sửa biệt danh.")
        
    link = db.query(ParentStudentLink).filter(
        ParentStudentLink.parent_id == current_user["id"],
        ParentStudentLink.student_id == student_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết với học sinh này.")
        
    link.student_nickname = request.nickname
    db.commit()
    
    # Lấy thông tin học sinh để trả về
    student = db.query(User).filter(User.id == student_id).first()
    
    return {
        "student_id": student.id,
        "email": student.email,
        "nickname": link.student_nickname,
        "created_at": link.created_at
    }

@router.delete("/students/{student_id}")
def remove_student_link(
    student_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Phụ huynh xóa (hủy liên kết) với con"""
    if current_user.get("role") != "MONITOR":
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới có quyền hủy liên kết.")
        
    link = db.query(ParentStudentLink).filter(
        ParentStudentLink.parent_id == current_user["id"],
        ParentStudentLink.student_id == student_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết với học sinh này.")
        
    db.delete(link)
    db.commit()
    
    return {"message": "Đã hủy liên kết thành công"}
