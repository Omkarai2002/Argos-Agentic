"""
Simple example of using the prompt completion pipeline.
"""

import logging
from prompt_completion_layer.orchestrator import PromptCompletionPipeline
from prompt_completion_layer.models import PromptCompletionRequest
from logging_config import LoggerFeature

# Setup logging
LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Run example."""
    
    # Initialize pipeline
    pipeline = PromptCompletionPipeline(llm_model="gpt-4o-mini")
    
    # Example 1: Complete prompt
    print("\n" + "="*60)
    print("Example 1: Complete Prompt")
    print("="*60)
    
    prompt1 = """
    Build a Python function that:
    - Takes a list of numbers as input
    - Returns sum, average, max, and min values
    - Handles empty lists and non-numeric values with proper error handling
    - Use type hints and docstrings
    """
    
    request1 = PromptCompletionRequest(
        prompt=prompt1,
        user_id="user_123"
    )
    
    response1 = pipeline.process(request1)
    print_response(response1)
    
    # Example 2: Incomplete prompt
    print("\n" + "="*60)
    print("Example 2: Incomplete Prompt")
    print("="*60)
    
    prompt2 = "Write code"
    
    request2 = PromptCompletionRequest(
        prompt=prompt2,
        user_id="user_456"
    )
    
    response2 = pipeline.process(request2)
    print_response(response2)
    
    # Example 3: Medium prompt
    print("\n" + "="*60)
    print("Example 3: Medium Detail Prompt")
    print("="*60)
    
    prompt3 = "Explain how machine learning works"
    
    request3 = PromptCompletionRequest(
        prompt=prompt3,
        user_id="user_789"
    )
    
    response3 = pipeline.process(request3)
    print_response(response3)


def print_response(response) -> None:
    """Print response nicely."""
    print("\n" + "-"*60)
    print(f"Request ID: {response.request_id}")
    print(f"Time: {response.processing_time_ms:.2f}ms")
    print(f"\nValidation:")
    print(f"  Valid: {response.validation_result.is_valid}")
    print(f"  Tokens: {response.validation_result.token_count}")
    if response.validation_result.validation_errors:
        print(f"  Errors: {response.validation_result.validation_errors}")
    print(f"\nCompletion Check:")
    print(f"  Status: {response.completion_result.status}")
    print(f"  Complete: {response.completion_result.is_complete}")
    print(f"  Confidence: {response.completion_result.confidence}")
    #print(f"  Reasoning: {response.completion_result.reasoning}")
    # if response.completion_result.suggestions:
    #     print(f"  Suggestions: {response.completion_result.suggestions}")
    # print("-"*60)


if __name__ == "__main__":
    main()
