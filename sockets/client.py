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

router = SuggestionRouter(
    WordCompletionEngine(words),
    SpellCheckEngine(words),
    NGramEngine(top_k=1)
)

sio = socketio.AsyncClient(reconnection=True, reconnection_delay=1, reconnection_delay_max=5)
mission_engine = MissionEngine(sio)

user_cache: dict[int, dict] = {}


# ── Connection Events ─────────────────────────────────────────────

@sio.event
def connect():
    print("Connected to Argos Socket Server")


@sio.event
def disconnect():
    print("Disconnected from Argos")


@sio.on("connected")
def on_authenticated(data):
    print(f"Authenticated by Argos: {data}")
    asyncio.create_task(heartbeat_loop())


@sio.on("argos-ai:user-register")
def on_user_register(data):
    print(f"user data registered: {data}")
    sio.emit("argos-ai:user-registered", {data})


@sio.on("argos-ai:user-connected")
def on_user_connected(data):
    print(f"user connected: {data}")
    user_id = data.get("user_id") or data.get("id")
    if user_id and "user" in data:
        user_cache[user_id] = data["user"]
        print(f"Cached user data for user_id={user_id}")


@sio.on("argos-ai:user-disconnected")
def on_user_disconnected(data):
    print(f"user disconnected: {data}")
    user_id = data.get("user_id") or data.get("id")
    if user_id and user_id in user_cache:
        del user_cache[user_id]
        print(f"Cleared cache for user_id={user_id}")


@sio.on("argos-ai:user-message")
async def on_user_message(data):
    print(f"user message: {data}")

    msg_type = data["type"]
    cid      = data.get("cid", "")
    user_id  = data["user_id"]

    # Inject cached user data into every message
    data["user"] = user_cache.get(user_id, {})

    # ── Prompt ────────────────────────────────────────────────────
    if msg_type == "prompt":
        cid    = str(uuid.uuid4())
        prompt = data["message"]

        await sio.emit("argos-ai:progress", {
            "cid":     cid,
            "user_id": user_id,
            "message": "Processing prompt"
        })

        response = await mission_engine.main(cid, data)

        if not response:
            await sio.emit("argos-ai:response", {
                "type":    "rejected",
                "cid":     cid,
                "message": "No response from engine"
            })
            return

        event = response.get("event", "argos-ai:progress")
        _type = response.get("type", "unknown")

        await sio.emit(event, {
            "type":    _type,
            "user_id": user_id,
            "cid":     cid,
            "message": response["payload"].get("message"),
            "params":  response["payload"] if _type == "success"
                       else response["payload"].get("params", None)
        })

    # ── Reply (human-in-loop) ─────────────────────────────────────
    elif msg_type == "reply":
        event_name = data.get("event", "")

        if event_name == "action:location":
            response = await mission_engine.handle_location_action(cid, data)
        elif event_name == "action:validate":
            response = await mission_engine.handle_validate_action(cid, data)
        else:
            print(f"Unknown reply event: {event_name}")
            return

        _type = response.get("type", "unknown")

        await sio.emit(response.get("event", "argos-ai:progress"), {
            "type":    _type,
            "user_id": user_id,
            "cid":     cid,
            "message": response["payload"].get("message"),
            "params":  response["payload"] if _type == "success"
                       else response["payload"].get("params", None)
        })

    else:
        print(f"Unknown message type: {msg_type}")


# ── Typing suggestions ────────────────────────────────────────────

@sio.on("argos-ai:user-typing")
async def on_user_typing(data):
    timestamp = data["timestamp"]
    try:
        ts        = TextState(data["input"], 5)
        predicted = router.suggest(ts)
        print("predicted:", predicted)
        latency = round((time.time() - timestamp) * 1000, 2)
        await sio.emit("argos-ai:type-suggestion", {
            "user_id":     data["user_id"],
            "relevant":    predicted["suggestions"][0] if len(predicted["suggestions"]) > 0 else "",
            "suggestions": [],
            "latency":     latency
        })
        print(f"user typing : {data}")
    except Exception as e:
        print(e)


# ── Heartbeat ─────────────────────────────────────────────────────

async def heartbeat_loop():
    while sio.connected:
        await sio.emit("ping")
        print("Ping sent to Argos")
        await asyncio.sleep(5)


@sio.on("pong")
def on_pong():
    print("Pong received from Argos")


# ── Connect ───────────────────────────────────────────────────────

async def connect_with_retry():
    try:
        print(f"Connecting to Argos at {ARGOS_SOCKET_URL}...")
        await sio.connect(
            ARGOS_SOCKET_URL,
            headers={"X-Argos-Ai": "argos-ai"},
            auth={"token": P2F_TOKEN},
            transports=["websocket", "polling"]
        )
        await sio.wait()
    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5s...")


if __name__ == "__main__":
    asyncio.run(connect_with_retry())