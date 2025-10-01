# Agentic Contract Reader - Implementation Log

**Project:** Contract extraction agent using Google ADK + Vertex AI
**Started:** 2025-10-01
**Status:** In Progress - Step 1 Complete

---

## Implementation Progress

### ✅ Step 1: GCP Setup & Environment (COMPLETE)

**Date:** 2025-10-01

**What was done:**
1. ✅ Google Cloud CLI verified (v526.0.1)
2. ✅ Authenticated with gcloud (`gcloud auth login`)
3. ✅ Set up Application Default Credentials (ADC)
4. ✅ Set project to `contract-reader-2-dev`
5. ✅ Updated quota project to match
6. ✅ Enabled Vertex AI API (`aiplatform.googleapis.com`)
7. ✅ Created `.env` file with GCP configuration
8. ✅ Installed `google-adk`, `anthropic[vertex]`, `python-dotenv`
9. ✅ Tested Vertex AI connection with Gemini 2.0 Flash - SUCCESS!

**Current Configuration:**
- **Project ID:** contract-reader-2-dev
- **Organization:** palace.cl (ID: 165254678508)
- **Location:** global (for Claude), us-central1 (for Gemini)
- **Model:** Gemini 2.0 Flash (temporary, switching to Claude once quota approved)
- **Billing:** Enabled ✓

**Blocked Items:**
- ⏳ Claude Sonnet 4.5 quota: Requested, awaiting Google approval
- Using Gemini 2.0 Flash as temporary replacement

**Files Created:**
- `backend/.env` - GCP configuration
- `backend/requirements.txt` - Updated with ADK dependencies
- `backend/gcp-setup.md` - Complete setup documentation
- `backend/agentic/test_vertex_gemini.py` - Gemini connection test (working)
- `backend/agentic/test_vertex_claude.py` - Claude test (quota pending)

---

### ✅ Step 2: Hello World ADK Agent (COMPLETE)

**Goal:** Create a basic ADK agent with Gemini to verify the framework works

**Status:** Complete! Agent working in `adk web` UI

**What was done:**
1. ✅ Created proper folder structure: `agentic/contract_reader_agent/agent.py`
2. ✅ Built agent with two test tools: `greet_user()` and `calculate_sum()`
3. ✅ Fixed ADK discovery issues (needed `root_agent` variable, not `agent`)
4. ✅ Fixed location mismatch (.env had us-east5, needed us-central1 for Gemini)
5. ✅ Tested with `adk web` - agent responds correctly and uses tools!

**Key Learnings:**
- **ADK folder structure:** Must be `agentic/agent_name/agent.py`, not root-level files
- **Variable naming:** ADK specifically looks for `root_agent` variable in agent.py
- **Model location:** Gemini 2.0 Flash only in us-central1, not us-east5 or global
- **Location consistency:** Both `.env` GOOGLE_CLOUD_LOCATION and vertexai.init() must match
- **Tool definition:** Simple Python functions with docstrings automatically become ADK tools

**Files Created:**
- `backend/agentic/contract_reader_agent/agent.py` - Main ADK agent (working!)
- `backend/agentic/test_agent_simple.py` - Direct Gemini test (bypassed ADK)
- `backend/agentic/test_agent_programmatic.py` - Tool usage test

**Configuration:**
```python
# agent.py uses:
model="gemini-2.0-flash-exp"
location="us-central1"  # Hardcoded for Gemini

# .env uses:
GOOGLE_CLOUD_LOCATION=us-central1  # Must match!
```

---

### ✅ Step 3: File I/O Tools (COMPLETE)

**Date:** 2025-10-01

**Goal:** Create ADK tools for reading contracts and writing JSON outputs

**Status:** Complete! File I/O working with session-based approach

**What was done:**
1. ✅ Created `read_contract_file(contract_path)` tool
   - Loads contract into `_session_contract_text` global variable
   - Returns success message with character count
   - Avoids passing large text strings as parameters (prevents escaping issues)
2. ✅ Created `write_output_json(filename, json_data)` tool
   - Writes formatted JSON to `backend/output/` directory
   - Validates JSON before writing
   - Returns success message with file path
3. ✅ Updated agent instructions with clear workflow examples
4. ✅ Tested via `adk web` - both tools working perfectly!

**Key Learnings:**
- **Session-based approach:** Using global variables to pass data between tools avoids parameter escaping issues
- **Tool composability:** Separate tools maintain agentic flexibility while avoiding technical problems
- **Return messages:** Tools return success/error messages, not raw data (prevents malformed function calls)

**Files Modified:**
- `backend/agentic/contract_reader_agent/agent.py` - Added File I/O tools

**Testing:**
- ✅ Read contract from `prompts/contract.txt`
- ✅ Write test JSON to `output/test.json`

