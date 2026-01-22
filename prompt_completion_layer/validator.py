
import tiktoken
import emoji
import re
from app.config import MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION, MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION, MODEL_NAME_FOR_PROMPT_COMPLETION
from logging_config import LoggerFeature
import logging

LoggerFeature.setup_logging()

logger = logging.getLogger(__name__)
class PreCheckPrompt:

    def __init__(self,prompt:str):
        self.prompt=prompt
        self.validated=False
        self.error_message=""
        self.model = MODEL_NAME_FOR_PROMPT_COMPLETION

    def remove_emojis(self, prompt: str) -> str:
        return emoji.replace_emoji(prompt, replace="")
    
    def remove_white_spaces(self,) -> str:
        return re.sub(r'\s+', ' ', self.remove_emojis(self.prompt)).strip()
    
    def count_tokens(self) -> int :
        encoding = tiktoken.encoding_for_model(self.model)
        tokens = encoding.encode(cleaned_prompt := self.remove_white_spaces())
        print(f"Cleaned Prompt: {cleaned_prompt}")
        return len(tokens)

    def validate_token_limit(self):
        token_count = self.count_tokens()
        if token_count >= MAX_TOKEN_LIMIT_FOR_PROMPT_COMPLETION:
            self.validated = False
            logger.error(f"Token count more than expected{token_count}.")
            return self.validated
        elif token_count <= MIN_TOKEN_LIMIT_FOR_PROMPT_COMPLETION:
            self.validated = False
            logger.warning(f"Token count less than expected {token_count}.")
            return self.validated
        else:
            self.validated = True
            logger.info(f"token check passed successfully with {token_count} tokens.")
        return self.validated
