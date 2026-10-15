import pytest
from fastapi.testclient import TestClient
from main import app
import dependencies

client = TestClient(app)

# Giả lập current_user là STUDENT
def mock_get_current_user():
    return {"id": "test-student-id", "role": "STUDENT", "grade": 5}

app.dependency_overrides[dependencies.get_current_user] = mock_get_current_user

def test_weekly_metrics():
    response = client.get("/metrics/study-time?student_id=test-student-id&mode=weekly")
    print("WEEKLY RESPONSE:", response.json())
    assert response.status_code == 200

def test_monthly_metrics():
    response = client.get("/metrics/study-time?student_id=test-student-id&mode=monthly")
    assert response.status_code == 200
    print("MONTHLY RESPONSE SUCCESS, total_minutes:", response.json().get("total_minutes"))

if __name__ == "__main__":
    test_weekly_metrics()
    test_monthly_metrics()
    print("All tests passed!")
