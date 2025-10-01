#!/usr/bin/env python3
"""
Test script to verify Claude access on Vertex AI.

This script tests:
1. Loading .env configuration
2. Authenticating with Google Cloud (using ADC)
3. Accessing Claude 3.5 Sonnet via Vertex AI
4. Making a simple test query

If this works, we know the full setup is correct.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

print("=" * 70)
print("VERTEX AI + CLAUDE ACCESS TEST")
print("=" * 70)
print()

# Step 1: Verify environment variables
print("[1/4] Checking environment variables...")
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION")

if not project_id:
    print("ERROR: GOOGLE_CLOUD_PROJECT not set in .env file")
    sys.exit(1)

if not location:
    print("ERROR: GOOGLE_CLOUD_LOCATION not set in .env file")
    sys.exit(1)

print(f"  Project ID: {project_id}")
print(f"  Location: {location}")
print("  [OK] Environment variables loaded")
print()

# Step 2: Test ADC authentication
print("[2/4] Testing Application Default Credentials (ADC)...")
try:
    from google.auth import default
    credentials, project = default()
    print(f"  Authenticated project: {project}")
    print("  [OK] ADC authentication working")
except Exception as e:
    print(f"  [ERROR] ADC authentication failed: {e}")
    print()
    print("  Fix: Run 'gcloud auth application-default login'")
    sys.exit(1)
print()

# Step 3: Initialize Vertex AI
print("[3/4] Initializing Vertex AI...")
try:
    import vertexai
    vertexai.init(project=project_id, location=location)
    print("  [OK] Vertex AI initialized")
except Exception as e:
    print(f"  [ERROR] Failed to initialize Vertex AI: {e}")
    sys.exit(1)
print()

# Step 4: Test Claude model access
print("[4/4] Testing Claude Sonnet 4.5 access...")
print("  Model: claude-sonnet-4-5@20250929")
print("  Sending test query to Claude...")
print()

try:
    from anthropic import AnthropicVertex

    # Initialize Anthropic Vertex client
    client = AnthropicVertex(
        region=location,
        project_id=project_id
    )

    # Make a simple test query
    # Using Claude Sonnet 4.5 - Latest GA version on Vertex AI
    response = client.messages.create(
        model="claude-sonnet-4-5@20250929",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: 'Vertex AI + Claude integration is working!'"
            }
        ]
    )

    # Extract response text
    response_text = response.content[0].text

    print("  " + "-" * 66)
    print(f"  Claude's response: {response_text}")
    print("  " + "-" * 66)
    print()
    print("  [OK] Claude Sonnet 4.5 access working!")
    print()

except ImportError as e:
    print(f"  [ERROR] Missing required package: {e}")
    print()
    print("  Fix: Run 'pip install anthropic[vertex]'")
    sys.exit(1)

except Exception as e:
    error_msg = str(e)
    print(f"  [ERROR] Failed to access Claude: {error_msg}")
    print()

    # Provide helpful troubleshooting tips
    if "403" in error_msg or "permission" in error_msg.lower():
        print("  Possible fixes:")
        print("  1. Ensure Claude models are enabled in your GCP project")
        print("  2. Check you have Vertex AI User role")
        print("  3. Visit: https://console.cloud.google.com/vertex-ai/publishers/anthropic")
    elif "404" in error_msg:
        print("  Possible fixes:")
        print("  1. Claude might not be available in your region")
        print("  2. Try changing GOOGLE_CLOUD_LOCATION to: us-east5 or us-central1")
    elif "billing" in error_msg.lower():
        print("  Possible fixes:")
        print("  1. Ensure billing is enabled for your GCP project")
        print("  2. Check: https://console.cloud.google.com/billing")

    sys.exit(1)

# Success!
print("=" * 70)
print("[SUCCESS] All tests passed!")
print()
print("Your setup is complete and ready for the ADK agent.")
print("=" * 70)
print()
print("Next steps:")
print("  1. We'll create the Hello World ADK agent")
print("  2. Test with 'adk web' visual UI")
print("  3. Build the contract extraction tools")
print()
