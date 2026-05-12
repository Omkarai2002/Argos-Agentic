import json
import re
import math

def _resolve_drone_and_camera(validated: dict) -> dict:
    data    = validated.get("data", {})
    org     = data.get("organization", {})
    site_id = validated["site_id"]

    site = next((s for s in org.get("sites", []) if s["id"] == site_id), None)
    if not site:
        return {}

    # Sort by dock_id ascending — primary dock first
    bindings_sorted = sorted(site.get("binding", []), key=lambda b: b["dock_id"])
    bound_drone_ids = [b["drone_id"] for b in bindings_sorted]
    all_drones      = {d["id"]: d for d in org.get("drones", [])}

    for drone_id in bound_drone_ids:
        drone  = all_drones.get(drone_id)
        if not drone:
            continue

        camera = next(
            (p for p in drone.get("payloads", []) if p["type"] == "camera"),
            None
        )
        if not camera:
            continue

        meta   = camera.get("meta", {})
        config = drone.get("config", {})

        return {
            "drone_id":         drone["id"],
            "drone_name":       drone["name"],
            "max_speed":        config.get("max_speed"),
            "max_altitude":     config.get("max_altitude"),
            "camera_name":      camera["name"],
            "focal_length_mm":  meta.get("focal_length"),
            "sensor_width_mm":  meta.get("sensor_width"),
            "sensor_height_mm": meta.get("sensor_height"),
            "image_width_px":   meta.get("camera_width_px"),
            "image_height_px":  meta.get("camera_height_px"),
        }

    return {}


def _resolve_annotations(validated: dict) -> list:
    data = validated.get("data", {})
    org = data.get("organization", {})
    site_id = validated["site_id"]

    site = next((s for s in org.get("sites", []) if s["id"] == site_id), None)
    if not site:
        return []

    annotations = []
    for section in site.get("sections", []):
        for ann in section.get("annotations", []):
            annotations.append(ann)
    return annotations


def _parse_flight_params(user_prompt: str) -> dict:
    params = {
        "altitude_m":    None,
        "front_overlap": 80,
        "side_overlap":  70,
    }

    alt = re.search(
        r'altitude\s+(\d+(?:\.\d+)?)\s*m|(\d+(?:\.\d+)?)\s*m(?:eters?)?\s+altitude|at\s+(\d+(?:\.\d+)?)\s*m',
        user_prompt, re.I
    )
    if alt:
        params["altitude_m"] = float(alt.group(1) or alt.group(2) or alt.group(3))

    front = re.search(r'front\s+overlap[:\s]+(\d+)', user_prompt, re.I)
    if front:
        params["front_overlap"] = int(front.group(1))

    side = re.search(r'side\s+overlap[:\s]+(\d+)', user_prompt, re.I)
    if side:
        params["side_overlap"] = int(side.group(1))

    return params


def _precompute_mission_params(drone_cam: dict, altitude_m: float,
                                front_overlap: int, side_overlap: int) -> dict:
    fl  = drone_cam["focal_length_mm"]
    sw  = drone_cam["sensor_width_mm"]
    sh  = drone_cam["sensor_height_mm"]
    wpx = drone_cam["image_width_px"]

    footprint_x = altitude_m * (sw / fl)
    footprint_y = altitude_m * (sh / fl)

    spacing_x = round(footprint_x * (1 - side_overlap  / 100), 4)
    spacing_y = round(footprint_y * (1 - front_overlap / 100), 4)

    gsd_cm = round((altitude_m * fl * 100) / (sw * wpx), 4)

    return {
        "gsd":       gsd_cm,
        "spacing_x": spacing_x,
        "spacing_y": spacing_y,
        "trigger":   spacing_y,
    }


def _precompute_grid_area(annotation: dict) -> float | None:
    shape    = annotation.get("shape")
    geometry = annotation.get("geometry", {})

    if shape == "circle":
        radius = geometry.get("radius")
        if radius:
            return round(math.pi * radius ** 2, 4)

    elif shape == "polygon":
        coords = geometry.get("hierarchy", [])
        if len(coords) >= 3:
            # Shoelace formula — approximate in degrees, convert to meters
            # 1 degree lat ≈ 111320 m, 1 degree lon ≈ 111320 * cos(lat) m
            avg_lat = sum(c[1] for c in coords) / len(coords)
            lat_m   = 111320
            lon_m   = 111320 * math.cos(math.radians(avg_lat))

            # Convert to meters
            pts = [(c[0] * lon_m, c[1] * lat_m) for c in coords]

            # Shoelace
            n   = len(pts)
            area = 0.0
            for i in range(n):
                j = (i + 1) % n
                area += pts[i][0] * pts[j][1]
                area -= pts[j][0] * pts[i][1]
            return round(abs(area) / 2, 4)

    elif shape == "rectangle":
        pts = geometry.get("points", [])
        if len(pts) == 2:
            avg_lat = (pts[0][1] + pts[1][1]) / 2
            lat_m   = 111320
            lon_m   = 111320 * math.cos(math.radians(avg_lat))
            dx = abs(pts[1][0] - pts[0][0]) * lon_m
            dy = abs(pts[1][1] - pts[0][1]) * lat_m
            return round(dx * dy, 4)

    return None

