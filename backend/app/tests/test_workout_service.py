import pytest
import json
from unittest.mock import MagicMock, patch
from app.domains.workouts.service import generate_running_workout, generate_strength_workout, _extract_json_from_response
from app.domains.users.models import User

@pytest.fixture
def mock_user():
    return User(
        email="test@example.com",
        target_race_distance="10k",
        target_race_date="2024-12-01",
        easy_pace="6:00",
        fitness_level="Intermediate",
        age=30,
        weight=75.0,
        primary_goal="Fitness",
        equipment_access='["Bench", "Dumbbells"]',
        days_per_week=3
    )

def test_extract_json_from_response_valid():
    raw_response = 'Here is your plan: {"title": "Test Plan", "daily_routines": []} Enjoy!'
    result = _extract_json_from_response(raw_response)
    assert result["title"] == "Test Plan"

def test_extract_json_from_response_invalid():
    raw_response = "Not a JSON at all"
    # The refactored version raises ValueError with a custom message
    with pytest.raises(ValueError, match="Invalid AI response format"):
        _extract_json_from_response(raw_response)

@patch("app.domains.workouts.service.get_ai_model")
def test_generate_running_workout(mock_get_ai_model, mock_user):
    mock_model = mock_get_ai_model.return_value
    mock_model.generate_content.return_value.text = '{"title": "Running Plan", "daily_routines": []}'
    
    result = generate_running_workout(mock_user)
    
    assert result["title"] == "Running Plan"
    mock_model.generate_content.assert_called_once()
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "elite Running Coach" in prompt_used
    assert "10k" in prompt_used

@patch("app.domains.workouts.service.get_ai_model")
def test_generate_strength_workout(mock_get_ai_model, mock_user):
    mock_model = mock_get_ai_model.return_value
    mock_model.generate_content.return_value.text = '{"title": "Strength Plan", "daily_routines": []}'
    
    result = generate_strength_workout(mock_user)
    
    assert result["title"] == "Strength Plan"
    mock_model.generate_content.assert_called_once()
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "Expert Hypertrophy & Strength Coach" in prompt_used
    assert "75.0kg" in prompt_used
