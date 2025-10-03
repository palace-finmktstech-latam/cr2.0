# Agentic Contract Reader - Complete Documentation

## Overview

This document describes an AI-powered contract extraction system built with Google ADK (Agent Development Kit) that processes Interest Rate Swap contracts and extracts structured data into JSON format.

The system uses **5 specialized extraction prompts** combined with:
- **Gemini 2.5 Pro** for contract extraction (with prompt caching - 75% cost savings)
- **Gemini 2.0 Flash** for agent orchestration
- **Session-based architecture** to avoid JSON parameter passing issues
- **Automatic leg ordering** to ensure data integrity across extractions

---

## Current Architecture (Production Ready)

### Integrated Processing Pipeline

The system now provides **end-to-end processing** combining CSV mapping and contract extraction:

**Complete Bank Processing Workflow:**
```
1. run_mapping_program(date, bank_name)  ← Processes CSV → banco JSON (trades)
2. list_contract_files()                 ← Discovers all *_anon.txt contracts
3. For each contract:
   - clear_session()                     ← Clears cache before new contract
   - read_contract_file(filename)        ← Loads contract into session
   - extract_core_values()               ← Extracts basic data, creates cache
   - extract_business_day_conventions()  ← Reuses cache (75% savings)
   - extract_period_payment_data()       ← Reuses cache (75% savings)
   - extract_fx_fixing()                 ← Reuses cache (75% savings)
   - extract_payment_date_offset()       ← Reuses cache (75% savings)
   - validate_extraction()               ← Validates quality & completeness
   - save_contract_to_batch()            ← Adds to consolidated output
4. write_consolidated_output()           ← Writes all contracts to JSON
```

**Output Files (all in date folder):**
- `ddmmyyyy_bancoabc_trades.json` - From CSV mapping (banco data)
- `ddmmyyyy_bancoabc_contracts.json` - From contract extraction (clean, no *Clear fields)
- `extraction_metadata/ddmmyyyy_bancoabc_contracts.json` - Debug version with *Clear fields

### Key Features

✅ **Integrated Pipeline** - Single command processes both CSV mapping and contract extraction
✅ **Bank Folder Structure** - Organized by bank and date for easy management
✅ **Prompt Caching** - Contract text cached once, reused 4x (75% cost reduction)
✅ **Session Storage** - All data stored in session variables to avoid JSON escaping issues
✅ **Auto-Merging** - Each extraction automatically merges into accumulating JSON
✅ **Leg Ordering** - Intelligent leg identification prevents data corruption
✅ **Validation Layer** - Comprehensive quality checks for structural integrity, completeness, and data quality
✅ **Clean + Debug Output** - Production-ready JSON + metadata version for quality analysis
✅ **Temperature: 0** - Maximum precision and consistency for extractions
✅ **Batch Processing** - Handles multiple contracts in one session

---

## Extraction Prompts & Schemas

### 1. Core Values Extraction (`promptCoreValues.txt`)

**Purpose:** Extracts fundamental contract data and identifies legs

**Key Innovation:** This extraction identifies each leg with:
- `legId` (Pata-Activa, Pata-Pasiva, etc.)
- `notionalCurrency` and `settlementCurrency`
- `payerPartyReference` and `receiverPartyReference`
- `rateType` (FIXED or FLOATING)

This leg identification data is stored in session and **injected into all subsequent extractions** to ensure correct leg ordering.

**Output Schema:**
```json
{
  "header": {
    "source": "contrato",
    "tradeDate": { "date": "DD/MM/YYYY" },
    "effectiveDate": { "date": "DD/MM/YYYY" },
    "terminationDate": { "date": "DD/MM/YYYY" },
    "party1": {
      "partyId": "ThisBank",
      "partyName": "Banco ABC"
    },
    "party2": {
      "partyId": "OurCounterparty",
      "partyName": "[EXTRACTED]"
    },
    "tradeId": { "id": "...", "idType": "INTERNAL" }
  },
  "legs": [
    {
      "legId": "Pata-Activa",
      "payerPartyReference": "OurCounterparty",
      "receiverPartyReference": "ThisBank",
      "notionalAmount": 0.00,
      "notionalCurrency": "CLP",
      "rateType": "FLOATING",
      "dayCountFraction": "ACT/360",
      "effectiveDate": { "date": "DD/MM/YYYY" },
      "terminationDate": { "date": "DD/MM/YYYY" },
      "settlementType": "CASH",
      "settlementCurrency": "USD",
      "floatingRateIndex": "CLP-ICP",
      "spread": 0.000000,
      "resetFrequency": "3M",
      "resetDayConvention": "MODFOLLOWING",
      "resetBusinessCenters": ["USNY", "CLSA"],
      "rateRoundingPrecision": 4,
      "rateRoundingDirection": "NEAREST"
    }
  ]
}
```

