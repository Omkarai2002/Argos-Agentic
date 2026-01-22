"""
Simple prompt validation - clean and count tokens.
"""

import tiktoken
import emoji
import re
from app.config import (
    MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION,
    MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION,
    MODEL_NAME_FOR_PROMPT_COMPLETION
)
from logging_config import LoggerFeature
from .models import PromptValidationResult
import logging

LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)


class PreCheckPrompt:
    """Clean and validate prompts."""

    def __init__(self, prompt: str):
        self.prompt = prompt
        self.model = MODEL_NAME_FOR_PROMPT_COMPLETION

    def clean_prompt(self) -> str:
        """Remove emojis and extra spaces."""
        # Remove emojis
        text = emoji.replace_emoji(self.prompt, replace="")
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def count_tokens(self) -> int:
        """Count tokens in cleaned prompt."""
        cleaned = self.clean_prompt()
        encoding = tiktoken.encoding_for_model(self.model)
        tokens = encoding.encode(cleaned)
        return len(tokens)

    def validate(self) -> PromptValidationResult:
        """Validate prompt and return result."""
        token_count = self.count_tokens()
        cleaned_prompt = self.clean_prompt()
        errors = []

        # Check if too many tokens
        if token_count > MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION:
            msg = f"Token count ({token_count}) exceeds limit ({MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION})"
            errors.append(msg)
            logger.error(msg)

        # Check if too few tokens
        if token_count < MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION:
            msg = f"Token count ({token_count}) below limit ({MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION})"
            errors.append(msg)
            logger.warning(msg)

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"Validation passed: {token_count} tokens")

        return PromptValidationResult(
            is_valid=is_valid,
            token_count=token_count,
            cleaned_prompt=cleaned_prompt,
            validation_errors=errors
        )
