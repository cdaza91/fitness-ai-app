import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.domains.users.dependencies import get_current_user
from app.domains.users.models import User

@pytest.fixture
def authenticated_client(client: TestClient):
    """Fixture that overrides the get_current_user dependency."""
    mock_user = User(id=1, email="test@example.com", hashed_password="hashed_password")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_generate_workout_endpoint(authenticated_client: TestClient):
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
        
        # We pass a fake token just to satisfy the OAuth2 schema requirement
        response = authenticated_client.post(
            "/api/v1/workouts/generate", 
            json=payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Plan"
        assert len(data["daily_routines"]) > 0
        assert data["daily_routines"][0]["focus"] == "Upper Body"