### 2. Business Day Conventions (`promptHeaderBusinessDayConventions.txt`)

**Purpose:** Extracts business day conventions and business centers for header dates only

**Leg Ordering:** Uses injected leg context to assign data to correct legs

**Note:** This prompt no longer extracts leg-level payment/period data (moved to prompt 3)

**Output Schema:**
```json
{
  "header": {
    "tradeDate": {
      "businessDayConvention": "MODFOLLOWING",
      "tradeDateBusinessDayConventionClear": true,
      "businessCenters": ["CLSA"],
      "tradeDateBusinessCentersClear": true
    },
    "effectiveDate": { /* same structure */ },
    "terminationDate": { /* same structure */ }
  },
  "legs": [
    {
      "effectiveDate": { /* same structure */ },
      "terminationDate": { /* same structure */ }
    }
  ]
}
```

### 3. Period/Payment Data (`promptPeriodEndAndPaymentBusinessDayConventions.txt`)

**Purpose:** Extracts payment and period end frequencies and conventions

**Output Schema (Flattened):**
```json
{
  "header": {},
  "legs": [
    {
      "paymentBusinessCenters": ["CLSA"],
      "paymentDayConvention": "MODFOLLOWING",
      "paymentDayConventionClear": true,
      "paymentFrequency": "6M",
      "paymentFrequencyClear": true,
      "calculationDayConvention": {
        "businessCenters": ["CLSA"],
        "businessDayConvention": "MODFOLLOWING",
        "calculationDayConventionClear": true
      },
      "calculationPeriodFrequency": "6M",
      "calculationPeriodFrequencyClear": true
    }
  ]
}
```

**Note:** paymentBusinessCenters is a flat array, not a nested object.

### 4. FX Fixing Data (`promptFXFixingData.txt`)

**Purpose:** Extracts FX fixing information for cross-currency legs

**Critical Logic:** Only extracts `fxFixing` for legs where `notionalCurrency ≠ settlementCurrency`

**How it works:**
1. Receives injected leg context showing both currencies for each leg
2. Compares notionalCurrency vs settlementCurrency
3. **Only includes `fxFixing` object** for legs that need currency conversion
4. Omits `fxFixing` entirely for legs where currencies match

**Example:**
- Leg 1: CLP → CLP: **NO** fxFixing
- Leg 2: CLF → CLP: **YES** fxFixing (requires UF conversion)

**Output Schema:**
```json
{
  "header": {},
  "legs": [
    {
      "fxFixing": {
        "fxFixingReference": "UAH_GFI_UAH01",
        "fxFixingOffset": 0,
        "fxFixingDayType": "BUSINESS",
        "dateRelativeTo": "PAYMENT_DATES",
        "fxFixingDayConvention": "MODFOLLOWING",
        "fxFixingBusinessCenters": ["CLSA"]
      }
    },
    {
      // No fxFixing - currencies match
    }
  ]
}
```

### 5. Payment Date Offset (`promptPaymentDateOffset.txt`)

**Purpose:** Calculates business days between period end date and payment date

**Complex Logic:**
- Analyzes cashflow tables
- Compares period end dates vs payment dates
- Calculates average offset if business day adjustments applied
- Default: 0 if dates match

**Output Schema:**
```json
{
  "header": { "source": "contrato" },
  "legs": [
    {
      "paymentDateOffset": 0,
      "paymentDateOffsetClear": true
    }
  ]
}
```

---

## Technical Architecture

### Session-Based Storage

**Problem Solved:** Large JSON strings passed as parameters between tool calls caused escaping errors in ADK.

**Solution:** Store all data in global session variables:

```python
_session_contract_text = None       # Original contract text
_session_leg_identifiers = None     # Leg IDs from Core Values
_session_merged_contract = None     # Accumulating merged JSON
_contract_cache = None              # Gemini API cache reference
```

