"""Tests for epic_status.py - API client and data models."""

import json
from pathlib import Path

import pytest
import responses

from src.epic_status import (
    Component,
    EventType,
    StatusEvent,
    StatusUpdate,
    _parse_event,
    fetch_active_maintenances,
    fetch_all_active_events,
    fetch_all_events,
    fetch_incidents,
    fetch_upcoming_maintenances,
    BASE_URL,
    INCIDENTS_URL,
    MAINTENANCE_ACTIVE_URL,
    MAINTENANCE_UPCOMING_URL,
)


@pytest.mark.unit
class TestStatusEventProperties:
    """Test StatusEvent dataclass properties."""

    def test_fingerprint_with_updates(self, sample_incident):
        """Test fingerprint generation with updates."""
        assert sample_incident.fingerprint == "investigating:update-1"

    def test_fingerprint_no_updates(self, sample_event_no_updates):
        """Test fingerprint generation without updates."""
        assert sample_event_no_updates.fingerprint == "investigating:"

    def test_latest_update(self, sample_incident):
        """Test getting latest update."""
        latest = sample_incident.latest_update
        assert latest is not None
        assert latest.id == "update-1"
        assert latest.status == "investigating"

    def test_latest_update_none(self, sample_event_no_updates):
        """Test latest_update when no updates exist."""
        assert sample_event_no_updates.latest_update is None

    def test_component_names(self, sample_incident):
        """Test component_names property."""
        assert sample_incident.component_names == ["Epic Games Store", "Launcher"]

    def test_is_maintenance(self, sample_maintenance):
        """Test is_maintenance property."""
        assert sample_maintenance.is_maintenance is True
        assert sample_maintenance.is_incident is False

    def test_is_incident(self, sample_incident):
        """Test is_incident property."""
        assert sample_incident.is_incident is True
        assert sample_incident.is_maintenance is False


@pytest.mark.unit
class TestParseEvent:
    """Test _parse_event function."""

    def test_parse_incident(self, sample_incident_data):
        """Test parsing an incident from API data."""
        event = _parse_event(sample_incident_data, EventType.INCIDENT)
        
        assert event.id == "test-incident-123"
        assert event.name == "Epic Games Store Login Issues"
        assert event.status == "investigating"
        assert event.impact == "major"
        assert event.event_type == EventType.INCIDENT
        assert len(event.updates) == 2
        assert len(event.components) == 2
        assert event.scheduled_for is None
        assert event.scheduled_until is None

    def test_parse_maintenance(self, sample_maintenance_data):
        """Test parsing a maintenance from API data."""
        event = _parse_event(sample_maintenance_data, EventType.MAINTENANCE)
        
        assert event.id == "maintenance-456"
        assert event.name == "Scheduled Maintenance: Rocket League Servers"
        assert event.status == "scheduled"
        assert event.event_type == EventType.MAINTENANCE
        assert event.scheduled_for == "2024-01-16T02:00:00Z"
        assert event.scheduled_until == "2024-01-16T04:00:00Z"

    def test_parse_event_missing_fields(self):
        """Test parsing event with missing optional fields."""
        minimal_data = {
            "id": "minimal-event",
            "name": "Test Event",
            "status": "investigating",
            "impact": "minor",
            "shortlink": "https://stspg.io/test",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "incident_updates": [],
            "components": [],
        }
        
        event = _parse_event(minimal_data, EventType.INCIDENT)
        assert event.id == "minimal-event"
        assert event.updates == []
        assert event.components == []
        assert event.scheduled_for is None

    def test_parse_event_empty_updates(self):
        """Test parsing event with empty updates array."""
        data = {
            "id": "no-updates",
            "name": "Event",
            "status": "resolved",
            "impact": "none",
            "shortlink": "https://stspg.io/test",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "incident_updates": [],
            "components": [{"id": "comp", "name": "Service", "status": "operational"}],
        }
        
        event = _parse_event(data, EventType.INCIDENT)
        assert len(event.updates) == 0
        assert event.fingerprint == "resolved:"

    def test_parse_event_component_missing_fields(self):
        """Test parsing with components missing optional fields."""
        data = {
            "id": "test",
            "name": "Test",
            "status": "investigating",
            "impact": "minor",
            "shortlink": "https://stspg.io/test",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z",
            "incident_updates": [],
            "components": [
                {"id": "comp-1", "name": "Service1"},
                {"id": "comp-2"},  # Missing name and status
            ],
        }
        
        event = _parse_event(data, EventType.INCIDENT)
        assert len(event.components) == 2
        assert event.components[0].name == "Service1"
        assert event.components[1].name == ""  # Default empty string


