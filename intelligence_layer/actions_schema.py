ACTION_SCHEMA = {
    "HOVER":               {"type": "HOVER",               "params": {"duration": 5}},
    "GIMBAL_CONTROL":      {"type": "GIMBAL_CONTROL",      "params": {"pitch": 0, "yaw": 0}},
    "GIMBAL_DOWN":         {"type": "GIMBAL_DOWN",         "params": None},
    "GIMBAL_RECENTER":     {"type": "GIMBAL_RECENTER",     "params": None},
    "CAMERA_ZOOM":         {"type": "CAMERA_ZOOM",         "params": {"zoom": 50}},
    "IMAGE_CAPTURE_SINGLE":{"type": "IMAGE_SINGLE","params": {"interval": 0, "count": 1}},
    "IMAGE_DISTANCE":      {"type": "IMAGE_DISTANCE",      "params": {"distance": 5}},
    "IMAGE_INTERVAL":      {"type": "IMAGE_INTERVAL",      "params": {"interval": 2}},
    "IMAGE_STOP":          {"type": "IMAGE_STOP",          "params": None},
    "VIDEO_START":         {"type": "VIDEO_START",         "params": None},
    "VIDEO_STOP":          {"type": "VIDEO_STOP",          "params": None},
}