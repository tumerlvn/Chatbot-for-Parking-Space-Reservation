#!/usr/bin/env python3
"""Test admin agent through orchestrator."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.chatbot.admin_main import AdminAgent

def test_admin_agent():
    """Test admin agent through orchestrator."""
    print("\n" + "="*60)
    print("Testing Admin Agent through Orchestrator")
    print("="*60)

    try:
        admin = AdminAgent()
        response = admin.chat("list")
        print(f"\nResponse: {response}")
        print("\n✅ Admin agent test passed!")
        return True
    except Exception as e:
        print(f"\n❌ Admin agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_agent()
    sys.exit(0 if success else 1)
