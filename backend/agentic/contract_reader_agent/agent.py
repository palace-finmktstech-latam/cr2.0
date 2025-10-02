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

# Session variable to store leg identifiers from Core Values extraction
# Used to ensure subsequent extractions assign data to correct legs
_session_leg_identifiers = None

# Session variables to store extraction results
# This avoids passing large JSON strings as parameters which causes escaping issues
_session_merged_contract = None  # Stores the accumulating merged contract data


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


def extract_leg_identifiers(core_values_json_str: str) -> list:
    """
    Extract leg identifier information from Core Values JSON for use in subsequent extractions.

    Args:
        core_values_json_str: JSON string from Core Values extraction

    Returns:
        List of dicts containing leg identifier information, or empty list on error
    """
    try:
        data = json.loads(core_values_json_str)
        legs = data.get("legs", [])

        identifiers = []
        for leg in legs:
            identifiers.append({
                "legId": leg.get("legId"),
                "notionalCurrency": leg.get("notionalCurrency"),
                "settlementCurrency": leg.get("settlementCurrency"),
                "rateType": leg.get("rateType"),
                "payerPartyReference": leg.get("payerPartyReference"),
                "receiverPartyReference": leg.get("receiverPartyReference")
            })

        return identifiers
    except Exception as e:
        print(f"WARNING: Could not extract leg identifiers: {e}")
        return []


def _deep_merge(base: dict, overlay: dict) -> dict:
    """
    Recursively merge overlay into base.
    - For dicts: merge keys recursively
    - For lists: merge by index (zip and merge each element)
    - For other types: overlay wins
    """
    result = base.copy()

    for key, overlay_value in overlay.items():
        if key not in result:
            # New key, just add it
            result[key] = overlay_value
        else:
            base_value = result[key]

            # Both are dicts - merge recursively
            if isinstance(base_value, dict) and isinstance(overlay_value, dict):
                result[key] = _deep_merge(base_value, overlay_value)

            # Both are lists - merge by index
            elif isinstance(base_value, list) and isinstance(overlay_value, list):
                merged_list = []
                # Merge matching indices
                for i in range(max(len(base_value), len(overlay_value))):
                    if i < len(base_value) and i < len(overlay_value):
                        # Both have element at this index
                        base_elem = base_value[i]
                        overlay_elem = overlay_value[i]

                        if isinstance(base_elem, dict) and isinstance(overlay_elem, dict):
                            # Merge dict elements
                            merged_list.append(_deep_merge(base_elem, overlay_elem))
                        else:
                            # Overlay wins
                            merged_list.append(overlay_elem)
                    elif i < len(base_value):
                        # Only base has this element
                        merged_list.append(base_value[i])
                    else:
                        # Only overlay has this element
                        merged_list.append(overlay_value[i])

                result[key] = merged_list

            # Different types or simple values - overlay wins
            else:
                result[key] = overlay_value

    return result


