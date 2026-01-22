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
    token_count: int
    cleaned_prompt: str
    validation_errors: list = []


# LLM Check Result
class CompletionCheckResult(BaseModel):
    status: str  # "accepted" or "rejected"
    is_complete: bool
    confidence: float
    

# Request
class PromptCompletionRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = None
    context: Optional[Dict] = None


# Response
class PromptCompletionResponse(BaseModel):
    request_id: str
    original_prompt: str
    validation_result: PromptValidationResult
    completion_result: CompletionCheckResult
    timestamp: datetime
    processing_time_ms: float
