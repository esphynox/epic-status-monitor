"""Tests for state.py - State management."""

import json
from pathlib import Path

import pytest

from src.state import JsonFileState
from src.epic_status import StatusEvent, StatusUpdate, Component, EventType


@pytest.mark.unit
class TestJsonFileState:
    """Test JsonFileState class."""

    def test_init_creates_new_file(self, temp_state_file):
        """Test initialization creates new state file."""
        state = JsonFileState(temp_state_file)
        assert state.seen_ids == set()
        assert state.fingerprints == {}

    def test_init_loads_existing_file(self, populated_state_file):
        """Test initialization loads existing state file."""
        state = JsonFileState(populated_state_file)
        assert len(state.seen_ids) == 1
        assert "test-incident-123" in state.seen_ids

    def test_init_handles_corrupted_file(self, temp_state_file):
        """Test initialization handles corrupted JSON file."""
        temp_state_file.write_text("invalid json{")
        
        state = JsonFileState(temp_state_file)
        # Should start fresh on corruption
        assert state.seen_ids == set()
        assert state.fingerprints == {}

    def test_is_new_event_true(self, empty_state_file, sample_incident):
        """Test is_new_event returns True for unseen event."""
        state = JsonFileState(empty_state_file)
        assert state.is_new_event(sample_incident) is True

    def test_is_new_event_false(self, populated_state_file, sample_incident):
        """Test is_new_event returns False for seen event."""
        state = JsonFileState(populated_state_file)
        assert state.is_new_event(sample_incident) is False

    def test_is_updated_event_false_for_new(self, empty_state_file, sample_incident):
        """Test is_updated_event returns False for new event."""
        state = JsonFileState(empty_state_file)
        assert state.is_updated_event(sample_incident) is False

    def test_is_updated_event_true_when_changed(self, populated_state_file, sample_incident):
        """Test is_updated_event returns True when fingerprint changed."""
        state = JsonFileState(populated_state_file)
        
        # Change the event's fingerprint by modifying its status
        updated_event = StatusEvent(
            id=sample_incident.id,
            name=sample_incident.name,
            status="resolved",  # Changed from "investigating"
            impact=sample_incident.impact,
            shortlink=sample_incident.shortlink,
            created_at=sample_incident.created_at,
            updated_at=sample_incident.updated_at,
            updates=[
                StatusUpdate(
                    id="new-update",
                    status="resolved",
                    body="Issue resolved",
                    created_at="2024-01-15T11:00:00Z",
                )
            ],
            components=sample_incident.components,
            event_type=sample_incident.event_type,
        )
        
        assert state.is_updated_event(updated_event) is True

    def test_is_updated_event_false_when_unchanged(self, populated_state_file, sample_incident):
        """Test is_updated_event returns False when fingerprint unchanged."""
        state = JsonFileState(populated_state_file)
        assert state.is_updated_event(sample_incident) is False

    def test_mark_seen(self, empty_state_file, sample_incident):
        """Test mark_seen adds event to tracking."""
        state = JsonFileState(empty_state_file)
        state.mark_seen(sample_incident)
        
        assert sample_incident.id in state.seen_ids
        assert state.fingerprints[sample_incident.id] == sample_incident.fingerprint

    def test_mark_seen_updates_fingerprint(self, populated_state_file, sample_incident):
        """Test mark_seen updates fingerprint for existing event."""
        state = JsonFileState(populated_state_file)
        old_fingerprint = state.fingerprints[sample_incident.id]
        
        # Create updated version
        updated_event = StatusEvent(
            id=sample_incident.id,
            name=sample_incident.name,
            status="resolved",
            impact=sample_incident.impact,
            shortlink=sample_incident.shortlink,
            created_at=sample_incident.created_at,
            updated_at=sample_incident.updated_at,
            updates=[
                StatusUpdate(
                    id="new-update",
                    status="resolved",
                    body="Fixed",
                    created_at="2024-01-15T11:00:00Z",
                )
            ],
            components=sample_incident.components,
            event_type=sample_incident.event_type,
        )
        
        state.mark_seen(updated_event)
        assert state.fingerprints[sample_incident.id] != old_fingerprint
        assert state.fingerprints[sample_incident.id] == updated_event.fingerprint

    def test_cleanup_removes_resolved_events(self, temp_state_file):
        """Test cleanup removes events that are no longer active."""
        # Create state with multiple events
        data = {
            "seen_ids": ["event-1", "event-2", "event-3"],
            "last_updates": {
                "event-1": "status:update-1",
                "event-2": "status:update-2",
                "event-3": "status:update-3",
            },
        }
        temp_state_file.write_text(json.dumps(data))
        state = JsonFileState(temp_state_file)
        
        # Only event-2 is still current
        current_events = [
            StatusEvent(
                id="event-2",
                name="Current Event",
                status="investigating",
                impact="minor",
                shortlink="https://stspg.io/test",
                created_at="2024-01-15T10:00:00Z",
                updated_at="2024-01-15T10:00:00Z",
                updates=[],
                components=[],
                event_type=EventType.INCIDENT,
            )
        ]
        
        state.cleanup(current_events)
        
        # event-2 should still be tracked, others removed
        assert "event-2" in state.seen_ids
        # event-1 and event-3 should be in recent history (slice(-50))

    def test_cleanup_limits_tracked_count(self, temp_state_file):
        """Test cleanup enforces max_tracked limit."""
        # Create state with more than max_tracked events
        max_tracked = 100
        many_ids = [f"event-{i}" for i in range(150)]
        data = {
            "seen_ids": many_ids,
            "last_updates": {id: "status:update" for id in many_ids},
        }
        temp_state_file.write_text(json.dumps(data))
        state = JsonFileState(temp_state_file)
        
        state.cleanup([], max_tracked=max_tracked)
        
        # Should keep only the last max_tracked events
        assert len(state.seen_ids) <= max_tracked

    def test_cleanup_removes_orphaned_fingerprints(self, temp_state_file):
        """Test cleanup removes fingerprints for untracked IDs."""
        data = {
            "seen_ids": ["event-1"],
            "last_updates": {
                "event-1": "status:update-1",
                "event-2": "status:update-2",  # Orphaned
            },
        }
        temp_state_file.write_text(json.dumps(data))
        state = JsonFileState(temp_state_file)
        
        state.cleanup([])
        
        assert "event-2" not in state.fingerprints
        assert "event-1" in state.fingerprints or "event-1" not in state.seen_ids

    def test_save_persists_state(self, empty_state_file, sample_incident):
        """Test save writes state to file."""
        state = JsonFileState(empty_state_file)
        state.mark_seen(sample_incident)
        state.save()
        
        # Reload and verify
        saved_data = json.loads(empty_state_file.read_text())
        assert sample_incident.id in saved_data["seen_ids"]
        assert saved_data["last_updates"][sample_incident.id] == sample_incident.fingerprint
        assert "last_checked" in saved_data

    def test_tracked_count_property(self, populated_state_file):
        """Test tracked_count property."""
        state = JsonFileState(populated_state_file)
        assert state.tracked_count == 1

    def test_load_with_missing_fields(self, temp_state_file):
        """Test loading state file with missing fields."""
        temp_state_file.write_text(json.dumps({"seen_ids": ["event-1"]}))
        
        state = JsonFileState(temp_state_file)
        # Should handle missing "last_updates" gracefully
        assert "event-1" in state.seen_ids
        assert isinstance(state.fingerprints, dict)
