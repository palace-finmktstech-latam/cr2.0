#!/usr/bin/env python3
"""
DSPy Experiment: Settlement Type & Currency Extraction
Using Vertex AI Gemini for contract analysis
"""

import dspy
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Initialize Vertex AI
project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "contract-reader-2-dev")
location = "us-central1"
vertexai.init(project=project_id, location=location)


# ==================== CUSTOM GEMINI WRAPPER FOR DSPY ====================

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
            # DSPy chat adapter passes messages list
            # Convert to single prompt string
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

        # DSPy expects a list of responses
        return [response_text]


# ==================== DSPY SIGNATURE ====================

class SettlementExtractor(dspy.Signature):
    """Extract settlement type and settlement currency from a derivatives contract leg.

    Settlement Type can be:
    - CASH: Payments are netted and settled in cash
    - PHYSICAL: Physical delivery of notional amounts

    Settlement Currency is the ISO currency code (CLP, USD, etc.)
    """

    # Inputs
    contract_text: str = dspy.InputField(desc="Full contract text in Spanish or English")
    leg_number: int = dspy.InputField(desc="Which leg to extract for (1 or 2)")
    notional_currency: str = dspy.InputField(desc="Notional currency for this leg (e.g., CLP, CLF, USD)")

    # Outputs
    settlement_type: str = dspy.OutputField(desc="Settlement type: CASH or PHYSICAL")
    settlement_currency: str = dspy.OutputField(desc="Settlement currency as ISO code (CLP, USD, CLF, etc.)")
    evidence: str = dspy.OutputField(desc="Quote from contract showing where you found this information")


# ==================== DSPY MODULE ====================

class SettlementExtractionModule(dspy.Module):
    """DSPy module for extracting settlement information"""

    def __init__(self):
        super().__init__()
        # Use ChainOfThought for reasoning
        self.extract = dspy.ChainOfThought(SettlementExtractor)

    def forward(self, contract_text, leg_number, notional_currency):
        """Extract settlement info for a specific leg"""
        result = self.extract(
            contract_text=contract_text,
            leg_number=leg_number,
            notional_currency=notional_currency
        )
        return result


# ==================== VALIDATION METRIC ====================

def settlement_accuracy(example, pred, trace=None):
    """
    Validation metric for settlement extraction.

    Returns:
        1.0 if both settlement_type and settlement_currency are correct
        0.5 if only one is correct
        0.0 if both are wrong
    """
    type_match = (pred.settlement_type.upper() == example.settlement_type.upper())
    currency_match = (pred.settlement_currency.upper() == example.settlement_currency.upper())

    if type_match and currency_match:
        return 1.0
    elif type_match or currency_match:
        return 0.5
    else:
        return 0.0


# ==================== TRAINING DATA LOADER ====================

