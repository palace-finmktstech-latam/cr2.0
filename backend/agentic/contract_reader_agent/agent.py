#!/usr/bin/env python3
"""
Contract Reader Agent - With Extraction and Context Caching

ADK Entry Point: This file is loaded by 'adk web' and 'adk run'
"""

import os
import json
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

# Import Google GenAI for context caching
from google import genai
from google.genai.types import Content, CreateCachedContentConfig, HttpOptions, Part

# Initialize GenAI client for caching
genai_client = genai.Client(
    vertexai=True,
    project=project_id,
    location=location,
    http_options=HttpOptions(api_version="v1")
)

# Get backend directory path
BACKEND_DIR = Path(__file__).parent.parent.parent

# Global variable to store cache between calls
_contract_cache = None

# Session variable to store contract text between tool calls
# This avoids passing large text strings as parameters which causes escaping issues
_session_contract_text = None


# ==================== FILE I/O TOOLS ====================

def read_contract_file(contract_path: str) -> str:
    """
    Reads a contract text file and stores it in session for use by extraction tools.

    Args:
        contract_path: Relative path to contract file from backend directory.
                      Examples: "prompts/contract.txt", "contracts/contract001.txt"

    Returns:
        Success message with character count. The actual contract text is stored
        in the session and available to extraction tools without passing as parameter.
    """
    global _session_contract_text

    try:
        # Construct full path relative to backend directory
        full_path = BACKEND_DIR / contract_path

        # Check if file exists
        if not full_path.exists():
            return f"ERROR: File not found at {full_path}"

        # Read file and store in session
        with open(full_path, 'r', encoding='utf-8') as f:
            _session_contract_text = f.read()

        return f"SUCCESS: Loaded contract with {len(_session_contract_text)} characters into session. Ready for extraction."

    except Exception as e:
        return f"ERROR reading file: {str(e)}"


def write_output_json(filename: str, json_data: str) -> str:
    """
    Writes JSON data to the output directory.

    Args:
        filename: Name of the output file (e.g., "contract001.json")
        json_data: JSON data as a string or valid JSON object

    Returns:
        Success message with full path, or error message if write fails
    """
    try:
        # Construct output path
        output_dir = BACKEND_DIR / "output"
        output_path = output_dir / filename

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Parse JSON if it's a string to validate and format it
        if isinstance(json_data, str):
            parsed_json = json.loads(json_data)
        else:
            parsed_json = json_data

        # Write formatted JSON to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)

        return f"SUCCESS: JSON written to {output_path}"

    except json.JSONDecodeError as e:
        return f"ERROR: Invalid JSON format - {str(e)}"
    except Exception as e:
        return f"ERROR writing file: {str(e)}"


# ==================== EXTRACTION TOOLS ====================

