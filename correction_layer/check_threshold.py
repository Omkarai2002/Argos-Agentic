from .geofence_validator import GeofenceValidator
from .db_manage import ConnectToDb
from .utils.distance_calculation import total_route_distance
from .utils.duration_calculation import total_time_calculation


class CheckThreshold:

    def __init__(self, validated):
        self.validated = validated
        self.geofence = GeofenceValidator()
        self.c = ConnectToDb()

    def parse_distance(self):
        gps_points = []
        waypoints = self.validated["model_for_extraction_json_output"]["waypoints"]

        for wp in waypoints:
            if wp.get("location"):
                gps_points.append(tuple(wp["location"][0:2]))

        return gps_points

    def _add_error(self, errors, field, message):
        errors.append({
            "field": field,
            "message": message
        })

    def check_waypoints(self):

        errors = []
        mission = self.validated["model_for_extraction_json_output"]

        finish_action = mission["finish_action"]
        takeoff = mission["takeoff_config"]
        waypoints = mission["waypoints"]

        # -----------------------------
        # FINISH ACTION VALIDATION
        # -----------------------------

        if not finish_action.get("type"):
            finish_action["type"] = "LAND"

        if finish_action["type"] != "HOVER":
            finish_action["duration"] = None

        if finish_action["type"] == "HOVER":
            if not finish_action.get("duration"):
                self._add_error(
                    errors,
                    "finish_action.duration",
                    "HOVER finish action requires duration"
                )

        # -----------------------------
        # TAKEOFF VALIDATION
        # -----------------------------

        altitude = takeoff.get("altitude")
        if not altitude or altitude <= 10 or altitude > 100:
            self._add_error(
                errors,
                "takeoff_config.altitude",
                "Altitude must be between 10 and 100"
            )

        speed = takeoff.get("speed")
        if not speed or speed <= 1 or speed >= 10:
            self._add_error(
                errors,
                "takeoff_config.speed",
                "Speed must be between 1 and 10"
            )

        # -----------------------------
        # WAYPOINT VALIDATION
        # -----------------------------

        for i, wp in enumerate(waypoints):

            if not wp.get("location"):
                self._add_error(
                    errors,
                    f"waypoints[{i}].location",
                    "Waypoint location missing or outside geofence"
                )

            altitude = wp.get("altitude")
            if altitude and (altitude <= 10 or altitude >= 100):
                self._add_error(
                    errors,
                    f"waypoints[{i}].altitude",
                    "Waypoint altitude must be between 10 and 100"
                )

            if not wp.get("altitude_mode"):
                wp["altitude_mode"] = "AGL"

            speed = wp.get("speed")
            if speed and (speed <= 1 or speed >= 10):
                self._add_error(
                    errors,
                    f"waypoints[{i}].speed",
                    "Waypoint speed must be between 1 and 10"
                )

            actions = wp.get("actions", [])

            for j, action in enumerate(actions):

                params = action["params"]
                action_type = action["type"]

                # ---------------- HOVER ----------------
                if action_type == "HOVER":
                    duration = params.get("duration")
                    if not duration or duration > 100:
                        self._add_error(
                            errors,
                            f"waypoints[{i}].actions[{j}].params.duration",
                            "Hover duration must be between 1 and 100"
                        )

                # ---------------- GIMBAL_CONTROL ----------------
                if action_type == "GIMBAL_CONTROL":
                    if params.get("pitch") is None:
                        self._add_error(
                            errors,
                            f"waypoints[{i}].actions[{j}].params.pitch",
                            "Pitch required for GIMBAL_CONTROL"
                        )
                    if params.get("yaw") is None:
                        self._add_error(
                            errors,
                            f"waypoints[{i}].actions[{j}].params.yaw",
                            "Yaw required for GIMBAL_CONTROL"
                        )

                # ---------------- CAMERA_ZOOM ----------------
                if action_type == "CAMERA_ZOOM":
                    zoom = params.get("zoom")
                    if not zoom or zoom <= 0 or zoom >= 100:
                        self._add_error(
                            errors,
                            f"waypoints[{i}].actions[{j}].params.zoom",
                            "Zoom must be between 1 and 99"
                        )

                # ---------------- IMAGE_INTERVAL ----------------
                if action_type == "IMAGE_INTERVAL":
                    interval = params.get("interval")
                    count = params.get("count")

                    if not interval or interval < 1:
                        self._add_error(
                            errors,
                            f"waypoints[{i}].actions[{j}].params.interval",
                            "Interval must be >= 1"
                        )

                    if not count or count < 1:
                        self._add_error(
                            errors,
                            f"waypoints[{i}].actions[{j}].params.count",
                            "Count must be >= 1"
                        )

                # ---------------- IMAGE_SINGLE ----------------
                if action_type == "IMAGE_SINGLE":
                    params["count"] = 1
                    params["interval"] = 0

                # ---------------- VIDEO START/STOP ----------------
                if action_type in ["VIDEO_START", "VIDEO_STOP"]:
                    params.update({
                        "count": None,
                        "interval": None,
                        "pitch": None,
                        "yaw": None,
                        "duration": None,
                        "zoom": None,
                        "distance": None
                    })

        # -----------------------------
        # DISTANCE CALCULATION
        # -----------------------------

        try:
            gps_points = self.parse_distance()
            if gps_points:
                segments, total = total_route_distance(gps_points)
                mission["total_distance"] = total
        except Exception:
            pass

        # -----------------------------
        # DURATION CALCULATION
        # -----------------------------

        mission["total_duration"] = total_time_calculation(self.validated)

        # -----------------------------
        # FINAL RESULT
        # -----------------------------

        if errors:
            return {
                "status": "need_input",
                "errors": errors
            }

        return {
            "status": "ok",
            "mission": self.validated
        }