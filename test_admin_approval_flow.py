#!/usr/bin/env python3
"""Test the complete admin approval flow with correct thread ID."""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rag-and-chatbot'))

from src.chatbot.admin_main import AdminAgent

def test_admin_approval_flow():
    """Test that admin approval generates correct thread ID in curl command."""
    print("\n" + "="*70)
    print("TESTING ADMIN APPROVAL FLOW - THREAD ID")
    print("="*70)

    admin = AdminAgent(admin_id="test_admin")
    print(f"\nAdmin thread_id: {admin.thread_id}")

    # List pending reservations
    print("\n[Step 1] List pending reservations")
    response = admin.chat("list")
    print(f"Response length: {len(response)} chars")

    # Find a pending reservation ID
    id_match = re.search(r'ID #(\d+)', response)
    if not id_match:
        print("❌ No pending reservations found. Create one first.")
        return False

    reservation_id = int(id_match.group(1))
    print(f"✅ Found reservation ID: {reservation_id}")

    # Try to approve it
    print(f"\n[Step 2] Approve reservation #{reservation_id}")
    response = admin.chat(f"approve {reservation_id}")
    print(f"\nResponse:\n{response}\n")

    # Check for interrupt message with curl command
    if "[INTERRUPT]" in response:
        print("✅ Hit interrupt as expected")

        # Extract thread_id from curl command
        thread_match = re.search(r'thread_id=([a-zA-Z0-9_]+)', response)
        if thread_match:
            curl_thread_id = thread_match.group(1)
            print(f"✅ Curl command thread_id: {curl_thread_id}")

            # The thread ID should be the MAPPED admin thread, not the base thread
            # Base thread: admin_test_admin
            # Expected mapped thread: admin_admin_test_admin
            if curl_thread_id == f"admin_{admin.thread_id}":
                print(f"✅ Thread ID correctly mapped! ({curl_thread_id})")
                print("\n" + "="*70)
                print("✅ TEST PASSED - Thread ID mapping works correctly")
                print("="*70)
                return True
            else:
                print(f"❌ Thread ID mismatch!")
                print(f"   Expected: admin_{admin.thread_id}")
                print(f"   Got: {curl_thread_id}")
                return False
        else:
            print("❌ Could not find thread_id in curl command")
            return False
    else:
        print("❌ Did not hit interrupt (expected [INTERRUPT] message)")
        return False

if __name__ == "__main__":
    success = test_admin_approval_flow()
    sys.exit(0 if success else 1)
