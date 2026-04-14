"""Subgraph wrappers for user and admin agents."""

from typing import Dict, Any
from langchain_core.messages import HumanMessage

from ..graph import create_chatbot_graph
from ..admin_graph import create_admin_graph
from ..state import GraphState
from ..admin_state import AdminGraphState
from .state import OrchestratorState


def wrap_user_subgraph():
    """
    Create a wrapped user agent subgraph.

    Returns the compiled user chatbot graph (from Stage 3).
    """
    return create_chatbot_graph()


def wrap_admin_subgraph():
    """
    Create a wrapped admin agent subgraph.

    Returns the compiled admin graph (from Stage 3) with interrupt pattern preserved.
    """
    return create_admin_graph()


def map_to_user_state(orchestrator_state: OrchestratorState) -> GraphState:
    """
    Map orchestrator state to user agent state.

    Args:
        orchestrator_state: The orchestrator state

    Returns:
        GraphState compatible with user agent
    """
    user_input = orchestrator_state.get("user_state", {})

    # Extract messages (required)
    messages = user_input.get("messages", [])

    # Build user agent state - only include fields that are explicitly provided
    # Let subgraph checkpoint handle fields not provided (like reservation_data)
    mapped_state = {"messages": messages}

    # Only include optional fields if they're explicitly set in user_input
    if "intent" in user_input:
        mapped_state["intent"] = user_input["intent"]
    if "reservation_data" in user_input:
        mapped_state["reservation_data"] = user_input["reservation_data"]
    if "next_action" in user_input:
        mapped_state["next_action"] = user_input["next_action"]

    # Pass the MAPPED user thread ID if available
    if "user_thread_id" in orchestrator_state:
        mapped_state["thread_id"] = orchestrator_state["user_thread_id"]
    elif "thread_id" in orchestrator_state:
        # Fallback to base thread if mapping not set yet
        mapped_state["thread_id"] = orchestrator_state["thread_id"]

    return mapped_state


def map_to_admin_state(orchestrator_state: OrchestratorState) -> AdminGraphState:
    """
    Map orchestrator state to admin agent state.

    Args:
        orchestrator_state: The orchestrator state

    Returns:
        AdminGraphState compatible with admin agent
    """
    admin_input = orchestrator_state.get("admin_state", {})

    # Extract messages (required)
    messages = admin_input.get("messages", [])

    # Build admin agent state - only include fields that are explicitly provided
    # Let subgraph checkpoint handle fields not provided (like action_data)
    mapped_state = {"messages": messages}

    # Only include optional fields if they're explicitly set in admin_input
    if "intent" in admin_input:
        mapped_state["intent"] = admin_input["intent"]
    if "action_data" in admin_input:
        mapped_state["action_data"] = admin_input["action_data"]
    if "admin_id" in admin_input:
        mapped_state["admin_id"] = admin_input["admin_id"]

    # CRITICAL: Pass the MAPPED admin thread ID, not the base thread ID
    # This ensures the curl command in the interrupt uses the correct thread
    if "admin_thread_id" in orchestrator_state:
        mapped_state["thread_id"] = orchestrator_state["admin_thread_id"]
    elif "thread_id" in orchestrator_state:
        # Fallback to base thread if mapping not set yet
        mapped_state["thread_id"] = orchestrator_state["thread_id"]

    if "should_write_confirmation" in admin_input:
        mapped_state["should_write_confirmation"] = admin_input["should_write_confirmation"]
    if "reservation_details" in admin_input:
        mapped_state["reservation_details"] = admin_input["reservation_details"]

    return mapped_state


def map_from_user_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map user agent result back to orchestrator format.

    Args:
        result: Result from user agent graph

    Returns:
        Dict with result data
    """
    return {
        "messages": result.get("messages", []),
        "intent": result.get("intent"),
        "reservation_data": result.get("reservation_data", {}),
        "next_action": result.get("next_action"),
        "thread_id": result.get("thread_id")
    }


def map_from_admin_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map admin agent result back to orchestrator format.

    Args:
        result: Result from admin agent graph

    Returns:
        Dict with result data
    """
    return {
        "messages": result.get("messages", []),
        "intent": result.get("intent"),
        "action_data": result.get("action_data", {}),
        "admin_id": result.get("admin_id"),
        "thread_id": result.get("thread_id"),
        "should_write_confirmation": result.get("should_write_confirmation"),
        "reservation_details": result.get("reservation_details", {})
    }
