"""
Simple prompt completion runner with database integration.
Validates prompts and saves results to local PostgreSQL database.
"""
import json
import logging
from logging_config import LoggerFeature
from prompt_completion_layer import (
    PromptCompletionPipeline,
    PromptCompletionRequest,
    PromptCompletionDB
)
from mission_classifier_layer.model_selection import Selection
from .config import MODEL_NAME_FOR_PROMPT_COMPLETION
from validation_layer.prompt_to_json_extraction import PromptToJsonConvert
LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)



class PromptRunner:
    """Simple runner for prompt completion with DB integration."""
    
    def __init__(self, user_id: int, org_id: int, site_id: int):
        """Initialize runner with user context."""
        self.user_id = user_id
        self.org_id = org_id
        self.site_id = site_id
        self.pipeline = PromptCompletionPipeline(
            llm_model=MODEL_NAME_FOR_PROMPT_COMPLETION,
            save_to_db=True
        )
        self.db = PromptCompletionDB()
        logger.info(f"PromptRunner initialized for user {user_id}")
    
    def process_prompt(self, prompt: str) -> dict:
        """
        Process a prompt and save to database.
        
        Args:
            prompt: The prompt to process
            
        Returns:
            Dictionary with results
        """
        logger.info(f"Processing prompt for user {self.user_id}")
        
        try:
            # Create request
            request = PromptCompletionRequest(
                prompt=prompt,
                user_id=self.user_id
            )
            
            # Process and save to database
            response = self.pipeline.process(
                request,
                user_id=self.user_id,
                site_id=self.site_id,
                org_id=self.org_id
            )
            
            # Log results
            logger.info(f"Prompt processed: {response.completion_result.status}")
            
            # Return results
            return {
                "success": True,
                "db_record_id": response.request_id,
                "status": response.completion_result.status,
                "is_complete": response.completion_result.is_complete,
                "confidence": response.completion_result.confidence,
                "suggestions": response.completion_result.suggestions,
                "processing_time_ms": response.processing_time_ms,
            }
            
        except Exception as e:
            logger.error(f"Error processing prompt: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error" : str(e)
            }

    def human_in_the_loop(self,result,data,validated):
        print("Human-in-the-loop review needed for this prompt.")
        print("Prompt seems to be incomplete or requires additional information.")
        print("Click 1 --> accept the prompt")
        print("Click 2--> reject and reenter the prompt")
        print("Click 3 --> edit the prompt")
        user_input = int(input("Enter your choice (1/2/3): "))
        if user_input == 1:
            print("prompt accepted by user.")
            update_result = self.db.update_status_of_prompt(result['db_record_id'], "APPROVED")
            validated["prompt"]=data["prompt"]
            return 1
        if user_input == 2:
            print("prompt rejected by user.")
            update_result = self.db.update_status_of_prompt(result['db_record_id'], "REJECTED")
            return 2
        if user_input == 3:
            print("prompt editing by user.")
            new_prompt = input("Re-enter the prompt: ")

            update_result = self.db.update_prompt_final(result['db_record_id'], new_prompt, "APPROVED")
            validated["prompt"]=new_prompt
            return 3

def main(data,validated):
    """Main entry point - process a test prompt."""
    # Create runner with test user context
    runner = PromptRunner(data["user_id"], data["org_id"], data["site_id"])
    
    # Test prompt
    prompt = data["prompt"]
    
    # Process
    print("\n" + "="*60)
    print("Processing Prompt with Database Integration")
    print("="*60)
    
    result = runner.process_prompt(prompt)
    logger.info(f"\nResult Dictionary: {result}")
    print(f"\nResult Dictionary: {result}")
    if result["status"] =="accepted":
    # Display results
        if result["success"]:
            print(f"\n✓ Prompt Completion Result:")
            print(f"  DB Record ID: {result['db_record_id']}")
            print(f"  Status: {result['status']}")
            print(f"  Complete: {result['is_complete']}")
            print(f"  Confidence: {result['confidence']}")
            validated["prompt"]=prompt
            validated["db_record_id"] = result['db_record_id']
            if result['suggestions']:
                print(f"  Suggestions: {result['suggestions']}")
            print(f"  Processing Time: {result['processing_time_ms']:.2f}ms")
            model_select=Selection(validated,data)
            validated=model_select.select_model()
            mission_json=PromptToJsonConvert(validated)
            validated=mission_json.convert()
            return validated
        else:
            print(f"\n✗ Error: {result['error']}")

        print("="*60 + "\n")
    elif result["status"] =="rejected":
        runner.human_in_the_loop(result,data,validated)
        validated["db_record_id"] = result['db_record_id']
        return validated
    else:
        print("Enter the correct prompt ,prompt is out of token limit or incomplete ")


        
if __name__ == "__main__":
    data ={
        "user_id":1,
        "site_id":1,
        "org_id":1,
        "prompt" :"Go to the public park near the main gate on MG Road. Once you reach there, hover above the walking path at a height of around 12 metre and maintain a speed of 13 km/h. Stay in that position for about 3 min before stopping ."
    }
    print(data)
    validated={
        "db_record_id":int,
        "user_id":data["user_id"],
        "site_id":data["site_id"],
        "org_id":data["org_id"],
        "prompt":"",
    }
    a=main(data,validated)
    print(a)
