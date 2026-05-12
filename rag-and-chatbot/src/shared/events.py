"""Event system with pub/sub pattern for cross-agent communication."""

import threading
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class Event:
    """
    Event object representing a system event.

    Events are emitted when important actions occur (e.g., reservation created,
    approved, rejected) and can be subscribed to by handlers.
    """
    event_type: str  # Event type identifier
    timestamp: str  # ISO timestamp
    data: Dict[str, Any]  # Event payload
    source: str  # Source of event (e.g., "user_agent", "admin_agent")
    metadata: Dict[str, Any] = field(default_factory=dict)  # Optional metadata

    @classmethod
    def create(cls, event_type: str, data: Dict[str, Any], source: str) -> "Event":
        """
        Create a new event with current timestamp.

        Args:
            event_type: Type of event
            data: Event payload
            source: Source agent

        Returns:
            New Event instance
        """
        return cls(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data,
            source=source,
            metadata={}
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
            "source": self.source,
            "metadata": self.metadata
        }


class EventBus:
    """
    In-memory event bus with pub/sub pattern.

    Supports multiple subscribers per event type and wildcard subscriptions.
    Thread-safe for concurrent access.
    """

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._event_log: List[Event] = []
        self._max_log_size = 1000  # Keep last 1000 events

    def subscribe(self, event_type: str, handler: Callable[[Event], None]):
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Event type to subscribe to (use "*" for all events)
            handler: Callback function that receives Event objects
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]):
        """
        Unsubscribe from events.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                except ValueError:
                    pass  # Handler not in list

    def publish(self, event: Event):
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        # Log event
        with self._lock:
            self._event_log.append(event)
            # Trim log if too large
            if len(self._event_log) > self._max_log_size:
                self._event_log = self._event_log[-self._max_log_size:]

            # Get subscribers for this event type + wildcard subscribers
            handlers = (
                self._subscribers.get(event.event_type, []) +
                self._subscribers.get("*", [])
            )

        # Call handlers (outside lock to avoid blocking)
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus] Error in event handler: {e}")

    def get_event_log(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """
        Get recent events from the log.

        Args:
            event_type: Optional filter by event type
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        with self._lock:
            if event_type:
                filtered = [e for e in self._event_log if e.event_type == event_type]
                return filtered[-limit:]
            return self._event_log[-limit:]

    def clear_log(self):
        """Clear the event log."""
        with self._lock:
            self._event_log.clear()


# Global event bus instance
global_event_bus = EventBus()


def publish_event(event_type: str, data: Dict[str, Any], source: str):
    """
    Publish an event to the global event bus (convenience function).

    Args:
        event_type: Event type identifier
        data: Event payload
        source: Source of event
    """
    event = Event.create(event_type, data, source)
    global_event_bus.publish(event)


def subscribe_to_events(event_type: str, handler: Callable[[Event], None]):
    """
    Subscribe to events on the global event bus (convenience function).

    Args:
        event_type: Event type to subscribe to
        handler: Callback function
    """
    global_event_bus.subscribe(event_type, handler)
