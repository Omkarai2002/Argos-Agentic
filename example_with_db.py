"""
Example: Save prompt completion results to database.
"""

from prompt_completion_layer import (
    PromptCompletionPipeline,
    PromptCompletionRequest,
    PromptCompletionDB
)
import logging
from logging_config import LoggerFeature

LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Example with database saving."""
    
    # Initialize pipeline with database saving enabled
    pipeline = PromptCompletionPipeline(
        llm_model="gpt-4o-mini",
        save_to_db=True
    )
    
    # Example request
    request = PromptCompletionRequest(
        prompt="Build a Python function that takes a list of numbers and returns sum, average, max, and min values.",
        user_id="user_123"
    )
    
    # Process and save to database
    print("\n" + "="*60)
    print("Processing and Saving to Database")
    print("="*60)
    
    response = pipeline.process(
        request,
        user_id=1,              # Database user ID
        site_id=1,              # Database site ID
        org_id=1                # Database org ID
    )
    
    print(f"\nRequest ID (DB Record): {response.request_id}")
    print(f"Status: {response.completion_result.status}")
    print(f"Complete: {response.completion_result.is_complete}")
    print(f"Confidence: {response.completion_result.confidence}")
    print(f"Processing Time: {response.processing_time_ms:.2f}ms")
    
    # Retrieve record from database
    print("\n" + "="*60)
    print("Retrieving Record from Database")
    print("="*60)
    
    try:
        db = PromptCompletionDB()
        record_id = int(response.request_id)
        record = db.get_prompt_record(record_id)
        
        if record:
            print(f"\nRecord ID: {record['id']}")
            print(f"User ID: {record['user_id']}")
            print(f"Status: {record['status']}")
            print(f"Initial Prompt: {record['initial_prompt'][:50]}...")
            print(f"Created At: {record['created_at']}")
        else:
            print("Record not found")
    except Exception as e:
        logger.error(f"Could not retrieve record: {str(e)}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