def _find_annotation_by_prompt(user_prompt: str, annotations: list) -> dict | None:
    """
    Find the annotation the user is referring to by
    matching annotation name against the user prompt.
    """
    prompt_lower = user_prompt.lower()
    for ann in annotations:
        if ann["name"].lower() in prompt_lower:
            return ann
    return None
def build_system_prompt(validated: dict) -> str:

    data    = validated.get("data", {})
    org     = data.get("organization", {})
    site_id = validated["site_id"]
    site    = next((s for s in org.get("sites", []) if s["id"] == site_id), None)

    drone_cam   = _resolve_drone_and_camera(validated)
    annotations = _resolve_annotations(validated)
    params      = _parse_flight_params(validated.get("user_prompt", ""))

    # Pre-compute mission params
    computed = {}
    if drone_cam and params["altitude_m"]:
        computed = _precompute_mission_params(
            drone_cam,
            params["altitude_m"],
            params["front_overlap"],
            params["side_overlap"]
        )

    # Build annotation list with pre-computed areas
    location_lines = []
    for ann in annotations:
        area = _precompute_grid_area(ann)
        area_str = f"{area} m²" if area is not None else "null (point)"
        location_lines.append(
            f"- Name: {ann['name']}\n"
            f"  Shape: {ann['shape']}\n"
            f"  Geometry: {json.dumps(ann['geometry'])}\n"
            f"  Pre-computed area: {area_str}"
        )
    locations_text = "\n\n".join(location_lines) if location_lines else "No locations available."

    # Drone block
    if drone_cam:
        drone_text = (
            f"Drone     : {drone_cam['drone_name']} (ID {drone_cam['drone_id']})\n"
            f"Max speed : {drone_cam['max_speed']} m/s\n"
            f"Max alt   : {drone_cam['max_altitude']} m\n"
            f"Camera    : {drone_cam['camera_name']}\n"
            f"Focal     : {drone_cam['focal_length_mm']} mm\n"
            f"Sensor    : {drone_cam['sensor_width_mm']} x {drone_cam['sensor_height_mm']} mm\n"
            f"Resolution: {drone_cam['image_width_px']} x {drone_cam['image_height_px']} px"
        )
    else:
        drone_text = "No drone resolved for this site."

    # Pre-computed block
    if computed:
        computed_text = f"""
## Pre-computed Values — copy these exactly, do NOT recalculate

gsd                    = {computed['gsd']} cm/pixel
image_spacing.x        = {computed['spacing_x']} m
image_spacing.y        = {computed['spacing_y']} m
image_trigger.distance = {computed['trigger']} m
media_capture.distance = {computed['trigger']} m
image_trigger.interval = 0
image_trigger.images   = 0
gimbal_settings.yaw    = 0
altitude               = {params['altitude_m']} m
front_overlap          = {params['front_overlap']}
side_overlap           = {params['side_overlap']}
speed                  = {drone_cam.get('max_speed', 8.0)} m/s
""".strip()
    else:
        computed_text = "## Flight Parameters\nNo altitude detected — ask user to specify altitude or GSD."

    return f"""
You are a drone mission planning assistant.
Your job is to fill the mission JSON using the values provided below.
Do NOT recalculate anything — use the pre-computed values exactly as given.

---

## Site: {site.get('name') if site else 'Unknown'} (ID: {site_id})

## Drone and Camera (pre-resolved from site binding)
{drone_text}

---

{computed_text}

---

## Available Annotations
{locations_text}

---

## Instructions
1. Find the annotation the user is referring to by name
2. Use its pre-computed area as grid_area
3. Copy all pre-computed values into the correct JSON fields
4. Fill takeoff_config and route_config with the same altitude and speed

## STRICT Output Rules
- waypoints                : always []
- grid_config.points       : always []
- total_distance           : 0
- total_duration           : 0
- type                     : "grid"
- altitude_mode            : "AGL" unless user specifies
- route_config.radius      : 2.0
- grid_config.angle        : 0 unless user specifies
- gimbal_settings.pitch    : -90
- media_capture.mode       : "distance"
- No null values — use schema defaults (0 for numerics, [] for lists)
""".strip()


def build_user_prompt(raw_user_input: str) -> str:
    return raw_user_input.strip()