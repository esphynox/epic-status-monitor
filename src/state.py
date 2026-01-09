"""
State management for tracking seen incidents.
Currently uses a JSON file, but interface allows swapping to Redis/KV.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .epic_status import StatusEvent


class StateBackend(ABC):
    """Abstract interface for state storage backends."""

    @abstractmethod
    def is_new_event(self, event: StatusEvent) -> bool:
        """Check if this event has never been seen before."""
        pass

    @abstractmethod
    def is_updated_event(self, event: StatusEvent) -> bool:
        """Check if this event has new updates since last seen."""
        pass

    @abstractmethod
    def mark_seen(self, event: StatusEvent) -> None:
        """Mark an event as seen with its current fingerprint."""
        pass

    @abstractmethod
    def cleanup(self, current_events: list[StatusEvent]) -> None:
        """Clean up old resolved events from state."""
        pass

    @abstractmethod
    def save(self) -> None:
        """Persist state changes."""
        pass


class JsonFileState(StateBackend):
    """JSON file-based state storage."""

    def __init__(self, file_path: Path | str | None = None):
        if file_path is None:
            file_path = Path(__file__).parent.parent / "seen_incidents.json"
        self.file_path = Path(file_path)
        self._load()

    def _load(self) -> None:
        """Load state from JSON file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    data = json.load(f)
                    self.seen_ids: set[str] = set(data.get("seen_ids", []))
                    self.fingerprints: dict[str, str] = data.get("last_updates", {})
            except json.JSONDecodeError:
                print("⚠️ State file corrupted, starting fresh")
                self.seen_ids = set()
                self.fingerprints = {}
        else:
            self.seen_ids = set()
            self.fingerprints = {}

    def is_new_event(self, event: StatusEvent) -> bool:
        """Check if this event has never been seen before."""
        return event.id not in self.seen_ids

    def is_updated_event(self, event: StatusEvent) -> bool:
        """Check if this event has new updates since last seen."""
        if event.id not in self.seen_ids:
            return False
        return self.fingerprints.get(event.id) != event.fingerprint

    def mark_seen(self, event: StatusEvent) -> None:
        """Mark an event as seen with its current fingerprint."""
        self.seen_ids.add(event.id)
        self.fingerprints[event.id] = event.fingerprint

    def cleanup(self, current_events: list[StatusEvent], max_tracked: int = 100) -> None:
        """
        Clean up resolved events from tracking.
        Keeps a limited history to prevent re-notification on API flaps.
        """
        current_ids = {e.id for e in current_events}
        resolved_ids = self.seen_ids - current_ids

        if resolved_ids:
            print(f"🧹 Cleaning up {len(resolved_ids)} resolved incident(s)")

        # Limit total tracked IDs to prevent unbounded growth
        if len(self.seen_ids) > max_tracked:
            all_ids = list(self.seen_ids)
            self.seen_ids = set(all_ids[-max_tracked:])

        # Clean fingerprints for IDs we're no longer tracking
        self.fingerprints = {
            k: v for k, v in self.fingerprints.items() 
            if k in self.seen_ids
        }

    def save(self) -> None:
        """Persist state to JSON file."""
        data = {
            "seen_ids": list(self.seen_ids),
            "last_updates": self.fingerprints,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    @property
    def tracked_count(self) -> int:
        """Number of incidents currently being tracked."""
        return len(self.seen_ids)
