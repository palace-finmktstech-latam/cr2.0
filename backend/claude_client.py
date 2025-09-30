#!/usr/bin/env python3
"""
Simple Claude API client script
"""

import os
from pathlib import Path
from anthropic import Anthropic

def query_claude(question: str, model: str = "claude-sonnet-4-20250514") -> str:
    """
    Send a question to Claude API and return the response.

    Args:
        question: The question to ask Claude
        model: The model to use (default: claude-sonnet-4-20250514)

    Returns:
        Claude's response as a string
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": question
            }
        ]
    )

    return response.content[0].text

def load_prompt_with_contract(prompt_filename: str, contract_filename: str = "contract.txt") -> str:
    """
    Load a prompt file and replace {contract_text} placeholder with content from contract file.

    Args:
        prompt_filename: Name of the prompt file in the prompts directory
        contract_filename: Name of the contract file in the prompts directory (default: contract.txt)

    Returns:
        The prompt with contract text inserted
    """
    # Get the prompts directory
    prompts_dir = Path(__file__).parent / "prompts"

    # Read the prompt file
    prompt_path = prompts_dir / prompt_filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_text = f.read()

    # Read the contract file
    contract_path = prompts_dir / contract_filename
    if not contract_path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")

    with open(contract_path, 'r', encoding='utf-8') as f:
        contract_text = f.read()

    # Replace the placeholder
    final_prompt = prompt_text.replace("{contract_text}", contract_text)

    return final_prompt

def query_claude_with_prompt_file(prompt_filename: str, contract_filename: str = "contract.txt", model: str = "claude-sonnet-4-20250514") -> str:
    """
    Load a prompt file with contract text and query Claude.

    Args:
        prompt_filename: Name of the prompt file in the prompts directory
        contract_filename: Name of the contract file in the prompts directory (default: contract.txt)
        model: The model to use (default: claude-sonnet-4-20250514)

    Returns:
        Claude's response as a string
    """
    # Load the prompt with contract text
    prompt = load_prompt_with_contract(prompt_filename, contract_filename)

    # Query Claude
    return query_claude(prompt, model)

def main():
    """Main function for testing the Claude API connection."""

    # Check if API key is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with your Claude API key")
        return

    # Test with prompt file if it exists
    try:
        print("Testing with prompt file...")

        # Check if promptPaymentDateOffset.txt exists
        prompts_dir = Path(__file__).parent / "prompts"
        #if (prompts_dir / "promptPaymentDateOffset.txt").exists() and (prompts_dir / "contract.txt").exists():
        if (prompts_dir / "promptPeriodEndAndPaymentBusinessDayConventions.txt").exists() and (prompts_dir / "contract.txt").exists():
            print("Loading promptPeriodEndAndPaymentBusinessDayConventions.txt...")
            response = query_claude_with_prompt_file("promptPeriodEndAndPaymentBusinessDayConventions.txt", "contract.txt")
            print("Response from Claude:")
            print(response)
        else:
            # Fallback to simple test
            question = "What is 2+2? Respond with just the number."
            print(f"Question: {question}")
            print("Calling Claude API...")
            answer = query_claude(question)
            print(f"Answer: {answer}")

    except Exception as e:
        print(f"Error calling Claude API: {e}")

if __name__ == "__main__":
    main()