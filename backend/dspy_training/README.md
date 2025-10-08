# DSPy Training Data for Settlement Extraction

This folder contains training data for the DSPy settlement extraction experiment.

## Folder Structure

```
dspy_training/
├── README.md                        # This file
├── contract_texts/                  # Put your contract .txt files here
│   ├── contract_7561-11287496.txt   # Full contract text (one file per contract)
│   ├── contract_7559-61863.txt
│   └── ...
└── settlement_training_data.json    # Generated training data (auto-created)
```

## How to Add Training Data

### Step 1: Save Contract Text Files

For each contract you want to use for training:

1. Create a `.txt` file in the `contract_texts/` folder
2. Name it: `contract_[CONTRACT_ID].txt` (e.g., `contract_7561-11287496.txt`)
3. Paste the **full contract text** into the file
4. Save it with UTF-8 encoding

**Example:**
```
contract_texts/contract_7561-11287496.txt
```

### Step 2: Run the Training Data Builder

From the `backend/` directory, run:

```bash
python prepare_training_data.py
```

The script will ask you:
- Contract ID (e.g., 7561-11287496)
- Contract filename (e.g., contract_7561-11287496.txt)
- For each leg:
  - Leg number (1 or 2)
  - Notional currency (CLP, CLF, USD, etc.)
  - Settlement type (CASH or PHYSICAL)
  - Settlement currency (CLP, USD, etc.)
  - Evidence (quote from contract showing where you found this)

### Step 3: Repeat for 15-20 Contracts

Run the script multiple times to add more contracts.

The script will automatically:
- Read the contract text file
- Handle JSON escaping
- Add the contract to `settlement_training_data.json`

### Step 4: Run the DSPy Experiment

Once you have 15-20 contracts labeled:

```bash
python settlement_dspy_experiment.py run dspy_training/settlement_training_data.json
```

## Example Training Session

```bash
# Add first contract
python prepare_training_data.py
> Contract ID: 7561-11287496
> Contract filename: contract_7561-11287496.txt
> Leg number: 1
>   Notional currency: CLP
>   Settlement type: 1 (CASH)
>   Settlement currency: CLP
>   Evidence: Line 72: Modalidad de Pago: Compensado CLP
> Leg number: 2
>   Notional currency: CLF
>   Settlement type: 1 (CASH)
>   Settlement currency: CLP
>   Evidence: Line 72: Compensado CLP
> Leg number: done

# Add more contracts...
# Repeat 15-20 times

# Run experiment
python settlement_dspy_experiment.py run dspy_training/settlement_training_data.json
```

## What to Look For in Contracts

When labeling settlement type and currency, look for these Spanish keywords:

**Settlement Type:**
- "Compensado" → CASH
- "Compensación" → CASH
- "Entrega Física" → PHYSICAL
- "Physical Delivery" → PHYSICAL

**Settlement Currency:**
- "Modalidad de Pago: Compensado CLP" → CLP
- "Settlement Currency: USD" → USD
- Usually stated explicitly in the contract

## Goal

Collect 15-20 diverse contracts covering:
- Different settlement types (CASH and PHYSICAL)
- Different currencies (CLP, CLF, USD, etc.)
- Different contract formats (Spanish and English)
- Different leg combinations

This diversity will help DSPy learn robust patterns for settlement extraction.
