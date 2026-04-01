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
import asyncio
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

    def __init__(self,sio):
        self.sio=sio
        self.sessions = {}
        self.loop = asyncio.get_event_loop()
    async def main(self, sid, data):

        prompt = data.get("prompt", "")

        if not prompt:
            return {
                "event": "mission:error",
                "payload": "Prompt is Empty",
                "sid":sid
            }

        validated = {
            "db_record_id": None,
            "user_id": data["user_id"],
            "site_id": data["site_id"],
            "org_id": data["org_id"],
            "prompt": prompt,
        }
        self.emit_progress(sid, "Starting mission pipeline")
        runner = PromptRunner(
            data["user_id"],
            data["org_id"],
            data["site_id"]
        )

        result = await asyncio.to_thread(
            runner.process_prompt,
            prompt
        )

        if not result["success"]:
            return {
                "event": "mission:error",
                "payload": result,
                "sid":sid
            }

        # CRITICAL FIX — propagate DB record ID
        validated["db_record_id"] = result["db_record_id"]

        # -----------------------------
        # If LLM accepted directly
        # -----------------------------
        if result["status"] == "accepted":
            self.emit_progress(sid, "prompt accepted by the user")
            return await asyncio.to_thread(
            self._continue_pipeline_sync,
            data,
            validated,
            sid
        )

        # -----------------------------
        # If LLM rejected → human review
        # -----------------------------
        if result["status"] == "rejected":

            self.sessions[sid] = {
                "stage": "waiting_human",
                "data": data,
                "validated": validated
            }
            self.emit_progress(sid, "prompt rejected by the system")
            return {
                "event": "mission:awaiting_human_review",
                "payload": {
                    "request_id": validated["db_record_id"],
                    "mission": validated,
                    "message": "Approve mission? (1=Accept, 2=Reject, 3=Edit)",
                    "sid":sid
                }
            }

        return {
            "event": "mission:error",
            "payload": {"message":"Invalid prompt state",
                        "sid":sid}
        }
    def set_nested_value(self, obj, path, value):

        keys = path.split(".")
        ref = obj

        for k in keys[:-1]:

            if k.isdigit():
                ref = ref[int(k)]
            else:
                ref = ref[k]

        last = keys[-1]

        if last.isdigit():
            ref[int(last)] = value
        else:
            ref[last] = value

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
            return await asyncio.to_thread(
            self._continue_pipeline_sync,
            original_data,
            validated,
            sid
        )
            
        

        # ---------------- REJECT ----------------
        if choice == "2":

            runner.db.update_status_of_prompt(
                validated["db_record_id"],
                "REJECTED"
            )

            del self.sessions[sid]

            return {
                "event": "mission:result",
                "payload": {"message":"Prompt rejected by user",
                            "sid":sid}
            }

        # ---------------- EDIT ----------------
        if choice == "3":

            return {
                "event": "mission:human_in_the_loop",
                "payload": {
                    "message": "Please enter new prompt",
                    "sid":sid
                }
            }

        return {
            "event": "mission:human_in_the_loop",
            "payload": {
                "message": "Invalid option. Enter 1, 2 or 3",
                "sid":sid
            }
        }
    async def handle_validation_reply(self, sid, data):

        session = self.sessions.get(sid)

        if not session:
            return {
                "event": "mission:error",
                "payload": {
                    "message": "Session expired",
                    "sid": sid
                }
            }

        mission = session["mission"]
        location_name = data.get("location")

        if not location_name:
            return {
                "event": "mission:error",
                "payload": {
                    "message": "No location provided",
                    "sid": sid
                }
            }

        # ---------------------------------------------------
        # STEP 1: Always recompute missing waypoint (CRITICAL)
        # ---------------------------------------------------
        threshold = CheckThreshold(mission)
        result = threshold.check_waypoints()

        if result["status"] != "need_location":
            # Nothing to fix, just continue pipeline
            validated = result["mission"]
        else:
            waypoint_index = result["waypoint_index"]

            waypoints = mission["model_for_extraction_json_output"].get("waypoints", [])

            if not waypoints:
                return {
                    "event": "mission:error",
                    "payload": {
                        "message": "Mission has no waypoints.",
                        "sid": sid
                    }
                }

            # Safety fallback
            if waypoint_index >= len(waypoints):
                waypoint_index = 0

            print("FIXING WAYPOINT INDEX:", waypoint_index)

            # ---------------------------------------------------
            # STEP 2: Apply user input to correct waypoint
            # ---------------------------------------------------
            waypoints[waypoint_index]["location"] = location_name

            print("AFTER USER INPUT:", waypoints[waypoint_index])

            # ---------------------------------------------------
            # STEP 3: Convert location → coordinates
            # ---------------------------------------------------
            connect = ConnectToDb()
            mission = connect.find_waypoint_closest_and_update(mission)

            print("AFTER DB UPDATE:", mission["model_for_extraction_json_output"]["waypoints"])

            # ---------------------------------------------------
            # STEP 4: Re-run validations
            # ---------------------------------------------------
            validator = GeofenceValidator()
            mission = validator.validate(mission)

            threshold = CheckThreshold(mission)
            result = threshold.check_waypoints()

            print("DEBUG threshold result:", result)

            # ---------------------------------------------------
            # STEP 5: If still missing → ask again (NEXT waypoint)
            # ---------------------------------------------------
            if result["status"] == "need_location":

                # Update session with NEW missing index
                session["mission"] = mission

                return {
                    "event": "mission:validation_errors",
                    "payload": {
                        "message": result["message"],
                        "sid": sid
                    }
                }

            validated = result["mission"]

        # ---------------------------------------------------
        # STEP 6: Final success
        # ---------------------------------------------------
        del self.sessions[sid]

        print("Sending mission result to frontend")

        return {
            "event": "mission:result",
            "payload": validated["model_for_extraction_json_output"],
            "sid": sid
        }
    
    def emit_progress(self, sid, message):

        asyncio.run_coroutine_threadsafe(
            self.sio.emit(
                "mission:progress",
                {"step": message,"sid":sid},
                room=sid
            ),
            self.loop
        )
    def _continue_pipeline_sync(self, data, validated,sid):
        self.emit_progress(sid, "model selection initiated")
        graphdb = Neo4jMissionDB()

        model_select = Selection(validated, data)
        validated = model_select.select_model()
        self.emit_progress(sid, "model selected")
        mission_json = PromptToJsonConvert(validated)
        validated = mission_json.convert()
        self.emit_progress(sid, "mission added to the graph db")
        graphdb.initialize()
        graphdb.insert_mission(validated)
        graphdb.close()
        self.emit_progress(sid, "Running geofence validation")
        connect = ConnectToDb()
        validated = connect.find_waypoint_closest_and_update(validated)
        print("validated_closest_waypoint:",validated)
        self.emit_progress(sid, "Running threshold checks")
        validator = GeofenceValidator()
        validated = validator.validate(validated)
        threshold = CheckThreshold(validated)
        result = threshold.check_waypoints()
        self.emit_progress(sid, "Mission pipeline complete")
        if result["status"] == "need_location":

            self.sessions[sid] = {
                "stage": "waiting_location",
                "waypoint_index": result["waypoint_index"],
                "mission": result["mission"],
                "data": data
            }

            return {
                "event": "mission:validation_errors",
                "payload": {
                    "message": result["message"],
                    "sid":sid
                }
            }

        validated = result["mission"]
        validated=validated
        if not validated["model_for_extraction_json_output"]["waypoints"]:
            return {
                "event": "mission:error",
                "payload": {"message":"No waypoints given or out of bound",
                "sid":sid}
            }

        return {
            "event": "mission:result",
            "payload": validated["model_for_extraction_json_output"],
            "sid":sid
        }