I've built four different prompts (in the backend/prompts directory) that in conjunction can run to extract all of the relevant data that I need from Interest Rate Swap contracts. The four prompts generate JSON outputs that have the following formats:

1) promptCoreValues.txt - extracts the simplest, most basic points from the contract, so it's not particularly specialised.

JSON output:

{
    "header": {
        "source": "contract",
        "tradeDate": {
            "date": "DD/MM/YYYY"
        },
        "effectiveDate": {
            "date": "DD/MM/YYYY"
        },
        "terminationDate": {
            "date": "DD/MM/YYYY"
        },
        "party1": {
            "partyId": "ThisBank",
            "partyName": "Banco ABC"
        },
        "party2": {
            "partyId": "OurCounterparty",
            "partyName": "[EXTRACTED_COUNTERPARTY_NAME]"
        }
    },
    "legs": [
        {
            "legId": "[Pata-Activa|Pata-Pasiva|Leg1]",
            "payerPartyReference": "[ThisBank|OurCounterparty|null]",
            "receiverPartyReference": "[ThisBank|OurCounterparty|null]",
            "notionalAmount": 0.00,
            "notionalCurrency": "CLP",
            "rateType": "[FIXED|FLOATING]",
            "dayCountFraction": "[ACT/360|ACT/365|30/360|etc]",
            "effectiveDate": {
                "date": "DD/MM/YYYY"
            },
            "terminationDate": {
                "date": "DD/MM/YYYY"
            },
            "settlementType": "[CASH|PHYSICAL]",
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

2) promptHeaderBusinessDayConventions.txt - extracts the business day convention and business centres for the trade date, effective date, and termination dates (both in the header and in the legs).

JSON output:

{
    "header": {
        "tradeDate": {
            "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
            "tradeDateBusinessDayConventionClear": "[true|false]",
            "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
            "tradeDateBusinessCentersClear": "[true|false]"
        },
        "effectiveDate": {
            "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]", 
            "effectiveDateBusinessDayConventionClear": "[true|false]",
            "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
            "effectiveDateBusinessCentersClear": "[true|false]"
        },
        "terminationDate": {
            "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
            "terminationDateBusinessDayConventionClear": "[true|false]",
            "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
            "terminationDateBusinessCentersClear": "[true|false]"
        }
    },
    "legs": [
        {
            "effectiveDate": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "effectiveDateBusinessDayConventionClear": "[true|false]",
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "effectiveDateBusinessCentersClear": "[true|false]"
            },
            "terminationDate": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "terminationDateBusinessDayConventionClear": "[true|false]",
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "terminationDateBusinessCentersClear": "[true|false]"
            },
            "paymentDates": {
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "paymentDatesBusinessCentersClear": "[true|false]"
            },
            "periodEndDates": {
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "periodEndDatesBusinessCentersClear": "[true|false]"
            }
        },
        {
            "effectiveDate": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "effectiveDateBusinessDayConventionClear": "[true|false]",
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "effectiveDateBusinessCentersClear": "[true|false]"
            },
            "terminationDate": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "terminationDateBusinessDayConventionClear": "[true|false]",
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "terminationDateBusinessCentersClear": "[true|false]"
            },
            "paymentDates": {
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "paymentDatesBusinessCentersClear": "[true|false]"
            },
            "periodEndDates": {
                "businessCenters": ["[USNY|CLSA|USGS|GBLO|JPTO|EUTA|CATO|AUSY|HKHK|CHZU]"],
                "periodEndDatesBusinessCentersClear": "[true|false]"
            }
        }
    ]
}

3) promptPeriodEndAndPaymentBusinessDayConventions.txt - extracts the business day convention and the frequency for both the payment dates and the period end dates of the legs.

JSON output:

