import dspy
import os
from dspy.datasets import HotPotQA
from dspy.teleprompt import BootstrapFewShot
from dspy.evaluate import Evaluate

# Configure the language model to use Claude via Anthropic
import os
from anthropic import Anthropic

# Alternative: If dspy.Anthropic doesn't exist, use a custom wrapper
try:
    # Try the built-in Anthropic class first
    lm = dspy.Anthropic(
        model="claude-sonnet-4-5@20250929",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=250
    )
except AttributeError:
    # Fallback: Create a custom LM wrapper for Claude
    class ClaudeLM(dspy.LM):
        def __init__(self, model="claude-sonnet-4-5@20250929", **kwargs):
            super().__init__(model)
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.kwargs = kwargs
        
        def basic_request(self, prompt, **kwargs):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get('max_tokens', 250),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
    
    lm = ClaudeLM(model="claude-3-5-sonnet-20241022", max_tokens=250)

dspy.settings.configure(lm=lm)

# Define a signature - this specifies input/output without the prompt
class GenerateAnswer(dspy.Signature):
    """Answer questions with short factual answers."""
    question = dspy.InputField()
    answer = dspy.OutputField(desc="often between 1 and 5 words")

# Create a basic module using the signature
class BasicQA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_answer = dspy.Predict(GenerateAnswer)
    
    def forward(self, question):
        prediction = self.generate_answer(question=question)
        return dspy.Prediction(answer=prediction.answer)

# Create a more sophisticated module with chain of thought
class CoTQA(dspy.Module):
    def __init__(self):
        super().__init__()
        # ChainOfThought automatically adds reasoning steps
        self.generate_answer = dspy.ChainOfThought(GenerateAnswer)
    
    def forward(self, question):
        prediction = self.generate_answer(question=question)
        # Return the full prediction object to see what's available
        return prediction

# Example usage without optimization
def basic_example():
    print("=== Basic DSPy Example ===")
    
    # Create a simple QA module
    qa = BasicQA()
    
    # Ask some questions
    questions = [
        "What is the capital of France?",
        "Who wrote Romeo and Juliet?",
        "What year did World War II end?"
    ]
    
    for question in questions:
        pred = qa(question=question)
        print(f"Q: {question}")
        print(f"A: {pred.answer}")
        print()

# Example with Chain of Thought
def cot_example():
    print("=== Chain of Thought Example ===")
    
    cot_qa = CoTQA()
    
    question = "If a train travels 60 mph for 2.5 hours, how far does it go?"
    pred = cot_qa(question=question)
    
    print(f"Q: {question}")
    print(f"A: {pred.answer}")
    
    # Extract reasoning from completions if available
    if hasattr(pred, 'completions') and pred.completions:
        # The reasoning is often in the first completion
        completion = pred.completions[0]
        if hasattr(completion, 'rationale') and completion.rationale:
            print(f"Reasoning: {completion.rationale}")
    print()

# Example with optimization (requires dataset)
def optimization_example():
    print("=== Optimization Example ===")
    
    # Load a small sample dataset (you'd use more data in practice)
    dataset = [
        dspy.Example(question="What is 2+2?", answer="4").with_inputs("question"),
        dspy.Example(question="What color is the sky?", answer="blue").with_inputs("question"),
        dspy.Example(question="How many legs does a spider have?", answer="8").with_inputs("question"),
        dspy.Example(question="What is the largest planet?", answer="Jupiter").with_inputs("question"),
    ]
    
    # Split into train/test
    trainset = dataset[:3]
    testset = dataset[3:]
    
    # Create and compile (optimize) the module
    qa_module = BasicQA()
    
    # Define a simple metric
    def validate_answer(example, pred, trace=None):
        return example.answer.lower() in pred.answer.lower()
    
    # Set up the optimizer
    teleprompter = BootstrapFewShot(metric=validate_answer)
    
    # Compile (optimize) the module
    compiled_qa = teleprompter.compile(qa_module, trainset=trainset)
    
    # Test the optimized module
    for example in testset:
        pred = compiled_qa(question=example.question)
        print(f"Q: {example.question}")
        print(f"Expected: {example.answer}")
        print(f"Got: {pred.answer}")
        print()

# Advanced example: Multi-hop reasoning
class MultiHopQA(dspy.Module):
    def __init__(self):
        super().__init__()
        self.decompose = dspy.ChainOfThought("question -> subquestions")
        self.answer_sub = dspy.ChainOfThought("subquestion -> answer")
        self.synthesize = dspy.ChainOfThought("question, answers -> final_answer")
    
    def forward(self, question):
        # Break down the question
        decomp = self.decompose(question=question)
        
        # Answer sub-questions (simplified - in practice you'd parse subquestions)
        sub_answers = []
        # This is a simplified version - real implementation would parse subquestions
        sub_answer = self.answer_sub(subquestion=question)
        sub_answers.append(sub_answer.answer)
        
        # Synthesize final answer
        final = self.synthesize(
            question=question, 
            answers="; ".join(sub_answers)
        )
        
        return dspy.Prediction(answer=final.final_answer)

def advanced_example():
    print("=== Advanced Multi-hop Example ===")
    
    multi_qa = MultiHopQA()
    
    question = "What is the population of the capital of the country where the Eiffel Tower is located?"
    pred = multi_qa(question=question)
    
    print(f"Q: {question}")
    print(f"A: {pred.answer}")

if __name__ == "__main__":
    # Note: You'll need to set your Anthropic API key
    # export ANTHROPIC_API_KEY="your-key-here"
    
    print("DSPy Framework Example with Claude")
    print("==================================")
    print("Note: This requires 'pip install dspy-ai' and an Anthropic API key")
    print()
    
    # Check if API key is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)
    
    try:
        basic_example()
        cot_example()
        optimization_example()
        advanced_example()
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("\nMake sure you have:")
        print("1. Installed DSPy: pip install dspy-ai")
        print("2. Installed Anthropic: pip install anthropic")
        print("3. Set your Anthropic API key: export ANTHROPIC_API_KEY='your-key'")
        print("4. DSPy supports Claude through the Anthropic class")