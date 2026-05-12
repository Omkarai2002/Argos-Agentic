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
import os
import json
from jsons import (TEMPLATE)
from validation_layer import (EnterDataToJSON, Template)
from intent_understanding import (GpsCalculation, build_app, run_pipeline_intent)
import copy
import asyncio
from mission_classifier_layer.model_selection import Selection
from .config import MODEL_NAME_FOR_PROMPT_COMPLETION
from validation_layer.prompt_to_json_extraction import PromptToJsonConvert
from graphdb import Neo4jMissionDB
from correction_layer import (ConnectToDb, GeofenceValidator, CheckThreshold, match_update)
from intelligence_layer.parameter_model_setup import optimize_parameters
from intelligence_layer.model_setup import add_to_json
from concurrent.futures import ThreadPoolExecutor
from relative_direction import (GpsCalculationRelative, run_pipeline_relative)

# Grid imports
from grid.main import plan_mission
from grid.llm.prompts import (
    _resolve_annotations,
    _resolve_drone_and_camera,
    _parse_flight_params,
    _find_annotation_by_prompt,
)

LoggerFeature.setup_logging()
logger = logging.getLogger(__name__)

SUPPORTED_GRID_SHAPES = {"polygon", "circle", "rectangle"}


# ── Grid Validation ───────────────────────────────────────────────

class ValidationCode:
    LOCATION_NOT_FOUND = "location_not_found"
    ALTITUDE_MISSING   = "altitude_missing"
    NO_DRONE_BOUND     = "no_drone_bound"
    ALTITUDE_EXCEEDED  = "altitude_exceeded"
    UNSUPPORTED_SHAPE  = "unsupported_shape"


def _validate_grid_request(validated: dict) -> list[dict]:
    """
    Returns list of issues. Empty = all good.
    Each issue: { "code": str, "message": str, "options": list }
    """
    issues      = []
    user_prompt = validated.get("user_prompt", "")
    annotations = _resolve_annotations(validated)

    # 1. No annotations at all
    if not annotations:
        issues.append({
            "code":    ValidationCode.LOCATION_NOT_FOUND,
            "message": "No locations found for this site.",
            "options": []
        })
        return issues

    # 2. Location name not found in prompt
    annotation = _find_annotation_by_prompt(user_prompt, annotations)
    if not annotation:
        names = [a["name"] for a in annotations]
        issues.append({
            "code":    ValidationCode.LOCATION_NOT_FOUND,
            "message": "Which area do you want to fly over?",
            "options": names
        })

    # 3. Shape not supported for grid
    if annotation and annotation.get("shape") not in SUPPORTED_GRID_SHAPES:
        valid_names = [
            a["name"] for a in annotations
            if a.get("shape") in SUPPORTED_GRID_SHAPES
        ]
        issues.append({
            "code":    ValidationCode.UNSUPPORTED_SHAPE,
            "message": (
                f"'{annotation['name']}' is a {annotation['shape']} "
                f"which doesn't support grid missions. "
                f"Please choose a polygon, circle, or rectangle."
            ),
            "options": valid_names
        })

    # 4. Altitude missing
    params = _parse_flight_params(user_prompt)
    if not params["altitude_m"]:
        issues.append({
            "code":    ValidationCode.ALTITUDE_MISSING,
            "message": "What altitude should the drone fly at? (in meters)",
            "options": ["10m", "20m", "30m", "50m"]
        })

    # 5. No drone bound to site
    drone_cam = _resolve_drone_and_camera(validated)
    if not drone_cam:
        issues.append({
            "code":    ValidationCode.NO_DRONE_BOUND,
            "message": "No drone with a camera is bound to this site.",
            "options": []
        })

    # 6. Altitude exceeds drone limit
    if drone_cam and params["altitude_m"]:
        max_alt = drone_cam.get("max_altitude", 0)
        if params["altitude_m"] > max_alt:
            issues.append({
                "code":    ValidationCode.ALTITUDE_EXCEEDED,
                "message": (
                    f"Requested altitude {params['altitude_m']}m exceeds "
                    f"drone max altitude of {max_alt}m."
                ),
                "options": [
                    f"{int(max_alt * 0.5)}m",
                    f"{int(max_alt * 0.75)}m",
                    f"{max_alt}m"
                ]
            })

    return issues


