import socketio
from fastapi import FastAPI
import uvicorn
from app.prompt_run import MissionEngine

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*"
)

app = FastAPI()
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

mission_engine = MissionEngine()


# ----------------------------------
# Connection Events
# ----------------------------------

@sio.event
async def connect(sid, environ, auth):
    print(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

# ----------------------------------
# Mission Creation
# ----------------------------------
@sio.on("mission:plan_create")
async def handle_mission_request(sid, data):

    print(f"Mission request received from {sid}")

    response = await mission_engine.main(sid, data)

    print("DEBUG RESPONSE:", response)

    await sio.emit(
        response["event"],
        response["payload"],
        to=sid
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
        to=sid
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
    print("VALIDATION RESPONSE:", response)
    await sio.emit(
        response["event"],
        response["payload"],
        to=sid
    )

# ----------------------------------
# Run Server
# ----------------------------------

if __name__ == "__main__":
    uvicorn.run(
        socket_app,
        host="0.0.0.0",
        port=8000
    )