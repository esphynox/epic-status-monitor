"""Telegram notification backend."""

import os
import re

import requests

from ..epic_status import StatusEvent, EventType
from .base import Notifier


class TelegramNotifier(Notifier):
    """Send notifications via Telegram Bot API."""

    STATUS_EMOJI = {
        # Incident statuses
        "investigating": "🔍",
        "identified": "🔎",
        "monitoring": "👀",
        "resolved": "✅",
        "postmortem": "📝",
        # Maintenance statuses
        "scheduled": "📅",
        "in_progress": "🔧",
        "verifying": "🔎",
        "completed": "✅",
    }

    IMPACT_EMOJI = {
        "none": "⚪",
        "minor": "🟡",
        "major": "🟠",
        "critical": "🔴",
        "maintenance": "🔵",
    }

    def __init__(
        self,
        token: str | None = None,
        chat_id: str | None = None,
        timeout: int = 30,
    ):
        """
        Initialize Telegram notifier.
        
        Args:
            token: Bot token from @BotFather. Falls back to TELEGRAM_TOKEN env var.
            chat_id: Chat ID to send messages to. Falls back to TELEGRAM_CHAT_ID env var.
            timeout: Request timeout in seconds.
        """
        self.token = token or os.environ.get("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        """Check if Telegram credentials are configured."""
        return bool(self.token and self.chat_id)

    def _format_message(self, event: StatusEvent, is_update: bool = False) -> str:
        """Format an event into a Telegram message."""
        status_emoji = self.STATUS_EMOJI.get(event.status, "🚨")
        
        # Use maintenance impact for maintenance events
        if event.is_maintenance:
            impact_emoji = self.IMPACT_EMOJI.get("maintenance", "🔵")
        else:
            impact_emoji = self.IMPACT_EMOJI.get(event.impact, "⚪")

        # Header based on event type and whether it's an update
        if is_update:
            header = "🔄 UPDATE"
        elif event.is_maintenance:
            header = "🔧 SCHEDULED MAINTENANCE"
        else:
            header = "🚨 NEW INCIDENT"

        lines = [
            header,
            "",
            f"{status_emoji} <b>{event.name}</b>",
            f"Status: {event.status.replace('_', ' ').title()}",
        ]
        
        # Show impact for incidents only
        if event.is_incident:
            lines.append(f"Impact: {impact_emoji} {event.impact.title()}")
        
        # Show scheduled time for maintenance
        if event.is_maintenance and event.scheduled_for:
            # Parse and format the time nicely
            scheduled = event.scheduled_for
            if event.scheduled_until:
                lines.append(f"⏰ Scheduled: {scheduled[:16].replace('T', ' ')} → {event.scheduled_until[11:16]} UTC")
            else:
                lines.append(f"⏰ Scheduled: {scheduled[:16].replace('T', ' ')} UTC")

        # Add latest update body if available
        if event.latest_update and event.latest_update.body:
            body = event.latest_update.body
            # Truncate long messages
            if len(body) > 500:
                body = body[:497] + "..."
            lines.append("")
            lines.append(f"📋 <i>{body}</i>")

        # Add affected components
        if event.component_names:
            components = ", ".join(event.component_names[:5])
            lines.append("")
            lines.append(f"🎮 Affected: {components}")

        # Add link
        if event.shortlink:
            lines.append("")
            lines.append(f"🔗 {event.shortlink}")

        return "\n".join(lines)

    def _send_message(self, message: str) -> bool:
        """Send a message via Telegram API."""
        if not self.is_configured:
            print("⚠️ Telegram not configured, printing message instead:")
            print("-" * 50)
            # Strip HTML tags for console output
            clean_message = re.sub(r'<[^>]+>', '', message)
            print(clean_message)
            print("-" * 50)
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            print("✅ Telegram message sent successfully")
            return True
        except (requests.RequestException, ConnectionError, TimeoutError) as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False

    def send_new_event(self, event: StatusEvent) -> bool:
        """Send notification for a new event."""
        message = self._format_message(event, is_update=False)
        return self._send_message(message)

    def send_event_update(self, event: StatusEvent) -> bool:
        """Send notification for an updated event."""
        message = self._format_message(event, is_update=True)
        return self._send_message(message)