def write_output_json(filename: str) -> str:
    """
    Writes the merged contract JSON from session to the output directory.

    Args:
        filename: Name of the output file (e.g., "contract001.json")

    Returns:
        Success message with full path, or error message if write fails
    """
    global _session_merged_contract

    if _session_merged_contract is None:
        return "ERROR: No contract data in session. Please run extractions first."

    try:
        # Construct output path
        output_dir = BACKEND_DIR / "output"
        output_path = output_dir / filename

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write formatted JSON to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(_session_merged_contract, f, indent=2, ensure_ascii=False)

        return f"SUCCESS: JSON written to {output_path}"

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
    global _contract_cache, _session_contract_text, _session_leg_identifiers  # Declare at function start

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

        # Helper function to create cache (contract only, no system instruction)
        def create_cache():
            contents = [
                Content(
                    role="user",
                    parts=[
                        Part.from_text(text=f"Contract to analyze:\n\n{contract_text}")
                    ]
                )
            ]

            cache = genai_client.caches.create(
                model="gemini-2.5-pro",
                config=CreateCachedContentConfig(
                    contents=contents,
                    # NO system_instruction here - we'll pass it per request
                    display_name="contract-extraction-cache",
                    ttl="300s",  # 5 minutes
                ),
            )
            print(f"Cache created: {cache.name}")
            print(f"Cached tokens: {cache.usage_metadata.total_token_count}")
            return cache

        # Create or reuse context cache
        if _contract_cache is None:
            print("Creating new context cache for contract...")
            _contract_cache = create_cache()
        else:
            print(f"Attempting to reuse cache: {_contract_cache.name}")

        # Make extraction request using the cache with system instruction passed per request
        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part.from_text(text=system_instruction),  # Pass prompt as part of request
                            Part.from_text(
                                text="\n\nPlease extract the core contract values according to the instructions above. "
                                     "Return only the PRIMARY JSON (not the secondary evidence JSON)."
                            )
                        ]
                    )
                ],
                config={
                    "cached_content": _contract_cache.name,
                    "temperature": 0,
                }
            )
        except Exception as cache_error:
            # If cache is expired or invalid, create a new one and retry
            error_msg = str(cache_error).lower()
            if "expired" in error_msg or "not found" in error_msg or "invalid" in error_msg:
                print(f"Cache expired/invalid, creating fresh cache...")
                _contract_cache = create_cache()

                # Retry with new cache
                response = genai_client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[
                        Content(
                            role="user",
                            parts=[
                                Part.from_text(text=system_instruction),
                                Part.from_text(
                                    text="\n\nPlease extract the core contract values according to the instructions above. "
                                         "Return only the PRIMARY JSON (not the secondary evidence JSON)."
                                )
                            ]
                        )
                    ],
                    config={
                        "cached_content": _contract_cache.name,
                        "temperature": 0,
                    }
                )
            else:
                # Re-raise if it's a different error
                raise

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

            # Store leg identifiers in session for use by subsequent extractions
            _session_leg_identifiers = extract_leg_identifiers(extracted_text)

            # Store extraction result in session (first extraction, no merge needed)
            global _session_merged_contract
            _session_merged_contract = parsed_json

            # Return success message instead of JSON
            return f"SUCCESS: Core values extracted and stored in session. Ready for next extraction."

        except json.JSONDecodeError as e:
            return f"ERROR: AI returned invalid JSON - {str(e)}\n\nRaw response:\n{extracted_text}"

    except Exception as e:
        # Reset cache on error so next attempt will create fresh cache
        _contract_cache = None
        return f"ERROR during extraction: {str(e)}\n\nCache has been reset. Please try again."


