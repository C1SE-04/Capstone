import requests
import json

try:
    res = requests.post("http://127.0.0.1:8000/family/link-student", json={"pairing_code": "QZ5PHR"})
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Exception:", str(e))
