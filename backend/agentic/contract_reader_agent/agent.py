#!/usr/bin/env python3
"""
Contract Reader Agent - Hello World Version

ADK Entry Point: This file is loaded by 'adk web' and 'adk run'
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Import ADK
from google.adk import Agent

# Initialize Vertex AI
import vertexai

project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "contract-reader-2-dev")
location = "us-central1"

vertexai.init(project=project_id, location=location)


# Tool 1: Greeting tool
def greet_user(name: str) -> str:
    """
    Greets a user by name with a friendly message.

    Args:
        name: The name of the person to greet

    Returns:
        A personalized greeting message
    """
    return f"Hello {name}! The ADK + Gemini agent is working perfectly!"


# Tool 2: Calculator tool
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


# Create the agent - ADK expects a variable named 'root_agent'
root_agent = Agent(
    model="gemini-2.0-flash-exp",
    name="contract_reader_agent",
    instruction=(
        "You are a helpful AI assistant for testing the ADK framework. "
        "Use the greet_user tool when asked to greet someone. "
        "Use the calculate_sum tool for math. "
        "Be friendly and concise."
    ),
    tools=[greet_user, calculate_sum]
)

# Also export as 'agent' for backwards compatibility
agent = root_agent
