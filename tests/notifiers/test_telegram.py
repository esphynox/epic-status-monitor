"""Tests for notifiers/telegram.py - Telegram notification backend."""

import os
from unittest.mock import Mock, patch

import pytest
import responses

from src.notifiers.telegram import TelegramNotifier
from src.epic_status import StatusEvent, StatusUpdate, Component, EventType


@pytest.mark.unit
class TestFormatMessage:
    """Test message formatting."""

    def test_format_incident_message(self, sample_incident):
        """Test formatting an incident message."""
        notifier = TelegramNotifier()
        message = notifier._format_message(sample_incident, is_update=False)
        
        assert "🚨 NEW INCIDENT" in message
        assert "Epic Games Store Login Issues" in message
        assert "Status: Investigating" in message
        assert "Impact: 🟠 Major" in message
        assert "Epic Games Store" in message or "Launcher" in message
        assert "https://stspg.io/test123" in message

    def test_format_maintenance_message(self, sample_maintenance):
        """Test formatting a maintenance message."""
        notifier = TelegramNotifier()
        message = notifier._format_message(sample_maintenance, is_update=False)
        
        assert "🔧 SCHEDULED MAINTENANCE" in message
        assert "Rocket League Servers" in message
        assert "Scheduled:" in message

    def test_format_update_message(self, sample_incident):
        """Test formatting an update message."""
        notifier = TelegramNotifier()
        message = notifier._format_message(sample_incident, is_update=True)
        
        assert "🔄 UPDATE" in message

    def test_format_message_truncates_long_body(self, sample_incident):
        """Test message truncation for long update bodies."""
        notifier = TelegramNotifier()
        
        # Create event with very long body
        long_body_event = StatusEvent(
            id="long-body",
            name="Long Event",
            status="investigating",
            impact="minor",
            shortlink="https://stspg.io/test",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[
                StatusUpdate(
                    id="update-1",
                    status="investigating",
                    body="A" * 600,  # Very long body
                    created_at="2024-01-15T10:30:00Z",
                )
            ],
            components=[],
            event_type=EventType.INCIDENT,
        )
        
        message = notifier._format_message(long_body_event, is_update=False)
        # Should truncate to 500 chars
        assert len(message) < 1000  # Reasonable limit
        assert "..." in message

    def test_format_message_status_emoji(self):
        """Test status emoji selection."""
        notifier = TelegramNotifier()
        
        investigating = StatusEvent(
            id="inv",
            name="Investigating",
            status="investigating",
            impact="minor",
            shortlink="https://stspg.io/test",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        
        resolved = StatusEvent(
            id="res",
            name="Resolved",
            status="resolved",
            impact="none",
            shortlink="https://stspg.io/test",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        
        inv_message = notifier._format_message(investigating, is_update=False)
        res_message = notifier._format_message(resolved, is_update=False)
        
        assert "🔍" in inv_message  # investigating emoji
        assert "✅" in res_message  # resolved emoji

    def test_format_message_impact_emoji(self):
        """Test impact emoji selection."""
        notifier = TelegramNotifier()
        
        critical = StatusEvent(
            id="critical",
            name="Critical",
            status="investigating",
            impact="critical",
            shortlink="https://stspg.io/test",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        
        message = notifier._format_message(critical, is_update=False)
        assert "🔴" in message  # critical emoji

    def test_format_message_no_components(self):
        """Test formatting event with no components."""
        notifier = TelegramNotifier()
        
        event = StatusEvent(
            id="no-comp",
            name="No Components",
            status="investigating",
            impact="minor",
            shortlink="https://stspg.io/test",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        
        message = notifier._format_message(event, is_update=False)
        # Should not crash, message should be valid
        assert len(message) > 0


@pytest.mark.integration
class TestSendMessage:
    """Test sending messages via Telegram API."""

    @responses.activate
    def test_send_message_success(self):
        """Test successful message send."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"ok": True, "result": {"message_id": 1}},
            status=200,
        )
        
        success = notifier._send_message("Test message")
        assert success is True

    @responses.activate
    def test_send_message_api_error(self):
        """Test handling of Telegram API errors."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"ok": False, "description": "Bad Request"},
            status=400,
        )
        
        success = notifier._send_message("Test message")
        assert success is False

    @responses.activate
    def test_send_message_network_error(self):
        """Test handling of network errors."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            body=ConnectionError("Network error"),
        )
        
        success = notifier._send_message("Test message")
        assert success is False

    @responses.activate
    def test_send_message_timeout(self):
        """Test handling of timeouts."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345", timeout=1)
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            body=TimeoutError("Request timeout"),
        )
        
        success = notifier._send_message("Test message")
        assert success is False

    def test_send_message_not_configured(self, sample_incident):
        """Test sending when not configured prints to console."""
        notifier = TelegramNotifier()  # No token or chat_id
        
        success = notifier._send_message("Test message")
        assert success is False

    def test_send_message_strips_html_in_console(self, sample_incident):
        """Test HTML tag stripping when printing to console."""
        notifier = TelegramNotifier()
        message = notifier._format_message(sample_incident, is_update=False)
        
        # When not configured, should strip HTML tags
        with patch('builtins.print') as mock_print:
            notifier._send_message(message)
            # Check that printed message doesn't contain HTML tags
            printed_args = ' '.join(str(call) for call in mock_print.call_args_list)
            assert '<b>' not in printed_args or '&lt;b&gt;' in printed_args


@pytest.mark.unit
class TestSendNewEvent:
    """Test send_new_event method."""

    @responses.activate
    def test_send_new_event_success(self, sample_incident):
        """Test successfully sending new event notification."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"ok": True},
            status=200,
        )
        
        success = notifier.send_new_event(sample_incident)
        assert success is True

    @responses.activate
    def test_send_new_event_failure(self, sample_incident):
        """Test handling of send failure."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"ok": False},
            status=400,
        )
        
        success = notifier.send_new_event(sample_incident)
        assert success is False


