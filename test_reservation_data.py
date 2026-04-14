#!/usr/bin/env python3
"""Test that reservation data is preserved across conversation turns."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.chatbot.main import ParkingChatbot

def test_reservation_data_persistence():
    """Test that reservation data accumulates properly."""
    print("\n" + "="*70)
    print("TESTING RESERVATION DATA PERSISTENCE")
    print("="*70)

    chatbot = ParkingChatbot()

    # Simulate user conversation for creating a reservation
    print("\n[Turn 1] User initiates reservation")
    response1 = chatbot.chat("I want to make a reservation")
    print(f"Bot: {response1[:100]}...")

    print("\n[Turn 2] User provides name")
    response2 = chatbot.chat("John Smith")
    print(f"Bot: {response2[:100]}...")

    print("\n[Turn 3] User provides car number")
    response3 = chatbot.chat("ABC123")
    print(f"Bot: {response3[:100]}...")

    print("\n[Turn 4] User provides start time")
    response4 = chatbot.chat("Today at 18:00")
    print(f"Bot: {response4[:100]}...")

    # Check if bot is asking for end time (not repeating start time question)
    if "leave" in response4.lower() or "end time" in response4.lower():
        print("\n✅ Bot correctly moved to asking for end time")
    elif "start" in response4.lower() or "arrive" in response4.lower():
        print("\n❌ Bot is still asking for start time - data not preserved!")
        return False
    else:
        print(f"\n⚠️  Unexpected response: {response4}")

    print("\n[Turn 5] User provides end time")
    response5 = chatbot.chat("Tomorrow at 14:00")
    print(f"Bot: {response5[:100]}...")

    # Check if bot moved on (not asking for end time again)
    if "leave" in response5.lower() or "end time" in response5.lower():
        print("\n❌ Bot is repeating end time question - data not preserved!")
        return False
    else:
        print("\n✅ Bot moved on from end time question - data preserved!")

    print("\n" + "="*70)
    print("✅ RESERVATION DATA PERSISTENCE TEST PASSED")
    print("="*70)
    return True

if __name__ == "__main__":
    success = test_reservation_data_persistence()
    sys.exit(0 if success else 1)