def extract_business_day_conventions() -> str:
    """
    Extracts business day conventions and business centers from the contract loaded in session.

    Uses the promptHeaderBusinessDayConventions.txt extraction instructions and reuses
    the same context cache created by extract_core_values() for cost savings.

    IMPORTANT: Must call read_contract_file() first to load contract into session.

    Returns:
        JSON string with extracted business day conventions, or error message if extraction fails
    """
    global _contract_cache, _session_contract_text  # Declare at function start

    # Check if contract is loaded in session
    if _session_contract_text is None:
        return "ERROR: No contract loaded in session. Please call read_contract_file() first."

    contract_text = _session_contract_text

    try:
        # Read the extraction prompt template
        prompt_path = BACKEND_DIR / "prompts" / "promptHeaderBusinessDayConventions.txt"

        if not prompt_path.exists():
            return f"ERROR: Business Day Conventions prompt not found at {prompt_path}"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        # Replace {contract_text} placeholder with actual contract
        system_instruction = prompt_template.replace("{contract_text}", "").strip()

        # Inject leg context from Core Values extraction if available
        global _session_leg_identifiers
        if _session_leg_identifiers:
            leg_context = "\n\n## KNOWN LEG INFORMATION FROM CORE VALUES EXTRACTION:\n\n"
            for i, leg_id in enumerate(_session_leg_identifiers):
                leg_context += f"**Leg {i+1}:**\n"
                leg_context += f"- legId: {leg_id.get('legId')}\n"
                leg_context += f"- Notional Currency: {leg_id.get('notionalCurrency')}\n"
                leg_context += f"- Settlement Currency: {leg_id.get('settlementCurrency')}\n"
                leg_context += f"- Rate Type: {leg_id.get('rateType')}\n"
                leg_context += f"- Payer: {leg_id.get('payerPartyReference')}\n"
                leg_context += f"- Receiver: {leg_id.get('receiverPartyReference')}\n\n"

            leg_context += "**CRITICAL**: Order your output legs to match this exact sequence.\n"
            system_instruction = leg_context + system_instruction

        # Helper function to create cache (contract only, no system instruction)
        def create_cache():
            contents = [
                Content(
                    role="user",
                    parts=[
                        Part.from_text(text=f"Contract to analyze:\n\n{contract_text}")
                    ]
                )
            ]

            cache = genai_client.caches.create(
                model="gemini-2.5-pro",
                config=CreateCachedContentConfig(
                    contents=contents,
                    # NO system_instruction here - we'll pass it per request
                    display_name="contract-extraction-cache",
                    ttl="300s",  # 5 minutes
                ),
            )
            print(f"Cache created: {cache.name}")
            print(f"Cached tokens: {cache.usage_metadata.total_token_count}")
            return cache

        # Create or reuse context cache
        if _contract_cache is None:
            print("Creating new context cache for contract...")
            _contract_cache = create_cache()
        else:
            print(f"Attempting to reuse cache: {_contract_cache.name}")

        # Make extraction request using the cache with system instruction passed per request
        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part.from_text(text=system_instruction),  # Pass prompt as part of request
                            Part.from_text(
                                text="\n\nPlease extract the business day conventions and business centers "
                                     "according to the instructions above. Return only the PRIMARY JSON "
                                     "(not the secondary evidence JSON)."
                            )
                        ]
                    )
                ],
                config={
                    "cached_content": _contract_cache.name,
                    "temperature": 0,
                }
            )
        except Exception as cache_error:
            # If cache is expired or invalid, create a new one and retry
            error_msg = str(cache_error).lower()
            if "expired" in error_msg or "not found" in error_msg or "invalid" in error_msg:
                print(f"Cache expired/invalid, creating fresh cache...")
                _contract_cache = create_cache()

                # Retry with new cache
                response = genai_client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[
                        Content(
                            role="user",
                            parts=[
                                Part.from_text(text=system_instruction),
                                Part.from_text(
                                    text="\n\nPlease extract the business day conventions and business centers "
                                         "according to the instructions above. Return only the PRIMARY JSON "
                                         "(not the secondary evidence JSON)."
                                )
                            ]
                        )
                    ],
                    config={
                        "cached_content": _contract_cache.name,
                        "temperature": 0,
                    }
                )
            else:
                # Re-raise if it's a different error
                raise

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

            # Merge with existing session data
            global _session_merged_contract
            if _session_merged_contract is None:
                _session_merged_contract = parsed_json
            else:
                _session_merged_contract = _deep_merge(_session_merged_contract, parsed_json)

            # Return success message instead of JSON
            return f"SUCCESS: Business day conventions extracted and merged into session. Ready for next extraction."

        except json.JSONDecodeError as e:
            return f"ERROR: AI returned invalid JSON - {str(e)}\n\nRaw response:\n{extracted_text}"

    except Exception as e:
        # Reset cache on error so next attempt will create fresh cache
        _contract_cache = None
        return f"ERROR during extraction: {str(e)}\n\nCache has been reset. Please try again."


