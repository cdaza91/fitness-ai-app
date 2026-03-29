from behave import given, when, then
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.domains.users.models import User
from app.main import app

@given('a user "{email}"')
def step_impl(context, email):
    context.user_email = email
    # Mock authentication to return this user
    context.current_user = User(email=email, id=1)

@when('the user submits valid Garmin credentials "{garmin_email}" and "{password}"')
def step_impl(context, garmin_email, password):
    # Mock auth dependency
    from app.domains.users.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: context.current_user
    
    with patch("app.api.v1.endpoints.integrations.sync_garmin_data") as mock_sync:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/garmin/sync",
            json={"email": garmin_email, "password": password}
        )
        context.response = response
        context.garmin_email = garmin_email

@then('the user\'s Garmin email should be "{garmin_email}"')
def step_impl(context, garmin_email):
    assert context.current_user.garmin_email == garmin_email

@then('the system should confirm the sync started')
def step_impl(context):
    assert context.response.status_code == 200
    assert "sincronización iniciada" in context.response.json()["message"]

@when('the user "{email}" tries to push a workout without Garmin link')
def step_impl(context, email):
    # Mock auth dependency for a user with no Garmin credentials
    user = User(email=email, id=2, garmin_email=None, garmin_password=None)
    from app.domains.users.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user
    
    client = TestClient(app)
    response = client.post(
        "/api/v1/integrations/garmin/push-workout",
        json={"day_index": 0}
    )
    context.response = response

@then('the system should return an error "{error_msg}"')
def step_impl(context, error_msg):
    assert context.response.status_code == 400
    assert error_msg in context.response.json()["detail"]
