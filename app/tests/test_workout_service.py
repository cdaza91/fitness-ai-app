import pytest
import json
from unittest.mock import MagicMock, patch
from app.domains.workouts.service import (
    generate_running_workout, 
    generate_strength_workout, 
    _extract_json_from_response,
    generate_adaptive_workout_update
)
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

@patch("app.domains.workouts.service.get_ai_model")
def test_generate_adaptive_workout_update(mock_get_ai_model, mock_user):
    mock_model = mock_get_ai_model.return_value
    mock_model.generate_content.return_value.text = '{"title": "Adapted Plan", "daily_routines": []}'
    
    result = generate_adaptive_workout_update(
        user=mock_user,
        training_type="strength",
        original_plan_json='{"title": "Old Plan", "daily_routines": []}',
        completed_sessions=[{"day": 0}],
        missed_sessions=[{"day": 2}],
        performance_metrics={"Bench Press": {"weight": 60}},
        health_metrics=[{"date": "2024-01-01", "sleep_score": 85}],
        activities=[{"name": "Morning Run", "avg_hr": 140}]
    )
    
    assert result["title"] == "Adapted Plan"
    mock_model.generate_content.assert_called_once()
    prompt_used = mock_model.generate_content.call_args[0][0]
    assert "Adaptive AI Fitness Coach" in prompt_used
    assert "performance data" in prompt_used.lower()
    assert "health & wellness metrics" in prompt_used.lower()
    assert "140" in prompt_used  # Activities HR
    assert "85" in prompt_used   # Sleep score
