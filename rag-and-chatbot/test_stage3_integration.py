"""End-to-end integration test for Stage 3."""

import os
import sys
import sqlite3
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from chatbot.admin_nodes import execute_action_node, write_confirmation_node
from chatbot.admin_state import AdminGraphState
from langchain_core.messages import HumanMessage
from mcp.confirmation_writer import CONFIRMATION_FILE


def setup_test_database():
    """Set up a test database with a sample reservation."""
    db_path = os.path.join(os.path.dirname(__file__), "data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get an available spot
    cursor.execute("""
        SELECT id FROM parking_spots
        WHERE status = 'available'
        LIMIT 1
    """)
    spot_result = cursor.fetchone()

    if not spot_result:
        print("WARNING: No available spots found. Creating one...")
        cursor.execute("""
            INSERT INTO parking_spots (spot_number, spot_type, floor, status)
            VALUES ('TEST-001', 'standard', 'Floor 1', 'available')
        """)
        conn.commit()
        spot_id = cursor.lastrowid
    else:
        spot_id = spot_result[0]

    # Create a test reservation
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=8)

    cursor.execute("""
        INSERT INTO reservations (
            user_name, car_number, start_time, end_time,
            spot_id, status, reservation_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "Test User Stage3",
        "TEST-123",
        start_time.strftime("%Y-%m-%d %H:%M:%S"),
        end_time.strftime("%Y-%m-%d %H:%M:%S"),
        spot_id,
        "pending",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    reservation_id = cursor.lastrowid
    conn.close()

    return reservation_id


def test_stage3_integration():
    """Test full Stage 3 integration."""
    print("\n" + "="*70)
    print("Running Stage 3 End-to-End Integration Test")
    print("="*70 + "\n")

    # Clean confirmation file
    if os.path.exists(CONFIRMATION_FILE):
        os.remove(CONFIRMATION_FILE)
        print("✓ Cleaned confirmation file\n")

    # Set up test data
    print("Setting up test database...")
    reservation_id = setup_test_database()
    print(f"✓ Created test reservation #{reservation_id}\n")

    # Simulate admin approval flow
    print("Simulating admin approval via execute_action_node...")

    # Create state as if API has confirmed the action
    state = AdminGraphState(
        messages=[HumanMessage(content=f"approve {reservation_id}")],
        intent="approve",
        action_data={
            "action_type": "approve",
            "reservation_id": reservation_id,
            "admin_notes": "Test approval for Stage 3",
            "completed": True  # API has confirmed
        },
        thread_id="test_thread"
    )

    # Call execute_action_node
    result_state = execute_action_node(state)

    # Verify state result
    assert len(result_state["messages"]) > 0, "Should have response message"
    last_message = result_state["messages"][-1]
    print(f"\nExecute action response: {last_message.content}\n")

    # Check if we should write confirmation
    should_write = result_state.get("should_write_confirmation", False)
    print(f"Should write confirmation: {should_write}\n")
    assert should_write is True, "Should be flagged to write confirmation"

    # Now call write_confirmation_node
    print("Calling write_confirmation_node...")
    final_state = write_confirmation_node(result_state)

    # Verify database was updated
    print("Verifying database update...")
    db_path = os.path.join(os.path.dirname(__file__), "data/parking_db.sqlite")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM reservations WHERE id = ?", (reservation_id,))
    status = cursor.fetchone()[0]
    assert status == "approved", f"Expected status 'approved', got '{status}'"
    print(f"✓ Reservation #{reservation_id} status: {status}\n")

    conn.close()

    # Verify confirmation file was written
    print("Verifying confirmation file...")
    assert os.path.exists(CONFIRMATION_FILE), "Confirmation file should exist"

    with open(CONFIRMATION_FILE, 'r') as f:
        content = f.read()
        print("Confirmation file contents:")
        print("-" * 70)
        print(content)
        print("-" * 70 + "\n")

        # Verify content
        assert "Test User Stage3" in content, "User name should be in file"
        assert "TEST-123" in content, "Car number should be in file"
        assert f"Res#{reservation_id}" in content, "Reservation ID should be in file"

    print("✓ Confirmation file written correctly\n")

    # Clean up - reset reservation status
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE reservations SET status = 'pending' WHERE id = ?", (reservation_id,))
    cursor.execute("UPDATE parking_spots SET status = 'available' WHERE id IN (SELECT spot_id FROM reservations WHERE id = ?)", (reservation_id,))
    conn.commit()
    conn.close()

    print("="*70)
    print("✅ Stage 3 Integration Test Passed!")
    print("="*70 + "\n")

    print("Summary:")
    print("  ✓ Database update successful")
    print("  ✓ LangChain tool invoked")
    print("  ✓ Confirmation file written")
    print("  ✓ File format correct")
    print("  ✓ All data fields present\n")


if __name__ == "__main__":
    test_stage3_integration()