def load_training_data(json_path):
    """
    Load training examples from JSON file.

    Expected format:
    {
        "contracts": [
            {
                "contract_id": "7561-11287496",
                "contract_text": "...",
                "legs": [
                    {
                        "leg_number": 1,
                        "notional_currency": "CLP",
                        "settlement_type": "CASH",
                        "settlement_currency": "CLP",
                        "evidence": "Line 72: Modalidad de Pago: Compensado CLP"
                    },
                    ...
                ]
            },
            ...
        ]
    }
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    examples = []
    for contract in data['contracts']:
        contract_text = contract['contract_text']
        for leg in contract['legs']:
            example = dspy.Example(
                contract_text=contract_text,
                leg_number=leg['leg_number'],
                notional_currency=leg['notional_currency'],
                settlement_type=leg['settlement_type'],
                settlement_currency=leg['settlement_currency'],
                evidence=leg.get('evidence', '')
            ).with_inputs('contract_text', 'leg_number', 'notional_currency')

            examples.append(example)

    return examples


# ==================== MAIN EXPERIMENT ====================

def run_experiment(training_data_path):
    """Run the DSPy optimization experiment"""

    print("=" * 60)
    print("DSPy Settlement Extraction Experiment")
    print("=" * 60)
    print()

    # Step 1: Configure DSPy with Gemini
    print("Step 1: Configuring DSPy with Vertex AI Gemini...")
    gemini_lm = GeminiVertexLM(model="gemini-2.0-flash-exp", temperature=0)
    dspy.settings.configure(lm=gemini_lm)
    print("✓ Gemini configured")
    print()

    # Step 2: Load training data
    print("Step 2: Loading training data...")
    if not Path(training_data_path).exists():
        print(f"ERROR: Training data not found at {training_data_path}")
        print("Please create the training data file first.")
        return

    examples = load_training_data(training_data_path)
    print(f"✓ Loaded {len(examples)} training examples")
    print()

    # Step 3: Split data
    print("Step 3: Splitting data into train/validation sets...")
    split_point = int(len(examples) * 0.8)
    trainset = examples[:split_point]
    valset = examples[split_point:]
    print(f"✓ Training set: {len(trainset)} examples")
    print(f"✓ Validation set: {len(valset)} examples")
    print()

    # Step 4: Test unoptimized module
    print("Step 4: Testing UNOPTIMIZED module on validation set...")
    unoptimized_module = SettlementExtractionModule()

    unoptimized_scores = []
    for i, example in enumerate(valset[:3]):  # Test first 3
        pred = unoptimized_module(
            contract_text=example.contract_text,
            leg_number=example.leg_number,
            notional_currency=example.notional_currency
        )
        score = settlement_accuracy(example, pred)
        unoptimized_scores.append(score)

        print(f"\nExample {i+1}:")
        print(f"  Expected: {example.settlement_type} / {example.settlement_currency}")
        print(f"  Got:      {pred.settlement_type} / {pred.settlement_currency}")
        print(f"  Score:    {score}")
        print(f"  Evidence: {pred.evidence[:100]}...")

    avg_unoptimized = sum(unoptimized_scores) / len(unoptimized_scores)
    print(f"\n✓ Unoptimized average accuracy: {avg_unoptimized:.2%}")
    print()

    # Step 5: Optimize with DSPy
    print("Step 5: Optimizing with BootstrapFewShot...")
    from dspy.teleprompt import BootstrapFewShot

    optimizer = BootstrapFewShot(
        metric=settlement_accuracy,
        max_bootstrapped_demos=3,  # Include 3 examples in optimized prompt
        max_labeled_demos=3,
        max_rounds=1
    )

    optimized_module = optimizer.compile(
        SettlementExtractionModule(),
        trainset=trainset
    )
    print("✓ Optimization complete")
    print()

    # Step 6: Test optimized module
    print("Step 6: Testing OPTIMIZED module on validation set...")
    optimized_scores = []
    for i, example in enumerate(valset[:3]):
        pred = optimized_module(
            contract_text=example.contract_text,
            leg_number=example.leg_number,
            notional_currency=example.notional_currency
        )
        score = settlement_accuracy(example, pred)
        optimized_scores.append(score)

        print(f"\nExample {i+1}:")
        print(f"  Expected: {example.settlement_type} / {example.settlement_currency}")
        print(f"  Got:      {pred.settlement_type} / {pred.settlement_currency}")
        print(f"  Score:    {score}")
        print(f"  Evidence: {pred.evidence[:100]}...")

    avg_optimized = sum(optimized_scores) / len(optimized_scores)
    print(f"\n✓ Optimized average accuracy: {avg_optimized:.2%}")
    print()

    # Step 7: Compare results
    print("=" * 60)
    print("RESULTS COMPARISON")
    print("=" * 60)
    print(f"Unoptimized accuracy: {avg_unoptimized:.2%}")
    print(f"Optimized accuracy:   {avg_optimized:.2%}")
    print(f"Improvement:          {(avg_optimized - avg_unoptimized):.2%}")
    print()

    # Step 8: Save optimized module
    output_path = Path(__file__).parent / "settlement_optimized.json"
    optimized_module.save(str(output_path))
    print(f"✓ Optimized module saved to: {output_path}")
    print()


# ==================== HELPER: CREATE SAMPLE TRAINING DATA ====================

def create_sample_training_file(output_path):
    """Create a sample training data file structure"""

    sample_data = {
        "contracts": [
            {
                "contract_id": "7561-11287496",
                "contract_text": "[PASTE FULL CONTRACT TEXT HERE FROM feedback.md]",
                "legs": [
                    {
                        "leg_number": 1,
                        "notional_currency": "CLP",
                        "settlement_type": "CASH",
                        "settlement_currency": "CLP",
                        "evidence": "Line 72: Modalidad de Pago: Compensado CLP"
                    },
                    {
                        "leg_number": 2,
                        "notional_currency": "CLF",
                        "settlement_type": "CASH",
                        "settlement_currency": "CLP",
                        "evidence": "Line 72: Modalidad de Pago: Compensado CLP"
                    }
                ]
            },
            {
                "contract_id": "EXAMPLE-2",
                "contract_text": "[PASTE SECOND CONTRACT TEXT]",
                "legs": [
                    {
                        "leg_number": 1,
                        "notional_currency": "USD",
                        "settlement_type": "PHYSICAL",
                        "settlement_currency": "USD",
                        "evidence": "Settlement: Physical delivery"
                    },
                    {
                        "leg_number": 2,
                        "notional_currency": "CLP",
                        "settlement_type": "PHYSICAL",
                        "settlement_currency": "CLP",
                        "evidence": "Settlement: Physical delivery"
                    }
                ]
            }
        ]
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Sample training data file created: {output_path}")
    print("  Please edit this file and add your real contract data.")


# ==================== MAIN ====================

if __name__ == "__main__":
    import sys

    print("DSPy Settlement Extraction Experiment")
    print("Using Vertex AI Gemini")
    print()

    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  1. Create sample training file:")
        print("     python settlement_dspy_experiment.py create-sample")
        print()
        print("  2. Run experiment:")
        print("     python settlement_dspy_experiment.py run <training_data.json>")
        print()
        sys.exit(1)

    command = sys.argv[1]

    if command == "create-sample":
        output_path = Path(__file__).parent / "settlement_training_data.json"
        create_sample_training_file(output_path)

    elif command == "run":
        if len(sys.argv) < 3:
            print("ERROR: Please provide path to training data JSON")
            print("Usage: python settlement_dspy_experiment.py run <training_data.json>")
            sys.exit(1)

        training_data_path = sys.argv[2]
        run_experiment(training_data_path)

    else:
        print(f"ERROR: Unknown command '{command}'")
        print("Valid commands: create-sample, run")
        sys.exit(1)