### Leg Ordering System

**Problem:** Extraction tools returned legs in arbitrary order, causing silent data corruption when merging by array index.

**Solution - Hybrid Approach:**

1. **Extract leg identifiers** from Core Values:
```python
def extract_leg_identifiers(core_values_json_str):
    # Returns list of dicts with:
    # - legId, notionalCurrency, settlementCurrency
    # - rateType, payerPartyReference, receiverPartyReference
```

2. **Inject leg context** into subsequent extractions:
```
## KNOWN LEG INFORMATION FROM CORE VALUES EXTRACTION:

**Leg 1:**
- legId: Pata-Activa
- Notional Currency: CLP
- Settlement Currency: CLP
- Rate Type: FLOATING
- Payer: OurCounterparty
- Receiver: ThisBank

**Leg 2:**
- legId: Pata-Pasiva
- Notional Currency: CLF
- Settlement Currency: CLP
- Rate Type: FIXED
- Payer: ThisBank
- Receiver: OurCounterparty

**CRITICAL**: Order your output legs to match this exact sequence.
```

3. **Prompt instructions** tell AI to identify legs independently + use provided context for validation

### Automatic JSON Merging

Each extraction automatically merges into `_session_merged_contract`:

```python
def _deep_merge(base: dict, overlay: dict) -> dict:
    """
    Recursively merges overlay into base:
    - Dicts: merge keys recursively
    - Lists: merge by index (legs[0] + legs[0])
    - Other: overlay wins
    """
```

### Prompt Caching Flow

```
First extraction (extract_core_values):
  1. Create cache with contract text
  2. Pass system instruction separately
  3. Cache persists for 5 minutes

Subsequent extractions (2-5):
  1. Reuse existing cache
  2. Pass different system instruction
  3. 75% cost savings per extraction
```

---

## Tools Available

### Bank Processing

| Tool | Purpose | Parameters |
|------|---------|------------|
| `run_mapping_program(date, bank_name)` | Run CSV→JSON mapping (ALWAYS RUN FIRST) | `date`: dd/mm/yyyy<br>`bank_name`: BankNameCL |
| `list_contract_files()` | List all *_anon.txt in date folder | None (uses session folder) |

### Session Management

| Tool | Purpose | Parameters |
|------|---------|------------|
| `clear_session()` | Clear all session data | None |
| `read_contract_file(filename)` | Load contract from date folder | `filename` only (not full path) |
| `get_session_status()` | Show session state | None |
| `save_contract_to_batch()` | Save current contract to batch | None |
| `write_consolidated_output()` | Write all contracts to date folder | None (uses session) |
| `write_output_json(filename)` | Write individual contract (legacy) | `filename` |
| `query_contract_data(question)` | Ask questions about contract/data | `question` |
| `validate_extraction()` | Validate data quality & completeness | None |

### Extraction Tools

All extraction tools:
- Take **no parameters** (read from session)
- Return **status message** (not JSON)
- Automatically **merge results** into session
- **Reuse cache** for 75% cost savings

| Tool | Purpose |
|------|---------|
| `extract_core_values()` | Extract basic data + identify legs |
| `extract_business_day_conventions()` | Extract BDCs and centers |
| `extract_period_payment_data()` | Extract frequencies and conventions |
| `extract_fx_fixing()` | Extract FX fixing (conditional) |
| `extract_payment_date_offset()` | Calculate payment offset |

---

## Usage Examples

### Complete Bank Processing (Recommended Workflow)

