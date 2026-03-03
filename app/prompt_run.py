"""
Async Mission Engine with Socket Support
No blocking input()
No decorator inside class
Fully socket-driven human loop
"""

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
from graphdb import Neo4jMissionDB
from correction_layer import (ConnectToDb, GeofenceValidator, CheckThreshold)

LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)


class PromptRunner:
    def __init__(self, user_id: int, org_id: int, site_id: int):
        self.user_id = user_id
        self.org_id = org_id
        self.site_id = site_id

        self.pipeline = PromptCompletionPipeline(
            llm_model=MODEL_NAME_FOR_PROMPT_COMPLETION,
            save_to_db=True
        )
        self.db = PromptCompletionDB()

    def process_prompt(self, prompt: str) -> dict:
        try:
            request = PromptCompletionRequest(
                prompt=prompt,
                user_id=self.user_id
            )

            response = self.pipeline.process(
                request,
                user_id=self.user_id,
                site_id=self.site_id,
                org_id=self.org_id
            )

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
                "error": str(e)
            }
class MissionEngine:
    """
    Async mission engine.
    Maintains session state per socket connection.
    """

    def __init__(self):
        self.sessions = {}

    async def main(self, sid, data):

        prompt = data.get("prompt", "")

        if not prompt:
            return {
                "event": "mission:error",
                "payload": "Prompt is Empty"
            }

        validated = {
            "db_record_id": None,
            "user_id": data["user_id"],
            "site_id": data["site_id"],
            "org_id": data["org_id"],
            "prompt": prompt,
        }

        runner = PromptRunner(
            data["user_id"],
            data["org_id"],
            data["site_id"]
        )

        result = runner.process_prompt(prompt)

        if not result["success"]:
            return {
                "event": "mission:error",
                "payload": result
            }

        # 🔥 CRITICAL FIX — propagate DB record ID
        validated["db_record_id"] = result["db_record_id"]

        # -----------------------------
        # If LLM accepted directly
        # -----------------------------
        if result["status"] == "accepted":
            return await self._continue_pipeline(data, validated)

        # -----------------------------
        # If LLM rejected → human review
        # -----------------------------
        if result["status"] == "rejected":

            self.sessions[sid] = {
                "stage": "waiting_human",
                "data": data,
                "validated": validated
            }

            return {
                "event": "mission:awaiting_human_review",
                "payload": {
                    "request_id": validated["db_record_id"],
                    "mission": validated,
                    "message": "Approve mission? (1=Accept, 2=Reject, 3=Edit)"
                }
            }

        return {
            "event": "mission:error",
            "payload": "Invalid prompt state"
        }

    async def handle_human_reply(self, sid, data):

        session = self.sessions.get(sid)

        if not session:
            return {
                "event": "mission:error",
                "payload": "Session expired"
            }

        choice = str(data.get("choice"))

        validated = session["validated"]
        original_data = session["data"]

        runner = PromptRunner(
            original_data["user_id"],
            original_data["org_id"],
            original_data["site_id"]
        )

        # ---------------- ACCEPT ----------------
        if choice == "1":

            runner.db.update_status_of_prompt(
                validated["db_record_id"],
                "APPROVED"
            )

            del self.sessions[sid]

            return await self._continue_pipeline(original_data, validated)

        # ---------------- REJECT ----------------
        if choice == "2":

            runner.db.update_status_of_prompt(
                validated["db_record_id"],
                "REJECTED"
            )

            del self.sessions[sid]

            return {
                "event": "mission:result",
                "payload": "Prompt rejected by user"
            }

        # ---------------- EDIT ----------------
        if choice == "3":

            return {
                "event": "mission:human_in_the_loop",
                "payload": {
                    "message": "Please enter new prompt"
                }
            }

        return {
            "event": "mission:human_in_the_loop",
            "payload": {
                "message": "Invalid option. Enter 1, 2 or 3"
            }
        }

    async def _continue_pipeline(self, data, validated):

        graphdb = Neo4jMissionDB()
        threshold = CheckThreshold(validated)

        model_select = Selection(validated, data)
        validated = model_select.select_model()

        mission_json = PromptToJsonConvert(validated)
        validated = mission_json.convert()

        graphdb.initialize()
        graphdb.insert_mission(validated)
        graphdb.close()

        connect = ConnectToDb()
        validated = connect.find_waypoint_closest_and_update(validated)

        validator = GeofenceValidator()
        validated = validator.validate(validated)

        validation_result = threshold.check_waypoints()

        # If validation errors exist
        if validation_result["status"] == "need_input":
            return {
                "event": "mission:validation_errors",
                "payload": validation_result
            }

        validated = validation_result["mission"]

        if not validated["model_for_extraction_json_output"]["waypoints"]:
            return {
                "event": "mission:error",
                "payload": "No waypoints given or out of bound"
            }

        return {
            "event": "mission:result",
            "payload": validated
        }