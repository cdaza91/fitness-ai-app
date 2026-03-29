import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.domains.users.dependencies import get_current_user
from app.domains.users.models import User

@pytest.fixture
def authenticated_client(client: TestClient, db):
    """Fixture that overrides the get_current_user dependency."""
    mock_user = User(id=1, email="test@example.com", hashed_password="hashed_password")
    db.add(mock_user)
    db.commit()
    db.refresh(mock_user)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)

def test_garmin_sync_endpoint(authenticated_client: TestClient):
    payload = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    with patch("app.api.v1.endpoints.integrations.sync_garmin_data") as mock_sync:
        response = authenticated_client.post(
            "/api/v1/integrations/garmin/sync", 
            json=payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 200
        assert "sincronización iniciada" in response.json()["message"]
        mock_sync.assert_called_once()

def test_google_fit_sync_endpoint(authenticated_client: TestClient, db):
    payload = {
        "access_token": "google_access",
        "refresh_token": "google_refresh"
    }
    
    with patch("app.api.v1.endpoints.integrations.sync_google_fit_data") as mock_sync:
        response = authenticated_client.post(
            "/api/v1/integrations/google-fit/sync", 
            json=payload,
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 200
        assert "Google Fit guardados" in response.json()["message"]
        
        # Verify tokens were saved
        user = db.query(User).filter(User.id == 1).first()
        assert user.google_fit_access_token == "google_access"
        assert user.google_fit_refresh_token == "google_refresh"
        
        mock_sync.assert_called_once_with(1)
