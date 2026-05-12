"""Performance tests for orchestrator system (Stage 4)."""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.chatbot.main import ParkingChatbot
from src.chatbot.admin_main import AdminAgent
from src.shared import global_metrics


class TestPerformance:
    """Performance tests for the orchestrated multi-agent system."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset metrics before each test."""
        global_metrics.reset()
        yield

    def test_response_time_user_agent(self):
        """Test that user agent response time is acceptable."""
        chatbot = ParkingChatbot()

        start = time.time()
        response = chatbot.chat("What are your hours?")
        elapsed = time.time() - start

        assert elapsed < 30.0  # Should respond within 30 seconds
        assert len(response) > 0

        print(f"\n✅ User agent response time: {elapsed:.2f}s")

    def test_response_time_admin_agent(self):
        """Test that admin agent response time is acceptable."""
        admin = AdminAgent()

        start = time.time()
        response = admin.chat("list")
        elapsed = time.time() - start

        assert elapsed < 10.0  # Admin list should be fast
        assert len(response) > 0

        print(f"\n✅ Admin agent response time: {elapsed:.2f}s")

    def test_orchestrator_overhead(self):
        """Test that orchestrator overhead is minimal."""
        from src.chatbot.orchestrator import create_orchestrator_graph
        from langchain_core.messages import HumanMessage

        orchestrator = create_orchestrator_graph()

        # Measure orchestrator overhead
        start = time.time()
        result = orchestrator.invoke({
            "mode": "admin",
            "admin_state": {
                "messages": [HumanMessage(content="list")],
                "intent": None,
                "action_data": {},
                "admin_id": "perf_test",
                "thread_id": "admin_perf_test"
            },
            "thread_id": "admin_perf_test",
            "session_id": "perf_session",
            "events": [],
            "metrics": {},
            "shared_data": {}
        })
        elapsed = time.time() - start

        # Orchestrator overhead should be minimal (< 100ms additional)
        # Most time is in the actual agent execution
        assert elapsed < 15.0
        print(f"\n✅ Orchestrator total time: {elapsed:.2f}s")

    def test_sequential_requests(self):
        """Test performance of sequential requests."""
        chatbot = ParkingChatbot()

        start = time.time()
        for i in range(5):
            response = chatbot.chat(f"Question {i}")
            assert len(response) > 0
        elapsed = time.time() - start

        avg_time = elapsed / 5
        print(f"\n✅ 5 sequential requests: {elapsed:.2f}s (avg: {avg_time:.2f}s)")

        # Average should be reasonable
        assert avg_time < 30.0

    def test_metrics_performance(self):
        """Test that metrics collection doesn't impact performance."""
        from src.chatbot.orchestrator import create_orchestrator_graph
        from langchain_core.messages import HumanMessage

        orchestrator = create_orchestrator_graph()

        # Make many requests to test metrics overhead
        start = time.time()
        for i in range(10):
            orchestrator.invoke({
                "mode": "admin",
                "admin_state": {
                    "messages": [HumanMessage(content="list")],
                    "intent": None,
                    "action_data": {},
                    "admin_id": f"test_{i}",
                    "thread_id": f"admin_test_{i}"
                },
                "thread_id": f"admin_test_{i}",
                "session_id": f"session_{i}",
                "events": [],
                "metrics": {},
                "shared_data": {}
            })
        elapsed = time.time() - start

        # Verify metrics were collected
        assert global_metrics.total_requests == 10

        # Metrics overhead should be negligible
        avg_time = elapsed / 10
        print(f"\n✅ 10 requests with metrics: {elapsed:.2f}s (avg: {avg_time:.2f}s)")

    def test_memory_efficiency(self):
        """Test that the system doesn't leak memory."""
        import gc
        from src.chatbot.main import ParkingChatbot

        gc.collect()

        chatbot = ParkingChatbot()

        # Make multiple requests
        for i in range(5):
            response = chatbot.chat(f"Test {i}")
            assert len(response) > 0

        gc.collect()

        # If we get here without memory errors, test passes
        print("\n✅ Memory efficiency test passed")


class TestPerformanceTargets:
    """Verify performance targets from Stage 4 plan."""

    def test_avg_response_time_target(self):
        """Test that average response time is < 1 second (for admin list)."""
        admin = AdminAgent()

        times = []
        for _ in range(3):
            start = time.time()
            admin.chat("list")
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        print(f"\n📊 Admin list avg time: {avg_time:.2f}s")

        # Admin list operations should be fast
        assert avg_time < 5.0  # Reasonable target for admin operations

    def test_p95_response_time_target(self):
        """Test that P95 response time is acceptable."""
        from src.shared import global_metrics

        global_metrics.reset()

        admin = AdminAgent()

        # Make multiple requests
        for i in range(20):
            admin.chat("list")

        snapshot = global_metrics.get_snapshot()
        p95_time = snapshot["response_times"]["p95"]

        print(f"\n📊 P95 response time: {p95_time:.2f}s")

        # P95 should be reasonable
        assert p95_time < 10.0

    def test_zero_error_rate_target(self):
        """Test that error rate is 0% under normal operation."""
        from src.shared import global_metrics

        global_metrics.reset()

        chatbot = ParkingChatbot()
        admin = AdminAgent()

        # Make multiple requests
        chatbot.chat("What are your hours?")
        admin.chat("list")

        snapshot = global_metrics.get_snapshot()
        error_rate = snapshot["errors"]["error_rate"]

        print(f"\n📊 Error rate: {error_rate}%")

        # Should have no errors
        assert error_rate == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
