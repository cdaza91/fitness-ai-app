from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_workout_endpoint():
    payload = {
        "goal": "hipertrofia",
        "muscles": ["pecho", "tríceps"],
        "fitness_level": "intermedio"
    }
    response = client.post("/api/v1/workouts/generate", json=payload)
    assert response.status_code == 200
    assert "exercises" in response.json()
    assert len(response.json()["exercises"]) > 0