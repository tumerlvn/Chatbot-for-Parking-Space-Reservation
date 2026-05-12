"""Integration tests for orchestrator system (Stage 4)."""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chatbot.orchestrator import create_orchestrator_graph
from src.shared import global_metrics, global_event_bus
from langchain_core.messages import HumanMessage


class TestOrchestratorIntegration:
    """Integration tests for orchestrator coordinating user and admin agents."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset metrics and events before each test."""
        global_metrics.reset()
        global_event_bus.clear_log()
        yield

    def test_user_agent_routing(self):
        """Test that user agent routes correctly through orchestrator."""
        orchestrator = create_orchestrator_graph()

        result = orchestrator.invoke({
            "mode": "user",
            "user_state": {
                "messages": [HumanMessage(content="What are your hours?")],
                "intent": None,
                "reservation_data": {},
                "thread_id": "test_user_thread"
            },
            "thread_id": "test_user_thread",
            "session_id": "test_session",
            "events": [],
            "metrics": {},
            "shared_data": {}
        })

        # Verify result structure
        assert result is not None
        assert "result" in result
        assert result["result"] is not None
        assert "messages" in result["result"]
        assert len(result["result"]["messages"]) > 0

        # Verify metrics were recorded
        assert global_metrics.total_requests == 1
        assert global_metrics.user_requests == 1

    def test_admin_agent_routing(self):
        """Test that admin agent routes correctly through orchestrator."""
        orchestrator = create_orchestrator_graph()

        result = orchestrator.invoke({
            "mode": "admin",
            "admin_state": {
                "messages": [HumanMessage(content="list")],
                "intent": None,
                "action_data": {},
                "admin_id": "test_admin",
                "thread_id": "admin_test_admin"
            },
            "thread_id": "admin_test_admin",
            "session_id": "test_session",
            "events": [],
            "metrics": {},
            "shared_data": {}
        })

        # Verify result structure
        assert result is not None
        assert "result" in result
        assert result["result"] is not None

        # Verify metrics were recorded
        assert global_metrics.total_requests == 1
        assert global_metrics.admin_requests == 1

    def test_metrics_collection(self):
        """Test that metrics are collected correctly."""
        orchestrator = create_orchestrator_graph()

        # Make multiple requests
        for i in range(3):
            orchestrator.invoke({
                "mode": "user",
                "user_state": {
                    "messages": [HumanMessage(content=f"Question {i}")],
                    "intent": None,
                    "reservation_data": {},
                    "thread_id": f"test_thread_{i}"
                },
                "thread_id": f"test_thread_{i}",
                "session_id": "test_session",
                "events": [],
                "metrics": {},
                "shared_data": {}
            })

        # Verify metrics
        snapshot = global_metrics.get_snapshot()
        assert snapshot["requests"]["total"] == 3
        assert snapshot["requests"]["user"] == 3
        assert snapshot["response_times"]["avg"] > 0
        assert snapshot["response_times"]["p95"] > 0

    def test_event_emission(self):
        """Test that events are emitted correctly."""
        orchestrator = create_orchestrator_graph()

        # Track events
        received_events = []

        def event_handler(event):
            received_events.append(event)

        global_event_bus.subscribe("test_event", event_handler)

        # Publish a test event through the system
        from src.shared import publish_event

        publish_event(
            event_type="test_event",
            data={"test": "data"},
            source="test"
        )

        # Verify event was received
        assert len(received_events) == 1
        assert received_events[0].event_type == "test_event"
        assert received_events[0].data["test"] == "data"

    def test_error_handling(self):
        """Test that errors are handled gracefully."""
        orchestrator = create_orchestrator_graph()

        # Try with invalid mode
        result = orchestrator.invoke({
            "mode": "invalid_mode",
            "user_state": {},
            "thread_id": "test_thread",
            "session_id": "test_session",
            "events": [],
            "metrics": {},
            "shared_data": {}
        })

        # Verify error is captured
        assert result["error"] is not None
        assert "Unknown mode" in result["error"]

        # Verify error metrics
        assert global_metrics.error_count == 1

    def test_shared_database_service(self):
        """Test that shared database service works correctly."""
        from src.shared import db_service

        # Test listing pending reservations
        pending = db_service.list_pending_reservations()
        assert isinstance(pending, list)

        # Test getting reservation (may not exist)
        reservation = db_service.get_reservation(999999)
        assert reservation is None  # Non-existent reservation

    def test_shared_llm_pool(self):
        """Test that shared LLM pool works correctly."""
        from src.shared import get_llm

        # Get LLM instance
        llm = get_llm()
        assert llm is not None

        # Get LLM again - should be same instance
        llm2 = get_llm()
        assert llm is llm2  # Singleton pattern

    def test_backward_compatibility(self):
        """Test that existing CLI interfaces still work."""
        from src.chatbot.main import ParkingChatbot
        from src.chatbot.admin_main import AdminAgent

        # Test user CLI
        chatbot = ParkingChatbot()
        response = chatbot.chat("What are your hours?")
        assert len(response) > 0
        assert isinstance(response, str)

        # Test admin CLI
        admin = AdminAgent()
        response = admin.chat("list")
        assert len(response) > 0
        assert isinstance(response, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