```
User: "Process 25/09/2025 for BancoInternacionalCL"

Agent calls sequentially:

1. run_mapping_program("25/09/2025", "BancoInternacionalCL")
   → "SUCCESS: Mapping completed. CSV transformed to JSON.
      Output file created: 25092025_bancoabc_trades.json
      Ready to process contract files."

2. list_contract_files()
   → "Found 3 contract file(s) in date folder:
      1. contract_7559-61863_anon.txt
      2. contract_7559-61864_anon.txt
      3. contract_7559-61865_anon.txt"

3. For each contract:
   a. clear_session()
      → "SUCCESS: Session cleared"

   b. read_contract_file("contract_7559-61863_anon.txt")
      → "SUCCESS: Loaded contract 'contract_7559-61863_anon' with 45000 characters"

   c. extract_core_values()
      → "SUCCESS: Core values extracted and stored in session"

   d. extract_business_day_conventions()
      → "SUCCESS: Business day conventions extracted and merged"

   e. extract_period_payment_data()
      → "SUCCESS: Period/payment data extracted and merged"

   f. extract_fx_fixing()
      → "SUCCESS: FX fixing data extracted and merged"

   g. extract_payment_date_offset()
      → "SUCCESS: Payment date offset extracted and merged"

   h. validate_extraction()
      → "=== EXTRACTION QUALITY REPORT ===
         Quality: EXCELLENT (95% complete, 0 critical issues)
         ..."

   i. save_contract_to_batch()
      → "SUCCESS: Contract saved to batch (1 contracts total)"

4. write_consolidated_output()
   → "SUCCESS: Consolidated output written:
      - Clean version: C:\...\25092025\25092025_bancoabc_contracts.json
      - Debug version: C:\...\25092025\extraction_metadata\25092025_bancoabc_contracts.json
      - Total contracts: 3"
```

### Legacy Single Contract Extraction

```
User: "Extract all data from prompts/mycontract.txt"

Agent calls sequentially:
1. clear_session()
2. read_contract_file("prompts/mycontract.txt")
3. extract_core_values()
4. extract_business_day_conventions()
5. extract_period_payment_data()
6. extract_fx_fixing()
7. extract_payment_date_offset()
8. validate_extraction()
9. write_output_json("mycontract.json")
```

### Querying Extracted Data

```
User: "What is the fixed rate on the CLF leg?"

Agent: query_contract_data("What is the fixed rate on the CLF leg?")

Response: "The fixed rate is -0.0093 (-0.93%) on the Pata-Pasiva leg
(legId: Pata-Pasiva, notionalCurrency: CLF, settlementCurrency: CLP)"
```

### Follow-up Questions (Same Contract)

```
User: "Show me the FX fixing data"

Agent: query_contract_data("Show me the FX fixing data")

Response: "FX fixing data is present on Leg 2 (Pata-Pasiva):
- fxFixingReference: UAH_GFI_UAH01
- fxFixingOffset: 0 days
- dateRelativeTo: PAYMENT_DATES
- fxFixingDayConvention: MODFOLLOWING
- fxFixingBusinessCenters: [CLSA]

Leg 1 (Pata-Activa) does not have FX fixing because the notional
and settlement currencies are both CLP."
```

### Bank Folder Structure

The system uses an organized folder hierarchy:

```
C:\Users\bencl\OneDrive - palace.cl\Documents\Palace\Ideas\Contract Extraction\v2.0\Servicio\
├── BancoInternacionalCL\
│   ├── 25092025\                                    # Date folder (ddmmyyyy)
│   │   ├── contract_7559-61863_anon.txt            # Input contracts
│   │   ├── contract_7559-61864_anon.txt
│   │   ├── bank_trades_25092025_anon.csv           # Input CSV
│   │   ├── 25092025_bancoabc_trades.json           # Output: CSV mapping
│   │   ├── 25092025_bancoabc_contracts.json        # Output: Contract extraction (clean)
│   │   └── extraction_metadata\
│   │       └── 25092025_bancoabc_contracts.json    # Output: With *Clear fields (debug)
│   └── 26092025\
│       └── ...
└── BancoSantanderCL\
    └── ...
```

**Key Points:**
- Bank name must include two-letter country code (e.g., `BancoInternacionalCL`)
- Date folders use ddmmyyyy format (e.g., `25092025`)
- Input contracts must end with `*_anon.txt`
- Input CSV must end with `*_anon.csv`
- All output files use hardcoded `bancoabc` for anonymization
- Clean output (no *Clear fields) goes to date folder
- Debug output (with *Clear fields) goes to `extraction_metadata/` subfolder

---

## Key Implementation Details

### Temperature Setting

All extraction calls use `temperature: 0` for:
- **100% deterministic** outputs
- **Maximum precision** - no creativity
- **Consistent results** across runs

### Sequential Execution

Agent instructions explicitly require:
```
CRITICAL: Call ONE tool at a time. Wait for response before calling next tool.
DO NOT batch multiple tool calls together. Each step depends on previous step.
```