def extract_period_payment_data() -> str:
    """
    Extracts period end dates and payment dates business day conventions and frequencies.

    Uses the promptPeriodEndAndPaymentBusinessDayConventions.txt extraction instructions
    and reuses the same context cache for cost savings.

    IMPORTANT: Must call read_contract_file() first to load contract into session.

    Returns:
        JSON string with period/payment conventions and frequencies, or error message
    """
    global _contract_cache, _session_contract_text

    if _session_contract_text is None:
        return "ERROR: No contract loaded in session. Please call read_contract_file() first."

    contract_text = _session_contract_text

    try:
        prompt_path = BACKEND_DIR / "prompts" / "promptPeriodEndAndPaymentBusinessDayConventions.txt"

        if not prompt_path.exists():
            return f"ERROR: Period/Payment prompt not found at {prompt_path}"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        system_instruction = prompt_template.replace("{contract_text}", "").strip()

        # Inject leg context from Core Values extraction if available
        global _session_leg_identifiers
        if _session_leg_identifiers:
            leg_context = "\n\n## KNOWN LEG INFORMATION FROM CORE VALUES EXTRACTION:\n\n"
            for i, leg_id in enumerate(_session_leg_identifiers):
                leg_context += f"**Leg {i+1}:**\n"
                leg_context += f"- legId: {leg_id.get('legId')}\n"
                leg_context += f"- Notional Currency: {leg_id.get('notionalCurrency')}\n"
                leg_context += f"- Settlement Currency: {leg_id.get('settlementCurrency')}\n"
                leg_context += f"- Rate Type: {leg_id.get('rateType')}\n"
                leg_context += f"- Payer: {leg_id.get('payerPartyReference')}\n"
                leg_context += f"- Receiver: {leg_id.get('receiverPartyReference')}\n\n"

            leg_context += "**CRITICAL**: Order your output legs to match this exact sequence.\n"
            system_instruction = leg_context + system_instruction

        def create_cache():
            contents = [
                Content(
                    role="user",
                    parts=[Part.from_text(text=f"Contract to analyze:\n\n{contract_text}")]
                )
            ]
            cache = genai_client.caches.create(
                model="gemini-2.5-pro",
                config=CreateCachedContentConfig(
                    contents=contents,
                    display_name="contract-extraction-cache",
                    ttl="300s",
                ),
            )
            print(f"Cache created: {cache.name}")
            print(f"Cached tokens: {cache.usage_metadata.total_token_count}")
            return cache

        if _contract_cache is None:
            print("Creating new context cache for contract...")
            _contract_cache = create_cache()
        else:
            print(f"Attempting to reuse cache: {_contract_cache.name}")

        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part.from_text(text=system_instruction),
                            Part.from_text(
                                text="\n\nPlease extract the period end dates and payment dates conventions and frequencies "
                                     "according to the instructions above. Return only the PRIMARY JSON."
                            )
                        ]
                    )
                ],
                config={
                    "cached_content": _contract_cache.name,
                    "temperature": 0,
                }
            )
        except Exception as cache_error:
            error_msg = str(cache_error).lower()
            if "expired" in error_msg or "not found" in error_msg or "invalid" in error_msg:
                print(f"Cache expired/invalid, creating fresh cache...")
                _contract_cache = create_cache()

                response = genai_client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[
                        Content(
                            role="user",
                            parts=[
                                Part.from_text(text=system_instruction),
                                Part.from_text(
                                    text="\n\nPlease extract the period end dates and payment dates conventions and frequencies "
                                         "according to the instructions above. Return only the PRIMARY JSON."
                                )
                            ]
                        )
                    ],
                    config={
                        "cached_content": _contract_cache.name,
                        "temperature": 0,
                    }
                )
            else:
                raise

        extracted_text = response.text.strip()

        try:
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
            elif extracted_text.startswith("```"):
                extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

            parsed_json = json.loads(extracted_text)

            # Merge with existing session data
            global _session_merged_contract
            if _session_merged_contract is None:
                _session_merged_contract = parsed_json
            else:
                _session_merged_contract = _deep_merge(_session_merged_contract, parsed_json)

            # Return success message instead of JSON
            return f"SUCCESS: Period/payment data extracted and merged into session. Ready for next extraction."

        except json.JSONDecodeError as e:
            return f"ERROR: AI returned invalid JSON - {str(e)}\n\nRaw response:\n{extracted_text}"

    except Exception as e:
        _contract_cache = None
        return f"ERROR during extraction: {str(e)}\n\nCache has been reset. Please try again."


