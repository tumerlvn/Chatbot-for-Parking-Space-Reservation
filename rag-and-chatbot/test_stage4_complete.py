"""
End-to-End Test for Stage 4: Complete Reservation Flow

Tests the complete business process:
1. User creates reservation
2. Graph automatically transitions to admin flow
3. Admin approves via API call (INTERRUPT pattern)
4. Confirmation file is written
5. Database is updated correctly
"""

import os
import sys
import pytest
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from langchain_core.messages import HumanMessage, AIMessage
from src.chatbot.orchestrator.graph import create_orchestrator_graph
from src.shared.database_service import db_service


class TestStage4CompleteFlow:
    """Test complete reservation flow with automatic cross-agent transitions."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        # Setup
        self.thread_id = f"test_session_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.orchestrator = create_orchestrator_graph()
        self.config = {"configurable": {"thread_id": self.thread_id}}

        # Calculate test dates
        tomorrow = datetime.now() + timedelta(days=1)
        self.start_time = tomorrow.replace(hour=9, minute=0).strftime("%Y-%m-%d %H:%M")
        self.end_time = tomorrow.replace(hour=17, minute=0).strftime("%Y-%m-%d %H:%M")

        print(f"\n{'='*70}")
        print(f"Starting test with thread_id: {self.thread_id}")
        print(f"Reservation times: {self.start_time} to {self.end_time}")
        print(f"{'='*70}\n")

        yield

        # Teardown - cleanup test reservation if created
        if hasattr(self, 'reservation_id') and self.reservation_id:
            try:
                # Clean up test reservation from database
                with db_service.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM reservations WHERE id = ?", (self.reservation_id,))
                    conn.commit()
                print(f"\n[Cleanup] Deleted test reservation #{self.reservation_id}")
            except Exception as e:
                print(f"\n[Cleanup] Failed to delete reservation: {e}")

    def test_complete_reservation_flow(self):
        """
        Test full pipeline: user creates → admin approves → confirmation written.

        This test exercises:
        1. Conditional edges routing to user subgraph
        2. Automatic transition from user to admin flow
        3. Admin approval with INTERRUPT and API call
        4. Confirmation file generation
        5. Database state verification
        """
        print("\n" + "="*70)
        print("TEST: Complete Reservation Flow")
        print("="*70)

        # ===================================================================
        # STEP 1: User initiates reservation
        # ===================================================================
        print("\n[Step 1] User initiates reservation request")
        result = self.orchestrator.invoke(
            {
                "messages": [HumanMessage(content="I want to make a parking reservation")],
                "thread_id": self.thread_id,
                "session_id": self.thread_id,
                "events": [],
                "metrics": {}
            },
            config=self.config
        )

        # Verify supervisor routed to user subgraph
        assert result.get("intent") == "user", "Should classify as user intent"
        print("✓ Intent classified as 'user'")

        # ===================================================================
        # STEP 2: User provides reservation details
        # ===================================================================
        print("\n[Step 2] User provides name")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content="Test User")],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        print("[Step 2] User provides car number")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content="TEST123")],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        print(f"[Step 2] User provides start time: {self.start_time}")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content=self.start_time)],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        print(f"[Step 2] User provides end time: {self.end_time}")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content=self.end_time)],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        # Bot now asks for name (after checking availability)
        print("[Step 2] User provides name (again after availability check)")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content="Test User")],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        # Bot asks for car number
        print("[Step 2] User provides car number (after name)")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content="TEST123")],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        # Bot asks for spot type preference
        print("[Step 2] User chooses spot type")
        result = self.orchestrator.invoke(
            {
                "messages": result["messages"] + [HumanMessage(content="Standard")],
                "thread_id": self.thread_id
            },
            config=self.config
        )

        # ===================================================================
        # STEP 3: Verify reservation created and auto-transition triggered
        # ===================================================================
        print("\n[Step 3] Verifying reservation creation and auto-transition")

        reservation_data = result.get("reservation_data", {})
        self.reservation_id = reservation_data.get("reservation_id")

        assert self.reservation_id is not None, "Reservation should be created"
        assert reservation_data.get("status") == "pending", "Reservation should be pending"
        print(f"✓ Reservation #{self.reservation_id} created with status: pending")

        # The graph should have automatically transitioned to admin and shown pending reservations
        # Check that we got a message showing pending reservations
        messages = result.get("messages", [])
        last_message = messages[-1] if messages else None

        if last_message:
            content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            # Admin view should show pending reservations
            assert str(self.reservation_id) in content or "pending" in content.lower(), \
                f"Admin should see pending reservations, got: {content[:200]}..."
            print(f"✓ Auto-transition to admin flow completed - showing reservation #{self.reservation_id}")

        # ===================================================================
        # STEP 4: Admin approves reservation (INTERRUPT)
        # ===================================================================

        print(f"\n[Step 4] Admin approves reservation #{self.reservation_id}")

        # Admin says approve - append to messages and clear mode/next_action so supervisor reclassifies
        result = self.orchestrator.invoke(
            {
                **result,  # Spread all existing state
                "messages": result["messages"] + [HumanMessage(content=f"Approve #{self.reservation_id}")],
                "mode": None,  # Clear mode so supervisor reclassifies intent
                "next_action": None  # Clear the auto-admin trigger
            },
            config=self.config
        )

        # Verify action_data was populated (admin flow reached initiate_action)
        action_data = result.get("action_data", {})
        assert action_data.get("reservation_id") == self.reservation_id, \
            f"Action data should have reservation_id={self.reservation_id}, got: {action_data}"
        assert action_data.get("action_type") == "approve", \
            f"Action data should have action_type='approve', got: {action_data}"
        print("✓ Graph reached INTERRUPT point with correct action_data")

        # ===================================================================
        # STEP 5: External API call to confirm approval
        # ===================================================================
        print(f"\n[Step 5] Calling external API to confirm approval")

        # Get the admin thread_id from orchestrator state
        # The admin agent uses a separate thread ID: "admin_{base_thread_id}"
        admin_thread_id = result.get("admin_thread_id") or f"admin_{self.thread_id}"
        print(f"Using admin_thread_id: {admin_thread_id}")

        # Call the actual API endpoint
        api_url = f"http://localhost:8000/reservations/{self.reservation_id}/approve"

        # Get API token from environment
        api_token = os.getenv("ADMIN_API_TOKEN", "test-token")

        try:
            api_response = requests.post(
                api_url,
                json={"decision": "approve", "admin_notes": "Test approval - stage 4"},
                params={"thread_id": admin_thread_id},  # Use admin thread_id, not base thread_id
                headers={"Authorization": f"Bearer {api_token}"},
                timeout=10
            )

            assert api_response.status_code == 200, \
                f"API approval should succeed. Got: {api_response.status_code} - {api_response.text}"

            response_data = api_response.json()
            assert response_data["status"] == "approved", "API should return approved status"
            print(f"✓ API call successful: {response_data['message']}")

        except requests.exceptions.ConnectionError:
            pytest.skip("API server not running. Start it with: uvicorn src.api.admin_api:app")

        # ===================================================================
        # STEP 6: Verify confirmation file written
        # ===================================================================
        print("\n[Step 6] Verifying confirmation file was written")

        confirmation_file = Path("data/confirmed_reservations.txt")

        # Wait a bit for file to be written
        max_wait = 5
        for i in range(max_wait):
            if confirmation_file.exists():
                break
            time.sleep(1)

        assert confirmation_file.exists(), \
            f"Confirmation file should exist: {confirmation_file}"
        print(f"✓ Confirmation file exists: {confirmation_file}")

        # Verify content - check that our reservation ID appears
        with open(confirmation_file, 'r') as f:
            content = f.read()
            assert "Test User" in content, "Confirmation should contain user name"
            assert "TEST123" in content, "Confirmation should contain car number"
            assert f"Res#{self.reservation_id}" in content, f"Confirmation should contain Res#{self.reservation_id}"
        print(f"✓ Confirmation file contains entry for Reservation #{self.reservation_id}")

        # ===================================================================
        # STEP 7: Verify database updated correctly
        # ===================================================================
        print("\n[Step 7] Verifying database state")

        reservation = db_service.get_reservation(self.reservation_id)
        assert reservation is not None, "Reservation should exist in database"
        assert reservation["status"] == "approved", \
            f"Reservation should be approved in DB. Got: {reservation['status']}"
        assert reservation["user_name"] == "Test User"
        assert reservation["car_number"] == "TEST123"
        print(f"✓ Database updated correctly - status: {reservation['status']}")

        # ===================================================================
        # TEST PASSED
        # ===================================================================
        print("\n" + "="*70)
        print("✅ COMPLETE FLOW TEST PASSED")
        print("="*70)
        print(f"Reservation #{self.reservation_id} successfully:")
        print("  1. Created by user")
        print("  2. Automatically shown to admin")
        print("  3. Approved via API")
        print("  4. Confirmation file written")
        print("  5. Database updated")
        print("="*70 + "\n")

    def test_conditional_edge_routing(self):
        """Test that conditional edges route correctly based on intent."""
        print("\n" + "="*70)
        print("TEST: Conditional Edge Routing")
        print("="*70)

        # Test user intent routing
        print("\n[Test] User intent → user_subgraph")
        result = self.orchestrator.invoke(
            {
                "messages": [HumanMessage(content="I want to park")],
                "thread_id": self.thread_id
            },
            config=self.config
        )
        assert result.get("intent") == "user", "Should route to user subgraph"
        print("✓ User intent routed correctly")

        # Test admin intent routing
        print("\n[Test] Admin intent → admin_subgraph")
        admin_thread_id = f"test_admin_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result = self.orchestrator.invoke(
            {
                "messages": [HumanMessage(content="Show pending reservations")],
                "thread_id": admin_thread_id
            },
            config={"configurable": {"thread_id": admin_thread_id}}
        )
        assert result.get("intent") == "admin", "Should route to admin subgraph"
        print("✓ Admin intent routed correctly")

        print("\n" + "="*70)
        print("✅ CONDITIONAL ROUTING TEST PASSED")
        print("="*70 + "\n")


if __name__ == "__main__":
    """Run tests directly."""
    print("Starting Stage 4 End-to-End Tests...")
    print("Make sure the API server is running: uvicorn src.api.admin_api:app\n")

    pytest.main([__file__, "-v", "-s"])
