import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models import User
from auth import create_access_token
import redis_client

db = SessionLocal()
parent = db.query(User).filter(User.role == "MONITOR").first()
student = db.query(User).filter(User.role == "STUDENT").first()

if not parent or not student:
    print("Missing users")
    exit(1)

# Generate valid token using the app's exact auth logic
token = create_access_token(data={"sub": parent.id, "email": parent.email, "role": parent.role})

# Create pairing code in redis directly via requests to the backend (impersonating student)
student_token = create_access_token(data={"sub": student.id, "email": student.email, "role": student.role})
res_gen = requests.post("http://127.0.0.1:8000/family/pairing-code", headers={"Authorization": f"Bearer {student_token}"})
if res_gen.status_code != 200:
    print("Failed to generate code:", res_gen.text)
    exit(1)

code = res_gen.json().get("pairing_code")
print("Generated code:", code)

# Link using parent token
res_link = requests.post("http://127.0.0.1:8000/family/link-student", json={"pairing_code": code}, headers={"Authorization": f"Bearer {token}"})
print("Link Status:", res_link.status_code)
print("Link Body:", res_link.text)

