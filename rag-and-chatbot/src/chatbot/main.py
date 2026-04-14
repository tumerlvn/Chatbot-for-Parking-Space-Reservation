"""Main entry point for parking reservation chatbot."""

import os
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage

from .orchestrator import create_orchestrator_graph

load_dotenv()


class ParkingChatbot:
    """Wrapper for parking reservation chatbot with conversation management."""

    def __init__(self):
        print("Initializing Parking Reservation Chatbot...")
        self.orchestrator = create_orchestrator_graph()
        self.thread_id = "default_thread"
        print("Chatbot ready.")

    def chat(self, user_message: str) -> str:
        """Send message to chatbot and return response."""
        # Route through orchestrator with checkpoint support
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.orchestrator.invoke({
            "mode": "user",
            "user_state": {
                "messages": [HumanMessage(content=user_message)],
                "intent": None,
                "next_action": None
            },
            "thread_id": self.thread_id,
            "session_id": self.thread_id,
            "events": [],
            "metrics": {},
            "shared_data": {}
        }, config=config)

        # Extract messages from orchestrator state
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)

        return "I'm sorry, I didn't understand that. Could you please rephrase?"

    def stream_chat(self, user_message: str):
        """Stream chatbot response for real-time display."""
        # Stream through orchestrator (now has checkpointer)
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.orchestrator.stream(
            {
                "mode": "user",
                "user_state": {
                    "messages": [HumanMessage(content=user_message)],
                    "intent": None,
                    "next_action": None
                },
                "thread_id": self.thread_id,
                "session_id": self.thread_id,
                "events": [],
                "metrics": {},
                "shared_data": {}
            },
            config=config
        ):
            for node_name, node_state in event.items():
                if "messages" in node_state and node_state["messages"]:
                    last_message = node_state["messages"][-1]
                    if hasattr(last_message, 'content'):
                        yield f"[{node_name}] {last_message.content}\n"

    def get_conversation_history(self) -> list:
        """Return full conversation history."""
        # Get history from orchestrator checkpoint
        config = {"configurable": {"thread_id": self.thread_id}}
        state = self.orchestrator.get_state(config)
        return state.values.get("messages", []) if state.values else []

    def reset(self):
        """Reset conversation to start fresh."""
        self.thread_id = f"thread_{os.urandom(4).hex()}"
        print("Conversation reset.")


def run_cli():
    """Run chatbot in interactive CLI mode."""
    print("\n" + "="*60)
    print("SmartPark City Center - Parking Reservation Chatbot")
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
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nThank you for using SmartPark. Goodbye.")
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

            print("\nBot: ", end="", flush=True)
            response = chatbot.chat(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables.")
        print("Please set it in a .env file or as an environment variable.")
        print("Example: export OPENAI_API_KEY='your-api-key-here'\n")

    run_cli()
