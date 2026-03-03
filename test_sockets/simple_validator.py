class SimpleValidator:

    def __init__(self, mission_data):
        self.mission = mission_data

    def validate(self):
        takeoff = self.mission.get("takeoff_config", {})

        altitude = takeoff.get("altitude")
        if not altitude:
            return {
                "status": "need_input",
                "field": "takeoff_config.altitude",
                "message": "Please provide altitude (10-100)"
            }

        if altitude < 10 or altitude > 100:
            return {
                "status": "need_input",
                "field": "takeoff_config.altitude",
                "message": "Altitude must be between 10 and 100"
            }

        speed = takeoff.get("speed")
        if not speed:
            return {
                "status": "need_input",
                "field": "takeoff_config.speed",
                "message": "Please provide speed (1-10)"
            }

        if speed < 1 or speed > 10:
            return {
                "status": "need_input",
                "field": "takeoff_config.speed",
                "message": "Speed must be between 1 and 10"
            }

        return {
            "status": "ok",
            "mission": self.mission
        }