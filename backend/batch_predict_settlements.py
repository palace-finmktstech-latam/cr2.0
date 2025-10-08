#!/usr/bin/env python3
"""
Batch prediction: Run DSPy settlement extraction on all contracts in a folder.
No training data required - just runs predictions.
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel
import dspy

# Load environment
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Initialize Vertex AI
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "contract-reader-2-dev")
location = "us-central1"
vertexai.init(project=project_id, location=location)


# ==================== CUSTOM GEMINI WRAPPER ====================

class GeminiVertexLM(dspy.LM):
    """Custom DSPy LM wrapper for Vertex AI Gemini"""

    def __init__(self, model="gemini-2.0-flash-exp", **kwargs):
        super().__init__(model)
        self.model_name = model
        self.kwargs = kwargs
        self.client = GenerativeModel(model)

    def basic_request(self, prompt, **kwargs):
        """Make a basic request to Gemini"""
        try:
            response = self.client.generate_content(
                prompt,
                generation_config={
                    "temperature": kwargs.get("temperature", 0),
                    "max_output_tokens": kwargs.get("max_tokens", 2048),
                }
            )
            return response.text
        except Exception as e:
            print(f"Error in Gemini request: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def __call__(self, prompt=None, messages=None, **kwargs):
        """DSPy calls this method - support both prompt and messages"""
        if messages is not None:
            if isinstance(messages, list):
                prompt = "\n\n".join([
                    f"{msg.get('content', '')}"
                    for msg in messages
                ])
            else:
                prompt = str(messages)

        if prompt is None:
            raise ValueError("Either prompt or messages must be provided")

        response_text = self.basic_request(prompt, **kwargs)
        return [response_text]


# ==================== LOAD OPTIMIZED MODULE ====================

def load_optimized_module():
    """Load the optimized DSPy module if it exists, otherwise use unoptimized"""
    optimized_path = Path(__file__).parent / "settlement_optimized.json"

    # Import the module class
    from settlement_dspy_experiment import SettlementExtractionModule

    if optimized_path.exists():
        print(f"✓ Loading optimized module from {optimized_path}")
        module = SettlementExtractionModule()
        module.load(str(optimized_path))
        return module, True
    else:
        print("⚠ No optimized module found, using baseline")
        return SettlementExtractionModule(), False


# ==================== BATCH PREDICTION ====================

def batch_predict(contract_texts_dir, output_file):
    """Run predictions on all contracts in a directory"""

    print("=" * 60)
    print("DSPy Batch Settlement Prediction")
    print("=" * 60)
    print()

    # Step 1: Configure DSPy
    print("Step 1: Configuring DSPy with Vertex AI Gemini...")
    gemini_lm = GeminiVertexLM(model="gemini-2.0-flash-exp")
    dspy.settings.configure(lm=gemini_lm)
    print("✓ Gemini configured")
    print()

    # Step 2: Load optimized module
    print("Step 2: Loading extraction module...")
    module, is_optimized = load_optimized_module()
    model_type = "OPTIMIZED" if is_optimized else "BASELINE"
    print(f"✓ Using {model_type} model")
    print()

    # Step 3: Find all contract text files
    print("Step 3: Finding contract files...")
    contracts_dir = Path(contract_texts_dir)
    contract_files = sorted(contracts_dir.glob("*.txt"))
    print(f"✓ Found {len(contract_files)} contract files")
    print()

    # Step 4: Run predictions
    print("Step 4: Running predictions...")
    print()

    results = []

    for i, contract_file in enumerate(contract_files, 1):
        contract_id = contract_file.stem  # filename without .txt

        print(f"[{i}/{len(contract_files)}] Processing {contract_id}...")

        # Read contract text
        with open(contract_file, 'r', encoding='utf-8') as f:
            contract_text = f.read()

        # Predict for both legs
        # Note: We don't have notional currency info, so we'll have to guess or extract it first
        # For now, assume both legs exist

        legs_predictions = []

        for leg_num in [1, 2]:
            try:
                # We don't know notional_currency, so use empty string
                # The model should still extract settlement info
                pred = module(
                    contract_text=contract_text,
                    leg_number=leg_num,
                    notional_currency="UNKNOWN"  # Don't have this info yet
                )

                legs_predictions.append({
                    "leg_number": leg_num,
                    "settlement_type": pred.settlement_type,
                    "settlement_currency": pred.settlement_currency,
                    "evidence": pred.evidence,
                })

                # Rate limiting: wait 6 seconds between requests (10 per minute)
                time.sleep(6)

            except Exception as e:
                print(f"  ⚠ Error processing leg {leg_num}: {e}")
                legs_predictions.append({
                    "leg_number": leg_num,
                    "settlement_type": "ERROR",
                    "settlement_currency": "ERROR",
                    "evidence": str(e),
                })
                # Still wait even on error to avoid hammering the API
                time.sleep(6)

        results.append({
            "contract_id": contract_id,
            "predictions": legs_predictions
        })

        # Print summary
        print(f"  Leg 1: {legs_predictions[0]['settlement_type']} / {legs_predictions[0]['settlement_currency']}")
        print(f"  Leg 2: {legs_predictions[1]['settlement_type']} / {legs_predictions[1]['settlement_currency']}")
        print()

    # Step 5: Save results
    print("Step 5: Saving results...")
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            "model_type": model_type,
            "total_contracts": len(results),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"✓ Results saved to: {output_path}")
    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)


# ==================== MAIN ====================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python batch_predict_settlements.py <contract_texts_dir> [output_file]")
        print()
        print("Example:")
        print("  python batch_predict_settlements.py dspy_training/contract_texts predictions.json")
        print()
        sys.exit(1)

    contract_texts_dir = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "settlement_predictions.json"

    batch_predict(contract_texts_dir, output_file)