def extract_fx_fixing() -> str:
    """
    Extracts FX fixing data for legs that settle in a different currency.

    Uses the promptFXFixingData.txt extraction instructions and reuses
    the same context cache for cost savings.

    IMPORTANT: Must call read_contract_file() first to load contract into session.

    Returns:
        JSON string with FX fixing data, or error message if extraction fails
    """
    global _contract_cache, _session_contract_text

    if _session_contract_text is None:
        return "ERROR: No contract loaded in session. Please call read_contract_file() first."

    contract_text = _session_contract_text

    try:
        prompt_path = BACKEND_DIR / "prompts" / "promptFXFixingData.txt"

        if not prompt_path.exists():
            return f"ERROR: FX Fixing prompt not found at {prompt_path}"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        system_instruction = prompt_template.replace("{contract_text}", "").strip()

        # Inject leg context from Core Values extraction if available
        global _session_leg_identifiers
        if _session_leg_identifiers:
            leg_context = "\n\n## KNOWN LEG INFORMATION FROM CORE VALUES EXTRACTION:\n\n"
            for i, leg_id in enumerate(_session_leg_identifiers):
                leg_context += f"**Leg {i+1}:**\n"
                leg_context += f"- legId: {leg_id.get('legId')}\n"
                leg_context += f"- Notional Currency: {leg_id.get('notionalCurrency')}\n"
                leg_context += f"- Settlement Currency: {leg_id.get('settlementCurrency')}\n"
                leg_context += f"- Rate Type: {leg_id.get('rateType')}\n"
                leg_context += f"- Payer: {leg_id.get('payerPartyReference')}\n"
                leg_context += f"- Receiver: {leg_id.get('receiverPartyReference')}\n\n"

            leg_context += "**CRITICAL**: Order your output legs to match this exact sequence.\n"
            system_instruction = leg_context + system_instruction

        def create_cache():
            contents = [
                Content(
                    role="user",
                    parts=[Part.from_text(text=f"Contract to analyze:\n\n{contract_text}")]
                )
            ]
            cache = genai_client.caches.create(
                model="gemini-2.5-pro",
                config=CreateCachedContentConfig(
                    contents=contents,
                    display_name="contract-extraction-cache",
                    ttl="300s",
                ),
            )
            print(f"Cache created: {cache.name}")
            print(f"Cached tokens: {cache.usage_metadata.total_token_count}")
            return cache

        if _contract_cache is None:
            print("Creating new context cache for contract...")
            _contract_cache = create_cache()
        else:
            print(f"Attempting to reuse cache: {_contract_cache.name}")

        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part.from_text(text=system_instruction),
                            Part.from_text(
                                text="\n\nPlease extract the FX fixing data "
                                     "according to the instructions above. Return only the PRIMARY JSON."
                            )
                        ]
                    )
                ],
                config={
                    "cached_content": _contract_cache.name,
                    "temperature": 0,
                }
            )
        except Exception as cache_error:
            error_msg = str(cache_error).lower()
            if "expired" in error_msg or "not found" in error_msg or "invalid" in error_msg:
                print(f"Cache expired/invalid, creating fresh cache...")
                _contract_cache = create_cache()

                response = genai_client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[
                        Content(
                            role="user",
                            parts=[
                                Part.from_text(text=system_instruction),
                                Part.from_text(
                                    text="\n\nPlease extract the FX fixing data "
                                         "according to the instructions above. Return only the PRIMARY JSON."
                                )
                            ]
                        )
                    ],
                    config={
                        "cached_content": _contract_cache.name,
                        "temperature": 0,
                    }
                )
            else:
                raise

        extracted_text = response.text.strip()

        try:
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
            elif extracted_text.startswith("```"):
                extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

            parsed_json = json.loads(extracted_text)

            # Merge with existing session data
            global _session_merged_contract
            if _session_merged_contract is None:
                _session_merged_contract = parsed_json
            else:
                _session_merged_contract = _deep_merge(_session_merged_contract, parsed_json)

            # Return success message instead of JSON
            return f"SUCCESS: FX fixing data extracted and merged into session. Ready to write output."

        except json.JSONDecodeError as e:
            return f"ERROR: AI returned invalid JSON - {str(e)}\n\nRaw response:\n{extracted_text}"

    except Exception as e:
        _contract_cache = None
        return f"ERROR during extraction: {str(e)}\n\nCache has been reset. Please try again."


