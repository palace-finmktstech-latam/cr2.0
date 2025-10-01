#!/usr/bin/env python3
"""
Test script to verify Gemini access on Vertex AI.

This tests the same architecture as Claude, but uses Gemini models
which have quota by default.

Once Claude quota is approved, we can switch back with minimal changes.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

print("=" * 70)
print("VERTEX AI + GEMINI ACCESS TEST")
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
    from vertexai.generative_models import GenerativeModel

    vertexai.init(project=project_id, location="us-central1")  # Gemini works better in us-central1
    print("  [OK] Vertex AI initialized")
except Exception as e:
    print(f"  [ERROR] Failed to initialize Vertex AI: {e}")
    sys.exit(1)
print()

# Step 4: Test Gemini model access
print("[4/4] Testing Gemini 2.0 Flash access...")
print("  Model: gemini-2.0-flash-exp")
print("  Sending test query to Gemini...")
print()

try:
    # Initialize Gemini model
    model = GenerativeModel("gemini-2.0-flash-exp")

    # Make a simple test query
    response = model.generate_content(
        "Reply with exactly: 'Vertex AI + Gemini integration is working!'"
    )

    # Extract response text
    response_text = response.text

    print("  " + "-" * 66)
    print(f"  Gemini's response: {response_text}")
    print("  " + "-" * 66)
    print()
    print("  [OK] Gemini 2.0 Flash access working!")
    print()

except Exception as e:
    error_msg = str(e)
    print(f"  [ERROR] Failed to access Gemini: {error_msg}")
    print()

    # Provide helpful troubleshooting tips
    if "403" in error_msg or "permission" in error_msg.lower():
        print("  Possible fixes:")
        print("  1. Ensure Vertex AI API is enabled")
        print("  2. Check you have Vertex AI User role")
    elif "404" in error_msg:
        print("  Possible fixes:")
        print("  1. Try changing location to: us-central1")
    elif "quota" in error_msg.lower() or "429" in error_msg:
        print("  Possible fixes:")
        print("  1. Gemini should have default quota")
        print("  2. Check: https://console.cloud.google.com/iam-admin/quotas")

    sys.exit(1)

# Success!
print("=" * 70)
print("[SUCCESS] All tests passed!")
print()
print("Gemini is working - we can use this while waiting for Claude quota.")
print("=" * 70)
print()
print("Next steps:")
print("  1. Build Hello World ADK agent with Gemini")
print("  2. Test with 'adk web' visual UI")
print("  3. Switch to Claude once quota is approved (minimal code change)")
print()
