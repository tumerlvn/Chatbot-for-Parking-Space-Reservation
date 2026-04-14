"""Confirmation file writer for parking reservation approvals."""

import os
from datetime import datetime
from typing import Dict, Any

# File configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")
CONFIRMATION_FILE = os.path.join(DATA_DIR, "confirmed_reservations.txt")


def _ensure_file_exists():
    """Create confirmation file with header if it doesn't exist."""
    if not os.path.exists(CONFIRMATION_FILE):
        os.makedirs(os.path.dirname(CONFIRMATION_FILE), exist_ok=True)
        with open(CONFIRMATION_FILE, 'w') as f:
            f.write("# Confirmed Parking Reservations\n")
            f.write("# Format: Name | Car Number | Period | Approval Time | Reservation ID\n")
            f.write("\n")


def _sanitize(value: str) -> str:
    """Remove special characters that could corrupt file format."""
    return str(value).replace('|', '-').replace('\n', ' ').replace('\r', ' ')


def write_confirmation(
    reservation_id: int,
    name: str,
    car_number: str,
    start_time: str,
    end_time: str
) -> Dict[str, Any]:
    """
    Write confirmation entry to file.

    Args:
        reservation_id: Reservation database ID
        name: User's full name
        car_number: License plate number
        start_time: Reservation start time (ISO format)
        end_time: Reservation end time (ISO format)

    Returns:
        Dict with success status and message
    """
    try:
        # Ensure file exists
        _ensure_file_exists()

        # Sanitize inputs
        name = _sanitize(name)
        car_number = _sanitize(car_number)
        start_time = _sanitize(start_time)
        end_time = _sanitize(end_time)

        # Generate approval timestamp
        approval_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build confirmation line
        period = f"{start_time} to {end_time}"
        line = f"{name} | {car_number} | {period} | {approval_time} | Res#{reservation_id}\n"

        # Append to file
        with open(CONFIRMATION_FILE, 'a') as f:
            f.write(line)

        success_msg = f"✅ Confirmation written: Reservation #{reservation_id} for {name} ({car_number})"
        return {
            "success": True,
            "message": success_msg
        }

    except Exception as e:
        error_msg = f"❌ Failed to write confirmation: {str(e)}"
        return {
            "success": False,
            "message": error_msg,
            "error": str(e)
        }
