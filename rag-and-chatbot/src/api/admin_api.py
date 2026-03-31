"""Admin REST API for parking reservation approval."""

import os
import sqlite3
import sys
from datetime import datetime
from typing import Literal, Optional
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from chatbot.graph import create_chatbot_graph


app = FastAPI(
    title="SmartPark Admin API",
    description="Reservation approval system for parking facility administrators",
    version="2.0.0"
)

chatbot_graph = create_chatbot_graph()


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


@app.get("/reservations/pending")
def get_pending_reservations():
    """List all pending reservations."""
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
                ps.spot_number,
                ps.spot_type,
                ps.floor,
                r.thread_id
            FROM reservations r
            JOIN parking_spots ps ON r.spot_id = ps.id
            WHERE r.status = 'pending'
            ORDER BY r.reservation_time ASC
        """)

        results = cursor.fetchall()

    reservations = [
        {
            "id": row[0],
            "user_name": row[1],
            "car_number": row[2],
            "start_time": row[3],
            "end_time": row[4],
            "requested_at": row[5],
            "assigned_spot": {
                "number": row[6],
                "type": row[7],
                "floor": row[8]
            },
            "thread_id": row[9]
        }
        for row in results
    ]

    return {
        "pending_count": len(reservations),
        "reservations": reservations
    }


@app.post("/reservations/{reservation_id}/approve")
def approve_reservation(reservation_id: int, request: ApprovalRequest):
    """Approve a pending reservation and resume graph execution."""
    if request.decision != "approve":
        raise HTTPException(
            status_code=400,
            detail="Use /approve endpoint only for approvals"
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_name, car_number, thread_id, status
            FROM reservations
            WHERE id = ?
        """, (reservation_id,))
        result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Reservation #{reservation_id} not found"
        )

    res_id, user_name, car_number, thread_id, current_status = result

    if current_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation #{reservation_id} is already {current_status}"
        )

    if not thread_id:
        thread_id = f"reservation_{reservation_id}"

    config = {"configurable": {"thread_id": thread_id}}

    try:
        current_state = chatbot_graph.get_state(config)

        if not current_state.values:
            raise HTTPException(
                status_code=500,
                detail=f"Could not find conversation state for reservation #{reservation_id}"
            )

        current_reservation_data = current_state.values.get("reservation_data", {})
        updated_reservation_data = {
            **current_reservation_data,
            "status": "approved",
            "admin_decision_time": datetime.now().isoformat(),
            "admin_notes": request.admin_notes
        }

        chatbot_graph.update_state(
            config,
            {"reservation_data": updated_reservation_data}
        )

        chatbot_graph.invoke(None, config)

        return {
            "success": True,
            "reservation_id": reservation_id,
            "status": "approved",
            "user_name": user_name,
            "car_number": car_number,
            "message": "Reservation approved and finalized successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process approval: {str(e)}"
        )


@app.post("/reservations/{reservation_id}/reject")
def reject_reservation(reservation_id: int, request: ApprovalRequest):
    """Reject a pending reservation."""
    if request.decision != "reject":
        raise HTTPException(
            status_code=400,
            detail="Use /reject endpoint only for rejections"
        )

    # Get reservation details including thread_id
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_name, car_number, thread_id, status
            FROM reservations
            WHERE id = ?
        """, (reservation_id,))
        result = cursor.fetchone()

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Reservation #{reservation_id} not found"
        )

    res_id, user_name, car_number, thread_id, current_status = result

    if current_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation #{reservation_id} is already {current_status}"
        )

    if not thread_id:
        thread_id = f"reservation_{reservation_id}"

    config = {"configurable": {"thread_id": thread_id}}

    try:
        current_state = chatbot_graph.get_state(config)

        if not current_state.values:
            raise HTTPException(
                status_code=500,
                detail=f"Could not find conversation state for reservation #{reservation_id}"
            )

        current_reservation_data = current_state.values.get("reservation_data", {})
        updated_reservation_data = {
            **current_reservation_data,
            "status": "rejected",
            "admin_decision_time": datetime.now().isoformat(),
            "admin_notes": request.admin_notes
        }

        chatbot_graph.update_state(
            config,
            {"reservation_data": updated_reservation_data}
        )

        chatbot_graph.invoke(None, config)

        return {
            "success": True,
            "reservation_id": reservation_id,
            "status": "rejected",
            "user_name": user_name,
            "car_number": car_number,
            "message": "Reservation rejected successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process rejection: {str(e)}"
        )


@app.get("/reservations/{reservation_id}")
def get_reservation_details(reservation_id: int):
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

    print("Starting SmartPark Admin API...")
    print("API will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")

    uvicorn.run(
        "admin_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