{
    "header": {
        
    },
    "legs": [
        {
            "paymentDates": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "paymentDatesBusinessDayConventionClear": "[true|false]",
                "paymentFrequency": "[1M|3M|6M|1Y|TERM]",
                "paymentFrequencyClear": "[true|false]"
            },
            "periodEndDates": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "periodEndDatesBusinessDayConventionClear": "[true|false]",
                "calculationPeriodFrequency": "[1M|3M|6M|1Y|TERM]",
                "calculationPeriodFrequencyClear": "[true|false]"
            }
        },
        {
            "paymentDates": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "paymentDatesBusinessDayConventionClear": "[true|false]",
                "paymentFrequency": "[1M|3M|6M|1Y|TERM]",
                "paymentFrequencyClear": "[true|false]"
            },
            "periodEndDates": {
                "businessDayConvention": "[MODFOLLOWING|FOLLOWING|PRECEDING|NONE]",
                "periodEndDatesBusinessDayConventionClear": "[true|false]",
                "calculationPeriodFrequency": "[1M|3M|6M|1Y|TERM]",
                "calculationPeriodFrequencyClear": "[true|false]"
            }
        }
    ]
}

4) promptFXFixingData.txt - extracts the FX fixing data for legs settle in a different currency to the notionalCurrency of the leg.

JSON output:

{
    "header": {

    },
    "legs": [
        {
            "fxFixing": {
                "fxFixingReference": "CLP_DOLAR_OBS_CLP10",
                "fxFixingOffset": -2,
                "fxFixingDayType": "BUSINESS",
                "dateRelativeTo": "PAYMENT_DATES",
                "fxFixingDayConvention": "PRECEDING",
                "fxFixingBusinessCenters": ["USNY", "CLSA"]
            }
        },
        {
            "fxFixing": {
                "fxFixingReference": "CLP_DOLAR_OBS_CLP10",
                "fxFixingOffset": -2,
                "fxFixingDayType": "BUSINESS", 
                "dateRelativeTo": "PAYMENT_DATES",
                "fxFixingDayConvention": "PRECEDING",
                "fxFixingBusinessCenters": ["USNY", "CLSA"]
            }
        }
    ]
}

As you can see, you can actually consolidate the JSON output into a single overall file, as each prompt contributes a different part to the overall file. I run these prompts manually through claude_client.py, and at the moment, I manually have to go in and change the file name of the prompt that I want to run each time. 

I would like to build this into an agentic workflow using the Google ADK. I can point at a specific contract which would be in contract.txt also within the prompts directory, and for the agent to run and extract or run each of these prompts as needed and finally to output into a single JSON. 

As we go forward, we will build it into a more complete application. But for the time being, this is my objective. 

*** Some initial thoughts on your feedback:

I like the idea of the contract analysis tool as the starting point. One thing I have discovered as I've gone through the analysis is that in general, the English language contracts tend to have a different structure to the Spanish language contracts. At some point, it might be worth us actually having different prompts for those. So I like the contract analysis tool; it's something that we could potentially separate branches out into whether it's a Spanish or an English language contract.

In the agent tree structure you propose, why is the JSON merger a subtool of the FX fixing tool? That doesn't seem right to me. 

In principle, I like the idea of the parallel tool. It seems to me to be smarter. My concern, however, would be whether it needs to be sequential because I think there may be some data that's easier to extract once you've got other initial data. Definitely, the core values extraction tool would have to be run before the business day conventions or the period end payment tool or the FX fixing tool. So the core values extraction tool would definitely have to be number two after the contract analysis tool. The others might be able to be run in parallel. 

I'd also like to add a tool at the end which provides some kind of summary for me as a human to read over it and alerts any points of attention I want to have a look at as the human in the loop of this overall process. That could be part of the validation layer that you mention. 

Would it also be worth having tools that go to a particular directory to pick up the contract text? And maybe another tool that writes the output JSON to a different directory. I'm not really sure about what the best practise is in terms of defining tools. I'm a novice in this agentic space, so I'd appreciate your guidance around best practise. 

*** Answering your questions:

1. Execution Model: Do you want all 4 prompts to always run, or should the agent decide which ones are needed based on the contract?
I think only the FX Fixing Tool prompt would be the only optional one, conditional one. I think the others would always have to run.

2. Error Handling: If one extraction fails or returns incomplete data, should the agent retry with a modified prompt, or just flag it for human review?
For the time being, I'd prefer to just flag it for human review.

3. Output Format: Should the final merged JSON be saved to a file? Any specific naming convention?
Yes, it should be saved to a file. Maybe just give it the same name as the input contract, but with a.json extension instead of a.txt.

4. Google ADK Experience: Have you used Google ADK before, or should I recommend sticking with a simpler orchestrator first?
No, I've not used it before, but I'm keen to do so. From what I've seen, it's not particularly complex, and I want to learn about it. Please let's stick with Google ADK.

5. Budget Constraints: Running 4 separate Claude API calls per contract - is latency or API cost a concern?
Yes, it is a bit of a concern - API cost in particular because the contracts themselves can be very long. So maybe for the time being, we can stick everything we can run the whole contract through each prompt (up to 4 times). Ideally, I would be open as we go forward into the future to your thoughts regarding how we can reduce API cost.

Ideally, one point which I would love to be true but I don't think the technology supports it is if you could kind of cache the contract once and each prompt simply refers to it without passing the whole thing as part of the prompt and therefore using a lot of input tokens. But I don't think that's technologically possible at the moment.

The other option I know that we have available to us is chunking the contract text into parts that will be valuable for each of the tools. But I think at least the gut feeling for me is that's a little bit more complex. 

Latency is not so much of an issue for me. This will probably be running as a batch process. Although for demo purposes, I would like to show something that runs very quickly.

---

## Refined Architecture Design (Based on Discussion)

### Final Tool Flow Structure

```
Supervisor Agent
├─ 1. Contract Analysis Tool (analyzes language, structure, determines if FX needed)
│    └─ Output: {language: "EN/ES", hasFXSettlement: true/false}
│
├─ 2. Core Values Extraction Tool (MUST run, uses contract analysis output)
│    └─ Output: core_values.json
│
├─ 3. Parallel Phase (runs simultaneously)
│    ├─ Business Day Conventions Tool
│    ├─ Period End & Payment Tool
│    └─ FX Fixing Tool (conditional - only if hasFXSettlement = true)
│
├─ 4. JSON Merger (combines all outputs)
│
└─ 5. Validation & Summary Tool
     └─ Output: human-readable summary + flags for review
```

### API Cost Optimization: Prompt Caching 🎉

**Anthropic supports Prompt Caching!** This is a game-changer for your use case:

- **How it works:** Cache the contract text once in the first API call
- Each subsequent prompt (2-4) references the cached contract
- **Cost savings:** Only pay full input tokens once, subsequent calls use cached pricing (90% cheaper on cached tokens)
- **Cache duration:** Persists for 5 minutes between calls (perfect for sequential processing)
- **Implementation:** Use cache_control parameter in messages API

**Estimated savings for your workflow:**
- Without caching: 4 × full contract tokens = 4× cost
- With caching: 1× full contract + 3× (prompt tokens only + 10% cache cost) ≈ 40-50% total cost reduction

### Proposed Tool Definitions

**File I/O Tools (simple Python functions, not LLM calls):**
- `read_contract_file(contract_path) -> str`
- `write_output_json(output_path, json_data) -> bool`

**Analysis & Extraction Tools (LLM-powered with caching):**
- `analyze_contract(contract_text) -> {language, hasFXSettlement, structure_type}`
- `extract_core_values(contract_text, language) -> JSON`
- `extract_business_day_conventions(contract_text, core_values) -> JSON`
- `extract_period_payment_data(contract_text, core_values) -> JSON`
- `extract_fx_fixing(contract_text, core_values) -> JSON` (conditional)

**Post-Processing Tools (Python + LLM):**
- `merge_extractions(core, bdc, period, fx?) -> final_json`
- `validate_and_summarize(final_json) -> {summary, flags, completeness_score}`

