#!/usr/bin/env python3
"""Quick test of orchestrator integration."""

import sys
import os

# Add the path to the rag-and-chatbot directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.chatbot.main import ParkingChatbot

def test_user_agent():
    """Test user agent through orchestrator."""
    print("\n" + "="*60)
    print("Testing User Agent through Orchestrator")
    print("="*60)

    try:
        chatbot = ParkingChatbot()
        response = chatbot.chat("What are your hours?")
        print(f"\nResponse: {response}")
        print("\n✅ User agent test passed!")
        return True
    except Exception as e:
        print(f"\n❌ User agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_user_agent()
    sys.exit(0 if success else 1)
