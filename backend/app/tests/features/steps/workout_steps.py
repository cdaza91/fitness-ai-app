from behave import given, when, then
from unittest.mock import MagicMock, patch
from app.domains.workouts.service import generate_workout
from app.domains.users.models import User

@given('a user with a goal of "{goal}" and a pace of "{pace}"')
def step_impl(context, goal, pace):
    context.user = User(
        email="runner@test.com",
        target_race_distance=goal,
        easy_pace=pace,
        fitness_level="Advanced"
    )

@given('a user with a goal of "{goal}" and "{equipment}" access')
def step_impl(context, goal, equipment):
    context.user = User(
        email="lifter@test.com",
        primary_goal=goal,
        equipment_access=equipment,
        days_per_week=4,
        fitness_level="Intermediate"
    )

@when('the user requests a "{training_type}" workout')
def step_impl(context, training_type):
    # Mock the AI call to return a fixed plan based on training type
    with patch("app.domains.workouts.service.get_ai_model") as mock_get_ai_model:
        mock_model = mock_get_ai_model.return_value
        if training_type == "running":
            mock_model.generate_content.return_value.text = '{"title": "Running Marathon Plan", "daily_routines": [{"day": 0, "focus": "Intervals", "exercises": [{"name": "LSD", "type": "active", "duration_s": 60, "target_min": "6:00", "target_max": "5:30", "instructions": "test"}]}]}'
        else:
            mock_model.generate_content.return_value.text = '{"title": "Strength Muscle Gain Plan", "daily_routines": [{"day": 0, "focus": "Upper", "exercises": [{"name": "Bench Press", "type": "active", "reps": 10, "instructions": "test"}]}]}'
        
        context.result = generate_workout(context.user, training_type)
        context.training_type = training_type

@then('the system should generate a plan with a focus on "{focus_type}"')
def step_impl(context, focus_type):
    assert focus_type.lower() in context.result["title"].lower()

@then('the plan should have MM:SS formatted paces')
def step_impl(context):
    exercises = context.result["daily_routines"][0]["exercises"]
    for ex in exercises:
        if ex.get("target_min"):
            assert ":" in ex["target_min"]
        if ex.get("target_max"):
            assert ":" in ex["target_max"]

@then('the plan should have exercises with "reps" or "duration_s"')
def step_impl(context):
    exercises = context.result["daily_routines"][0]["exercises"]
    for ex in exercises:
        assert "reps" in ex or "duration_s" in ex