def extract_payment_date_offset() -> str:
    """
    Extracts payment date offset (days between period end and payment date) for each leg.

    Uses the promptPaymentDateOffset.txt extraction instructions and reuses
    the same context cache for cost savings.

    IMPORTANT: Must call read_contract_file() first to load contract into session.

    Returns:
        Success message indicating extraction completed and merged into session
    """
    global _contract_cache, _session_contract_text

    if _session_contract_text is None:
        return "ERROR: No contract loaded in session. Please call read_contract_file() first."

    contract_text = _session_contract_text

    try:
        prompt_path = BACKEND_DIR / "prompts" / "promptPaymentDateOffset.txt"

        if not prompt_path.exists():
            return f"ERROR: Payment Date Offset prompt not found at {prompt_path}"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        system_instruction = prompt_template.replace("{contract_text}", "").strip()

        # Inject leg context from Core Values extraction if available
        global _session_leg_identifiers
        if _session_leg_identifiers:
            leg_context = "\n\n## KNOWN LEG INFORMATION FROM CORE VALUES EXTRACTION:\n\n"
            for i, leg_id in enumerate(_session_leg_identifiers):
                leg_context += f"**Leg {i+1}:**\n"
                leg_context += f"- legId: {leg_id.get('legId')}\n"
                leg_context += f"- Notional Currency: {leg_id.get('notionalCurrency')}\n"
                leg_context += f"- Settlement Currency: {leg_id.get('settlementCurrency')}\n"
                leg_context += f"- Rate Type: {leg_id.get('rateType')}\n"
                leg_context += f"- Payer: {leg_id.get('payerPartyReference')}\n"
                leg_context += f"- Receiver: {leg_id.get('receiverPartyReference')}\n\n"

            leg_context += "**CRITICAL**: Order your output legs to match this exact sequence.\n"
            system_instruction = leg_context + system_instruction

        def create_cache():
            contents = [
                Content(
                    role="user",
                    parts=[Part.from_text(text=f"Contract to analyze:\n\n{contract_text}")]
                )
            ]

            cache = genai_client.caches.create(
                model="gemini-2.5-pro",
                config=CreateCachedContentConfig(
                    contents=contents,
                    display_name="contract-extraction-cache",
                    ttl="300s",
                ),
            )
            print(f"Cache created: {cache.name}")
            print(f"Cached tokens: {cache.usage_metadata.total_token_count}")
            return cache

        if _contract_cache is None:
            print("Creating new context cache for contract...")
            _contract_cache = create_cache()
        else:
            print(f"Attempting to reuse cache: {_contract_cache.name}")

        try:
            response = genai_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    Content(
                        role="user",
                        parts=[
                            Part.from_text(text=system_instruction),
                            Part.from_text(
                                text="\n\nPlease extract the payment date offset data according to the instructions above. "
                                     "Return only the PRIMARY JSON."
                            )
                        ]
                    )
                ],
                config={
                    "cached_content": _contract_cache.name,
                    "temperature": 0,
                }
            )
        except Exception as cache_error:
            error_msg = str(cache_error).lower()
            if "expired" in error_msg or "not found" in error_msg or "invalid" in error_msg:
                print(f"Cache expired/invalid, creating fresh cache...")
                _contract_cache = create_cache()

                response = genai_client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[
                        Content(
                            role="user",
                            parts=[
                                Part.from_text(text=system_instruction),
                                Part.from_text(
                                    text="\n\nPlease extract the payment date offset data according to the instructions above. "
                                         "Return only the PRIMARY JSON."
                                )
                            ]
                        )
                    ],
                    config={
                        "cached_content": _contract_cache.name,
                        "temperature": 0,
                    }
                )
            else:
                raise

        extracted_text = response.text.strip()

        try:
            if extracted_text.startswith("```json"):
                extracted_text = extracted_text.split("```json")[1].split("```")[0].strip()
            elif extracted_text.startswith("```"):
                extracted_text = extracted_text.split("```")[1].split("```")[0].strip()

            parsed_json = json.loads(extracted_text)

            # Merge with existing session data
            global _session_merged_contract
            if _session_merged_contract is None:
                _session_merged_contract = parsed_json
            else:
                _session_merged_contract = _deep_merge(_session_merged_contract, parsed_json)

            # Return success message instead of JSON
            return f"SUCCESS: Payment date offset extracted and merged into session. Ready to write output."

        except json.JSONDecodeError as e:
            return f"ERROR: AI returned invalid JSON - {str(e)}\n\nRaw response:\n{extracted_text}"

    except Exception as e:
        _contract_cache = None
        return f"ERROR during extraction: {str(e)}\n\nCache has been reset. Please try again."


