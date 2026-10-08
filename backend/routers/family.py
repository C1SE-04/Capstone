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
from redis_client import get_redis
import redis.asyncio as aioredis

router = APIRouter(
    prefix="/family",
    tags=["Family"]
)

def generate_pairing_code() -> str:
    """Tạo mã liên kết 6 ký tự ngẫu nhiên (chữ IN HOA và số), loại bỏ các ký tự dễ nhầm lẫn (O, 0, I, 1)"""
    safe_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return ''.join(random.choices(safe_chars, k=6))

@router.post("/pairing-code", response_model=schemas.PairingCodeResponse)
async def generate_student_pairing_code(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    Học sinh (STUDENT) gọi API này để lấy mã Pairing Code.
    Mã sẽ được lưu vào Redis và có hạn 15 phút (900 giây).
    """
    if current_user.get("role") != "STUDENT":
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể tạo mã liên kết.")
    
    student_id = current_user["id"]
    
    # Kiểm tra xem học sinh đã tạo mã nào chưa hết hạn không
    # Tránh spam mã mới liên tục
    existing_code = await redis.get(f"student_active_code:{student_id}")
    if existing_code:
        code_str = existing_code.decode('utf-8')
        ttl = await redis.ttl(f"pairing_code:{code_str}")
        return {"pairing_code": code_str, "expires_in": ttl if ttl > 0 else 0}

    # Tạo mã mới
    new_code = generate_pairing_code()
    # Nếu mã ngẫu nhiên bị trùng (rất hiếm, nhưng check cho an toàn)
    while await redis.exists(f"pairing_code:{new_code}"):
        new_code = generate_pairing_code()
            
    # Lưu vào Redis: key là pairing_code, value là student_id, tồn tại 15 phút
    await redis.setex(f"pairing_code:{new_code}", 900, student_id)
    # Lưu thêm 1 key ngược lại để biết học sinh này đang có mã nào active
    await redis.setex(f"student_active_code:{student_id}", 900, new_code)
        
    return {"pairing_code": new_code, "expires_in": 900}

@router.get("/pairing-code", response_model=schemas.PairingCodeResponse)
async def get_student_pairing_code(
    current_user: dict = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    Lấy mã Pairing Code hiện tại của học sinh nếu còn hạn.
    Không tạo mã mới. Dùng để reload trang F5.
    """
    if current_user.get("role") != "STUDENT":
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể xem mã liên kết.")
        
    student_id = current_user["id"]
    existing_code = await redis.get(f"student_active_code:{student_id}")
    
    if existing_code:
        code_str = existing_code.decode('utf-8')
        ttl = await redis.ttl(f"pairing_code:{code_str}")
        if ttl > 0:
            return {"pairing_code": code_str, "expires_in": ttl}
            
    # Nếu không có mã nào active, trả về mã rỗng hoặc báo lỗi 404 cũng được.
    # Ở đây chọn trả về HTTP 404 để FE dễ handle
    raise HTTPException(status_code=404, detail="Không có mã liên kết nào đang hoạt động.")

@router.post("/link-student", response_model=schemas.LinkedStudentResponse)
async def link_student_to_parent(
    request: schemas.LinkStudentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
):
    """
    Phụ huynh (MONITOR) nhập Pairing Code để liên kết với học sinh.
    Lấy thông tin từ Redis, nếu hợp lệ thì lưu vào DB và xoá mã trên Redis.
    """
    if current_user.get("role") != "MONITOR":
        raise HTTPException(status_code=403, detail="Chỉ phụ huynh mới có thể liên kết học sinh.")
        
    code = request.pairing_code.upper()
    student_id_bytes = await redis.get(f"pairing_code:{code}")
    
    if not student_id_bytes:
        raise HTTPException(status_code=404, detail="Mã liên kết đã hết hạn hoặc không tồn tại.")
        
    student_id = student_id_bytes.decode('utf-8')
    
    # Tìm học sinh trong DB để lấy email trả về
    student = db.query(User).filter(User.id == student_id, User.role == "STUDENT").first()
    if not student:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu học sinh.")
        
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
    
    # Xoá mã khỏi Redis sau khi đã dùng (One-time use)
    await redis.delete(f"pairing_code:{code}")
    await redis.delete(f"student_active_code:{student_id}")
    
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
