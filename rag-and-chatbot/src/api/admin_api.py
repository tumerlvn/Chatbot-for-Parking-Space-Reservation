"""Admin REST API for parking reservation approval."""

import os
import sqlite3
import sys
import logging
from datetime import datetime
from typing import Literal, Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.chatbot.admin_graph import create_admin_graph
from src.chatbot.orchestrator.nodes import get_admin_graph
from src.shared.models import Reservation, ParkingSpot


app = FastAPI(
    title="SmartPark Admin API",
    description="Reservation approval system for parking facility administrators",
    version="2.0.0"
)

# Use the singleton admin graph from orchestrator (maintains same checkpoint state)
admin_agent_graph = get_admin_graph()

# Security setup
security = HTTPBearer()

# Load admin API token from environment
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")

if not ADMIN_API_TOKEN:
    logger.warning("ADMIN_API_TOKEN not set in environment. API authentication disabled!")


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    Verify bearer token for API authentication.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        True if token is valid

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not ADMIN_API_TOKEN:
        # If no token configured, allow all requests (development mode)
        logger.warning("No ADMIN_API_TOKEN configured - allowing unauthenticated request")
        return True

    if credentials.credentials != ADMIN_API_TOKEN:
        logger.warning(f"Invalid authentication token provided")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return True


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    db_path = os.path.join(os.path.dirname(__file__), "../../data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


class ApprovalRequest(BaseModel):
    """Request model for approval/rejection."""
    decision: Literal["approve", "reject"]
    admin_notes: str = ""


class ReservationResponse(BaseModel):
    """Individual reservation in response."""
    id: int
    user_name: str
    car_number: str
    start_time: str
    end_time: str
    requested_at: str
    assigned_spot: dict

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "smartpark-admin-api",
        "version": "2.0.0"
    }


