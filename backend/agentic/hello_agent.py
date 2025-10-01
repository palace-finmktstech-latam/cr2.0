#!/usr/bin/env python3
"""
Step 1: Hello World Agent - Verifying Google ADK Setup

This is a minimal agent that demonstrates basic Google ADK functionality.
It shows how to:
1. Create a simple agent
2. Define a basic tool
3. Make the agent use the tool
4. See the agent's reasoning process

This uses Anthropic's Claude (via your existing API key), not Google's models.
"""

import os
from anthropic import Anthropic

# Simple tool definition - this will be called by the agent
def greet_user(name: str) -> str:
    """
    A simple greeting tool.

    Args:
        name: The name of the person to greet

    Returns:
        A greeting message
    """
    return f"Hello {name}! The agentic workflow setup is working correctly."


# Define the tool schema for Claude
tools = [
    {
        "name": "greet_user",
        "description": "Greets a user by name. Use this tool when you want to say hello to someone.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the person to greet"
                }
            },
            "required": ["name"]
        }
    }
]


def run_hello_agent(user_message: str) -> str:
    """
    Run a simple agent that can use tools.

    Args:
        user_message: The message from the user

    Returns:
        The agent's final response
    """
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = Anthropic(api_key=api_key)

    # Initial message to the agent
    messages = [
        {
            "role": "user",
            "content": user_message
        }
    ]

    print("[AGENT] Starting...")
    print(f"[USER] Message: {user_message}\n")

    # Agent loop - the agent might need multiple turns to complete its task
    while True:
        # Call Claude with tools
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            tools=tools,
            messages=messages
        )

        print(f"[AGENT] Thinking... (stop_reason: {response.stop_reason})")

        # Check if agent wants to use a tool
        if response.stop_reason == "tool_use":
            # Agent wants to use a tool
            tool_use_block = next(block for block in response.content if block.type == "tool_use")
            tool_name = tool_use_block.name
            tool_input = tool_use_block.input

            print(f"[TOOL] Agent calling tool: {tool_name}")
            print(f"       Input: {tool_input}")

            # Execute the tool
            if tool_name == "greet_user":
                tool_result = greet_user(**tool_input)
            else:
                tool_result = f"Error: Unknown tool {tool_name}"

            print(f"[RESULT] Tool result: {tool_result}\n")

            # Add assistant's response and tool result to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": tool_result
                    }
                ]
            })

            # Continue the loop - agent will process the tool result
            continue

        elif response.stop_reason == "end_turn":
            # Agent is done, extract the text response
            text_content = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "No response text"
            )

            print(f"[RESPONSE] Agent final response: {text_content}\n")
            return text_content

        else:
            # Unexpected stop reason
            print(f"[WARNING] Unexpected stop_reason: {response.stop_reason}")
            break

    return "Agent finished unexpectedly"


def main():
    """Main function to test the Hello World agent."""

    print("=" * 60)
    print("STEP 1: HELLO WORLD AGENT TEST")
    print("=" * 60)
    print()

    # Test 1: Simple greeting
    print("TEST 1: Ask agent to greet someone")
    print("-" * 60)
    #result = run_hello_agent("Please greet Ben and let him know if the setup is working")
    #result = run_hello_agent("Say hi to Maria and tell her what you think of her.")
    result = run_hello_agent("What's 2+2?")

    print("=" * 60)
    print("[SUCCESS] Step 1 Complete!")
    print()
    print("What you just saw:")
    print("1. The agent received your message")
    print("2. It decided to use the 'greet_user' tool")
    print("3. It called the tool with the name 'Ben'")
    print("4. The tool returned a greeting")
    print("5. The agent formulated a final response")
    print()
    print("This demonstrates the basic agentic loop:")
    print("  User -> Agent -> Tool -> Agent -> Response")
    print("=" * 60)


if __name__ == "__main__":
    main()