def extract_core_values() -> str:
    """
    Extracts core contract values from the contract loaded in session.

    Uses the promptCoreValues.txt extraction instructions and creates a context cache
    for cost savings (75% cheaper) on subsequent extractions.

    IMPORTANT: Must call read_contract_file() first to load contract into session.

    Returns:
        JSON string with extracted core values, or error message if extraction fails
    """
    global _contract_cache, _session_contract_text

    # Check if contract is loaded in session
    if _session_contract_text is None:
        return "ERROR: No contract loaded in session. Please call read_contract_file() first."

    contract_text = _session_contract_text

    try:
        # Read the extraction prompt template
        prompt_path = BACKEND_DIR / "prompts" / "promptCoreValues.txt"

        if not prompt_path.exists():
            return f"ERROR: Extraction prompt not found at {prompt_path}"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Replace {contract_text} placeholder with actual contract
        # The prompt template ends with "### Contract Text:\n\n{contract_text}"
        system_instruction = prompt_template.replace("{contract_text}", "").strip()

        # Create or reuse context cache
        if _contract_cache is None:
            print("Creating new context cache for contract...")

            # Create cache with contract text as cached content
            contents = [
                Content(
                    role="user",
                    parts=[
                        Part.from_text(text=f"Contract to analyze:\n\n{contract_text}")
                    ]
                )
            ]

            _contract_cache = genai_client.caches.create(
                model="gemini-2.0-flash-exp",
                config=CreateCachedContentConfig(
                    contents=contents,
                    system_instruction=system_instruction,
                    display_name="contract-extraction-cache",
                    ttl="300s",  # 5 minutes - perfect for multi-prompt workflow
                ),
            )

            print(f"Cache created: {_contract_cache.name}")
            print(f"Cached tokens: {_contract_cache.usage_metadata.total_token_count}")
        else:
            print(f"Reusing existing cache: {_contract_cache.name}")

        # Make extraction request using the cache
        response = genai_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=[
                Content(
                    role="user",
                    parts=[
                        Part.from_text(
                            text="Please extract the core contract values according to the instructions. "
                                 "Return only the PRIMARY JSON (not the secondary evidence JSON)."
                        )
                    ]
                )
            ],
            config={
                "cached_content": _contract_cache.name,
                "temperature": 0.1,  # Low temperature for consistent extractions
            }
        )

        # Extract JSON from response
        extracted_text = response.text.strip()

        # Try to parse as JSON to validate
        try:
            # Remove markdown code blocks if present
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
            elif extracted_text.startswith("```"):
                extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

            parsed_json = json.loads(extracted_text)

            # Return formatted JSON
            return json.dumps(parsed_json, indent=2, ensure_ascii=False)

        except json.JSONDecodeError as e:
            return f"ERROR: AI returned invalid JSON - {str(e)}\n\nRaw response:\n{extracted_text}"

    except Exception as e:
        return f"ERROR during extraction: {str(e)}"


# ==================== TEST TOOLS (from Hello World) ====================

def greet_user(name: str) -> str:
    """
    Greets a user by name with a friendly message.

    Args:
        name: The name of the person to greet

    Returns:
        A personalized greeting message
    """
    return f"Hello {name}! The ADK + Gemini agent is working perfectly!"


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
        "You are an AI assistant for Interest Rate Swap contract extraction. "
        "You have tools to read contracts, extract structured data, and write JSON outputs. "
        "\n\n"
        "# Available Tools:\n\n"
        "**File I/O:**\n"
        "- read_contract_file(path): Loads contract into session from prompts/ or contracts/\n"
        "  Returns success message with character count\n"
        "- write_output_json(filename, json_data): Writes JSON to output/ directory\n"
        "  Returns success message with file path\n"
        "\n"
        "**Extraction (with Context Caching):**\n"
        "- extract_core_values(): Extracts core contract data using AI from loaded session\n"
        "  IMPORTANT: Must call read_contract_file() first!\n"
        "  Returns JSON with: header (dates, parties, tradeId), legs (notional, rates, settlements)\n"
        "  Uses context caching for 75% cost savings\n"
        "\n"
        "**Test Tools:**\n"
        "- greet_user(name): Test greeting\n"
        "- calculate_sum(a, b): Test math\n"
        "\n\n"
        "# Workflow Pattern:\n\n"
        "User: 'Extract core values from prompts/contract.txt and save to output/contract.json'\n"
        "\n"
        "Your steps:\n"
        "1. Call read_contract_file('prompts/contract.txt')\n"
        "   → Loads contract into session (no need to pass text around)\n"
        "2. Call extract_core_values()\n"
        "   → Uses contract from session, returns JSON string\n"
        "3. Call write_output_json('contract.json', <json_from_step_2>)\n"
        "   → Saves the extracted JSON\n"
        "\n\n"
        "# Important Notes:\n"
        "- The session-based approach avoids passing large contract text between tools\n"
        "- Always read the contract first before extracting\n"
        "- The extraction tool handles all AI processing and caching automatically\n"
        "- Pass the JSON string from extract_core_values() directly to write_output_json()\n"
        "- Be helpful and concise in your responses"
    ),
    tools=[
        read_contract_file,
        write_output_json,
        extract_core_values,
        greet_user,
        calculate_sum
    ]
)

# Also export as 'agent' for backwards compatibility
agent = root_agent
