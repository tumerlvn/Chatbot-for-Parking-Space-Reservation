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
    Supervisor node - classifies intent only, does not invoke subgraphs.

    Conditional edges in the graph will route to appropriate subgraph based on intent.

    Args:
        state: Current orchestrator state

    Returns:
        Updated state with intent classification
    """
    import logging
    logger = logging.getLogger(__name__)

    # Check if we're in automatic admin flow (triggered by notification hub)
    next_action = state.get("next_action")
    if next_action == "admin_approval_needed":
        logger.info("[Supervisor] Auto-triggering admin flow for pending reservation")
        return {
            **state,
            "intent": "admin",
            "mode": "admin"  # Keep for backward compatibility
        }

    # Check if mode is explicitly set (backward compatibility)
    mode = state.get("mode")
    if mode in ["user", "admin"]:
        logger.info(f"[Supervisor] Mode explicitly set: {mode}")
        return {
            **state,
            "intent": mode
        }

    # Classify intent from last message
    messages = state.get("messages", [])
    if not messages:
        # No messages, default to user mode
        return {
            **state,
            "intent": "user",
            "mode": "user"
        }

    last_message = messages[-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    user_input_lower = user_input.lower()

    # Simple rule-based classification
    admin_keywords = [
        "pending", "approve", "reject",
        "show pending", "list pending",
        "show reservations", "list reservations",
        "pending reservations"
    ]
    is_admin = any(keyword in user_input_lower for keyword in admin_keywords)

    intent = "admin" if is_admin else "user"

    logger.info(f"[Supervisor] Classified intent: {intent}")

    # Store thread mapping for subgraphs
    base_thread_id = state.get("thread_id", "default_thread")
    user_thread_id = state.get("user_thread_id") or f"user_{base_thread_id}"
    admin_thread_id = state.get("admin_thread_id") or f"admin_{base_thread_id}"

    return {
        **state,
        "intent": intent,
        "mode": intent,  # Keep for backward compatibility
        "user_thread_id": user_thread_id,
        "admin_thread_id": admin_thread_id
    }


def user_subgraph_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Execute user agent subgraph.

    Args:
        state: Current orchestrator state

    Returns:
        Updated state with user agent results
    """
    import logging
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info("[Orchestrator] Invoking user subgraph")

    try:
        # Get user graph
        user_graph = get_user_graph()

        # Map orchestrator state to user state
        user_state = map_to_user_state(state)

        # Get thread ID for user subgraph
        user_thread_id = state.get("user_thread_id", "user_default")
        config = {"configurable": {"thread_id": user_thread_id}}

        # Invoke user subgraph
        result = user_graph.invoke(user_state, config)

        # Map result back to orchestrator state
        mapped_result = map_from_user_result(result)

        # Detect events from result
        events = detect_user_events(result)

        # Record metrics
        elapsed_time = time.time() - start_time
        global_metrics.record_request("user", elapsed_time, error=False)

        metrics = state.get("metrics", {})
        metrics["last_request_time"] = elapsed_time
        metrics["total_requests"] = metrics.get("total_requests", 0) + 1

        logger.info(f"[Orchestrator] User subgraph completed in {elapsed_time:.3f}s")

        # Convert reservation_data to dict if it's a Pydantic model
        reservation_data = result.get("reservation_data", {})
        if hasattr(reservation_data, 'model_dump'):
            reservation_data = reservation_data.model_dump()
        elif hasattr(reservation_data, 'dict'):
            reservation_data = reservation_data.dict()

        # Return updated state
        return {
            **state,
            "messages": result.get("messages", state.get("messages", [])),
            "result": mapped_result,
            "events": events,
            "metrics": metrics,
            "reservation_data": reservation_data,
            "next_action": result.get("next_action"),
            "error": None
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[Orchestrator] Error in user_subgraph_node: {e}")

        global_metrics.record_request("user", elapsed_time, error=True)

        metrics = state.get("metrics", {})
        metrics["last_request_time"] = elapsed_time
        metrics["error_count"] = metrics.get("error_count", 0) + 1

        return {
            **state,
            "result": None,
            "events": [],
            "metrics": metrics,
            "error": str(e)
        }


def admin_subgraph_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Execute admin agent subgraph.

    Args:
        state: Current orchestrator state

    Returns:
        Updated state with admin agent results
    """
    import logging
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info("[Orchestrator] Invoking admin subgraph")

    try:
        # Get admin graph
        admin_graph = get_admin_graph()

        # Map orchestrator state to admin state
        admin_state = map_to_admin_state(state)

        # Get thread ID for admin subgraph
        admin_thread_id = state.get("admin_thread_id", "admin_default")
        config = {"configurable": {"thread_id": admin_thread_id}}

        # Invoke admin subgraph (may hit INTERRUPT)
        result = admin_graph.invoke(admin_state, config)

        # Map result back to orchestrator state
        mapped_result = map_from_admin_result(result)

        # Detect events from result
        events = detect_admin_events(result)

        # Record metrics
        elapsed_time = time.time() - start_time
        global_metrics.record_request("admin", elapsed_time, error=False)

        metrics = state.get("metrics", {})
        metrics["last_request_time"] = elapsed_time
        metrics["total_requests"] = metrics.get("total_requests", 0) + 1

        logger.info(f"[Orchestrator] Admin subgraph completed in {elapsed_time:.3f}s")

        # Convert action_data to dict if it's a Pydantic model
        action_data = result.get("action_data", {})
        if hasattr(action_data, 'model_dump'):
            action_data = action_data.model_dump()
        elif hasattr(action_data, 'dict'):
            action_data = action_data.dict()

        # Return updated state
        return {
            **state,
            "messages": result.get("messages", state.get("messages", [])),
            "result": mapped_result,
            "events": events,
            "metrics": metrics,
            "action_data": action_data,
            "next_action": None,  # Clear next_action after admin completes
            "error": None
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"[Orchestrator] Error in admin_subgraph_node: {e}")

        global_metrics.record_request("admin", elapsed_time, error=True)

        metrics = state.get("metrics", {})
        metrics["last_request_time"] = elapsed_time
        metrics["error_count"] = metrics.get("error_count", 0) + 1

        return {
            **state,
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
    Notification hub - broadcasts events and triggers cross-agent transitions.

    1. Publishes detected events to the global event bus
    2. Checks if user created a pending reservation
    3. If so, triggers automatic admin approval flow

    Args:
        state: Current orchestrator state

    Returns:
        Updated state with next_action set if admin flow needed
    """
    import logging
    logger = logging.getLogger(__name__)

    events = state.get("events", [])

    # Publish all events to the event bus
    for event_dict in events:
        publish_event(
            event_type=event_dict.get("event_type"),
            data=event_dict.get("data", {}),
            source=event_dict.get("source", "orchestrator")
        )

    # Check if user created a pending reservation
    reservation_data = state.get("reservation_data", {})
    reservation_id = reservation_data.get("reservation_id")
    status = reservation_data.get("status")

    if reservation_id and status == "pending":
        logger.info(f"[NotificationHub] Reservation {reservation_id} created - triggering admin flow")

        # Trigger admin approval flow
        return {
            **state,
            "next_action": "admin_approval_needed"
        }

    return {}


def health_monitor_node(state: OrchestratorState) -> Dict[str, Any]:
    """
    Health monitor - collects and displays metrics.

    Args:
        state: Current orchestrator state

    Returns:
        Empty dict (no state changes)
    """
    import logging
    logger = logging.getLogger(__name__)

    metrics = state.get("metrics", {})

    # Log local metrics for this request
    if metrics:
        logger.info(f"[METRICS] Total requests: {metrics.get('total_requests', 0)}, "
                   f"Last request time: {metrics.get('last_request_time', 0):.3f}s")
        if metrics.get("error_count"):
            logger.warning(f"[METRICS] Errors: {metrics.get('error_count', 0)}")

    # Periodically log global metrics summary (every 10 requests)
    if global_metrics.total_requests > 0 and global_metrics.total_requests % 10 == 0:
        snapshot = global_metrics.get_snapshot()
        logger.info(f"[GLOBAL METRICS] Total: {snapshot['requests']['total']}, "
                   f"Avg: {snapshot['response_times']['avg']}s, "
                   f"P95: {snapshot['response_times']['p95']}s")
        if snapshot['errors']['total'] > 0:
            logger.warning(f"[GLOBAL METRICS] Error rate: {snapshot['errors']['error_rate']}%")

    return {}