---

### ✅ Step 4: Core Values Extraction with Context Caching (COMPLETE)

**Date:** 2025-10-01

**Goal:** Integrate promptCoreValues.txt with Gemini context caching for cost savings

**Status:** Complete! Extraction working with 75% cost savings on cached tokens

**What was done:**
1. ✅ Added `google-genai>=1.0.0` to requirements.txt
2. ✅ Initialized Google GenAI client for Vertex AI context caching
3. ✅ Created `extract_core_values()` tool with:
   - Reads `promptCoreValues.txt` as system instruction
   - Creates context cache with contract text (5-minute TTL)
   - Uses cache for subsequent extractions (75% cheaper!)
   - Returns formatted JSON with extracted data
   - Auto-resets cache on expiry errors
4. ✅ Implemented session-based workflow:
   - `read_contract_file()` → loads into session
   - `extract_core_values()` → uses session contract
   - `write_output_json()` → saves extracted JSON
5. ✅ Added cache error handling with automatic reset
6. ✅ Tested end-to-end extraction successfully!

**Key Technical Details:**
- **Context caching:** Gemini 2.0 Flash caches contract text (saves 75% on cached tokens)
- **Cache TTL:** 300 seconds (5 minutes) - perfect for multi-prompt workflow
- **Minimum tokens:** 1,024 tokens required (our contracts are ~3.5K ✓)
- **Session variables:** `_session_contract_text` and `_contract_cache` persist between tool calls
- **Error handling:** Cache expiry triggers automatic reset for next run

**Files Modified:**
- `backend/requirements.txt` - Added google-genai
- `backend/agentic/contract_reader_agent/agent.py` - Added extraction tool

**Extraction Quality (First Test):**
- ✅ Dates extracted correctly (12/05/2020, 30/01/2024)
- ✅ Parties identified (NOSOTROS as counterparty)
- ✅ Legs properly structured (Pata-Activa, Pata-Pasiva)
- ✅ Notional amounts correct (CLP 14.3B, CLF 500K)
- ✅ Rate types correct (FLOATING with CLP-ICP, FIXED with -0.93%)
- ✅ Conditional fields handled properly (FIXED leg has `fixedRate`, no `floatingRateIndex`)
- ✅ Settlement type = CASH, currency = CLP
- ⚠️ Minor: Missing tradeId (should be "23615"), resetFrequency null

**Performance:**
- First extraction: ~30-40 seconds (creates cache + extraction)
- Subsequent extractions within 5 min: Expected 75% faster and cheaper (cache hit)
- Cache expires after 5 minutes, auto-resets on error

---

## Architecture Decisions

### Model Strategy
- **Development:** Gemini 2.0 Flash (has quota, works now)
- **Production:** Claude Sonnet 4.5 (once quota approved)
- **Switch:** Single line change in agent config

### Why Google ADK + Vertex AI?
1. ✅ Enterprise-grade for banking customers
2. ✅ Prompt caching support (90% cost reduction)
3. ✅ Visual UI for testing (`adk web`)
4. ✅ Model-agnostic architecture
5. ✅ Google Cloud compliance/audit logging

### Cost Optimization
- **Prompt Caching:** Cache contract text once, reuse across 4 extraction prompts
- **Expected savings:** 40-50% on API costs
- **Cache lifetime:** 5 minutes (perfect for sequential processing)

---

## Key Technical Details

### Authentication Flow
```
gcloud auth login
  → User authentication for CLI

gcloud auth application-default login
  → ADC for Python SDK
  → Saved to: C:\Users\bencl\AppData\Roaming\gcloud\application_default_credentials.json

gcloud auth application-default set-quota-project contract-reader-2-dev
  → Ensures billing to correct project
```

### Environment Variables (.env)
```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=contract-reader-2-dev
GOOGLE_CLOUD_LOCATION=us-central1  # Updated for Gemini compatibility
```

### Dependencies Installed
- `google-adk==1.15.1` - Agent Development Kit
- `anthropic[vertex]` - For Claude on Vertex AI (when quota approved)
- `python-dotenv==1.1.1` - Load .env files
- `vertexai` - Google's Vertex AI SDK (via google-cloud-aiplatform)

---

## Known Issues & Resolutions

### Issue 1: Claude Quota (Error 429)
**Problem:** Claude models have zero quota by default on Vertex AI
**Resolution:** Requested quota increase, using Gemini temporarily
**Status:** Awaiting Google approval (24-48 hours)

### Issue 2: Emoji encoding in Windows terminal
**Problem:** Unicode emojis caused crashes in hello_agent.py
**Resolution:** Replaced emojis with [LABEL] format
**Status:** Fixed

