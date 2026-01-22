"""
Simple pipeline orchestrator for prompt completion.
Validates prompt then checks completeness with LLM.
"""

import uuid
import time
import logging
from datetime import datetime
from app.config import MODEL_NAME_FOR_PROMPT_COMPLETION
from .models import (
    PromptCompletionRequest,
    PromptCompletionResponse,
    PromptValidationResult,
)
from .validator import PreCheckPrompt
from .prompt_completion_status import PromptCompletionChecker
from prompt_completion_layer import validator

logger = logging.getLogger(__name__)


class PromptCompletionPipeline:
    """Pipeline: Validate prompt → Check with LLM → Return result."""
    
    def __init__(self, llm_model: str = MODEL_NAME_FOR_PROMPT_COMPLETION):
        self.validator = PreCheckPrompt("")
        self.checker = PromptCompletionChecker(model_name=llm_model)
        logger.info(f"Pipeline initialized with model: {llm_model}")
    
    def process(self, request: PromptCompletionRequest) -> PromptCompletionResponse:
        """
        Process a prompt.
        1. Validate (clean and count tokens)
        2. Check with LLM if complete
        3. Return result
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        logger.info(f"Processing request {request_id}")
        
        try:
            # Step 1: Validate prompt
            logger.info("Step 1: Validating prompt")
            self.validator.prompt = request.prompt
            validation_result = self.validator.validate()
            cleaned_prompt = self.validator.clean_prompt()
            # Step 2: Check completion with LLM
            logger.info("Step 2: Checking with LLM")
            completion_result = self.checker.check_completion(cleaned_prompt)
            
            # Step 3: Build response
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Step 3: Building response for prompt completion")
            response = PromptCompletionResponse(
                request_id=request_id,
                original_prompt=request.prompt,
                validation_result=validation_result,
                completion_result=completion_result,
                timestamp=datetime.utcnow(),
                processing_time_ms=processing_time
            )
            #this is the point where we have to add the entry of end_time in the database
            logger.info(f"Request {request_id} completed in {processing_time:.2f}ms")
            return response
            
        except Exception as e:
            logger.error(f"Error processing request {request_id}: {str(e)}", exc_info=True)
            raise
