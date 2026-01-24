"""
Simple data models for prompt completion layer.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


# Status options
class CompletionStatus:
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# Validation Result
class PromptValidationResult(BaseModel):
    is_valid: bool
    acceptance_value: int
    cleaned_prompt: str
    validation_errors: list = []


# LLM Check Result
class CompletionCheckResult(BaseModel):
    status: str  # "accepted" or "rejected"
    is_complete: bool
    confidence: float
    reasoning: Optional[str] = None
    suggestions: Optional[str] = None
    missing_elements: Optional[list] = None


# Request
class PromptCompletionRequest(BaseModel):
    prompt: str
    user_id: Optional[Any] = None  # Can be int or string
    context: Optional[Dict] = None


# Response
class PromptCompletionResponse(BaseModel):
    request_id: str
    original_prompt: str
    validation_result: PromptValidationResult
    completion_result: CompletionCheckResult
    timestamp: datetime
    processing_time_ms: float