### Sequential vs Parallel Execution Strategy

**Phase 1 (Sequential):**
- Contract Analysis → Core Values Extraction
- *Reason:* Core values needed as context for other extractions

**Phase 2 (Parallel - Future enhancement):**
- Business Day Conventions || Period/Payment || FX Fixing
- *Reason:* All can run independently once core values are available

**Phase 3 (Sequential):**
- Merge → Validate & Summarize
- *Reason:* Must wait for all extractions to complete

### Directory Structure

```
backend/
  contracts/              # Input contracts (new)
    contract001.txt
    contract002.txt
  output/                 # Generated JSONs (new)
    contract001.json
    contract002.json
  prompts/                # Existing prompt templates
    promptCoreValues.txt
    promptHeaderBusinessDayConventions.txt
    promptPeriodEndAndPaymentBusinessDayConventions.txt
    promptFXFixingData.txt
    contract.txt
  agentic/                # New Google ADK implementation
    agent.py              # Main supervisor agent
    tools.py              # Tool definitions
    merger.py             # JSON merging logic
    cache_manager.py      # Prompt caching utilities
  claude_client.py        # Existing manual runner
```

### Language-Specific Prompts (Future Enhancement)

For future expansion when English vs Spanish structure differences matter:
```
prompts/
  en/
    promptCoreValues.txt
    promptBusinessDayConventions.txt
    ...
  es/
    promptCoreValues.txt  # Spanish-optimized version
    promptBusinessDayConventions.txt
    ...
```

The Contract Analysis tool would determine which prompt set to use based on detected language.

---

## Implementation Plan - MVP Phase 1

### Step 1: Environment Setup & Google ADK Installation
**Goal:** Get Google ADK installed and verify it works

**What you'll learn:** How Google ADK is structured, basic agent concepts

**Tasks:**
1. Install Google ADK: `pip install google-adk`
2. Verify installation with simple "Hello World" agent
3. Create `backend/agentic/` directory structure

**Deliverable:** A minimal agent that responds to "Hello" - proves environment works

**Testing:** Run agent, see it respond, understand the basic request/response flow

---

### Step 2: Create Basic File I/O Tools (No AI Yet)
**Goal:** Build tools that read contracts and write JSON files

**What you'll learn:** How to define tools in Google ADK, tool schemas

**Tasks:**
1. Create `backend/agentic/tools.py`
2. Implement `read_contract_file(contract_path)` function
3. Implement `write_output_json(output_path, json_data)` function
4. Define tool schemas for Google ADK
5. Test both tools independently (Python unit tests)

**Deliverable:** Tools that can read a contract.txt and write a dummy.json

**Testing:**
- Read existing `backend/prompts/contract.txt` successfully
- Write a test JSON to `backend/output/test.json`

---

### Step 3: Integrate Existing Prompt with Caching (Single Extraction)
**Goal:** Get ONE of your existing prompts working with prompt caching

**What you'll learn:** How prompt caching works, how to structure cached messages

**Tasks:**
1. Create `backend/agentic/cache_manager.py`
2. Implement prompt caching for Claude API calls
3. Create a tool that uses `promptCoreValues.txt` with caching
4. Test extraction on a real contract

**Deliverable:** Working Core Values extraction with caching enabled

**Testing:**
- Run extraction on `contract.txt`
- Verify JSON output matches expected schema
- Check API response headers to confirm cache hit/miss
- Run twice to see cache hit on second run

---

### Step 4: Create Simple JSON Merger
**Goal:** Merge two JSON extractions into one combined output

**What you'll learn:** Deep merging logic for nested JSON structures

**Tasks:**
1. Create `backend/agentic/merger.py`
2. Implement deep merge function that combines header + legs data
3. Handle conflicts (newer data overwrites vs. deep merge)
4. Unit test with sample JSONs from your specs

**Deliverable:** Merger that can combine CoreValues + BusinessDayConventions JSONs

