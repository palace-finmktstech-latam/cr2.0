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
_session_mapped_trades = None  # Cached mapped trades JSON data from mapping_program output
_session_pending_corrections = []  # Stores pending corrections from cross_validate for apply_corrections


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


def run_cdm_generator() -> str:
    """
    Runs the CDM generator JAR to convert JSON files to CDM format.

    Must be called AFTER write_consolidated_output() which creates the input files.

    Reads from: {date_folder}/cdm_inputs/
    - ddmmyyyy_bancoabc_trades.json (from mapping)
    - ddmmyyyy_bancoabc_contracts.json (from extraction)

    Writes to: {date_folder}/cdm_outputs/
    - CDM-formatted JSON files

    Returns:
        Success message with output file count, or error message
    """
    global _session_date_folder
    import subprocess
    from pathlib import Path

    if _session_date_folder is None:
        return "ERROR: No date folder set in session. Call run_mapping_program() first to initialize."

    try:
        # Define paths
        cdm_jar_path = Path(r"c:\Users\bencl\Proyectos\cr2.0\backend\cdm\cdm-generator.jar")
        input_dir = _session_date_folder / "cdm_inputs"
        output_dir = _session_date_folder / "cdm_outputs"

        # Validate JAR exists
        if not cdm_jar_path.exists():
            return f"ERROR: CDM generator JAR not found at: {cdm_jar_path}"

        # Validate input directory exists and has files
        if not input_dir.exists():
            return f"ERROR: Input directory not found: {input_dir}\nMake sure run_mapping_program() and write_consolidated_output() completed successfully."

        input_files = list(input_dir.glob("*.json"))
        if not input_files:
            return f"ERROR: No JSON files found in {input_dir}"

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run CDM generator JAR
        result = subprocess.run(
            [
                "java", "-jar", str(cdm_jar_path),
                "--inputDir", str(input_dir),
                "--outputDir", str(output_dir)
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Check return code
        if result.returncode != 0:
            error_msg = f"ERROR: CDM generator failed with return code {result.returncode}\n\n"
            if result.stderr:
                error_msg += f"Error output:\n{result.stderr}\n"
            if result.stdout:
                error_msg += f"Standard output:\n{result.stdout}"
            return error_msg

        # Validate output files were created (check both root and subfolders)
        output_files = list(output_dir.glob("*.json"))
        output_files_recursive = list(output_dir.glob("**/*.json"))

        if not output_files and not output_files_recursive:
            return f"WARNING: CDM generator completed but no output files found in {output_dir}\n\nOutput:\n{result.stdout}"

        # Use recursive search if no files in root
        files_to_report = output_files if output_files else output_files_recursive

        # Success!
        file_list = "\n".join([f"  - {f.relative_to(output_dir)}" for f in files_to_report])
        msg = f"SUCCESS: CDM generation completed!\n"
        msg += f"Input files: {len(input_files)}\n"
        msg += f"Output files: {len(files_to_report)}\n"
        msg += f"Output directory: {output_dir}\n\n"
        msg += f"Generated CDM files:\n{file_list}"

        if result.stdout:
            msg += f"\n\nCDM Generator output:\n{result.stdout}"

        return msg

    except subprocess.TimeoutExpired:
        return "ERROR: CDM generator timed out after 5 minutes"
    except Exception as e:
        return f"ERROR running CDM generator: {str(e)}"


def run_pdf_report() -> str:
    """
    Generates PDF comparison report between Banco and Contract CDM outputs.

    Must be called AFTER run_cdm_generator() which creates the CDM files.

    Reads from:
    - {date_folder}/cdm_outputs/banks/ (Banco CDM files)
    - {date_folder}/cdm_outputs/contracts/ (Contract CDM files)
    - {bank_folder}/translations.json (field translations)
    - backend/palace_logo.png (logo)

    Writes to: {date_folder}/reports/reporte_operaciones_ddmmyyyy_<timestamp>.pdf

    Returns:
        Success message with report path and summary, or error message
    """
    global _session_date_folder, _session_bank_name
    import subprocess
    from pathlib import Path
    from datetime import datetime

    if _session_date_folder is None or _session_bank_name is None:
        return "ERROR: No date folder or bank name set in session. Call run_mapping_program() first to initialize."

    try:
        # Define paths
        pdf_script_path = Path(__file__).parent.parent.parent / "json_pdf_report.py"

        # Validate script exists
        if not pdf_script_path.exists():
            return f"ERROR: PDF report script not found at: {pdf_script_path}"

        # Extract date string from folder name
        date_folder_name = _session_date_folder.name  # e.g., "25092025"
        # Convert back to dd/mm/yyyy
        date_obj = datetime.strptime(date_folder_name, "%d%m%Y")
        date_str = date_obj.strftime("%d/%m/%Y")

        # Run PDF report script
        result = subprocess.run(
            [
                "python", str(pdf_script_path),
                date_str,
                _session_bank_name
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        # Check return code
        if result.returncode != 0:
            error_msg = f"ERROR: PDF report generation failed with return code {result.returncode}\n\n"
            if result.stderr:
                error_msg += f"Error output:\n{result.stderr}\n"
            if result.stdout:
                error_msg += f"Standard output:\n{result.stdout}"
            return error_msg

        # Parse output to find PDF filename
        output_lines = result.stdout

        # Success!
        msg = f"SUCCESS: PDF report generated!\n\n"
        msg += f"Report output:\n{output_lines}"

        return msg

    except subprocess.TimeoutExpired:
        return "ERROR: PDF report generation timed out after 5 minutes"
    except Exception as e:
        return f"ERROR running PDF report generator: {str(e)}"


def resume_workflow(date_str: str, bank_name: str, start_from: str) -> str:
    """
    Resume the bank processing workflow from a specific step.

    Use this when you've manually fixed files and want to continue from a certain point
    without re-running previous steps (like extraction).

    Args:
        date_str: Date in dd/mm/yyyy format (e.g., "01/10/2025")
        bank_name: Bank name with country code (e.g., "BankAlias1CL")
        start_from: Where to resume from:
            - "mapping": Re-run mapping program, then continue full workflow
            - "cdm_generator": Run CDM generator and PDF report (skip extraction)
            - "pdf_report": Run only PDF report (skip everything else)

    Returns:
        Status message with results of each step executed
    """
    global _session_date_folder, _session_bank_name
    from datetime import datetime
    from pathlib import Path

    try:
        # Parse date and set up session
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        date_folder_name = date_obj.strftime("%d%m%Y")

        base_path = Path(r"C:\Users\bencl\OneDrive - palace.cl\Documents\Palace\Ideas\Contract Extraction\v2.0\Servicio")
        _session_date_folder = base_path / bank_name / date_folder_name
        _session_bank_name = bank_name

        if not _session_date_folder.exists():
            return f"ERROR: Date folder not found: {_session_date_folder}"

        results = []
        results.append(f"Session initialized: {_session_date_folder}")
        results.append(f"Bank: {_session_bank_name}")
        results.append(f"Resuming workflow from: {start_from}")
        results.append("")

        # Load mapped trades into session (needed for matching and PDF report)
        results.append("=== Loading mapped trades into session ===")
        load_result = load_mapped_trades()
        results.append(load_result)
        results.append("")

        # Execute requested steps
        if start_from == "mapping":
            results.append("=== STEP 1: Running mapping program ===")
            mapping_result = run_mapping_program(date_str, bank_name)
            results.append(mapping_result)
            results.append("")

            results.append("=== STEP 2: Running CDM generator ===")
            cdm_result = run_cdm_generator()
            results.append(cdm_result)
            results.append("")

            results.append("=== STEP 3: Running PDF report ===")
            pdf_result = run_pdf_report()
            results.append(pdf_result)

        elif start_from == "cdm_generator":
            results.append("=== STEP 1: Running CDM generator ===")
            cdm_result = run_cdm_generator()
            results.append(cdm_result)
            results.append("")

            results.append("=== STEP 2: Running PDF report ===")
            pdf_result = run_pdf_report()
            results.append(pdf_result)

        elif start_from == "pdf_report":
            results.append("=== Running PDF report ===")
            pdf_result = run_pdf_report()
            results.append(pdf_result)

        else:
            return f"ERROR: Unknown start_from value '{start_from}'. Valid options: mapping, cdm_generator, pdf_report"

        return "\n".join(results)

    except Exception as e:
        return f"ERROR resuming workflow: {str(e)}"


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

    Creates TWO files:
    1. Clean version: cdm_inputs/{date}_bancoabc_contracts.json - No *Clear fields (CDM ready)
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

        # Write clean version (without Clear fields) to cdm_inputs subfolder
        cdm_inputs_dir = _session_date_folder / "cdm_inputs"
        cdm_inputs_dir.mkdir(parents=True, exist_ok=True)
        output_path = cdm_inputs_dir / filename

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


def load_mapped_trades() -> str:
    """
    Loads the mapped trades JSON file into session for matching with contract extractions.

    Must be called AFTER run_mapping_program() which creates the mapping output file.
    This should be called once after mapping completes, then the data is cached for all
    contract matching operations.

    Returns:
        Success message with number of trades loaded, or error message
    """
    global _session_date_folder, _session_mapped_trades

    if _session_date_folder is None:
        return "ERROR: No date folder set in session. Call run_mapping_program() first to initialize."

    # Construct mapping output filename in cdm_inputs folder
    date_folder_name = _session_date_folder.name  # e.g., "25092025"
    mapping_file = _session_date_folder / "cdm_inputs" / f"{date_folder_name}_bancoabc_trades.json"

    # Check if file exists
    if not mapping_file.exists():
        return f"ERROR: Mapping output file not found: {mapping_file}\nMake sure run_mapping_program() completed successfully."

    # Read and parse JSON
    try:
        with open(mapping_file, 'r', encoding='utf-8') as f:
            _session_mapped_trades = json.load(f)

        # Count trades
        num_trades = len(_session_mapped_trades.get("trades", []))

        return f"SUCCESS: Loaded {num_trades} mapped trade(s) from {mapping_file.name} into session cache.\nReady for contract matching."

    except json.JSONDecodeError as e:
        return f"ERROR: Failed to parse mapping JSON: {e}"
    except Exception as e:
        return f"ERROR: Failed to load mapping file: {e}"


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
    Validates the structural integrity of extracted contract data.

    Performs structural validation only:
    - Leg count and structure (expected 2-leg swaps)
    - Rate type combinations (FIXED/FLOATING patterns)
    - Payer/receiver relationships (valid swap directions)
    - Critical field presence (not values, just existence)

    Does NOT validate extraction quality or field values.
    Use cross_validate() for quality verification.

    Returns:
        Human-readable structural validation report
    """
    global _session_merged_contract

    if _session_merged_contract is None:
        return "ERROR: No extracted data in session. Please run extractions first."

    try:
        data = _session_merged_contract

        # Initialize validation results
        critical_issues = []
        structural_issues = []

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
                structural_issues.append("Some legs missing rate type information")
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
        # CRITICAL HEADER FIELDS PRESENCE CHECK
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
            if not value or value in ["", "N/A"]:
                critical_issues.append(f"Missing critical field: {field_name}")

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

            # Check rate-specific fields exist (presence only, not values)
            if leg.get("rateType") == "FIXED":
                if "fixedRate" not in leg:
                    critical_issues.append(f"Leg {leg_num}: FIXED leg but no fixedRate field")
            elif leg.get("rateType") == "FLOATING":
                if not leg.get("floatingRateIndex"):
                    critical_issues.append(f"Leg {leg_num}: FLOATING leg but no floatingRateIndex field")

        # ============================================================
        # BUILD REPORT
        # ============================================================

        report = "=" * 60 + "\n"
        report += "EXTRACTION STRUCTURAL REPORT\n"
        report += "=" * 60 + "\n\n"

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
                    fixed_rate = leg.get('fixedRate', 'N/A')
                    if fixed_rate != 'N/A':
                        report += f"  Fixed Rate: {fixed_rate}%\n"
                    else:
                        report += f"  Fixed Rate: N/A\n"
                elif leg.get('rateType') == 'FLOATING':
                    report += f"  Index: {leg.get('floatingRateIndex', 'N/A')}\n"
                    spread = leg.get('spread', 'N/A')
                    if spread != 'N/A':
                        report += f"  Spread: {spread}\n"

                report += f"  Payer: {leg.get('payerPartyReference', 'N/A')} → Receiver: {leg.get('receiverPartyReference', 'N/A')}\n"
                report += "\n"

        # Critical field checks summary
        report += "CRITICAL FIELD CHECKS:\n"
        report += "-" * 60 + "\n"

        if not critical_issues:
            report += "✓ Trade date present\n"
            report += "✓ Effective date present\n"
            report += "✓ Termination date present\n"
            report += "✓ Party names present\n"
            report += "✓ All legs have notional amounts\n"
            report += "✓ All legs have currencies\n"
            report += "✓ All legs have rate types\n"
            report += "\n"

        # Structural issues section
        if structural_issues or critical_issues:
            report += "⚠ STRUCTURAL ISSUES:\n"
            report += "-" * 60 + "\n"
            if structural_issues:
                for issue in structural_issues:
                    report += f"  ✗ {issue}\n"
            if critical_issues:
                for issue in critical_issues:
                    report += f"  ✗ {issue}\n"
            report += "\n"
        else:
            report += "⚠ STRUCTURAL ISSUES:\n"
            report += "-" * 60 + "\n"
            report += "(none found)\n"
            report += "\n"

        # Final summary
        report += "=" * 60 + "\n"
        if not critical_issues and not structural_issues:
            report += "✓ STRUCTURAL VALIDATION PASSED\n"
            report += "→ Proceed to cross-validation for quality verification\n"
        else:
            report += "✗ STRUCTURAL ISSUES FOUND\n"
            report += "⚠ Review issues above before proceeding\n"

        report += "=" * 60

        return report

    except Exception as e:
        return f"ERROR during validation: {str(e)}"


def cross_validate() -> str:
    """
    Cross-validates specific critical fields using Claude Sonnet 4.5.

    Validates field-by-field:
    - legs[].settlementType (CASH vs PHYSICAL)
    - legs[].settlementCurrency (ISO currency code)
    - legs[].fxFixing placement (correct leg assignment)
    - header date business day conventions (tradeDate, effectiveDate, terminationDate)
    - leg date business day conventions (effectiveDate, terminationDate for each leg)

    Uses original Gemini extraction prompts as validation context for consistency.
    Provides numeric confidence scores (0-100) for each field.

    Returns:
        Human-readable cross-validation report with disagreements flagged for manual review
    """
    global _session_merged_contract, _session_contract_text, _session_date_folder, _session_contract_name

    if _session_merged_contract is None:
        return "ERROR: No extracted data in session. Run extraction steps first."

    if _session_contract_text is None:
        return "ERROR: No contract text in session. Call read_contract_file() first."

    try:
        import anthropic
        import os

        # Initialize Claude client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return "ERROR: ANTHROPIC_API_KEY environment variable not set"

        client = anthropic.Anthropic(api_key=api_key)

        data = _session_merged_contract
        contract_text = _session_contract_text
        legs = data.get("legs", [])

        if len(legs) == 0:
            return "ERROR: No legs found in extracted data"

        # ============================================================
        # LOAD ORIGINAL EXTRACTION PROMPTS
        # ============================================================

        def extract_prompt_section(prompt_text, section_marker):
            """Extract relevant section from prompt file"""
            # For settlement fields, look for settlement-related sections
            if "settlement" in section_marker.lower():
                # Find settlement type/currency definitions
                lines = prompt_text.split('\n')
                start_idx = None
                end_idx = None

                for i, line in enumerate(lines):
                    if 'settlementType' in line or 'Settlement Type' in line:
                        start_idx = max(0, i - 5)
                    if start_idx and (i - start_idx > 50 or 'fxFixing' in line):
                        end_idx = i
                        break

                if start_idx:
                    return '\n'.join(lines[start_idx:end_idx if end_idx else start_idx + 50])

            return prompt_text[:2000]  # Fallback: first 2000 chars

        # Load Core Values prompt for settlement definitions
        core_values_path = BACKEND_DIR / "prompts" / "promptCoreValues.txt"
        settlement_instructions = ""
        if core_values_path.exists():
            with open(core_values_path, 'r', encoding='utf-8') as f:
                core_values_prompt = f.read()
                settlement_instructions = extract_prompt_section(core_values_prompt, "settlement")

        # Load FX Fixing prompt for assignment logic
        fx_fixing_path = BACKEND_DIR / "prompts" / "promptFXFixingData.txt"
        fx_fixing_instructions = ""
        if fx_fixing_path.exists():
            with open(fx_fixing_path, 'r', encoding='utf-8') as f:
                fx_fixing_prompt = f.read()
                # Extract the CRITICAL section
                if "CRITICAL - FX FIXING ASSIGNMENT LOGIC" in fx_fixing_prompt:
                    start = fx_fixing_prompt.index("CRITICAL - FX FIXING ASSIGNMENT LOGIC")
                    # Find end (look for next major section or 1000 chars)
                    end = start + min(1500, len(fx_fixing_prompt) - start)
                    fx_fixing_instructions = fx_fixing_prompt[start:end]
                else:
                    fx_fixing_instructions = fx_fixing_prompt[:1500]

        # Load Business Day Conventions prompt for header dates
        header_bdc_path = BACKEND_DIR / "prompts" / "promptHeaderBusinessDayConventions.txt"
        header_bdc_instructions = ""
        if header_bdc_path.exists():
            with open(header_bdc_path, 'r', encoding='utf-8') as f:
                header_bdc_instructions = f.read()[:3000]  # First 3000 chars for context

        # Load Period End and Payment Business Day Conventions prompt for leg dates
        period_payment_bdc_path = BACKEND_DIR / "prompts" / "promptPeriodEndAndPaymentBusinessDayConventions.txt"
        period_payment_bdc_instructions = ""
        if period_payment_bdc_path.exists():
            with open(period_payment_bdc_path, 'r', encoding='utf-8') as f:
                period_payment_bdc_instructions = f.read()[:3000]  # First 3000 chars for context

        # ============================================================
        # BUILD FIELDS TO VALIDATE
        # ============================================================

        fields_to_validate = []

        # Header date business day conventions
        header = data.get("header", {})

        # Trade Date business day convention
        trade_date = header.get("tradeDate", {})
        trade_bdc = trade_date.get("businessDayConvention", "")
        trade_bdc_clear = trade_date.get("tradeDateBusinessDayConventionClear", True)
        fields_to_validate.append({
            "field": "header.tradeDate.businessDayConvention",
            "extractedValue": trade_bdc,
            "geminiConfidence": "high" if trade_bdc_clear else "low"
        })

        # Effective Date business day convention
        effective_date = header.get("effectiveDate", {})
        effective_bdc = effective_date.get("businessDayConvention", "")
        effective_bdc_clear = effective_date.get("effectiveDateBusinessDayConventionClear", True)
        fields_to_validate.append({
            "field": "header.effectiveDate.businessDayConvention",
            "extractedValue": effective_bdc,
            "geminiConfidence": "high" if effective_bdc_clear else "low"
        })

        # Termination Date business day convention
        termination_date = header.get("terminationDate", {})
        termination_bdc = termination_date.get("businessDayConvention", "")
        termination_bdc_clear = termination_date.get("terminationDateBusinessDayConventionClear", True)
        fields_to_validate.append({
            "field": "header.terminationDate.businessDayConvention",
            "extractedValue": termination_bdc,
            "geminiConfidence": "high" if termination_bdc_clear else "low"
        })

        # For each leg, validate settlement type and currency
        for i, leg in enumerate(legs):
            leg_num = i + 1

            # Settlement Type
            settlement_type = leg.get("settlementType", "")
            settlement_type_clear = leg.get("settlementTypeClear", True)
            fields_to_validate.append({
                "field": f"legs[{i}].settlementType",
                "extractedValue": settlement_type,
                "geminiConfidence": "high" if settlement_type_clear else "low"
            })

            # Settlement Currency
            settlement_currency = leg.get("settlementCurrency", "")
            settlement_currency_clear = leg.get("settlementCurrencyClear", True)
            fields_to_validate.append({
                "field": f"legs[{i}].settlementCurrency",
                "extractedValue": settlement_currency,
                "geminiConfidence": "high" if settlement_currency_clear else "low"
            })

            # Leg effective date business day convention
            leg_effective_date = leg.get("effectiveDate", {})
            leg_effective_bdc = leg_effective_date.get("businessDayConvention", "")
            leg_effective_bdc_clear = leg_effective_date.get("effectiveDateBusinessDayConventionClear", True)
            fields_to_validate.append({
                "field": f"legs[{i}].effectiveDate.businessDayConvention",
                "extractedValue": leg_effective_bdc,
                "geminiConfidence": "high" if leg_effective_bdc_clear else "low"
            })

            # Leg termination date business day convention
            leg_termination_date = leg.get("terminationDate", {})
            leg_termination_bdc = leg_termination_date.get("businessDayConvention", "")
            leg_termination_bdc_clear = leg_termination_date.get("terminationDateBusinessDayConventionClear", True)
            fields_to_validate.append({
                "field": f"legs[{i}].terminationDate.businessDayConvention",
                "extractedValue": leg_termination_bdc,
                "geminiConfidence": "high" if leg_termination_bdc_clear else "low"
            })

        # FX Fixing placement validation
        fx_fixing_info = []
        for i, leg in enumerate(legs):
            notional_curr = leg.get("notionalCurrency", "")
            settlement_curr = leg.get("settlementCurrency", "")
            has_fx_fixing = "fxFixing" in leg
            fx_fixing_info.append({
                "leg": i,
                "notionalCurrency": notional_curr,
                "settlementCurrency": settlement_curr,
                "hasFxFixing": has_fx_fixing
            })

        fields_to_validate.append({
            "field": "legs[].fxFixing.placement",
            "extractedValue": fx_fixing_info,
            "geminiConfidence": "N/A"
        })

        # ============================================================
        # AUTOMATIC VALIDATIONS
        # ============================================================

        # 1. Settlement Type Validation
        # Check if settlement currencies are the same → must be CASH
        # If different → must be PHYSICAL

        settlement_type_validation = None
        business_day_convention_validations = []
        if len(legs) >= 2:
            leg0_settlement_curr = legs[0].get("settlementCurrency", "")
            leg1_settlement_curr = legs[1].get("settlementCurrency", "")
            leg0_settlement_type = legs[0].get("settlementType", "")
            leg1_settlement_type = legs[1].get("settlementType", "")

            if leg0_settlement_curr and leg1_settlement_curr:
                # Determine expected settlement type based on currencies
                expected_settlement_type = "CASH" if leg0_settlement_curr == leg1_settlement_curr else "PHYSICAL"

                # Check if actual matches expected
                if leg0_settlement_type != expected_settlement_type or leg1_settlement_type != expected_settlement_type:
                    # Dynamic evidence and reasoning based on whether currencies match
                    if leg0_settlement_curr == leg1_settlement_curr:
                        evidence_msg = f"Settlement currencies: Leg 0 = {leg0_settlement_curr}, Leg 1 = {leg1_settlement_curr}. BOTH legs settle in the SAME currency ({leg0_settlement_curr})."
                        reasoning_msg = f"CRITICAL ERROR: Both legs have the SAME settlement currency ({leg0_settlement_curr}), therefore settlement type MUST be CASH (net settlement), not PHYSICAL. The rule is: same settlement currency → CASH, different settlement currencies → PHYSICAL."
                    else:
                        evidence_msg = f"Settlement currencies: Leg 0 = {leg0_settlement_curr}, Leg 1 = {leg1_settlement_curr}. Legs settle in DIFFERENT currencies."
                        reasoning_msg = f"CRITICAL ERROR: Legs have DIFFERENT settlement currencies ({leg0_settlement_curr} vs {leg1_settlement_curr}), therefore settlement type MUST be PHYSICAL (full delivery), not CASH. The rule is: same settlement currency → CASH, different settlement currencies → PHYSICAL."

                    settlement_type_validation = {
                        "field": "legs[].settlementType",
                        "extractedValue": f"Leg 0: {leg0_settlement_type}, Leg 1: {leg1_settlement_type}",
                        "suggestedValue": expected_settlement_type,
                        "geminiConfidence": "N/A",
                        "confidence": 5,  # STRONG_DISAGREE
                        "evidence": evidence_msg,
                        "reasoning": reasoning_msg
                    }
                    # Add to beginning of validations list for prominence
                    fields_to_validate.insert(0, {
                        "field": "legs[].settlementType",
                        "extractedValue": f"Leg 0: {leg0_settlement_type}, Leg 1: {leg1_settlement_type}",
                        "geminiConfidence": "high"
                    })

        # 2. Business Day Convention Validation
        # Check if BDC is FOLLOWING with Clear=false → should be MODFOLLOWING

        # Check header dates
        header = data.get("header", {})
        for date_field, date_name in [("tradeDate", "Trade Date"), ("effectiveDate", "Effective Date"), ("terminationDate", "Termination Date")]:
            date_obj = header.get(date_field, {})
            bdc = date_obj.get("businessDayConvention", "")
            bdc_clear = date_obj.get(f"{date_field}BusinessDayConventionClear", True)

            if bdc == "FOLLOWING" and not bdc_clear:
                business_day_convention_validations.append({
                    "field": f"header.{date_field}.businessDayConvention",
                    "extractedValue": "FOLLOWING",
                    "suggestedValue": "MODFOLLOWING",
                    "geminiConfidence": "low",
                    "confidence": 5,  # STRONG_DISAGREE
                    "evidence": f"No explicit business day convention found in contract for {date_name}. Gemini defaulted to FOLLOWING (Clear=false).",
                    "reasoning": f"When no explicit business day convention is found, the default MUST be MODFOLLOWING (industry standard), not FOLLOWING. Since Gemini set Clear=false, this indicates it used a default value, which should have been MODFOLLOWING."
                })

        # Check leg dates
        for i, leg in enumerate(legs):
            for date_field, date_name in [("effectiveDate", "Effective Date"), ("terminationDate", "Termination Date")]:
                date_obj = leg.get(date_field, {})
                bdc = date_obj.get("businessDayConvention", "")
                bdc_clear = date_obj.get(f"{date_field}BusinessDayConventionClear", True)

                if bdc == "FOLLOWING" and not bdc_clear:
                    business_day_convention_validations.append({
                        "field": f"legs[{i}].{date_field}.businessDayConvention",
                        "extractedValue": "FOLLOWING",
                        "suggestedValue": "MODFOLLOWING",
                        "geminiConfidence": "low",
                        "confidence": 5,  # STRONG_DISAGREE
                        "evidence": f"No explicit business day convention found in contract for Leg {i} {date_name}. Gemini defaulted to FOLLOWING (Clear=false).",
                        "reasoning": f"When no explicit business day convention is found, the default MUST be MODFOLLOWING (industry standard), not FOLLOWING. Since Gemini set Clear=false, this indicates it used a default value, which should have been MODFOLLOWING."
                    })

        # ============================================================
        # BUILD CLAUDE PROMPT
        # ============================================================

        prompt = f"""You are validating a contract extraction performed by another AI system (Gemini).

The original AI was given specific extraction instructions. Your job is to verify if the extracted values are correct according to BOTH:
1. The contract text
2. The original extraction instructions

---

ORIGINAL EXTRACTION INSTRUCTIONS:

## Business Day Conventions for Header Dates:
{header_bdc_instructions}

## Business Day Conventions for Leg Dates (Period End & Payment):
{period_payment_bdc_instructions}

## Settlement Type and Currency:
{settlement_instructions}

**CRITICAL VALIDATION RULE FOR SETTLEMENT TYPE:**

**DO NOT confuse notional currency with settlement currency!**
- Notional currency = the currency the leg is denominated in
- Settlement currency = the currency payments are actually made in
- These can be DIFFERENT on the same leg (e.g., notional in CLF, settlement in CLP)

**The settlement type is determined by comparing SETTLEMENT currencies ACROSS legs:**
- Compare: legs[0].settlementCurrency vs legs[1].settlementCurrency
- **DO NOT compare**: notional currencies
- **DO NOT compare**: notional vs settlement on the same leg

**Rule:**
- If legs[0].settlementCurrency == legs[1].settlementCurrency → BOTH legs MUST be "CASH"
- If legs[0].settlementCurrency != legs[1].settlementCurrency → BOTH legs MUST be "PHYSICAL"

**Ignore contract terminology** like "Entrega Física" or "Physical Delivery" - these are misleading.

**Examples:**
1. Leg 0: notional=CLF, settlement=CLP | Leg 1: notional=CLP, settlement=CLP
   → BOTH settlement currencies are CLP → BOTH legs MUST be CASH (confidence: 0-5 if PHYSICAL)

2. Leg 0: notional=USD, settlement=USD | Leg 1: notional=CLP, settlement=CLP
   → Different settlement currencies (USD vs CLP) → BOTH legs MUST be PHYSICAL (confidence: 0-5 if CASH)

## FX Fixing Assignment Logic:
{fx_fixing_instructions}

---

CONTRACT TEXT:
{contract_text}

---

EXTRACTED DATA (JSON):
{json.dumps(data, indent=2)}

---

VALIDATE THESE SPECIFIC FIELDS:

"""

        # Add each field to validate
        for idx, field_info in enumerate(fields_to_validate[:-1], 1):  # Exclude FX fixing for now
            prompt += f"""Field {idx}: {field_info['field']}
  Extracted Value: "{field_info['extractedValue']}"
  Gemini Confidence: {field_info['geminiConfidence']}
  {"⚠️ LOW CONFIDENCE - extra scrutiny needed" if field_info['geminiConfidence'] == "low" else ""}

"""

        # Add FX fixing validation
        prompt += f"""Field {len(fields_to_validate)}: legs[].fxFixing.placement

"""
        for leg_info in fx_fixing_info:
            prompt += f"""  Leg {leg_info['leg']}: notionalCurrency={leg_info['notionalCurrency']}, settlementCurrency={leg_info['settlementCurrency']}
    - Has fxFixing? {"Yes" if leg_info['hasFxFixing'] else "No"}
"""

        prompt += """
  VERIFY: According to the FX fixing rules above, fxFixing should ONLY appear on legs where notionalCurrency ≠ settlementCurrency. Is the placement correct?

---

RESPONSE FORMAT:

For EACH field, provide a JSON object with:
- confidence: 0-100 numeric score
  - 90-100 = Strong agreement (extracted value is definitely correct per instructions + contract)
  - 70-89 = Mild agreement (extracted value is probably correct)
  - 30-69 = Uncertain (cannot determine from contract or ambiguous)
  - 10-29 = Mild disagreement (extracted value is probably wrong)
  - 0-9 = Strong disagreement (extracted value is definitely wrong per instructions + contract)
- suggestedValue: What the value should be (null if agreeing, or string/object if disagreeing)
- evidence: Quote from contract supporting your assessment
- reasoning: Brief explanation referencing the original instructions

Return ONLY valid JSON in this exact format:
{
  "fieldValidations": [
    {
      "field": "legs[0].settlementType",
      "extractedValue": "CASH",
      "confidence": 95,
      "suggestedValue": null,
      "evidence": "...",
      "reasoning": "..."
    },
    ...
  ]
}

Return JSON only, no other text."""

        # ============================================================
        # CALL CLAUDE API
        # ============================================================

        print("Calling Claude API for cross-validation...")

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract response text
        response_text = response.content[0].text.strip()

        # Parse JSON (handle markdown code blocks)
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()

        claude_result = json.loads(response_text)

        # ============================================================
        # INJECT AUTOMATIC VALIDATIONS
        # ============================================================
        claude_result.setdefault("fieldValidations", [])

        # If we detected a settlement type error, inject it into Claude's validations
        if settlement_type_validation:
            claude_result["fieldValidations"].insert(0, settlement_type_validation)

        # Inject business day convention validations
        for bdc_validation in business_day_convention_validations:
            claude_result["fieldValidations"].insert(0, bdc_validation)

        # ============================================================
        # BUILD HUMAN-READABLE REPORT
        # ============================================================

        def confidence_to_label(conf):
            if conf >= 90:
                return "STRONG_AGREE"
            elif conf >= 70:
                return "MILD_AGREE"
            elif conf >= 30:
                return "UNCERTAIN"
            elif conf >= 10:
                return "MILD_DISAGREE"
            else:
                return "STRONG_DISAGREE"

        validations = claude_result.get("fieldValidations", [])

        # Count agreement levels
        strong_agree = sum(1 for v in validations if v.get("confidence", 0) >= 90)
        mild_agree = sum(1 for v in validations if 70 <= v.get("confidence", 0) < 90)
        uncertain = sum(1 for v in validations if 30 <= v.get("confidence", 0) < 70)
        mild_disagree = sum(1 for v in validations if 10 <= v.get("confidence", 0) < 30)
        strong_disagree = sum(1 for v in validations if v.get("confidence", 0) < 10)

        # Count double uncertainties (Gemini low confidence + Claude < 70)
        double_uncertainty_count = 0
        for field_info in fields_to_validate[:-1]:  # Exclude FX fixing
            matching_validation = next((v for v in validations if v.get("field") == field_info["field"]), None)
            if matching_validation and field_info["geminiConfidence"] == "low" and matching_validation.get("confidence", 100) < 70:
                double_uncertainty_count += 1

        # Overall assessment
        if strong_disagree > 0 or double_uncertainty_count > 0:
            overall_assessment = "NEEDS_REVIEW"
        elif mild_disagree > 0 or uncertain > 0:
            overall_assessment = "REVIEW_RECOMMENDED"
        else:
            overall_assessment = "PASSED"

        # Build report
        report = "=" * 60 + "\n"
        report += "CLAUDE CROSS-VALIDATION REPORT\n"
        report += "=" * 60 + "\n\n"

        report += f"Model: Claude Sonnet 4.5 (claude-sonnet-4-20250514)\n"
        report += f"Validation Method: Field-by-field with original prompt context\n"
        report += f"Fields Validated: {len(validations)}\n"
        report += f"Overall Assessment: {overall_assessment}\n\n"

        report += "VALIDATIONS:\n"
        report += "-" * 60 + "\n\n"

        # Show each validation
        for validation in validations:
            field = validation.get("field", "")
            extracted_value = validation.get("extractedValue", "")
            confidence = validation.get("confidence", 0)
            suggested_value = validation.get("suggestedValue")
            evidence = validation.get("evidence", "")
            reasoning = validation.get("reasoning", "")

            label = confidence_to_label(confidence)

            # Find Gemini confidence for this field
            gemini_conf = "N/A"
            for field_info in fields_to_validate:
                if field_info["field"] == field:
                    gemini_conf = field_info["geminiConfidence"]
                    break

            # Determine if double uncertainty
            is_double_uncertain = (gemini_conf == "low" and confidence < 70)

            # Icon based on agreement level
            if confidence >= 70:
                icon = "✓"
                status_text = f"{label} (confidence: {confidence})"
            elif confidence >= 30:
                icon = "?"
                status_text = f"{label} (confidence: {confidence})"
            else:
                icon = "✗"
                status_text = f"{label} (confidence: {confidence})"

            report += f"{icon} {status_text}\n"
            report += f"  Field: {field}\n"

            # Handle different value types
            if isinstance(extracted_value, (list, dict)):
                report += f"  Extracted Value: {json.dumps(extracted_value, indent=2)}\n"
            else:
                report += f"  Extracted Value: {extracted_value}\n"

            if suggested_value:
                if isinstance(suggested_value, (list, dict)):
                    report += f"  Claude's Suggested Value: {json.dumps(suggested_value, indent=2)}\n"
                else:
                    report += f"  Claude's Suggested Value: {suggested_value}\n"

            report += f"  Gemini Confidence: {gemini_conf}"
            if is_double_uncertain:
                report += " ⚠️⚠️ [BOTH MODELS UNCERTAIN]"
            report += "\n"

            # Wrap evidence text
            report += f"  Evidence: {evidence}\n"
            report += f"  Reasoning: {reasoning}\n"

            if confidence < 70:
                report += "  \n  ⚠️ MANUAL REVIEW REQUIRED\n"

            report += "\n"

        # Summary section
        report += "-" * 60 + "\n"
        report += "SUMMARY:\n"
        report += "-" * 60 + "\n"
        report += f"  ✓ Strong Agreements: {strong_agree}\n"
        report += f"  ✓ Mild Agreements: {mild_agree}\n"
        report += f"  ⚠ Uncertainties: {uncertain}\n"
        report += f"  ✗ Mild Disagreements: {mild_disagree}\n"
        report += f"  ✗ Strong Disagreements: {strong_disagree}\n"

        if double_uncertainty_count > 0:
            report += f"\n  🚨 Double Uncertainty Flags: {double_uncertainty_count}\n"
            report += f"     (Both Gemini AND Claude uncertain/disagreeing)\n"

        report += "\n"

        if strong_disagree > 0 or double_uncertainty_count > 0:
            review_count = strong_disagree + double_uncertainty_count
            report += f"ACTION REQUIRED:\n"
            report += f"------------------------------------------------------------\n"
            report += f"  ⚠️ {review_count} field(s) need HIGH PRIORITY manual review\n"
            if double_uncertainty_count > 0:
                report += f"  ⚠️ {double_uncertainty_count} field(s) flagged by both models\n"
        elif mild_disagree > 0 or uncertain > 0:
            report += f"ACTION RECOMMENDED:\n"
            report += f"------------------------------------------------------------\n"
            report += f"  ⚠️ Consider reviewing {mild_disagree + uncertain} field(s) with lower confidence\n"
        else:
            report += f"✓ ALL VALIDATIONS PASSED\n"
            report += f"✓ Claude confirms extraction quality is high\n"

        report += "\n" + "=" * 60

        # ============================================================
        # INTERACTIVE CORRECTION FOR STRONG DISAGREEMENTS
        # ============================================================

        # Store strong disagreements in global session variable for apply_corrections() to use
        global _session_pending_corrections
        strong_disagreements = [v for v in validations if v.get("confidence", 0) < 10]

        if strong_disagreements:
            # Store for later application
            _session_pending_corrections = strong_disagreements

            # Add interactive prompt section to report
            report += "\n\n" + "=" * 60 + "\n"
            report += "🚨 STRONG DISAGREEMENTS REQUIRE YOUR DECISION\n"
            report += "=" * 60 + "\n\n"
            report += f"Found {len(strong_disagreements)} field(s) with STRONG disagreement.\n"
            report += "Review each disagreement below and decide whether to apply Claude's correction.\n\n"

            for idx, disagreement in enumerate(strong_disagreements, 1):
                field = disagreement.get("field", "")
                extracted_value = disagreement.get("extractedValue", "")
                suggested_value = disagreement.get("suggestedValue")
                reasoning = disagreement.get("reasoning", "")

                report += f"DISAGREEMENT #{idx}:\n"
                report += f"  Field: {field}\n"
                report += f"  Current (Gemini): {extracted_value}\n"
                report += f"  Suggested (Claude): {suggested_value}\n"
                report += f"  Reasoning: {reasoning}\n\n"

            report += "=" * 60 + "\n"
            report += "TO APPLY CORRECTIONS:\n"
            report += "  Use: apply_corrections(\"field_index1,field_index2,...\" or \"all\" or \"none\")\n"
            report += f"  Example: apply_corrections(\"1,2\") to apply disagreements 1 and 2\n"
            report += f"  Example: apply_corrections(\"all\") to apply all {len(strong_disagreements)} corrections\n"
            report += f"  Example: apply_corrections(\"none\") to skip all corrections\n"
            report += "=" * 60
        else:
            _session_pending_corrections = []

        # ============================================================
        # SAVE REPORT TO FILE
        # ============================================================

        # Save to extraction_metadata folder if session date folder is set
        if _session_date_folder and _session_contract_name:
            try:
                metadata_dir = _session_date_folder / "extraction_metadata"
                metadata_dir.mkdir(parents=True, exist_ok=True)

                report_filename = f"{_session_contract_name}_cross_validation.txt"
                report_path = metadata_dir / report_filename

                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)

                report += f"\n\n✓ Cross-validation report saved to: {report_path}"
            except Exception as file_error:
                report += f"\n\n⚠ Warning: Could not save report to file: {str(file_error)}"

        return report

    except json.JSONDecodeError as e:
        return f"ERROR: Claude returned invalid JSON.\n\nParsing error: {str(e)}\n\nRaw response:\n{response_text[:500]}"
    except Exception as e:
        import traceback
        return f"ERROR during cross-validation: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


def apply_corrections(corrections_to_apply: str) -> str:
    """
    Applies corrections from cross_validate() based on user selection.

    Args:
        corrections_to_apply: Comma-separated indices (e.g., "1,3"), "all", or "none"

    Returns:
        Success message with details of applied corrections, or error if no pending corrections
    """
    global _session_pending_corrections, _session_merged_contract, _session_date_folder, _session_contract_name

    if not _session_pending_corrections:
        return "ERROR: No pending corrections found. Run cross_validate() first."

    if _session_merged_contract is None:
        return "ERROR: No extracted data in session."

    try:
        # Parse user input
        corrections_to_apply = corrections_to_apply.strip().lower()

        if corrections_to_apply == "none":
            count = len(_session_pending_corrections)
            _session_pending_corrections = []
            return f"✓ Skipped all {count} correction(s). No changes made."

        # Determine which corrections to apply
        if corrections_to_apply == "all":
            selected_corrections = list(range(len(_session_pending_corrections)))
        else:
            # Parse comma-separated indices
            try:
                selected_corrections = [int(idx.strip()) - 1 for idx in corrections_to_apply.split(",")]
                # Validate indices
                for idx in selected_corrections:
                    if idx < 0 or idx >= len(_session_pending_corrections):
                        return f"ERROR: Invalid index {idx + 1}. Valid range is 1-{len(_session_pending_corrections)}"
            except ValueError:
                return f"ERROR: Invalid format. Use comma-separated numbers (e.g., '1,2'), 'all', or 'none'"

        # Apply selected corrections
        corrections_applied = []

        for idx in selected_corrections:
            disagreement = _session_pending_corrections[idx]
            field = disagreement.get("field", "")
            extracted_value = disagreement.get("extractedValue", "")
            suggested_value = disagreement.get("suggestedValue")

            # Special handling for settlement type (apply to BOTH legs)
            if field == "legs[].settlementType":
                legs = _session_merged_contract.get("legs", [])
                if len(legs) >= 2:
                    # Apply the same settlement type to both legs
                    legs[0]["settlementType"] = suggested_value
                    legs[1]["settlementType"] = suggested_value
                    corrections_applied.append({
                        "field": field,
                        "oldValue": extracted_value,
                        "newValue": f"Set both legs to {suggested_value}"
                    })
                else:
                    return f"ERROR: Not enough legs to apply settlement type correction"
            # Special handling for fxFixing.placement (move fxFixing object between legs)
            elif field == "legs[].fxFixing.placement":
                legs = _session_merged_contract.get("legs", [])
                if len(legs) >= 2:
                    # Determine which leg should have fxFixing based on notional vs settlement currency
                    leg0_notional = legs[0].get("notionalCurrency", "")
                    leg0_settlement = legs[0].get("settlementCurrency", "")
                    leg1_notional = legs[1].get("notionalCurrency", "")
                    leg1_settlement = legs[1].get("settlementCurrency", "")

                    leg0_needs_fx = (leg0_notional != leg0_settlement)
                    leg1_needs_fx = (leg1_notional != leg1_settlement)

                    # Find which leg currently has fxFixing
                    fx_fixing_data = None
                    current_fx_leg = None
                    if "fxFixing" in legs[0]:
                        fx_fixing_data = legs[0]["fxFixing"]
                        current_fx_leg = 0
                    elif "fxFixing" in legs[1]:
                        fx_fixing_data = legs[1]["fxFixing"]
                        current_fx_leg = 1

                    # Apply correction
                    correction_made = False
                    if leg0_needs_fx and not leg1_needs_fx:
                        # Move fxFixing to leg 0
                        if current_fx_leg == 1:
                            legs[0]["fxFixing"] = fx_fixing_data
                            del legs[1]["fxFixing"]
                            corrections_applied.append({
                                "field": field,
                                "oldValue": "Leg 1 had fxFixing",
                                "newValue": "Moved to Leg 0"
                            })
                            correction_made = True
                    elif leg1_needs_fx and not leg0_needs_fx:
                        # Move fxFixing to leg 1
                        if current_fx_leg == 0:
                            legs[1]["fxFixing"] = fx_fixing_data
                            del legs[0]["fxFixing"]
                            corrections_applied.append({
                                "field": field,
                                "oldValue": "Leg 0 had fxFixing",
                                "newValue": "Moved to Leg 1"
                            })
                            correction_made = True

                    if not correction_made:
                        return f"ERROR: Could not determine correct fxFixing placement"
                else:
                    return f"ERROR: Not enough legs to apply fxFixing correction"
            else:
                # Standard field update for simple paths
                parts = field.replace('[', '.').replace(']', '').split('.')
                parts = [p for p in parts if p]

                # Navigate to the parent object
                current = _session_merged_contract
                for i, part in enumerate(parts[:-1]):
                    if part.isdigit():
                        current = current[int(part)]
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]

                # Set the new value
                final_key = parts[-1]
                current[final_key] = suggested_value
                corrections_applied.append({
                    "field": field,
                    "oldValue": extracted_value,
                    "newValue": suggested_value
                })

        # Save corrected data back to cdm_inputs file
        if _session_date_folder and _session_contract_name:
            cdm_inputs_dir = _session_date_folder / "cdm_inputs"
            output_path = cdm_inputs_dir / f"{_session_contract_name}.json"

            # Remove *Clear fields for clean output
            corrected_clean = _remove_clear_fields(_session_merged_contract)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(corrected_clean, f, indent=2, ensure_ascii=False)

            # Build success report
            result = "=" * 60 + "\n"
            result += f"✓ APPLIED {len(corrections_applied)} CORRECTION(S)\n"
            result += "=" * 60 + "\n\n"

            for correction in corrections_applied:
                result += f"Field: {correction['field']}\n"
                result += f"  Old Value: {correction['oldValue']}\n"
                result += f"  New Value: {correction['newValue']}\n\n"

            result += f"✓ Corrected data saved to: {output_path}\n"
            result += "=" * 60

            # Clear pending corrections
            _session_pending_corrections = []

            return result
        else:
            return "ERROR: Session folder not set. Cannot save corrections."

    except Exception as e:
        import traceback
        return f"ERROR applying corrections: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"


def match_with_mapped_trade() -> str:
    """
    Matches the current extracted contract with mapped trades from the CSV mapping output.

    Matching criteria (all must match exactly):
    - Counterparty name (party2.partyName)
    - Trade date
    - Termination date
    - For BOTH legs:
      - Notional amount
      - Notional currency
      - Payer party reference
      - Receiver party reference
      - Rate type (FIXED/FLOATING)

    If a unique match is found, adds "matchingTradeId" field to header with the tradeId from mapping.
    If no match found, sets "matchingTradeId": "No Match"
    If multiple matches found, sets "matchingTradeId": "Multiple Matches"

    Must be called AFTER:
    - load_mapped_trades() (to cache mapping data)
    - All extraction steps (to have complete contract data)

    Returns:
        Success message with match result
    """
    global _session_merged_contract, _session_mapped_trades

    # Validate session state
    if _session_merged_contract is None:
        return "ERROR: No contract data in session. Run extraction steps first."

    if _session_mapped_trades is None:
        return "ERROR: Mapped trades not loaded. Call load_mapped_trades() first."

    try:
        # Get contract data
        contract = _session_merged_contract
        contract_header = contract.get("header", {})
        contract_legs = contract.get("legs", [])

        if len(contract_legs) != 2:
            # Only match 2-leg swaps for now
            if "header" not in contract:
                contract["header"] = {}
            contract["header"]["matchingTradeId"] = "No Match"
            return "INFO: Contract does not have exactly 2 legs. Set matchingTradeId to 'No Match'."

        # Extract contract matching fields
        contract_party2 = contract_header.get("party2", {}).get("partyName", "")
        contract_trade_date = contract_header.get("tradeDate", {}).get("date", "")
        contract_term_date = contract_header.get("terminationDate", {}).get("date", "")

        # Prepare leg matching data
        contract_leg_data = []
        for leg in contract_legs:
            contract_leg_data.append({
                "notionalAmount": leg.get("notionalAmount"),
                "notionalCurrency": leg.get("notionalCurrency", ""),
                "payerPartyReference": leg.get("payerPartyReference", ""),
                "receiverPartyReference": leg.get("receiverPartyReference", ""),
                "rateType": leg.get("rateType", "")
            })

        # Search mapped trades for matches
        mapped_trades_list = _session_mapped_trades.get("trades", [])
        matches = []

        for mapped_trade in mapped_trades_list:
            mapped_header = mapped_trade.get("header", {})
            mapped_legs = mapped_trade.get("legs", [])

            # Check if this trade has 2 legs
            if len(mapped_legs) != 2:
                continue

            # Match header fields
            mapped_party2 = mapped_header.get("party2", {}).get("partyName", "")
            mapped_trade_date = mapped_header.get("tradeDate", {}).get("date", "")
            mapped_term_date = mapped_header.get("terminationDate", {}).get("date", "")

            if (contract_party2 != mapped_party2 or
                contract_trade_date != mapped_trade_date or
                contract_term_date != mapped_term_date):
                continue

            # Match legs (both legs must match in order)
            legs_match = True
            for i in range(2):
                contract_leg = contract_leg_data[i]
                mapped_leg = mapped_legs[i]

                if (contract_leg["notionalAmount"] != mapped_leg.get("notionalAmount") or
                    contract_leg["notionalCurrency"] != mapped_leg.get("notionalCurrency", "") or
                    contract_leg["payerPartyReference"] != mapped_leg.get("payerPartyReference", "") or
                    contract_leg["receiverPartyReference"] != mapped_leg.get("receiverPartyReference", "") or
                    contract_leg["rateType"] != mapped_leg.get("rateType", "")):
                    legs_match = False
                    break

            if legs_match:
                # Found a match!
                trade_id = mapped_header.get("tradeId", {})
                if isinstance(trade_id, dict):
                    trade_id_value = trade_id.get("id", "Unknown")
                else:
                    trade_id_value = str(trade_id)
                matches.append(trade_id_value)

        # Update contract with matching result
        if "header" not in contract:
            contract["header"] = {}

        if len(matches) == 0:
            contract["header"]["matchingTradeId"] = "No Match"
            return "INFO: No matching trade found in mapped data. Set matchingTradeId to 'No Match'."
        elif len(matches) == 1:
            contract["header"]["matchingTradeId"] = matches[0]
            return f"SUCCESS: Found unique match! Set matchingTradeId to '{matches[0]}'."
        else:
            contract["header"]["matchingTradeId"] = "Multiple Matches"
            return f"WARNING: Found {len(matches)} matching trades. Set matchingTradeId to 'Multiple Matches'."

    except Exception as e:
        return f"ERROR during matching: {str(e)}"


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
        "- run_cdm_generator(): Converts JSON to CDM format (call after write_consolidated_output)\n"
        "- run_pdf_report(): Generates PDF comparison report (call after run_cdm_generator)\n"
        "- resume_workflow(date, bank_name, start_from): Resume from specific step after manual fixes\n"
        "  start_from options: 'mapping', 'cdm_generator', 'pdf_report'\n"
        "\n"
        "**Session Management:**\n"
        "- list_contract_files(): Lists all *_anon.txt files in date folder\n"
        "- load_mapped_trades(): Loads mapped trades JSON into session (call after run_mapping_program)\n"
        "- clear_session(): Clears all session data - USE THIS BEFORE NEW CONTRACT!\n"
        "- read_contract_file(filename): Loads contract from date folder (just filename, not full path)\n"
        "- get_session_status(): Shows what's currently loaded in session\n"
        "- match_with_mapped_trade(): Matches contract with mapped trade, adds matchingTradeId to header\n"
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
        "**Validation Tools:**\n"
        "- validate_extraction(): Validates structural integrity (leg count, combinations, field presence)\n"
        "- cross_validate(): Cross-validates critical fields using Claude Sonnet 4.5\n"
        "  Validates: settlementType, settlementCurrency, fxFixing placement,\n"
        "  header/leg date business day conventions (tradeDate, effectiveDate, terminationDate)\n"
        "  Provides confidence scores and flags disagreements for manual review\n"
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
        "8. validate_extraction() → wait for response (checks structure)\n"
        "9. cross_validate() → wait for response (quality check with Claude)\n"
        "10. write_output_json('filename.json') → wait for response (use same base name as input)\n"
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
        "2. load_mapped_trades()\n"
        "   Loads the mapping output JSON into session for contract matching\n"
        "\n"
        "3. list_contract_files()\n"
        "   Shows all *_anon.txt files in the date folder\n"
        "\n"
        "4. For EACH contract file:\n"
        "   a. clear_session()\n"
        "   b. read_contract_file('filename_anon.txt')\n"
        "   c. extract_core_values()\n"
        "   d. extract_business_day_conventions()\n"
        "   e. extract_period_payment_data()\n"
        "   f. extract_fx_fixing()\n"
        "   g. extract_payment_date_offset()\n"
        "   h. validate_extraction() → show structural validation\n"
        "   i. cross_validate() → show Claude cross-validation\n"
        "   j. match_with_mapped_trade() → adds matchingTradeId to header\n"
        "   k. save_contract_to_batch()\n"
        "\n"
        "5. write_consolidated_output()\n"
        "   Writes ddmmyyyy_bancoabc_contracts.json to cdm_inputs folder (CDM ready)\n"
        "   Also writes debug version to extraction_metadata folder\n"
        "\n"
        "6. run_cdm_generator()\n"
        "   Converts JSON files to CDM format using Java JAR\n"
        "   Reads from cdm_inputs folder, writes to cdm_outputs folder\n"
        "\n"
        "7. run_pdf_report()\n"
        "   Generates PDF comparison report between Banco and Contract CDM outputs\n"
        "   Writes to reports folder\n"
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
        run_cdm_generator,
        run_pdf_report,
        resume_workflow,
        list_contract_files,
        load_mapped_trades,
        clear_session,
        read_contract_file,
        get_session_status,
        match_with_mapped_trade,
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
        cross_validate,
        apply_corrections,
        greet_user,
        calculate_sum
    ]
)

# Also export as 'agent' for backwards compatibility
agent = root_agent
