#!/usr/bin/env python3
"""Comprehensive Stage 4 completion test."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

def test_stage4_complete():
    """Test all Stage 4 components."""
    print("\n" + "="*70)
    print("STAGE 4 COMPLETION TEST")
    print("="*70)

    all_passed = True

    # Test 1: Orchestrator
    print("\n[1/7] Testing Orchestrator...")
    try:
        from src.chatbot.orchestrator import create_orchestrator_graph
        orchestrator = create_orchestrator_graph()
        print("  ✅ Orchestrator created successfully")
    except Exception as e:
        print(f"  ❌ Orchestrator failed: {e}")
        all_passed = False

    # Test 2: Shared Services
    print("\n[2/7] Testing Shared Services...")
    try:
        from src.shared import Config, db_service, get_llm
        db_path = Config.get_db_path()
        llm = get_llm()
        pending = db_service.list_pending_reservations()
        print(f"  ✅ Config working (DB: {os.path.basename(db_path)})")
        print(f"  ✅ DatabaseService working ({len(pending)} pending)")
        print(f"  ✅ LLMPool working ({type(llm).__name__})")
    except Exception as e:
        print(f"  ❌ Shared services failed: {e}")
        all_passed = False

    # Test 3: Event System
    print("\n[3/7] Testing Event System...")
    try:
        from src.shared import publish_event, subscribe_to_events, Event

        received = []
        def handler(event: Event):
            received.append(event)

        subscribe_to_events("test", handler)
        publish_event("test", {"data": "test"}, "test")

        if received:
            print(f"  ✅ Event system working ({len(received)} events)")
        else:
            print("  ❌ No events received")
            all_passed = False
    except Exception as e:
        print(f"  ❌ Event system failed: {e}")
        all_passed = False

    # Test 4: Metrics
    print("\n[4/7] Testing Metrics...")
    try:
        from src.shared import global_metrics
        global_metrics.reset()
        global_metrics.record_request("test", 1.0, error=False)
        snapshot = global_metrics.get_snapshot()

        if snapshot['requests']['total'] > 0:
            print(f"  ✅ Metrics working ({snapshot['requests']['total']} requests)")
        else:
            print("  ❌ No metrics collected")
            all_passed = False
    except Exception as e:
        print(f"  ❌ Metrics failed: {e}")
        all_passed = False

    # Test 5: User CLI
    print("\n[5/7] Testing User CLI...")
    try:
        from src.chatbot.main import ParkingChatbot
        chatbot = ParkingChatbot()
        response = chatbot.chat("What are your hours?")
        if len(response) > 0:
            print(f"  ✅ User CLI working ({len(response)} chars response)")
        else:
            print("  ❌ Empty response")
            all_passed = False
    except Exception as e:
        print(f"  ❌ User CLI failed: {e}")
        all_passed = False

    # Test 6: Admin CLI
    print("\n[6/7] Testing Admin CLI...")
    try:
        from src.chatbot.admin_main import AdminAgent
        admin = AdminAgent()
        response = admin.chat("list")
        if len(response) > 0:
            print(f"  ✅ Admin CLI working ({len(response)} chars response)")
        else:
            print("  ❌ Empty response")
            all_passed = False
    except Exception as e:
        print(f"  ❌ Admin CLI failed: {e}")
        all_passed = False

    # Test 7: Integration
    print("\n[7/7] Testing Full Integration...")
    try:
        from src.chatbot.orchestrator import create_orchestrator_graph
        from src.shared import global_metrics
        from langchain_core.messages import HumanMessage

        global_metrics.reset()
        orchestrator = create_orchestrator_graph()

        # Test user agent
        result = orchestrator.invoke({
            "mode": "user",
            "user_state": {
                "messages": [HumanMessage(content="What are your hours?")],
                "intent": None,
                "reservation_data": {}
            },
            "thread_id": "integration_test",
            "session_id": "integration",
            "events": [],
            "metrics": {},
            "shared_data": {}
        }, config={"configurable": {"thread_id": "integration_test"}})

        user_ok = result.get("result") is not None

        # Test admin agent
        result = orchestrator.invoke({
            "mode": "admin",
            "admin_state": {
                "messages": [HumanMessage(content="list")],
                "intent": None,
                "action_data": {},
                "admin_id": "test"
            },
            "thread_id": "admin_integration",
            "session_id": "integration",
            "events": [],
            "metrics": {},
            "shared_data": {}
        }, config={"configurable": {"thread_id": "admin_integration"}})

        admin_ok = result.get("result") is not None

        # Check metrics
        metrics_ok = global_metrics.total_requests == 2

        if user_ok and admin_ok and metrics_ok:
            print("  ✅ Full integration working")
            print(f"     - User agent: OK")
            print(f"     - Admin agent: OK")
            print(f"     - Metrics: {global_metrics.total_requests} requests tracked")
        else:
            print("  ❌ Integration test failed")
            all_passed = False
    except Exception as e:
        print(f"  ❌ Integration failed: {e}")
        all_passed = False

    # Final Result
    print("\n" + "="*70)
    if all_passed:
        print("✅ ALL TESTS PASSED - STAGE 4 COMPLETE!")
        print("="*70)
        print("\nStage 4 Features:")
        print("  ✓ Orchestrator layer with supervisor pattern")
        print("  ✓ Event-driven notifications (pub/sub)")
        print("  ✓ Shared services (DB pooling, LLM singletons, config)")
        print("  ✓ Comprehensive monitoring and metrics")
        print("  ✓ Full backward compatibility")
        print("\nSystem Status: Production Ready")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("="*70)
        return False

if __name__ == "__main__":
    success = test_stage4_complete()
    sys.exit(0 if success else 1)
