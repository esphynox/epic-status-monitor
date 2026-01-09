"""Base notifier interface."""

from abc import ABC, abstractmethod

from ..epic_status import StatusEvent


class Notifier(ABC):
    """Abstract base class for notification backends."""

    @abstractmethod
    def send_new_event(self, event: StatusEvent) -> bool:
        """
        Send notification for a new event (incident or maintenance).
        
        Args:
            event: The new event to notify about.
            
        Returns:
            True if notification was sent successfully.
        """
        pass

    @abstractmethod
    def send_event_update(self, event: StatusEvent) -> bool:
        """
        Send notification for an updated event.
        
        Args:
            event: The updated event to notify about.
            
        Returns:
            True if notification was sent successfully.
        """
        pass

    def send(self, event: StatusEvent, is_update: bool = False) -> bool:
        """
        Send notification for an event.
        
        Args:
            event: The event to notify about.
            is_update: Whether this is an update to an existing event.
            
        Returns:
            True if notification was sent successfully.
        """
        if is_update:
            return self.send_event_update(event)
        return self.send_new_event(event)
