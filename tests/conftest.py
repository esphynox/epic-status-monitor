"""Shared pytest fixtures for tests."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

from src.epic_status import StatusEvent, StatusUpdate, Component, EventType
from src.filters import FilterConfig


@pytest.fixture
def sample_incident_data():
    """Sample incident API response data."""
    with open(Path(__file__).parent / "fixtures" / "sample_incident.json") as f:
        return json.load(f)


@pytest.fixture
def sample_maintenance_data():
    """Sample maintenance API response data."""
    with open(Path(__file__).parent / "fixtures" / "sample_maintenance.json") as f:
        return json.load(f)


@pytest.fixture
def sample_incident(sample_incident_data):
    """Create a sample StatusEvent incident."""
    from src.epic_status import _parse_event, EventType
    return _parse_event(sample_incident_data, EventType.INCIDENT)


@pytest.fixture
def sample_maintenance(sample_maintenance_data):
    """Create a sample StatusEvent maintenance."""
    from src.epic_status import _parse_event, EventType
    return _parse_event(sample_maintenance_data, EventType.MAINTENANCE)


@pytest.fixture
def sample_event_no_updates():
    """Create a StatusEvent with no updates."""
    return StatusEvent(
        id="event-no-updates",
        name="Test Event",
        status="investigating",
        impact="minor",
        shortlink="https://stspg.io/test",
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:00:00Z",
        updates=[],
        components=[
            Component(id="comp-1", name="Service", status="operational")
        ],
        event_type=EventType.INCIDENT,
    )


@pytest.fixture
def sample_fortnite_incident():
    """Create a Fortnite-specific incident."""
    return StatusEvent(
        id="fortnite-incident",
        name="Fortnite Matchmaking Issues",
        status="monitoring",
        impact="major",
        shortlink="https://stspg.io/fortnite",
        created_at="2024-01-15T10:00:00Z",
        updated_at="2024-01-15T10:30:00Z",
        updates=[
            StatusUpdate(
                id="update-1",
                status="monitoring",
                body="Investigating matchmaking problems",
                created_at="2024-01-15T10:30:00Z",
            )
        ],
        components=[
            Component(id="comp-fn", name="Fortnite", status="degraded_performance")
        ],
        event_type=EventType.INCIDENT,
    )


@pytest.fixture
def temp_state_file():
    """Create a temporary state file."""
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_config_file():
    """Create a temporary config file."""
    with NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def empty_state_file(temp_state_file):
    """Create an empty state file."""
    temp_state_file.write_text(json.dumps({
        "seen_ids": [],
        "last_updates": {},
        "last_checked": "2024-01-15T10:00:00Z"
    }, indent=2))
    return temp_state_file


@pytest.fixture
def populated_state_file(temp_state_file, sample_incident):
    """Create a state file with one seen event."""
    data = {
        "seen_ids": [sample_incident.id],
        "last_updates": {sample_incident.id: sample_incident.fingerprint},
        "last_checked": "2024-01-15T10:00:00Z"
    }
    temp_state_file.write_text(json.dumps(data, indent=2))
    return temp_state_file


@pytest.fixture
def default_filter_config():
    """Create a default FilterConfig (no filtering)."""
    return FilterConfig()


@pytest.fixture
def fortnite_filter_config():
    """Create a FilterConfig that filters for Fortnite only."""
    return FilterConfig(services=["Fortnite"])


@pytest.fixture
def impact_filter_config():
    """Create a FilterConfig that filters for major+ incidents."""
    return FilterConfig(min_impact="major")


@pytest.fixture
def incidents_only_filter_config():
    """Create a FilterConfig that only allows incidents."""
    return FilterConfig(event_types="incidents")


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to mock environment variables."""
    def _set_env(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setenv(key, value)
        return kwargs
    return _set_env


@pytest.fixture
def clear_env_vars(monkeypatch):
    """Clear specific environment variables for tests."""
    def _clear(*var_names):
        for var in var_names:
            monkeypatch.delenv(var, raising=False)
    return _clear
