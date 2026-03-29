import pytest
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.domains.users.models import SupportedExercise

def test_full_user_flow(client: TestClient, db):
    # 1. Register
    reg_payload = {"email": "test_user@example.com", "password": "password123"}
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # 2. Login
    login_payload = {"email": "test_user@example.com", "password": "password123"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "test_user@example.com"

    # 3. Add a Supported Exercise
    rules = {
        "target_joints": [11, 13, 15],
        "down_stage": {"condition": "<", "angle": 90},
        "up_stage": {"condition": ">", "angle": 160},
        "feedback_push": "Baja más"
    }
    exercise = SupportedExercise(
        name="pushup", 
        rules_json=json.dumps(rules),
        is_active=True
    )
    db.add(exercise)
    db.commit()

    # 4. Generate Workout
    headers = {"Authorization": f"Bearer {token}"}
    workout_payload = {
        "training_type": "strength",
        "primary_goal": "muscle gain",
        "days_per_week": 3,
        "fitness_level": "intermediate"
    }
    
    # Mock AI response to avoid external API calls during tests
    mock_response = {
            "title": "Garmin Strength Plan",
            "target_goal": "muscle gain",
            "daily_routines": [
                {
                    "day": 0,
                    "focus": "Upper",
                    "exercises": [
                        {
                            "name": "Pushup", 
                            "type": "active", 
                            "duration_s": 60, 
                            "target_min": "01:00", 
                            "target_max": "00:50", 
                            "instructions": "test instructions"
                        }
                    ]
                }
            ]
        }

    # Use patch on the endpoint's reference to the service function
    with patch("app.api.v1.endpoints.workouts.generate_workout", return_value=mock_response):
        response = client.post("/api/v1/workouts/generate", json=workout_payload, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Garmin Strength Plan"

        # 5. Check if exercise is supported in the last workout (retrieved via /me)
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        me_data = response.json()
        last_workout = me_data["last_workout"]
        assert last_workout is not None
        
        exercises = last_workout["daily_routines"][0]["exercises"]
        pushup_ex = next(e for e in exercises if e["name"].lower() == "pushup")
        assert pushup_ex["is_posture_supported"] is True