@pytest.mark.integration
class TestFetchFunctions:
    """Test API fetch functions with mocked HTTP responses."""

    @responses.activate
    def test_fetch_incidents_success(self, sample_incident_data):
        """Test successful fetch of incidents."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"incidents": [sample_incident_data]},
            status=200,
        )
        
        events = fetch_incidents()
        assert len(events) == 1
        assert events[0].id == "test-incident-123"
        assert events[0].event_type == EventType.INCIDENT

    @responses.activate
    def test_fetch_incidents_empty(self):
        """Test fetch when no incidents exist."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"incidents": []},
            status=200,
        )
        
        events = fetch_incidents()
        assert events == []

    @responses.activate
    def test_fetch_active_maintenances_success(self, sample_maintenance_data):
        """Test successful fetch of active maintenances."""
        responses.add(
            responses.GET,
            MAINTENANCE_ACTIVE_URL,
            json={"scheduled_maintenances": [sample_maintenance_data]},
            status=200,
        )
        
        events = fetch_active_maintenances()
        assert len(events) == 1
        assert events[0].id == "maintenance-456"
        assert events[0].event_type == EventType.MAINTENANCE

    @responses.activate
    def test_fetch_upcoming_maintenances_success(self, sample_maintenance_data):
        """Test successful fetch of upcoming maintenances."""
        responses.add(
            responses.GET,
            MAINTENANCE_UPCOMING_URL,
            json={"scheduled_maintenances": [sample_maintenance_data]},
            status=200,
        )
        
        events = fetch_upcoming_maintenances()
        assert len(events) == 1
        assert events[0].event_type == EventType.MAINTENANCE

    @responses.activate
    def test_fetch_all_active_events(self, sample_incident_data, sample_maintenance_data):
        """Test fetching all active events (incidents + active maintenances)."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"incidents": [sample_incident_data]},
            status=200,
        )
        responses.add(
            responses.GET,
            MAINTENANCE_ACTIVE_URL,
            json={"scheduled_maintenances": [sample_maintenance_data]},
            status=200,
        )
        
        events = fetch_all_active_events()
        assert len(events) == 2
        assert any(e.event_type == EventType.INCIDENT for e in events)
        assert any(e.event_type == EventType.MAINTENANCE for e in events)

    @responses.activate
    def test_fetch_all_events_with_upcoming(self, sample_incident_data, sample_maintenance_data):
        """Test fetch_all_events with include_upcoming=True."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"incidents": [sample_incident_data]},
            status=200,
        )
        responses.add(
            responses.GET,
            MAINTENANCE_ACTIVE_URL,
            json={"scheduled_maintenances": []},
            status=200,
        )
        responses.add(
            responses.GET,
            MAINTENANCE_UPCOMING_URL,
            json={"scheduled_maintenances": [sample_maintenance_data]},
            status=200,
        )
        
        events = fetch_all_events(include_upcoming=True)
        assert len(events) == 2  # 1 incident + 1 upcoming maintenance

    @responses.activate
    def test_fetch_all_events_without_upcoming(self, sample_incident_data):
        """Test fetch_all_events with include_upcoming=False."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"incidents": [sample_incident_data]},
            status=200,
        )
        responses.add(
            responses.GET,
            MAINTENANCE_ACTIVE_URL,
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        events = fetch_all_events(include_upcoming=False)
        assert len(events) == 1  # Only incident

    @responses.activate
    def test_fetch_network_error(self):
        """Test handling of network errors."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            body=ConnectionError("Network error"),
        )
        
        events = fetch_incidents()
        assert events == []  # Should return empty list on error

    @responses.activate
    def test_fetch_http_error(self):
        """Test handling of HTTP errors."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            status=500,
        )
        
        events = fetch_incidents()
        assert events == []  # Should return empty list on HTTP error

    @responses.activate
    def test_fetch_timeout(self):
        """Test handling of timeouts."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            body=TimeoutError("Request timeout"),
        )
        
        events = fetch_incidents(timeout=1)
        assert events == []

    @responses.activate
    def test_fetch_invalid_json(self):
        """Test handling of invalid JSON response."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            body="invalid json",
            status=200,
            content_type="application/json",
        )
        
        events = fetch_incidents()
        # Should handle JSON decode error gracefully
        assert isinstance(events, list)

    @responses.activate
    def test_fetch_missing_key_in_response(self):
        """Test handling when expected key is missing from response."""
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"unexpected_key": []},  # Missing "incidents" key
            status=200,
        )
        
        events = fetch_incidents()
        assert events == []
