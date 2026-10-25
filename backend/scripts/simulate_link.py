# coding: utf-8
import os
import requests
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis
import dotenv
dotenv.load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

from models import User
parent = db.query(User).filter(User.role == "MONITOR").first()
student = db.query(User).filter(User.role == "STUDENT").first()

SECRET_KEY = os.environ.get("SECRET_KEY", "your-super-secret-key")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
token = jwt.encode({"sub": parent.id, "email": parent.email, "role": parent.role, "exp": datetime.utcnow() + timedelta(minutes=60)}, SECRET_KEY, algorithm=ALGORITHM)

r = redis.from_url(os.environ.get("REDIS_URL"))
r.setex("pairing_code:TESTXX", 900, student.id)
r.setex(f"student_active_code:{student.id}", 900, "TESTXX")

res = requests.post("http://127.0.0.1:8000/family/link-student", json={"pairing_code": "TESTXX"}, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
print("Status:", res.status_code)
print("Response:", res.text.encode('utf-8'))
