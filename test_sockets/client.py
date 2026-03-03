import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server")

@sio.on("mission:need_input")
def need_input(data):
    print("Server says:", data)

@sio.on("mission:plan")
def mission_plan(data):
    print("Mission completed:", data)

sio.connect("http://localhost:8000")

# Send first mission (missing both altitude and speed)
sio.emit("mission:prompt", {
    "request_id": "r1",
    "mission_data": {
        "takeoff_config": {
            "altitude": 40,
            "speed": None
        }
    }
})

sio.wait()