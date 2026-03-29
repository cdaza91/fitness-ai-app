import pytest
from unittest.mock import MagicMock, patch
from app.domains.integrations.garmin_service import pace_to_mps, _create_running_step

def test_pace_to_mps_valid():
    # 5:00 min/km = 12 km/h = 3.333... m/s
    assert pytest.approx(pace_to_mps("5:00")) == 3.333333
    # 10:00 min/km = 6 km/h = 1.666... m/s
    assert pytest.approx(pace_to_mps("10:00")) == 1.666667

def test_pace_to_mps_invalid():
    assert pace_to_mps("") is None
    assert pace_to_mps("invalid") is None
    assert pace_to_mps("0:00") is None
    assert pace_to_mps(None) is None

@patch("app.domains.integrations.garmin_service.create_warmup_step")
def test_create_running_step_warmup(mock_warmup):
    ex = {"name": "Warmup Run", "type": "warmup", "duration_s": 600}
    _create_running_step(ex, 0)
    mock_warmup.assert_called_once()
    assert mock_warmup.call_args[0][0] == 600.0
    # Default target type should be no target
    assert mock_warmup.call_args[1]["target_type"]["targetTypeKey"] == "no.target"

@patch("app.domains.integrations.garmin_service.create_interval_step")
def test_create_running_step_interval_with_pace(mock_interval):
    ex = {
        "name": "Tempo Run", 
        "type": "active", 
        "duration_s": 1200, 
        "target_min": "5:30", 
        "target_max": "5:00"
    }
    _create_running_step(ex, 1)
    mock_interval.assert_called_once()
    target_type = mock_interval.call_args[1]["target_type"]
    assert target_type["targetTypeKey"] == "pace.zone"
    assert pytest.approx(target_type["targetValueOne"]) == pace_to_mps("5:30")
    assert pytest.approx(target_type["targetValueTwo"]) == pace_to_mps("5:00")
