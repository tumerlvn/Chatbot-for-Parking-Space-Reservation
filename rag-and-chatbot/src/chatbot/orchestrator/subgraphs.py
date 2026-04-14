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

    # Build user agent state
    return {
        "messages": messages,
        "intent": user_input.get("intent"),
        "reservation_data": user_input.get("reservation_data", {}),
        "next_action": user_input.get("next_action"),
        "thread_id": orchestrator_state.get("thread_id")
    }


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

    # Build admin agent state
    return {
        "messages": messages,
        "intent": admin_input.get("intent"),
        "action_data": admin_input.get("action_data", {}),
        "admin_id": admin_input.get("admin_id", "admin1"),
        "thread_id": orchestrator_state.get("thread_id"),
        "should_write_confirmation": admin_input.get("should_write_confirmation"),
        "reservation_details": admin_input.get("reservation_details", {})
    }


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