@pytest.mark.unit
class TestSendEventUpdate:
    """Test send_event_update method."""

    @responses.activate
    def test_send_event_update_success(self, sample_incident):
        """Test successfully sending event update notification."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        
        responses.add(
            responses.POST,
            "https://api.telegram.org/bottest-token/sendMessage",
            json={"ok": True},
            status=200,
        )
        
        success = notifier.send_event_update(sample_incident)
        assert success is True


@pytest.mark.unit
class TestTelegramNotifierConfig:
    """Test TelegramNotifier configuration."""

    def test_init_with_args(self):
        """Test initialization with explicit token and chat_id."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        assert notifier.token == "test-token"
        assert notifier.chat_id == "12345"

    def test_init_from_env(self, mock_env_vars):
        """Test initialization from environment variables."""
        mock_env_vars(TELEGRAM_TOKEN="env-token", TELEGRAM_CHAT_ID="env-chat-id")
        notifier = TelegramNotifier()
        assert notifier.token == "env-token"
        assert notifier.chat_id == "env-chat-id"

    def test_is_configured_true(self):
        """Test is_configured returns True when both token and chat_id set."""
        notifier = TelegramNotifier(token="test-token", chat_id="12345")
        assert notifier.is_configured is True

    def test_is_configured_false_no_token(self):
        """Test is_configured returns False when token missing."""
        notifier = TelegramNotifier(chat_id="12345")
        assert notifier.is_configured is False

    def test_is_configured_false_no_chat_id(self):
        """Test is_configured returns False when chat_id missing."""
        notifier = TelegramNotifier(token="test-token")
        assert notifier.is_configured is False

    def test_is_configured_false_both_missing(self):
        """Test is_configured returns False when both missing."""
        notifier = TelegramNotifier()
        assert notifier.is_configured is False