# ── Prompt Runner (unchanged) ─────────────────────────────────────

class PromptRunner:
    def __init__(self, user_id: int, org_id: int, site_id: int):
        self.user_id  = user_id
        self.org_id   = org_id
        self.site_id  = site_id

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
                "success":         True,
                "db_record_id":    response.request_id,
                "status":          response.completion_result.status,
                "is_complete":     response.completion_result.is_complete,
                "confidence":      response.completion_result.confidence,
                "suggestions":     response.completion_result.suggestions,
                "processing_time_ms": response.processing_time_ms,
            }
        except Exception as e:
            logger.error(f"Error processing prompt: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}


# ── Mission Engine ────────────────────────────────────────────────

class MissionEngine:
    """
    Async mission engine.
    Maintains session state per socket connection.
    """

    def __init__(self, sio):
        self.sio      = sio
        self.sessions = {}

    # ── Entry point ───────────────────────────────────────────────

    async def main(self, cid, data):
        self.loop = asyncio.get_event_loop()
        prompt = data.get("message", "")

        if not prompt:
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "Prompt is Empty", "cid": cid}
            }

        # Detect if this is a grid mission
        if self._is_grid_prompt(prompt):
            return await self._handle_grid(cid, data, prompt)

        # ── Existing non-grid pipeline ────────────────────────────
        validated = {
            "db_record_id": None,
            "user_id":      data["user_id"],
            "site_id":      data["site_id"],
            "org_id":       data["organization_id"],
            "prompt":       prompt,
        }

        self.emit_progress(data["user_id"], cid, "Starting mission pipeline")

        runner = PromptRunner(
            data["user_id"],
            data["organization_id"],
            data["site_id"]
        )

        result = await asyncio.to_thread(runner.process_prompt, prompt)

        if not result["success"]:
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": str(result), "cid": cid}
            }

        validated["db_record_id"] = result["db_record_id"]

        if result["status"] == "accepted":
            self.emit_progress(data["user_id"], cid, "Prompt accepted")
            return await asyncio.to_thread(
                self._continue_pipeline_sync, data, validated, cid
            )

        if result["status"] == "rejected":
            self.sessions[cid] = {
                "stage":     "waiting_human",
                "data":      data,
                "validated": validated
            }
            self.emit_progress(data["user_id"], cid, "Prompt rejected by system")
            return {
                "event": "argos-ai:action",
                "type":  "validate",
                "payload": {
                    "params": {1: "Accept", 2: "Reject", 3: "Edit"},
                    "request_id": validated["db_record_id"],
                    "mission":    validated,
                    "message":    "Approve mission? (1=Accept, 2=Reject, 3=Edit)",
                    "cid":        cid
                }
            }

        return {
            "event": "argos-ai:response",
            "type":  "rejected",
            "payload": {"message": "Invalid prompt state", "cid": cid}
        }

    # ── Grid handling ─────────────────────────────────────────────

    def _is_grid_prompt(self, prompt: str) -> bool:
        keywords = ["grid", "survey", "map", "mapping", "coverage", "scan", "aerial survey"]
        return any(k in prompt.lower() for k in keywords)

    def _build_grid_validated(self, data: dict, prompt: str) -> dict:
        return {
            "site_id":     data.get("site_id"),
            "user_id":     data.get("user_id"),
            "org_id":      data.get("organization_id"),
            "user_prompt": prompt,
            "data":        data.get("user", {}),  # ← full org/site/drone JSON from cache
        }

    async def _handle_grid(self, cid: str, data: dict, prompt: str) -> dict:

        validated = self._build_grid_validated(data, prompt)

        self.emit_progress(data["user_id"], cid, "Validating grid mission request")

        issues = _validate_grid_request(validated)

        if issues:
            issue = issues[0]  # handle one at a time

            # Store session so we can resume after user replies
            self.sessions[cid] = {
                "stage":         "grid_waiting",
                "pending_issue": issue["code"],
                "validated":     validated,
                "data":          data,
            }

            self.emit_progress(data["user_id"], cid, "Waiting for user input")

            # Use action:location for location issues, action:validate for others
            event_type = (
                "location"
                if issue["code"] in (
                    ValidationCode.LOCATION_NOT_FOUND,
                    ValidationCode.UNSUPPORTED_SHAPE
                )
                else "validate"
            )

            return {
                "event": "argos-ai:action",
                "type":  event_type,
                "payload": {
                    "message": issue["message"],
                    "cid":     cid,
                    "params":  issue["options"] if issue["options"] else None
                }
            }

        # All validated — run planner
        self.emit_progress(data["user_id"], cid, "Planning grid mission")

        try:
            result = await asyncio.to_thread(plan_mission, validated)

            self.emit_progress(data["user_id"], cid, "Grid mission ready")

            return {
                "event": "argos-ai:response",
                "type":  "success",
                "payload": result.model_dump()
            }

        except Exception as e:
            logger.error(f"Grid mission failed: {e}", exc_info=True)
            return {
                "event": "argos-ai:response",
                "type":  "error",
                "payload": {"message": f"Mission planning failed: {str(e)}", "cid": cid}
            }

    # ── Human-in-loop handlers ────────────────────────────────────

    async def handle_location_action(self, cid, data):

        session = self.sessions.get(cid)
        if not session:
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "Session expired", "cid": cid}
            }

        # ── Grid location reply ───────────────────────────────────
        if session.get("stage") == "grid_waiting":
            chosen    = data.get("param", "") or data.get("message", "")
            if isinstance(chosen, dict):
                chosen = chosen.get("name", "")

            validated = session["validated"]
            issue     = session["pending_issue"]

            if issue == ValidationCode.LOCATION_NOT_FOUND:
                validated["user_prompt"] += f" for {chosen}"
            elif issue == ValidationCode.UNSUPPORTED_SHAPE:
                # Replace old location reference with new one
                validated["user_prompt"] += f" for {chosen}"

            del self.sessions[cid]
            return await self._handle_grid(cid, session["data"], validated["user_prompt"])

        # ── Existing location action (path/point) ─────────────────
        print("handle_location_action_triggered")
        mission       = session["mission"]
        location_name = data.get("param", {"name": ""})

        if isinstance(location_name, dict):
            location_name = location_name.get("name", "")

        if not location_name:
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "No location provided", "cid": cid}
            }

        waypoint_index = session.get("waypoint_index", 0)
        waypoints      = mission["model_for_extraction_json_output"].get("waypoints", [])

        if not waypoints or waypoint_index >= len(waypoints):
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "Invalid waypoint index", "cid": cid}
            }

        waypoints[waypoint_index]["location"] = location_name

        connect  = ConnectToDb()
        mission  = connect.find_waypoint_closest_and_update(mission)
        validator = GeofenceValidator()
        mission  = validator.validate(mission)
        session["mission"] = mission

        threshold = CheckThreshold(mission)
        result    = threshold.check_waypoints()

        if result["status"] == "need_location":
            session["waypoint_index"] = result["waypoint_index"]
            session["mission"]        = result["mission"]
            return {
                "event": "argos-ai:action",
                "type":  "location",
                "payload": {
                    "message": result["message"],
                    "cid":     cid,
                    "params":  None
                }
            }

        del self.sessions[cid]
        validated = result["mission"]
        output    = validated["model_for_extraction_json_output"]

        if output["type"] == "point" and len(output.get("waypoints", [])) >= 2:
            output["type"] = "path"
        elif output["type"] == "path" and len(output.get("waypoints", [])) <= 1:
            output["type"] = "point"

        return {
            "event": "argos-ai:response",
            "type":  "success",
            "payload": output,
            "cid":     cid
        }

    async def handle_validate_action(self, cid, data):

        session = self.sessions.get(cid)
        if not session:
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "Session expired", "cid": cid}
            }

        # ── Grid validate reply ───────────────────────────────────
        if session.get("stage") == "grid_waiting":
            user_reply = data.get("param", "") or data.get("message", "")
            validated  = session["validated"]
            issue      = session["pending_issue"]

            if issue == ValidationCode.ALTITUDE_MISSING:
                validated["user_prompt"] += f" at altitude {user_reply}"
            elif issue == ValidationCode.ALTITUDE_EXCEEDED:
                validated["user_prompt"] += f" at altitude {user_reply}"

            del self.sessions[cid]
            return await self._handle_grid(cid, session["data"], validated["user_prompt"])

        # ── Existing validate action (path/point) ─────────────────
        choice    = str(data.get("param"))
        validated = session["validated"]
        original_data = session["data"]

        runner = PromptRunner(
            original_data["user_id"],
            original_data["organization_id"],
            original_data["site_id"]
        )

        if choice == "1":
            runner.db.update_status_of_prompt(validated["db_record_id"], "APPROVED")
            del self.sessions[cid]
            return await asyncio.to_thread(
                self._continue_pipeline_sync, original_data, validated, cid
            )

        if choice == "2":
            runner.db.update_status_of_prompt(validated["db_record_id"], "REJECTED")
            del self.sessions[cid]
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "Prompt rejected by user", "cid": cid}
            }

        if choice == "3":
            return {
                "event": "argos-ai:action",
                "type":  "retry",
                "payload": {"message": "Please enter new prompt", "cid": cid, "params": None}
            }

        return {
            "event": "argos-ai:action",
            "type":  "validate",
            "payload": {
                "params":  {1: "Accept", 2: "Reject", 3: "Edit"},
                "message": "Invalid option. Enter 1, 2 or 3",
                "cid":     cid
            }
        }

    # ── Helpers ───────────────────────────────────────────────────

    def _is_grid_prompt(self, prompt: str) -> bool:
        keywords = ["grid", "survey", "map", "mapping", "coverage", "scan", "aerial survey"]
        return any(k in prompt.lower() for k in keywords)

    def emit_progress(self, user_id, cid, message):
        asyncio.run_coroutine_threadsafe(
            self.sio.emit(
                "argos-ai:progress",
                {"message": message, "cid": cid, "user_id": user_id},
            ),
            self.loop
        )

    def set_nested_value(self, obj, path, value):
        keys = path.split(".")
        ref  = obj
        for k in keys[:-1]:
            ref = ref[int(k)] if k.isdigit() else ref[k]
        last = keys[-1]
        if last.isdigit():
            ref[int(last)] = value
        else:
            ref[last] = value

    def run_optimization(self, local_validated):
        try:
            v = add_to_json(local_validated)
            v = optimize_parameters(v)
            return v
        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            return local_validated

    # ── Existing pipeline (unchanged) ─────────────────────────────

    def _continue_pipeline_sync(self, data, validated, cid):
        self.emit_progress(data["user_id"], cid, "Model selection initiated")
        executor     = ThreadPoolExecutor(max_workers=1)
        model_select = Selection(validated, data)
        validated    = model_select.select_model()
        future       = executor.submit(self.run_optimization, copy.deepcopy(validated))

        if validated["category"] == "absolute_location":
            graphdb = Neo4jMissionDB()
            self.emit_progress(data["user_id"], cid, "Model selected")
            mission_json = PromptToJsonConvert(validated)
            validated    = mission_json.convert()
            self.emit_progress(data["user_id"], cid, "Mission added to graph DB")
            graphdb.initialize()
            graphdb.insert_mission(validated)
            graphdb.close()
            self.emit_progress(data["user_id"], cid, "Running geofence validation")
            connect   = ConnectToDb()
            validated = connect.find_waypoint_closest_and_update(validated)
            validator = GeofenceValidator()
            validated = validator.validate(validated)

            try:
                optimized = future.result(timeout=5)
                try:
                    validated = match_update(validated, optimized["final_result"])
                except Exception as e:
                    print(f"match_update failed: {e}")
            except Exception as e:
                print(f"Optimization timed out: {e}")

            threshold = CheckThreshold(validated)
            result    = threshold.check_waypoints()

            if result["mission"]["model_for_extraction_json_output"]["type"] == "point" \
                    and len(result["mission"]["model_for_extraction_json_output"]["waypoints"]) >= 2:
                result["mission"]["model_for_extraction_json_output"]["type"] = "path"
            if result["mission"]["model_for_extraction_json_output"]["type"] == "path" \
                    and len(result["mission"]["model_for_extraction_json_output"]["waypoints"]) <= 1:
                result["mission"]["model_for_extraction_json_output"]["type"] = "point"

            self._save_entry(result, "output/absolute.json")

        elif validated["category"] == "relative_direction":
            validated["dock_coordinates"] = {"lat": 19.966591, "lon": 73.667184}
            pipeline_output = run_pipeline_relative(validated["prompt"])
            validated["model_for_extraction_json_output"] = pipeline_output.copy()
            validated["category"] = "relative_direction"
            gps       = GpsCalculationRelative()
            validated = gps.indivisual_waypoint_gps_fetch(validated)
            output_from_json = EnterDataToJSON()
            extracted_json   = copy.deepcopy(TEMPLATE)
            validated["model_for_extraction_json_output"] = output_from_json.parse_json(validated, extracted_json)
            validator = GeofenceValidator()
            validated = validator.validate(validated)
            threshold = CheckThreshold(validated)
            result    = threshold.check_waypoints()

            if result["mission"]["model_for_extraction_json_output"]["type"] == "point" \
                    and len(result["mission"]["model_for_extraction_json_output"]["waypoints"]) >= 2:
                result["mission"]["model_for_extraction_json_output"]["type"] = "path"
            if result["mission"]["model_for_extraction_json_output"]["type"] == "path" \
                    and len(result["mission"]["model_for_extraction_json_output"]["waypoints"]) <= 1:
                result["mission"]["model_for_extraction_json_output"]["type"] = "point"

            self._save_entry(result, "output/relative.json")

        elif validated["category"] == "intent_understanding":
            validated["dock_coordinates"] = {"lat": 19.966591, "lon": 73.667184}
            pipeline_output = run_pipeline_intent(validated)
            validated["model_for_extraction_json_output"] = pipeline_output.copy()
            validated["category"] = "intent_understanding"
            gps       = GpsCalculation()
            validated = gps.indivisual_waypoint_gps_fetch(validated)
            output_from_json = EnterDataToJSON()
            extracted_json   = copy.deepcopy(TEMPLATE)
            validated["model_for_extraction_json_output"] = output_from_json.parse_json(validated, extracted_json)
            validator = GeofenceValidator()
            validated = validator.validate(validated)
            threshold = CheckThreshold(validated)
            result    = threshold.check_waypoints()

            if result["mission"]["model_for_extraction_json_output"]["type"] == "point" \
                    and len(result["mission"]["model_for_extraction_json_output"]["waypoints"]) >= 2:
                result["mission"]["model_for_extraction_json_output"]["type"] = "path"
            if result["mission"]["model_for_extraction_json_output"]["type"] == "path" \
                    and len(result["mission"]["model_for_extraction_json_output"]["waypoints"]) <= 1:
                result["mission"]["model_for_extraction_json_output"]["type"] = "point"

            self._save_entry(result, "output/intent.json")

        self.emit_progress(data["user_id"], cid, "Mission pipeline complete")

        if result["status"] == "need_location":
            self.sessions[cid] = {
                "stage":         "waiting_location",
                "waypoint_index": result["waypoint_index"],
                "mission":        result["mission"],
                "data":           data
            }
            return {
                "event": "argos-ai:action",
                "type":  "location",
                "payload": {
                    "message": result["message"],
                    "cid":     cid,
                    "params":  None
                }
            }

        validated = result["mission"]
        if validated["model_for_extraction_json_output"]["type"] == "point" \
                and len(validated["model_for_extraction_json_output"]["waypoints"]) >= 2:
            validated["model_for_extraction_json_output"]["type"] = "path"
        if validated["model_for_extraction_json_output"]["type"] == "path" \
                and len(validated["model_for_extraction_json_output"]["waypoints"]) <= 1:
            validated["model_for_extraction_json_output"]["type"] = "point"

        if not validated["model_for_extraction_json_output"]["waypoints"]:
            return {
                "event": "argos-ai:response",
                "type":  "rejected",
                "payload": {"message": "No waypoints given or out of bound", "cid": cid}
            }

        return {
            "event": "argos-ai:response",
            "type":  "success",
            "payload": validated["model_for_extraction_json_output"],
            "cid":     cid
        }

    @staticmethod
    def _save_entry(data, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        existing = []
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []
        existing.append({"serial_no": len(existing) + 1, "data": data})
        with open(filepath, "w") as f:
            json.dump(existing, f, indent=2)