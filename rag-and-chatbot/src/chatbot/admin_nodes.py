"""Admin agent nodes for reservation approval workflow."""

import os
import sqlite3
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from .admin_state import AdminGraphState


_llm = None

def _get_llm():
    """Lazy load LLM."""
    global _llm
    if _llm is None:
        _llm = AzureChatOpenAI(model_name="gpt-4o-mini-2024-07-18")
    return _llm


def admin_router_node(state: AdminGraphState) -> AdminGraphState:
    """Classify admin's intent."""
    llm = _get_llm()

    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    classification_prompt = f"""You are an intent classifier for a parking admin interface.

Analyze the admin's message and classify it into ONE of these intents:

"list_pending" - Admin wants to see pending reservations
  Examples: "Show pending reservations", "Any pending?", "What needs approval?"

"approve" - Admin wants to approve a specific reservation
  Examples: "Approve reservation #5", "I want to approve #3", "Approve #1"

"reject" - Admin wants to reject a specific reservation
  Examples: "Reject reservation #5", "Reject #2", "I want to reject #1"

"query" - Admin asking about specific reservation details
  Examples: "Show me details for #5", "What's reservation #3?"

Admin message: "{user_input}"

Respond with ONLY one word: "list_pending", "approve", "reject", or "query"
"""

    response = llm.invoke([SystemMessage(content=classification_prompt)])
    intent = response.content.strip().lower()

    if intent not in ["list_pending", "approve", "reject", "query"]:
        intent = "list_pending"

    return {
        **state,
        "intent": intent
    }


def list_pending_node(state: AdminGraphState) -> AdminGraphState:
    """List all pending reservations."""
    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                r.id,
                r.user_name,
                r.car_number,
                r.start_time,
                r.end_time,
                r.reservation_time,
                ps.spot_number,
                ps.spot_type,
                ps.floor
            FROM reservations r
            JOIN parking_spots ps ON r.spot_id = ps.id
            WHERE r.status = 'pending'
            ORDER BY r.reservation_time ASC
        """)

        results = cursor.fetchall()

    finally:
        conn.close()

    if not results:
        response_text = "No pending reservations at this time."
    else:
        response_text = f"Pending Reservations ({len(results)}):\n\n"
        for row in results:
            res_id, name, car, start, end, req_time, spot, spot_type, floor = row
            response_text += f"ID #{res_id}\n"
            response_text += f"  User: {name} | Car: {car}\n"
            response_text += f"  Time: {start} to {end}\n"
            response_text += f"  Spot: {spot} ({spot_type}, {floor})\n"
            response_text += f"  Requested: {req_time}\n\n"

        response_text += "To approve/reject, say: 'Approve #ID' or 'Reject #ID'"

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response_text)]
    }


def initiate_action_node(state: AdminGraphState) -> AdminGraphState:
    """Admin initiates approve/reject - INTERRUPT POINT."""
    llm = _get_llm()

    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    intent = state.get("intent")

    # Extract reservation ID from user input
    extraction_prompt = f"""Extract the reservation ID number from this message:
"{user_input}"

Respond with ONLY the number, or "none" if no number found.
"""

    response = llm.invoke([HumanMessage(content=extraction_prompt)])
    res_id_str = response.content.strip()

    try:
        reservation_id = int(res_id_str)
    except:
        # Could not parse ID
        error_text = "Please specify a reservation ID number. Example: 'Approve #5' or 'Reject #3'"
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=error_text)]
        }

    # Verify reservation exists and is pending
    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT id, user_name, car_number, status
            FROM reservations
            WHERE id = ?
        """, (reservation_id,))

        result = cursor.fetchone()
    finally:
        conn.close()

    if not result:
        error_text = f"Reservation #{reservation_id} not found."
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=error_text)]
        }

    res_id, name, car, status = result

    if status != "pending":
        error_text = f"Reservation #{reservation_id} is already {status}."
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=error_text)]
        }

    # Store action data for later execution
    action_type = "approve" if intent == "approve" else "reject"

    updated_action_data = {
        "action_type": action_type,
        "reservation_id": reservation_id,
        "admin_notes": "",
        "completed": False
    }

    # Get thread_id from state for API call
    thread_id = state.get("thread_id", "admin_admin1")

    confirmation_text = f"""Ready to {action_type} reservation #{reservation_id} for {name} ({car}).

[INTERRUPT] Please confirm this action via REST API:

curl -X POST "http://localhost:8000/reservations/{reservation_id}/{action_type}?thread_id={thread_id}" \\
  -H "Content-Type: application/json" \\
  -d '{{"decision": "{action_type}", "admin_notes": "Processed by admin"}}'

Waiting for API confirmation...
"""

    print(f"[ADMIN AGENT INTERRUPT] Waiting for {action_type} confirmation via API for reservation #{reservation_id}")

    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=confirmation_text)],
        "action_data": updated_action_data
    }


def execute_action_node(state: AdminGraphState) -> AdminGraphState:
    """Execute approved/rejected action after API confirmation."""
    action_data = state.get("action_data", {})

    print(f"[execute_action_node] Called with action_data: {action_data}")

    if not action_data.get("completed"):
        # Should not reach here without API confirmation
        error_text = "Action not yet confirmed via API."
        print(f"[execute_action_node] Not completed, returning error")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=error_text)]
        }

    reservation_id = action_data.get("reservation_id")
    action_type = action_data.get("action_type")
    admin_notes = action_data.get("admin_notes", "")

    print(f"[execute_action_node] Executing {action_type} for reservation #{reservation_id}")

    # Update database
    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    print(f"[execute_action_node] Database path: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Update reservation status
        new_status = "approved" if action_type == "approve" else "rejected"
        print(f"[execute_action_node] Updating reservation {reservation_id} to status: {new_status}")

        cursor.execute("""
            UPDATE reservations
            SET status = ?
            WHERE id = ?
        """, (new_status, reservation_id))

        rows_affected = cursor.rowcount
        print(f"[execute_action_node] UPDATE reservations affected {rows_affected} rows")

        # If approved, mark spot as occupied
        if action_type == "approve":
            cursor.execute("""
                SELECT spot_id FROM reservations WHERE id = ?
            """, (reservation_id,))
            spot_result = cursor.fetchone()

            if spot_result:
                spot_id = spot_result[0]
                print(f"[execute_action_node] Marking spot {spot_id} as occupied")

                cursor.execute("""
                    UPDATE parking_spots
                    SET status = 'occupied'
                    WHERE id = ?
                """, (spot_id,))

                spot_rows_affected = cursor.rowcount
                print(f"[execute_action_node] UPDATE parking_spots affected {spot_rows_affected} rows")
            else:
                print(f"[execute_action_node] WARNING: No spot_id found for reservation {reservation_id}")

        print(f"[execute_action_node] Committing changes...")
        conn.commit()
        print(f"[execute_action_node] Commit successful!")

        success_text = f"Reservation #{reservation_id} has been {new_status}."
        if admin_notes:
            success_text += f"\nNotes: {admin_notes}"

        print(f"[execute_action_node] Returning success message")
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=success_text)],
            "action_data": {}  # Clear action data
        }

    except Exception as e:
        print(f"[execute_action_node] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()
        print(f"[execute_action_node] Connection closed")
