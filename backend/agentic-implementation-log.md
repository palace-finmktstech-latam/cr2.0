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

## Next Steps (After Step 2)

### Step 3: File I/O Tools
- Create ADK tools for reading contracts
- Create ADK tools for writing JSON output
- Test tools independently

### Step 4: Core Values Extraction + Caching
- Integrate `promptCoreValues.txt`
- Implement prompt caching on contract text
- Verify 90% cost reduction on cache hits

### Step 5: Sequential Agent Orchestration
- Build supervisor agent
- Orchestrate: read → extract → merge → write
- Test end-to-end with 2 extractions

### Step 6-8: Complete remaining steps per original plan
(See agentic-contract-reader.md for full plan)

---

## Reference Links

- **GCP Project Console:** https://console.cloud.google.com/home/dashboard?project=contract-reader-2-dev
- **Vertex AI Console:** https://console.cloud.google.com/vertex-ai?project=contract-reader-2-dev
- **Model Garden (Claude):** https://console.cloud.google.com/vertex-ai/publishers/anthropic?project=contract-reader-2-dev
- **Quotas:** https://console.cloud.google.com/iam-admin/quotas?project=contract-reader-2-dev
- **ADK Documentation:** https://google.github.io/adk-docs/

---

## Session Notes

### 2025-10-01 Session 1: GCP Setup & First Agent
- ✅ Initial GCP setup completed successfully
- ✅ Discovered Claude quota limitation, requested increase
- ✅ Pivoted to Gemini 2.0 Flash to maintain momentum
- ✅ Built and tested first ADK agent with tools
- ✅ Debugged ADK folder structure and variable naming
- ✅ Fixed location mismatch between .env and agent code
- ✅ Agent now working perfectly in `adk web` UI!

**Time invested:** ~3 hours
**Blockers removed:** Authentication, API enablement, model access, ADK configuration
**Current blocker:** Claude quota (workaround: Gemini working great)
**Momentum:** High - ready to build contract extraction tools!

---

**Last Updated:** 2025-10-01 (Steps 1-2 Complete)
