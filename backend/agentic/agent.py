#!/usr/bin/env python3
"""
ADK Agent Entry Point

This is the main agent file that 'adk web' and 'adk run' look for.
It defines the agent with Gemini 2.0 Flash and two simple tools.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Import ADK
from google.adk import Agent

# Initialize Vertex AI
import vertexai

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = "us-central1"  # Gemini works best in us-central1

vertexai.init(project=project_id, location=location)


# Define tools for the agent
def greet_user(name: str) -> str:
    """
    Greets a user by name with a friendly message.

    Args:
        name: The name of the person to greet

    Returns:
        A personalized greeting message
    """
    return f"Hello {name}! The ADK agent with Gemini is working perfectly. Ready to build the contract extraction system!"


def calculate_sum(a: float, b: float) -> float:
    """
    Adds two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    result = a + b
    return result


# Create and export the agent
# ADK looks for a variable named 'agent' or 'app'
agent = Agent(
    model="gemini-2.0-flash-exp",
    name="contract_reader_agent",
    instruction=(
        "You are a helpful AI assistant testing the Google ADK framework with Gemini. "
        "When asked to greet someone, use the greet_user tool. "
        "When asked to perform calculations, use the calculate_sum tool. "
        "Be friendly, concise, and helpful."
    ),
    tools=[greet_user, calculate_sum]
)

print(f"[ADK] Agent initialized: {agent.name}")
print(f"[ADK] Model: gemini-2.0-flash-exp")
print(f"[ADK] Tools: {len(agent.tools)} available")
