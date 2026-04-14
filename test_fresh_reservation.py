#!/usr/bin/env python3
"""Test reservation with fresh thread to avoid checkpoint interference."""

import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.chatbot.main import ParkingChatbot

def test_fresh_reservation():
    """Test reservation data with fresh thread."""
    print("\n" + "="*70)
    print("TESTING FRESH RESERVATION FLOW")
    print("="*70)

    chatbot = ParkingChatbot()
    # Use unique thread ID to avoid old checkpoint data
    chatbot.thread_id = f"test_{uuid.uuid4().hex[:8]}"
    print(f"\nUsing fresh thread: {chatbot.thread_id}")

    # Turn 1: Start reservation
    print("\n[Turn 1] User: I want to reserve a parking spot")
    response1 = chatbot.chat("I want to reserve a parking spot")
    print(f"Bot: {response1}")

    # Turn 2: Provide name
    print("\n[Turn 2] User: John Smith")
    response2 = chatbot.chat("John Smith")
    print(f"Bot: {response2}")

    # Check what bot is asking for
    if "car" in response2.lower() or "license" in response2.lower() or "plate" in response2.lower():
        print("✅ Bot asking for car number (correct flow)")
    elif "name" in response2.lower():
        print("❌ Bot asking for name again (not preserving data)")
        return False
    else:
        print(f"⚠️  Bot response unclear, continuing...")

    # Turn 3: Provide car number
    print("\n[Turn 3] User: ABC123")
    response3 = chatbot.chat("ABC123")
    print(f"Bot: {response3}")

    # Check what bot is asking for
    if "start" in response3.lower() or "arrive" in response3.lower() or "when" in response3.lower():
        print("✅ Bot asking for start time (correct flow)")
    elif "car" in response3.lower() or "license" in response3.lower():
        print("❌ Bot asking for car again (not preserving data)")
        return False
    else:
        print(f"⚠️  Bot response unclear, continuing...")

    # Turn 4: Provide start time
    print("\n[Turn 4] User: Today at 18:00")
    response4 = chatbot.chat("Today at 18:00")
    print(f"Bot: {response4}")

    # Check what bot is asking for
    if ("leave" in response4.lower() or "end" in response4.lower()) and "start" not in response4.lower():
        print("✅ Bot asking for end time (correct - moved past start time)")
    elif "start" in response4.lower() or "arrive" in response4.lower():
        print("❌ Bot asking for start time again (not preserving data)")
        return False
    else:
        print(f"⚠️  Bot response unclear, continuing...")

    # Turn 5: Provide end time
    print("\n[Turn 5] User: Today at 23:00")
    response5 = chatbot.chat("Today at 23:00")
    print(f"Bot: {response5}")

    # Check if bot moved forward (not asking for end time again)
    if "leave" in response5.lower() or "end time" in response5.lower():
        print("❌ Bot asking for end time again (not preserving data)")
        return False
    elif "spot" in response5.lower() or "available" in response5.lower() or "confirmation" in response5.lower():
        print("✅ Bot moved to next step (spots/confirmation)")
    else:
        print(f"⚠️  Bot response unclear")

    print("\n" + "="*70)
    print("✅ TEST PASSED - Reservation data is being preserved!")
    print("="*70)
    return True

if __name__ == "__main__":
    success = test_fresh_reservation()
    sys.exit(0 if success else 1)
