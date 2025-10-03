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

# Session variable to store the current contract filename (without extension)
_session_contract_name = None

# Session variable to store all completed contract extractions for consolidated output
_session_all_contracts = []  # List of all extracted contract JSONs

# Session variables for bank folder structure
_session_date_folder = None  # Path to current date folder being processed
_session_bank_name = None  # Bank name for current processing session


# ==================== FILE I/O TOOLS ====================

def run_mapping_program(date_str: str, bank_name: str) -> str:
    """
    Runs the mapping_program.py to convert bank CSV data to JSON format.

    This should be run FIRST before contract extraction, as it processes the bank's
    trade data CSV file and creates the banco JSON output.

    Args:
        date_str: Date in dd/mm/yyyy format (e.g., "25/09/2025")
        bank_name: Bank name with country code (e.g., "BancoInternacionalCL")

    Returns:
        Success message with output path, or error message
    """
    import subprocess
    from datetime import datetime

    try:
        # Parse date
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        date_folder_name = date_obj.strftime("%d%m%Y")

        # Store in session for later use
        global _session_date_folder, _session_bank_name
        base_path = Path(r"C:\Users\bencl\OneDrive - palace.cl\Documents\Palace\Ideas\Contract Extraction\v2.0\Servicio")
        _session_date_folder = base_path / bank_name / date_folder_name
        _session_bank_name = bank_name

        # Build mapping_program.py path
        mapping_script = BACKEND_DIR / "mapping_program.py"

        # Run mapping_program.py
        result = subprocess.run(
            ["python", str(mapping_script), date_str, bank_name],
            capture_output=True,
            text=True,
            timeout=120
        )

        # Check for success indicators in output (look in both stdout and stderr)
        combined_output = result.stdout + result.stderr
        success_indicators = ["Transformation completed successfully", "Output written to", "✓ Transformation completed"]
        error_indicators = ["ERROR:", "Error:", "Traceback", "Exception:", "FAILED"]

        has_success = any(indicator in combined_output for indicator in success_indicators)
        has_error = any(indicator in combined_output for indicator in error_indicators)

        # Check if output file was actually created
        output_file = _session_date_folder / f"{date_folder_name}_bancoabc_trades.json"
        file_created = output_file.exists()

        if result.returncode == 0 and (has_success or file_created):
            # Success! Even if there were warnings in stderr, the file was created
            msg = f"SUCCESS: Mapping completed. CSV transformed to JSON.\n"
            if file_created:
                msg += f"Output file created: {output_file.name}\n"
            msg += f"\nReady to process contract files."
            return msg
        elif has_error:
            return f"ERROR: Mapping encountered errors.\n\nOutput:\n{combined_output}"
        else:
            return f"UNCERTAIN: Mapping completed with return code {result.returncode}.\n\nOutput:\n{combined_output}"

    except Exception as e:
        return f"ERROR running mapping program: {str(e)}"

def read_contract_file(filename: str) -> str:
    """
    Reads a contract text file from the session date folder and stores it in session.

    Must be called AFTER run_mapping_program() which sets up the session folder paths.

    Args:
        filename: Just the filename (e.g., "contract_7559-61863_anon.txt")
                 File will be read from the session date folder.

    Returns:
        Success message with character count. The actual contract text is stored
        in the session and available to extraction tools without passing as parameter.
    """
    global _session_contract_text, _session_contract_name, _session_date_folder
    import os

    try:
        # Check session folder is set
        if _session_date_folder is None:
            return "ERROR: No date folder set in session. Call run_mapping_program() first."

        # Construct full path from session folder
        full_path = _session_date_folder / filename

        # Check if file exists
        if not full_path.exists():
            return f"ERROR: File not found: {full_path}"

        # Extract contract name from filename (without extension)
        _session_contract_name = os.path.splitext(filename)[0]

        # Read file and store in session
        with open(full_path, 'r', encoding='utf-8') as f:
            _session_contract_text = f.read()

        return f"SUCCESS: Loaded contract '{_session_contract_name}' with {len(_session_contract_text)} characters into session. Ready for extraction."

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


