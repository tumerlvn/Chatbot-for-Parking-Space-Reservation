"""Main entry point for admin agent."""

import os
import time
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage

from .admin_graph import create_admin_graph
from .admin_state import AdminGraphState

load_dotenv()


class AdminAgent:
    """Admin agent for reservation approval."""

    def __init__(self, admin_id: str = "admin1"):
        print("Initializing Admin Agent...")
        self.app = create_admin_graph()
        self.admin_id = admin_id
        self.thread_id = f"admin_{admin_id}"
        print("Admin Agent ready.")

    def chat(self, admin_message: str) -> str:
        """Send message to admin agent and return response."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.app.invoke(
            {
                "messages": [HumanMessage(content=admin_message)],
                "intent": None,
                "action_data": {},
                "admin_id": self.admin_id,
                "thread_id": self.thread_id
            },
            config=config
        )

        if result["messages"]:
            last_message = result["messages"][-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)

        return "No response from admin agent."

    def get_state(self):
        """Get current conversation state."""
        config = {"configurable": {"thread_id": self.thread_id}}
        return self.app.get_state(config)

    def reset(self):
        """Reset admin conversation."""
        self.thread_id = f"admin_{self.admin_id}_{os.urandom(4).hex()}"
        print("Admin conversation reset.")

    def wait_for_completion(self, initial_message_count: int, timeout: int = 120) -> str:
        """
        Poll the graph state waiting for new messages after an interrupt.

        Args:
            initial_message_count: Number of messages before interrupt
            timeout: Maximum seconds to wait (default 120)

        Returns:
            The new completion message, or timeout message
        """
        config = {"configurable": {"thread_id": self.thread_id}}
        start_time = time.time()
        poll_interval = 2  # Check every 2 seconds

        print("\n⏳ Waiting for API confirmation", end="", flush=True)

        while time.time() - start_time < timeout:
            time.sleep(poll_interval)
            print(".", end="", flush=True)

            try:
                state = self.app.get_state(config)
                current_message_count = len(state.values.get("messages", []))

                # Check if new messages have been added
                if current_message_count > initial_message_count:
                    print()  # New line after dots
                    # Get the new messages
                    messages = state.values.get("messages", [])
                    new_messages = messages[initial_message_count:]

                    # Return the content of the last new message
                    if new_messages:
                        last_message = new_messages[-1]
                        content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                        return content

            except Exception as e:
                print(f"\n⚠️  Error checking state: {e}")
                continue

        print()  # New line after dots
        return "⏰ Timeout: No response received from API. The request may still be processing."


def run_admin_cli():
    """Run admin agent in CLI mode."""
    print("\n" + "="*60)
    print("SmartPark Admin Interface")
    print("="*60)
    print("\nCommands:")
    print("  - 'list' or 'show pending' - List pending reservations")
    print("  - 'approve #ID' - Approve reservation")
    print("  - 'reject #ID' - Reject reservation")
    print("  - 'reset' - Start new conversation")
    print("  - 'exit' or 'quit' - Exit")
    print("\n" + "="*60 + "\n")

    admin = AdminAgent()

    while True:
        try:
            admin_input = input("\nAdmin: ").strip()

            if not admin_input:
                continue

            if admin_input.lower() in ['exit', 'quit', 'q']:
                print("\nGoodbye.")
                break

            if admin_input.lower() == 'reset':
                admin.reset()
                continue

            print("\nAgent: ", end="", flush=True)
            response = admin.chat(admin_input)
            print(response)

            # Check if we hit an interrupt (waiting for API confirmation)
            if "[INTERRUPT]" in response:
                # Get current message count before waiting
                state = admin.get_state()
                initial_message_count = len(state.values.get("messages", []))

                # Wait for the API to resume the graph and add completion message
                completion_message = admin.wait_for_completion(initial_message_count)

                # Display the completion message
                print(f"\n✅ Agent: {completion_message}")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye.")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    run_admin_cli()
