#!/usr/bin/env python3
"""
Helper script to prepare training data for DSPy settlement extraction.
Handles proper JSON escaping of contract text.
"""

import json
from pathlib import Path


def create_contract_entry(contract_id, contract_text_file, legs_data):
    """
    Create a properly formatted contract entry.

    Args:
        contract_id: String identifier (e.g., "7561-11287496")
        contract_text_file: Path to .txt file with contract text
        legs_data: List of dicts with leg information

    Example legs_data:
        [
            {
                "leg_number": 1,
                "notional_currency": "CLP",
                "settlement_type": "CASH",
                "settlement_currency": "CLP",
                "evidence": "Line 72: Modalidad de Pago: Compensado CLP"
            },
            ...
        ]
    """
    # Read contract text from file
    with open(contract_text_file, 'r', encoding='utf-8') as f:
        contract_text = f.read()

    return {
        "contract_id": contract_id,
        "contract_text": contract_text,  # Python json.dump handles escaping automatically
        "legs": legs_data
    }


def main():
    """Interactive script to build training data"""

    print("DSPy Training Data Builder")
    print("=" * 60)
    print()

    # Define paths
    training_dir = Path(__file__).parent / "dspy_training"
    contract_texts_dir = training_dir / "contract_texts"
    output_file = training_dir / "settlement_training_data.json"

    # Ensure directories exist
    contract_texts_dir.mkdir(parents=True, exist_ok=True)

    print(f"Training data directory: {training_dir}")
    print(f"Contract texts folder: {contract_texts_dir}")
    print()

    # Load existing data or create new
    if output_file.exists():
        print(f"Loading existing data from {output_file}...")
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Loaded {len(data['contracts'])} existing contracts")
    else:
        print("Creating new training data file...")
        data = {"contracts": []}

    print()
    print("=" * 60)
    print("Add New Contract")
    print("=" * 60)
    print()

    # Get contract ID
    contract_id = input("Contract ID (e.g., 7561-11287496): ").strip()

    # Get contract text file (check in contract_texts folder first)
    contract_file_input = input(f"Contract filename (should be in {contract_texts_dir}): ").strip()

    # If just filename given, look in contract_texts_dir
    if not Path(contract_file_input).is_absolute():
        contract_file = contract_texts_dir / contract_file_input
    else:
        contract_file = Path(contract_file_input)

    if not contract_file.exists():
        print(f"ERROR: File not found: {contract_file}")
        return

    print()
    print("=" * 60)
    print("LEG INFORMATION")
    print("=" * 60)
    print()
    print("IMPORTANT: Leg numbers refer to JSON output structure, NOT contract order:")
    print("  Leg 1 = Pata-Activa  (OurCounterparty pays, ThisBank receives)")
    print("  Leg 2 = Pata-Pasiva  (ThisBank pays, OurCounterparty receives)")
    print()
    print("To identify which leg is which:")
    print("  - Look for who pays what in the contract")
    print("  - The leg where the OTHER BANK pays → Leg 1 (Pata-Activa)")
    print("  - The leg where Banco ABC pays → Leg 2 (Pata-Pasiva)")
    print()

    legs_data = []

    while True:
        print("-" * 60)
        leg_input = input("Which leg? (1=Pata-Activa, 2=Pata-Pasiva, or 'done'): ").strip()

        if leg_input.lower() == 'done':
            break

        if leg_input not in ['1', '2']:
            print("Please enter 1, 2, or 'done'")
            continue

        leg_num = int(leg_input)
        leg_name = "Pata-Activa (OurCounterparty pays)" if leg_num == 1 else "Pata-Pasiva (ThisBank pays)"

        print(f"\nLeg {leg_num}: {leg_name}")
        print()

        # Get leg details
        notional_currency = input(f"  Notional currency (e.g., CLP, CLF, USD): ").strip().upper()

        print(f"  Settlement type:")
        print("    1. CASH (Compensado)")
        print("    2. PHYSICAL (Entrega Física)")
        settlement_choice = input("  Choose (1 or 2): ").strip()
        settlement_type = "CASH" if settlement_choice == "1" else "PHYSICAL"

        settlement_currency = input(f"  Settlement currency (e.g., CLP, USD): ").strip().upper()

        print()
        print("  Evidence: Quote or reference showing where you found this info")
        print("  Examples:")
        print("    - 'Modalidad de Pago: Compensado CLP'")
        print("    - 'Section II: Compensado in CLP'")
        print("    - 'Payment terms section: CASH settlement'")
        evidence = input("  Your evidence: ").strip()

        legs_data.append({
            "leg_number": leg_num,
            "notional_currency": notional_currency,
            "settlement_type": settlement_type,
            "settlement_currency": settlement_currency,
            "evidence": evidence
        })

        print(f"  ✓ Leg {leg_num} added")
        print()

    # Create contract entry
    contract_entry = create_contract_entry(contract_id, contract_file, legs_data)

    # Check if contract already exists
    existing_ids = [c['contract_id'] for c in data['contracts']]
    if contract_id in existing_ids:
        print(f"WARNING: Contract {contract_id} already exists. Replacing...")
        data['contracts'] = [c for c in data['contracts'] if c['contract_id'] != contract_id]

    data['contracts'].append(contract_entry)

    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print()
    print(f"✓ Contract added! Total contracts: {len(data['contracts'])}")
    print(f"✓ Saved to: {output_file}")
    print()
    print("Run this script again to add more contracts, or run the experiment with:")
    print(f"  python settlement_dspy_experiment.py run {output_file}")
    print()


if __name__ == "__main__":
    main()
