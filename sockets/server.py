import socketio
from fastapi import FastAPI
import uvicorn
from app.prompt_run import MissionEngine
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

mission_engine = MissionEngine(sio)

@app.get("/")
def home():
    return FileResponse("static/index.html")
# ----------------------------------
# Connection Events
# ----------------------------------

@sio.event
async def connect(sid, environ, auth):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

    if sid in mission_engine.sessions:
        del mission_engine.sessions[sid]
        print("Session cleared for:", sid)
# ----------------------------------
# Mission Creation
# ----------------------------------
@sio.on("mission:plan_create")
async def handle_mission_request(sid, data):

    print(f"Mission request received from {sid}")
    await sio.emit(
        "mission:progress",
        {"step": "Validating prompt", "status": "running","sid":sid},
        room=sid
    )
    response = await mission_engine.main(sid, data)
    if not response:
        print("no response from the server")
        return 
    print("DEBUG RESPONSE:", response)

    await sio.emit(
        response["event"],
        response["payload"],
        room=sid
    )


# ----------------------------------
# Human Review Reply
# ----------------------------------

@sio.on("mission:human_reply")
async def receive_human_reply(sid, data):

    print(f"Human reply received from {sid}: {data}")

    response = await mission_engine.handle_human_reply(
        sid,
        data
    )

    await sio.emit(
        response["event"],
        response["payload"],
        room=sid
    )


# ----------------------------------
# Validation Reply (NEW)
# ----------------------------------

@sio.on("mission:validation_reply")
async def receive_validation_reply(sid, data):

    print(f"Validation reply received from {sid}: {data}")

    response = await mission_engine.handle_validation_reply(
        sid,
        data
    )
    if not response:
        print("No response returned from MissionEngine")
        return 
    print("VALIDATION RESPONSE:", response)
    await sio.emit(
        response["event"],
        response["payload"],
        room=sid
    )

# ----------------------------------
# Run Server
# ----------------------------------

# if __name__ == "__main__":
#     uvicorn.run(
#         socket_app,
#         host="0.0.0.0",
#         port=8000,
#         workers=4
#     )