"""
LLM-based prompt completion checker using LangChain.
Uses OpenAI with LangChain pipelines for structured analysis.
"""

import os
import logging
import json
from app.config import OPENAI_API_KEY, MODEL_NAME_FOR_PROMPT_COMPLETION, TEMPERATURE_FOR_PROMPT_COMPLETION
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from typing import Optional

from .models import CompletionCheckResult, CompletionStatus

logger = logging.getLogger(__name__)


class CompletionAnalysisOutput(BaseModel):
    """Output schema for LLM response - used by JsonOutputParser."""
    is_complete: bool = Field(description="Whether prompt is complete")
    status: str = Field(description="Status: accepted or rejected")
    confidence: float = Field(description="Confidence score 0-1")
    reasoning: Optional[str] = Field(default=None, description="Reasoning behind decision")
    suggestions: Optional[str] = Field(description="Suggestions for improvement")


class PromptCompletionChecker:
    """Check if prompt is complete using LangChain + OpenAI."""

    # LangChain prompt template
    SYSTEM_PROMPT = """You are a Prompt Completion Analyzer.

Your job is to analyze a user-provided prompt and check whether it is complete based on required parameters.
You must NOT assume or infer any missing information.

Required parameters (in order):

1. Location
   - Check whether a specific location or place name is explicitly mentioned.
   - Examples: park, warehouse, building A, sector 7, GPS coordinates.

2. Action
   - If a location is present, check whether a clear action is specified.
   - Examples: hover, loiter, move, patrol, follow, inspect.

3. Action Attributes
   - If an action is present, check whether at least one measurable attribute is specified.
   - Acceptable attributes:
     - Speed (e.g., 5 m/s, slow, fast)
     - Altitude or height (e.g., 10 m, 50 feet)
     - Distance or range (e.g., 3 m, 3 km)
     - Duration or time (e.g., 5 minutes, 10 seconds)
4. Unit should be specified for each attribute (e.g., metres, m, km, minutes, etc.);it means unit should be assigned after every attribute.

Evaluation rules:
- The prompt is COMPLETE only if all required parameters are present.
- If ANY parameter is missing, the prompt is INCOMPLETE.
- Do not add suggestions that are not directly related to missing parameters.
- Suggestions MUST explicitly state what is missing and why the prompt is incomplete.
- Suggestions must be short, factual, and parameter-focused.

- Qualitative words like "slow", "fast" are NOT valid attributes unless accompanied by a numeric value AND unit like metre,min,km,m etc.
- A numeric value WITHOUT a unit MUST be treated as MISSING.
- Do NOT guess or normalize values.
- If duration is mentioned without a unit, it is INVALID.
- If speed is qualitative only, it is INVALID.
- If ANY attribute violates these rules, the prompt MUST be marked INCOMPLETE.

Output rules:
- Respond ONLY in valid JSON.
- Do not include explanations outside the JSON.
- Do not include extra fields.

Respond in JSON format with:
    - is_complete: true/false
    - status: "accepted" or "rejected"
    - confidence: 0.0 to 1.0
    - suggestions:
        "Missing <parameter>: <reason it is required>"
      


Confidence scoring:
- 0.9–1.0 → All parameters clearly present
- 0.6–0.8 → Parameters present but slightly ambiguous
- 0.0–0.5 → One or more parameters missing
"""

    def __init__(self, model_name: str = MODEL_NAME_FOR_PROMPT_COMPLETION):
        self.model_name = model_name
        self.api_key = OPENAI_API_KEY
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=TEMPERATURE_FOR_PROMPT_COMPLETION,
            api_key=self.api_key
        )
        
        # Setup LangChain pipeline
        self._setup_chain()
        
        logger.info(f"LLM initialized with {model_name}")

    def _setup_chain(self):
        """Setup the complete LangChain pipeline."""
        # Create prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("user", "Analyze this prompt:\n\n{prompt}\n\nRespond in JSON format.")
        ])
        
        # Create parser
        self.parser = JsonOutputParser(pydantic_object=CompletionAnalysisOutput)
        
        # Build the chain: prompt -> LLM -> parser
        self.chain = self.prompt_template | self.llm | self.parser
        
        logger.debug("LangChain pipeline setup complete")

    def check_completion(self, prompt: str) -> CompletionCheckResult:
        """
        Check if prompt is complete using LangChain pipeline.
        
        Args:
            prompt: The prompt to analyze
            
        Returns:
            CompletionCheckResult with status and confidence
        """
        if not prompt or prompt.strip() == "":
            logger.error("Empty prompt provided")
            return self._error_result("Empty prompt provided")
        
        try:
            logger.info(f"Checking prompt completion ({len(prompt)} chars)")
            
            # Invoke the LangChain pipeline
            analysis_output = self.chain.invoke({"prompt": prompt})
            print("analysis_output in prompt_completion_status", analysis_output)
            logger.debug(f"LLM analysis output: {analysis_output}")
            
            # Convert LangChain output to CompletionCheckResult
            result = self._convert_output_to_result(analysis_output)
            print("result in prompt_completion_status", result)
            logger.info(f"Completion check result: {result.status}")
            return result
            
        except Exception as e:
            logger.error(f"Error in check_completion: {str(e)}", exc_info=True)
            return self._error_result(str(e))

    def _convert_output_to_result(self, analysis_output: dict) -> CompletionCheckResult:
        """
        Convert LangChain parser output to CompletionCheckResult.
        
        Args:
            analysis_output: Dictionary from JsonOutputParser
            
        Returns:
            CompletionCheckResult object
        """
        try:
            is_complete = analysis_output.get("is_complete")
            status = analysis_output.get("status")
            confidence = float(analysis_output.get("confidence"))
            #reasoning = analysis_output.get("reasoning")
            suggestions = analysis_output.get("suggestions")
            print("expected :",CompletionCheckResult(status=status,
                is_complete=is_complete,
                confidence=confidence,
                #reasoning=reasoning,
                suggestions=list[suggestions]))
            return CompletionCheckResult(   
                status=status,
                is_complete=is_complete,
                confidence=confidence,
                #reasoning=reasoning,
                suggestions=list[suggestions]
            )
        except Exception as e:
            logger.error(f"Error converting output: {str(e)}")
            print("hi from except")
            return self._error_result(str(e))

    def _error_result(self, error_msg: str) -> CompletionCheckResult:
        """Return error result."""
        return CompletionCheckResult(
            status="rejected",
            is_complete=False,
            confidence=0.0,
            reasoning=[f"Error during analysis: {error_msg}"],
            suggestions=["Please try again or check your prompt"]
        )
