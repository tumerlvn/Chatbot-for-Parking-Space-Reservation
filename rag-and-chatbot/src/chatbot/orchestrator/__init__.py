"""LangGraph orchestrator for multi-agent parking reservation system."""

from .graph import create_orchestrator_graph
from .state import OrchestratorState

# Initialize notification manager and metrics on import
from ...shared import (
    global_notification_manager,
    global_metrics,
    subscribe_to_events
)


# Set up metrics tracking for events
def _setup_metrics_handlers():
    """Set up event handlers for metrics tracking."""
    from ...shared import Event

    def on_reservation_created(event: Event):
        global_metrics.record_reservation_created()

    def on_reservation_approved(event: Event):
        global_metrics.record_reservation_approved()

    def on_reservation_rejected(event: Event):
        global_metrics.record_reservation_rejected()

    subscribe_to_events("reservation_created", on_reservation_created)
    subscribe_to_events("reservation_approved", on_reservation_approved)
    subscribe_to_events("reservation_rejected", on_reservation_rejected)


_setup_metrics_handlers()

__all__ = ["create_orchestrator_graph", "OrchestratorState"]