def _process_reservation_decision(
    reservation_id: int,
    decision: Literal["approve", "reject"],
    thread_id: str,
    request: ApprovalRequest
) -> dict:
    """
    Private helper to process reservation approval/rejection.

    Args:
        reservation_id: The reservation to process
        decision: "approve" or "reject"
        thread_id: Admin agent thread ID
        request: Request with decision and notes

    Returns:
        Success response dict

    Raises:
        HTTPException: On validation or processing errors
    """
    # Get reservation from DB
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_name, car_number, status
            FROM reservations
            WHERE id = ?
        """, (reservation_id,))
        result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Reservation #{reservation_id} not found"
        )

    # Use dict-like access instead of tuple indexing
    user_name = result["user_name"]
    car_number = result["car_number"]
    current_status = result["status"]

    if current_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation #{reservation_id} is already {current_status}"
        )

    # Get admin agent state using provided thread_id
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"[API] Using thread_id: {thread_id}")

    try:
        current_state = admin_agent_graph.get_state(config)

        if not current_state.values:
            raise HTTPException(
                status_code=500,
                detail="Could not find admin conversation state"
            )

        # Update action_data with completion flag
        current_action_data = current_state.values.get("action_data", {})
        updated_action_data = {
            **current_action_data,
            "completed": True,
            "admin_notes": request.admin_notes
        }

        # Update state
        logger.info(f"[API] Updating action_data to: {updated_action_data}")
        admin_agent_graph.update_state(
            config,
            {"action_data": updated_action_data}
        )

        # Resume execution (will execute execute_action_node)
        logger.info(f"[API] Resuming admin agent graph for reservation #{reservation_id}")

        # Pass None as input to resume from interrupt
        result = admin_agent_graph.invoke(None, config)

        logger.info(f"[API] Graph execution result: {result}")
        logger.info(f"[API] Graph execution completed: action_data = {result.get('action_data', {})}")

        # Verify the database was updated
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM reservations WHERE id = ?", (reservation_id,))
            db_result = cursor.fetchone()
            if db_result:
                db_status = db_result[0]
                logger.info(f"[API] Database status for reservation #{reservation_id}: {db_status}")
                if db_status != decision + "d":  # "approved" or "rejected"
                    raise HTTPException(
                        status_code=500,
                        detail=f"Graph executed but database not updated. Current status: {db_status}"
                    )

        return {
            "success": True,
            "reservation_id": reservation_id,
            "status": decision + "d",
            "user_name": user_name,
            "car_number": car_number,
            "message": f"Reservation {decision}d successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"[API] Error processing {decision}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process {decision}: {str(e)}"
        )


@app.get("/reservations/pending")
def get_pending_reservations(authorized: bool = Depends(verify_token)):
    """List all pending reservations."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        cursor = conn.cursor()

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
                ps.floor,
                r.thread_id,
                r.status,
                r.spot_id
            FROM reservations r
            JOIN parking_spots ps ON r.spot_id = ps.id
            WHERE r.status = 'pending'
            ORDER BY r.reservation_time ASC
        """)

        results = cursor.fetchall()

    reservations = [
        {
            "id": row["id"],
            "user_name": row["user_name"],
            "car_number": row["car_number"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "requested_at": row["reservation_time"],
            "assigned_spot": {
                "number": row["spot_number"],
                "type": row["spot_type"],
                "floor": row["floor"]
            },
            "thread_id": row["thread_id"]
        }
        for row in results
    ]

    return {
        "pending_count": len(reservations),
        "reservations": reservations
    }


@app.post("/reservations/{reservation_id}/approve")
def approve_reservation(
    reservation_id: int,
    request: ApprovalRequest,
    thread_id: str = "admin_admin1",
    authorized: bool = Depends(verify_token)
):
    """
    Approve reservation - called from admin CLI after interrupt.
    Resumes admin agent graph execution.

    Args:
        reservation_id: The reservation to approve
        request: Approval request with decision and notes
        thread_id: Admin agent thread ID (from curl command)
    """
    if request.decision != "approve":
        raise HTTPException(
            status_code=400,
            detail="Use /approve endpoint only for approvals"
        )

    return _process_reservation_decision(reservation_id, "approve", thread_id, request)


@app.post("/reservations/{reservation_id}/reject")
def reject_reservation(
    reservation_id: int,
    request: ApprovalRequest,
    thread_id: str = "admin_admin1",
    authorized: bool = Depends(verify_token)
):
    """
    Reject reservation - called from admin CLI after interrupt.
    Resumes admin agent graph execution.

    Args:
        reservation_id: The reservation to reject
        request: Rejection request with decision and notes
        thread_id: Admin agent thread ID (from curl command)
    """
    if request.decision != "reject":
        raise HTTPException(
            status_code=400,
            detail="Use /reject endpoint only for rejections"
        )

    return _process_reservation_decision(reservation_id, "reject", thread_id, request)


@app.get("/reservations/{reservation_id}")
def get_reservation_details(reservation_id: int, authorized: bool = Depends(verify_token)):
    """Get details of a specific reservation."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                r.id,
                r.user_name,
                r.car_number,
                r.start_time,
                r.end_time,
                r.reservation_time,
                r.status,
                ps.spot_number,
                ps.spot_type,
                ps.floor
            FROM reservations r
            JOIN parking_spots ps ON r.spot_id = ps.id
            WHERE r.id = ?
        """, (reservation_id,))

        result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Reservation #{reservation_id} not found"
        )

    return {
        "id": result[0],
        "user_name": result[1],
        "car_number": result[2],
        "start_time": result[3],
        "end_time": result[4],
        "requested_at": result[5],
        "status": result[6],
        "assigned_spot": {
            "number": result[7],
            "type": result[8],
            "floor": result[9]
        }
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting SmartPark Admin API...")
    logger.info("API will be available at: http://localhost:8000")
    logger.info("API docs at: http://localhost:8000/docs")

    uvicorn.run(
        "src.api.admin_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
