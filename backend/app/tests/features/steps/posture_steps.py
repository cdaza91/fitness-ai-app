from behave import given, when, then
from unittest.mock import MagicMock, patch
import json
import numpy as np
from app.domains.workouts.posture_service import analyze_posture
from app.domains.users.models import SupportedExercise

@given('the database has an exercise "{ex_name}" with valid rules')
def step_impl(context, ex_name):
    context.ex_name = ex_name
    rules = {
        "target_joints": [0, 1, 2],
        "down_stage": {"condition": "<", "angle": 100},
        "up_stage": {"condition": ">", "angle": 160},
        "feedback_push": "Baja más"
    }
    context.mock_db = MagicMock()
    mock_exercise = SupportedExercise(name=ex_name, rules_json=json.dumps(rules))
    context.mock_db.query.return_value.filter.return_value.first.return_value = mock_exercise

@when('the user uploads a valid image for "{ex_name}"')
def step_impl(context, ex_name):
    with patch("app.domains.workouts.posture_service.cv2.imdecode") as mock_imdecode:
        with patch("app.domains.workouts.posture_service.get_detector") as mock_get_detector:
            with patch("app.domains.workouts.posture_service.mp.Image") as mock_mp_image:
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
                
                context.result = analyze_posture(context.mock_db, b"fake_image_bytes", ex_name)

@then('the status should be "{status}"')
def step_impl(context, status):
    assert context.result["status"] == status

@then('the stage should be "{stage}"')
def step_impl(context, stage):
    assert context.result["stage"] == stage

@then('the feedback should be "{feedback}"')
def step_impl(context, feedback):
    assert context.result["feedback"] == feedback