This prevents the orchestrator from batching all tools in parallel.

### Error Handling

- Cache expiration: Automatically creates fresh cache and retries
- JSON parsing errors: Returns error message with raw AI response
- Missing session data: Returns clear error asking to load contract first
- File not found: Returns error with expected path

---

## File Structure

```
backend/
├── mapping_program.py                             # CSV to JSON mapping (legacy, now tool)
├── contract_reader_config.yaml                    # Config for CSV mapping
├── prompts/                                       # Extraction prompts
│   ├── promptCoreValues.txt
│   ├── promptHeaderBusinessDayConventions.txt
│   ├── promptPeriodEndAndPaymentBusinessDayConventions.txt
│   ├── promptFXFixingData.txt
│   └── promptPaymentDateOffset.txt
├── agentic/
│   └── contract_reader_agent/
│       └── agent.py                               # Main agent (1900+ lines)
├── agentic-contract-reader.md                     # This file
└── agentic-implementation-log.md                  # Implementation history

# External folder structure (outside repo):
C:\Users\bencl\OneDrive - palace.cl\Documents\Palace\Ideas\Contract Extraction\v2.0\Servicio\
├── BancoInternacionalCL\
│   └── 25092025\
│       ├── *_anon.txt                            # Input contracts
│       ├── *_anon.csv                            # Input CSV
│       ├── 25092025_bancoabc_trades.json         # Output: Mapping
│       ├── 25092025_bancoabc_contracts.json      # Output: Extraction (clean)
│       └── extraction_metadata\
│           └── 25092025_bancoabc_contracts.json  # Output: Debug
└── contract_reader_config.yaml                    # Bank-specific config
```

---

## Cost Optimization

### Prompt Caching Savings

**Without caching:**
- 5 extractions × full contract tokens = 5× cost

**With caching:**
- 1× full contract (extract_core_values)
- 4× cached contract (75% discount) + new prompt tokens
- **Total savings: ~75% on contract tokens**

**Example for 40,000 token contract:**
- Without cache: 5 × 40,000 = 200,000 input tokens
- With cache: 40,000 + (4 × 10,000) = 80,000 effective tokens
- **Savings: 60% total cost reduction**

---

---

## Validation Layer

### Overview

The validation layer performs comprehensive quality checks on extracted contract data **before** writing the output JSON. It detects unusual structures, missing data, and potential extraction issues.

### Validation Types

**1. Structural Validation**
- **Leg Count Check**: Flags 1-leg or 3+ leg swaps (expected: 2 legs)
- **Leg Combinations**: Validates FIXED vs FLOATING, FLOATING vs FLOATING (flags FIXED vs FIXED as unusual)
- **Payer/Receiver Logic**: Detects invalid structures where both legs have same payer
- **Unusual Structures**: Reports contracts significantly different from expected Interest Rate Swaps

**2. Completeness Validation**
- Checks critical fields are populated (dates, parties, notionals, rates)
- Calculates completeness percentage
- Identifies missing required fields per leg type (FIXED needs `fixedRate`, FLOATING needs `floatingRateIndex`)

**3. Clarity Validation**
- Counts fields marked with `*Clear: false`
- Reports which extractions had ambiguous source data
- Helps identify contracts needing manual review

**4. Data Quality Validation**
- Negative notionals (suspicious)
- Missing rate types
- Invalid date formats
- Out-of-range values

**5. Consistency Validation**
- **FX Fixing Logic**: Verifies FX fixing only present when `notionalCurrency ≠ settlementCurrency`
- Reports legs missing FX fixing when currencies differ
- Reports legs with unnecessary FX fixing when currencies match

### Quality Scoring

| Score | Criteria | Meaning |
|-------|----------|---------|
| **EXCELLENT** | ≥90% complete, 0 critical issues, ≤3 warnings | High-quality extraction ready for production |
| **GOOD** | ≥75% complete, 0 critical issues, ≤3 warnings | Acceptable quality, minor gaps |
| **FAIR** | ≥60% complete, 0 critical issues | Usable but significant data missing |
| **POOR** | <60% complete OR critical issues OR structural issues | Requires manual review/re-extraction |

### Example Report

