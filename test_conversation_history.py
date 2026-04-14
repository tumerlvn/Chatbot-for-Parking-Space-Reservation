#!/usr/bin/env python3
"""Test conversation history retention."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.chatbot.main import ParkingChatbot

def test_history():
    """Test that conversation history is maintained."""
    print("\n" + "="*60)
    print("Testing Conversation History")
    print("="*60)

    chatbot = ParkingChatbot()

    # First message
    print("\n1. Asking about hours...")
    response1 = chatbot.chat("What are your hours?")
    print(f"Response: {response1[:100]}...")

    # Second message
    print("\n2. Asking about prices...")
    response2 = chatbot.chat("How much does it cost?")
    print(f"Response: {response2[:100]}...")

    # Get history
    print("\n3. Getting conversation history...")
    history = chatbot.get_conversation_history()

    print(f"\nHistory has {len(history)} messages:")
    for i, msg in enumerate(history, 1):
        msg_type = "User" if "Human" in str(type(msg)) else "Bot"
        content = msg.content if hasattr(msg, 'content') else str(msg)
        print(f"  {i}. [{msg_type}] {content[:80]}...")

    # Verify history
    if len(history) >= 4:  # 2 user messages + 2 bot responses
        print("\n✅ Conversation history is being maintained!")
        return True
    else:
        print(f"\n❌ History incomplete: only {len(history)} messages")
        return False

if __name__ == "__main__":
    success = test_history()
    sys.exit(0 if success else 1)
