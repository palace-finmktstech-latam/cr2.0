#!/usr/bin/env python3
"""
Hello World ADK Agent with Gemini on Vertex AI

This demonstrates:
1. Google ADK agent setup
2. Using Gemini 2.0 Flash via Vertex AI
3. Tool definition and usage
4. Agent reasoning loop

Once Claude quota is approved, switching models is a single line change.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Import ADK components - using correct API
from google.adk import Agent

# Initialize Vertex AI
import vertexai

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = "us-central1"  # Gemini works best here

vertexai.init(project=project_id, location=location)

print(f"[SETUP] Initializing ADK agent...")
print(f"[SETUP] Project: {project_id}")
print(f"[SETUP] Location: {location}")
print(f"[SETUP] Model: Gemini 2.0 Flash")
print()


# Define a simple tool for the agent to use
def greet_user(name: str) -> str:
    """
    Greets a user by name with a friendly message.

    Args:
        name: The name of the person to greet

    Returns:
        A personalized greeting message
    """
    return f"Hello {name}! The ADK agent setup is working perfectly. You're ready to build the contract extraction system!"


def calculate_sum(a: float, b: float) -> float:
    """
    Adds two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


# Create the ADK agent
agent = Agent(
    model="gemini-2.0-flash-exp",  # Using Gemini for now, will switch to Claude later
    name="hello_world_agent",
    instruction=(
        "You are a helpful assistant testing the Google ADK framework. "
        "When asked to greet someone, use the greet_user tool. "
        "When asked to calculate, use the calculate_sum tool. "
        "Be friendly and concise."
    ),
    tools=[greet_user, calculate_sum]
)

print("[AGENT] Agent created successfully!")
print("[AGENT] Available tools: greet_user, calculate_sum")
print()

print("=" * 70)
print("HELLO WORLD ADK AGENT - READY!")
print("=" * 70)
print()
print("The agent is configured and ready to use.")
print()
print("To interact with the agent, you can:")
print("  1. Use adk CLI commands")
print("  2. Call agent.generate() directly")
print()
print("Try asking:")
print("  - 'Please greet Ben'")
print("  - 'What is 25 + 17?'")
print("=" * 70)


# For testing without the UI
if __name__ == "__main__":
    print()
    print("[TEST] Running quick test...")
    print()

    # Test the agent programmatically
    test_prompt = "Please greet Ben and tell him the system is ready"

    print(f"[USER] {test_prompt}")
    print()

    # Execute the agent - ADK uses send() method
    try:
        response = agent.send(test_prompt)
        print(f"[AGENT] {response}")
        print()
        print("[SUCCESS] Agent test complete!")
    except Exception as e:
        print(f"[INFO] Direct execution not available in this mode")
        print(f"[INFO] To interact with agent, use: adk web")
        print(f"[INFO] Error: {e}")

    print()
    print("To test the agent interactively:")
    print("  cd C:\\Users\\bencl\\Proyectos\\cr2.0\\backend\\agentic")
    print("  adk web")
    print()
    print("This will start a web UI where you can chat with the agent!")