```
=== EXTRACTION QUALITY REPORT ===

Quality: EXCELLENT (95% complete, 0 critical issues)

## Structural Validation:
✓ Structure: 2-leg swap
✓ Leg combination: FIXED vs FLOATING (expected)
✓ Payer/receiver relationships valid

## Completeness: 95% (19/20 critical fields)
✓ Header: All critical fields present
✓ Leg 1 (Pata-Activa): 9/10 fields (missing: resetRelativeTo)
✓ Leg 2 (Pata-Pasiva): 10/10 fields

## Clarity: 3 fields marked unclear
⚠ tradeDate businessDayConvention unclear
⚠ effectiveDate businessCenters unclear
⚠ Leg 2 periodEndDates businessCenters unclear

## Data Quality:
✓ All notionals positive
✓ All rate types present
✓ No suspicious values detected

## Consistency Checks:
✓ FX Fixing Logic: Correct
  - Leg 1: No FX fixing (CLP→CLP, same currency) ✓
  - Leg 2: Has FX fixing (CLF→CLP, different currencies) ✓

=====================================
```

### Usage in Workflow

The validation step is **automatic** in the standard extraction workflow:

```
7. extract_payment_date_offset()
8. validate_extraction()          ← Automatic quality check
9. write_output_json()             ← Proceed if quality acceptable
```

If validation reports **POOR** quality or critical issues, review the report before using the output JSON.

---

## Future Enhancements (Not Yet Implemented)

- [ ] Parallel execution of extractions 2-5 (all depend on Core Values only)
- [ ] Language detection (EN vs ES) with language-specific prompts
- [ ] Human-readable summary generation
- [ ] Instance-based architecture for true parallel processing (multiple contracts simultaneously)
- [ ] Async batch processing with progress tracking
- [ ] GCP bucket integration (replace local file paths with cloud storage URLs)
- [ ] Automated matching/merging of CSV trades with contract extractions
- [ ] CDM format conversion integration

---

## Troubleshooting

### "Malformed function call" Error
**Cause:** Orchestrator trying to batch multiple tool calls
**Fix:** Updated agent instructions to require sequential execution

### Legs in Wrong Order
**Cause:** AI returned legs in different order than Core Values
**Fix:** Leg context injection + prompt instructions ensure ordering

### FX Fixing on Wrong Leg
**Cause:** Settlement currency not included in leg context
**Fix:** Added settlementCurrency to leg identifiers, updated prompt logic

### Session Data Not Found
**Cause:** Forgot to call `read_contract_file()` or `clear_session()` cleared it
**Fix:** Always start new contract with: clear_session() → read_contract_file()

### Mapping Program Reports Error But File Created
**Cause:** Python logging output to stderr interpreted as failure
**Fix:** Check both stdout/stderr for success indicators + verify output file exists

### Business Centers Wrong Enum (e.g., "Santiago" instead of "CLSA")
**Cause:** Prompt didn't include enum mapping for business centers
**Fix:** Added business center pattern mapping at top of period/payment prompt

### Nested paymentBusinessCenters Object
**Cause:** Prompt schema showed nested structure, downstream expects flat array
**Fix:** Updated prompt schema to show flat array: `"paymentBusinessCenters": ["CLSA"]`

---

## Version History

- **v1.0** - MVP with 4 extractions, manual JSON merging
- **v2.0** - Added prompt caching, auto-merging, session storage
- **v2.1** - Added leg ordering system, FX fixing conditional logic
- **v2.2** - Added payment date offset extraction
- **v2.3** - Added query tool, clear_session, sequential execution enforcement
- **v2.4** - Temperature: 0, comprehensive documentation
- **v2.5** - Added validation layer with quality scoring and structural checks
- **v2.6** - Added batch processing for multiple contracts with automatic naming
- **v3.0** (Current) - **Integrated Pipeline**
  - CSV mapping integrated as agent tool (`run_mapping_program`)
  - Bank folder structure for organized processing
  - Session-based folder management
  - Clean + debug output files (with/without *Clear fields)
  - Consolidated output format (all contracts in single JSON)
  - Simplified CLI (date + bank name only)
  - Hardcoded anonymization (always outputs "bancoabc")
  - Flattened JSON structure for downstream compatibility
  - Enhanced error handling for subprocess outputs

---

## Contact & Support

For issues or questions about this system, refer to:
- Implementation log: `agentic-implementation-log.md`
- Feedback/issues: `feedback.md`
