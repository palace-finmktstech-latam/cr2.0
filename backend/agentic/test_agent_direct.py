#!/usr/bin/env python3
"""
Direct test of the agent without the UI
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Import the agent
import sys
sys.path.insert(0, str(Path(__file__).parent / "contract_reader_agent"))

from agent import agent

print("=" * 70)
print("TESTING AGENT DIRECTLY")
print("=" * 70)
print()

# Test 1: Simple greeting
print("Test 1: Asking agent to greet Ben")
print("-" * 70)

# Use the ADK session API to interact with agent
from google.adk.sessions import InMemorySessionStore

session_store = InMemorySessionStore()
session = session_store.create()

# Send message to agent
user_message = "Please greet Ben"
print(f"User: {user_message}")
print()

try:
    # This is how you interact with ADK agents
    events = agent.execute(user_message, session=session)

    # Process events
    for event in events:
        if hasattr(event, 'content'):
            print(f"Agent: {event.content}")
        elif hasattr(event, 'text'):
            print(f"Agent: {event.text}")
        else:
            print(f"Event: {event}")

except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
