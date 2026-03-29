import pytest
import numpy as np
import json
from unittest.mock import MagicMock, patch
from app.domains.workouts.posture_service import calculate_angle, get_coords, analyze_posture
from app.domains.users.models import SupportedExercise

def test_calculate_angle_90_degrees():
    a = (0, 1)
    b = (0, 0)
    c = (1, 0)
    angle = calculate_angle(a, b, c)
    assert pytest.approx(angle) == 90.0

def test_calculate_angle_180_degrees():
    a = (1, 0)
    b = (0, 0)
    c = (-1, 0)
    angle = calculate_angle(a, b, c)
    assert pytest.approx(angle) == 180.0

def test_calculate_angle_45_degrees():
    a = (1, 1)
    b = (0, 0)
    c = (1, 0)
    angle = calculate_angle(a, b, c)
    assert pytest.approx(angle) == 45.0

def test_get_coords():
    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y
    
    landmarks = [MockLandmark(0.5, 0.5), MockLandmark(1.0, 1.0)]
    coords = get_coords(landmarks, 0, 100, 200)
    assert coords == (50.0, 100.0)
    
    coords = get_coords(landmarks, 1, 100, 200)
    assert coords == (100.0, 200.0)
    
    with pytest.raises(IndexError):
        get_coords(landmarks, 2, 100, 200)

@patch("app.domains.workouts.posture_service.cv2.imdecode")
@patch("app.domains.workouts.posture_service.get_detector")
@patch("app.domains.workouts.posture_service.mp.Image")
def test_analyze_posture_exercise_not_found(mock_mp_image, mock_get_detector, mock_imdecode):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    result = analyze_posture(mock_db, b"fake_image_bytes", "unknown_exercise")
    assert result["status"] == "error"
    assert "no encontrado" in result["feedback"]

@patch("app.domains.workouts.posture_service.cv2.imdecode")
@patch("app.domains.workouts.posture_service.get_detector")
@patch("app.domains.workouts.posture_service.mp.Image")
def test_analyze_posture_no_rules(mock_mp_image, mock_get_detector, mock_imdecode):
    mock_db = MagicMock()
    mock_exercise = SupportedExercise(name="test_ex", rules_json=None)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_exercise
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    
    result = analyze_posture(mock_db, b"fake_image_bytes", "test_ex")
    assert result["status"] == "error"
    assert "no tiene reglas configuradas" in result["feedback"]

@patch("app.domains.workouts.posture_service.cv2.imdecode")
@patch("app.domains.workouts.posture_service.get_detector")
@patch("app.domains.workouts.posture_service.mp.Image")
def test_analyze_posture_success(mock_mp_image, mock_get_detector, mock_imdecode):
    mock_db = MagicMock()
    rules = {
        "target_joints": [0, 1, 2],
        "down_stage": {"condition": "<", "angle": 100},
        "up_stage": {"condition": ">", "angle": 160},
        "feedback_push": "Baja más"
    }
    mock_exercise = SupportedExercise(name="test_ex", rules_json=json.dumps(rules))
    mock_db.query.return_value.filter.return_value.first.return_value = mock_exercise
    
    # Mock image and detector
    mock_imdecode.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
    mock_detector = mock_get_detector.return_value
    
    class MockLandmark:
        def __init__(self, x, y):
            self.x = x
            self.y = y
            
    mock_res = MagicMock()
    # P1: (0.5, 1.0), P2: (0.5, 0.5), P3: (1.0, 0.5) => 90 degrees
    mock_res.pose_landmarks = [[MockLandmark(0.5, 1.0), MockLandmark(0.5, 0.5), MockLandmark(1.0, 0.5)]]
    mock_detector.detect.return_value = mock_res
    
    result = analyze_posture(mock_db, b"fake_image_bytes", "test_ex")
    
    assert result["status"] == "success"
    assert pytest.approx(result["angle"]) == 90.0
    assert result["stage"] == "down"
    assert result["feedback"] == "¡Buen movimiento!"
