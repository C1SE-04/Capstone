# schemas.py
from pydantic import BaseModel, EmailStr

# Dữ liệu gửi lên khi Đăng ký & Đăng nhập
class AuthInput(BaseModel):
    email: EmailStr
    password: str

# Dữ liệu trả về khi Đăng ký thành công
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

# Dữ liệu trả về khi Đăng nhập thành công
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str