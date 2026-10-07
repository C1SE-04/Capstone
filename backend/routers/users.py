from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import dependencies
import models
from database import get_db

router = APIRouter(tags=["Users"])

@router.get("/user/me")
def get_current_user_info(current_user: dict = Depends(dependencies.get_current_user)):
    return {"message": "Thông tin người dùng hiện tại", "user": current_user}

@router.get("/monitor/dashboard")
def monitor_dashboard(current_user: dict = Depends(dependencies.require_role(["MONITOR"]))):
    return {"message": "Chào mừng cán sự lớp", "user": current_user}

@router.delete("/students/{student_id}")
def delete_student(student_id: int, current_user: dict = Depends(dependencies.require_role(["ADMIN"]))):
    return {"message": f"Đã xoá sinh viên {student_id}"}


class GradePatchRequest(BaseModel):
    grade: int

# Task #131: PATCH /users/me/grade — Đổi lớp học trong trang Cài đặt
@router.patch("/users/me/grade")
def update_my_grade(
    body: GradePatchRequest,
    current_user: dict = Depends(dependencies.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Học sinh cập nhật lớp học của chính mình (4–9).
    Chỉ dành cho role STUDENT.
    """
    if current_user.get("role") != "STUDENT":
        raise HTTPException(status_code=403, detail="Chỉ học sinh mới có thể thay đổi lớp học.")

    if body.grade not in range(4, 10):
        raise HTTPException(status_code=422, detail="Lớp học phải là số từ 4 đến 9.")

    user_db = db.query(models.User).filter(models.User.id == current_user["id"]).first()
    if not user_db:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại.")

    user_db.grade = body.grade
    db.commit()
    db.refresh(user_db)

    return {
        "message": f"Đã cập nhật lớp học thành lớp {body.grade} thành công.",
        "grade": user_db.grade
    }