# ==================== SESSION MANAGEMENT ====================

def clear_session() -> str:
    """
    Clears all session data including contract text, cache, leg identifiers, and extracted data.

    Use this BEFORE starting work on a new contract to avoid cache confusion and ensure
    clean state. This prevents the AI from mixing data from different contracts.

    Returns:
        Success message confirming session has been cleared
    """
    global _contract_cache, _session_contract_text, _session_leg_identifiers, _session_merged_contract

    # Clear the contract cache
    if _contract_cache is not None:
        try:
            # Delete the cache from Gemini API
            genai_client.caches.delete(name=_contract_cache.name)
            print(f"Cache deleted: {_contract_cache.name}")
        except Exception as e:
            print(f"Note: Could not delete cache (may already be expired): {e}")

    _contract_cache = None
    _session_contract_text = None
    _session_leg_identifiers = None
    _session_merged_contract = None

    return "SUCCESS: Session cleared. All contract data, cache, and extracted results removed. Ready for new contract."


def get_session_status() -> str:
    """
    Returns the current status of the session including what's loaded and extracted.

    Returns:
        Status message describing session state
    """
    global _session_contract_text, _session_merged_contract, _session_leg_identifiers

    status = "SESSION STATUS:\n\n"

    # Contract loaded?
    if _session_contract_text:
        status += f"✓ Contract loaded ({len(_session_contract_text)} characters)\n"
    else:
        status += "✗ No contract loaded\n"

    # Leg identifiers extracted?
    if _session_leg_identifiers:
        status += f"✓ Leg identifiers extracted ({len(_session_leg_identifiers)} legs)\n"
    else:
        status += "✗ No leg identifiers\n"

    # Merged contract data?
    if _session_merged_contract:
        json_str = json.dumps(_session_merged_contract, indent=2, ensure_ascii=False)
        status += f"✓ Contract data in session ({len(json_str)} characters)\n"
        status += f"  Data ready to write to file\n"
    else:
        status += "✗ No extracted contract data\n"

    return status


