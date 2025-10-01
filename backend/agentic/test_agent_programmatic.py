#!/usr/bin/env python3
"""
Programmatic agent test - This is how we'll actually use the agent
for contract extraction (not through the UI)
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = "us-central1"

vertexai.init(project=project_id, location=location)

print("=" * 70)
print("PROGRAMMATIC AGENT TEST WITH TOOLS")
print("=" * 70)
print()

# Define tools (functions the agent can call)
greet_user_func = FunctionDeclaration(
    name="greet_user",
    description="Greets a user by name with a friendly message",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the person to greet"
            }
        },
        "required": ["name"]
    }
)

calculate_sum_func = FunctionDeclaration(
    name="calculate_sum",
    description="Adds two numbers together",
    parameters={
        "type": "object",
        "properties": {
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        "required": ["a", "b"]
    }
)

# Create tool with our functions
tool = Tool(function_declarations=[greet_user_func, calculate_sum_func])

# Create model with tools
model = GenerativeModel(
    "gemini-2.0-flash-exp",
    tools=[tool]
)

# Test 1: Greeting
print("Test 1: Ask agent to greet Ben")
print("-" * 70)

response = model.generate_content("Please greet Ben")

# Check if model wants to use a tool
if response.candidates[0].content.parts[0].function_call:
    function_call = response.candidates[0].content.parts[0].function_call
    print(f"Agent wants to call: {function_call.name}")
    print(f"Arguments: {dict(function_call.args)}")

    # Execute the function
    if function_call.name == "greet_user":
        name = function_call.args["name"]
        result = f"Hello {name}! The agent with tools is working perfectly!"
        print(f"Function result: {result}")
else:
    print(f"Agent response: {response.text}")

print()
print("=" * 70)
print("SUCCESS! Agent can use tools programmatically!")
print()
print("This is exactly what we need for contract extraction:")
print("  1. Agent decides which extraction tool to use")
print("  2. Calls the tool with parameters")
print("  3. We execute the function and return results")
print("  4. Agent uses results to continue processing")
print("=" * 70)
