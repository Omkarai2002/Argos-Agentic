from prompt_completion_layer.validator import PreCheckPrompt
from logging_config import LoggerFeature
import logging
LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)
def validate_prompt(prompt: str) -> bool:
    validator = PreCheckPrompt(prompt)
    is_valid = validator.validate_token_limit()
    if is_valid:
        logger.info("Prompt validation successful.")
    else:
        logger.error(f"Prompt validation failed: {validator.error_message}")
    return is_valid
# Example usage
if __name__ == "__main__":
    test_prompt = "Hello 👋 Omkar 😄, let's build 🚀"
    if validate_prompt(test_prompt):
        print("Prompt is valid.")
    else:
        print("Prompt is invalid.")