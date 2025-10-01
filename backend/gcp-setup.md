# Google Cloud Platform Setup for Contract Reader Agent

## Project Information
- **Organization:** palace.cl
- **Project ID:** contract-reader-2-dev
- **Purpose:** Deploy ADK-based contract extraction agent with Claude on Vertex AI

---

## Step 1: Verify Google Cloud CLI Installation

First, let's verify that `gcloud` CLI is installed and updated.

### Commands to Run:

```bash
# Check if gcloud is installed
gcloud --version

# Update to latest version (if needed)
gcloud components update
```

**What to expect:**
- Should show gcloud version (e.g., Google Cloud SDK 500.0.0)
- Should show `gsutil`, `bq`, and other components

**Status:** ✅ Complete
- **Confirmed:** Google Cloud SDK 526.0.1
- **Components:** bq 2.1.18, core 2025.06.10, gsutil 5.34, gcloud-crc32c 1.0.0

---

## Step 2: Authenticate with Google Cloud

### Commands to Run:

```bash
# Login to your Google Cloud account
gcloud auth login

# Set up Application Default Credentials (required for ADK)
gcloud auth application-default login
```

**What happens:**
1. First command opens browser for account login
2. Second command opens browser again for ADC setup
3. Both will save credentials locally

**Why we need both:**
- `gcloud auth login`: For gcloud CLI commands
- `gcloud auth application-default login`: For Python ADK SDK to access Vertex AI

**Status:** ✅ Complete (Both authentications done)
- **Authenticated as:** ben.clark@palace.cl
- **ADC saved to:** `C:\Users\bencl\AppData\Roaming\gcloud\application_default_credentials.json`
- **Quota project:** ccm-dev-pool (will change to contract-reader-2-dev in Step 3)

---

## Step 3: Set Your Default Project

### Commands to Run:

```bash
# Set the active project
gcloud config set project contract-reader-2-dev

# Verify the project is set
gcloud config get-value project

# Get project details
gcloud projects describe contract-reader-2-dev
```

**What to expect:**
- Should confirm project is set to `contract-reader-2-dev`
- Should show project details including organization info

**Status:** ✅ Complete
- **Project ID:** contract-reader-2-dev
- **Project Number:** 857991264119
- **Organization ID:** 165254678508 (palace.cl)
- **Lifecycle State:** ACTIVE
- **Created:** 2025-09-25

✅ **Quota project updated** to contract-reader-2-dev
- All API calls from Python/ADK will now be billed to contract-reader-2-dev

---

## Step 4: Enable Required APIs

We need to enable several Google Cloud APIs for Vertex AI and Claude models.

### Commands to Run:

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Compute Engine API (sometimes required)
gcloud services enable compute.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled | grep -E '(aiplatform|compute)'
```

**What to expect:**
- Each enable command takes 30-60 seconds
- List command should show both APIs as ENABLED

**Status:** ✅ Complete
- **aiplatform.googleapis.com** - ENABLED ✓
- **compute.googleapis.com** - ENABLED ✓

---

## Step 5: Verify Claude Model Access

Check if you have access to Claude models in Vertex AI Model Garden.

### Commands to Run:

```bash
# List available models in Vertex AI (this might not show Claude directly)
gcloud ai models list --region=us-east5

# Alternative: Check via Python (we'll create a test script)
```

**Note:** Claude models might not appear in the gcloud list. We'll verify access by testing in the next steps.

**Status:** ✅ Complete
- **Vertex AI endpoint:** https://us-east5-aiplatform.googleapis.com/
- **Listed models:** 0 (expected - Claude partner models don't show here)
- **Connection:** Working ✓

Claude models are accessed as "partner models" through Vertex AI and won't appear in the standard model list. We'll verify actual Claude access with a Python test script in Step 8.

---

## Step 6: Set Environment Variables

Create a `.env` file in your backend directory with GCP configuration.

### Create file: `backend/.env`

Add the following content:

```bash
# Google Cloud Configuration
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=contract-reader-2-dev
GOOGLE_CLOUD_LOCATION=us-east5

# Note: us-east5 is where Claude models are available
# Other Claude-supported regions: us-central1, europe-west1

# Anthropic API Key (backup for testing)
ANTHROPIC_API_KEY=your_existing_api_key_here
```

**Manual steps:**
1. Create this file in `C:\Users\bencl\Proyectos\cr2.0\backend\.env`
2. Replace `your_existing_api_key_here` with your actual Anthropic API key (if you have one)

**Status:** ✅ Complete
- `.env` file created with GCP configuration
- **Note:** ANTHROPIC_API_KEY removed from .env (using system environment variable instead)

---

## Step 7: Install Python Dependencies

### Commands to Run (in your backend directory):

```bash
cd C:\Users\bencl\Proyectos\cr2.0\backend
venv\Scripts\activate
pip install google-adk python-dotenv
```

**What this installs:**
- `google-adk`: Agent Development Kit
- `python-dotenv`: To load .env file

**Status:** ✅ Complete
- **google-adk:** 1.15.1 installed
- **python-dotenv:** 1.1.1 installed
- **All dependencies:** Resolved successfully
- Installed via `pip install -r requirements.txt`

---

## Step 8: Test GCP Connection

We'll create a simple test script to verify everything works.

**Status:** ✅ Complete - Using Gemini 2.0 Flash (Claude quota pending)

**Test Results:**
- ✅ Environment variables loaded
- ✅ ADC authentication working
- ✅ Vertex AI initialized successfully
- ✅ **Gemini 2.0 Flash working perfectly**
- ⏳ Claude Sonnet 4.5: Quota requested, awaiting approval

**Resolution:**
- Using Gemini 2.0 Flash for development
- Claude quota request submitted to Google
- Agent architecture is model-agnostic - can switch to Claude later with 1 line change

---

## Summary Checklist

Before proceeding, verify:
- [x] gcloud CLI installed and updated
- [x] Authenticated with `gcloud auth login`
- [x] Application Default Credentials set up
- [x] Project set to `contract-reader-2-dev`
- [x] Vertex AI API enabled
- [x] `.env` file created with correct values
- [x] google-adk installed in venv

---

## Troubleshooting

### Issue: "gcloud: command not found"
**Solution:** Install Google Cloud SDK from https://cloud.google.com/sdk/docs/install

### Issue: "Permission denied" errors
**Solution:** Make sure your Google account has appropriate roles:
- Vertex AI User
- Service Account User
- Or Project Editor/Owner

### Issue: "API not enabled"
**Solution:** Run the enable commands in Step 4 again and wait for completion

---

## Next Steps

Once all steps above are complete, we'll:
1. Create a test script to verify Claude access on Vertex AI
2. Build the Hello World ADK agent
3. Test with `adk web` visual UI

---

**Last Updated:** 2025-10-01
**Status:** Setup in progress
