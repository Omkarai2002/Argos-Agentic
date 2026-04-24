"""
Async Mission Engine with Socket Support
No blocking input()
No decorator incide class
Fully socket-driven human loop
"""

import logging
from logging_config import LoggerFeature
from prompt_completion_layer import (
    PromptCompletionPipeline,
    PromptCompletionRequest,
    PromptCompletionDB
)
import os
import json
from jsons import (TEMPLATE)
from validation_layer import (
    EnterDataToJSON,Template)
from intent_understanding import (GpsCalculation,build_app,run_pipeline_intent)
import copy
import asyncio
from mission_classifier_layer.model_selection import Selection
from .config import MODEL_NAME_FOR_PROMPT_COMPLETION
from validation_layer.prompt_to_json_extraction import PromptToJsonConvert
from graphdb import Neo4jMissionDB
from correction_layer import (ConnectToDb, GeofenceValidator, CheckThreshold,match_update)
from intelligence_layer.parameter_model_setup import optimize_parameters
from intelligence_layer.model_setup import add_to_json
from concurrent.futures import ThreadPoolExecutor
from relative_direction import (GpsCalculationRelative,run_pipeline_relative)
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

    async def main(self, cid, data):
        self.loop = asyncio.get_event_loop()
        prompt = data.get("message", "")

        if not prompt:
            return {
                "event": "argos-ai:response",
                "type": "rejected",
                "payload": {"message":"Prompt is Empty",
                "cid":cid
                }
            }

        validated = {
            "db_record_id": None,
            "user_id": data["user_id"],
            "site_id": data["site_id"],
            "org_id": data["organization_id"],
            "prompt": prompt,
        }
        self.emit_progress(data["user_id"],cid, "Starting mission pipeline")
        runner = PromptRunner(
            data["user_id"],
            data["organization_id"],
            data["site_id"]
        )

        result = await asyncio.to_thread(
            runner.process_prompt,
            prompt
        )

        if not result["success"]:
            return {
                "event": "argos-ai:response",
                "type": "rejected",
                "payload": {
                    "message":str(result),
                "cid":cid
                }
            }

        # CRITICAL FIX — propagate DB record ID
        validated["db_record_id"] = result["db_record_id"]

        # -----------------------------
        # If LLM accepted directly
        # -----------------------------
        if result["status"] == "accepted":
            self.emit_progress(data["user_id"],cid, "prompt accepted by the user")
            return await asyncio.to_thread(
            self._continue_pipeline_sync,
            data,
            validated,
            cid
        )

        # -----------------------------
        # If LLM rejected → human review
        # -----------------------------
        if result["status"] == "rejected":

            self.sessions[cid] = {
                "stage": "waiting_human",
                "data": data,
                "validated": validated
            }
            self.emit_progress(data["user_id"],cid, "prompt rejected by the system")
            return {
                "event": "argos-ai:action",
                "type": "validate",
                "payload": {
                    "params": {
                        1: "Accept",
                        2: 'Reject',
                        3: 'Edit'
                    },
                    "request_id": validated["db_record_id"],
                    "mission": validated,
                    "message": "Approve mission? (1=Accept, 2=Reject, 3=Edit)",
                    "cid":cid
                }
            }

        return {
            "event": "argos-ai:response",
            "type": "rejected",
            "payload": {"message":"Invalid prompt state",
                        "cid":cid
                        }
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

    async def handle_validate_action(self, cid, data):

        session = self.sessions.get(cid)
        
        if not session:
            return {
                "event": "argos-ai:response",
                "type": "rejected",
                "payload": {"message":"session expired",
                            "cid":cid
                            }
            }

        choice = str(data.get("param"))
        print("choice_from_argos:",choice)
        validated = session["validated"]
        original_data = session["data"]
        print("original_data",original_data)

        runner = PromptRunner(
            original_data["user_id"],
            original_data["organization_id"],
            original_data["site_id"]
        )

        # ---------------- ACCEPT ----------------
        if choice == "1":

            runner.db.update_status_of_prompt(
                validated["db_record_id"],
                "APPROVED"
            )

            del self.sessions[cid]
            return await asyncio.to_thread(
                self._continue_pipeline_sync,
                original_data,
                validated,
                cid
            )
            
        

        # ---------------- REJECT ----------------
        if choice == "2":

            runner.db.update_status_of_prompt(
                validated["db_record_id"],
                "REJECTED"
            )

            del self.sessions[cid]

            return {
                "event": "argos-ai:response",
                "type":"rejected",
                "payload": {"message":"Prompt rejected by user",
                            "cid":cid
                            }
            }

        # ---------------- EDIT ----------------
        if choice == "3":

            return {
                "event": "argos-ai:action",
                "type":"retry",
                "payload": {
                    "message": "Please enter new prompt",
                    "cid":cid,
                    "params":None
                }
            }

        return {
            "event": "argos-ai:action",
            "type":"validate",
            "payload": {
                "params": {
                    1: "Accept",
                    2: 'Reject',
                    3: 'Edit'
                },
                "message": "Invalid option. Enter 1, 2 or 3",
                "cid":cid
            }
        }
    async def handle_location_action(self, cid, data):

        session = self.sessions.get(cid)

        if not session:
            return {
                "event": "argos-ai:response",
                "type":"rejected",
                "payload": {
                    "message": "Session expired",
                    "cid": cid
                }
            }

        mission = session["mission"]
        location_name = data.get("param", { 'name': '' })['name']

        if not location_name:
            return {
                "event": "argos-ai:response",
                "type":"rejected",
                "payload": {
                    "message": "No location provided",
                    "cid": cid
                }
            }

        # ---------------------------------------------------
        # STEP 1: Always recompute missing waypoint (CRITICAL)
        # ---------------------------------------------------
        threshold = CheckThreshold(mission)
        result = threshold.check_waypoints()
        print("result_status:",result["status"])
        if result["status"] != "need_location":
            # Nothing to fix, just continue pipeline
            validated = result["mission"]
        else:
            waypoint_index = result["waypoint_index"]

            waypoints = mission["model_for_extraction_json_output"].get("waypoints", [])

            if not waypoints:
                return {
                    "event": "argos-ai:response",
                    "type":"rejected",
                    "payload": {
                        "message": "Mission has no waypoints.",
                        "cid": cid
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
                    "event": "argos-ai:action",
                    "type": "location",
                    "payload": {
                        "message": result["message"],
                        "cid": cid,
                        "params":None
                    }
                }

            validated = result["mission"]

        # ---------------------------------------------------
        # STEP 6: Final success
        # ---------------------------------------------------
        del self.sessions[cid]

        print("Sending mission result to frontend")

        return {
            "event": "argos-ai:result",
            "type": "success",
            "payload": validated["model_for_extraction_json_output"],
            "cid": cid
        }
    
    def emit_progress(self, user_id,cid, message):
        asyncio.run_coroutine_threadsafe(
            self.sio.emit(
                "argos-ai:progress",
                {"message": message,"cid":cid,"user_id":user_id},
            ),
            self.loop
        )
    def save_entry(new_data):
        # Load existing data
        if os.path.exists(FILE_PATH):
            with open(FILE_PATH, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        # Add serial number
        serial_no = len(data) + 1

        entry = {
            "serial_no": serial_no,
            "data": new_data
        }

        data.append(entry)

        # Write back with formatting
        with open(FILE_PATH, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Entry {serial_no} saved")
    def run_optimization(self,local_validated):
            v = add_to_json(local_validated)
            v = optimize_parameters(v)
            return v
    
    def _continue_pipeline_sync(self, data, validated,cid):
        self.emit_progress(data["user_id"],cid, "model selection initiated")
        executor = ThreadPoolExecutor(max_workers=1)
        model_select = Selection(validated, data)
        validated = model_select.select_model()
        future = executor.submit(self.run_optimization, copy.deepcopy(validated))
        if validated["category"]=="absolute_location":
            graphdb = Neo4jMissionDB()
            print("🔥 FUNCTION CALLED")
            print("model_selection:",validated)
            self.emit_progress(data["user_id"],cid, "model selected")
            mission_json = PromptToJsonConvert(validated)
            validated = mission_json.convert()
            self.emit_progress(data["user_id"],cid, "mission added to the graph db")
            graphdb.initialize()
            graphdb.insert_mission(validated)
            graphdb.close()
            self.emit_progress(data["user_id"],cid, "Running geofence validation")
            connect = ConnectToDb()
            validated = connect.find_waypoint_closest_and_update(validated)
            print("validated_closest_waypoint:",validated)
            self.emit_progress(data["user_id"],cid, "Running threshold checks")
            validator = GeofenceValidator()
            validated = validator.validate(validated)
            print("geofence_validator:",validated)
            optimized_validated = future.result()
            print("optimized_validated",optimized_validated["final_result"])
            try:
                validated=match_update(validated,optimized_validated["final_result"])
                print("matched:",validated)
            except:
                validated=validated
            threshold = CheckThreshold(validated)

            result = threshold.check_waypoints()
            print("validated_result:",result)
            if result["mission"]["model_for_extraction_json_output"]["type"]=="point" and len(result["mission"]["model_for_extraction_json_output"]["waypoints"])>=2:
                result["mission"]["model_for_extraction_json_output"]["type"]="path"
            if result["mission"]["model_for_extraction_json_output"]["type"]=="path" and len(result["mission"]["model_for_extraction_json_output"]["waypoints"])<=1:
                result["mission"]["model_for_extraction_json_output"]["type"]="point"  
            def save_entry(new_data):
                # Load existing data
                if os.path.exists("output/absolute.json"):
                    with open("output/absolute.json", "r") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = []
                else:
                    data = []

                # Add serial number
                serial_no = len(data) + 1

                entry = {
                    "serial_no": serial_no,
                    "data": new_data
                }

                data.append(entry)

                # Write back with formatting
                with open("output/absolute.json", "w") as f:
                    json.dump(data, f, indent=2)
            save_entry(result)

        if validated["category"]=="relative_direction":
            validated["dock_coordinates"] = {
        "lat": 19.95868,
        "lon": 73.75717
    }   
            pipeline_output = run_pipeline_relative(validated["prompt"])
            print("pipeline_ouput",pipeline_output)
            validated["model_for_extraction_json_output"] = pipeline_output.copy()
            print("validated_first:",validated)
            validated["category"]="relative_direction"
            gps = GpsCalculationRelative()
            validated = gps.indivisual_waypoint_gps_fetch(validated)
            print("validated_geofence:",validated)
            output_from_json=EnterDataToJSON()
            extracted_json = copy.deepcopy(TEMPLATE)
            validated["model_for_extraction_json_output"] =output_from_json.parse_json(validated, extracted_json)
            print("validated_extracted_json:",validated["model_for_extraction_json_output"])
            validator = GeofenceValidator()
            validated = validator.validate(validated)
            print("validated_geo:",validated)
            threshold = CheckThreshold(validated)
            result = threshold.check_waypoints()
            print("validated_result:",result)
            if result["mission"]["model_for_extraction_json_output"]["type"]=="point" and len(result["mission"]["model_for_extraction_json_output"]["waypoints"])>=2:
                result["mission"]["model_for_extraction_json_output"]["type"]="path"
            if result["mission"]["model_for_extraction_json_output"]["type"]=="path" and len(result["mission"]["model_for_extraction_json_output"]["waypoints"])<=1:
                result["mission"]["model_for_extraction_json_output"]["type"]="point"  
            def save_entry(new_data):
                # Load existing data
                if os.path.exists("output/relative.json"):
                    with open("output/relative.json", "r") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = []
                else:
                    data = []

                # Add serial number
                serial_no = len(data) + 1

                entry = {
                    "serial_no": serial_no,
                    "data": new_data
                }

                data.append(entry)

                # Write back with formatting
                with open("output/absolute.json", "w") as f:
                    json.dump(data, f, indent=2)
            save_entry(result)
        if validated["category"]=="intent_understanding":
            validated["dock_coordinates"] = {
        "lat": 19.95868,
        "lon": 73.75717
    }   
            pipeline_output = run_pipeline_intent(validated)
            validated["model_for_extraction_json_output"] = pipeline_output.copy()
        
            validated["category"]="intent_understanding"
            print("validated_first:",validated)
            gps = GpsCalculation()
            validated = gps.indivisual_waypoint_gps_fetch(validated)
            print("validated:",validated)
            output_from_json=EnterDataToJSON()
            extracted_json = copy.deepcopy(TEMPLATE)
            validated["model_for_extraction_json_output"] =output_from_json.parse_json(validated, extracted_json)
            validator = GeofenceValidator()
            validated = validator.validate(validated)
            threshold = CheckThreshold(validated)
            result = threshold.check_waypoints()
            print("validated_result:",result)
            if result["mission"]["model_for_extraction_json_output"]["type"]=="point" and len(result["mission"]["model_for_extraction_json_output"]["waypoints"])>=2:
                result["mission"]["model_for_extraction_json_output"]["type"]="path"
            if result["mission"]["model_for_extraction_json_output"]["type"]=="path" and len(result["mission"]["model_for_extraction_json_output"]["waypoints"])<=1:
                result["mission"]["model_for_extraction_json_output"]["type"]="point"  
            def save_entry(new_data):
                # Load existing data
                if os.path.exists("output/intent.json"):
                    with open("output/intent.json", "r") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = []
                else:
                    data = []

                # Add serial number
                serial_no = len(data) + 1

                entry = {
                    "serial_no": serial_no,
                    "data": new_data
                }

                data.append(entry)

                # Write back with formatting
                with open("output/intent.json", "w") as f:
                    json.dump(data, f, indent=2)
            save_entry(result)
            


            
        self.emit_progress(data["user_id"],cid, "Mission pipeline complete")
        if result["status"] == "need_location":

            self.sessions[cid] = {
                "stage": "waiting_location",
                "waypoint_index": result["waypoint_index"],
                "mission": result["mission"],
                "data": data
            }

            return {
                "event": "argos-ai:action",
                "type": "location",
                "payload": {
                    "message": result["message"],
                    "cid":cid,
                    "params":None
                }
            }

        validated = result["mission"]
        validated=validated
        print("validate_last:",validated)
        if not validated["model_for_extraction_json_output"]["waypoints"]:
            return {
                "event": "argos-ai:response",
                "type": "rejected",
                "payload": {"message":"No waypoints given or out of bound",
                "cid":cid}
            }

        return {
            "event": "argos-ai:response",
            "type": "success",
            "payload": validated["model_for_extraction_json_output"],
            "cid":cid
        }