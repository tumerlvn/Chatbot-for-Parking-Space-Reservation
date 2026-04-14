"""LangChain Tools for confirmation file writing."""

import os
from typing import Dict, Any
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mcp.confirmation_writer import write_confirmation


class WriteConfirmationInput(BaseModel):
    """Input schema for write_confirmation tool."""
    reservation_id: int = Field(description="Reservation database ID")
    name: str = Field(description="User's full name")
    car_number: str = Field(description="License plate number")
    start_time: str = Field(description="Reservation start time (ISO format)")
    end_time: str = Field(description="Reservation end time (ISO format)")


def write_confirmation_func(
    reservation_id: int,
    name: str,
    car_number: str,
    start_time: str,
    end_time: str
) -> str:
    """
    Write confirmed reservation details to file.

    Args:
        reservation_id: Reservation database ID
        name: User's full name
        car_number: License plate number
        start_time: Reservation start time (ISO format)
        end_time: Reservation end time (ISO format)

    Returns:
        Success/failure message as string
    """
    # Call confirmation writer
    result = write_confirmation(
        reservation_id=reservation_id,
        name=name,
        car_number=car_number,
        start_time=start_time,
        end_time=end_time
    )

    return result.get("message", "Confirmation written")


# Create LangChain StructuredTool
write_confirmation_tool = StructuredTool.from_function(
    func=write_confirmation_func,
    name="write_confirmation",
    description="Write confirmed parking reservation details to file. Call this after approving a reservation.",
    args_schema=WriteConfirmationInput,
    return_direct=False
)


def get_confirmation_tools() -> list:
    """Get list of all confirmation tools."""
    return [write_confirmation_tool]
