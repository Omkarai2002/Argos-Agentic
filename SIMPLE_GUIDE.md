"""
PROMPT COMPLETION LAYER - SIMPLE GUIDE

This layer validates prompts and checks if they are complete enough for an AI system to execute.

================================================================================
QUICK START
================================================================================

1. Initialize the pipeline:

    from prompt_completion_layer import PromptCompletionPipeline, PromptCompletionRequest
    
    pipeline = PromptCompletionPipeline(llm_model="gpt-4o-mini")

2. Create a request:

    request = PromptCompletionRequest(
        prompt="Your prompt here",
        user_id="user_123"
    )

3. Process the request:

    response = pipeline.process(request)

4. Check the results:

    print(response.completion_result.status)  # "accepted" or "rejected"
    print(response.completion_result.is_complete)  # True or False
    print(response.completion_result.confidence)  # 0.0 to 1.0
    print(response.completion_result.reasoning)  # Why this decision?

================================================================================
FLOW (What Happens Inside)
================================================================================

User Prompt
    ↓
[1. VALIDATE]
   - Remove emojis
   - Clean whitespace
   - Count tokens
   - Check token limits
    ↓
[2. LLM CHECK]
   - Send to OpenAI
   - Get completeness score
   - Get confidence level
   - Get suggestions
    ↓
[3. RETURN RESPONSE]
   - Validation results
   - LLM results
   - Processing time

================================================================================
THE 3 MAIN CLASSES
================================================================================

1. PreCheckPrompt (validator.py)
   - clean_prompt(): Remove emojis and extra spaces
   - count_tokens(): Count how many tokens
   - validate(): Check token limits, return result

   Example:
       validator = PreCheckPrompt("your prompt")
       result = validator.validate()
       print(result.is_valid)

2. PromptCompletionChecker (prompt_completion_status.py)
   - check_completion(prompt): Send to LLM, get analysis

   Example:
       checker = PromptCompletionChecker(model_name="gpt-4o-mini")
       result = checker.check_completion("your prompt")
       print(result.status)

3. PromptCompletionPipeline (orchestrator.py)
   - process(request): Run validation + LLM check, return full response

   Example:
       pipeline = PromptCompletionPipeline()
       request = PromptCompletionRequest(prompt="...")
       response = pipeline.process(request)

================================================================================
DATA MODELS (models.py) - What You Get Back
================================================================================

PromptCompletionRequest (What you send in):
    - prompt: str (required) - The user's prompt
    - user_id: str (optional) - User identifier
    - context: dict (optional) - Extra info

PromptValidationResult (Validation output):
    - is_valid: bool - Passed token check?
    - token_count: int - Number of tokens
    - cleaned_prompt: str - After cleaning
    - validation_errors: list - Any errors

CompletionCheckResult (LLM output):
    - status: str - "accepted" or "rejected"
    - is_complete: bool - Complete or not?
    - confidence: float - How sure? (0.0 to 1.0)
    - reasoning: str - Why this decision?
    - suggestions: str - How to improve

PromptCompletionResponse (Final response):
    - request_id: str - Unique ID for this request
    - original_prompt: str - What you sent
    - validation_result: PromptValidationResult
    - completion_result: CompletionCheckResult
    - processing_time_ms: float - How long it took

================================================================================
CONFIGURATION (app/config.py)
================================================================================

These settings control validation:

MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 8192
    -> Maximum tokens allowed in a prompt

MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 10
    -> Minimum tokens required

MODEL_NAME_FOR_PROMPT_COMPLETION = "gpt-4o-mini"
    -> Which LLM model to use

Adjust these based on your needs!

================================================================================
EXAMPLE: Complete Workflow
================================================================================

from prompt_completion_layer import (
    PromptCompletionPipeline, 
    PromptCompletionRequest
)

# Initialize once
pipeline = PromptCompletionPipeline()

# Create request
request = PromptCompletionRequest(
    prompt="Build a Python function that sorts a list of numbers",
    user_id="john_doe"
)

# Process
response = pipeline.process(request)

# Use results
if response.validation_result.is_valid:
    print("✓ Validation passed")
else:
    print("✗ Validation failed:", response.validation_result.validation_errors)

if response.completion_result.is_complete:
    print("✓ Prompt is complete")
    print(f"  Confidence: {response.completion_result.confidence}")
else:
    print("✗ Prompt needs more detail")
    if response.completion_result.suggestions:
        print(f"  Tips: {response.completion_result.suggestions}")

print(f"Processed in {response.processing_time_ms:.2f}ms")

================================================================================
COMMON ISSUES & FIXES
================================================================================

Issue: "OPENAI_API_KEY not found"
Fix: Set environment variable
    export OPENAI_API_KEY="your-key-here"

Issue: "Token count too high/low"
Fix: Adjust limits in app/config.py
    MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION = 5

Issue: "Module not found"
Fix: Install requirements
    pip install -r requirements.txt

Issue: "LLM response parsing error"
Fix: This happens occasionally. The pipeline will return an error status.
     Just try again.

================================================================================
REQUIREMENTS
================================================================================

Installed by:  pip install -r requirements.txt

Main packages:
- langchain: LLM orchestration
- langchain-openai: OpenAI integration
- pydantic: Data validation
- tiktoken: Token counting
- emoji: Emoji detection
- python-dotenv: Environment variables

================================================================================
TESTING YOUR SETUP
================================================================================

1. Set your API key:
   export OPENAI_API_KEY=""

2. Run the example:
   python example_usage.py

3. You should see 3 test prompts analyzed with results

If it works, you're all set!

================================================================================
