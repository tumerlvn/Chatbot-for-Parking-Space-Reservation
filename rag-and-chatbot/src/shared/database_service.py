"""Database service with connection pooling and abstraction layer."""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime

from .config import Config


class DatabaseService:
    """
    Database service with connection pooling and abstraction.

    Provides a single interface for all database operations across the
    multi-agent system. Uses thread-local storage for connection management.
    """

    _instance = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls):
        """Singleton pattern for database service."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize database service (only once)."""
        if self._initialized:
            return

        self.db_path = Config.get_db_path()
        self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local database connection.

        Creates a new connection if one doesn't exist for the current thread.
        """
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                timeout=Config.DB_TIMEOUT,
                check_same_thread=Config.DB_CHECK_SAME_THREAD
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Usage:
            with db_service.get_connection() as conn:
                cursor = conn.cursor()
                # ... use cursor ...
        """
        conn = self._get_connection()
        try:
            yield conn
        finally:
            pass  # Don't close - reuse thread-local connection

    def close_thread_connection(self):
        """Close the thread-local connection (called on thread cleanup)."""
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ========================================================================
    # Reservation Operations
    # ========================================================================

    def get_reservation(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get reservation by ID.

        Args:
            reservation_id: Reservation ID

        Returns:
            Dict with reservation data or None if not found
        """
        with self.get_connection() as conn:
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
                    r.thread_id,
                    ps.id as spot_id,
                    ps.spot_number,
                    ps.spot_type,
                    ps.floor
                FROM reservations r
                JOIN parking_spots ps ON r.spot_id = ps.id
                WHERE r.id = ?
            """, (reservation_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "user_name": row["user_name"],
            "car_number": row["car_number"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "reservation_time": row["reservation_time"],
            "status": row["status"],
            "thread_id": row["thread_id"],
            "spot_id": row["spot_id"],
            "spot_number": row["spot_number"],
            "spot_type": row["spot_type"],
            "floor": row["floor"]
        }

    def list_pending_reservations(self) -> List[Dict[str, Any]]:
        """
        List all pending reservations.

        Returns:
            List of pending reservation dicts
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    r.id,
                    r.user_name,
                    r.car_number,
                    r.start_time,
                    r.end_time,
                    r.reservation_time,
                    r.thread_id,
                    ps.spot_number,
                    ps.spot_type,
                    ps.floor
                FROM reservations r
                JOIN parking_spots ps ON r.spot_id = ps.id
                WHERE r.status = 'pending'
                ORDER BY r.reservation_time ASC
            """)
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "user_name": row["user_name"],
                "car_number": row["car_number"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "reservation_time": row["reservation_time"],
                "thread_id": row["thread_id"],
                "spot_number": row["spot_number"],
                "spot_type": row["spot_type"],
                "floor": row["floor"]
            }
            for row in rows
        ]

    def create_reservation(self, reservation_data: Dict[str, Any]) -> int:
        """
        Create a new reservation.

        Args:
            reservation_data: Dict with name, car_number, start_time, end_time, spot_id, thread_id

        Returns:
            New reservation ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reservations (
                    user_name, car_number, start_time, end_time,
                    spot_id, status, reservation_time, thread_id
                ) VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'), ?)
            """, (
                reservation_data["name"],
                reservation_data["car_number"],
                reservation_data["start_time"],
                reservation_data["end_time"],
                reservation_data["spot_id"],
                reservation_data.get("thread_id", "default_thread")
            ))
            conn.commit()
            reservation_id = cursor.lastrowid

        return reservation_id

    def update_reservation_status(
        self,
        reservation_id: int,
        status: str,
        admin_id: Optional[str] = None
    ) -> bool:
        """
        Update reservation status.

        Args:
            reservation_id: Reservation ID
            status: New status ('approved' or 'rejected')
            admin_id: Optional admin ID for tracking

        Returns:
            True if updated, False if reservation not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if reservation exists
            cursor.execute("SELECT id, status FROM reservations WHERE id = ?", (reservation_id,))
            row = cursor.fetchone()

            if not row:
                return False

            # Update status
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE reservations
                SET status = ?, admin_decision_time = ?
                WHERE id = ?
            """, (status, now, reservation_id))
            conn.commit()

        return True

    def check_availability(
        self,
        start_time: str,
        end_time: str
    ) -> Dict[str, Any]:
        """
        Check parking spot availability for a time range.

        Args:
            start_time: Start time (ISO format)
            end_time: End time (ISO format)

        Returns:
            Dict with available_spots list and count_by_type dict
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Find spots that don't have overlapping approved reservations
            cursor.execute("""
                SELECT ps.id, ps.spot_number, ps.spot_type, ps.floor
                FROM parking_spots ps
                WHERE ps.id NOT IN (
                    SELECT r.spot_id
                    FROM reservations r
                    WHERE r.status = 'approved'
                    AND (
                        (r.start_time <= ? AND r.end_time > ?)
                        OR (r.start_time < ? AND r.end_time >= ?)
                        OR (r.start_time >= ? AND r.end_time <= ?)
                    )
                )
                ORDER BY ps.floor, ps.spot_number
            """, (start_time, start_time, end_time, end_time, start_time, end_time))

            rows = cursor.fetchall()

        available_spots = [
            {
                "id": row["id"],
                "spot_number": row["spot_number"],
                "spot_type": row["spot_type"],
                "floor": row["floor"]
            }
            for row in rows
        ]

        # Count by type
        count_by_type = {}
        for spot in available_spots:
            spot_type = spot["spot_type"]
            count_by_type[spot_type] = count_by_type.get(spot_type, 0) + 1

        return {
            "available_spots": available_spots,
            "count_by_type": count_by_type
        }

    def get_spot_details(self, spot_id: int) -> Optional[Dict[str, Any]]:
        """
        Get parking spot details.

        Args:
            spot_id: Spot ID

        Returns:
            Dict with spot details or None if not found
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, spot_number, spot_type, floor
                FROM parking_spots
                WHERE id = ?
            """, (spot_id,))
            row = cursor.fetchone()

        if not row:
            return None

        return {
            "id": row["id"],
            "spot_number": row["spot_number"],
            "spot_type": row["spot_type"],
            "floor": row["floor"]
        }


# Global singleton instance
db_service = DatabaseService()
