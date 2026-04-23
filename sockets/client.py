import asyncio
import socketio
from suggestion_layer.text_state.extractor import TextState
from suggestion_layer.router import SuggestionRouter
from suggestion_layer.word_completion.engine import WordCompletionEngine
from suggestion_layer.spell_check.engine import SpellCheckEngine
from suggestion_layer.ngram.engine import NGramEngine
from logging_config import LoggerFeature
import time
import uuid
import logging
from app.prompt_run import MissionEngine
from app.config import ARGOS_SOCKET_URL, P2F_TOKEN

LoggerFeature.setup_logging()

logger = logging.getLogger(__name__)

words = []
#sentences = ["general science", "good morning"]

router = SuggestionRouter(
    WordCompletionEngine(words),
    SpellCheckEngine(words),
    NGramEngine(top_k=1)
)

# P2F is now a CLIENT — connects INTO Argos
sio = socketio.AsyncClient(reconnection=True, reconnection_delay=1, reconnection_delay_max=5)
mission_engine = MissionEngine(sio)


# ── Connection Events ─────────────────────────────────────────────

@sio.event
def connect():
    print("Connected to Argos Socket Server")


@sio.event
def disconnect():
    print("Disconnected from Argos")


@sio.on("connected")
def on_authenticated(data):
    # Argos confirmed our token is valid
    print(f"Authenticated by Argos: {data}")
    asyncio.create_task(heartbeat_loop())  # start heartbeat

@sio.on("argos-ai:user-register")
def on_user_register(data):
    # Argos confirmed our token is valid
    print(f"user data registered: {data}")
    sio.emit("argos-ai:user-registered",{data})

@sio.on("argos-ai:user-disconnected")
def on_user_disconnected(data):
    # Argos confirmed our token is valid
    print(f"user disconnected: {data}")
     # start heartbeat

@sio.on("argos-ai:user-connected")
def on_user_connected(data):
    # Argos confirmed our token is valid
    print(f"user connected: {data}")

@sio.on("argos-ai:user-message")
async def on_user_message(data):
    # Argos confirmed our token is valid

    print(f"user message: {data}")
    type = data["type"]
    cid = data.get('cid', '')
    user_id = data["user_id"]

    # Generate a random UUID (Version 4)
    
    if type == "prompt":
        cid = str(uuid.uuid4())
        print(f"Random UUID: {cid}")
        prompt=data["message"]

        print(f"Query received for user: {cid}")
        print(f"Prompt: {prompt}")

        # Send progress update → Argos will forward to browser
        await sio.emit("argos-ai:progress", {
            "cid": cid,
            "user_id":user_id,
            "payload": {"step": "Processing prompt", "status": "running"}
        })

        # Run your existing MissionEngine (unchanged)
        response = await mission_engine.main(cid, data)

        if not response:
            await sio.emit("argos-ai:response", {
                "type": "rejected",
                "cid": cid,
                "payload": {"step": "No response from engine"}
            })
            return

        # Send final result back to Argos
        await sio.emit(response.get("event", 'argos-ai:progress'), {
            "type": response.get('type', 'unknown'),
            "user_id":user_id,
            "cid": cid,
            "event": response["event"],
            "payload": response["payload"]
        })
    elif type == 'reply':
        if data['event'] == 'action:location':
            response = await mission_engine.handle_location_action(cid, data)

            await sio.emit(response.get("event", 'argos-ai:progress'), {
                "type": response.get('type', 'unknown'),
                "user_id": user_id,
                "cid": cid,
                "event": response["event"],
                "payload": response["payload"]
            })
        elif data['event'] == 'action:validate':
            response = await mission_engine.handle_validate_action(cid, data)

            await sio.emit(response.get("event", 'argos-ai:progress'), {
                "type": response.get('type', 'unknown'),
                "user_id": user_id,
                "cid": cid,
                "event": response["event"],
                "payload": response["payload"]
            })
        else:
            pass
            



@sio.on("argos-ai:user-typing")
def on_user_typing(data):
    # Argos confirmed our token is valid
    # @TODO: find  suggestions
    timestamp=data["timestamp"]

    try:
        ts = TextState(data["input"], 5)
        predicted=router.suggest(ts)
        print("predicted:",predicted)
        latency=time.time() - timestamp
        sio.emit('argos-ai:type-suggestion',{ 'user_id': data["user_id"], 'relevant':predicted['suggestions'][0] if len(predicted["suggestions"])>0 else "", 'suggestions': [],"latency":latency })
        print(f"user typing : {data}")
    except Exception as e:
        print(e)

async def heartbeat_loop():
    while sio.connected:
        await sio.emit("ping")
        print("Ping sent to Argos")
        await asyncio.sleep(5)


@sio.on("pong")
def on_pong():
    print("Pong received from Argos")

async def connect_with_retry():
    try:
        print(f"Connecting to Argos at {ARGOS_SOCKET_URL}...")
        await sio.connect(
            ARGOS_SOCKET_URL,
            headers={
                'X-Argos-Ai': 'argos-ai',
            },
            auth={"token": P2F_TOKEN},   # token sent on handshake
            transports=["websocket","polling"]
        )
        await sio.wait()                 # keep alive

    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5s...")


if __name__ == "__main__":
    asyncio.run(connect_with_retry())