"""
Simple LLM-based prompt completion checker.
Uses OpenAI to check if prompt is complete and has all necessary info.
"""

import os
import logging
import json
from app.config import OPENAI_API_KEY
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from app.config import OPENAI_API_KEY,MODEL_NAME_FOR_PROMPT_COMPLETION,TEMPERATURE_FOR_PROMPT_COMPLETION
from .models import CompletionCheckResult, CompletionStatus

logger = logging.getLogger(__name__)


class PromptCompletionChecker:
    """Check if prompt is complete using OpenAI."""

    def __init__(self, model_name: str = MODEL_NAME_FOR_PROMPT_COMPLETION):
        self.model_name = model_name
        self.api_key = OPENAI_API_KEY
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found")
        
        # Setup LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=TEMPERATURE_FOR_PROMPT_COMPLETION,
            api_key=self.api_key
        )
        
        logger.info(f"LLM initialized with {model_name}")

    def check_completion(self, prompt: str) -> CompletionCheckResult:
        """
        Check if prompt is complete.
        
        Returns:
            CompletionCheckResult with status and confidence
        """
        try:
            logger.info(f"Checking prompt completion ({len(prompt)} chars)")
            
            # Create the prompt for LLM
            analysis_prompt = f"""Analyze this prompt and decide if it's COMPLETE or NEEDS MORE INFO.

Prompt: {prompt}

Respond in JSON format with:
- is_complete: true/false
- status: "accepted" or "rejected"
- confidence: 0.0 to 1.0


JSON response:"""

            # Call LLM
            response = self.llm.invoke(analysis_prompt)
            
            # Parse response
            result = self._parse_response(response.content)
            
            logger.info(f"Result: {result.status}")
            return result
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return self._error_result(str(e))

    def _parse_response(self, response_text: str) -> CompletionCheckResult:
        """Parse LLM response."""
        try:
            # Extract JSON from response
            json_str = response_text.strip()
            if json_str.startswith('```'):
                json_str = json_str.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
            
            data = json.loads(json_str)
            
            # Extract fields
            is_complete = data.get("is_complete", True)
            status = data.get("status", "accepted")
            confidence = float(data.get("confidence", 0.0))
            
            return CompletionCheckResult(
                status=status,
                is_complete=is_complete,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Parse error: {str(e)}")
            return self._error_result(str(e))

    def _error_result(self, error_msg: str) -> CompletionCheckResult:
        """Return error result."""
        return CompletionCheckResult(
            status="rejected",
            is_complete=False,
            confidence=0.0,
            reasoning=f"Error: {error_msg}",
            suggestions="Please try again"
        )
