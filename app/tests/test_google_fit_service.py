import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
from app.domains.integrations.google_fit_service import sync_google_fit_data, refresh_google_token
from app.domains.users.models import User, HealthMetric

@pytest.fixture
def mock_user_with_tokens(db):
    user = User(
        email="google_test@example.com",
        hashed_password="hashed_password",
        google_fit_access_token="old_access_token",
        google_fit_refresh_token="valid_refresh_token"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@patch("app.domains.integrations.google_fit_service.requests.post")
def test_refresh_google_token(mock_post, mock_user_with_tokens, db):
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "new_access_token"}
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    new_token = refresh_google_token(mock_user_with_tokens, db)

    assert new_token == "new_access_token"
    assert mock_user_with_tokens.google_fit_access_token == "new_access_token"
    mock_post.assert_called_once()

@patch("app.domains.integrations.google_fit_service.SessionLocal")
@patch("app.domains.integrations.google_fit_service.requests.post")
def test_sync_google_fit_data_success(mock_post, mock_session, mock_user_with_tokens, db):
    # Ensure the service uses the test database session
    mock_session.return_value = db
    
    # Capture the original close method to restore it later if needed, 
    # but for the test we want it to do nothing so the session stays open for assertions.
    db.close = MagicMock()

    test_now = datetime(2024, 1, 1, 12, 0, 0)
    test_millis = int(test_now.timestamp() * 1000)
    user_id = mock_user_with_tokens.id

    # Mock Google Fit API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "bucket": [
            {
                "startTimeMillis": str(test_millis),
                "dataset": [
                    {
                        "point": [
                            {
                                "dataTypeName": "com.google.step_count.delta",
                                "value": [{"intVal": 5000}]
                            }
                        ]
                    },
                    {
                        "point": [
                            {
                                "dataTypeName": "com.google.weight.summary",
                                "value": [{"fpVal": 75.5}]
                            }
                        ]
                    }
                ]
            }
        ]
    }
    mock_post.return_value = mock_response

    sync_google_fit_data(user_id)

    # Verify data was saved to DB
    metric = db.query(HealthMetric).filter(HealthMetric.user_id == user_id).first()
    
    assert metric is not None, "HealthMetric should have been created"
    assert metric.steps == 5000
    assert metric.weight_kg == 75.5
    assert metric.source == "google_fit"
