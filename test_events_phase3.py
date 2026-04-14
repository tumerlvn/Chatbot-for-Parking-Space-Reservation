#!/usr/bin/env python3
"""Test event system integration in Phase 3."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.shared import global_event_bus, subscribe_to_events, Event
from src.chatbot.orchestrator import create_orchestrator_graph
from langchain_core.messages import HumanMessage

def test_event_system():
    """Test that events are published and handled correctly."""
    print("\n" + "="*60)
    print("Testing Event System Integration")
    print("="*60)

    # Track received events
    received_events = []

    def event_handler(event: Event):
        """Test event handler that captures events."""
        received_events.append(event)

    # Subscribe to all events
    subscribe_to_events("*", event_handler)

    print("\n1. Creating orchestrator...")
    orchestrator = create_orchestrator_graph()

    print("\n2. Simulating user agent request...")
    result = orchestrator.invoke({
        "mode": "user",
        "user_state": {
            "messages": [HumanMessage(content="What are your hours?")],
            "intent": None,
            "reservation_data": {},
            "thread_id": "test_event_thread"
        },
        "thread_id": "test_event_thread",
        "session_id": "test_event_session",
        "events": [],
        "metrics": {},
        "shared_data": {}
    })

    print(f"\n3. Events received: {len(received_events)}")

    if received_events:
        print("\n✅ Event system working!")
        for i, event in enumerate(received_events, 1):
            print(f"\n   Event {i}:")
            print(f"   - Type: {event.event_type}")
            print(f"   - Source: {event.source}")
            print(f"   - Data: {event.data}")
    else:
        print("\n⚠️  No events received (this is OK for Q&A queries)")
        print("   Events are only triggered for reservations/approvals")

    # Test manual event publication
    print("\n4. Testing manual event publication...")
    from src.shared import publish_event

    publish_event(
        event_type="test_event",
        data={"message": "This is a test"},
        source="test_script"
    )

    # Check if test event was received
    test_events = [e for e in received_events if e.event_type == "test_event"]
    if test_events:
        print("✅ Manual event publication working!")
    else:
        print("❌ Manual event publication failed")
        return False

    print("\n✅ Event system test passed!")
    return True

if __name__ == "__main__":
    success = test_event_system()
    sys.exit(0 if success else 1)
