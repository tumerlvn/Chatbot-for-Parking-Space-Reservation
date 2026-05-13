"""Notification manager for handling system events."""

import logging
from typing import Dict, Any, Optional
from .events import Event, global_event_bus, subscribe_to_events

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages notifications for system events.

    Handles event subscriptions and provides notification delivery mechanisms
    (console, email, webhooks, etc.).
    """

    def __init__(self):
        """Initialize notification manager."""
        self.enabled = True
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up default event handlers."""
        # Subscribe to all events for console logging
        subscribe_to_events("*", self._console_handler)

        # Subscribe to specific events for specialized handling
        subscribe_to_events("reservation_created", self._handle_reservation_created)
        subscribe_to_events("reservation_approved", self._handle_reservation_approved)
        subscribe_to_events("reservation_rejected", self._handle_reservation_rejected)

    def _console_handler(self, event: Event):
        """
        Default console handler - prints all events.

        Args:
            event: Event to handle
        """
        if not self.enabled:
            return

        logger.info(f"[EVENT] {event.event_type}")
        logger.info(f"  Source: {event.source}")
        logger.info(f"  Time: {event.timestamp}")
        if event.data:
            logger.info(f"  Data:")
            for key, value in event.data.items():
                logger.info(f"    - {key}: {value}")

    def _handle_reservation_created(self, event: Event):
        """
        Handle reservation_created events.

        In production, this could:
        - Send confirmation email to user
        - Notify admins of pending approval
        - Update external systems

        Args:
            event: Reservation created event
        """
        if not self.enabled:
            return

        data = event.data
        logger.info(f"📝 New reservation created!")
        logger.info(f"   Reservation ID: {data.get('reservation_id')}")
        logger.info(f"   User: {data.get('user_name')}")
        logger.info(f"   Status: Pending admin approval")

    def _handle_reservation_approved(self, event: Event):
        """
        Handle reservation_approved events.

        In production, this could:
        - Send approval email to user
        - Generate QR code
        - Update parking system

        Args:
            event: Reservation approved event
        """
        if not self.enabled:
            return

        data = event.data
        logger.info(f"✅ Reservation approved!")
        logger.info(f"   Reservation ID: {data.get('reservation_id')}")
        if data.get('admin_notes'):
            logger.info(f"   Admin notes: {data.get('admin_notes')}")

    def _handle_reservation_rejected(self, event: Event):
        """
        Handle reservation_rejected events.

        In production, this could:
        - Send rejection email to user
        - Provide alternative suggestions
        - Log rejection reason

        Args:
            event: Reservation rejected event
        """
        if not self.enabled:
            return

        data = event.data
        logger.info(f"❌ Reservation rejected")
        logger.info(f"   Reservation ID: {data.get('reservation_id')}")
        if data.get('admin_notes'):
            logger.info(f"   Reason: {data.get('admin_notes')}")

    def enable(self):
        """Enable notifications."""
        self.enabled = True

    def disable(self):
        """Disable notifications."""
        self.enabled = False

    def send_custom_notification(
        self,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Send a custom notification.

        Args:
            event_type: Type of notification
            message: Notification message
            data: Optional additional data
        """
        if not self.enabled:
            return

        logger.info(f"[NOTIFICATION] {event_type}")
        logger.info(f"  {message}")
        if data:
            logger.info(f"  Data: {data}")


# Global notification manager instance
global_notification_manager = NotificationManager()


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    return global_notification_manager