def save_contract_to_batch() -> str:
    """
    Saves the current contract from session to the batch collection for consolidated output.

    Call this after completing extraction and validation for each contract when processing
    multiple contracts. The contract will be added to the consolidated output file.

    Returns:
        Success message confirming contract was added to batch
    """
    global _session_merged_contract, _session_all_contracts, _session_contract_name

    if _session_merged_contract is None:
        return "ERROR: No contract data in session. Please run extractions first."

    # Add current contract to the batch
    _session_all_contracts.append(_session_merged_contract.copy())

    return f"SUCCESS: Contract '{_session_contract_name}' added to batch ({len(_session_all_contracts)} total contracts)"


def _remove_clear_fields(obj):
    """
    Recursively removes all fields ending with 'Clear' from a dictionary or list.

    Args:
        obj: Dictionary, list, or other object to clean

    Returns:
        Cleaned copy of the object
    """
    if isinstance(obj, dict):
        return {
            key: _remove_clear_fields(value)
            for key, value in obj.items()
            if not key.endswith('Clear')
        }
    elif isinstance(obj, list):
        return [_remove_clear_fields(item) for item in obj]
    else:
        return obj


def write_consolidated_output() -> str:
    """
    Writes all contracts from the batch to consolidated JSON files in the session date folder.

    Must be called AFTER run_mapping_program() which sets up the session folder paths.

    Creates TWO files in the date folder:
    1. Clean version: {date}_bancoabc_contracts.json - No *Clear fields (ready for downstream)
    2. Debug version: extraction_metadata/{date}_bancoabc_contracts.json - With *Clear fields

    Output filename always uses "bancoabc" (hardcoded for anonymization).
    Structure: { "trades": [ {...}, {...}, ... ] }

    Returns:
        Success message with file paths and contract count
    """
    global _session_all_contracts, _session_date_folder
    from datetime import datetime

    if not _session_all_contracts:
        return "ERROR: No contracts in batch. Process contracts and call save_contract_to_batch() first."

    if _session_date_folder is None:
        return "ERROR: No date folder set in session. Call run_mapping_program() first."

    try:
        # Extract date from folder name (last component of path)
        date_folder_name = _session_date_folder.name  # e.g., "25092025"

        # Construct filename (always use "bancoabc" for anonymization)
        filename = f"{date_folder_name}_bancoabc_contracts.json"

        # Create consolidated structure with all Clear fields (debug version)
        consolidated_debug = {
            "trades": _session_all_contracts
        }

        # Create clean version without Clear fields
        consolidated_clean = _remove_clear_fields(consolidated_debug)

        # Write debug version (with Clear fields) to extraction_metadata subfolder
        debug_dir = _session_date_folder / "extraction_metadata"
        debug_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_dir / filename

        with open(debug_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated_debug, f, indent=2, ensure_ascii=False)

        # Write clean version (without Clear fields) to date folder
        output_path = _session_date_folder / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated_clean, f, indent=2, ensure_ascii=False)

        return (f"SUCCESS: Consolidated output written:\n"
                f"  - Clean version: {output_path}\n"
                f"  - Debug version (with *Clear fields): {debug_path}\n"
                f"  - Total contracts: {len(_session_all_contracts)}")

    except Exception as e:
        return f"ERROR writing consolidated file: {str(e)}"


