# scripts/init_admin.py
# Khởi tạo hoặc cập nhật tài khoản ADMIN duy nhất trong hệ thống SocraticKid.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
import auth
from database import SessionLocal

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@socratickid.edu.vn").lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123456")

def ensure_single_admin() -> models.User:
    db = SessionLocal()
    try:
        # 1. Kiểm tra xem đã có admin nào chưa
        existing_admins = db.query(models.User).filter(models.User.role == "ADMIN").all()

        # Nếu có nhiều hơn 1 admin, xóa các tài khoản thừa hoặc hạ role để đảm bảo DUY NHẤT 1 admin
        if len(existing_admins) > 1:
            print(f"⚠️ Phát hiện {len(existing_admins)} tài khoản ADMIN. Đang giữ lại duy nhất {ADMIN_EMAIL}...")
            for a in existing_admins:
                if a.email.lower() != ADMIN_EMAIL:
                    db.delete(a)
            db.commit()

        # 2. Tìm tài khoản admin chuẩn theo email
        admin = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()

        if admin:
            # Đảm bảo role là ADMIN và cập nhật mật khẩu chuẩn
            admin.role = "ADMIN"
            admin.hashed_password = auth.hash_password(ADMIN_PASSWORD)
            db.commit()
            db.refresh(admin)
            print(f"✅ Đã cập nhật tài khoản ADMIN duy nhất:")
            print(f"   Email:    {admin.email}")
            print(f"   Password: {ADMIN_PASSWORD}")
            print(f"   ID:       {admin.id}")
        else:
            # Tạo mới admin
            admin = models.User(
                email=ADMIN_EMAIL,
                hashed_password=auth.hash_password(ADMIN_PASSWORD),
                role="ADMIN",
                grade=None,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"🎉 Đã tạo thành công tài khoản ADMIN duy nhất:")
            print(f"   Email:    {admin.email}")
            print(f"   Password: {ADMIN_PASSWORD}")
            print(f"   ID:       {admin.id}")

        return admin
    finally:
        db.close()

if __name__ == "__main__":
    ensure_single_admin()
