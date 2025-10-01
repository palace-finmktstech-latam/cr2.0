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