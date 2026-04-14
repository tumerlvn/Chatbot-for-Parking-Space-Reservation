#!/usr/bin/env python3
"""Test metrics collection in Phase 4."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.shared import global_metrics
from src.chatbot.main import ParkingChatbot
from src.chatbot.admin_main import AdminAgent

def test_metrics():
    """Test metrics collection across multiple requests."""
    print("\n" + "="*60)
    print("Testing Metrics Collection")
    print("="*60)

    # Reset metrics
    global_metrics.reset()

    print("\n1. Testing user agent requests...")
    chatbot = ParkingChatbot()

    # Make several requests
    questions = [
        "What are your hours?",
        "How much does parking cost?",
        "Do you have EV charging?"
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n   Request {i}: {question}")
        response = chatbot.chat(question)
        print(f"   Response length: {len(response)} chars")

    print("\n2. Testing admin agent requests...")
    admin = AdminAgent()

    # List pending reservations
    print("\n   Listing pending reservations...")
    response = admin.chat("list")
    print(f"   Found reservations: {'pending' in response.lower()}")

    print("\n3. Metrics snapshot:")
    snapshot = global_metrics.get_snapshot()

    print(f"\n   Total requests: {snapshot['requests']['total']}")
    print(f"   User requests: {snapshot['requests']['user']}")
    print(f"   Admin requests: {snapshot['requests']['admin']}")
    print(f"   Avg response time: {snapshot['response_times']['avg']}s")
    print(f"   P95 response time: {snapshot['response_times']['p95']}s")
    print(f"   P99 response time: {snapshot['response_times']['p99']}s")
    print(f"   Error rate: {snapshot['errors']['error_rate']}%")

    # Validate metrics
    expected_total = len(questions) + 1  # 3 user + 1 admin
    if snapshot['requests']['total'] == expected_total:
        print(f"\n✅ Metrics collection working!")
        print(f"   Captured {expected_total} requests correctly")
        return True
    else:
        print(f"\n❌ Metrics mismatch!")
        print(f"   Expected {expected_total}, got {snapshot['requests']['total']}")
        return False

if __name__ == "__main__":
    success = test_metrics()
    sys.exit(0 if success else 1)
