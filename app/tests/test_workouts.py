import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.domains.users.dependencies import get_current_user
from app.domains.users.models import User, WorkoutPlan, WorkoutDay

@pytest.fixture
def test_user(db):
    user = User(id=1, email="test_workout@example.com", hashed_password="hashed_password")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def authenticated_client(client: TestClient, test_user):
    """Fixture that overrides the get_current_user dependency."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_generate_workout_endpoint(authenticated_client: TestClient, db, test_user):
    payload = {
        "training_type": "strength",
        "primary_goal": "hypertrophy",
        "fitness_level": "intermediate"
    }
    
    with patch("app.api.v1.endpoints.workouts.generate_workout") as mock_gen:
        mock_gen.return_value = {
            "title": "Test Plan",
            "daily_routines": [
                {
                    "day": 0,
                    "focus": "Upper Body",
                    "exercises": [
                        {
                            "name": "Pushups",
                            "type": "warmup",
                            "instructions": "Warmup sets"
                        }
                    ]
                }
            ]
        }
        
        response = authenticated_client.post(
            "/api/v1/workouts/generate", 
            json=payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Plan"
        assert len(data["days"]) == 1
        assert data["days"][0]["day_index"] == 0
        
        # Verify it was saved to DB
        plan_in_db = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == test_user.id).first()
        assert plan_in_db is not None
        assert plan_in_db.title == "Test Plan"
        assert len(plan_in_db.days) == 1

def test_replan_workout_endpoint(authenticated_client: TestClient, db, test_user):
    # Setup: Create an existing plan
    old_plan = WorkoutPlan(
        user_id=test_user.id, 
        title="Old Plan", 
        json_data='{"title": "Old Plan", "daily_routines": [{"day": 0, "focus": "Bench"}]}',
        training_type="strength"
    )
    db.add(old_plan)
    db.commit()
    
    day = WorkoutDay(workout_plan_id=old_plan.id, day_index=0, is_completed=True, performance_data='{"Bench": {"weight": 100}}')
    db.add(day)
    db.commit()

    with patch("app.api.v1.endpoints.workouts.generate_adaptive_workout_update") as mock_adapt:
        mock_adapt.return_value = {
            "title": "Adapted Plan",
            "daily_routines": [
                {
                    "day": 1,
                    "focus": "Squats",
                    "exercises": [{"name": "Squat", "type": "active", "instructions": "Do it"}]
                }
            ]
        }
        
        response = authenticated_client.post(
            "/api/v1/workouts/replan",
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Adapted Plan"
        assert len(data["days"]) == 1
        assert data["days"][0]["day_index"] == 1
        
        mock_adapt.assert_called_once()
