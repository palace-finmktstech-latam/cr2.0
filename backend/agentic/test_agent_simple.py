#!/usr/bin/env python3
"""
Simple direct test of the Gemini agent
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = "us-central1"

vertexai.init(project=project_id, location=location)

print("=" * 70)
print("SIMPLE GEMINI TEST (bypassing ADK)")
print("=" * 70)
print()

# Test Gemini directly
model = GenerativeModel("gemini-2.0-flash-exp")

test_prompt = "Say 'Hello Ben! The agent is working!'"
print(f"User: {test_prompt}")
print()

response = model.generate_content(test_prompt)

print(f"Gemini: {response.text}")
print()
print("=" * 70)
print("SUCCESS - Gemini is responding!")
print()
print("This means:")
print("  1. Vertex AI connection works")
print("  2. Gemini model works")
print("  3. The issue is with ADK agent communication")
print()
print("Let's check if adk web is running correctly.")
print("In the browser, check the developer console (F12) for errors.")
print("=" * 70)
