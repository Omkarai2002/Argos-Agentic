import json
import math
from typing import List

from grid.llm.llm_setup import LLMSetup
from grid.location_resolver import LocationResolver
from grid.llm.prompts import (
    build_system_prompt,
    build_user_prompt,
    _resolve_drone_and_camera,
    _parse_flight_params,
    _precompute_mission_params,
    _resolve_annotations,
    _precompute_grid_area,
    _find_annotation_by_prompt,  # ← now imported from prompts
)
from grid.services.schema import CameraSpecs, PrecisionMode, FinishAction


def _get_polygon_points(annotation: dict) -> list:
    shape    = annotation.get("shape")
    geometry = annotation.get("geometry", {})
    coords   = []

    if shape == "polygon":
        coords = geometry.get("hierarchy", [])

    elif shape == "rectangle":
        coords = geometry.get("points", [])

    elif shape == "circle":
        center = geometry.get("center", [])
        radius = geometry.get("radius")

        if center and radius:
            lon, lat   = center[0], center[1]
            num_points = 36
            lat_deg    = radius / 111320
            lon_deg    = radius / (111320 * math.cos(math.radians(lat)))

            for i in range(num_points):
                angle   = math.radians(i * (360 / num_points))
                pt_lon  = lon + lon_deg * math.cos(angle)
                pt_lat  = lat + lat_deg * math.sin(angle)
                coords.append([pt_lon, pt_lat])

            coords.append(coords[0])  # close polygon

    elif shape == "point":
        pos = geometry.get("position", [])
        if pos:
            coords = [pos[:2]]

    return [
        {"sequence": i + 1, "point": list(coord[:2])}
        for i, coord in enumerate(coords)
    ]



def _resolve_dock_info(validated: dict) -> dict:
    data    = validated.get("data", {})
    org     = data.get("organization", {})
    site_id = validated["site_id"]

    site = next((s for s in org.get("sites", []) if s["id"] == site_id), None)
    if not site:
        return {
            "dock_id":        None,
            "can_select_dock": False,
            "is_hidden":      False,
            "is_private":     False,
        }

    bindings          = site.get("binding", [])
    drone_cam         = _resolve_drone_and_camera(validated)
    selected_drone_id = drone_cam.get("drone_id") if drone_cam else None

    dock_id = None
    for b in bindings:
        if b["drone_id"] == selected_drone_id:
            dock_id = b["dock_id"]
            break

    return {
        "dock_id":        dock_id,
        "can_select_dock": len(bindings) > 1,
        "is_hidden":      False,
        "is_private":     False,
    }


def _enforce_computed_values(result, validated: dict):

    drone_cam   = _resolve_drone_and_camera(validated)
    params      = _parse_flight_params(validated.get("user_prompt", ""))
    annotations = _resolve_annotations(validated)
    user_prompt = validated.get("user_prompt", "")

    # --- annotation match ---
    annotation = _find_annotation_by_prompt(user_prompt, annotations)

    # --- grid_config.points = perimeter coordinates ---
    if annotation:
        result.mission_config.grid_config.points = _get_polygon_points(annotation)

    # --- grid_area ---
    if annotation:
        area = _precompute_grid_area(annotation)
        result.mission_config.grid_area = area if area is not None else 0

    # --- camera_specs ---
    if drone_cam:
        result.mission_config.camera_specs = CameraSpecs(
            focalLength  = drone_cam["focal_length_mm"],
            sensorWidth  = drone_cam["sensor_width_mm"],
            sensorHeight = drone_cam["sensor_height_mm"],
            pixelWidth   = drone_cam["image_width_px"],
            pixelHeight  = drone_cam["image_height_px"],
        )

    if not drone_cam or not params["altitude_m"]:
        return result

    computed = _precompute_mission_params(
        drone_cam,
        params["altitude_m"],
        params["front_overlap"],
        params["side_overlap"],
    )

    speed = drone_cam["max_speed"]

    # --- grid_config ---
    result.mission_config.grid_config.gsd   = computed["gsd"]
    result.mission_config.grid_config.angle = result.mission_config.grid_config.angle or 0

    # --- overlaps ---
    result.mission_config.image_overlap.front = params["front_overlap"]
    result.mission_config.image_overlap.side  = params["side_overlap"]

    # --- spacing ---
    result.mission_config.image_spacing.x = computed["spacing_x"]
    result.mission_config.image_spacing.y = computed["spacing_y"]

    # --- trigger ---
    result.mission_config.image_trigger.distance = computed["trigger"]
    result.mission_config.image_trigger.interval = 0
    result.mission_config.image_trigger.images   = 0

    # --- media capture ---
    result.mission_config.media_capture.distance = computed["trigger"]
    result.mission_config.media_capture.mode     = "distance"

    # --- gimbal ---
    result.mission_config.gimbal_settings.pitch = -90
    result.mission_config.gimbal_settings.yaw   = 0

    # --- takeoff ---
    result.takeoff_config.altitude      = params["altitude_m"]
    result.takeoff_config.altitude_mode = "AGL"
    result.takeoff_config.speed         = speed
    result.takeoff_config.actions       = []

    # --- route ---
    result.route_config.altitude      = params["altitude_m"]
    result.route_config.altitude_mode = "AGL"
    result.route_config.speed         = speed
    result.route_config.radius        = 2.0

    # --- always fixed ---
    result.waypoints      = []
    result.total_distance = 0.0
    result.total_duration = 0.0
    result.type           = "grid"

    # --- precision + finish ---
    result.precision_mode = PrecisionMode()
    result.finish_action  = FinishAction()

    # --- dock info ---
    dock_info              = _resolve_dock_info(validated)
    result.dock_id         = dock_info["dock_id"]
    result.can_select_dock = dock_info["can_select_dock"]
    result.is_hidden       = dock_info["is_hidden"]
    result.is_private      = dock_info["is_private"]

    # --- city from site ---
    data    = validated.get("data", {})
    org     = data.get("organization", {})
    site_id = validated["site_id"]
    site    = next((s for s in org.get("sites", []) if s["id"] == site_id), None)
    if site:
        result.city = site.get("city")

    return result


def plan_mission(validated: dict):

    resolver = LocationResolver()
    try:
        resolver.resolve(
            validated["site_id"],
            validated["user_id"],
            validated["org_id"]
        )
    finally:
        resolver.close()

    system_prompt = build_system_prompt(validated)
    llm           = LLMSetup(system_prompt=system_prompt)
    user_prompt   = build_user_prompt(validated["user_prompt"])

    result = llm.generate(user_prompt)

    # Python enforces all values — LLM output is overwritten
    result = _enforce_computed_values(result, validated)

    return result


# if __name__ == "__main__":

#     user_input = (
#         "Plan a grid mission for O Building "
#         "with altitude 10m, front overlap 80%, side overlap 70%."
#     )

#     validated = {
#         "site_id":     2,
#         "user_id":     3,
#         "org_id":      1,
#         "user_prompt": user_input,
#     }

#     with open("/home/ostajanpure/Desktop/prompt_to_fly/data.json", "r") as f:
#         validated["data"] = json.load(f)

#     result = plan_mission(validated)
#     print(result.model_dump_json(indent=2))