def query_contract_data(question: str) -> str:
    """
    Answers questions about the contract or extracted data using AI.

    This tool allows you to ask questions about:
    - The original contract text
    - The extracted and merged contract data
    - Comparisons or analysis of specific fields
    - Validation or verification of extracted values

    Args:
        question: Natural language question about the contract or extracted data

    Returns:
        AI-generated answer based on available contract data

    Examples:
        - "What is the fixed rate on the CLF leg?"
        - "Which party pays the floating leg?"
        - "What business day conventions are used for payment dates?"
        - "Show me the FX fixing data for both legs"
    """
    global _session_contract_text, _session_merged_contract

    if _session_contract_text is None and _session_merged_contract is None:
        return "ERROR: No contract data available in session. Please load a contract first."

    try:
        # Build context from available session data
        context_parts = []

        if _session_contract_text:
            context_parts.append(f"ORIGINAL CONTRACT TEXT:\n{_session_contract_text}")

        if _session_merged_contract:
            json_str = json.dumps(_session_merged_contract, indent=2, ensure_ascii=False)
            context_parts.append(f"\nEXTRACTED CONTRACT DATA (JSON):\n{json_str}")

        full_context = "\n\n".join(context_parts)

        # Use Gemini to answer the question
        response = genai_client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                Content(
                    role="user",
                    parts=[
                        Part.from_text(
                            text=f"{full_context}\n\n"
                                 f"USER QUESTION: {question}\n\n"
                                 f"Please answer the question based on the contract text and/or extracted data above. "
                                 f"Be concise and specific. If the answer is in the extracted JSON, reference the field names."
                        )
                    ]
                )
            ],
            config={
                "temperature": 0,
            }
        )

        return response.text.strip()

    except Exception as e:
        return f"ERROR answering question: {str(e)}"


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
        "All extraction data is stored in session to avoid JSON parameter passing issues. "
        "\n\n"
        "# Available Tools:\n\n"
        "**Session Management:**\n"
        "- clear_session(): Clears all session data - USE THIS BEFORE NEW CONTRACT!\n"
        "- read_contract_file(path): Loads contract into session\n"
        "- get_session_status(): Shows what's currently loaded in session\n"
        "- write_output_json(filename): Writes merged session data to file\n"
        "- query_contract_data(question): Ask questions about contract or extracted data\n"
        "\n"
        "**Extraction Tools (auto-merge into session):**\n"
        "- extract_core_values(): Extracts core data, stores in session\n"
        "- extract_business_day_conventions(): Extracts & merges into session\n"
        "- extract_period_payment_data(): Extracts & merges into session\n"
        "- extract_fx_fixing(): Extracts & merges into session\n"
        "- extract_payment_date_offset(): Extracts payment offset & merges into session\n"
        "\n"
        "All extractions automatically merge into session. No manual merging needed!\n"
        "\n"
        "**Test Tools:**\n"
        "- greet_user(name): Test greeting\n"
        "- calculate_sum(a, b): Test math\n"
        "\n\n"
        "# Workflow:\n\n"
        "**Complete Extraction (NEW CONTRACT):**\n"
        "CRITICAL: Call ONE tool at a time. Wait for response before calling next tool.\n"
        "DO NOT batch multiple tool calls together. Each step depends on previous step.\n\n"
        "Step-by-step process:\n"
        "1. clear_session() → wait for response\n"
        "2. read_contract_file('prompts/contract.txt') → wait for response\n"
        "3. extract_core_values() → wait for response\n"
        "4. extract_business_day_conventions() → wait for response\n"
        "5. extract_period_payment_data() → wait for response\n"
        "6. extract_fx_fixing() → wait for response\n"
        "7. extract_payment_date_offset() → wait for response\n"
        "8. write_output_json('complete_contract.json') → wait for response\n"
        "\n"
        "**Follow-up questions about same contract:**\n"
        "- DO NOT clear session - data is already loaded\n"
        "- Use query_contract_data(question) to answer user questions\n"
        "- You can re-run specific extractions if needed\n"
        "\n"
        "Each extraction auto-merges into session.\n"
        "\n"
        "# Important:\n"
        "- NO parameters needed for write_output_json - it reads from session\n"
        "- Extractions return status messages, not JSON\n"
        "- Session storage avoids JSON escaping issues in tool calls"
    ),
    tools=[
        clear_session,
        read_contract_file,
        get_session_status,
        write_output_json,
        query_contract_data,
        extract_core_values,
        extract_business_day_conventions,
        extract_period_payment_data,
        extract_fx_fixing,
        extract_payment_date_offset,
        greet_user,
        calculate_sum
    ]
)

# Also export as 'agent' for backwards compatibility
agent = root_agent