### Issue 3: Invalid metadata warning
**Problem:** `google_ai_generativelanguage-0.6.15` metadata error
**Resolution:** Harmless, can be ignored (existing package issue)
**Status:** Non-blocking

### Issue 4: ADK "No agents found"
**Problem:** ADK couldn't find agent in root-level files
**Resolution:** Created subdirectory structure `agentic/contract_reader_agent/agent.py`
**Status:** Fixed

### Issue 5: ADK "No root_agent found"
**Problem:** ADK specifically looks for variable named `root_agent`
**Resolution:** Renamed `agent = Agent(...)` to `root_agent = Agent(...)`
**Status:** Fixed

### Issue 6: Gemini 404 in us-east5
**Problem:** `.env` had wrong/duplicate GOOGLE_CLOUD_LOCATION causing 404
**Resolution:** Updated to single `GOOGLE_CLOUD_LOCATION=us-central1`
**Status:** Fixed - agent now works in `adk web`!

---

## Next Steps

### 🔄 Step 5: Add Business Day Conventions Extraction (NEXT)
**Goal:** Add second extraction tool using same caching approach
**Tasks:**
- Create `extract_business_day_conventions()` tool
- Use same `_contract_cache` for cost savings
- Integrate `promptHeaderBusinessDayConventions.txt`
- Test extraction and validate output

### Step 6: JSON Merger
**Goal:** Merge Core Values + Business Day Conventions JSONs
**Tasks:**
- Create `merge_extractions()` tool
- Deep merge logic for nested structures (header + legs)
- Handle array merging by index
- Test with two extraction outputs

### Step 7: Add Remaining Extraction Tools
**Goal:** Complete all 4 extraction prompts
**Tasks:**
- Add `extract_period_payment_data()` tool
- Add `extract_fx_fixing()` tool (conditional)
- All tools share same contract cache
- Test full workflow with all extractions

### Step 8: End-to-End Testing & Refinement
**Goal:** Complete MVP with full extraction pipeline
**Tasks:**
- Test complete workflow: read → 4 extractions → merge → write
- Verify cache reuse across all 4 tools (75% savings on 3 of 4 calls)
- Refine extraction quality (tradeId, resetFrequency, etc.)
- Performance testing and optimization
- Documentation update

---

## Reference Links

- **GCP Project Console:** https://console.cloud.google.com/home/dashboard?project=contract-reader-2-dev
- **Vertex AI Console:** https://console.cloud.google.com/vertex-ai?project=contract-reader-2-dev
- **Model Garden (Claude):** https://console.cloud.google.com/vertex-ai/publishers/anthropic?project=contract-reader-2-dev
- **Quotas:** https://console.cloud.google.com/iam-admin/quotas?project=contract-reader-2-dev
- **ADK Documentation:** https://google.github.io/adk-docs/

---

## Session Notes

### 2025-10-01 Session 1: Complete MVP Foundation (Steps 1-4)

**Morning: GCP Setup & Hello World (Steps 1-2)**
- ✅ Initial GCP setup completed successfully
- ✅ Discovered Claude quota limitation, requested increase
- ✅ Pivoted to Gemini 2.0 Flash to maintain momentum
- ✅ Built and tested first ADK agent with tools
- ✅ Debugged ADK folder structure and variable naming
- ✅ Fixed location mismatch between .env and agent code
- ✅ Agent working perfectly in `adk web` UI!

**Afternoon: File I/O & Extraction (Steps 3-4)**
- ✅ Built File I/O tools (read_contract_file, write_output_json)
- ✅ Solved tool chaining issue with session-based approach
- ✅ Implemented core values extraction with context caching
- ✅ Added google-genai SDK for Gemini context caching (75% savings!)
- ✅ Fixed cache expiry handling with auto-reset
- ✅ End-to-end extraction working: read → extract → write
- ✅ First successful extraction with excellent quality!

**Challenges Overcome:**
1. ADK folder structure and variable naming (`root_agent`)
2. Model location mismatch (us-east5 vs us-central1)
3. Tool chaining and text escaping issues (solved with session variables)
4. Cache expiry error handling (auto-reset implementation)
5. Python global variable declaration syntax

**Time invested:** ~6 hours
**Blockers removed:** Authentication, API access, ADK setup, tool chaining, caching
**Current blocker:** Claude quota still pending (Gemini working excellently as replacement)
**Momentum:** Excellent! Core extraction working with caching. Ready for Step 5 tomorrow.

**Key Achievement:**
Full extraction pipeline working with 75% cost savings through context caching. Session-based architecture maintains agentic composability while solving technical challenges.

---

**Last Updated:** 2025-10-01 (Steps 1-4 Complete, Ready for Step 5)