def write_output_json(filename: str) -> str:
    """
    Writes the merged contract JSON from session to the output directory as individual file.

    NOTE: For batch processing multiple contracts, use save_contract_to_batch() and
    write_consolidated_output() instead.

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

            # Inject contractName programmatically into header section
            global _session_contract_name
            if _session_contract_name:
                if "header" not in parsed_json:
                    parsed_json["header"] = {}
                parsed_json["header"]["contractName"] = _session_contract_name

            # Store leg identifiers in session for use by subsequent extractions
            _session_leg_identifiers = extract_leg_identifiers(json.dumps(parsed_json))

            # Store extraction result in session (first extraction, no merge needed)
            global _session_merged_contract
            _session_merged_contract = parsed_json

            # Return success message instead of JSON
            return f"SUCCESS: Core values extracted and stored in session (contractName: {_session_contract_name}). Ready for next extraction."

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
    global _contract_cache, _session_contract_text, _session_leg_identifiers, _session_merged_contract, _session_contract_name

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
    _session_contract_name = None

    return "SUCCESS: Session cleared. All contract data, cache, and extracted results removed. Ready for new contract."


def process_contract_folder(folder_path: str = "prompts") -> str:
    """
    Processes all .txt contract files in a folder, generating corresponding .json output files.

    For each contract file (e.g., 'gscontract.txt'), this function:
    1. Clears session
    2. Reads the contract
    3. Runs all 5 extractions
    4. Validates the extraction
    5. Writes output to same filename with .json extension (e.g., 'gscontract.json')

    Args:
        folder_path: Relative path to folder containing contract .txt files (default: "prompts")

    Returns:
        Summary report of all processed contracts with success/failure status
    """
    import os
    import glob

    # Build absolute path
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    contracts_dir = os.path.join(backend_dir, folder_path)

    # Find all .txt files
    pattern = os.path.join(contracts_dir, "*.txt")
    contract_files = glob.glob(pattern)

    # Filter out prompt files (keep only contract files)
    contract_files = [f for f in contract_files if not os.path.basename(f).startswith("prompt")]

    if not contract_files:
        return f"ERROR: No contract files found in {folder_path}/"

    results = []
    results.append(f"BATCH PROCESSING: Found {len(contract_files)} contract(s)\n")
    results.append("=" * 60)

    for contract_path in contract_files:
        filename = os.path.basename(contract_path)
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}.json"

        results.append(f"\n\n📄 Processing: {filename}")
        results.append("-" * 60)

        try:
            # 1. Clear session
            clear_session()

            # 2. Read contract
            relative_path = os.path.join(folder_path, filename)
            read_result = read_contract_file(relative_path)

            # 3. Extract core values
            extract_core_values()

            # 4. Extract business day conventions
            extract_business_day_conventions()

            # 5. Extract period/payment data
            extract_period_payment_data()

            # 6. Extract FX fixing
            extract_fx_fixing()

            # 7. Extract payment date offset
            extract_payment_date_offset()

            # 8. Validate
            validation_report = validate_extraction()

            # 9. Write output
            write_result = write_output_json(output_filename)

            results.append(f"✅ SUCCESS: {output_filename}")

            # Extract quality score from validation report
            quality_score = 'N/A'
            if 'Quality: ' in validation_report:
                quality_line = validation_report.split('Quality: ')[1].split('\n')[0]
                quality_score = quality_line
            results.append(f"   Validation: {quality_score}")

        except Exception as e:
            results.append(f"❌ FAILED: {filename}")
            results.append(f"   Error: {str(e)}")

    results.append("\n" + "=" * 60)
    results.append("BATCH PROCESSING COMPLETE")

    return "\n".join(results)


def list_contract_files() -> str:
    """
    Lists all *_anon.txt contract files in the current session date folder.

    Must be called AFTER run_mapping_program() which sets up the session folder paths.
    Only shows anonymized contract files ending in _anon.txt.

    Returns:
        List of contract filenames found in the date folder
    """
    global _session_date_folder

    if _session_date_folder is None:
        return "ERROR: No date folder set in session. Call run_mapping_program() first to initialize."

    # Check if folder exists
    if not _session_date_folder.exists():
        return f"ERROR: Date folder not found: {_session_date_folder}"

    # Find all *_anon.txt files
    contract_files = list(_session_date_folder.glob("*_anon.txt"))

    if not contract_files:
        return f"No *_anon.txt contract files found in {_session_date_folder}"

    # Return just the filenames
    filenames = [f.name for f in contract_files]

    result = f"Found {len(filenames)} contract file(s) in date folder:\n\n"
    for i, filename in enumerate(filenames, 1):
        result += f"{i}. {filename}\n"

    return result


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


def validate_extraction() -> str:
    """
    Validates the extracted contract data and generates a quality report.

    Performs comprehensive validation including:
    - Structural validation (leg count, expected combinations, unusual structures)
    - Completeness validation (critical fields populated)
    - Clarity validation (fields marked as unclear)
    - Data quality validation (suspicious values, invalid data)
    - Consistency validation (FX fixing logic, payer/receiver relationships)

    Returns:
        Human-readable validation report with quality score, structural analysis,
        and flags for manual review
    """
    global _session_merged_contract

    if _session_merged_contract is None:
        return "ERROR: No extracted data in session. Please run extractions first."

    try:
        data = _session_merged_contract

        # Initialize validation results
        critical_issues = []
        warnings = []
        structural_issues = []
        total_fields = 0
        populated_fields = 0
        unclear_fields = []

        # Helper function to get nested field
        def get_nested(obj, path):
            keys = path.split('.')
            for key in keys:
                if isinstance(obj, dict) and key in obj:
                    obj = obj[key]
                else:
                    return None
            return obj

        # ============================================================
        # STRUCTURAL VALIDATION
        # ============================================================

        legs = data.get("legs", [])

        # Check leg count
        if len(legs) == 0:
            critical_issues.append("CRITICAL: No legs found in extraction")
        elif len(legs) == 1:
            structural_issues.append("UNUSUAL: Single-leg contract (expected 2 legs)")
        elif len(legs) > 2:
            structural_issues.append(f"UNUSUAL: {len(legs)}-leg swap (expected 2 legs)")

        # Check leg combinations
        if len(legs) >= 2:
            rate_types = [leg.get("rateType") for leg in legs if leg.get("rateType")]

            if len(rate_types) >= 2:
                # Expected combinations
                if set(rate_types[:2]) == {"FIXED", "FLOATING"}:
                    structural_validation = "✓ Expected combination: FIXED vs FLOATING"
                elif rate_types[0] == "FLOATING" and rate_types[1] == "FLOATING":
                    structural_validation = "✓ Valid combination: FLOATING vs FLOATING"
                elif rate_types[0] == "FIXED" and rate_types[1] == "FIXED":
                    structural_issues.append("UNUSUAL: FIXED vs FIXED (uncommon structure)")
                    structural_validation = "⚠ Unusual combination: FIXED vs FIXED"
                else:
                    structural_validation = f"? Unknown combination: {' vs '.join(rate_types[:2])}"
            else:
                structural_validation = "✗ Cannot determine leg combination (missing rate types)"
                warnings.append("Some legs missing rate type information")
        else:
            structural_validation = "N/A (insufficient legs)"

        # Check for unusual leg count combinations
        if len(legs) > 2:
            rate_combo = " vs ".join([leg.get("rateType", "UNKNOWN") for leg in legs])
            structural_validation = f"⚠ Unusual: {rate_combo}"

        # Check payer/receiver relationships
        if len(legs) >= 2:
            payers = [leg.get("payerPartyReference") for leg in legs if leg.get("payerPartyReference")]
            receivers = [leg.get("receiverPartyReference") for leg in legs if leg.get("receiverPartyReference")]

            # Check for invalid payer/receiver patterns
            if len(payers) >= 2:
                if payers[0] == payers[1]:
                    critical_issues.append(f"CRITICAL: Legs 1 & 2 both have same payer ({payers[0]}) - invalid swap structure")

            if len(receivers) >= 2:
                if receivers[0] == receivers[1]:
                    critical_issues.append(f"CRITICAL: Legs 1 & 2 both have same receiver ({receivers[0]}) - invalid swap structure")

        # Check for proper leg identifiers
        has_leg_ids = all(leg.get("legId") for leg in legs)
        leg_id_status = "✓ All legs have proper identifiers" if has_leg_ids else "⚠ Some legs missing leg identifiers"

        # ============================================================
        # CRITICAL FIELDS VALIDATION
        # ============================================================

        CRITICAL_FIELDS = [
            ("header.tradeDate.date", "Trade Date"),
            ("header.effectiveDate.date", "Effective Date"),
            ("header.terminationDate.date", "Termination Date"),
            ("header.party1.partyName", "Party 1 Name"),
            ("header.party2.partyName", "Party 2 Name"),
        ]

        for field_path, field_name in CRITICAL_FIELDS:
            value = get_nested(data, field_path)
            total_fields += 1
            if value and value not in ["", "N/A", None]:
                populated_fields += 1
            else:
                critical_issues.append(f"Missing critical field: {field_name}")

        # ============================================================
        # CLARITY VALIDATION (*Clear fields)
        # ============================================================

        def check_unclear_recursive(obj, path=""):
            nonlocal unclear_fields, total_fields, populated_fields

            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    if key.endswith("Clear") and value is False:
                        base_field = key.replace("Clear", "")
                        unclear_fields.append(f"{path}.{base_field}" if path else base_field)

                    elif not key.endswith("Clear"):
                        if isinstance(value, (str, int, float, bool)):
                            total_fields += 1
                            if value not in ["", "N/A", None, 0]:
                                populated_fields += 1

                        check_unclear_recursive(value, current_path)

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_unclear_recursive(item, f"{path}[{i}]")

        check_unclear_recursive(data)

        # ============================================================
        # LEG-LEVEL VALIDATION
        # ============================================================

        for i, leg in enumerate(legs):
            leg_num = i + 1

            # Check critical leg fields
            if not leg.get("notionalAmount"):
                critical_issues.append(f"Leg {leg_num}: Missing notional amount")
            elif leg.get("notionalAmount") < 0:
                critical_issues.append(f"Leg {leg_num}: Negative notional amount ({leg.get('notionalAmount')})")

            if not leg.get("notionalCurrency"):
                critical_issues.append(f"Leg {leg_num}: Missing notional currency")

            if not leg.get("rateType"):
                critical_issues.append(f"Leg {leg_num}: Missing rate type (FIXED/FLOATING)")

            # Check rate-specific fields
            if leg.get("rateType") == "FIXED":
                if "fixedRate" not in leg:
                    warnings.append(f"Leg {leg_num}: FIXED leg but no fixedRate specified")
            elif leg.get("rateType") == "FLOATING":
                if not leg.get("floatingRateIndex"):
                    warnings.append(f"Leg {leg_num}: FLOATING leg but no floatingRateIndex")

            # Check FX fixing consistency
            notional_curr = leg.get("notionalCurrency")
            settlement_curr = leg.get("settlementCurrency")
            has_fx_fixing = "fxFixing" in leg

            if notional_curr and settlement_curr:
                if notional_curr != settlement_curr and not has_fx_fixing:
                    warnings.append(f"Leg {leg_num}: Different currencies ({notional_curr}→{settlement_curr}) but no FX fixing data")
                elif notional_curr == settlement_curr and has_fx_fixing:
                    warnings.append(f"Leg {leg_num}: Same currencies ({notional_curr}) but FX fixing data present")

        # ============================================================
        # QUALITY SCORE CALCULATION
        # ============================================================

        completeness_score = int((populated_fields / total_fields * 100)) if total_fields > 0 else 0

        # Determine overall quality
        if structural_issues or critical_issues:
            quality = "POOR ✗"
        elif completeness_score >= 90 and len(warnings) == 0 and len(unclear_fields) <= 5:
            quality = "EXCELLENT ✓"
        elif completeness_score >= 75 and len(warnings) <= 3 and len(unclear_fields) <= 10:
            quality = "GOOD ✓"
        elif completeness_score >= 60:
            quality = "FAIR ⚠"
        else:
            quality = "POOR ✗"

        # ============================================================
        # BUILD REPORT
        # ============================================================

        report = "=" * 60 + "\n"
        report += "EXTRACTION QUALITY REPORT\n"
        report += "=" * 60 + "\n\n"

        report += f"Quality: {quality}\n"
        report += f"Completeness: {completeness_score}% ({populated_fields}/{total_fields} fields)\n\n"

        # Structural validation section
        report += "STRUCTURAL VALIDATION:\n"
        report += "-" * 60 + "\n"

        if len(legs) == 2:
            report += "✓ Standard 2-leg swap structure\n"
        elif structural_issues:
            for issue in structural_issues:
                report += f"✗ {issue}\n"

        report += f"{structural_validation}\n"
        report += f"{leg_id_status}\n"

        # Show payer/receiver validation
        if len(legs) >= 2 and not any("same payer" in str(issue) or "same receiver" in str(issue) for issue in critical_issues):
            report += "✓ Payer/receiver directions valid\n"

        report += "\n"

        # Contract overview
        if "header" in data:
            header = data["header"]
            report += "CONTRACT OVERVIEW:\n"
            report += "-" * 60 + "\n"
            report += f"Parties: {header.get('party1', {}).get('partyName', 'N/A')} ↔ {header.get('party2', {}).get('partyName', 'N/A')}\n"
            report += f"Trade Date: {header.get('tradeDate', {}).get('date', 'N/A')}\n"
            report += f"Effective Date: {header.get('effectiveDate', {}).get('date', 'N/A')}\n"
            report += f"Termination Date: {header.get('terminationDate', {}).get('date', 'N/A')}\n"
            if header.get('tradeId'):
                trade_id = header['tradeId']
                if isinstance(trade_id, dict):
                    report += f"Trade ID: {trade_id.get('id', 'N/A')}\n"
                else:
                    report += f"Trade ID: {trade_id}\n"
            report += "\n"

        # Legs summary
        if legs:
            report += f"LEGS: {len(legs)} leg(s) found\n"
            report += "-" * 60 + "\n"
            for i, leg in enumerate(legs):
                leg_num = i + 1
                report += f"Leg {leg_num} ({leg.get('legId', f'Leg{leg_num}')}):\n"
                report += f"  Type: {leg.get('rateType', 'N/A')}\n"

                notional = leg.get('notionalAmount')
                if notional:
                    report += f"  Notional: {leg.get('notionalCurrency', 'N/A')} {notional:,.2f}\n"
                else:
                    report += f"  Notional: N/A\n"

                report += f"  Settlement: {leg.get('settlementCurrency', 'N/A')}\n"

                if leg.get('rateType') == 'FIXED':
                    report += f"  Fixed Rate: {leg.get('fixedRate', 'N/A')}\n"
                elif leg.get('rateType') == 'FLOATING':
                    report += f"  Index: {leg.get('floatingRateIndex', 'N/A')}\n"
                    report += f"  Spread: {leg.get('spread', 'N/A')}\n"

                report += f"  Payer: {leg.get('payerPartyReference', 'N/A')} → Receiver: {leg.get('receiverPartyReference', 'N/A')}\n"
                report += "\n"

        # Critical issues section
        if critical_issues:
            report += "⚠ CRITICAL ISSUES (MUST REVIEW):\n"
            report += "-" * 60 + "\n"
            for issue in critical_issues:
                report += f"  ✗ {issue}\n"
            report += "\n"

        # Warnings section
        if warnings:
            report += "⚠ WARNINGS (REVIEW RECOMMENDED):\n"
            report += "-" * 60 + "\n"
            for warning in warnings:
                report += f"  ⚠ {warning}\n"
            report += "\n"

        # Unclear fields section
        if unclear_fields:
            report += f"⚠ UNCLEAR EXTRACTIONS ({len(unclear_fields)} field(s)):\n"
            report += "-" * 60 + "\n"
            for field in unclear_fields[:10]:
                report += f"  ? {field}\n"
            if len(unclear_fields) > 10:
                report += f"  ... and {len(unclear_fields) - 10} more\n"
            report += "\n"

        # Final summary
        if not critical_issues and not structural_issues and len(warnings) == 0 and len(unclear_fields) <= 5:
            report += "✓ ALL CRITICAL VALIDATIONS PASSED\n"
            report += "✓ Extraction quality is high - ready for processing\n\n"
        elif not critical_issues and not structural_issues:
            report += "✓ No critical issues found\n"
            report += "⚠ Review warnings and unclear fields before processing\n\n"
        else:
            report += "✗ Critical issues found - manual review required\n\n"

        report += "=" * 60

        return report

    except Exception as e:
        return f"ERROR during validation: {str(e)}"


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
        "**Bank Processing:**\n"
        "- run_mapping_program(date, bank_name): Runs CSV to JSON mapping - ALWAYS RUN THIS FIRST!\n"
        "  Date format: dd/mm/yyyy (e.g., '25/09/2025')\n"
        "  Bank name format: BankNameCL (e.g., 'BancoInternacionalCL')\n"
        "\n"
        "**Session Management:**\n"
        "- list_contract_files(): Lists all *_anon.txt files in date folder\n"
        "- clear_session(): Clears all session data - USE THIS BEFORE NEW CONTRACT!\n"
        "- read_contract_file(filename): Loads contract from date folder (just filename, not full path)\n"
        "- get_session_status(): Shows what's currently loaded in session\n"
        "- save_contract_to_batch(): Saves current contract to batch (for consolidated output)\n"
        "- write_consolidated_output(): Writes all contracts to date folder\n"
        "- write_output_json(filename): Writes individual contract file (single contract mode)\n"
        "- query_contract_data(question): Ask questions about contract or extracted data\n"
        "\n"
        "**Extraction Tools (auto-merge into session):**\n"
        "- extract_core_values(): Extracts core data, stores in session\n"
        "- extract_business_day_conventions(): Extracts & merges into session\n"
        "- extract_period_payment_data(): Extracts & merges into session\n"
        "- extract_fx_fixing(): Extracts & merges into session\n"
        "- extract_payment_date_offset(): Extracts payment offset & merges into session\n"
        "\n"
        "**Validation Tool:**\n"
        "- validate_extraction(): Validates extracted data quality & completeness\n"
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
        "2. read_contract_file('folder/filename.txt') → wait for response (use EXACT path user specifies)\n"
        "3. extract_core_values() → wait for response\n"
        "4. extract_business_day_conventions() → wait for response\n"
        "5. extract_period_payment_data() → wait for response\n"
        "6. extract_fx_fixing() → wait for response\n"
        "7. extract_payment_date_offset() → wait for response\n"
        "8. validate_extraction() → wait for response (reviews quality)\n"
        "9. write_output_json('filename.json') → wait for response (use same base name as input)\n"
        "\n"
        "**Follow-up questions about same contract:**\n"
        "- DO NOT clear session - data is already loaded\n"
        "- Use query_contract_data(question) to answer user questions\n"
        "- You can re-run specific extractions if needed\n"
        "\n"
        "**Complete Bank Processing Workflow:**\n"
        "When user says 'Process [date] for [BankName]':\n"
        "\n"
        "1. run_mapping_program(date, bank_name)\n"
        "   Example: run_mapping_program('25/09/2025', 'BancoInternacionalCL')\n"
        "   This sets up session folders and processes CSV → banco JSON\n"
        "\n"
        "2. list_contract_files()\n"
        "   Shows all *_anon.txt files in the date folder\n"
        "\n"
        "3. For EACH contract file:\n"
        "   a. clear_session()\n"
        "   b. read_contract_file('filename_anon.txt')\n"
        "   c. extract_core_values()\n"
        "   d. extract_business_day_conventions()\n"
        "   e. extract_period_payment_data()\n"
        "   f. extract_fx_fixing()\n"
        "   g. extract_payment_date_offset()\n"
        "   h. validate_extraction() → show validation report\n"
        "   i. save_contract_to_batch()\n"
        "\n"
        "4. write_consolidated_output()\n"
        "   Writes ddmmyyyy_bancoabc_contracts.json to date folder\n"
        "\n"
        "CRITICAL: Call tools ONE at a time. Wait for response before next tool.\n"
        "\n"
        "Each extraction auto-merges into session.\n"
        "\n"
        "# Important:\n"
        "- NO parameters needed for write_output_json - it reads from session\n"
        "- Extractions return status messages, not JSON\n"
        "- Session storage avoids JSON escaping issues in tool calls"
    ),
    tools=[
        run_mapping_program,
        list_contract_files,
        clear_session,
        read_contract_file,
        get_session_status,
        save_contract_to_batch,
        write_consolidated_output,
        write_output_json,
        query_contract_data,
        extract_core_values,
        extract_business_day_conventions,
        extract_period_payment_data,
        extract_fx_fixing,
        extract_payment_date_offset,
        validate_extraction,
        greet_user,
        calculate_sum
    ]
)

# Also export as 'agent' for backwards compatibility
agent = root_agent
