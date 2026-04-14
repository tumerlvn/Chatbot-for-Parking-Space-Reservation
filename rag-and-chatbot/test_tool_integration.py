"""Integration test for LangChain tool."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from chatbot.mcp_tools import write_confirmation_tool
from mcp.confirmation_writer import CONFIRMATION_FILE


def test_langchain_tool():
    """Test that the LangChain tool works end-to-end."""
    print("\n" + "="*60)
    print("Testing LangChain Tool Integration")
    print("="*60 + "\n")

    # Clean state
    if os.path.exists(CONFIRMATION_FILE):
        os.remove(CONFIRMATION_FILE)

    # Test tool invocation
    print("Invoking write_confirmation tool...")
    result = write_confirmation_tool.invoke({
        "reservation_id": 42,
        "name": "Jane Doe",
        "car_number": "XYZ-9876",
        "start_time": "2026-04-05 10:00:00",
        "end_time": "2026-04-05 18:00:00"
    })

    print(f"Tool result: {result}\n")

    # Verify result
    assert "✅" in result or "Confirmation written" in result, f"Expected success message, got: {result}"

    # Verify file was created
    assert os.path.exists(CONFIRMATION_FILE), "Confirmation file should exist"

    # Verify file contents
    with open(CONFIRMATION_FILE, 'r') as f:
        content = f.read()
        print("File contents:")
        print(content)
        print()

        assert "Jane Doe" in content
        assert "XYZ-9876" in content
        assert "2026-04-05 10:00:00 to 2026-04-05 18:00:00" in content
        assert "Res#42" in content

    print("="*60)
    print("✅ LangChain tool integration test passed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_langchain_tool()
