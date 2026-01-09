"""
Epic Games Status API client.
Fetches and parses incident and maintenance data from status.epicgames.com.
"""

from dataclasses import dataclass
from enum import Enum

import requests

# Statuspage.io API endpoints
BASE_URL = "https://status.epicgames.com/api/v2"
INCIDENTS_URL = f"{BASE_URL}/incidents/unresolved.json"
MAINTENANCE_ACTIVE_URL = f"{BASE_URL}/scheduled-maintenances/active.json"
MAINTENANCE_UPCOMING_URL = f"{BASE_URL}/scheduled-maintenances/upcoming.json"


class EventType(Enum):
    """Type of status event."""
    INCIDENT = "incident"
    MAINTENANCE = "maintenance"


@dataclass
class StatusUpdate:
    """A single update within an incident or maintenance."""
    id: str
    status: str
    body: str
    created_at: str


@dataclass
class Component:
    """An affected service component."""
    id: str
    name: str
    status: str


@dataclass
class StatusEvent:
    """An Epic Games status event (incident or scheduled maintenance)."""
    id: str
    name: str
    status: str
    impact: str
    shortlink: str
    created_at: str
    updated_at: str
    updates: list[StatusUpdate]
    components: list[Component]
    event_type: EventType
    scheduled_for: str | None = None  # For maintenance only
    scheduled_until: str | None = None  # For maintenance only

    @property
    def fingerprint(self) -> str:
        """
        Unique fingerprint that changes when event is updated.
        Used to detect updates to existing events.
        """
        latest_update_id = self.updates[0].id if self.updates else ""
        return f"{self.status}:{latest_update_id}"

    @property
    def latest_update(self) -> StatusUpdate | None:
        """Get the most recent update, if any."""
        return self.updates[0] if self.updates else None

    @property
    def component_names(self) -> list[str]:
        """Get list of affected component names."""
        return [c.name for c in self.components]

    @property
    def is_maintenance(self) -> bool:
        """Check if this is a scheduled maintenance."""
        return self.event_type == EventType.MAINTENANCE

    @property
    def is_incident(self) -> bool:
        """Check if this is an incident."""
        return self.event_type == EventType.INCIDENT


def _parse_event(data: dict, event_type: EventType) -> StatusEvent:
    """Parse raw API data into a StatusEvent object."""
    # Handle both incident_updates and scheduled_maintenance_updates
    updates_key = "incident_updates" if event_type == EventType.INCIDENT else "incident_updates"
    raw_updates = data.get(updates_key, [])
    
    updates = [
        StatusUpdate(
            id=u.get("id", ""),
            status=u.get("status", ""),
            body=u.get("body", ""),
            created_at=u.get("created_at", ""),
        )
        for u in raw_updates
    ]

    components = [
        Component(
            id=c.get("id", ""),
            name=c.get("name", ""),
            status=c.get("status", ""),
        )
        for c in data.get("components", [])
    ]

    return StatusEvent(
        id=data.get("id", ""),
        name=data.get("name", "Unknown Event"),
        status=data.get("status", "unknown"),
        impact=data.get("impact", "unknown"),
        shortlink=data.get("shortlink", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        updates=updates,
        components=components,
        event_type=event_type,
        scheduled_for=data.get("scheduled_for"),
        scheduled_until=data.get("scheduled_until"),
    )


def _fetch_from_url(url: str, key: str, event_type: EventType, timeout: int = 30) -> list[StatusEvent]:
    """Fetch events from a specific API URL."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        raw_events = resp.json().get(key, [])
        return [_parse_event(data, event_type) for data in raw_events]
    except (requests.RequestException, ConnectionError, TimeoutError) as e:
        print(f"❌ Failed to fetch from {url}: {e}")
        return []


def fetch_incidents(timeout: int = 30) -> list[StatusEvent]:
    """
    Fetch unresolved incidents from Epic Games status API.
    
    Args:
        timeout: Request timeout in seconds.
        
    Returns:
        List of StatusEvent objects (incidents only).
    """
    return _fetch_from_url(INCIDENTS_URL, "incidents", EventType.INCIDENT, timeout)


def fetch_active_maintenances(timeout: int = 30) -> list[StatusEvent]:
    """
    Fetch active scheduled maintenances from Epic Games status API.
    
    Args:
        timeout: Request timeout in seconds.
        
    Returns:
        List of StatusEvent objects (active maintenances only).
    """
    return _fetch_from_url(MAINTENANCE_ACTIVE_URL, "scheduled_maintenances", EventType.MAINTENANCE, timeout)


def fetch_upcoming_maintenances(timeout: int = 30) -> list[StatusEvent]:
    """
    Fetch upcoming scheduled maintenances from Epic Games status API.
    
    Args:
        timeout: Request timeout in seconds.
        
    Returns:
        List of StatusEvent objects (upcoming maintenances only).
    """
    return _fetch_from_url(MAINTENANCE_UPCOMING_URL, "scheduled_maintenances", EventType.MAINTENANCE, timeout)


def fetch_all_active_events(timeout: int = 30) -> list[StatusEvent]:
    """
    Fetch all active events: unresolved incidents + active maintenances.
    
    Args:
        timeout: Request timeout in seconds.
        
    Returns:
        List of all active StatusEvent objects.
    """
    incidents = fetch_incidents(timeout)
    maintenances = fetch_active_maintenances(timeout)
    return incidents + maintenances


def fetch_all_events(include_upcoming: bool = True, timeout: int = 30) -> list[StatusEvent]:
    """
    Fetch all events: incidents + active maintenances + optionally upcoming maintenances.
    
    Args:
        include_upcoming: Whether to include upcoming scheduled maintenances.
        timeout: Request timeout in seconds.
        
    Returns:
        List of all StatusEvent objects.
    """
    events = fetch_all_active_events(timeout)
    if include_upcoming:
        events += fetch_upcoming_maintenances(timeout)
    return events