**Testing:**
- Create two sample JSONs (core values + business day conventions)
- Merge them
- Verify nested structure is preserved
- Check that legs array merges correctly by index

---

### Step 5: Build Sequential Agent (Core Values → Business Day Conventions)
**Goal:** Create an agent that runs TWO extractions sequentially and merges results

**What you'll learn:** Google ADK agent orchestration, sequential tool calling

**Tasks:**
1. Create `backend/agentic/agent.py` with Google ADK supervisor
2. Register the file I/O, extraction, and merger tools
3. Implement logic: read contract → extract core → extract BDC → merge → write output
4. Add basic error handling

**Deliverable:** End-to-end agent that processes contract.txt → output JSON with 2 extractions

**Testing:**
- Run agent on real contract
- Verify it calls tools in correct order
- Check final merged JSON has data from both extractions
- Confirm caching worked (check token usage in API responses)

---

### Step 6: Add Remaining Extractions (Period/Payment + FX Fixing)
**Goal:** Complete all 4 extractions in sequence

**What you'll learn:** Tool expansion, handling optional tools (FX)

**Tasks:**
1. Add tools for Period/Payment and FX Fixing extractions
2. Update agent to run all 4 sequentially
3. Update merger to handle all 4 JSON outputs
4. Add logic to detect if FX fixing is needed (simple check: does contract mention "USD" or currency conversion?)

**Deliverable:** Full extraction pipeline with all 4 prompts

**Testing:**
- Run on contract with FX fixing → verify FX data extracted
- Run on contract without FX → verify FX tool skipped
- Validate final merged JSON has all expected sections

---

### Step 7: Add Basic Validation & Summary Tool
**Goal:** Generate human-readable summary with flags for review

**What you'll learn:** Post-processing, business logic validation

**Tasks:**
1. Create validation tool that checks for:
   - Missing required fields (dates, notionals, etc.)
   - Unclear extractions (where `*Clear` fields = false)
   - Suspicious values (negative notionals, invalid dates)
2. Generate markdown summary:
   - Contract overview (parties, dates, notionals)
   - Extraction quality score
   - List of flags requiring human review
3. Output summary to console and/or text file

**Deliverable:** Agent outputs both JSON + human-readable summary

**Testing:**
- Run on complete contract → see "All good" summary
- Run on partial/messy contract → see flags for unclear fields
- Verify summary accurately reflects JSON content

---

### Step 8: End-to-End Testing & Refinement
**Goal:** Test entire pipeline, fix bugs, optimize

**What you'll learn:** Real-world debugging, prompt refinement

**Tasks:**
1. Test on 3-5 different real contracts
2. Compare outputs with your manual extractions
3. Identify and fix discrepancies
4. Optimize prompts if needed
5. Add logging for debugging
6. Document how to run the agent

**Deliverable:** Production-ready MVP with documentation

**Testing:**
- Process multiple contracts
- Measure accuracy vs. manual extraction
- Verify caching reduces costs (check API usage)
- Create README with usage instructions

---

## Summary of MVP Deliverables

After Step 8, you will have:
- ✅ Google ADK agent that processes IRS contracts
- ✅ All 4 extraction prompts integrated with caching
- ✅ JSON merger producing final consolidated output
- ✅ Validation & summary for human review
- ✅ File I/O (contracts/ → output/)
- ✅ 40-50% API cost savings via prompt caching
- ✅ End-to-end testing on real contracts

**Not included in MVP (Phase 2):**
- ❌ Contract analysis tool (language detection)
- ❌ Parallel execution of Phase 2 tools
- ❌ Language-specific prompt routing
- ❌ Advanced retry logic
- ❌ Batch processing multiple contracts

---

## Next Steps

**Ready to begin Step 1?** Let me know and I'll create:
1. The Google ADK installation instructions
2. The basic "Hello World" agent
3. The directory structure

We'll test it together, get your feedback, then move to Step 2.