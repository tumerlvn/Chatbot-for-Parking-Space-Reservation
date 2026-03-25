"""
Main Entry Point for the Parking Reservation Chatbot
Provides a CLI interface to interact with the chatbot
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage

from .graph import create_chatbot_graph
from .state import GraphState


# Load environment variables (for OpenAI API key)
load_dotenv()


class ParkingChatbot:
    """
    Wrapper class for the parking reservation chatbot.
    Manages conversation state and provides a simple interface.
    """

    def __init__(self):
        """Initialize the chatbot graph"""
        print("Initializing Parking Reservation Chatbot...")
        self.app = create_chatbot_graph()
        self.thread_id = "default_thread"
        print("✓ Chatbot ready!")

    def chat(self, user_message: str) -> str:
        """
        Send a message to the chatbot and get a response.

        Args:
            user_message: The user's input message

        Returns:
            The chatbot's response
        """
        # Create initial state with user message
        config = {"configurable": {"thread_id": self.thread_id}}

        # Invoke the graph
        # Note: Only pass messages (with add_messages reducer), intent, and next_action
        # Do NOT pass reservation_data - it will be loaded from checkpoint to preserve
        # data collected across multiple turns (name, car_number, times, etc.)
        result = self.app.invoke(
            {
                "messages": [HumanMessage(content=user_message)],
                "intent": None,        # Router recalculates each turn
                "next_action": None    # Handler nodes set this each turn
                # reservation_data: omitted - loaded from checkpoint
            },
            config=config
        )

        # Extract the last AI message
        if result["messages"]:
            last_message = result["messages"][-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)

        return "I'm sorry, I didn't understand that. Could you please rephrase?"

    def stream_chat(self, user_message: str):
        """
        Stream the chatbot response (for real-time display).

        Args:
            user_message: The user's input message

        Yields:
            Chunks of the chatbot's response
        """
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.app.stream(
            {
                "messages": [HumanMessage(content=user_message)],
                "intent": None,
                "next_action": None
                # reservation_data: omitted - loaded from checkpoint
            },
            config=config
        ):
            for node_name, node_state in event.items():
                if "messages" in node_state and node_state["messages"]:
                    last_message = node_state["messages"][-1]
                    if hasattr(last_message, 'content'):
                        yield f"[{node_name}] {last_message.content}\n"

    def get_conversation_history(self) -> list:
        """
        Get the full conversation history.

        Returns:
            List of messages in the conversation
        """
        config = {"configurable": {"thread_id": self.thread_id}}
        state = self.app.get_state(config)
        return state.values.get("messages", []) if state.values else []

    def reset(self):
        """Reset the conversation (start fresh)"""
        self.thread_id = f"thread_{os.urandom(4).hex()}"
        print("✓ Conversation reset!")


def run_cli():
    """
    Run the chatbot in CLI mode.
    Interactive command-line interface for testing.
    """
    print("\n" + "="*60)
    print("🚗 SmartPark City Center - Parking Reservation Chatbot")
    print("="*60)
    print("\nCommands:")
    print("  - Type your message to chat")
    print("  - 'reset' to start a new conversation")
    print("  - 'history' to view conversation history")
    print("  - 'exit' or 'quit' to quit")
    print("\n" + "="*60 + "\n")

    chatbot = ParkingChatbot()

    while True:
        try:
            user_input = input("\n🧑 You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nThank you for using SmartPark! Goodbye! 👋")
                break

            if user_input.lower() == 'reset':
                chatbot.reset()
                continue

            if user_input.lower() == 'history':
                history = chatbot.get_conversation_history()
                print("\n" + "="*60)
                print("Conversation History:")
                print("="*60)
                for msg in history:
                    role = "You" if msg.__class__.__name__ == "HumanMessage" else "Bot"
                    content = msg.content if hasattr(msg, 'content') else str(msg)
                    print(f"\n{role}: {content}")
                print("\n" + "="*60)
                continue

            # Send message and get response
            print("\n🤖 Bot: ", end="", flush=True)
            response = chatbot.chat(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment variables.")
        print("Please set it in a .env file or as an environment variable.")
        print("Example: export OPENAI_API_KEY='your-api-key-here'\n")

    run_cli()
