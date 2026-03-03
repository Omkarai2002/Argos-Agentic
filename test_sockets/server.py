import socketio
from fastapi import FastAPI
import uvicorn
from simple_validator import SimpleValidator

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()

socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


@sio.on("mission:prompt")
async def handle_prompt(sid, data):

    request_id = data.get("request_id")
    mission_data = data.get("mission_data", {})

    validator = SimpleValidator(mission_data)
    result = validator.validate()

    if result["status"] == "need_input":
        await sio.emit("mission:need_input", {
            "request_id": request_id,
            "field": result["field"],
            "message": result["message"]
        }, to=sid)
        return

    await sio.emit("mission:plan", {
        "request_id": request_id,
        "mission": result["mission"]
    }, to=sid)


if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)