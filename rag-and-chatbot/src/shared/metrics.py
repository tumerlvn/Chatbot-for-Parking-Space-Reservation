"""Metrics collection and monitoring."""

import threading
import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class Metrics:
    """
    Metrics collector for system monitoring.

    Tracks performance metrics, request counts, error rates, and response times
    across the multi-agent system.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._lock = threading.Lock()
        self._reset_metrics()

    def _reset_metrics(self):
        """Reset all metrics to initial state."""
        self.start_time = time.time()

        # Request metrics
        self.total_requests = 0
        self.user_requests = 0
        self.admin_requests = 0

        # Response time metrics
        self.response_times: List[float] = []
        self.max_response_time = 0.0
        self.min_response_time = float('inf')

        # Error metrics
        self.error_count = 0
        self.llm_errors = 0
        self.db_errors = 0

        # Reservation metrics
        self.reservations_created = 0
        self.reservations_approved = 0
        self.reservations_rejected = 0
        self.pending_reservations = 0

        # Agent-specific metrics
        self.agent_metrics = defaultdict(lambda: {
            "requests": 0,
            "avg_response_time": 0.0,
            "errors": 0
        })

    def record_request(
        self,
        agent: str,
        response_time: float,
        error: bool = False
    ):
        """
        Record a request and its metrics.

        Args:
            agent: Agent name ("user" or "admin")
            response_time: Response time in seconds
            error: Whether an error occurred
        """
        with self._lock:
            self.total_requests += 1

            if agent == "user":
                self.user_requests += 1
            elif agent == "admin":
                self.admin_requests += 1

            # Record response time
            self.response_times.append(response_time)
            self.max_response_time = max(self.max_response_time, response_time)
            self.min_response_time = min(self.min_response_time, response_time)

            # Record errors
            if error:
                self.error_count += 1
                self.agent_metrics[agent]["errors"] += 1

            # Update agent-specific metrics
            self.agent_metrics[agent]["requests"] += 1
            # Incremental average calculation
            current_avg = self.agent_metrics[agent]["avg_response_time"]
            n = self.agent_metrics[agent]["requests"]
            self.agent_metrics[agent]["avg_response_time"] = (
                (current_avg * (n - 1) + response_time) / n
            )

    def record_reservation_created(self):
        """Record a reservation creation."""
        with self._lock:
            self.reservations_created += 1

    def record_reservation_approved(self):
        """Record a reservation approval."""
        with self._lock:
            self.reservations_approved += 1

    def record_reservation_rejected(self):
        """Record a reservation rejection."""
        with self._lock:
            self.reservations_rejected += 1

    def update_pending_count(self, count: int):
        """
        Update pending reservation count.

        Args:
            count: Current pending count
        """
        with self._lock:
            self.pending_reservations = count

    def record_llm_error(self):
        """Record an LLM error."""
        with self._lock:
            self.llm_errors += 1
            self.error_count += 1

    def record_db_error(self):
        """Record a database error."""
        with self._lock:
            self.db_errors += 1
            self.error_count += 1

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a snapshot of current metrics.

        Returns:
            Dict with all current metrics
        """
        with self._lock:
            uptime = time.time() - self.start_time

            # Calculate percentiles
            p50, p95, p99 = self._calculate_percentiles()

            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": round(uptime, 2),
                "requests": {
                    "total": self.total_requests,
                    "user": self.user_requests,
                    "admin": self.admin_requests,
                    "requests_per_minute": round(self.total_requests / (uptime / 60), 2) if uptime > 0 else 0
                },
                "response_times": {
                    "avg": round(sum(self.response_times) / len(self.response_times), 3) if self.response_times else 0,
                    "min": round(self.min_response_time, 3) if self.min_response_time != float('inf') else 0,
                    "max": round(self.max_response_time, 3),
                    "p50": round(p50, 3),
                    "p95": round(p95, 3),
                    "p99": round(p99, 3)
                },
                "errors": {
                    "total": self.error_count,
                    "llm": self.llm_errors,
                    "db": self.db_errors,
                    "error_rate": round(self.error_count / self.total_requests * 100, 2) if self.total_requests > 0 else 0
                },
                "reservations": {
                    "created": self.reservations_created,
                    "approved": self.reservations_approved,
                    "rejected": self.reservations_rejected,
                    "pending": self.pending_reservations,
                    "approval_rate": round(
                        self.reservations_approved / (self.reservations_approved + self.reservations_rejected) * 100, 2
                    ) if (self.reservations_approved + self.reservations_rejected) > 0 else 0
                },
                "agents": dict(self.agent_metrics)
            }

    def _calculate_percentiles(self) -> tuple:
        """
        Calculate response time percentiles.

        Returns:
            Tuple of (p50, p95, p99)
        """
        if not self.response_times:
            return (0.0, 0.0, 0.0)

        sorted_times = sorted(self.response_times)
        n = len(sorted_times)

        def percentile(p):
            k = (n - 1) * p / 100
            f = int(k)
            c = int(k) + 1 if k < n - 1 else f
            return sorted_times[f] + (k - f) * (sorted_times[c] - sorted_times[f])

        return (percentile(50), percentile(95), percentile(99))

    def print_summary(self):
        """Print a formatted summary of metrics."""
        snapshot = self.get_snapshot()

        logger.info("="*60)
        logger.info("SYSTEM METRICS SUMMARY")
        logger.info("="*60)
        logger.info(f"Uptime: {snapshot['uptime_seconds']}s")
        logger.info(f"Timestamp: {snapshot['timestamp']}")

        logger.info("[REQUESTS]")
        logger.info(f"  Total: {snapshot['requests']['total']}")
        logger.info(f"  User: {snapshot['requests']['user']}")
        logger.info(f"  Admin: {snapshot['requests']['admin']}")
        logger.info(f"  Rate: {snapshot['requests']['requests_per_minute']} req/min")

        logger.info("[RESPONSE TIMES]")
        logger.info(f"  Average: {snapshot['response_times']['avg']}s")
        logger.info(f"  Min: {snapshot['response_times']['min']}s")
        logger.info(f"  Max: {snapshot['response_times']['max']}s")
        logger.info(f"  P50: {snapshot['response_times']['p50']}s")
        logger.info(f"  P95: {snapshot['response_times']['p95']}s")
        logger.info(f"  P99: {snapshot['response_times']['p99']}s")

        logger.info("[ERRORS]")
        logger.info(f"  Total: {snapshot['errors']['total']}")
        logger.info(f"  LLM: {snapshot['errors']['llm']}")
        logger.info(f"  Database: {snapshot['errors']['db']}")
        logger.info(f"  Error Rate: {snapshot['errors']['error_rate']}%")

        logger.info("[RESERVATIONS]")
        logger.info(f"  Created: {snapshot['reservations']['created']}")
        logger.info(f"  Approved: {snapshot['reservations']['approved']}")
        logger.info(f"  Rejected: {snapshot['reservations']['rejected']}")
        logger.info(f"  Pending: {snapshot['reservations']['pending']}")
        logger.info(f"  Approval Rate: {snapshot['reservations']['approval_rate']}%")

        logger.info("="*60)

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._reset_metrics()


# Global metrics instance
global_metrics = Metrics()


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    return global_metrics
