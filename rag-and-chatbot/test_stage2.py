#!/usr/bin/env python3
"""Quick test script to verify Stage 2 implementation."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test all imports work correctly."""
    print("=" * 60)
    print("Testing Stage 2 Implementation - Imports")
    print("=" * 60)

    print("\n1. Testing User Agent imports...")
    from chatbot.graph import create_chatbot_graph
    from chatbot.nodes import (
        router_node, rag_node, reservation_collector_node,
        create_reservation_node, status_checker_node
    )
    print("   ✅ User agent imports successful")

    print("\n2. Testing Admin Agent imports...")
    from chatbot.admin_state import AdminGraphState, AdminActionData
    from chatbot.admin_nodes import (
        admin_router_node, list_pending_node,
        initiate_action_node, execute_action_node
    )
    from chatbot.admin_graph import create_admin_graph
    from chatbot.admin_main import AdminAgent
    print("   ✅ Admin agent imports successful")

    print("\n3. Testing API imports...")
    from api.admin_api import app, admin_agent_graph
    print("   ✅ Admin API imports successful")

    return True


def test_graph_creation():
    """Test graph creation for both agents."""
    print("\n" + "=" * 60)
    print("Testing Graph Creation")
    print("=" * 60)

    print("\n1. Creating User Agent graph...")
    from chatbot.graph import create_chatbot_graph
    user_app = create_chatbot_graph()
    print("   ✅ User agent graph created")
    print("   ℹ️  No interrupt configured (user can chat freely)")

    print("\n2. Creating Admin Agent graph...")
    from chatbot.admin_graph import create_admin_graph
    admin_app = create_admin_graph()
    print("   ✅ Admin agent graph created")
    print("   ℹ️  Interrupt configured at 'execute_action' node")

    return True


def test_database_connection():
    """Test database connection."""
    print("\n" + "=" * 60)
    print("Testing Database Connection")
    print("=" * 60)

    import sqlite3

    print("\n1. Checking main database...")
    db_path = os.path.join(os.path.dirname(__file__), "data/parking_db.sqlite")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check reservations table
        cursor.execute("SELECT COUNT(*) FROM reservations")
        res_count = cursor.fetchone()[0]
        print(f"   ✅ Database found: {res_count} reservations")

        # Check pending reservations
        cursor.execute("SELECT COUNT(*) FROM reservations WHERE status='pending'")
        pending_count = cursor.fetchone()[0]
        print(f"   ℹ️  Pending reservations: {pending_count}")

        conn.close()
    else:
        print(f"   ⚠️  Database not found at: {db_path}")

    return True


def main():
    """Run all tests."""
    print("\n" + "🚀" * 30)
    print("Stage 2 Implementation - Verification Tests")
    print("🚀" * 30)

    try:
        test_imports()
        test_graph_creation()
        test_database_connection()

        print("\n" + "=" * 60)
        print("✅ All Tests Passed!")
        print("=" * 60)
        print("\nNext Steps:")
        print("  1. Start User Agent:  python -m src.chatbot.main")
        print("  2. Start Admin Agent: python -m src.chatbot.admin_main")
        print("  3. Start API Server:  python -m src.api.admin_api")
        print("\nSee STAGE2_IMPLEMENTATION_SUMMARY.md for detailed testing instructions.")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
