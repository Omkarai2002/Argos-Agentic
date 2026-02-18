"""
Simple pipeline orchestrator for prompt completion.
Validates prompt then checks completeness with LLM.
Optionally saves results to database.
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

logger = logging.getLogger(__name__)


class PromptCompletionPipeline:
    """Pipeline: Validate prompt → Check with LLM → Return result."""
    
    def __init__(self, llm_model: str = MODEL_NAME_FOR_PROMPT_COMPLETION, save_to_db: bool = False):
        self.validator = PreCheckPrompt("")
        self.checker = PromptCompletionChecker(model_name=llm_model)
        self.save_to_db = save_to_db
        
        if save_to_db:
            from .db_manager import PromptCompletionDB
            self.db = PromptCompletionDB()
        else:
            self.db = None
        
        logger.info(f"Pipeline initialized with model: {llm_model}")
    
    def process(
        self,
        request: PromptCompletionRequest,
        user_id: int = None,
        site_id: int = None,
        org_id: int = None
    ) -> PromptCompletionResponse:
        """
        Process a prompt.
        1. Validate (clean and count tokens)
        2. Check with LLM if complete
        3. Save to DB (optional)
        4. Return result
        
        Args:
            request: PromptCompletionRequest
            user_id: User ID (for database)
            site_id: Site ID (for database)
            org_id: Organization ID (for database)
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
            
            if validation_result.is_valid and validation_result.acceptance_value==3:
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
                
                # Step 4: Save to database if enabled
                if self.save_to_db and user_id and site_id and org_id:
                    logger.info("Step 4: Saving to database")
                    try:
                        db_record_id = self.db.save_prompt_completion(
                            response=response,
                            user_id=user_id,
                            site_id=site_id,
                            org_id=org_id,
                            status="APPROVED" if completion_result.is_complete else "REJECTED"
                        )
                        response.request_id = str(db_record_id)  # Use DB ID as request ID
                        logger.info(f"Saved to database with record ID: {db_record_id}")
                    except Exception as db_error:
                        logger.error(f"Prompt CompletionDatabase save failed: {str(db_error)}")
                        # Continue even if DB save fails
                
                logger.info(f"Request {request_id} completed in {processing_time:.2f}ms")
                return response
            else:
                processing_time = (time.time() - start_time) * 1000
                logger.info(f"Step 3: Building response for prompt completion")
                response = PromptCompletionResponse(
                    request_id=request_id,
                    original_prompt=request.prompt,
                    validation_result=validation_result,
                    completion_result=dict({'is_complete': False, 'status': 'invalid response', 'confidence': 0.0}),
                    timestamp=datetime.utcnow(),
                    processing_time_ms=processing_time
                )
                if self.save_to_db and user_id and site_id and org_id:
                    logger.info("Step 4: Saving to database")
                    try:
                        db_record_id = self.db.save_prompt_completion(
                            response=response,
                            user_id=user_id,
                            site_id=site_id,
                            org_id=org_id,
                            status="REJECTED"
                        )
                        response.request_id = str(db_record_id)  # Use DB ID as request ID
                        logger.info(f"Saved to database with record ID: {db_record_id}")
                    except Exception as db_error:
                        logger.error(f"Prompt CompletionDatabase save failed: {str(db_error)}")
                        # Continue even if DB save fails
                
                logger.info(f"Request {request_id} completed in {processing_time:.2f}ms")
                logger.info(f"please enter a valid prompt as the prompt should be minimum{MODEL_NAME_FOR_PROMPT_COMPLETION} and maximum {MODEL_NAME_FOR_PROMPT_COMPLETION} tokens")
                return response
            
        except Exception as e:
            logger.error(f"Error processing request {request_id}: {str(e)}", exc_info=True)
            raise
