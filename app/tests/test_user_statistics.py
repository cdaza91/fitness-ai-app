import pytest
import json
from datetime import date, datetime
from fastapi.testclient import TestClient
from app.main import app
from app.domains.users.dependencies import get_current_user
from app.domains.users.models import User, WorkoutPlan, WorkoutDay, HealthMetric, Activity

@pytest.fixture
def test_user(db):
    user = User(id=1, email="stats_test@example.com", hashed_password="hashed_password")
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

def test_get_user_statistics_empty(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/users/me/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["weight_history"] == []
    assert data["workout_completion"]["total_planned"] == 0
    assert data["total_activities_count"] == 0

def test_get_user_statistics_populated(authenticated_client: TestClient, db, test_user):
    # 1. Setup Weight History
    h1 = HealthMetric(user_id=test_user.id, date=date(2024, 1, 1), weight_kg=80.0)
    h2 = HealthMetric(user_id=test_user.id, date=date(2024, 1, 15), weight_kg=78.0)
    db.add_all([h1, h2])
    
    # 2. Setup Workout Completion & Strength Trends
    plan = WorkoutPlan(user_id=test_user.id, title="Test Plan", json_data="{}", training_type="strength")
    db.add(plan)
    db.flush()
    
    # Day 1: Bench Press @ 60kg
    d1 = WorkoutDay(
        workout_plan_id=plan.id, 
        day_index=0, 
        is_completed=True, 
        performance_data=json.dumps({"Bench Press": {"weight": 60}})
    )
    # Day 2: Bench Press @ 65kg
    d2 = WorkoutDay(
        workout_plan_id=plan.id, 
        day_index=1, 
        is_completed=True, 
        performance_data=json.dumps({"Bench Press": {"weight": 65}})
    )
    # Day 3: Not completed
    d3 = WorkoutDay(workout_plan_id=plan.id, day_index=2, is_completed=False)
    db.add_all([d1, d2, d3])
    
    # 3. Setup Activity Totals
    a1 = Activity(user_id=test_user.id, external_id="act1", calories=500, date=datetime.now())
    db.add(a1)
    
    db.commit()

    # Call Endpoint
    response = authenticated_client.get("/api/v1/users/me/statistics")
    assert response.status_code == 200
    data = response.json()
    
    # Verify Weight
    assert len(data["weight_history"]) == 2
    assert data["weight_history"][0]["weight"] == 80.0
    assert data["weight_history"][1]["weight"] == 78.0
    
    # Verify Completion
    assert data["workout_completion"]["total_planned"] == 3
    assert data["workout_completion"]["total_completed"] == 2
    assert data["workout_completion"]["completion_rate"] == (2/3 * 100)
    
    # Verify Strength Trends
    assert len(data["strength_trends"]) == 1
    bench_trend = data["strength_trends"][0]
    assert bench_trend["exercise_name"] == "Bench Press"
    assert bench_trend["last_weight"] == 65.0
    assert bench_trend["best_weight"] == 65.0
    # Improvement: (65-60)/60 * 100 = 8.333%
    assert pytest.approx(bench_trend["improvement_percentage"]) == 8.333333
    
    # Verify Activities
    assert data["total_activities_count"] == 1
    assert data["total_calories_burned"] == 500.0
