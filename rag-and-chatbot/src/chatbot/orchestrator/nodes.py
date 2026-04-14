"""Orchestrator nodes for routing and coordination."""

import time
from datetime import datetime
from typing import Dict, Any

from .state import OrchestratorState
from .subgraphs import (
    wrap_user_subgraph,
    wrap_admin_subgraph,
    map_to_user_state,
    map_to_admin_state,
    map_from_user_result,
    map_from_admin_result
)
from ...shared import publish_event, global_metrics


# Lazy-load subgraphs (created once on first use)
_user_graph = None
_admin_graph = None


def get_user_graph():
    """Get or create user agent graph."""
    global _user_graph
    if _user_graph is None:
        _user_graph = wrap_user_subgraph()
    return _user_graph


def get_admin_graph():
    """Get or create admin agent graph."""
    global _admin_graph
    if _admin_graph is None:
        _admin_graph = wrap_admin_subgraph()
    return _admin_graph


def supervisor_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Supervisor node - routes to appropriate agent subgraph.

    This is the main orchestration logic. It:
    1. Checks the mode (user/admin)
    2. Routes to the appropriate subgraph
    3. Collects metrics
    4. Returns result

    Args:
        state: Current orchestrator state

    Returns:
        Updated state with result from subgraph
    """
    mode = state.get("mode", "user")
    start_time = time.time()

    print(f"[Orchestrator] Routing to {mode} agent")

    try:
        if mode == "user":
            # Route to user agent
            user_graph = get_user_graph()
            user_state = map_to_user_state(state)

            # Configure with thread_id
            config = {"configurable": {"thread_id": state.get("thread_id", "default_thread")}}

            # Invoke user subgraph
            result = user_graph.invoke(user_state, config)

            # Map result back
            mapped_result = map_from_user_result(result)

            # Detect events from result
            events = detect_user_events(result)

        elif mode == "admin":
            # Route to admin agent
            admin_graph = get_admin_graph()
            admin_state = map_to_admin_state(state)

            # Configure with thread_id
            config = {"configurable": {"thread_id": state.get("thread_id", "admin_admin1")}}

            # Invoke admin subgraph (may hit interrupt)
            result = admin_graph.invoke(admin_state, config)

            # Map result back
            mapped_result = map_from_admin_result(result)

            # Detect events from result
            events = detect_admin_events(result)

        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Record metrics in global metrics collector
        elapsed_time = time.time() - start_time
        global_metrics.record_request(mode, elapsed_time, error=False)

        # Also keep local metrics for backward compatibility
        metrics = state.get("metrics", {})
        metrics["last_request_time"] = elapsed_time
        metrics["total_requests"] = metrics.get("total_requests", 0) + 1

        return {
            "result": mapped_result,
            "events": events,
            "metrics": metrics,
            "error": None
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[Orchestrator] Error in supervisor_node: {e}")

        # Record error in global metrics
        global_metrics.record_request(mode, elapsed_time, error=True)

        metrics = state.get("metrics", {})
        metrics["last_request_time"] = elapsed_time
        metrics["error_count"] = metrics.get("error_count", 0) + 1

        return {
            "result": None,
            "events": [],
            "metrics": metrics,
            "error": str(e)
        }


def detect_user_events(result: Dict[str, Any]) -> list:
    """
    Detect events from user agent result.

    Args:
        result: User agent result

    Returns:
        List of events
    """
    events = []
    reservation_data = result.get("reservation_data", {})

    # Check if reservation was created
    if reservation_data.get("reservation_id") and reservation_data.get("status") == "pending":
        events.append({
            "event_type": "reservation_created",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "reservation_id": reservation_data.get("reservation_id"),
                "user_name": reservation_data.get("name"),
                "car_number": reservation_data.get("car_number"),
                "start_time": reservation_data.get("start_time"),
                "end_time": reservation_data.get("end_time")
            },
            "source": "user_agent"
        })

    return events


def detect_admin_events(result: Dict[str, Any]) -> list:
    """
    Detect events from admin agent result.

    Args:
        result: Admin agent result

    Returns:
        List of events
    """
    events = []
    action_data = result.get("action_data", {})

    # Check if action was completed
    if action_data.get("completed"):
        action_type = action_data.get("action_type")
        reservation_id = action_data.get("reservation_id")

        if action_type == "approve":
            events.append({
                "event_type": "reservation_approved",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "reservation_id": reservation_id,
                    "admin_notes": action_data.get("admin_notes", "")
                },
                "source": "admin_agent"
            })
        elif action_type == "reject":
            events.append({
                "event_type": "reservation_rejected",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "reservation_id": reservation_id,
                    "admin_notes": action_data.get("admin_notes", "")
                },
                "source": "admin_agent"
            })

    return events


def notification_hub_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Notification hub - broadcasts events to the event bus.

    Publishes detected events to the global event bus, which triggers
    registered handlers (notifications, logging, etc.).

    Args:
        state: Current orchestrator state

    Returns:
        Empty dict (no state changes)
    """
    events = state.get("events", [])

    for event_dict in events:
        # Publish each event to the global event bus
        publish_event(
            event_type=event_dict.get("event_type"),
            data=event_dict.get("data", {}),
            source=event_dict.get("source", "orchestrator")
        )

    return {}


def health_monitor_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Health monitor - collects and displays metrics.

    Args:
        state: Current orchestrator state

    Returns:
        Empty dict (no state changes)
    """
    metrics = state.get("metrics", {})

    # Display local metrics for this request
    if metrics:
        print(f"\n[METRICS] Total requests: {metrics.get('total_requests', 0)}")
        print(f"[METRICS] Last request time: {metrics.get('last_request_time', 0):.3f}s")
        if metrics.get("error_count"):
            print(f"[METRICS] Errors: {metrics.get('error_count', 0)}")

    # Periodically display global metrics summary (every 10 requests)
    if global_metrics.total_requests > 0 and global_metrics.total_requests % 10 == 0:
        print("\n[GLOBAL METRICS SUMMARY]")
        snapshot = global_metrics.get_snapshot()
        print(f"  Total requests: {snapshot['requests']['total']}")
        print(f"  Avg response time: {snapshot['response_times']['avg']}s")
        print(f"  P95 response time: {snapshot['response_times']['p95']}s")
        if snapshot['errors']['total'] > 0:
            print(f"  Error rate: {snapshot['errors']['error_rate']}%")

    return {}
