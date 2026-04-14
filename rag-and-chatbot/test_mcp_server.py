"""Unit tests for confirmation file writing."""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mcp.confirmation_writer import (
    _ensure_file_exists,
    _sanitize,
    write_confirmation,
    CONFIRMATION_FILE,
    DATA_DIR
)


def test_sanitization():
    """Test that special characters are sanitized properly."""
    print("Testing sanitization...")

    # Test pipe character removal
    assert _sanitize("John | Doe") == "John - Doe"

    # Test newline removal
    assert _sanitize("John\nDoe") == "John Doe"
    assert _sanitize("John\rDoe") == "John Doe"

    # Test combination
    assert _sanitize("John | Doe\nJr.") == "John - Doe Jr."

    print("✓ Test passed: Special character sanitization")


def test_file_creation():
    """Test that confirmation file is created with header."""
    print("Testing file creation...")

    # Remove file if exists
    if os.path.exists(CONFIRMATION_FILE):
        os.remove(CONFIRMATION_FILE)

    # Ensure file exists
    _ensure_file_exists()

    # Check file exists
    assert os.path.exists(CONFIRMATION_FILE), "File should be created"

    # Check header
    with open(CONFIRMATION_FILE, 'r') as f:
        content = f.read()
        assert "# Confirmed Parking Reservations" in content
        assert "# Format: Name | Car Number | Period | Approval Time | Reservation ID" in content

    print("✓ Test passed: File creation with header")


def test_write_confirmation():
    """Test the write_confirmation function."""
    print("Testing write_confirmation function...")

    # Ensure clean state
    if os.path.exists(CONFIRMATION_FILE):
        os.remove(CONFIRMATION_FILE)

    # Test data
    result = write_confirmation(
        reservation_id=123,
        name="Test User",
        car_number="ABC-1234",
        start_time="2026-04-03 09:00:00",
        end_time="2026-04-03 17:00:00"
    )

    # Check result
    assert result["success"] is True, "Should return success"
    assert "✅" in result["message"] or "Confirmation written" in result["message"]

    # Check file content
    with open(CONFIRMATION_FILE, 'r') as f:
        content = f.read()
        assert "Test User" in content
        assert "ABC-1234" in content
        assert "2026-04-03 09:00:00 to 2026-04-03 17:00:00" in content
        assert "Res#123" in content

    print("✓ Test passed: Write confirmation function works")


def test_multiple_writes():
    """Test multiple writes append to file."""
    print("Testing multiple writes...")

    # Clean state
    if os.path.exists(CONFIRMATION_FILE):
        os.remove(CONFIRMATION_FILE)

    # Write first entry
    write_confirmation(
        reservation_id=1,
        name="User One",
        car_number="CAR-001",
        start_time="2026-04-03 09:00:00",
        end_time="2026-04-03 17:00:00"
    )

    # Write second entry
    write_confirmation(
        reservation_id=2,
        name="User Two",
        car_number="CAR-002",
        start_time="2026-04-04 09:00:00",
        end_time="2026-04-04 17:00:00"
    )

    # Check both entries exist
    with open(CONFIRMATION_FILE, 'r') as f:
        content = f.read()
        assert "User One" in content
        assert "CAR-001" in content
        assert "Res#1" in content
        assert "User Two" in content
        assert "CAR-002" in content
        assert "Res#2" in content

    print("✓ Test passed: Multiple writes (append mode)")


def test_special_characters_in_data():
    """Test that special characters in data are sanitized."""
    print("Testing special characters in data...")

    # Clean state
    if os.path.exists(CONFIRMATION_FILE):
        os.remove(CONFIRMATION_FILE)

    # Write entry with special characters
    write_confirmation(
        reservation_id=999,
        name="John | Doe\nJr.",
        car_number="ABC|123",
        start_time="2026-04-03 09:00:00",
        end_time="2026-04-03 17:00:00"
    )

    # Check sanitization in file
    with open(CONFIRMATION_FILE, 'r') as f:
        content = f.read()
        # Pipes should be replaced with dashes
        assert "John - Doe Jr." in content
        assert "ABC-123" in content
        # Should not contain raw pipes or newlines that break format
        lines = content.split('\n')
        data_lines = [l for l in lines if l and not l.startswith('#')]
        for line in data_lines:
            # Each data line should have exactly 4 pipes (5 fields)
            assert line.count('|') == 4, f"Line should have 4 pipes: {line}"

    print("✓ Test passed: Special character sanitization in data")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("Running Confirmation Writer Tests")
    print("="*60 + "\n")

    test_sanitization()
    test_file_creation()
    test_write_confirmation()
    test_multiple_writes()
    test_special_characters_in_data()

    print("\n" + "="*60)
    print("✅ All confirmation writer tests passed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
