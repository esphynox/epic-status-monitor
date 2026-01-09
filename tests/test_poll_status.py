"""Integration tests for poll_status.py - Main orchestration."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import responses

from src.state import JsonFileState
from src.epic_status import BASE_URL, INCIDENTS_URL, MAINTENANCE_ACTIVE_URL, MAINTENANCE_UPCOMING_URL
from src.filters import FilterConfig


@pytest.mark.integration
class TestPollStatusWorkflow:
    """Test the main polling workflow."""

    @responses.activate
    @patch('src.notifiers.telegram.TelegramNotifier.send_new_event')
    @patch('src.notifiers.telegram.TelegramNotifier.send_event_update')
    def test_full_workflow_new_event(self, mock_send_update, mock_send_new, temp_state_file, sample_incident_data):
        """Test full workflow with a new event."""
        # Mock API responses
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
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        # Mock successful notification
        mock_send_new.return_value = True
        
        # Import and run main function
        from poll_status import main
        
        # Mock filter config to return default
        with patch('poll_status.load_filter_config', return_value=FilterConfig()), \
             patch('poll_status.JsonFileState', return_value=JsonFileState(temp_state_file)), \
             patch('poll_status.TelegramNotifier', return_value=Mock(send_new_event=mock_send_new, send_event_update=mock_send_update)):
            
            result = main()
            assert result == 0
        
        # Verify notification was sent
        mock_send_new.assert_called_once()
        
        # Verify state was saved
        state = JsonFileState(temp_state_file)
        state._load()
        assert "test-incident-123" in state.seen_ids

    @responses.activate
    @patch('src.notifiers.telegram.TelegramNotifier.send_event_update')
    def test_full_workflow_updated_event(self, mock_send_update, populated_state_file, sample_incident_data):
        """Test full workflow with an updated event."""
        state = JsonFileState(populated_state_file)
        old_fingerprint = state.fingerprints["test-incident-123"]
        
        # Create updated version of incident
        updated_incident_data = sample_incident_data.copy()
        updated_incident_data["status"] = "resolved"
        updated_incident_data["incident_updates"].insert(0, {
            "id": "new-update",
            "status": "resolved",
            "body": "Issue resolved",
            "created_at": "2024-01-15T11:00:00Z",
        })
        
        # Mock API responses
        responses.add(
            responses.GET,
            INCIDENTS_URL,
            json={"incidents": [updated_incident_data]},
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
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        mock_send_update.return_value = True
        
        from poll_status import main
        
        with patch('poll_status.load_filter_config', return_value=FilterConfig()), \
             patch('poll_status.JsonFileState', return_value=JsonFileState(populated_state_file)), \
             patch('poll_status.TelegramNotifier', return_value=Mock(send_new_event=Mock(return_value=True), send_event_update=mock_send_update)):
            
            result = main()
            assert result == 0
        
        # Verify update notification was sent
        mock_send_update.assert_called_once()

    @responses.activate
    def test_full_workflow_no_new_events(self, populated_state_file, sample_incident_data):
        """Test workflow when no new or updated events."""
        # Mock API responses with same event
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
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        mock_notifier = Mock()
        mock_notifier.send_new_event.return_value = True
        mock_notifier.send_event_update.return_value = True
        
        from poll_status import main
        
        with patch('poll_status.load_filter_config', return_value=FilterConfig()), \
             patch('poll_status.JsonFileState', return_value=JsonFileState(populated_state_file)), \
             patch('poll_status.TelegramNotifier', return_value=mock_notifier):
            
            result = main()
            assert result == 0
        
        # Should not send any notifications
        mock_notifier.send_new_event.assert_not_called()
        mock_notifier.send_event_update.assert_not_called()

    @responses.activate
    def test_dry_run_mode(self, temp_state_file, sample_incident_data):
        """Test dry-run mode still updates state."""
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
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        from poll_status import main
        
        mock_notifier = Mock()
        mock_notifier.send_new_event.return_value = False  # Notification fails
        mock_notifier.send_event_update.return_value = False
        
        # Create a mock args object with dry_run=True
        mock_args = Mock()
        mock_args.dry_run = True
        
        with patch('poll_status.load_filter_config', return_value=FilterConfig()), \
             patch('poll_status.JsonFileState', return_value=JsonFileState(temp_state_file)), \
             patch('poll_status.TelegramNotifier', return_value=mock_notifier), \
             patch('poll_status.argparse.ArgumentParser.parse_args', return_value=mock_args):
            
            result = main()
            assert result == 0
        
        # State should still be updated in dry-run (even if notification fails)
        state = JsonFileState(temp_state_file)
        state._load()
        assert "test-incident-123" in state.seen_ids

    @responses.activate
    def test_filtering_works(self, temp_state_file, sample_incident_data):
        """Test that filtering is applied correctly."""
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
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        # Filter config that excludes this incident
        filter_config = FilterConfig(services=["Unreal Engine"])
        
        mock_notifier = Mock()
        mock_notifier.send_new_event.return_value = True
        
        from poll_status import main
        
        with patch('poll_status.load_filter_config', return_value=filter_config), \
             patch('poll_status.JsonFileState', return_value=JsonFileState(temp_state_file)), \
             patch('poll_status.TelegramNotifier', return_value=mock_notifier):
            
            result = main()
            assert result == 0
        
        # Should not send notification due to filtering
        mock_notifier.send_new_event.assert_not_called()

    @responses.activate
    def test_state_cleanup_on_save(self, temp_state_file, sample_incident_data):
        """Test that state cleanup happens during save."""
        # Create state with old events
        state_data = {
            "seen_ids": ["old-event-1", "old-event-2", "old-event-3"],
            "last_updates": {
                "old-event-1": "status:update-1",
                "old-event-2": "status:update-2",
                "old-event-3": "status:update-3",
            },
        }
        temp_state_file.write_text(json.dumps(state_data))
        
        # New API response with different event
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
            json={"scheduled_maintenances": []},
            status=200,
        )
        
        from poll_status import main
        
        with patch('poll_status.load_filter_config', return_value=FilterConfig()), \
             patch('poll_status.JsonFileState', return_value=JsonFileState(temp_state_file)), \
             patch('poll_status.TelegramNotifier', return_value=Mock(send_new_event=Mock(return_value=True), send_event_update=Mock(return_value=True))):
            
            result = main()
            assert result == 0
        
        # Verify cleanup happened - old events should be removed
        saved_state = JsonFileState(temp_state_file)
        saved_state._load()
        # New event should be in seen_ids
        assert "test-incident-123" in saved_state.seen_ids
